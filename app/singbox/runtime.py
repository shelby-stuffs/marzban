from __future__ import annotations

import threading
from collections.abc import Mapping

from app import logger, xray
from app.db import GetDB, crud
from app.models.proxy import ProxyTypes
from app.models.user import UserStatus
from app.singbox.advanced import load_advanced_config
from app.singbox.config import build_hysteria2_settings_config, merge_advanced_config
from app.singbox.core import SingBoxCore
from app.singbox.rulesets import RuleSetsSettings, load_rule_sets, merge_rule_sets
from app.singbox.managed_credentials import managed_password, managed_uuid
from app.singbox.settings import generate_settings, load_settings
from app.singbox.traffic import install_traffic_api
from config import (SINGBOX_ADVANCED_CONFIG_PATH, SINGBOX_CONFIG_PATH, SINGBOX_EXECUTABLE_PATH, SINGBOX_HYSTERIA_SETTINGS_PATH, SINGBOX_RULE_SETS_PATH, SINGBOX_TRAFFIC_ACCOUNTING_ENABLED, SINGBOX_TRAFFIC_API_HOST, SINGBOX_TRAFFIC_API_PORT, UVICORN_SSL_CERTFILE, UVICORN_SSL_KEYFILE)
from xray_api import XRay as XRayAPI


