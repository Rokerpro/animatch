import pytest

from app.core.client_ip import resolve_client_ip
from app.core.config import settings


@pytest.fixture
def trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", ["10.0.0.0/8", "127.0.0.1"])


def test_ignores_forwarded_header_without_trusted_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", [])
    assert resolve_client_ip("203.0.113.9", "1.2.3.4") == "203.0.113.9"


def test_ignores_forwarded_header_from_untrusted_peer(trusted: None) -> None:
    assert resolve_client_ip("203.0.113.9", "1.2.3.4") == "203.0.113.9"


def test_uses_client_from_trusted_proxy(trusted: None) -> None:
    assert resolve_client_ip("10.0.0.5", "198.51.100.7") == "198.51.100.7"


def test_spoofed_leading_entries_are_ignored(trusted: None) -> None:
    chain = "6.6.6.6, 198.51.100.7, 10.0.0.2"
    assert resolve_client_ip("10.0.0.5", chain) == "198.51.100.7"


def test_malformed_chain_falls_back_to_peer(trusted: None) -> None:
    assert resolve_client_ip("10.0.0.5", "not-an-ip") == "10.0.0.5"


def test_missing_peer_falls_back(trusted: None) -> None:
    assert resolve_client_ip(None, None) == "127.0.0.1"
