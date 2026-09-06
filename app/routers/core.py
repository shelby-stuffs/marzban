from app.utils.hysteria2_validation import validate_hysteria2_config

import asyncio
import json
import os
import tempfile
import time
from copy import deepcopy

import commentjson
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from starlette.websockets import WebSocketDisconnect

from app import xray
from app.db import Session, get_db
from app.subscription import cache as subscription_cache
from app.models.admin import Admin
from app.models.core import CoreStats
from app.utils import responses
from app.xray import XRayConfig
from app.xray.config import normalize_xray_v26_config
from config import XRAY_JSON

router = APIRouter(tags=["Core"], prefix="/api", responses={401: responses._401})


def _atomic_write_json(path: str, payload: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temp_path = tempfile.mkstemp(
        prefix=".marzban-xray-",
        suffix=".json.tmp",
        dir=directory,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(payload, temp_file, indent=4)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.websocket("/core/logs")
async def core_logs(websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token") or websocket.headers.get(
        "Authorization", ""
    ).removeprefix("Bearer ")
    admin = Admin.get_admin(token, db)
    if not admin:
        return await websocket.close(reason="Unauthorized", code=4401)

    if not admin.is_sudo:
        return await websocket.close(reason="You're not allowed", code=4403)

    interval = websocket.query_params.get("interval")
    if interval:
        try:
            interval = float(interval)
        except ValueError:
            return await websocket.close(reason="Invalid interval value", code=4400)
        if interval > 10:
            return await websocket.close(
                reason="Interval must be more than 0 and at most 10 seconds", code=4400
            )

    await websocket.accept()

    cache = ""
    last_sent_ts = 0
    with xray.core.get_logs() as logs:
        while True:
            if interval and time.time() - last_sent_ts >= interval and cache:
                try:
                    await websocket.send_text(cache)
                except (WebSocketDisconnect, RuntimeError):
                    break
                cache = ""
                last_sent_ts = time.time()

            if not logs:
                try:
                    await asyncio.wait_for(websocket.receive(), timeout=0.2)
                    continue
                except asyncio.TimeoutError:
                    continue
                except (WebSocketDisconnect, RuntimeError):
                    break

            log = logs.popleft()

            if interval:
                cache += f"{log}\n"
                continue

            try:
                await websocket.send_text(log)
            except (WebSocketDisconnect, RuntimeError):
                break


@router.get("/core", response_model=CoreStats)
def get_core_stats(admin: Admin = Depends(Admin.get_current)):
    """Retrieve core statistics such as version and uptime."""
    return CoreStats(
        version=xray.core.version,
        started=xray.core.started,
        logs_websocket=router.url_path_for("core_logs"),
    )


@router.post("/core/restart", responses={403: responses._403})
def restart_core(admin: Admin = Depends(Admin.check_sudo_admin)):
    """Restart the core and all connected nodes."""
    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)

    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)

    return {}


@router.get("/core/config", responses={403: responses._403})
def get_core_config(admin: Admin = Depends(Admin.check_sudo_admin)) -> dict:
    """Get the current core configuration."""
    with open(XRAY_JSON, "r") as f:
        config = commentjson.loads(f.read())

    return config


@router.put("/core/config", responses={403: responses._403})
def modify_core_config(
    payload: dict, admin: Admin = Depends(Admin.check_sudo_admin)
) -> dict:
    """Modify the core configuration and restart the core."""
    try:
        normalized_payload = normalize_xray_v26_config(deepcopy(payload))
        validate_hysteria2_config(normalized_payload)
        config = XRayConfig(
            normalized_payload,
            api_port=xray.config.api_port,
        )
        startup_config = config.include_db_users()
        validate_hysteria2_config(startup_config)
        # Validate while the currently working core is still running.
        xray.core.validate_config(startup_config)
    except (ValueError, TypeError, RuntimeError, TimeoutError) as err:
        raise HTTPException(status_code=400, detail=str(err))

    # Persist only the user's normalized config. XRayConfig's dynamic API
    # inbound, policies and database users must never leak into XRAY_JSON.
    _atomic_write_json(XRAY_JSON, normalized_payload)
    xray.config = config
    xray.core.restart(startup_config)

    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)

    xray.hosts.update()
    subscription_cache.invalidate()

    return normalized_payload
