from dataclasses import dataclass
from typing import Any, Optional, Tuple, Union
from app.models.admin import AdminInDB, AdminValidationResult, Admin
from app.models.user import UserResponse, UserStatus
from app.db import Session, crud, get_db
from app.db import subscription as subscription_store
from config import SUDOERS
from fastapi import Depends, HTTPException
from datetime import datetime, timezone, timedelta
from app.utils.jwt import get_subscription_payload


def validate_admin(db: Session, username: str, password: str) -> Optional[AdminValidationResult]:
    """Validate admin credentials with environment variables or database."""
    if SUDOERS.get(username) == password:
        return AdminValidationResult(username=username, is_sudo=True)

    dbadmin = crud.get_admin(db, username)
    if dbadmin and AdminInDB.model_validate(dbadmin).verify_password(password):
        return AdminValidationResult(username=dbadmin.username, is_sudo=dbadmin.is_sudo)

    return None


def get_admin_by_username(username: str, db: Session = Depends(get_db)):
    """Fetch an admin by username from the database."""
    dbadmin = crud.get_admin(db, username)
    if not dbadmin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return dbadmin


def get_dbnode(node_id: int, db: Session = Depends(get_db)):
    """Fetch a node by its ID from the database, raising a 404 error if not found."""
    dbnode = crud.get_node_by_id(db, node_id)
    if not dbnode:
        raise HTTPException(status_code=404, detail="Node not found")
    return dbnode


def validate_dates(start: Optional[Union[str, datetime]], end: Optional[Union[str, datetime]]) -> (datetime, datetime):
    """Validate if start and end dates are correct and if end is after start."""
    try:
        if start:
            start_date = start if isinstance(start, datetime) else datetime.fromisoformat(
                start).astimezone(timezone.utc)
        else:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if end:
            end_date = end if isinstance(end, datetime) else datetime.fromisoformat(end).astimezone(timezone.utc)
            if start_date and end_date < start_date:
                raise HTTPException(status_code=400, detail="Start date must be before end date")
        else:
            end_date = datetime.now(timezone.utc)

        return start_date, end_date
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date range or format")


def get_user_template(template_id: int, db: Session = Depends(get_db)):
    """Fetch a User Template by its ID, raise 404 if not found."""
    dbuser_template = crud.get_user_template(db, template_id)
    if not dbuser_template:
        raise HTTPException(status_code=404, detail="User Template not found")
    return dbuser_template


@dataclass
class SubscriptionContext:
    """Everything the subscription endpoints need about the caller.

    ``token`` is set only for tokens issued through the token manager; legacy
    signed tokens keep working and simply leave it empty.
    """

    dbuser: Any
    token: Optional[Any] = None


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Not Found")


def _resolve_managed_token(token: str, db: Session) -> Tuple[Any, Any]:
    dbtoken = subscription_store.get_token(db, token)
    if not dbtoken or not dbtoken.is_active:
        raise _not_found()

    dbuser = crud.get_user_by_id(db, dbtoken.user_id)
    if not dbuser:
        raise _not_found()

    # A global revocation invalidates every token issued before it.
    if dbuser.sub_revoked_at and dbtoken.created_at and dbuser.sub_revoked_at > dbtoken.created_at:
        raise _not_found()

    return dbuser, dbtoken


def _resolve_legacy_token(token: str, db: Session) -> Tuple[Any, None]:
    sub = get_subscription_payload(token)
    if not sub:
        raise _not_found()

    dbuser = crud.get_user(db, sub['username'])
    if not dbuser or dbuser.created_at > sub['created_at']:
        raise _not_found()

    if dbuser.sub_revoked_at and dbuser.sub_revoked_at > sub['created_at']:
        raise _not_found()

    return dbuser, None


def resolve_subscription(token: str, db: Session) -> SubscriptionContext:
    """Resolve any subscription token, new or legacy, to its owner."""
    if subscription_store.is_managed_token(token):
        dbuser, dbtoken = _resolve_managed_token(token, db)
    else:
        dbuser, dbtoken = _resolve_legacy_token(token, db)
    return SubscriptionContext(dbuser=dbuser, token=dbtoken)


def get_subscription_context(
        token: str,
        db: Session = Depends(get_db)
) -> SubscriptionContext:
    return resolve_subscription(token, db)


def get_validated_sub(
        token: str,
        db: Session = Depends(get_db)
) -> UserResponse:
    return resolve_subscription(token, db).dbuser


def get_validated_user(
        username: str,
        admin: Admin = Depends(Admin.get_current),
        db: Session = Depends(get_db)
) -> UserResponse:
    dbuser = crud.get_user(db, username)
    if not dbuser:
        raise HTTPException(status_code=404, detail="User not found")

    if not (admin.is_sudo or (dbuser.admin and dbuser.admin.username == admin.username)):
        raise HTTPException(status_code=403, detail="You're not allowed")

    return dbuser


def get_expired_users_list(db: Session, admin: Admin, expired_after: Optional[datetime] = None,
                           expired_before: Optional[datetime] = None):
    expired_before = expired_before or datetime.now(timezone.utc)
    expired_after = expired_after or datetime.min.replace(tzinfo=timezone.utc)

    dbadmin = crud.get_admin(db, admin.username)
    dbusers = crud.get_users(
        db=db,
        status=[UserStatus.expired, UserStatus.limited],
        admin=dbadmin if not admin.is_sudo else None
    )

    return [
        u for u in dbusers
        if u.expire and expired_after.timestamp() <= u.expire <= expired_before.timestamp()
    ]
