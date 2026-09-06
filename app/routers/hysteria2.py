from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, Query

from app import xray
from app.models.admin import Admin
from app.singbox.advanced import (
    ALLOWED_TOP_LEVEL_KEYS,
    RESERVED_TOP_LEVEL_KEYS,
    load_advanced_config,
    save_advanced_config,
    validate_advanced_config,
)
from app.singbox.config import (
    build_hysteria2_settings_config,
    install_virtual_hysteria_inbound,
)
from app.singbox.settings import (
    Hysteria2ServerSettings,
    generate_settings,
    load_settings,
    save_settings,
)
from app.subscription import cache as subscription_cache
from config import (
    SINGBOX_ADVANCED_CONFIG_PATH,
    SINGBOX_HYSTERIA_ENABLED,
    SINGBOX_HYSTERIA_SETTINGS_PATH,
    UVICORN_SSL_CERTFILE,
    UVICORN_SSL_KEYFILE,
)

router = APIRouter(prefix="/api/hysteria2", tags=["Hysteria2 legacy"] )
singbox_router = APIRouter(prefix="/api/singbox", tags=["sing-box"])


_SECRET_KEYS = {
    "password", "auth", "token", "secret", "private_key", "api_key",
    "access_token", "client_secret", "uuid",
}


def _redact(value, key: str = ""):
    normalized = key.lower().replace("-", "_")
    if normalized in _SECRET_KEYS or normalized.endswith("_password"):
        return "***"
    if isinstance(value, dict):
        return {item_key: _redact(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _generated():
    return generate_settings(
        xray.config,
        fallback_certificate_path=UVICORN_SSL_CERTFILE or "",
        fallback_key_path=UVICORN_SSL_KEYFILE or "",
    )


@router.get("")
@singbox_router.get("")
def get_hysteria2_settings(_admin: Admin = Depends(Admin.check_sudo_admin)):
    settings = load_settings(SINGBOX_HYSTERIA_SETTINGS_PATH)
    source = "saved"
    if settings is None:
        generated, source = _generated()
        return {
            "settings": generated,
            "source": source,
            "persisted": False,
            "feature_enabled": SINGBOX_HYSTERIA_ENABLED,
            "runtime_started": False,
        }
    runtime_started = False
    if SINGBOX_HYSTERIA_ENABLED:
        from app.singbox.runtime import runtime
        runtime_started = runtime.core.started
    return {
        "settings": settings.model_dump(),
        "source": source,
        "persisted": True,
        "feature_enabled": SINGBOX_HYSTERIA_ENABLED,
        "runtime_started": runtime_started,
    }


@router.post("/generate")
@singbox_router.post("/generate")
def generate_hysteria2_settings(_admin: Admin = Depends(Admin.check_sudo_admin)):
    generated, source = _generated()
    return {"settings": generated, "source": source}


@router.get("/runtime-config")
@singbox_router.get("/runtime-config")
def get_generated_runtime_config(_admin: Admin = Depends(Admin.check_sudo_admin)):
    settings = load_settings(SINGBOX_HYSTERIA_SETTINGS_PATH)
    if settings is None:
        generated, _source = _generated()
        try:
            settings = Hysteria2ServerSettings.model_validate(generated)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    from app.singbox.runtime import runtime
    users = runtime._users(settings.tag)
    config = runtime.build_current(settings)
    return {"config": _redact(config), "user_count": len(users)}


@singbox_router.get("/advanced-config")
def get_advanced_singbox_config(_admin: Admin = Depends(Admin.check_sudo_admin)):
    try:
        config, persisted = load_advanced_config(SINGBOX_ADVANCED_CONFIG_PATH)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "config": config,
        "persisted": persisted,
        "allowed_top_level_keys": sorted(ALLOWED_TOP_LEVEL_KEYS),
        "reserved_top_level_keys": sorted(RESERVED_TOP_LEVEL_KEYS),
    }


@singbox_router.post("/advanced-config/check")
def check_advanced_singbox_config(
    payload: dict,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    try:
        advanced = validate_advanced_config(payload)
        checked_by_binary = False
        generated = None
        if SINGBOX_HYSTERIA_ENABLED:
            from app.singbox.runtime import runtime
            generated = runtime.build_current(advanced_config=advanced)
            runtime.core.validate(generated)
            checked_by_binary = True
        return {
            "valid": True,
            "checked_by_binary": checked_by_binary,
            "runtime_config": _redact(generated) if generated else None,
        }
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@singbox_router.put("/advanced-config")
def put_advanced_singbox_config(
    payload: dict,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    runtime = None
    try:
        advanced = validate_advanced_config(payload)
        if SINGBOX_HYSTERIA_ENABLED:
            from app.singbox.runtime import runtime
            generated = runtime.build_current(advanced_config=advanced)
            runtime.core.validate(generated)
        save_advanced_config(SINGBOX_ADVANCED_CONFIG_PATH, advanced)
        if runtime is not None:
            runtime.apply_current()
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "config": advanced,
        "persisted": True,
        "checked_by_binary": runtime is not None,
        "runtime_started": bool(runtime and runtime.core.started),
    }


@router.get("/logs")
@singbox_router.get("/logs")
def get_singbox_logs(
    limit: int = Query(default=200, ge=1, le=500),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    if not SINGBOX_HYSTERIA_ENABLED:
        return {
            "feature_enabled": False,
            "started": False,
            "pid": None,
            "config_path": None,
            "logs": [],
        }
    from app.singbox.runtime import runtime
    process = runtime.core.process
    return {
        "feature_enabled": True,
        "started": runtime.core.started,
        "pid": process.pid if process and process.poll() is None else None,
        "config_path": str(runtime.core.config_path),
        "logs": list(runtime.core.logs)[-limit:],
    }


@router.delete("/logs")
@singbox_router.delete("/logs")
def clear_singbox_logs(_admin: Admin = Depends(Admin.check_sudo_admin)):
    if SINGBOX_HYSTERIA_ENABLED:
        from app.singbox.runtime import runtime
        runtime.core.logs.clear()
    return {"cleared": True}


@router.put("")
@singbox_router.put("")
def put_hysteria2_settings(
    payload: Hysteria2ServerSettings,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    runtime = None
    try:
        if SINGBOX_HYSTERIA_ENABLED:
            from app.singbox.runtime import runtime
            generated = runtime.build_current(payload)
            if payload.enabled:
                runtime.core.validate(generated)
        save_settings(SINGBOX_HYSTERIA_SETTINGS_PATH, payload)
        install_virtual_hysteria_inbound(xray.config, payload.model_dump())
        xray.hosts.update()
        subscription_cache.invalidate()
        if SINGBOX_HYSTERIA_ENABLED:
            runtime.apply_current()
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "settings": payload.model_dump(),
        "persisted": True,
        "feature_enabled": SINGBOX_HYSTERIA_ENABLED,
        "runtime_started": bool(runtime and payload.enabled and runtime.core.started),
    }
