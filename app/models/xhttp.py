from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.proxy import ProxyHost

RangeValue = str | int


class XHTTPHostSettings(BaseModel):
    """Validated Xray v26 xHTTP settings accepted from the dashboard."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    mode: Literal["auto", "packet-up", "stream-up", "stream-one"] | None = None
    headers: dict[str, str] | None = None
    no_grpc_header: bool | None = Field(None, alias="noGRPCHeader")
    no_sse_header: bool | None = Field(None, alias="noSSEHeader")
    sc_max_each_post_bytes: RangeValue | None = Field(None, alias="scMaxEachPostBytes")
    sc_max_concurrent_posts: int | None = Field(None, alias="scMaxConcurrentPosts", ge=0)
    sc_min_posts_interval_ms: RangeValue | None = Field(None, alias="scMinPostsIntervalMs")
    sc_max_buffered_posts: int | None = Field(None, alias="scMaxBufferedPosts", ge=0)
    sc_stream_up_server_secs: int | None = Field(None, alias="scStreamUpServerSecs", ge=0)
    x_padding_bytes: RangeValue | None = Field(None, alias="xPaddingBytes")
    x_padding_obfs_mode: bool | None = Field(None, alias="xPaddingObfsMode")
    x_padding_key: str | None = Field(None, alias="xPaddingKey")
    x_padding_header: str | None = Field(None, alias="xPaddingHeader")
    x_padding_placement: str | None = Field(None, alias="xPaddingPlacement")
    x_padding_method: str | None = Field(None, alias="xPaddingMethod")
    uplink_http_method: str | None = Field(None, alias="uplinkHTTPMethod")
    session_id_placement: str | None = Field(None, alias="sessionIDPlacement")
    session_id_key: str | None = Field(None, alias="sessionIDKey")
    session_id_table: str | None = Field(None, alias="sessionIDTable")
    session_id_length: RangeValue | None = Field(None, alias="sessionIDLength")
    seq_placement: str | None = Field(None, alias="seqPlacement")
    seq_key: str | None = Field(None, alias="seqKey")
    uplink_data_placement: str | None = Field(None, alias="uplinkDataPlacement")
    uplink_data_key: str | None = Field(None, alias="uplinkDataKey")
    uplink_chunk_size: RangeValue | None = Field(None, alias="uplinkChunkSize")
    server_max_header_bytes: int | None = Field(None, alias="serverMaxHeaderBytes", ge=0)
    keep_alive_period: int | None = Field(None, alias="keepAlivePeriod", ge=0)
    xmux: dict[str, Any] | None = None
    download_settings: dict[str, Any] | None = Field(None, alias="downloadSettings")

    @field_validator(
        "sc_max_each_post_bytes",
        "sc_min_posts_interval_ms",
        "x_padding_bytes",
        "session_id_length",
        "uplink_chunk_size",
        mode="before",
    )
    @classmethod
    def validate_range(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, int):
            if value < 0:
                raise ValueError("range value cannot be negative")
            return value
        if not isinstance(value, str):
            raise ValueError("range value must be an integer or min-max string")
        parts = value.split("-")
        if len(parts) not in (1, 2) or not all(part.isdigit() for part in parts):
            raise ValueError("range value must be an integer or min-max string")
        numbers = [int(part) for part in parts]
        if len(numbers) == 2 and numbers[0] > numbers[1]:
            raise ValueError("range minimum cannot exceed maximum")
        return value

    @field_validator("uplink_http_method")
    @classmethod
    def validate_http_method(cls, value):
        if value is None:
            return None
        value = value.upper()
        if value not in {"POST", "PUT", "PATCH"}:
            raise ValueError("uplinkHTTPMethod must be POST, PUT, or PATCH")
        return value


class XHTTPInboundSettings(XHTTPHostSettings):
    """Complete runtime xHTTP inbound transport settings."""

    path: str | None = None
    host: str | list[str] | None = None


class XHTTPProxyHost(ProxyHost):
    """Proxy host with optional per-host xHTTP subscription overrides."""

    xhttp_settings: XHTTPHostSettings | None = Field(default=None, nullable=True)
