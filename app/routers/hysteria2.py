from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException, Query

from app import xray
from app.models.admin import Admin
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
    SINGBOX_HYSTERIA_ENABLED,
    SINGBOX_HYSTERIA_SETTINGS_PATH,
    UVICORN_SSL_CERTFILE,
    UVICORN_SSL_KEYFILE,
)

router = APIRouter(prefix="/api/hysteria2", tags=["Hysteria2 legacy"] )
singbox_router = APIRouter(prefix="/api/singbox", tags=["sing-box"])


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
    config = build_hysteria2_settings_config(settings.model_dump(), users)
    redacted = deepcopy(config)
    for inbound in redacted.get("inbounds", []):
        inbound["users"] = [{"name": user["name"], "password": "***"} for user in inbound.get("users", [])]
        if inbound.get("obfs"):
            inbound["obfs"]["password"] = "***"
    return {"config": redacted, "user_count": len(users)}


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
