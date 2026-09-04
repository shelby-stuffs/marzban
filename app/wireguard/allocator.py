from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_interface, ip_network
from typing import Iterable

IpNetwork = IPv4Network | IPv6Network
IpAddress = IPv4Address | IPv6Address


@dataclass(frozen=True)
class WireGuardNamespace:
    subnet: IpNetwork
    reserved: frozenset[int]


def build_namespaces(interface_addresses: Iterable[str]) -> list[WireGuardNamespace]:
    """Build unique allocation pools and reserve network/server/broadcast addresses."""
    by_subnet: dict[str, tuple[IpNetwork, set[int]]] = {}

    for cidr in interface_addresses:
        interface = ip_interface(str(cidr).strip())
        subnet = interface.network
        key = str(subnet)
        if key not in by_subnet:
            reserved = {0, subnet.num_addresses - 1}
            by_subnet[key] = (subnet, reserved)
        by_subnet[key][1].add(int(interface.ip) - int(subnet.network_address))

    ordered = sorted(by_subnet.values(), key=lambda item: (item[0].version, int(item[0].network_address), item[0].prefixlen))
    return [WireGuardNamespace(subnet=subnet, reserved=frozenset(reserved)) for subnet, reserved in ordered]


def _host_identity(value: str) -> tuple[int, int] | None:
    try:
        network = ip_network(str(value).strip(), strict=False)
    except ValueError:
        return None
    return network.version, int(network.network_address)


def _render_peer_ip(subnet: IpNetwork, offset: int) -> str:
    address = ip_address(int(subnet.network_address) + offset)
    return f"{address}/{'32' if subnet.version == 4 else '128'}"


def allocate_peer_ips(
    interface_addresses: Iterable[str],
    *,
    occupied_peer_ips: Iterable[str] = (),
    current_peer_ips: Iterable[str] = (),
) -> list[str]:
    """Allocate one stable peer address from every interface subnet.

    `occupied_peer_ips` must contain addresses owned by other peers; callers
    should exclude the current user's addresses before invoking this function.
    """
    namespaces = build_namespaces(interface_addresses)
    occupied = {identity for value in occupied_peer_ips if (identity := _host_identity(value)) is not None}
    current = [identity for value in current_peer_ips if (identity := _host_identity(value)) is not None]

    allocations = []
    for namespace in namespaces:
        subnet = namespace.subnet
        base = int(subnet.network_address)
        last_offset = subnet.num_addresses - 1

        selected_offset = None
        for version, host_int in current:
            if version != subnet.version:
                continue
            address = ip_address(host_int)
            offset = host_int - base
            if address in subnet and 0 < offset < last_offset and offset not in namespace.reserved:
                if (version, host_int) not in occupied:
                    selected_offset = offset
                    break

        if selected_offset is None:
            offset = 1
            while offset < last_offset:
                identity = (subnet.version, base + offset)
                if offset not in namespace.reserved and identity not in occupied:
                    selected_offset = offset
                    break
                offset += 1

        if selected_offset is None:
            raise ValueError(f"WireGuard subnet {subnet} has no free addresses")

        peer_ip = _render_peer_ip(subnet, selected_offset)
        allocations.append(peer_ip)
        occupied.add(_host_identity(peer_ip))

    return allocations
