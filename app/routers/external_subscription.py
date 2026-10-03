"""Management API for external subscriptions."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.db import Session, get_db, User
from app.db import subscription as subscription_store
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.user import UserResponse
from app.models.subscription import (
    ExternalSubscriptionCreate,
    ExternalSubscriptionModify,
    ExternalSubscriptionResponse,
    ExternalSubscriptionsResponse,
)

router = APIRouter(tags=["External Subscriptions"], prefix="/api/external-subscription")


def require_sudo(admin: Admin = Depends(get_current_admin)) -> Admin:
    if not admin.is_sudo:
        raise HTTPException(status_code=403, detail="You're not allowed")
    return admin


@router.get("", response_model=ExternalSubscriptionsResponse)
def get_external_subscriptions(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """List all external subscriptions."""
    subs = subscription_store.get_external_subscriptions(db)
    return ExternalSubscriptionsResponse(
        subscriptions=[ExternalSubscriptionResponse.model_validate(sub) for sub in subs]
    )


@router.post("", response_model=ExternalSubscriptionResponse)
def create_external_subscription(
    new_sub: ExternalSubscriptionCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Create a new external subscription."""
    if subscription_store.get_external_subscription_by_name(db, new_sub.name):
        raise HTTPException(status_code=409, detail="External subscription with this name already exists")

    sub = subscription_store.create_external_subscription(
        db,
        name=new_sub.name,
        url=new_sub.url,
        update_interval=new_sub.update_interval,
        is_enabled=new_sub.is_enabled,
    )
    return ExternalSubscriptionResponse.model_validate(sub)


@router.get("/{sub_id}", response_model=ExternalSubscriptionResponse)
def get_external_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Get an external subscription by ID."""
    sub = subscription_store.get_external_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="External subscription not found")
    return ExternalSubscriptionResponse.model_validate(sub)


@router.put("/{sub_id}", response_model=ExternalSubscriptionResponse)
def update_external_subscription(
    sub_id: int,
    modified_sub: ExternalSubscriptionModify,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Update an external subscription."""
    sub = subscription_store.get_external_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="External subscription not found")

    values = modified_sub.model_dump(exclude_unset=True)
    if "name" in values:
        duplicate = subscription_store.get_external_subscription_by_name(db, values["name"])
        if duplicate and duplicate.id != sub.id:
            raise HTTPException(status_code=409, detail="External subscription with this name already exists")

    sub = subscription_store.update_external_subscription(db, sub, **values)
    return ExternalSubscriptionResponse.model_validate(sub)


@router.delete("/{sub_id}")
def delete_external_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Delete an external subscription."""
    sub = subscription_store.get_external_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="External subscription not found")

    subscription_store.delete_external_subscription(db, sub)
    return {}


@router.post("/{sub_id}/fetch")
def fetch_external_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Manually trigger a fetch of an external subscription."""
    sub = subscription_store.get_external_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="External subscription not found")

    from app.jobs.fetch_external_subscriptions import fetch_single_external_subscription
    result = fetch_single_external_subscription(db, sub)
    return result


# --- user-external subscription associations ---


@router.get("/{sub_id}/users", response_model=List[UserResponse])
def get_external_subscription_users(
    sub_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """List users who have access to this external subscription."""
    sub = subscription_store.get_external_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="External subscription not found")
    return [UserResponse.model_validate(user) for user in sub.users]


@router.post("/{sub_id}/users/{user_id}")
def add_user_to_external_subscription(
    sub_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Grant a user access to an external subscription."""
    sub = subscription_store.get_external_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="External subscription not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user not in sub.users:
        sub.users.append(user)
        db.commit()

    return {"status": "ok"}


@router.delete("/{sub_id}/users/{user_id}")
def remove_user_from_external_subscription(
    sub_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_sudo),
):
    """Revoke a user's access to an external subscription."""
    sub = subscription_store.get_external_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="External subscription not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user in sub.users:
        sub.users.remove(user)
        db.commit()

    return {"status": "ok"}