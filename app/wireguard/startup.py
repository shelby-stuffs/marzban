from __future__ import annotations

import logging

from app.db.base import SessionLocal

from .config import WireGuardConfig
from .models import WireGuardPeerSettings
from .runtime import WireGuardRuntime
from .storage import WireGuardPeerRecord, get_wireguard_server

logger = logging.getLogger(__name__)


def restore_wireguard_runtime() -> dict:
    with SessionLocal() as db:
        server_record = get_wireguard_server(db)
        if server_record is None:
            return {"restored": False, "reason": "not_configured"}

        server = WireGuardConfig(server_record.config)
        runtime = WireGuardRuntime()
        interface_name = server["interface_name"]
        if not runtime.should_restore(interface_name):
            return {"restored": False, "reason": "not_enabled"}

        peers = [
            WireGuardPeerSettings.model_validate(record.settings)
            for record in db.query(WireGuardPeerRecord).all()
        ]
        result = runtime.apply(server, peers)
        logger.info("Restored WireGuard interface %s", interface_name)
        return {"restored": True, **result}
