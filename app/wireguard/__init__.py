from .allocator import WireGuardNamespace, allocate_peer_ips, build_namespaces
from .config import WireGuardConfig
from .models import WireGuardPeerSettings
from .subscription import WireGuardSubscription, render_wireguard_client_config

# Register SQLAlchemy lifecycle listeners when the WireGuard package is loaded.
from . import lifecycle as _lifecycle

__all__ = [
    "WireGuardConfig",
    "WireGuardNamespace",
    "WireGuardPeerSettings",
    "WireGuardSubscription",
    "allocate_peer_ips",
    "build_namespaces",
    "render_wireguard_client_config",
]
