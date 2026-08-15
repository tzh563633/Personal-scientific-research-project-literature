from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from ..config import settings


def validate_public_url(value: str, label: str = "External source URL") -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{label} must use http or https without embedded credentials")
    hostname = parsed.hostname.lower().rstrip(".")
    allowed_hosts = {
        item.strip().lower().rstrip(".")
        for item in settings.outbound_allowed_hosts.split(",")
        if item.strip()
    }
    addresses = socket.getaddrinfo(
        hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
    )
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if hostname in allowed_hosts:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError(f"{label} resolves to a private or reserved address")
