"""Thread-safe, expiring dialog state for Telegram chats."""

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any


@dataclass
class Dialog:
    name: str
    data: dict[str, Any]
    expires_at: float


class DialogStore:
    def __init__(self, ttl: int = 900):
        self.ttl = ttl
        self._items: dict[int, Dialog] = {}
        self._lock = RLock()

    def begin(self, chat_id: int, name: str, **data: Any) -> Dialog:
        with self._lock:
            dialog = Dialog(name, data, monotonic() + self.ttl)
            self._items[chat_id] = dialog
            return dialog

    def get(self, chat_id: int) -> Dialog | None:
        with self._lock:
            dialog = self._items.get(chat_id)
            if not dialog:
                return None
            if dialog.expires_at <= monotonic():
                self._items.pop(chat_id, None)
                return None
            return dialog

    def update(self, chat_id: int, **data: Any) -> Dialog | None:
        dialog = self.get(chat_id)
        if dialog:
            with self._lock:
                dialog.data.update(data)
                dialog.expires_at = monotonic() + self.ttl
        return dialog

    def clear(self, chat_id: int) -> None:
        with self._lock:
            self._items.pop(chat_id, None)


dialogs = DialogStore()