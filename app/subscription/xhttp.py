from __future__ import annotations

import base64
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.utils.xhttp import xhttp_extra_from_metadata

from .v2ray import V2rayJsonConfig as BaseV2rayJsonConfig
from .v2ray import V2rayShareLink as BaseV2rayShareLink


def enrich_xhttp_share_link(link: str, inbound: dict) -> str:
    extra = xhttp_extra_from_metadata(inbound)
    mode = inbound.get("mode", "auto")
    if not extra and not mode:
        return link

    if link.startswith("vmess://"):
        encoded = link.removeprefix("vmess://")
        payload = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4)))
        current_extra = json.loads(payload.get("extra", "{}"))
        current_extra.update(extra)
        payload["type"] = mode
        if current_extra:
            payload["extra"] = json.dumps(current_extra, separators=(",", ":"))
        return "vmess://" + base64.b64encode(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).decode()

    if not link.startswith(("vless://", "trojan://")):
        return link

    parsed = urlsplit(link)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    try:
        current_extra = json.loads(query.get("extra", "{}"))
    except (TypeError, json.JSONDecodeError):
        current_extra = {}
    current_extra.update(extra)
    query["mode"] = mode
    if current_extra:
        query["extra"] = json.dumps(current_extra, separators=(",", ":"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


class V2rayShareLink(BaseV2rayShareLink):
    def add(self, remark: str, address: str, inbound: dict, settings: dict):
        before = len(self.links)
        super().add(remark, address, inbound, settings)
        if len(self.links) == before or inbound.get("network") not in ("xhttp", "splithttp"):
            return
        self.links[-1] = enrich_xhttp_share_link(self.links[-1], inbound)


class V2rayJsonConfig(BaseV2rayJsonConfig):
    def add(self, remark: str, address: str, inbound: dict, settings: dict):
        before = len(self.config)
        super().add(remark, address, inbound, settings)
        if len(self.config) == before or inbound.get("network") not in ("xhttp", "splithttp"):
            return

        extra = xhttp_extra_from_metadata(inbound)
        if not extra:
            return
        for outbound in self.config[-1].get("outbounds", []):
            stream = outbound.get("streamSettings")
            if not isinstance(stream, dict):
                continue
            xhttp_settings = stream.get("xhttpSettings")
            if isinstance(xhttp_settings, dict):
                xhttp_settings.update(extra)
                xhttp_settings["mode"] = inbound.get("mode", "auto")
                break
