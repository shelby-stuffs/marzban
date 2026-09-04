from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import Session, get_db
from app.models.admin import Admin
from app.wireguard.reconcile import (
    get_wireguard_reconciliation_status,
    reconcile_wireguard_peers,
)

router = APIRouter(prefix="/api/wireguard/reconciliation", tags=["WireGuard"])


class WireGuardReconciliationFailure(BaseModel):
    user_id: int
    error: str


class WireGuardReconciliationStatus(BaseModel):
    configured: bool
    total_users: int
    provisioned_users: int
    missing_users: int
    orphaned_peers: int


class WireGuardReconciliationResult(WireGuardReconciliationStatus):
    created_peers: int
    failed_users: list[WireGuardReconciliationFailure]


@router.get("", response_model=WireGuardReconciliationStatus)
def read_wireguard_reconciliation_status(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    return get_wireguard_reconciliation_status(db)


@router.post("", response_model=WireGuardReconciliationResult)
def run_wireguard_reconciliation(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(Admin.check_sudo_admin),
):
    result = reconcile_wireguard_peers(db)
    if not result["configured"]:
        raise HTTPException(status_code=409, detail="WireGuard server is not configured")
    return result
