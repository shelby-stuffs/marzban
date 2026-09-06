from __future__ import annotations

import threading

from app import logger, xray
from app.db import GetDB, crud
from app.models.proxy import ProxyTypes
from app.models.user import UserStatus
from app.singbox.config import build_hysteria2_server_config
from app.singbox.core import SingBoxCore
from config import SINGBOX_CONFIG_PATH, SINGBOX_EXECUTABLE_PATH


class SingBoxHysteriaRuntime:
    def __init__(self):
        self.core = SingBoxCore(SINGBOX_EXECUTABLE_PATH, SINGBOX_CONFIG_PATH)
        self._timer = None
        self._timer_lock = threading.Lock()

    def _users_by_tag(self) -> dict[str, list[dict]]:
        tags = [item["tag"] for item in xray.config.inbounds_by_protocol.get("hysteria", [])]
        result = {tag: [] for tag in tags}
        with GetDB() as db:
            users = crud.get_users(db, status=[UserStatus.active, UserStatus.on_hold])
            for user in users:
                proxy = next(
                    (
                        item for item in user.proxies
                        if getattr(item.type, "value", item.type) == ProxyTypes.Hysteria2.value
                    ),
                    None,
                )
                if proxy is None:
                    continue
                password = (proxy.settings or {}).get("auth")
                excluded = {item.tag for item in proxy.excluded_inbounds}
                for tag in tags:
                    if tag not in excluded:
                        result[tag].append({"name": f"{user.id}.{user.username}", "password": password})
        return result

    def apply_current(self) -> bool:
        config = build_hysteria2_server_config(xray.config, self._users_by_tag())
        if not config["inbounds"]:
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
