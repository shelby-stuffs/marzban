from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import User

from .storage import (
    WireGuardPeerRecord,
    allocate_wireguard_peer,
    get_wireguard_server,
)


def get_wireguard_reconciliation_status(db: Session) -> dict:
    user_ids = {row[0] for row in db.query(User.id).all()}
    peer_user_ids = {row[0] for row in db.query(WireGuardPeerRecord.user_id).all()}
    missing_user_ids = sorted(user_ids - peer_user_ids)

    return {
        "configured": get_wireguard_server(db) is not None,
        "total_users": len(user_ids),
        "provisioned_users": len(user_ids & peer_user_ids),
        "missing_users": len(missing_user_ids),
        "orphaned_peers": len(peer_user_ids - user_ids),
    }


def reconcile_wireguard_peers(db: Session) -> dict:
    status = get_wireguard_reconciliation_status(db)
    if not status["configured"]:
        return {**status, "created_peers": 0, "failed_users": []}

    user_ids = {row[0] for row in db.query(User.id).all()}
    peer_user_ids = {row[0] for row in db.query(WireGuardPeerRecord.user_id).all()}
    missing_user_ids = sorted(user_ids - peer_user_ids)

    created_peers = 0
    failed_users = []
    for user_id in missing_user_ids:
        try:
            allocate_wireguard_peer(db, user_id=user_id)
            created_peers += 1
        except Exception as exc:
            db.rollback()
            failed_users.append({"user_id": user_id, "error": str(exc)})

    return {
        **get_wireguard_reconciliation_status(db),
        "created_peers": created_peers,
        "failed_users": failed_users,
    }
