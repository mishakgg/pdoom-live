"""Bounded, SSRF-resistant HTTP fetch for public collectors.

Fetched bytes are data. They are never executed or treated as instructions.
Production retries sleep, honor Retry-After, and stop at a deadline.
"""

from __future__ import annotations

import http.client
import socket
import ssl
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable
from urllib.parse import urljoin, urlparse

from pdoom_pipeline.errors import (
    CONTENT_TOO_LARGE,
    CollectorFailure,
    UNSAFE_URL,
    classify_http_status,
)
from pdoom_pipeline.urls import hostname_is_blocked, ip_is_blocked

USER_AGENT = "pdoom.live-collector/0.1 (+https://github.com/mishakgg/pdoom-live; mailto:collector@pdoom.live)"

Resolver = Callable[[str, int], list[str]]
SleepFn = Callable[[float], None]


@dataclass
class FetchResult:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    requested_urls: list[str] = field(default_factory=list)
    not_modified: bool = False
    attempts: int = 1


def default_resolver(hostname: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise CollectorFailure("temporarily_unavailable", f"dns failure for {hostname}: {exc}") from exc
    ips: list[str] = []
    for info in infos:
        addr = info[4][0]
        if addr not in ips:
            ips.append(addr)
    return ips


def _decode_body(raw: bytes, encoding: str, max_bytes: int) -> bytes:
    enc = (encoding or "").lower().strip()
    if enc in {"", "identity"}:
        if len(raw) > max_bytes:
            raise CollectorFailure(CONTENT_TOO_LARGE, "response exceeds max_bytes")
        return raw
    if enc not in {"gzip", "deflate"}:
        raise CollectorFailure("parser_unsupported", f"unsupported content-encoding: {encoding}")
    wbits = 16 + zlib.MAX_WBITS if enc == "gzip" else zlib.MAX_WBITS
    try:
        decompressor = zlib.decompressobj(wbits)
        out = decompressor.decompress(raw, max_bytes + 1)
    except zlib.error as exc:
        raise CollectorFailure("invalid_content", f"decompression failed: {exc}") from exc
    if len(out) > max_bytes or decompressor.unconsumed_tail:
        raise CollectorFailure(CONTENT_TOO_LARGE, "decompressed response exceeds max_bytes")
    rest = decompressor.flush()
    if rest:
        if len(out) + len(rest) > max_bytes:
            raise CollectorFailure(CONTENT_TOO_LARGE, "decompressed response exceeds max_bytes")
        out += rest
    return out


def _header_map(headers: http.client.HTTPMessage | dict) -> dict[str, str]:
    if isinstance(headers, dict):
        return {str(k).lower(): str(v) for k, v in headers.items()}
    return {k.lower(): v for k, v in headers.items()}


class SafeFetcher:
    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        transport: Callable[[str, dict[str, str]], FetchResult] | None = None,
        sleep: SleepFn | None = None,
        timeout: float = 10.0,
        max_bytes: int = 1_000_000,
        max_redirects: int = 5,
        max_attempts: int = 3,
        user_agent: str = USER_AGENT,
        allowed_content_types: tuple[str, ...] | None = None,
    ):
        self.resolver = resolver or default_resolver
        self.transport = transport
        self.sleep = sleep or time.sleep
        self.clock = time.monotonic
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.max_attempts = max_attempts
        self.max_retry_after = 60.0
        self.host_interval = 0.0
        self.deadline_at: float | None = None
        self.cancelled: Callable[[], bool] | None = None
        self.header_provider: Callable[[str], dict[str, str]] | None = None
        self.cache_get: Callable[[str], bytes | None] | None = None
        self.cache_put: Callable[[str, bytes, dict[str, str]], None] | None = None
        self.url_policy: Callable[[str], None] | None = None
        self.user_agent = user_agent
        self.allowed_content_types = allowed_content_types
        self._host_next: dict[str, float] = {}
        self.last: FetchResult | None = None

    def validate_destination(self, url: str) -> list[str]:
        if self.url_policy is not None:
            self.url_policy(url)
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise CollectorFailure(UNSAFE_URL, f"unsupported scheme: {parsed.scheme}")
        if parsed.username or parsed.password:
            raise CollectorFailure(UNSAFE_URL, "urls with userinfo are rejected")
        host = parsed.hostname
        if not host or hostname_is_blocked(host):
            raise CollectorFailure(UNSAFE_URL, f"blocked host: {host}")
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        if self.transport is not None:
            return []
        ips = self.resolver(host, port)
        if not ips:
            raise CollectorFailure("temporarily_unavailable", f"no addresses for {host}")
        for ip_text in ips:
            try:
                ip = ipaddress_of(ip_text)
            except ValueError as exc:
                raise CollectorFailure(UNSAFE_URL, f"unparseable address for {host}") from exc
            if ip_is_blocked(ip):
                raise CollectorFailure(UNSAFE_URL, f"blocked address for {host}: {ip}")
        return ips

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResult:
        request_headers = dict(headers or {})
        conditional = True
        last_error: CollectorFailure | None = None
        attempt = 1
        while attempt <= self.max_attempts:
            self._before_attempt(url)
            try:
                result = self._get_once(url, request_headers, conditional=conditional)
                result.attempts = attempt
                if result.status == 304:
                    result.not_modified = True
                    cached = self.cache_get(url) if self.cache_get else None
                    if cached is not None:
                        result.body = cached
                        self.last = result
                        return result
                    if conditional:
                        conditional = False
                        continue
                    self.last = result
                    raise CollectorFailure("invalid_content", "304 has no validated retained body")
                if self.cache_put is not None and result.body:
                    self.cache_put(url, result.body, result.headers)
                self.last = result
                return result
            except CollectorFailure as exc:
                last_error = exc
                if not exc.retryable or attempt >= self.max_attempts:
                    raise
                delay = self._retry_delay(attempt, exc)
                self._sleep_bounded(delay)
                attempt += 1
        assert last_error is not None
        raise last_error

    def _before_attempt(self, url: str) -> None:
        if self.cancelled and self.cancelled():
            raise CollectorFailure("temporarily_unavailable", "fetch cancelled", retryable=False)
        self._check_deadline(0)
        self._pace(url)

    def _pace(self, url: str) -> None:
        if self.host_interval <= 0:
            return
        host = (urlparse(url).hostname or "").lower()
        now = self.clock()
        ready = self._host_next.get(host, now)
        if ready > now:
            self._sleep_bounded(ready - now)
        self._host_next[host] = self.clock() + self.host_interval

    def _retry_delay(self, attempt: int, exc: CollectorFailure) -> float:
        backoff = min(2 ** (attempt - 1), 8)
        if exc.retry_after is None:
            return backoff
        hinted = min(max(exc.retry_after, 0.0), self.max_retry_after)
        if exc.retry_after == 0:
            return 0.0
        return max(backoff, hinted)

    def _sleep_bounded(self, delay: float) -> None:
        if delay < 0:
            delay = 0
        self._check_deadline(delay)
        if delay:
            self.sleep(delay)

    def _check_deadline(self, upcoming_sleep: float) -> None:
        if self.deadline_at is None:
            return
        if self.clock() + upcoming_sleep > self.deadline_at:
            raise CollectorFailure("temporarily_unavailable", "fetch deadline exceeded", retryable=False)

    def _get_once(self, url: str, headers: dict[str, str], *, conditional: bool = True) -> FetchResult:
        requested: list[str] = []
        current = url
        for _hop in range(self.max_redirects + 1):
            self.validate_destination(current)
            requested.append(current)
            provided = self.header_provider(current) if conditional and self.header_provider else {}
            merged = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate", **provided, **headers}
            if not conditional:
                merged = {
                    key: value
                    for key, value in merged.items()
                    if key.lower() not in {"if-none-match", "if-modified-since"}
                }
            # HTTP header names are case-insensitive. Collectors and tests
            # match the lowercase form used by the response header map.
            request_headers = {key.lower(): value for key, value in merged.items()}
            if self.transport is not None:
                result = self.transport(current, request_headers)
                self.validate_destination(result.url)
                result.requested_urls = list(requested)
                self._check_status_and_type(result)
                if result.status != 304 and len(result.body) > self.max_bytes:
                    raise CollectorFailure(CONTENT_TOO_LARGE, "response exceeds max_bytes")
                return result
            result = self._request_pinned(current, request_headers)
            result.requested_urls = list(requested)
            if result.status in {301, 302, 303, 307, 308}:
                location = result.headers.get("location")
                if not location:
                    raise CollectorFailure("invalid_content", "redirect without location")
                current = urljoin(current, location)
                continue
            self._check_status_and_type(result)
            return result
        raise CollectorFailure("invalid_content", "too many redirects")

    def _check_status_and_type(self, result: FetchResult) -> None:
        if result.status == 304:
            return
        if result.status >= 400:
            error_class = classify_http_status(result.status)
            raise CollectorFailure(
                error_class,
                f"http {result.status} for {result.url}",
                retry_after=_retry_after_seconds(result.headers),
            )
        if self.allowed_content_types:
            ctype = result.headers.get("content-type", "").split(";")[0].strip().lower()
            allowed = {item.lower() for item in self.allowed_content_types}
            if ctype not in allowed:
                raise CollectorFailure("parser_unsupported", f"content-type {ctype or 'missing'} is not allowed")

    def _request_pinned(self, url: str, headers: dict[str, str]) -> FetchResult:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        ips = self.validate_destination(url)
        ip = ips[0]
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        try:
            if parsed.scheme == "https":
                connection = _PinnedHTTPSConnection(host, port, ip, timeout=self.timeout)
            else:
                connection = _PinnedHTTPConnection(host, port, ip, timeout=self.timeout)
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            length = response.getheader("Content-Length")
            if length and length.isdigit() and int(length) > self.max_bytes:
                connection.close()
                raise CollectorFailure(CONTENT_TOO_LARGE, "content-length exceeds max_bytes")
            raw = _read_limited(response, self.max_bytes)
            encoding = response.getheader("Content-Encoding") or ""
            body = _decode_body(raw, encoding, self.max_bytes)
            status = response.status
            header_map = _header_map(response.headers)
            final_url = url
            connection.close()
        except CollectorFailure:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise CollectorFailure("temporarily_unavailable", f"timeout fetching {url}") from exc
        except OSError as exc:
            raise CollectorFailure("temporarily_unavailable", f"network error fetching {url}: {exc}") from exc
        return FetchResult(url=final_url, status=status, headers=header_map, body=body)


def _retry_after_seconds(headers: dict[str, str]) -> float | None:
    raw = headers.get("retry-after")
    if raw is None or not str(raw).strip():
        return None
    text = str(raw).strip()
    if text.isdigit():
        return float(text)
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())


def _read_limited(response: http.client.HTTPResponse, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining > 0:
        block = response.read(min(65536, remaining))
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
    data = b"".join(chunks)
    if len(data) > max_bytes:
        raise CollectorFailure(CONTENT_TOO_LARGE, "response exceeds max_bytes")
    return data


def ipaddress_of(value: str):
    import ipaddress

    return ipaddress.ip_address(value)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float):
        super().__init__(host, port, timeout=timeout)
        self._pinned_ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float):
        context = ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=context)
        self._pinned_ip = ip

    def connect(self) -> None:
        raw = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
