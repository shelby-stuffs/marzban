"""Telegram UI builders for the modern bot."""

from html import escape

from telebot import types

from app.models.proxy import ProxyTypes
from app.utils.system import cpu_usage, memory_usage, readable_size, realtime_bandwidth

from .callbacks import encode

STATUS_ICONS = {
    "active": "✅",
    "disabled": "❌",
    "expired": "🕰",
    "limited": "📵",
    "on_hold": "🔌",
}


def main_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("👥 Пользователи", callback_data=encode("users", page=1)),
        types.InlineKeyboardButton("➕ Создать", callback_data=encode("create")),
    )
    keyboard.row(
        types.InlineKeyboardButton("📊 Система", callback_data=encode("system")),
        types.InlineKeyboardButton("❓ Помощь", callback_data=encode("help")),
    )
    return keyboard


def users_menu(users, page: int, total_pages: int):
    keyboard = types.InlineKeyboardMarkup()
    for user in users:
        status = getattr(user.status, "value", user.status)
        keyboard.add(
            types.InlineKeyboardButton(
                f"{STATUS_ICONS.get(status, '❔')} {user.username}",
                callback_data=encode("user", user.username, page),
            )
        )
    navigation = []
    if page > 1:
        navigation.append(types.InlineKeyboardButton("◀️", callback_data=encode("users", page=page - 1)))
    navigation.append(types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data=encode("noop")))
    if page < total_pages:
        navigation.append(types.InlineKeyboardButton("▶️", callback_data=encode("users", page=page + 1)))
    keyboard.row(*navigation)
    keyboard.row(types.InlineKeyboardButton("🔙 Меню", callback_data=encode("menu")))
    return keyboard


def user_menu(user):
    username = user.username
    status = getattr(user.status, "value", user.status)
    action = "activate" if status != "active" else "disable"
    label = "✅ Включить" if action == "activate" else "⏸ Отключить"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(label, callback_data=encode(action, username)),
        types.InlineKeyboardButton("🗑 Удалить", callback_data=encode("delete", username)),
    )
    keyboard.row(
        types.InlineKeyboardButton("🔁 Сбросить трафик", callback_data=encode("reset", username)),
        types.InlineKeyboardButton("🚫 Отозвать подписку", callback_data=encode("revoke", username)),
    )
    keyboard.row(
        types.InlineKeyboardButton("📡 Ссылки", callback_data=encode("links", username)),
        types.InlineKeyboardButton("🔙 Пользователи", callback_data=encode("users", page=1)),
    )
    return keyboard


def confirm(action: str, username: str):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Да", callback_data=encode(f"yes_{action}", username)),
        types.InlineKeyboardButton("Нет", callback_data=encode("user", username)),
    )
    return keyboard


def system_text() -> str:
    mem = memory_usage()
    cpu = cpu_usage()
    speed = realtime_bandwidth()
    return (
        "📊 <b>Состояние сервера</b>\n\n"
        f"CPU: <code>{cpu.percent}%</code> ({cpu.cores} ядер)\n"
        f"RAM: <code>{readable_size(mem.used)}</code> / <code>{readable_size(mem.total)}</code>\n"
        f"↓ <code>{readable_size(speed.incoming_bytes)}/с</code> "
        f"↑ <code>{readable_size(speed.outgoing_bytes)}/с</code>"
    )


def protocol_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    labels = {
        ProxyTypes.VLESS.value: "VLESS",
        ProxyTypes.VMess.value: "VMess",
        ProxyTypes.Trojan.value: "Trojan",
        ProxyTypes.Shadowsocks.value: "Shadowsocks",
        ProxyTypes.Hysteria2.value: "Hysteria2",
    }
    row = []
    for value, label in labels.items():
        row.append(types.InlineKeyboardButton(label, callback_data=encode("protocol", value)))
        if len(row) == 2:
            keyboard.row(*row)
            row = []
    if row:
        keyboard.row(*row)
    keyboard.row(types.InlineKeyboardButton("🔙 Отмена", callback_data=encode("menu")))
    return keyboard


def text(value: object) -> str:
    return escape(str(value))