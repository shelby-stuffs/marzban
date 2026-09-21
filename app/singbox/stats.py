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

    def query_stats(
        self, pattern: str, reset: bool = False, timeout: int | None = None
    ) -> typing.Iterable[StatResponse]:
        try:
            query = self._channel.unary_unary(
                "/v2ray.app.stats.command.StatsService/QueryStats",
                request_serializer=command_pb2.QueryStatsRequest.SerializeToString,
                response_deserializer=command_pb2.QueryStatsResponse.FromString,
            )
            response = query(
                command_pb2.QueryStatsRequest(pattern=pattern, reset=reset),
                timeout=timeout,
            )
        except grpc.RpcError as exc:
            raise RelatedError(exc) from exc

        for stat in response.stat:
            try:
                stat_type, name, _, link = stat.name.split(">>>")
            except ValueError:
                continue
            yield StatResponse(name, stat_type, link, stat.value)