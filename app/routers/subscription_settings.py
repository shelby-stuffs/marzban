"""Management API for subscription client rules and per-device tokens."""

import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import Session, get_db
from app.db import subscription as subscription_store
from app.dependencies import get_validated_user
from app.models.admin import Admin
from app.models.subscription import (
    SubscriptionClientPreview,
    SubscriptionRuleCreate,
    SubscriptionRuleModify,
    SubscriptionRuleResponse,
    SubscriptionRulesResponse,
    SubscriptionTokenCreate,
    SubscriptionTokenResponse,
    SubscriptionTokensResponse,
)
from app.models.user import UserResponse
from app.subscription import cache
from app.subscription.rules import CONFIG_FORMATS, resolve_client
from config import (
    SUB_TOKEN_DEFAULT_TTL_DAYS,
    SUB_TOKEN_MAX_PER_USER,
    XRAY_SUBSCRIPTION_PATH,
    XRAY_SUBSCRIPTION_URL_PREFIX,
)

router = APIRouter(tags=["Subscription Settings"], prefix="/api/subscription")
token_router = APIRouter(tags=["Subscription Settings"], prefix="/api/user")


def require_sudo(admin: Admin = Depends(Admin.get_current)) -> Admin:
    if not admin.is_sudo:
        raise HTTPException(status_code=403, detail="You're not allowed")
    return admin


def subscription_url(token: str) -> str:
    salt = secrets.token_hex(8)
    url_prefix = XRAY_SUBSCRIPTION_URL_PREFIX.replace("*", salt)
    return f"{url_prefix}/{XRAY_SUBSCRIPTION_PATH}/{token}"


def token_response(dbtoken) -> SubscriptionTokenResponse:
    return SubscriptionTokenResponse(
        id=dbtoken.id,
        name=dbtoken.name,
        token=dbtoken.token,
        url=subscription_url(dbtoken.token),
        created_at=dbtoken.created_at,
        expires_at=dbtoken.expires_at,
        revoked_at=dbtoken.revoked_at,
        last_used_at=dbtoken.last_used_at,
        last_user_agent=dbtoken.last_user_agent,
        is_active=dbtoken.is_active,
    )


# --- client rules ----------------------------------------------------------


