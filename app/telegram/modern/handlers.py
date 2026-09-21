"""Handlers for the rewritten Telegram admin panel."""

from __future__ import annotations

import logging
from functools import wraps

from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

from app.models.user import UserResponse, UserStatus
from config import TELEGRAM_ADMIN_ID

from . import services
from .callbacks import decode, encode
from .state import dialogs
from .ui import confirm, main_menu, protocol_keyboard, system_text, text, user_menu, users_menu

logger = logging.getLogger("uvicorn.error")
_active_bot: TeleBot | None = None


def is_admin(user_id: int) -> bool:
    return bool(user_id and user_id in TELEGRAM_ADMIN_ID)


def _answer(bot: TeleBot, call: types.CallbackQuery, message: str = ""):
    try:
        bot.answer_callback_query(call.id, text=message)
    except ApiTelegramException:
        pass


def _edit(bot: TeleBot, call: types.CallbackQuery, message: str, keyboard=None):
    bot.edit_message_text(
        message,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


def _links(user) -> tuple[str, list[str]]:
    try:
        response = UserResponse.model_validate(user)
        return response.subscription_url, response.links or []
    except Exception:
        logger.exception("Unable to render links for Telegram user %s", user.username)
        return "", []


def _user_text(user) -> str:
    status = getattr(user.status, "value", user.status)
    limit = services.format_usage(user)
    subscription_url, _ = _links(user)
    return (
        f"{'✅' if status == 'active' else '❌'} "
        f"<b>Пользователь {text(user.username)}</b>\n\n"
        f"{limit}\n"
        f"Подписка: <code>{text(subscription_url or 'недоступна')}</code>"
    )


def _show_users(bot: TeleBot, chat_id: int, page: int, call=None):
    users, total, pages = services.list_users(page)
    message = f"👥 <b>Пользователи</b> · {total}\n\nВыберите пользователя:"
    keyboard = users_menu(users, page, pages)
    if call:
        _edit(bot, call, message, keyboard)
    else:
        bot.send_message(chat_id, message, parse_mode="HTML", reply_markup=keyboard)


def _show_user(bot: TeleBot, call, username: str):
    user = services.get_user(username)
    if not user:
        _edit(bot, call, "Пользователь не найден.", main_menu())
        return
    _edit(bot, call, _user_text(user), user_menu(user))


def _admin_only(handler):
    @wraps(handler)
    def wrapped(message, *args, **kwargs):
        user = getattr(message, "from_user", None)
        if not user or not is_admin(user.id):
            if hasattr(message, "chat"):
                return None
            _answer(_active_bot, message, "Доступ запрещён.")
            return None
        return handler(message, *args, **kwargs)
    return wrapped


def register(bot: TeleBot) -> None:
    global _active_bot
    _active_bot = bot

    @bot.message_handler(commands=["start", "help"])
    @_admin_only
    def start(message):
        dialogs.clear(message.chat.id)
        bot.send_message(
            message.chat.id,
            "👋 <b>Marzban</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )

    @bot.message_handler(commands=["users"])
    @_admin_only
    def users_command(message):
        _show_users(bot, message.chat.id, 1)

    @bot.message_handler(commands=["user", "usage"])
    @_admin_only
    def user_command(message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "Использование: <code>/user имя</code>", parse_mode="HTML")
            return
        user = services.get_user(parts[1].strip())
        if not user:
            bot.reply_to(message, "Пользователь не найден.")
        elif message.text.startswith("/usage"):
            bot.reply_to(message, services.format_usage(user), parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, _user_text(user), parse_mode="HTML", reply_markup=user_menu(user))

    @bot.message_handler(func=lambda message: dialogs.get(message.chat.id) is not None)
    @_admin_only
    def dialog_input(message):
        dialog = dialogs.get(message.chat.id)
        if dialog:
            _handle_dialog(bot, message, dialog)

    @bot.callback_query_handler(func=lambda call: True)
    def callback(call):
        if not is_admin(call.from_user.id):
            _answer(bot, call, "Доступ запрещён.")
            return
        _answer(bot, call)
        item = decode(call.data)
        if item.action == "menu":
            dialogs.clear(call.message.chat.id)
            _edit(bot, call, "👋 <b>Marzban</b>\n\nВыберите действие:", main_menu())
        elif item.action == "users":
            _show_users(bot, call.message.chat.id, item.page, call)
        elif item.action == "user":
            _show_user(bot, call, item.value)
        elif item.action == "system":
            _edit(bot, call, system_text(), main_menu())
        elif item.action == "help":
            _edit(bot, call, "Команды: <code>/users</code>, <code>/user имя</code>, <code>/usage имя</code>.", main_menu())
        elif item.action == "create":
            dialogs.begin(call.message.chat.id, "create", step="username")
            _edit(bot, call, "Введите имя нового пользователя:")
        elif item.action == "protocol":
            _create_protocol(bot, call, item.value)
        elif item.action in {"disable", "activate"}:
            _change_status(bot, call, item)
        elif item.action in {"delete", "reset", "revoke"}:
            _edit(bot, call, f"Подтвердить действие для <b>{text(item.value)}</b>?", confirm(item.action, item.value))
        elif item.action.startswith("yes_"):
            _perform_action(bot, call, item.action[4:], item.value)
        elif item.action == "links":
            _show_links(bot, call, item.value)


def _change_status(bot: TeleBot, call, item):
    status = UserStatus.active if item.action == "activate" else UserStatus.disabled
    user = services.set_status(item.value, status)
    _edit(bot, call, _user_text(user), user_menu(user)) if user else _edit(bot, call, "Пользователь не найден.", main_menu())


def _perform_action(bot: TeleBot, call, action: str, username: str):
    operation = {
        "delete": services.delete_user,
        "reset": services.reset_usage,
        "revoke": services.revoke_subscription,
    }[action]
    user = operation(username)
    if not user:
        _edit(bot, call, "Пользователь не найден.", main_menu())
    elif action == "delete":
        _edit(bot, call, "🗑 Пользователь удалён.", main_menu())
    else:
        _edit(bot, call, _user_text(user), user_menu(user))


def _show_links(bot: TeleBot, call, username: str):
    user = services.get_user(username)
    if not user:
        _edit(bot, call, "Пользователь не найден.", main_menu())
        return
    _, links = _links(user)
    message = f"📡 <b>Ссылки {text(username)}</b>\n\n"
    message += "\n".join(f"<code>{text(link)}</code>" for link in links) or "Ссылок нет."
    _edit(bot, call, message, user_menu(user))


def _handle_dialog(bot: TeleBot, message, dialog):
    value = (message.text or "").strip()
    if dialog.name != "create":
        dialogs.clear(message.chat.id)
        return
    step = dialog.data["step"]
    if step == "username":
        if not value or services.get_user(value):
            bot.reply_to(message, "Имя пустое или уже занято.")
            return
        dialogs.update(message.chat.id, username=value, step="data_limit")
        bot.send_message(message.chat.id, "Лимит в GB (0 — без лимита):")
    elif step == "data_limit":
        try:
            limit = float(value.replace(",", "."))
            if limit < 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "Введите неотрицательное число.")
            return
        dialogs.update(message.chat.id, data_limit=limit, step="expire")
        bot.send_message(message.chat.id, "Срок в днях (0 — бессрочно):")
    elif step == "expire":
        try:
            expire = int(value)
            if expire < 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "Введите целое неотрицательное число.")
            return
        dialogs.update(message.chat.id, expire_days=expire, step="protocol")
        bot.send_message(message.chat.id, "Выберите протокол:", reply_markup=protocol_keyboard())


def _create_protocol(bot: TeleBot, call, protocol: str):
    dialog = dialogs.get(call.message.chat.id)
    if not dialog or dialog.name != "create":
        _edit(bot, call, "Диалог создания истёк. Начните заново.", main_menu())
        return
    try:
        user = services.create_user(
            dialog.data["username"],
            protocol,
            dialog.data.get("data_limit", 0),
            dialog.data.get("expire_days", 0),
        )
        dialogs.clear(call.message.chat.id)
        _edit(bot, call, _user_text(user), user_menu(user))
    except Exception as exc:
        logger.exception("Telegram user creation failed")
        _edit(bot, call, f"Не удалось создать пользователя:\n<code>{text(exc)}</code>", main_menu())


def install(bot: TeleBot) -> None:
    register(bot)