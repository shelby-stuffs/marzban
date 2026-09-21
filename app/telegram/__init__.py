"""Telegram integration entrypoint.

The default implementation is the modular bot in ``app.telegram.modern``.
Set ``TELEGRAM_BOT_MODE=legacy`` to roll back without changing the database.
"""

from app import app
from config import TELEGRAM_API_TOKEN, TELEGRAM_BOT_MODE, TELEGRAM_PROXY_URL
from telebot import TeleBot, apihelper

bot = None
if TELEGRAM_API_TOKEN:
    if TELEGRAM_PROXY_URL:
        apihelper.proxy = {"http": TELEGRAM_PROXY_URL, "https": TELEGRAM_PROXY_URL}
    bot = TeleBot(TELEGRAM_API_TOKEN)


@app.on_event("startup")
def start_bot():
    if not bot:
        return
    if TELEGRAM_BOT_MODE == "legacy":
        from app.telegram.legacy import start as start_legacy
        start_legacy(bot)
    else:
        from app.telegram.modern import start as start_modern
        start_modern(bot)


@app.on_event("shutdown")
def stop_bot():
    if bot and TELEGRAM_BOT_MODE != "legacy":
        from app.telegram.modern import stop as stop_modern
        stop_modern()


# Kept compatible with app.utils.report and existing notification hooks.
from .handlers.report import (  # noqa: E402
    report,
    report_new_user,
    report_user_modification,
    report_user_deletion,
    report_status_change,
    report_user_usage_reset,
    report_user_data_reset_by_next,
    report_user_subscription_revoked,
    report_login,
)

__all__ = [
    "bot",
    "report",
    "report_new_user",
    "report_user_modification",
    "report_user_deletion",
    "report_status_change",
    "report_user_usage_reset",
    "report_user_data_reset_by_next",
    "report_user_subscription_revoked",
    "report_login",
]