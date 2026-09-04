from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.orm import Session as OrmSession

from app.db.base import SessionLocal, engine
from app.db.models import User

from .storage import allocate_wireguard_peer, delete_wireguard_peer, get_wireguard_server

logger = logging.getLogger(__name__)

_CREATED_IDS = "wireguard_created_user_ids"
_DELETED_IDS = "wireguard_deleted_user_ids"


def reconcile_wireguard_users(*, created_user_ids: set[int], deleted_user_ids: set[int]) -> None:
    """Apply WireGuard lifecycle changes after the user transaction commits."""
    for user_id in deleted_user_ids:
        with SessionLocal() as db:
            try:
                delete_wireguard_peer(db, user_id)
            except Exception:
                db.rollback()
                logger.exception("Failed to release WireGuard peer for user id %s", user_id)

    for user_id in created_user_ids - deleted_user_ids:
        with SessionLocal() as db:
            try:
                if get_wireguard_server(db) is not None:
                    allocate_wireguard_peer(db, user_id=user_id)
            except Exception:
                db.rollback()
                logger.exception("Failed to provision WireGuard peer for user id %s", user_id)


@event.listens_for(OrmSession, "after_flush")
def collect_wireguard_user_changes(session: OrmSession, _flush_context) -> None:
    if session.get_bind() is not engine:
        return

    created = session.info.setdefault(_CREATED_IDS, set())
    deleted = session.info.setdefault(_DELETED_IDS, set())

    created.update(obj.id for obj in session.new if isinstance(obj, User) and obj.id is not None)
    deleted.update(obj.id for obj in session.deleted if isinstance(obj, User) and obj.id is not None)


@event.listens_for(OrmSession, "after_commit")
def apply_wireguard_user_changes(session: OrmSession) -> None:
    if session.get_bind() is not engine:
        return

    created = session.info.pop(_CREATED_IDS, set())
    deleted = session.info.pop(_DELETED_IDS, set())
    if created or deleted:
        reconcile_wireguard_users(created_user_ids=created, deleted_user_ids=deleted)


@event.listens_for(OrmSession, "after_rollback")
def discard_wireguard_user_changes(session: OrmSession) -> None:
    session.info.pop(_CREATED_IDS, None)
    session.info.pop(_DELETED_IDS, None)
