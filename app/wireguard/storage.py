from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Session

from app.db.base import Base

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


def delete_wireguard_peer(db: Session, user_id: int) -> bool:
    record = get_wireguard_peer(db, user_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True
