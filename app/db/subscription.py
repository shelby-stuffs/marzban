"""Persistence for subscription client rules, per-device tokens, and external subscriptions."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Session, backref, relationship

from app.db.base import Base
from app.subscription.rules import DEFAULT_RULES, ClientRule

if TYPE_CHECKING:
    from app.db.models import User

#: New tokens carry a prefix so the router can tell them apart from the legacy
#: signed tokens without a database round trip.
TOKEN_PREFIX = "st_"


class ExternalSubscription(Base):
    """An external subscription source to fetch and merge with local configs."""

    __tablename__ = "external_subscriptions"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, unique=True)
    url = Column(String(1024), nullable=False)
    update_interval = Column(Integer, nullable=False, default=3600, server_default="3600")
    is_enabled = Column(Boolean, nullable=False, default=True, server_default="1")
    last_fetched_at = Column(DateTime, nullable=True)
    last_error = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    links = relationship("ExternalSubscriptionLink", back_populates="subscription", cascade="all, delete-orphan")


class ExternalSubscriptionLink(Base):
    """A cached proxy link from an external subscription."""

    __tablename__ = "external_subscription_links"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("external_subscriptions.id"), nullable=False, index=True)
    link = Column(String(2048), nullable=False)
    link_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscription = relationship("ExternalSubscription", back_populates="links")


class SubscriptionRule(Base):
    """A User-Agent rule editable from the dashboard."""

    __tablename__ = "subscription_rules"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    pattern = Column(String(512), nullable=False)
    config_format = Column(String(32), nullable=False)
    as_base64 = Column(Boolean, nullable=False, default=False, server_default="0")
    reverse = Column(Boolean, nullable=False, default=False, server_default="0")
    priority = Column(Integer, nullable=False, default=100, server_default="100")
    ignore_case = Column(Boolean, nullable=False, default=False, server_default="0")
    min_version = Column(String(32), nullable=True)
    max_version = Column(String(32), nullable=True)
    is_disabled = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    def to_client_rule(self) -> ClientRule:
        return ClientRule(
            name=self.name,
            pattern=self.pattern,
            config_format=self.config_format,
            as_base64=bool(self.as_base64),
            reverse=bool(self.reverse),
            priority=int(self.priority),
            ignore_case=bool(self.ignore_case),
            min_version=self.min_version,
            max_version=self.max_version,
            custom_json_flag=None,
            source="database",
        )


class SubscriptionToken(Base):
    """An issued subscription token, one per device when desired."""

    __tablename__ = "subscription_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(128), nullable=False, unique=True, index=True)
    name = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    last_user_agent = Column(String(512), nullable=True)

    user = relationship(
        "User",
        backref=backref("subscription_tokens", cascade="all, delete-orphan"),
    )

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= datetime.utcnow()

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_active(self) -> bool:
        return not (self.is_revoked or self.is_expired)


def generate_token_value() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(24)


def is_managed_token(token: str) -> bool:
    return bool(token) and token.startswith(TOKEN_PREFIX)


# --- rules -----------------------------------------------------------------


def get_rules(db: Session, include_disabled: bool = True) -> List[SubscriptionRule]:
    query = db.query(SubscriptionRule)
    if not include_disabled:
        query = query.filter(SubscriptionRule.is_disabled.is_(False))
    return query.order_by(SubscriptionRule.priority, SubscriptionRule.name).all()


def get_rule(db: Session, rule_id: int) -> Optional[SubscriptionRule]:
    return db.query(SubscriptionRule).filter(SubscriptionRule.id == rule_id).first()


def get_rule_by_name(db: Session, name: str) -> Optional[SubscriptionRule]:
    return db.query(SubscriptionRule).filter(SubscriptionRule.name == name).first()


def load_active_rules(db: Session) -> List[ClientRule]:
    """Return enabled rules as plain dataclasses for the resolver."""
    return [rule.to_client_rule() for rule in get_rules(db, include_disabled=False)]


def create_rule(db: Session, **values) -> SubscriptionRule:
    rule = SubscriptionRule(**values)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule: SubscriptionRule, **values) -> SubscriptionRule:
    for key, value in values.items():
        if value is not None:
            setattr(rule, key, value)
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule: SubscriptionRule) -> None:
    db.delete(rule)
    db.commit()


def seed_default_rules(db: Session) -> List[SubscriptionRule]:
    """Materialise the built-in rules so they can be edited.

    Existing rules are never touched, which keeps the operation idempotent.
    """
    created = []
    for default in DEFAULT_RULES:
        if get_rule_by_name(db, default.name):
            continue
        rule = SubscriptionRule(
            name=default.name,
            pattern=default.pattern,
            config_format=default.config_format,
            as_base64=default.as_base64,
            reverse=default.reverse,
            priority=default.priority,
            ignore_case=default.ignore_case,
            min_version=default.min_version,
            max_version=default.max_version,
            is_disabled=not default.enabled,
        )
        db.add(rule)
        created.append(rule)
    if created:
        db.commit()
        for rule in created:
            db.refresh(rule)
    return created


# --- tokens ----------------------------------------------------------------


def get_tokens(db: Session, user_id: int, include_inactive: bool = True) -> List[SubscriptionToken]:
    tokens = (
        db.query(SubscriptionToken)
        .filter(SubscriptionToken.user_id == user_id)
        .order_by(SubscriptionToken.created_at.desc())
        .all()
    )
    if include_inactive:
        return tokens
    return [token for token in tokens if token.is_active]


def get_token(db: Session, token: str) -> Optional[SubscriptionToken]:
    return db.query(SubscriptionToken).filter(SubscriptionToken.token == token).first()


def get_token_by_id(db: Session, token_id: int) -> Optional[SubscriptionToken]:
    return db.query(SubscriptionToken).filter(SubscriptionToken.id == token_id).first()


def create_token(
    db: Session,
    user_id: int,
    name: Optional[str] = None,
    expires_in_days: Optional[int] = None,
) -> SubscriptionToken:
    token = SubscriptionToken(
        user_id=user_id,
        token=generate_token_value(),
        name=name,
        expires_at=(
            datetime.utcnow() + timedelta(days=expires_in_days)
            if expires_in_days
            else None
        ),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def revoke_token(db: Session, token: SubscriptionToken) -> SubscriptionToken:
    if token.revoked_at is None:
        token.revoked_at = datetime.utcnow()
        db.commit()
        db.refresh(token)
    return token


def delete_token(db: Session, token: SubscriptionToken) -> None:
    db.delete(token)
    db.commit()


def touch_token(db: Session, token: SubscriptionToken, user_agent: str = "") -> SubscriptionToken:
    """Record usage of a token; used for the "last seen" column in the panel."""
    token.last_used_at = datetime.utcnow()
    if user_agent:
        token.last_user_agent = user_agent[:512]
    db.commit()
    db.refresh(token)
    return token


def purge_expired_tokens(db: Session, older_than_days: int = 0) -> int:
    """Delete revoked or expired tokens that are no longer useful."""
    threshold = datetime.utcnow() - timedelta(days=max(older_than_days, 0))
    stale = (
        db.query(SubscriptionToken)
        .filter(
            (SubscriptionToken.revoked_at.isnot(None) & (SubscriptionToken.revoked_at <= threshold))
            | (SubscriptionToken.expires_at.isnot(None) & (SubscriptionToken.expires_at <= threshold))
        )
        .all()
    )
    for token in stale:
        db.delete(token)
    if stale:
        db.commit()
    return len(stale)


# --- external subscriptions --------------------------------------------------


def get_external_subscriptions(db: Session, include_disabled: bool = True) -> List[ExternalSubscription]:
    query = db.query(ExternalSubscription)
    if not include_disabled:
        query = query.filter(ExternalSubscription.is_enabled.is_(True))
    return query.order_by(ExternalSubscription.name).all()


def get_external_subscription(db: Session, sub_id: int) -> Optional[ExternalSubscription]:
    return db.query(ExternalSubscription).filter(ExternalSubscription.id == sub_id).first()


def get_external_subscription_by_name(db: Session, name: str) -> Optional[ExternalSubscription]:
    return db.query(ExternalSubscription).filter(ExternalSubscription.name == name).first()


def create_external_subscription(
    db: Session,
    name: str,
    url: str,
    update_interval: int = 3600,
    is_enabled: bool = True,
) -> ExternalSubscription:
    sub = ExternalSubscription(
        name=name,
        url=url,
        update_interval=update_interval,
        is_enabled=is_enabled,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def update_external_subscription(
    db: Session,
    sub: ExternalSubscription,
    **values,
) -> ExternalSubscription:
    for key, value in values.items():
        if value is not None:
            setattr(sub, key, value)
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return sub


def delete_external_subscription(db: Session, sub: ExternalSubscription) -> None:
    db.delete(sub)
    db.commit()


# --- external subscription links ---------------------------------------------


def compute_link_hash(link: str) -> str:
    """Compute a hash of the link for deduplication."""
    return hashlib.sha256(link.encode()).hexdigest()[:64]


def get_external_subscription_links(db: Session, subscription_id: int) -> List[ExternalSubscriptionLink]:
    return db.query(ExternalSubscriptionLink).filter(
        ExternalSubscriptionLink.subscription_id == subscription_id
    ).all()


def get_all_external_links(db: Session) -> List[str]:
    """Get all cached external links from enabled subscriptions."""
    links = db.query(ExternalSubscriptionLink).join(ExternalSubscription).filter(
        ExternalSubscription.is_enabled.is_(True)
    ).all()
    return [link.link for link in links]


def get_user_external_links(db: Session, user_id: int) -> List[str]:
    """Get cached external links for subscriptions the user has access to."""
    from app.db.models import User, ExternalSubscription
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    # Get enabled external subscriptions the user has access to
    sub_ids = [sub.id for sub in user.external_subscriptions if sub.is_enabled]
    if not sub_ids:
        return []
    
    links = db.query(ExternalSubscriptionLink).filter(
        ExternalSubscriptionLink.subscription_id.in_(sub_ids)
    ).all()
    return [link.link for link in links]


def store_external_links(db: Session, subscription_id: int, links: List[str]) -> int:
    """Store fetched links for a subscription, replacing old ones."""
    # Delete old links
    db.query(ExternalSubscriptionLink).filter(
        ExternalSubscriptionLink.subscription_id == subscription_id
    ).delete()
    
    # Insert new links with deduplication
    seen_hashes = set()
    stored = 0
    for link in links:
        link_hash = compute_link_hash(link)
        if link_hash in seen_hashes:
            continue
        seen_hashes.add(link_hash)
        
        db_link = ExternalSubscriptionLink(
            subscription_id=subscription_id,
            link=link,
            link_hash=link_hash,
        )
        db.add(db_link)
        stored += 1
    
    db.commit()
    return stored