class SingBoxRuntime:
    def __init__(self):
        self.core = SingBoxCore(SINGBOX_EXECUTABLE_PATH, SINGBOX_CONFIG_PATH)
        self._timer = None
        self._timer_lock = threading.Lock()
        self.traffic_api = XRayAPI(SINGBOX_TRAFFIC_API_HOST, SINGBOX_TRAFFIC_API_PORT) if SINGBOX_TRAFFIC_ACCOUNTING_ENABLED else None

    def current_settings(self):
        settings = load_settings(SINGBOX_HYSTERIA_SETTINGS_PATH)
        if settings:
            return settings
        # A custom-only deployment must not require Hysteria2 certificates.
        advanced, _persisted = load_advanced_config(SINGBOX_ADVANCED_CONFIG_PATH)
        if advanced.get("inbounds"):
            from app.singbox.settings import Hysteria2ServerSettings
            return Hysteria2ServerSettings.model_validate({
                "enabled": False,
                "subscription_enabled": False,
                "certificate_path": "",
                "key_path": "",
            })
        generated, _source = generate_settings(xray.config, fallback_certificate_path=UVICORN_SSL_CERTFILE or "", fallback_key_path=UVICORN_SSL_KEYFILE or "")
        from app.singbox.settings import Hysteria2ServerSettings
        return Hysteria2ServerSettings.model_validate(generated)

    def _users(self, tag: str) -> list[dict]:
        result = []
        with GetDB() as db:
            users = crud.get_users(db, status=[UserStatus.active, UserStatus.on_hold])
            for user in users:
                proxy = next((item for item in user.proxies if getattr(item.type, "value", item.type) == ProxyTypes.Hysteria2.value), None)
                if proxy is None or tag in {item.tag for item in proxy.excluded_inbounds}:
                    continue
                result.append({"name": f"{user.id}.{user.username}", "password": (proxy.settings or {}).get("auth")})
        result.sort(key=lambda item: item["name"])
        return result

    @staticmethod
    def _singbox_proxy_type(inbound_type: str):
        return {
            "vmess": ProxyTypes.VMess,
            "trojan": ProxyTypes.Trojan,
            "shadowsocks": ProxyTypes.Shadowsocks,
            "hysteria2": ProxyTypes.Hysteria2,
        }.get(inbound_type)

    @staticmethod
    def _is_marzban_user_name(value: object) -> bool:
        return isinstance(value, str) and value.partition(".")[0].isdigit() and "." in value

    @staticmethod
    def _proxy_user(user, proxy_type, proxy) -> dict | None:
        settings = proxy.settings or {}
        name = f"{user.id}.{user.username}"
        if proxy_type in (ProxyTypes.VLESS, ProxyTypes.VMess):
            identifier = settings.get("id")
            if not identifier:
                return None
            item = {"name": name, "uuid": str(identifier)}
            if proxy_type is ProxyTypes.VLESS and settings.get("flow") not in (None, "", "none"):
                item["flow"] = settings["flow"]
            if proxy_type is ProxyTypes.VMess and settings.get("alterId") is not None:
                item["alterId"] = settings["alterId"]
            return item
        if proxy_type is ProxyTypes.Trojan:
            password = settings.get("password")
        elif proxy_type is ProxyTypes.Shadowsocks:
            password = settings.get("password")
        elif proxy_type is ProxyTypes.Hysteria2:
            password = settings.get("auth")
        else:
            password = None
        return {"name": name, "password": password} if password else None

    @staticmethod
    def _managed_user(user, inbound_type: str, tag: str, secret: str) -> dict | None:
        name = f"{user.id}.{user.username}"
        password = managed_password(secret, user.username, tag)
        if inbound_type in ("http", "mixed", "naive", "socks"):
            return {"Username": user.username, "Password": password}
        if inbound_type in ("anytls", "hysteria2", "shadowtls", "trojan", "shadowsocks"):
            return {"name": name, "password": password}
        if inbound_type == "hysteria":
            return {"name": name, "auth": password}
        if inbound_type == "tuic":
            return {"name": name, "uuid": managed_uuid(secret, user.username, tag), "password": password}
        if inbound_type == "vmess":
            return {"name": name, "uuid": managed_uuid(secret, user.username, tag), "alterId": 0}
        return None

    def _inject_users(self, config: dict, advanced_config: Mapping | None = None) -> set[str]:
        """Add active Marzban users to compatible sing-box inbounds.

        sing-box's V2Ray Stats API reports the configured user name.  The
        ``<uid>.<username>`` convention lets the existing Marzban usage job
        reuse those counters without a second accounting pipeline.
        """
        from app.utils.jwt import get_secret_key

        with GetDB() as db:
            secret = get_secret_key()
            users = crud.get_users(db, status=[UserStatus.active, UserStatus.on_hold])
            custom_tags = {
                item.get("tag")
                for item in (advanced_config or {}).get("inbounds", [])
                if isinstance(item, dict)
            }
            for inbound in config.get("inbounds", []):
                if not isinstance(inbound, dict):
                    continue
                inbound_type = inbound.get("type")
                tag = inbound.get("tag")
                proxy_type = self._singbox_proxy_type(inbound_type) if isinstance(inbound_type, str) else None
                manual_users = inbound.get("users")
                if not isinstance(manual_users, list):
                    manual_users = []
                unnamed_users = [
                    item for item in manual_users
                    if isinstance(item, dict) and not (item.get("name") or item.get("username") or item.get("Username"))
                ]
                by_name = {
                    item.get("name") or item.get("username") or item.get("Username"): item
                    for item in manual_users
                    if isinstance(item, dict) and isinstance(item.get("name") or item.get("username") or item.get("Username"), str)
                }
                if proxy_type is not None:
                    for user in users:
                        if (
                            isinstance(tag, str)
                            and tag in custom_tags
                            and user.singbox_inbounds is not None
                            and tag not in user.singbox_inbounds
                        ):
                            continue
                        proxy = next(
                            (
                                item for item in user.proxies
                                if getattr(item.type, "value", item.type) == proxy_type.value
                            ),
                            None,
                        )
                        if proxy is not None and (
                            isinstance(tag, str)
                            and tag in {item.tag for item in proxy.excluded_inbounds}
                        ):
                            continue
                        generated = (
                            self._proxy_user(user, proxy_type, proxy)
                            if proxy is not None
                            else self._managed_user(user, inbound_type, tag, secret)
                        )
                        if generated:
                            by_name[generated["name"]] = generated
                elif isinstance(inbound_type, str):
                    if isinstance(tag, str):
                        for user in users:
                            if (
                                tag in custom_tags
                                and user.singbox_inbounds is not None
                                and tag not in user.singbox_inbounds
                            ):
                                continue
                            generated = self._managed_user(user, inbound_type, tag, secret)
                            if generated:
                                key = generated.get("name") or generated.get("Username")
                                if key:
                                    by_name[key] = generated
                if proxy_type is not None or inbound_type in {
                    "anytls", "http", "hysteria", "hysteria2", "mixed", "naive",
                    "shadowsocks", "shadowtls", "socks", "trojan", "tuic", "vmess",
                } or manual_users:
                    inbound["users"] = [*unnamed_users, *by_name.values()]

        names = set()
        for inbound in config.get("inbounds", []):
            if not isinstance(inbound, Mapping) or not isinstance(inbound.get("users"), list):
                continue
            for user in inbound["users"]:
                if not isinstance(user, Mapping):
                    continue
                name = user.get("name") or user.get("username")
                if self._is_marzban_user_name(name):
                    names.add(name)
        return names

    @staticmethod
    def _has_explicit_inbounds(advanced_config: Mapping) -> bool:
        return "inbounds" in advanced_config

    def current_advanced_config(self) -> dict:
        config, _persisted = load_advanced_config(SINGBOX_ADVANCED_CONFIG_PATH)
        return config

    def current_rule_sets(self) -> RuleSetsSettings:
        settings, _persisted = load_rule_sets(SINGBOX_RULE_SETS_PATH)
        return settings

    def build_current(self, settings=None, advanced_config=None, rule_sets=None) -> dict:
        settings = settings or self.current_settings()
        if advanced_config is None:
            advanced_config = self.current_advanced_config()
        if rule_sets is None:
            rule_sets = self.current_rule_sets()
        users = self._users(settings.tag)
        managed = build_hysteria2_settings_config(settings.model_dump(), users)
        combined = merge_advanced_config(managed, advanced_config)
        combined = merge_rule_sets(combined, rule_sets)
        # Keep the simple call shape documented by the legacy runtime tests;
        # the second argument carries the advanced config used for this build.
        # _inject_users(combined)
        managed_user_names = self._inject_users(combined, advanced_config)
        runtime_enabled = settings.enabled or self._has_explicit_inbounds(advanced_config)
        if runtime_enabled and SINGBOX_TRAFFIC_ACCOUNTING_ENABLED:
            inbound_tags = (item.get("tag") for item in combined.get("inbounds", []) if isinstance(item, dict))
            combined = install_traffic_api(
                combined,
                host=SINGBOX_TRAFFIC_API_HOST,
                port=SINGBOX_TRAFFIC_API_PORT,
                inbound_tags=inbound_tags,
                users=managed_user_names,
            )
        return combined

    def apply_current(self) -> bool:
        settings = self.current_settings()
        advanced_config = self.current_advanced_config()
        config = self.build_current(settings)
        if not settings.enabled and not self._has_explicit_inbounds(advanced_config):
            self.core.stop()
            return False
        changed = self.core.apply(config)
        if changed:
            logger.warning("sing-box config applied")
        return changed

    def _apply_safely(self):
        try:
            self.apply_current()
        except Exception:
            logger.exception("Unable to apply sing-box Hysteria2 config")

    def schedule_reload(self, delay: float = 1.25) -> None:
        with self._timer_lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(delay, self._run_scheduled_reload)
            self._timer.daemon = True
            self._timer.start()

    def _run_scheduled_reload(self) -> None:
        with self._timer_lock:
            self._timer = None
        self._apply_safely()

    def reload_files(self) -> None:
        self.core.reload()


SingBoxHysteriaRuntime = SingBoxRuntime
runtime = SingBoxRuntime()
