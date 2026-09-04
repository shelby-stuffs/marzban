from __future__ import annotations

from copy import deepcopy
from random import choice

from .clash import ClashMetaConfiguration as BaseClashMetaConfiguration


_FIELD_MAP = {
    "noGRPCHeader": "no-grpc-header",
    "noSSEHeader": "no-sse-header",
    "scMaxEachPostBytes": "sc-max-each-post-bytes",
    "scMinPostsIntervalMs": "sc-min-posts-interval-ms",
    "scMaxBufferedPosts": "sc-max-buffered-posts",
    "scStreamUpServerSecs": "sc-stream-up-server-secs",
    "xPaddingBytes": "x-padding-bytes",
    "xPaddingObfsMode": "x-padding-obfs-mode",
    "xPaddingKey": "x-padding-key",
    "xPaddingHeader": "x-padding-header",
    "xPaddingPlacement": "x-padding-placement",
    "xPaddingMethod": "x-padding-method",
    "uplinkHTTPMethod": "uplink-http-method",
    "sessionIDPlacement": "session-placement",
    "sessionIDKey": "session-key",
    "sessionIDTable": "session-id-table",
    "sessionIDLength": "session-id-length",
    "seqPlacement": "seq-placement",
    "seqKey": "seq-key",
    "uplinkDataPlacement": "uplink-data-placement",
    "uplinkDataKey": "uplink-data-key",
    "uplinkChunkSize": "uplink-chunk-size",
    "serverMaxHeaderBytes": "server-max-header-bytes",
}


def _clean(value):
    if isinstance(value, dict):
        return {key: cleaned for key, item in value.items() if (cleaned := _clean(item)) is not None}
    if value is None or value == "" or value == {} or value == []:
        return None
    return value


def _first(value):
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _reuse_settings(xmux):
    if not isinstance(xmux, dict):
        return None
    mapping = {
        "maxConcurrency": "max-concurrency",
        "maxConnections": "max-connections",
        "cMaxReuseTimes": "c-max-reuse-times",
        "hMaxRequestTimes": "h-max-request-times",
        "hMaxReusableSecs": "h-max-reusable-secs",
        "hKeepAlivePeriod": "h-keep-alive-period",
    }
    return _clean({mapping.get(key, key): value for key, value in xmux.items()})


def _download_settings(settings):
    if not isinstance(settings, dict):
        return None
    stream = settings.get("streamSettings", {})
    if not isinstance(stream, dict):
        stream = {}
    xhttp = settings.get("xhttpSettings") or stream.get("xhttpSettings") or {}
    if not isinstance(xhttp, dict):
        xhttp = {}
    security = settings.get("security") or stream.get("security")
    tls = settings.get(f"{security}Settings", {}) or stream.get(f"{security}Settings", {})
    if not isinstance(tls, dict):
        tls = {}
    return _clean({
        "server": settings.get("address"),
        "port": settings.get("port"),
        "path": xhttp.get("path"),
        "host": xhttp.get("host"),
        "tls": bool(security and security != "none") or None,
        "servername": tls.get("serverName"),
        "skip-cert-verify": tls.get("allowInsecure"),
        "client-fingerprint": tls.get("fingerprint"),
        "alpn": tls.get("alpn"),
        "reality-opts": {
            "public-key": tls.get("publicKey"),
            "short-id": tls.get("shortId", ""),
        } if security == "reality" and tls.get("publicKey") else None,
    })


def make_mihomo_xhttp_opts(inbound: dict, user_agents: list[str] | None = None) -> dict:
    headers = deepcopy(inbound.get("headers") or {})
    headers.pop("Host", None)
    headers.pop("host", None)
    if inbound.get("random_user_agent") and user_agents:
        headers["User-Agent"] = choice(user_agents)

    opts = {
        "path": inbound.get("path") or "/",
        "host": _first(inbound.get("host")),
        "mode": inbound.get("mode") or "auto",
        "headers": headers or None,
        "reuse-settings": _reuse_settings(inbound.get("xmux")),
        "download-settings": _download_settings(inbound.get("downloadSettings")),
    }
    for source, target in _FIELD_MAP.items():
        opts[target] = inbound.get(source)
    return _clean(opts) or {}


class ClashMetaConfiguration(BaseClashMetaConfiguration):
    """Clash Meta serializer with Mihomo-compatible VLESS xHTTP support."""

    def add(self, remark: str, address: str, inbound: dict, settings: dict):
        if inbound.get("network") not in ("xhttp", "splithttp"):
            return super().add(remark, address, inbound, settings)
        if inbound.get("protocol") != "vless":
            return

        proxy_remark = self._remark_validation(remark)
        node = {
            "name": proxy_remark,
            "type": "vless",
            "server": address,
            "port": inbound["port"],
            "uuid": settings["id"],
            "network": "xhttp",
            "udp": True,
            "xhttp-opts": make_mihomo_xhttp_opts(inbound, self.user_agent_list),
        }

        flow = settings.get("flow")
        if flow and inbound.get("tls") in ("tls", "reality"):
            node["flow"] = flow
        if inbound.get("tls") in ("tls", "reality"):
            node["tls"] = True
            node["servername"] = _first(inbound.get("sni"))
            if inbound.get("alpn"):
                node["alpn"] = inbound["alpn"].split(",") if isinstance(inbound["alpn"], str) else inbound["alpn"]
            if inbound.get("ais"):
                node["skip-cert-verify"] = True
            if inbound.get("fp"):
                node["client-fingerprint"] = inbound["fp"]
        if inbound.get("tls") == "reality" and inbound.get("pbk"):
            node["reality-opts"] = {
                "public-key": inbound["pbk"],
                "short-id": inbound.get("sid", ""),
            }

        self.data["proxies"].append(_clean(node))
        self.proxy_remarks.append(proxy_remark)
