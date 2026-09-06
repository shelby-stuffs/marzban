from app.utils.hysteria2_validation import validate_hysteria2_config

from copy import deepcopy
from typing import Literal

import commentjson
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import xray
from app.subscription import cache as subscription_cache
from app.models.admin import Admin
from app.xray import XRayConfig
from app.xray.config import normalize_xray_v26_config
from app.xray.wireguard_outbound import (
    atomic_write_json,
    build_wireguard_outbound,
    remove_wireguard_outbound,
    upsert_wireguard_outbound,
)
from config import XRAY_JSON

router = APIRouter(prefix="/api/core/wireguard-outbounds", tags=["Core"])


class XrayWireGuardPeer(BaseModel):
    public_key: str
    endpoint: str = Field(min_length=1)
    allowed_ips: list[str] = Field(min_length=1)
    keep_alive: int = Field(default=0, ge=0, le=65535)
    reserved: list[int] | None = None


class XrayWireGuardOutboundRequest(BaseModel):
    secret_key: str
    address: list[str] = Field(min_length=1)
    peers: list[XrayWireGuardPeer] = Field(min_length=1)
    mtu: int = Field(default=1420, ge=576, le=9000)
    reserved: list[int] | None = None
    domain_strategy: Literal["AsIs", "UseIP", "UseIPv4", "UseIPv6", "ForceIP", "ForceIPv4", "ForceIPv6"] = "ForceIP"
    route_inbound_tags: list[str] = Field(default_factory=list)


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
def list_xray_wireguard_outbounds(
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    return [
        outbound
        for outbound in _read_user_config().get("outbounds", [])
        if outbound.get("protocol") == "wireguard"
    ]


@router.put("/{tag}")
def put_xray_wireguard_outbound(
    tag: str,
    payload: XrayWireGuardOutboundRequest,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    try:
        outbound = build_wireguard_outbound(
            tag=tag,
            secret_key=payload.secret_key,
            address=payload.address,
            peers=[peer.model_dump() for peer in payload.peers],
            mtu=payload.mtu,
            reserved=payload.reserved,
            domain_strategy=payload.domain_strategy,
        )
        updated = upsert_wireguard_outbound(
            _read_user_config(),
            outbound=outbound,
            route_inbound_tags=payload.route_inbound_tags,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _validate_and_apply(updated)


@router.delete("/{tag}")
def delete_xray_wireguard_outbound(
    tag: str,
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    updated = remove_wireguard_outbound(_read_user_config(), tag)
    return _validate_and_apply(updated)
