from datetime import date, datetime

from bot.conversations import (
    apply_adjustoil_payload,
    apply_massadjust_payload,
    build_adjust_user_keyboard,
    build_admin_summary_text,
    handle_newuser_apply,
    handle_single_apply,
    update_all_admin_pm,
)
from bot.ui import (
    _is_group,
    build_calendar,
    cancel_keyboard,
    send_group_quiet,
    validate_application_date,
)
from services.runtime_state import pending_payloads, user_state
from services.sheets_repo import last_off_for_user


async def handle_callback(update, context):
    if not update.callback_query:
        return

    q = update.callback_query
    await q.answer()

    data = q.data or ""
    parts = data.split("|")
    if not parts:
        return

    kind = parts[0]
    sid = parts[1] if len(parts) > 1 else ""

    uid = q.from_user.id
    st = user_state.get(uid)

    def not_owner_block():
        return (not st) or (st.get("sid") != sid) or (st.get("owner_id") != uid)

    if kind == "cancel":
        if not_owner_block():
            await q.answer("This isn’t your session.", show_alert=True)
            return
        user_state.pop(uid, None)
        try:
            await q.edit_message_text("🧹 Cancelled.")
        except Exception:
            pass
        return

    if kind == "noop":
        return

    if kind in ("calnav", "manual", "cal", "adjtype", "adjuser", "adjconfirm", "massadjtype", "massadjconfirm"):
        if not_owner_block():
            await q.answer("This isn’t your session.", show_alert=True)
            return

    if kind == "adjtype":
        oil_type = parts[2]
        st["oil_type"] = oil_type
        st["stage"] = "awaiting_target_user"

        try:
            await q.edit_message_text(
                f"🛠 Selected OIL type: {oil_type.title()}\n\nChoose the personnel to adjust:",
                reply_markup=build_adjust_user_keyboard(sid),
            )
        except Exception:
            pass
        return

    if kind == "adjuser":
        target_uid = parts[2]
        users = {uid: name for uid, name in __import__("bot.conversations", fromlist=["_extract_unique_users"])._extract_unique_users()}
        st["target_user_id"] = str(target_uid)
        st["target_name"] = users.get(str(target_uid), str(target_uid))
        st["stage"] = "awaiting_amount"

        try:
            await q.edit_message_text(
                f"👤 Selected: {st['target_name']} ({st['target_user_id']})\n"
                f"🏷 OIL Type: {st['oil_type'].title()}\n\n"
                f"Enter adjustment amount.\n"
                f"Use positive to add, negative to subtract.\n"
                f"Examples: 1.0, -0.5",
                reply_markup=cancel_keyboard(sid),
            )
        except Exception:
            pass
        return

    if kind == "adjconfirm":
        payload = st.get("payload")
        if not payload:
            await q.answer("Nothing to confirm.", show_alert=True)
            return

        await apply_adjustoil_payload(context, payload)

        try:
            await q.edit_message_text(
                "✅ Adjustment applied successfully.\n\n"
                f"User: {payload['target_name']} ({payload['target_user_id']})\n"
                f"Type: {payload['oil_type'].title()}\n"
                f"Adjustment: {payload['amount']:+.1f}",
            )
        except Exception:
            pass

        user_state.pop(uid, None)
        return

    if kind == "massadjtype":
        oil_type = parts[2]
        st["oil_type"] = oil_type
        st["stage"] = "awaiting_amount"

        try:
            await q.edit_message_text(
                f"🛠 Selected OIL type: {oil_type.title()}\n\n"
                f"Enter adjustment amount.\n"
                f"Use positive to add, negative to subtract.\n"
                f"Examples: 1.0, -0.5",
                reply_markup=cancel_keyboard(sid),
            )
        except Exception:
            pass
        return

    if kind == "massadjconfirm":
        payload = st.get("payload")
        if not payload:
            await q.answer("Nothing to confirm.", show_alert=True)
            return

        adjusted, skipped = await apply_massadjust_payload(context, payload)

        lines = [
            "✅ Mass adjustment applied successfully.",
            "",
            f"Type: {payload['oil_type'].title()}",
            f"Adjustment: {payload['amount']:+.1f}",
            f"Adjusted users: {len(adjusted)}",
            f"Skipped users: {len(skipped)}",
        ]

        if skipped:
            preview = ", ".join(skipped[:10])
            if len(skipped) > 10:
                preview += ", ..."
            lines.append(f"Skipped: {preview}")

        try:
            await q.edit_message_text("\n".join(lines))
        except Exception:
            pass

        user_state.pop(uid, None)
        return

    if kind == "calnav":
        try:
            target = datetime.strptime(parts[2], "%Y-%m-%d").date()
        except Exception:
            target = date.today()

        min_d = st.get("min_date")
        max_d = st.get("max_date")
        await q.edit_message_reply_markup(reply_markup=build_calendar(sid, target, min_d, max_d))
        return

    if kind == "manual":
        if st["flow"] in ("normal", "ph", "special") and st["stage"] == "awaiting_app_date":
            st["stage"] = "awaiting_app_date_manual"
            await q.edit_message_text("⌨️ Type the application date as YYYY-MM-DD.", reply_markup=cancel_keyboard(sid))
            return

        if st["flow"] == "newuser" and st["stage"] == "ph_date":
            st["stage"] = "ph_date_manual"
            await q.edit_message_text("⌨️ Type the PH application date as YYYY-MM-DD.", reply_markup=cancel_keyboard(sid))
            return

        return

    if kind == "cal":
        chosen = parts[2]

        if st["flow"] in ("normal", "ph", "special") and st["stage"] == "awaiting_app_date":
            ok, msg = validate_application_date(st.get("action", ""), chosen)
            if not ok:
                await q.answer(msg, show_alert=True)
                return

            st["app_date"] = chosen
            try:
                await q.edit_message_text(f"📅 Application Date: {chosen}")
            except Exception:
                pass

            st["stage"] = "awaiting_reason"

            if st.get("action") == "clockoff":
                prompt = "📝 Enter clocking reason."
            elif st.get("action") == "clockphoff":
                prompt = "📝 Enter PH name."
            elif st.get("action") == "clockspecialoff":
                prompt = "📝 Enter Special Off name."
            else:
                prompt = "📝 Enter remarks (optional). Type 'nil' to skip."

            if update.effective_chat and _is_group(update.effective_chat.type):
                await send_group_quiet(
                    context,
                    q.message.chat.id,
                    prompt,
                    reply_markup=cancel_keyboard(st["sid"]),
                )
            else:
                await context.bot.send_message(
                    chat_id=q.message.chat.id,
                    text=prompt,
                    reply_markup=cancel_keyboard(st["sid"]),
                )
            return

        if st["flow"] == "newuser" and st["stage"] == "ph_date":
            ok, msg = validate_application_date("newuser_ph", chosen)
            if not ok:
                await q.answer(msg, show_alert=True)
                return

            nu = st["newuser"]
            idx = st["ph_idx"]
            nu["ph_entries"].append({"date": chosen, "reason": None})

            try:
                await q.edit_message_text(f"📅 PH Entry {idx+1}/{nu['ph_count']} — Date: {chosen}")
            except Exception:
                pass

            st["stage"] = "ph_reason"
            await send_group_quiet(
                context,
                q.message.chat.id,
                f"PH Entry {idx+1}/{nu['ph_count']} — Enter *PH name*:",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard(sid),
            )
            return

    if kind in ("approve", "deny"):
        key = parts[1] if len(parts) > 1 else ""
        payload = pending_payloads.pop(key, None)
        approver = q.from_user.full_name
        approver_id = q.from_user.id

        if not payload:
            try:
                await q.edit_message_text("⚠️ This request has already been handled.")
            except Exception:
                pass
            return

        if payload.get("type") == "newuser":
            await handle_newuser_apply(update, context, payload, kind == "approve", approver, approver_id)
            summary = build_admin_summary_text(payload, approved=(kind == "approve"), approver_name=approver, final_off=None)
            try:
                await q.edit_message_text(summary)
            except Exception:
                pass
            return

        if payload.get("type") == "single":
            await handle_single_apply(update, context, payload, kind == "approve", approver, approver_id)
            final_off = None
            if kind == "approve":
                cur = last_off_for_user(payload["user_id"])
                calc = cur + (payload["days"] if "clock" in payload["action"] else -payload["days"])
                final_off = calc
            try:
                await q.edit_message_text(
                    build_admin_summary_text(
                        payload,
                        approved=(kind == "approve"),
                        approver_name=approver,
                        final_off=final_off,
                    )
                )
            except Exception:
                pass
            return
