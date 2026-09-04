from __future__ import annotations

from copy import deepcopy


def _stream_settings(inbound: dict) -> dict:
    stream = inbound.get("streamSettings")
    return stream if isinstance(stream, dict) else {}


def is_xhttp_inbound(inbound: dict) -> bool:
    stream = _stream_settings(inbound)
    method = stream.get("method") or stream.get("network")
    return method in ("xhttp", "splithttp")


def list_xhttp_inbounds(config: dict) -> list[dict]:
    result = []
    for inbound in config.get("inbounds", []):
        if not is_xhttp_inbound(inbound):
            continue
        stream = _stream_settings(inbound)
        settings = stream.get("xhttpSettings")
        if not isinstance(settings, dict):
            settings = stream.get("splithttpSettings")
        result.append(
            {
                "tag": inbound.get("tag", ""),
                "protocol": inbound.get("protocol", ""),
                "listen": inbound.get("listen"),
                "port": inbound.get("port"),
                "settings": deepcopy(settings) if isinstance(settings, dict) else {},
            }
        )
    return result


def update_xhttp_inbound(config: dict, tag: str, settings: dict) -> dict:
    if not tag:
        raise ValueError("XHTTP inbound tag is required")

    updated = deepcopy(config)
    for inbound in updated.get("inbounds", []):
        if inbound.get("tag") != tag:
            continue
        if not is_xhttp_inbound(inbound):
            raise ValueError(f"Inbound {tag} is not an XHTTP inbound")

        stream = inbound.setdefault("streamSettings", {})
        stream["network"] = "xhttp"
        stream.pop("method", None)
        stream.pop("splithttpSettings", None)
        stream["xhttpSettings"] = deepcopy(settings)
        return updated

    raise ValueError(f"Inbound {tag} does not exist")
