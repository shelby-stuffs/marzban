"""Lifecycle of the modular Telegram bot."""

from threading import Thread

from telebot import TeleBot

from .handlers import register

_thread: Thread | None = None
_bot: TeleBot | None = None


def start(bot: TeleBot) -> None:
    global _thread, _bot
    if _thread and _thread.is_alive():
        return
    _bot = bot
    register(bot)
    _thread = Thread(
        target=bot.infinity_polling,
        kwargs={"skip_pending": True},
        daemon=True,
        name="telegram-bot",
    )
    _thread.start()


def stop() -> None:
    if _bot:
        _bot.stop_polling()