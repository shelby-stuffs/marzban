from __future__ import annotations

import threading

from app import logger, xray
from app.db import GetDB, crud
from app.models.proxy import ProxyTypes
from app.models.user import UserStatus
from app.singbox.config import build_hysteria2_settings_config
from app.singbox.core import SingBoxCore
from app.singbox.settings import generate_settings, load_settings
from config import (
    SINGBOX_CONFIG_PATH,
    SINGBOX_EXECUTABLE_PATH,
    SINGBOX_HYSTERIA_SETTINGS_PATH,
    UVICORN_SSL_CERTFILE,
    UVICORN_SSL_KEYFILE,
)


class SingBoxHysteriaRuntime:
    def __init__(self):
        self.core = SingBoxCore(SINGBOX_EXECUTABLE_PATH, SINGBOX_CONFIG_PATH)
        self._timer = None
        self._timer_lock = threading.Lock()

    def current_settings(self):
        settings = load_settings(SINGBOX_HYSTERIA_SETTINGS_PATH)
        if settings:
            return settings
        generated, _source = generate_settings(
            xray.config,
            fallback_certificate_path=UVICORN_SSL_CERTFILE or "",
            fallback_key_path=UVICORN_SSL_KEYFILE or "",
        )
        from app.singbox.settings import Hysteria2ServerSettings
        return Hysteria2ServerSettings.model_validate(generated)

    def _users(self, tag: str) -> list[dict]:
        result = []
        with GetDB() as db:
            users = crud.get_users(db, status=[UserStatus.active, UserStatus.on_hold])
            for user in users:
                proxy = next(
                    (item for item in user.proxies
                     if getattr(item.type, "value", item.type) == ProxyTypes.Hysteria2.value),
                    None,
                )
                if proxy is None or tag in {item.tag for item in proxy.excluded_inbounds}:
                    continue
                result.append({
                    "name": f"{user.id}.{user.username}",
                    "password": (proxy.settings or {}).get("auth"),
                })
        return result

    def build_current(self, settings=None) -> dict:
        settings = settings or self.current_settings()
        return build_hysteria2_settings_config(
            settings.model_dump(), self._users(settings.tag)
        )

    def apply_current(self) -> bool:
        settings = self.current_settings()
        config = self.build_current(settings)
        if not settings.enabled:
            self.core.stop()
            return False
        changed = self.core.apply(config)
        if changed:
            logger.warning("sing-box Hysteria2 config applied")
        return changed

    def _apply_safely(self):
        try:
            self.apply_current()
        except Exception:
            logger.exception("Unable to apply sing-box Hysteria2 config")

    def schedule_reload(self, delay: float = 0.75) -> None:
        with self._timer_lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(delay, self._apply_safely)
            self._timer.daemon = True
            self._timer.start()


runtime = SingBoxHysteriaRuntime()
