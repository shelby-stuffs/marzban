from fastapi import APIRouter

from . import (
    admin,
    core,
    home,
    hysteria2,
    node,
    subscription,
    subscription_settings,
    system,
    user,
    user_template,
    wireguard_outbound,
    xhttp_inbound,
)

api_router = APIRouter()

routers = [
    admin.router,
    core.router,
    hysteria2.router,
    node.router,
    wireguard_outbound.router,
    xhttp_inbound.router,
    subscription_settings.router,
    subscription_settings.token_router,
    subscription.router,
    system.router,
    user_template.router,
    user.router,
    home.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]