@router.get("/rules", response_model=SubscriptionRulesResponse)
def get_subscription_rules(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """List the stored User-Agent rules and the available output formats."""
    rules = subscription_store.get_rules(db)
    return SubscriptionRulesResponse(
        rules=[SubscriptionRuleResponse.model_validate(rule) for rule in rules],
        formats=list(CONFIG_FORMATS),
    )


@router.post("/rules", response_model=SubscriptionRuleResponse)
def create_subscription_rule(
    new_rule: SubscriptionRuleCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Add a rule. Lower priority values are evaluated first."""
    if subscription_store.get_rule_by_name(db, new_rule.name):
        raise HTTPException(status_code=409, detail="Rule already exists")

    rule = subscription_store.create_rule(db, **new_rule.model_dump())
    cache.invalidate()
    return SubscriptionRuleResponse.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=SubscriptionRuleResponse)
def modify_subscription_rule(
    rule_id: int,
    modified_rule: SubscriptionRuleModify,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Update a rule; omitted fields keep their current value."""
    rule = subscription_store.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    values = modified_rule.model_dump(exclude_unset=True)
    if "name" in values:
        duplicate = subscription_store.get_rule_by_name(db, values["name"])
        if duplicate and duplicate.id != rule.id:
            raise HTTPException(status_code=409, detail="Rule already exists")

    # Booleans are applied explicitly so they can be switched off.
    for key in ("as_base64", "reverse", "ignore_case", "is_disabled"):
        if key in values:
            setattr(rule, key, bool(values.pop(key)))

    rule = subscription_store.update_rule(db, rule, **values)
    cache.invalidate()
    return SubscriptionRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}")
def delete_subscription_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Remove a rule. Removing every rule restores the built-in defaults."""
    rule = subscription_store.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    subscription_store.delete_rule(db, rule)
    cache.invalidate()
    return {}


@router.post("/rules/seed", response_model=SubscriptionRulesResponse)
def seed_subscription_rules(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Copy the built-in defaults into the database so they can be edited."""
    subscription_store.seed_default_rules(db)
    cache.invalidate()
    return SubscriptionRulesResponse(
        rules=[
            SubscriptionRuleResponse.model_validate(rule)
            for rule in subscription_store.get_rules(db)
        ],
        formats=list(CONFIG_FORMATS),
    )


@router.get("/preview", response_model=SubscriptionClientPreview)
def preview_subscription_client(
    user_agent: str = Query(default="", description="User-Agent to test"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Show which format a User-Agent would receive with the current rules."""
    rules = subscription_store.load_active_rules(db) or None
    resolved = resolve_client(user_agent, rules=rules)
    return SubscriptionClientPreview(
        user_agent=user_agent,
        rule=resolved.name,
        config_format=resolved.config_format,
        as_base64=resolved.as_base64,
        reverse=resolved.reverse,
        media_type=resolved.media_type,
        source=resolved.source,
    )


@router.get("/cache")
def get_subscription_cache_state(admin: Admin = Depends(require_sudo)):
    """Inspect the subscription response cache."""
    return {"entries": cache.size(), "ttl": cache.TTL, "etag": cache.ETAG_ENABLED}


@router.delete("/cache")
def flush_subscription_cache(admin: Admin = Depends(require_sudo)):
    """Drop every cached subscription response."""
    return {"dropped": cache.invalidate()}


# --- per-user tokens -------------------------------------------------------


@token_router.get("/{username}/subscription/tokens", response_model=SubscriptionTokensResponse)
def get_user_subscription_tokens(
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    """List the tokens issued for a user."""
    tokens = subscription_store.get_tokens(db, dbuser.id)
    return SubscriptionTokensResponse(tokens=[token_response(token) for token in tokens])


@token_router.post("/{username}/subscription/tokens", response_model=SubscriptionTokenResponse)
def create_user_subscription_token(
    new_token: SubscriptionTokenCreate,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    """Issue an additional subscription token, optionally with a lifetime."""
    active = subscription_store.get_tokens(db, dbuser.id, include_inactive=False)
    if SUB_TOKEN_MAX_PER_USER and len(active) >= SUB_TOKEN_MAX_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=f"User already has {SUB_TOKEN_MAX_PER_USER} active tokens",
        )

    expires_in_days = new_token.expires_in_days
    if expires_in_days is None and SUB_TOKEN_DEFAULT_TTL_DAYS > 0:
        expires_in_days = SUB_TOKEN_DEFAULT_TTL_DAYS

    dbtoken = subscription_store.create_token(
        db,
        user_id=dbuser.id,
        name=new_token.name,
        expires_in_days=expires_in_days,
    )
    return token_response(dbtoken)


@token_router.post(
    "/{username}/subscription/tokens/{token_id}/revoke",
    response_model=SubscriptionTokenResponse,
)
def revoke_user_subscription_token(
    token_id: int,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    """Revoke a single token without touching the user's other links."""
    dbtoken = subscription_store.get_token_by_id(db, token_id)
    if not dbtoken or dbtoken.user_id != dbuser.id:
        raise HTTPException(status_code=404, detail="Token not found")

    dbtoken = subscription_store.revoke_token(db, dbtoken)
    cache.invalidate(prefix=f"{dbuser.username}|")
    return token_response(dbtoken)


@token_router.delete("/{username}/subscription/tokens/{token_id}")
def delete_user_subscription_token(
    token_id: int,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    """Delete a token permanently."""
    dbtoken = subscription_store.get_token_by_id(db, token_id)
    if not dbtoken or dbtoken.user_id != dbuser.id:
        raise HTTPException(status_code=404, detail="Token not found")

    subscription_store.delete_token(db, dbtoken)
    cache.invalidate(prefix=f"{dbuser.username}|")
    return {}
