"""Outbound fetches reject local and metadata targets before any socket connect."""

from __future__ import annotations

import pytest

from pdoom_pipeline.errors import UNSAFE_URL, CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher

BLOCKED_URLS = (
    "http://127.0.0.1/",
    "http://localhost/",
    "http://169.254.169.254/",
    "http://10.0.0.1/",
    "http://192.168.0.1/",
    "http://172.16.0.1/",
)

PUBLIC_URL = "https://example.com/records/1"
PUBLIC_IP = "93.184.216.34"


def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> list:
    attempts: list = []

    def create_connection(address, *args, **kwargs):
        attempts.append(address)
        raise AssertionError(f"socket connect attempted: {address}")

    def getaddrinfo(*args, **kwargs):
        raise AssertionError(f"dns lookup attempted: {args!r}")

    monkeypatch.setattr("pdoom_pipeline.fetch.socket.create_connection", create_connection)
    monkeypatch.setattr("pdoom_pipeline.fetch.socket.getaddrinfo", getaddrinfo)
    return attempts


def _resolver(host: str, port: int) -> list[str]:
    if host == "example.com":
        return [PUBLIC_IP]
    raise AssertionError(f"resolver called for {host}")


@pytest.mark.parametrize("url", BLOCKED_URLS)
def test_blocked_destination_rejected_before_connect(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    attempts = _forbid_network(monkeypatch)
    fetcher = SafeFetcher(resolver=_resolver, max_attempts=3, sleep=lambda _seconds: None)
    with pytest.raises(CollectorFailure) as caught:
        fetcher.get(url)
    assert caught.value.error_class == UNSAFE_URL
    assert caught.value.retryable is False
    assert attempts == []


class _RedirectResponse:
    def __init__(self, location: str) -> None:
        self.status = 302
        self.headers = {"location": location}

    def getheader(self, name: str, default=None):
        return self.headers.get(name.lower(), default)

    def read(self, _amount: int = -1) -> bytes:
        return b""


@pytest.mark.parametrize("target", BLOCKED_URLS)
def test_redirect_to_blocked_destination_rejected_before_connect(
    monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    attempts = _forbid_network(monkeypatch)
    opened: list[tuple[str, str]] = []

    class _Connection:
        def __init__(self, host: str, port: int, ip: str, timeout: float) -> None:
            opened.append((host, ip))

        def request(self, method: str, path: str, headers=None) -> None:
            return None

        def getresponse(self) -> _RedirectResponse:
            return _RedirectResponse(target)

        def close(self) -> None:
            return None

    monkeypatch.setattr("pdoom_pipeline.fetch._PinnedHTTPConnection", _Connection)
    monkeypatch.setattr("pdoom_pipeline.fetch._PinnedHTTPSConnection", _Connection)

    fetcher = SafeFetcher(resolver=_resolver, max_attempts=1, sleep=lambda _seconds: None)
    with pytest.raises(CollectorFailure) as caught:
        fetcher.get(PUBLIC_URL)
    assert caught.value.error_class == UNSAFE_URL
    assert caught.value.retryable is False
    assert target.split("/")[2] in str(caught.value)
    assert attempts == []
    assert opened == [("example.com", PUBLIC_IP)]


def test_public_https_url_shape_classified_without_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = _forbid_network(monkeypatch)
    fetcher = SafeFetcher(resolver=_resolver, max_attempts=1)
    assert fetcher.validate_destination(PUBLIC_URL) == [PUBLIC_IP]
    assert attempts == []
