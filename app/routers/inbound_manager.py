"""Management API for dynamic inbounds, 3x-ui style."""

from copy import deepcopy

import commentjson
from fastapi import APIRouter, Depends, HTTPException

from app import xray
from app.models.admin import Admin
from app.models.inbound_manager import InboundCreate, InboundModify
from app.subscription import cache as subscription_cache
from app.utils.hysteria2_validation import validate_hysteria2_config
from app.xray import XRayConfig
from app.xray.config import normalize_xray_v26_config
from app.xray.inbound_manager import (
    create_inbound,
    delete_inbound,
    list_inbounds,
    update_inbound,
)
from app.xray.wireguard_outbound import atomic_write_json
from config import XRAY_JSON

router = APIRouter(prefix="/api/core/inbounds", tags=["Core"])


def _read_user_config() -> dict:
    with open(XRAY_JSON, "r", encoding="utf-8") as file:
        return commentjson.loads(file.read())


def _validate_and_apply(payload: dict) -> dict:
    try:
        normalized = normalize_xray_v26_config(deepcopy(payload))
        validate_hysteria2_config(normalized)
        config = XRayConfig(normalized, api_port=xray.config.api_port)
        startup_config = config.include_db_users()
        validate_hysteria2_config(startup_config)
        xray.core.validate_config(startup_config)
    except (ValueError, TypeError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    atomic_write_json(XRAY_JSON, normalized)
    xray.config = config
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)
    xray.hosts.update()
    subscription_cache.invalidate()
    return normalized


@router.get("")
def get_inbounds(_admin: Admin = Depends(Admin.check_sudo_admin)):
    """List all managed inbounds from the Xray config."""
    return list_inbounds(_read_user_config())


@router.post("")
def post_inbound(
    payload: InboundCreate,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Create a new inbound and restart the core."""
    try:
        updated = create_inbound(
            _read_user_config(),
            payload.model_dump(by_alias=True, exclude_none=True),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    normalized = _validate_and_apply(updated)
    return next(
        item for item in list_inbounds(normalized)
        if item["tag"] == payload.tag
    )


@router.put("/{tag}")
def put_inbound(
    tag: str,
    payload: InboundModify,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Update an existing inbound and restart the core."""
    try:
        updated = update_inbound(
            _read_user_config(),
            tag,
            payload.model_dump(by_alias=True, exclude_none=True),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    normalized = _validate_and_apply(updated)
    return next(
        item for item in list_inbounds(normalized)
        if item["tag"] == tag
    )


@router.delete("/{tag}")
def remove_inbound(
    tag: str,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Delete an inbound and restart the core."""
    try:
        updated = delete_inbound(_read_user_config(), tag)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _validate_and_apply(updated)
    return {}
