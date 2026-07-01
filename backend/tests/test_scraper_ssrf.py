"""SSRF egress guard tests (SPEC-002, task T2.1).

Covers AC1 (block loopback/private/link-local before the request), AC2 (validate
the *resolved* IP, not just the hostname), AC3 (no ``verify=False`` / TLS stays
on) and AC5 (representative cases). DNS is mocked, so no test touches the
network.
"""

import asyncio
import pathlib
import socket

import pytest

from app.core.config import settings
from app.modules.agents.adapters import scraper
from app.shared import egress
from app.shared.egress import EgressBlocked, assert_safe_url, is_egress_allowed


def _fake_getaddrinfo(ip: str):
    """Return a getaddrinfo stub resolving every host to *ip*."""
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, 0, 0, 0) if family == socket.AF_INET6 else (ip, 0)

    def _inner(host, port, *args, **kwargs):
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)]

    return _inner


@pytest.fixture(autouse=True)
def _reset_egress():
    egress.reset_egress_cache()
    yield
    egress.reset_egress_cache()


# ── AC1/AC2: non-public destinations are blocked ────────────────────────────────

BLOCKED_IPS = [
    "127.0.0.1",        # IPv4 loopback
    "10.0.0.5",         # private 10/8
    "172.16.3.4",       # private 172.16/12
    "192.168.1.10",     # private 192.168/16
    "169.254.169.254",  # link-local / cloud metadata
    "0.0.0.0",          # unspecified
    "::1",              # IPv6 loopback
    "fd00::1",          # IPv6 unique-local
    "fe80::1",          # IPv6 link-local
    "::ffff:127.0.0.1",  # IPv4-mapped loopback smuggled via IPv6
]


@pytest.mark.parametrize("ip", BLOCKED_IPS)
def test_assert_safe_url_blocks_non_public(monkeypatch, ip):
    monkeypatch.setattr(egress.socket, "getaddrinfo", _fake_getaddrinfo(ip))
    with pytest.raises(EgressBlocked):
        assert_safe_url("http://malicious.example/path")
    egress.reset_egress_cache()
    assert is_egress_allowed("http://malicious.example/path") is False


def test_public_host_is_allowed(monkeypatch):
    monkeypatch.setattr(egress.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    assert_safe_url("https://example.com/article")  # does not raise
    assert is_egress_allowed("https://example.com/article") is True


def test_dns_failure_is_blocked(monkeypatch):
    def _boom(*args, **kwargs):
        raise socket.gaierror("name resolution failed")

    monkeypatch.setattr(egress.socket, "getaddrinfo", _boom)
    with pytest.raises(EgressBlocked):
        assert_safe_url("https://does-not-resolve.example/")


@pytest.mark.parametrize("url", ["ftp://example.com/x", "file:///etc/passwd", "gopher://example.com"])
def test_non_http_scheme_is_blocked(url):
    with pytest.raises(EgressBlocked):
        assert_safe_url(url)


def test_missing_host_is_blocked():
    with pytest.raises(EgressBlocked):
        assert_safe_url("http:///no-host")


# ── AC4: configurable allowlist ─────────────────────────────────────────────────

def test_allowlist_denies_unlisted_public_host(monkeypatch):
    monkeypatch.setattr(egress.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))
    monkeypatch.setattr(settings, "SCRAPER_ALLOWED_DOMAINS", ["arxiv.org"])
    with pytest.raises(EgressBlocked):
        assert_safe_url("https://evil.example/")
    egress.reset_egress_cache()
    assert_safe_url("https://export.arxiv.org/api/query")  # subdomain allowed


# ── AC1 integration: the scraper refuses internal targets without network ───────

@pytest.mark.parametrize(
    "url,ip",
    [
        ("http://127.0.0.1:6333/collections", "127.0.0.1"),
        ("http://169.254.169.254/latest/meta-data/", "169.254.169.254"),
    ],
)
def test_fetch_page_refuses_internal_targets(monkeypatch, url, ip):
    monkeypatch.setattr(egress.socket, "getaddrinfo", _fake_getaddrinfo(ip))

    def _fail_fetch(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("scraper attempted a network fetch to a blocked URL")

    monkeypatch.setattr(scraper, "_fetch_with_requests", _fail_fetch)

    result = asyncio.run(scraper._fetch_page(url, use_playwright_fallback=False))
    assert result is None


# ── AC3: TLS verification is never disabled ─────────────────────────────────────

@pytest.mark.parametrize(
    "module",
    [scraper, __import__("app.modules.agents.adapters.tools", fromlist=["x"])],
)
def test_no_verify_false_in_outbound_modules(module):
    src = pathlib.Path(module.__file__).read_text(encoding="utf-8")
    assert "verify=False" not in src
