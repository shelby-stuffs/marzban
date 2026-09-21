"""Bounded callback data helpers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Callback:
    action: str
    value: str = ""
    page: int = 1


def encode(action: str, value: str = "", page: int | None = None) -> str:
    value = value.replace(":", "%3A")
    result = f"{action}:{value}"
    if page is not None:
        result += f":{max(1, page)}"
    # Telegram limits callback_data to 64 bytes.
    return result[:64]


def decode(data: str) -> Callback:
    parts = (data or "").split(":")
    try:
        page = max(1, int(parts[2])) if len(parts) > 2 else 1
    except ValueError:
        page = 1
    return Callback(
        action=parts[0] if parts else "",
        value=parts[1].replace("%3A", ":") if len(parts) > 1 else "",
        page=page,
    )