import asyncio
import logging
import threading

import nest_asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder

from bot.handlers import register_handlers
from config import settings, validate_settings
from constants import HEALTH_OK_TEXT, ROOT_OK_TEXT
from services.sheets_repo import init_gsheet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)

telegram_app = None
loop = asyncio.new_event_loop()


@app.route("/")
def index():
    return ROOT_OK_TEXT


@app.route("/health")
def health():
    return HEALTH_OK_TEXT


@app.route(f"/{settings.bot_token}", methods=["POST"])
def webhook():
    global telegram_app

    if telegram_app is None:
        return "Bot not ready", 503

    try:
        payload = request.get_json(force=True)
        update = Update.de_json(payload, telegram_app.bot)
        future = asyncio.run_coroutine_threadsafe(
            telegram_app.process_update(update),
            loop,
        )
        future.add_done_callback(_log_future_exception)
        return "OK"
    except Exception:
        log.exception("Error processing incoming update")
        return "Internal Server Error", 500


def _log_future_exception(future):
    try:
        future.result()
    except Exception:
        log.exception("Unhandled exception while processing Telegram update")


async def init_app():
    global telegram_app

    missing = validate_settings()
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    init_gsheet()

    telegram_app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .get_updates_http_version("1.1")
        .build()
    )

    register_handlers(telegram_app)

    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=f"{settings.webhook_url}/{settings.bot_token}")

    log.info("🚀 Webhook set.")
    log.info("✅ Baseline v2 app initialised successfully.")


if __name__ == "__main__":
    nest_asyncio.apply()

    threading.Thread(target=loop.run_forever, daemon=True).start()
    loop.call_soon_threadsafe(lambda: asyncio.ensure_future(init_app()))

    log.info("🟢 Starting Flask on port %s...", settings.port)
    app.run(host="0.0.0.0", port=settings.port)
