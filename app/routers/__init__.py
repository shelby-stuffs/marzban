from fastapi import APIRouter

from . import (
    admin,
    core,
    home,
    node,
    subscription,
    system,
    user,
    user_template,
    wireguard_outbound,
)

api_router = APIRouter()

routers = [
    admin.router,
    core.router,
    node.router,
    wireguard_outbound.router,
    subscription.router,
    system.router,
    user_template.router,
    user.router,
    home.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]
