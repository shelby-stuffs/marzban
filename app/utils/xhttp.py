from __future__ import annotations

from copy import deepcopy

XHTTP_FIELDS = (
    "headers",
    "mode",
    "noGRPCHeader",
    "noSSEHeader",
    "scMaxEachPostBytes",
    "scMaxConcurrentPosts",
    "scMinPostsIntervalMs",
    "scMaxBufferedPosts",
    "scStreamUpServerSecs",
    "xPaddingBytes",
    "xPaddingObfsMode",
    "xPaddingKey",
    "xPaddingHeader",
    "xPaddingPlacement",
    "xPaddingMethod",
    "uplinkHTTPMethod",
    "sessionIDPlacement",
    "sessionIDKey",
    "sessionIDTable",
    "sessionIDLength",
    "seqPlacement",
    "seqKey",
    "uplinkDataPlacement",
    "uplinkDataKey",
    "uplinkChunkSize",
    "serverMaxHeaderBytes",
    "keepAlivePeriod",
    "xmux",
    "downloadSettings",
)


def get_xhttp_settings(stream_settings: dict) -> dict | None:
    """Return canonical xHTTP settings from v26 or legacy SplitHTTP input."""
    method = stream_settings.get("method") or stream_settings.get("network")
    if method not in ("xhttp", "splithttp"):
        return None

    settings = stream_settings.get("xhttpSettings")
    if not isinstance(settings, dict):
        settings = stream_settings.get("splithttpSettings")
    return settings if isinstance(settings, dict) else {}


def enrich_xhttp_inbound_metadata(config) -> None:
    """Expose all Xray v26 xHTTP fields to subscription generators."""
    for inbound in config.get("inbounds", []):
        tag = inbound.get("tag")
        metadata = config.inbounds_by_tag.get(tag)
        if metadata is None:
            continue

        stream = inbound.get("streamSettings")
        if not isinstance(stream, dict):
            continue
        settings = get_xhttp_settings(stream)
        if settings is None:
            continue

        metadata["network"] = "xhttp"
        metadata["path"] = settings.get("path", metadata.get("path", ""))
        host = settings.get("host", metadata.get("host", []))
        metadata["host"] = [host] if isinstance(host, str) and host else host or []

        for field in XHTTP_FIELDS:
            if field in settings:
                metadata[field] = deepcopy(settings[field])


def xhttp_extra_from_metadata(metadata: dict) -> dict:
    """Build the compact `extra` object used by Xray-compatible share links."""
    extra = {}
    for field in XHTTP_FIELDS:
        if field == "mode":
            continue
        value = metadata.get(field)
        if value is None or value == "" or value == {} or value == []:
            continue
        extra[field] = deepcopy(value)
    return extra
