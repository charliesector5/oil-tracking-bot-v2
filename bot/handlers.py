from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.callbacks import handle_callback
from bot.conversations import (
    cmd_claimoff,
    cmd_claimphoff,
    cmd_claimspecialoff,
    cmd_clockoff,
    cmd_clockphoff,
    cmd_clockspecialoff,
    cmd_history,
    cmd_newuser,
    cmd_startadmin,
    handle_message,
)
from constants import HELP_TEXT, START_TEXT
from services.sheets_repo import healthcheck, try_get_worksheet_title
from services.ledger import compute_overview, compute_user_summary


async def cmd_start(update, context):
    await update.message.reply_text(START_TEXT)


async def cmd_help(update, context):
    await update.message.reply_text(HELP_TEXT)


async def cmd_ping(update, context):
    await update.message.reply_text("pong")


async def cmd_checksheet(update, context):
    ok, message = healthcheck()
    prefix = "✅" if ok else "❌"
    await update.message.reply_text(f"{prefix} {message}")


async def cmd_sheetinfo(update, context):
    title = try_get_worksheet_title()
    if title:
        await update.message.reply_text(f"Connected sheet: {title}")
    else:
        await update.message.reply_text("Sheet not ready.")


async def cmd_summary(update, context):
    uid = str(update.effective_user.id)
    s = compute_user_summary(uid)

    text = (
        f"📊 *Your OIL Summary*\n\n"
        f"👤 Name: {s.user_name}\n"
        f"🆔 ID: {s.user_id}\n"
        f"🔹 Total OIL: {s.total_balance:.1f}\n"
        f"🔸 Normal OIL: {s.normal_balance:.1f}\n"
        f"🏖 Active PH OIL: {s.ph_active:.1f}\n"
        f"⌛ Expired PH OIL: {s.ph_expired:.1f}\n"
        f"⭐ Active Special OIL: {s.special_active:.1f}\n"
        f"⌛ Expired Special OIL: {s.special_expired:.1f}\n"
    )

    if s.last_action or s.last_application_date:
        text += (
            f"\nLast record:\n"
            f"- Action: {s.last_action or '—'}\n"
            f"- Application Date: {s.last_application_date or '—'}"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_overview(update, context):
    items = compute_overview()
    if not items:
        await update.message.reply_text("No records found.")
        return

    lines = ["📋 *Sector OIL Overview*\n"]
    for s in items:
        lines.append(
            f"{s.user_name}\n"
            f"Total: {s.total_balance:.1f} | "
            f"Normal: {s.normal_balance:.1f} | "
            f"PH: {s.ph_active:.1f} | "
            f"Special: {s.special_active:.1f}"
        )

    text = "\n\n".join(lines)

    # Telegram message limit guard
    if len(text) <= 3800:
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    chunk = ""
    for block in lines:
        part = block + "\n\n"
        if len(chunk) + len(part) > 3800:
            await update.message.reply_text(chunk.strip(), parse_mode="Markdown")
            chunk = ""
        chunk += part

    if chunk.strip():
        await update.message.reply_text(chunk.strip(), parse_mode="Markdown")


def register_handlers(application):
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("ping", cmd_ping))
    application.add_handler(CommandHandler("checksheet", cmd_checksheet))
    application.add_handler(CommandHandler("sheetinfo", cmd_sheetinfo))

    application.add_handler(CommandHandler("startadmin", cmd_startadmin))
    application.add_handler(CommandHandler("history", cmd_history))

    application.add_handler(CommandHandler("clockoff", cmd_clockoff))
    application.add_handler(CommandHandler("claimoff", cmd_claimoff))
    application.add_handler(CommandHandler("clockphoff", cmd_clockphoff))
    application.add_handler(CommandHandler("claimphoff", cmd_claimphoff))
    application.add_handler(CommandHandler("clockspecialoff", cmd_clockspecialoff))
    application.add_handler(CommandHandler("claimspecialoff", cmd_claimspecialoff))
    application.add_handler(CommandHandler("newuser", cmd_newuser))

    application.add_handler(CommandHandler("summary", cmd_summary))
    application.add_handler(CommandHandler("overview", cmd_overview))

    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
