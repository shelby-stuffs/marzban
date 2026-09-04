from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Session

from app.db.base import Base

from .allocator import allocate_peer_ips
from .config import WireGuardConfig
from .models import WireGuardPeerSettings


class WireGuardServerRecord(Base):
    __tablename__ = "wireguard_server"

    id = Column(Integer, primary_key=True, default=1)
    endpoint_address = Column(String(256), nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class WireGuardPeerRecord(Base):
    __tablename__ = "wireguard_peers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    settings = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_wireguard_server(db: Session) -> WireGuardServerRecord | None:
    return db.query(WireGuardServerRecord).filter(WireGuardServerRecord.id == 1).first()


def save_wireguard_server(db: Session, *, endpoint_address: str, config: dict) -> WireGuardServerRecord:
    record = get_wireguard_server(db)
    if record is None:
        record = WireGuardServerRecord(id=1, endpoint_address=endpoint_address, config=config)
        db.add(record)
    else:
        record.endpoint_address = endpoint_address
        record.config = config
        record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def get_wireguard_peer(db: Session, user_id: int) -> WireGuardPeerRecord | None:
    return db.query(WireGuardPeerRecord).filter(WireGuardPeerRecord.user_id == user_id).first()


def get_occupied_wireguard_peer_ips(db: Session, *, exclude_user_id: int | None = None) -> list[str]:
    query = db.query(WireGuardPeerRecord)
    if exclude_user_id is not None:
        query = query.filter(WireGuardPeerRecord.user_id != exclude_user_id)

    occupied = []
    for record in query.all():
        settings = WireGuardPeerSettings.model_validate(record.settings)
        occupied.extend(settings.peer_ips)
    return occupied


def save_wireguard_peer(db: Session, *, user_id: int, settings: WireGuardPeerSettings) -> WireGuardPeerRecord:
    settings.ensure_keypair()
    record = get_wireguard_peer(db, user_id)
    serialized = settings.model_dump(mode="json")
    if record is None:
        record = WireGuardPeerRecord(user_id=user_id, settings=serialized)
        db.add(record)
    else:
        record.settings = serialized
        record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def allocate_wireguard_peer(
    db: Session,
    *,
    user_id: int,
    settings: WireGuardPeerSettings | None = None,
) -> WireGuardPeerRecord:
    server_record = get_wireguard_server(db)
    if server_record is None:
        raise ValueError("WireGuard server is not configured")

    current_record = get_wireguard_peer(db, user_id)
    if settings is None:
        settings = (
            WireGuardPeerSettings.model_validate(current_record.settings)
            if current_record is not None
            else WireGuardPeerSettings()
        )

    current_peer_ips = settings.peer_ips
    settings.peer_ips = allocate_peer_ips(
        WireGuardConfig(server_record.config)["address"],
        occupied_peer_ips=get_occupied_wireguard_peer_ips(db, exclude_user_id=user_id),
        current_peer_ips=current_peer_ips,
    )
    settings.ensure_keypair()
    return save_wireguard_peer(db, user_id=user_id, settings=settings)


def delete_wireguard_peer(db: Session, user_id: int) -> bool:
    record = get_wireguard_peer(db, user_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True
