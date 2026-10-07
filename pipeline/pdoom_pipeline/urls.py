"""Deterministic canonical URLs and outbound target checks."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "si",
    "ref_src",
    "feature",
}

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.internal",
}

# Cloud metadata addresses and names that sometimes resolve publicly in tests.
BLOCKED_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("fd00:ec2::254"),
}

_ARXIV_NEW = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?", re.I)
_ARXIV_OLD = re.compile(r"arxiv\.org/(?:abs|pdf)/([a-z\-]+/[0-9]{7})(?:v\d+)?", re.I)
_YOUTUBE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{6,})",
    re.I,
)
_OPENALEX_AUTHOR = re.compile(r"openalex\.org/(A\d+)", re.I)
_OPENALEX_WORK = re.compile(r"openalex\.org/(W\d+)", re.I)
_DOI = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)


def canonicalize_url(url: str) -> str:
    """Return a stable URL for deduplication. Fragments and tracking params are removed."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("empty url")
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"not an http(s) url: {url}")
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    if not host:
        raise ValueError(f"missing host: {url}")
    port = parsed.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query_pairs.sort()
    canonical = urlunparse((scheme, netloc, path, "", urlencode(query_pairs), ""))
    return _platform_canonical(canonical)


def _platform_canonical(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"youtube.com", "www.youtube.com"}:
        values = [value for key, value in parse_qsl(parsed.query) if key == "v"]
        video = values[0] if parsed.path == "/watch" and len(values) == 1 else None
        embedded = re.fullmatch(r"/embed/([A-Za-z0-9_-]{6,})", parsed.path)
        video = embedded.group(1) if embedded else video
        if video and re.fullmatch(r"[A-Za-z0-9_-]{6,}", video):
            return f"https://www.youtube.com/watch?v={video}"
    elif host == "youtu.be":
        video = parsed.path.lstrip("/")
        if re.fullmatch(r"[A-Za-z0-9_-]{6,}", video):
            return f"https://www.youtube.com/watch?v={video}"
    if host in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
        target = "arxiv.org" + parsed.path
        arxiv = _ARXIV_NEW.match(target) or _ARXIV_OLD.match(target)
        if arxiv:
            return f"https://arxiv.org/abs/{arxiv.group(1)}"
    if host == "openalex.org":
        author = _OPENALEX_AUTHOR.fullmatch("openalex.org" + parsed.path)
        work = _OPENALEX_WORK.fullmatch("openalex.org" + parsed.path)
        if author or work:
            return f"https://openalex.org/{(author or work).group(1).upper()}"
    if host in {"doi.org", "dx.doi.org", "www.doi.org"}:
        doi = _DOI.fullmatch(parsed.path.lstrip("/"))
        if doi:
            return f"https://doi.org/{doi.group(1)}"
    return url


def arxiv_id_from_url(url: str) -> str | None:
    match = _ARXIV_NEW.search(url) or _ARXIV_OLD.search(url)
    return match.group(1) if match else None


def ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip in BLOCKED_IPS:
        return True
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def hostname_is_blocked(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    if host in BLOCKED_HOSTNAMES:
        return True
    if host.endswith(".localhost") or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip_is_blocked(ip)
