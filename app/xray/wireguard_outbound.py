from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from ipaddress import ip_interface, ip_network

from app.utils.crypto import validate_wireguard_key


def build_wireguard_outbound(
    *,
    tag: str,
    secret_key: str,
    address: list[str],
    peers: list[dict],
    mtu: int = 1420,
    reserved: list[int] | None = None,
    domain_strategy: str = "ForceIP",
) -> dict:
    if not tag or "," in tag:
        raise ValueError("WireGuard outbound tag must be non-empty and cannot contain commas")
    if not address:
        raise ValueError("WireGuard outbound requires at least one local address")
    if not peers:
        raise ValueError("WireGuard outbound requires at least one peer")
    if not 576 <= mtu <= 9000:
        raise ValueError("WireGuard MTU must be between 576 and 9000")

    normalized_peers = []
    for peer in peers:
        endpoint = str(peer.get("endpoint") or "").strip()
        allowed_ips = peer.get("allowed_ips") or []
        if not endpoint:
            raise ValueError("WireGuard peer endpoint is required")
        if not allowed_ips:
            raise ValueError("WireGuard peer allowed_ips cannot be empty")

        normalized_peer = {
            "publicKey": validate_wireguard_key(peer.get("public_key", ""), "public_key"),
            "endpoint": endpoint,
            "allowedIPs": [str(ip_network(cidr, strict=False)) for cidr in allowed_ips],
            "keepAlive": int(peer.get("keep_alive") or 0),
        }
        peer_reserved = peer.get("reserved")
        if peer_reserved is not None:
            normalized_peer["reserved"] = _validate_reserved(peer_reserved)
        normalized_peers.append(normalized_peer)

    settings = {
        "secretKey": validate_wireguard_key(secret_key, "secret_key"),
        "address": [str(ip_interface(cidr)) for cidr in address],
        "peers": normalized_peers,
        "mtu": mtu,
        "domainStrategy": domain_strategy,
    }
    if reserved is not None:
        settings["reserved"] = _validate_reserved(reserved)

    return {"tag": tag, "protocol": "wireguard", "settings": settings}


def _validate_reserved(reserved: list[int]) -> list[int]:
    if len(reserved) != 3 or any(not isinstance(value, int) or not 0 <= value <= 255 for value in reserved):
        raise ValueError("WireGuard reserved must contain exactly three bytes")
    return list(reserved)


def upsert_wireguard_outbound(
    config: dict,
    *,
    outbound: dict,
    route_inbound_tags: list[str] | None = None,
) -> dict:
    updated = deepcopy(config)
    outbounds = updated.setdefault("outbounds", [])
    outbounds[:] = [item for item in outbounds if item.get("tag") != outbound["tag"]]
    outbounds.append(outbound)

    rules = updated.setdefault("routing", {}).setdefault("rules", [])
    rules[:] = [rule for rule in rules if rule.get("outboundTag") != outbound["tag"]]
    if route_inbound_tags:
        rules.append(
            {
                "type": "field",
                "inboundTag": list(dict.fromkeys(route_inbound_tags)),
                "outboundTag": outbound["tag"],
            }
        )
    return updated


def remove_wireguard_outbound(config: dict, tag: str) -> dict:
    updated = deepcopy(config)
    updated["outbounds"] = [item for item in updated.get("outbounds", []) if item.get("tag") != tag]
    routing = updated.get("routing")
    if isinstance(routing, dict):
        routing["rules"] = [
            rule for rule in routing.get("rules", []) if rule.get("outboundTag") != tag
        ]
    return updated


def atomic_write_json(path: str, payload: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, temporary_path = tempfile.mkstemp(
        prefix=".marzban-xray-wireguard-",
        suffix=".json.tmp",
        dir=directory,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
