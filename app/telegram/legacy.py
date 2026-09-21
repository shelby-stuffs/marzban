"""Rollback loader for the pre-rewrite Telegram handlers."""

import importlib
from threading import Thread

from telebot import TeleBot

_started = False


def start(bot: TeleBot) -> None:
    global _started
    if _started:
        return
    for name in ("admin", "report", "user"):
        importlib.import_module(f"app.telegram.handlers.{name}")
    from app.telegram import utils
    utils.setup()
    Thread(target=bot.infinity_polling, daemon=True, name="telegram-bot-legacy").start()
    _started = True