"""V2Ray Stats API client for sing-box.

sing-box exposes the V2Ray-compatible protobuf messages under the
``v2ray.app.stats.command`` service namespace. Xray uses the same wire format
but registers it under ``xray.app.stats.command``, so the shared xray_api
client cannot be used directly.
"""
from __future__ import annotations

import typing

import grpc

from xray_api import XRay
from xray_api.exceptions import RelatedError
from xray_api.proto.app.stats.command import command_pb2
from xray_api.stats import StatResponse


class SingBoxStats(XRay):
    """XRay-compatible client using sing-box's gRPC service namespace."""

    SERVICE_NAMES = (
        # sing-box's generated protobuf package uses this service name.
        "/experimental.v2rayapi.StatsService/QueryStats",
        # Some sing-box/extended builds override the descriptor name to the
        # canonical V2Ray service name while keeping the same wire format.
        "/v2ray.core.app.stats.command.StatsService/QueryStats",
        "/v2ray.app.stats.command.StatsService/QueryStats",
        # Some sing-box builds register the compatibility service under the
        # Xray namespace even though the protobuf contract is the same.
        "/xray.app.stats.command.StatsService/QueryStats",
    )

    def query_stats(
        self, pattern: str, reset: bool = False, timeout: int | None = None
    ) -> typing.Iterable[StatResponse]:
        request = command_pb2.QueryStatsRequest(pattern=pattern, reset=reset)
        last_error = None
        response = None
        for service_name in self.SERVICE_NAMES:
            try:
                query = self._channel.unary_unary(
                    service_name,
                    request_serializer=command_pb2.QueryStatsRequest.SerializeToString,
                    response_deserializer=command_pb2.QueryStatsResponse.FromString,
                )
                response = query(request, timeout=timeout)
                break
            except grpc.RpcError as exc:
                last_error = exc
                # UNIMPLEMENTED is the normal signal when a sing-box build
                # chose the other compatibility namespace. Do not retry
                # connection/authentication failures against another path.
                details = (exc.details() or "").lower()
                namespace_missing = "unknown service" in details or "unimplemented" in details
                if exc.code() != grpc.StatusCode.UNIMPLEMENTED and not namespace_missing:
                    raise RelatedError(exc) from exc

        if response is None:
            raise RelatedError(last_error) from last_error

        for stat in response.stat:
            try:
                stat_type, name, _, link = stat.name.split(">>>")
            except ValueError:
                continue
            yield StatResponse(name, stat_type, link, stat.value)