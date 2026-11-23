"""Client IP resolution that only trusts forwarded headers from known proxies."""

import ipaddress
import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)

_FALLBACK_IP = "127.0.0.1"

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


@lru_cache(maxsize=8)
def _parse_networks(entries: tuple[str, ...]) -> tuple[IPNetwork, ...]:
    networks: list[IPNetwork] = []
    for entry in entries:
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Ignoring invalid TRUSTED_PROXIES entry: %r", entry)
    return tuple(networks)


def _is_trusted(ip: str, networks: tuple[IPNetwork, ...]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def resolve_client_ip(peer: str | None, forwarded_for: str | None) -> str:
    """Return the real client IP.

    X-Forwarded-For is only consulted when the direct peer is a trusted proxy.
    The chain is walked right to left and the first address that is not itself a
    trusted proxy is the client, so entries a caller prepends are ignored.
    """
    peer_ip = peer or _FALLBACK_IP
    networks = _parse_networks(tuple(settings.TRUSTED_PROXIES))
    if not networks or not forwarded_for or not _is_trusted(peer_ip, networks):
        return peer_ip

    hops = [h.strip() for h in forwarded_for.split(",") if h.strip()]
    for hop in reversed(hops):
        try:
            ipaddress.ip_address(hop)
        except ValueError:
            return peer_ip
        if not _is_trusted(hop, networks):
            return hop
    return hops[0] if hops else peer_ip
