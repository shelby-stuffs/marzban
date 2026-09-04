from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.db import Session, get_db
from app.dependencies import get_validated_sub, get_validated_user
from app.models.admin import Admin
from app.wireguard import WireGuardConfig, WireGuardPeerSettings, WireGuardSubscription
from app.wireguard.storage import (
    allocate_wireguard_peer,
    delete_wireguard_peer,
    get_wireguard_peer,
    get_wireguard_server,
    save_wireguard_peer,
    save_wireguard_server,
)
from config import XRAY_SUBSCRIPTION_PATH

router = APIRouter(tags=["WireGuard"])


class WireGuardServerRequest(BaseModel):
    endpoint_address: str = Field(min_length=1, max_length=256)
    interface_name: str = Field(min_length=1, max_length=64)
    private_key: str
    pre_shared_key: str | None = None
    listen_port: int = Field(ge=1, le=65535)
    address: list[str] = Field(min_length=1)

    def wireguard_config(self) -> WireGuardConfig:
        return WireGuardConfig(
            {
                "interface_name": self.interface_name,
                "private_key": self.private_key,
                "pre_shared_key": self.pre_shared_key,
                "listen_port": self.listen_port,
                "address": self.address,
            }
        )


class WireGuardServerResponse(BaseModel):
    endpoint_address: str
    config: dict


def _allocate_or_http_error(
    db: Session,
    *,
    user_id: int,
    settings: WireGuardPeerSettings | None = None,
):
    try:
        return allocate_wireguard_peer(db, user_id=user_id, settings=settings)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "WireGuard server is not configured" else 409
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.put("/api/wireguard/server", response_model=WireGuardServerResponse)
def configure_wireguard_server(
    payload: WireGuardServerRequest,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    config = payload.wireguard_config()
    record = save_wireguard_server(
        db,
        endpoint_address=payload.endpoint_address.strip(),
        config=dict(config),
    )
    return {"endpoint_address": record.endpoint_address, "config": record.config}


@router.get("/api/wireguard/server", response_model=WireGuardServerResponse)
def read_wireguard_server(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    record = get_wireguard_server(db)
    if record is None:
        raise HTTPException(status_code=404, detail="WireGuard server is not configured")
    return {"endpoint_address": record.endpoint_address, "config": record.config}


@router.put("/api/user/{username}/wireguard", response_model=WireGuardPeerSettings)
def configure_wireguard_peer(
    payload: WireGuardPeerSettings,
    db: Session = Depends(get_db),
    dbuser=Depends(get_validated_user),
    _admin: Admin = Depends(Admin.get_current),
):
    if payload.peer_ips:
        record = save_wireguard_peer(db, user_id=dbuser.id, settings=payload)
    else:
        record = _allocate_or_http_error(db, user_id=dbuser.id, settings=payload)
    return WireGuardPeerSettings.model_validate(record.settings)


@router.post("/api/user/{username}/wireguard/allocate", response_model=WireGuardPeerSettings)
def allocate_user_wireguard_peer(
    db: Session = Depends(get_db),
    dbuser=Depends(get_validated_user),
    _admin: Admin = Depends(Admin.get_current),
):
    record = _allocate_or_http_error(db, user_id=dbuser.id)
    return WireGuardPeerSettings.model_validate(record.settings)


@router.get("/api/user/{username}/wireguard", response_model=WireGuardPeerSettings)
def read_wireguard_peer(
    db: Session = Depends(get_db),
    dbuser=Depends(get_validated_user),
    _admin: Admin = Depends(Admin.get_current),
):
    record = get_wireguard_peer(db, dbuser.id)
    if record is None:
        raise HTTPException(status_code=404, detail="WireGuard peer is not configured")
    return WireGuardPeerSettings.model_validate(record.settings)


@router.delete("/api/user/{username}/wireguard")
def remove_wireguard_peer(
    db: Session = Depends(get_db),
    dbuser=Depends(get_validated_user),
    _admin: Admin = Depends(Admin.get_current),
):
    if not delete_wireguard_peer(db, dbuser.id):
        raise HTTPException(status_code=404, detail="WireGuard peer is not configured")
    return {"detail": "WireGuard peer deleted"}


@router.get(f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}/wireguard")
def wireguard_subscription(
    db: Session = Depends(get_db),
    dbuser=Depends(get_validated_sub),
):
    server_record = get_wireguard_server(db)
    if server_record is None:
        raise HTTPException(status_code=404, detail="WireGuard server is not configured")

    peer_record = get_wireguard_peer(db, dbuser.id)
    if peer_record is None:
        raise HTTPException(status_code=404, detail="WireGuard peer is not configured")

    server = WireGuardConfig(server_record.config)
    peer = WireGuardPeerSettings.model_validate(peer_record.settings)
    subscription = WireGuardSubscription()
    subscription.add(
        f"{dbuser.username}-wireguard",
        peer=peer,
        server=server,
        endpoint_address=server_record.endpoint_address,
    )

    return Response(
        content=subscription.render(),
        media_type="application/zip",
        headers={"content-disposition": f'attachment; filename="{dbuser.username}-wireguard.zip"'},
    )
