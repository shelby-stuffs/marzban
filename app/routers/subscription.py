from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Path, Request, Response
from fastapi.responses import HTMLResponse

from app.db import Session, crud, get_db
from app.db import subscription as subscription_store
from app.dependencies import (
    SubscriptionContext,
    get_subscription_context,
    get_validated_sub,
    validate_dates,
)
from app.models.user import SubscriptionUserResponse, UserResponse
from app.subscription import cache
from app.subscription.rules import (
    CONFIG_FORMATS,
    ClientRule,
    ResolvedClient,
    resolve_client,
    resolve_format,
)
from app.subscription.share import encode_title, generate_subscription
from app.templates import render_template
from config import (
    SUB_PROFILE_TITLE,
    SUB_RULES_FROM_DB,
    SUB_SUPPORT_URL,
    SUB_UPDATE_INTERVAL,
    SUBSCRIPTION_PAGE_TEMPLATE,
    XRAY_SUBSCRIPTION_PATH,
)

#: Longest formats first so "v2ray" cannot shadow "v2ray-json" in the path regex.
CLIENT_TYPE_PATTERN = "|".join(sorted(CONFIG_FORMATS, key=len, reverse=True))

router = APIRouter(tags=['Subscription'], prefix=f'/{XRAY_SUBSCRIPTION_PATH}')


def get_subscription_user_info(user: UserResponse) -> dict:
    """Retrieve user subscription information including upload, download, total data, and expiry."""
    return {
        "upload": 0,
        "download": user.used_traffic,
        "total": user.data_limit if user.data_limit is not None else 0,
        "expire": user.expire if user.expire is not None else 0,
    }


def build_response_headers(request: Request, user: UserResponse) -> dict:
    """The single source of truth for subscription headers."""
    return {
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "profile-title": encode_title(SUB_PROFILE_TITLE),
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }


def active_rules(db: Session) -> Optional[List[ClientRule]]:
    """Database rules win when present; otherwise the built-in defaults apply."""
    if not SUB_RULES_FROM_DB:
        return None
    try:
        rules = subscription_store.load_active_rules(db)
    except Exception:
        # A missing or unmigrated table must never break subscription delivery.
        return None
    return rules or None


def cache_key(dbuser, client: ResolvedClient) -> str:
    """Identity of a rendered subscription.

    Traffic counters are intentionally excluded: they change constantly and the
    short TTL keeps the rendered usage figures fresh enough.
    """
    return cache.build_key(
        dbuser.username,
        client.config_format,
        client.as_base64,
        client.reverse,
        getattr(dbuser, "status", None),
        getattr(dbuser, "edit_at", None),
        getattr(dbuser, "sub_revoked_at", None),
        getattr(dbuser, "data_limit", None),
        getattr(dbuser, "expire", None),
    )


def render_subscription(dbuser, user: UserResponse, client: ResolvedClient) -> cache.CachedResponse:
    key = cache_key(dbuser, client)
    cached = cache.get(key)
    if cached is not None:
        return cached

    content = generate_subscription(
        user=user,
        config_format=client.config_format,
        as_base64=client.as_base64,
        reverse=client.reverse,
    )
    return cache.store(key, content)


def subscription_response(
    request: Request,
    dbuser,
    user: UserResponse,
    client: ResolvedClient,
    if_none_match: Optional[str] = None,
) -> Response:
    entry = render_subscription(dbuser, user, client)
    headers = build_response_headers(request, user)
    if cache.ETAG_ENABLED:
        headers["etag"] = entry.etag

    if cache.etag_matches(if_none_match, entry.etag):
        return Response(status_code=304, headers=headers)

    return Response(content=entry.content, media_type=client.media_type, headers=headers)


@router.get("/{token}/")
@router.get("/{token}", include_in_schema=False)
def user_subscription(
    request: Request,
    db: Session = Depends(get_db),
    context: SubscriptionContext = Depends(get_subscription_context),
    user_agent: str = Header(default=""),
    if_none_match: str = Header(default=None, alias="If-None-Match"),
):
    """Provides a subscription link based on the user agent (Clash, V2Ray, etc.)."""
    dbuser = context.dbuser
    user: UserResponse = UserResponse.model_validate(dbuser)

    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        return HTMLResponse(
            render_template(
                SUBSCRIPTION_PAGE_TEMPLATE,
                {"user": user}
            )
        )

    crud.update_user_sub(db, dbuser, user_agent)
    if context.token is not None:
        subscription_store.touch_token(db, context.token, user_agent)

    client = resolve_client(user_agent, rules=active_rules(db))
    return subscription_response(request, dbuser, user, client, if_none_match)


@router.get("/{token}/info", response_model=SubscriptionUserResponse)
def user_subscription_info(
    dbuser: UserResponse = Depends(get_validated_sub),
):
    """Retrieves detailed information about the user's subscription."""
    return dbuser


@router.get("/{token}/usage")
def user_get_usage(
    dbuser: UserResponse = Depends(get_validated_sub),
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db)
):
    """Fetches the usage statistics for the user within a specified date range."""
    start, end = validate_dates(start, end)

    usages = crud.get_user_usages(db, dbuser, start, end)

    return {"usages": usages, "username": dbuser.username}


@router.get("/{token}/{client_type}")
def user_subscription_with_client_type(
    request: Request,
    dbuser: UserResponse = Depends(get_validated_sub),
    client_type: str = Path(..., pattern=CLIENT_TYPE_PATTERN),
    db: Session = Depends(get_db),
    user_agent: str = Header(default=""),
    if_none_match: str = Header(default=None, alias="If-None-Match"),
):
    """Provides a subscription link based on the specified client type (e.g., Clash, V2Ray)."""
    user: UserResponse = UserResponse.model_validate(dbuser)
    client = resolve_format(client_type)
    return subscription_response(request, dbuser, user, client, if_none_match)
