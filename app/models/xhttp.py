from typing import Any

from pydantic import Field

from app.models.proxy import ProxyHost


class XHTTPProxyHost(ProxyHost):
    """Proxy host with optional per-host xHTTP subscription overrides."""

    xhttp_settings: dict[str, Any] | None = Field(default=None, nullable=True)
