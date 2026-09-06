from app.utils.hysteria2_validation import validate_hysteria2_config

from copy import deepcopy

import commentjson
from fastapi import APIRouter, Depends, HTTPException

from app import xray
from app.models.admin import Admin
from app.models.xhttp import XHTTPInboundSettings
from app.xray import XRayConfig
from app.xray.config import normalize_xray_v26_config
from app.xray.wireguard_outbound import atomic_write_json
from app.xray.xhttp_inbound import list_xhttp_inbounds, update_xhttp_inbound
from config import XRAY_JSON

router = APIRouter(prefix="/api/core/xhttp-inbounds", tags=["Core"])


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
    return normalized


@router.get("")
def get_xhttp_inbounds(_admin: Admin = Depends(Admin.check_sudo_admin)):
    return list_xhttp_inbounds(_read_user_config())


@router.put("/{tag}")
def put_xhttp_inbound(
    tag: str,
    payload: XHTTPInboundSettings,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    try:
        updated = update_xhttp_inbound(
            _read_user_config(),
            tag,
            payload.model_dump(by_alias=True, exclude_none=True),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _validate_and_apply(updated)
    return next(item for item in list_xhttp_inbounds(updated) if item["tag"] == tag)
