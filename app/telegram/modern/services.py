"""Application operations exposed to the Telegram adapter."""

from datetime import datetime
from math import ceil

from app.db import GetDB, crud
from app.models.proxy import ProxyTypes
from app.models.user import UserCreate, UserStatus, UserStatusCreate
from app.utils.system import readable_size

PAGE_SIZE = 8


def list_users(page: int = 1):
    page = max(1, page)
    with GetDB() as db:
        users, total = crud.get_users(
            db,
            offset=(page - 1) * PAGE_SIZE,
            limit=PAGE_SIZE,
            sort=[crud.UsersSortingOptions.username],
            return_with_count=True,
        )
    return users, total, max(1, ceil(total / PAGE_SIZE))


def get_user(username: str):
    with GetDB() as db:
        return crud.get_user(db, username)


def set_status(username: str, status: UserStatus):
    with GetDB() as db:
        user = crud.get_user(db, username)
        return crud.update_user_status(db, user, status) if user else None


def delete_user(username: str):
    with GetDB() as db:
        user = crud.get_user(db, username)
        return crud.remove_user(db, user) if user else None


def reset_usage(username: str):
    with GetDB() as db:
        user = crud.get_user(db, username)
        return crud.reset_user_data_usage(db, user) if user else None


def revoke_subscription(username: str):
    with GetDB() as db:
        user = crud.get_user(db, username)
        return crud.revoke_user_sub(db, user) if user else None


def create_user(username: str, protocol: str, data_limit_gb: float, expire_days: int):
    protocol = protocol.lower().strip()
    if protocol == "hysteria2":
        protocol = ProxyTypes.Hysteria2.value
    proxy_type = ProxyTypes(protocol)
    payload = UserCreate(
        username=username.strip(),
        proxies={proxy_type: {}},
        data_limit=int(data_limit_gb * 1024**3) if data_limit_gb else None,
        expire=int(datetime.now().timestamp()) + expire_days * 86400 if expire_days else 0,
        status=UserStatusCreate.active,
    )
    with GetDB() as db:
        return crud.create_user(db, payload)


def format_usage(user) -> str:
    limit = readable_size(user.data_limit) if user.data_limit else "без лимита"
    used = readable_size(user.used_traffic) if user.used_traffic else "0 B"
    remaining = readable_size(max(0, user.data_limit - user.used_traffic)) if user.data_limit else "∞"
    expire = datetime.fromtimestamp(user.expire).strftime("%Y-%m-%d") if user.expire else "никогда"
    return (
        f"👤 <b>{user.username}</b>\n"
        f"Статус: <code>{user.status}</code>\n"
        f"Трафик: <code>{used}</code> / <code>{limit}</code>\n"
        f"Осталось: <code>{remaining}</code>\n"
        f"Истекает: <code>{expire}</code>"
    )