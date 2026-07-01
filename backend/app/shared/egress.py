"""Central egress guard against SSRF (SPEC-002).

A single policy governs where the platform is allowed to make outbound HTTP
requests. Every user-influenced fetch (the Investigador scraper, its robots.txt
lookups, and any other remote fetch) routes through :func:`assert_safe_url` /
:func:`is_egress_allowed` so a URL that resolves to a loopback, private,
link-local or otherwise non-public address is rejected **before** the request is
made.

Design notes
------------
- DNS is resolved and the **resolved IP(s)** are checked, not just the hostname
  (anti DNS-rebinding, AC2). All addresses a host resolves to must be public.
- An optional allowlist (``settings.SCRAPER_ALLOWED_DOMAINS``) restricts egress
  to specific domains and their subdomains; empty means "any public host".
- Resolutions are cached briefly to avoid re-resolving the same host on every
  page of a scrape without granting long-lived trust.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import time
import urllib.parse

logger = logging.getLogger(__name__)

# Short-lived cache: host -> (allowed, reason, expiry_monotonic). The TTL is
# intentionally small — it amortises resolution cost within a single scrape, it
# is not a long-term trust store (which would reopen the rebinding window).
_RESOLVE_TTL = 30.0
_resolve_cache: dict[str, tuple[bool, str, float]] = {}

# Simple counter of URLs blocked by the egress policy (observability, SPEC-002
# §7). A Prometheus metric is out of scope here (see task T5.2).
_blocked_total = 0


class EgressBlocked(Exception):
    """Raised when an outbound URL is denied by the egress policy."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"egress blocked for {url!r}: {reason}")


def blocked_total() -> int:
    """Number of URLs rejected by the egress policy since process start."""
    return _blocked_total


def reset_egress_cache() -> None:
    """Clear the resolution cache (used by tests to isolate cases)."""
    _resolve_cache.clear()


def _is_public_ip(ip: str) -> bool:
    """True only for globally routable unicast addresses."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    # Treat IPv4-mapped IPv6 (::ffff:127.0.0.1) as its embedded IPv4 address so
    # loopback/private ranges cannot be smuggled through an IPv6 literal.
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:
        addr = mapped
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _allowlist() -> list[str]:
    # Imported lazily to avoid any import cycle at module load.
    from app.core.config import settings

    return [d.strip().lower().rstrip(".") for d in (settings.SCRAPER_ALLOWED_DOMAINS or []) if d.strip()]


def _host_allowed(host: str, allowlist: list[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in allowlist)


def _block(url: str, reason: str) -> EgressBlocked:
    global _blocked_total
    _blocked_total += 1
    logger.warning("egress blocked: %s (%s)", url, reason)
    return EgressBlocked(url, reason)


def assert_safe_url(url: str) -> None:
    """Raise :class:`EgressBlocked` if *url* must not be fetched.

    Rejects non-http(s) schemes, hosts outside the configured allowlist, and any
    host that resolves to a non-public address.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise _block(url, f"scheme {parsed.scheme!r} not allowed")

    host = parsed.hostname
    if not host:
        raise _block(url, "missing host")

    allowlist = _allowlist()
    if allowlist and not _host_allowed(host, allowlist):
        raise _block(url, f"host {host!r} not in SCRAPER_ALLOWED_DOMAINS")

    now = time.monotonic()
    cached = _resolve_cache.get(host)
    if cached is not None and cached[2] > now:
        if cached[0]:
            return
        raise _block(url, cached[1])

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        reason = f"dns resolution failed: {exc}"
        _resolve_cache[host] = (False, reason, now + _RESOLVE_TTL)
        raise _block(url, reason) from exc

    for info in infos:
        ip = info[4][0]
        if not _is_public_ip(ip):
            reason = f"host {host!r} resolves to non-public address {ip}"
            _resolve_cache[host] = (False, reason, now + _RESOLVE_TTL)
            raise _block(url, reason)

    _resolve_cache[host] = (True, "", now + _RESOLVE_TTL)


def is_egress_allowed(url: str) -> bool:
    """Boolean wrapper over :func:`assert_safe_url` for call-sites that skip."""
    try:
        assert_safe_url(url)
        return True
    except EgressBlocked:
        return False
