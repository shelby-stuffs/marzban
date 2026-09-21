"""Modular Telegram bot implementation.

Handlers are registered only from :func:`start`, never while importing the
FastAPI application. This makes startup deterministic and keeps the legacy
bot available as a rollback option.
"""

from .runtime import start, stop

__all__ = ["start", "stop"]