from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import Session, get_db
from app.models.admin import Admin
from app.wireguard import WireGuardConfig, WireGuardPeerSettings
from app.wireguard.runtime import WireGuardRuntime, WireGuardRuntimeError
from app.wireguard.storage import WireGuardPeerRecord, get_wireguard_server

router = APIRouter(prefix="/api/wireguard/runtime", tags=["WireGuard"])


class WireGuardRuntimeStatus(BaseModel):
    interface_name: str
    active: bool
    config_path: str | None = None
    action: str | None = None


def _load_runtime_state(db: Session) -> tuple[WireGuardConfig, list[WireGuardPeerSettings]]:
    server_record = get_wireguard_server(db)
    if server_record is None:
        raise HTTPException(status_code=404, detail="WireGuard server is not configured")

    peers = [
        WireGuardPeerSettings.model_validate(record.settings)
        for record in db.query(WireGuardPeerRecord).all()
    ]
    return WireGuardConfig(server_record.config), peers


def _runtime_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WireGuardRuntimeError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


@router.get("", response_model=WireGuardRuntimeStatus)
def read_wireguard_runtime_status(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    server, _ = _load_runtime_state(db)
    try:
        return WireGuardRuntime().status(server["interface_name"])
    except (ValueError, WireGuardRuntimeError) as exc:
        raise _runtime_http_error(exc) from exc


@router.post("/apply", response_model=WireGuardRuntimeStatus)
def apply_wireguard_runtime(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    server, peers = _load_runtime_state(db)
    try:
        return WireGuardRuntime().apply(server, peers)
    except (ValueError, WireGuardRuntimeError, OSError) as exc:
        raise _runtime_http_error(exc) from exc


@router.post("/stop", response_model=WireGuardRuntimeStatus)
def stop_wireguard_runtime(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    server, _ = _load_runtime_state(db)
    try:
        return WireGuardRuntime().stop(server["interface_name"])
    except (ValueError, WireGuardRuntimeError, OSError) as exc:
        raise _runtime_http_error(exc) from exc
