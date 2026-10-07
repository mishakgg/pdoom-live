"""Curated collection admission and outbound URL identity, never upstream hints."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.urls import hostname_is_blocked


def public_url(url: str):
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 80, 443}
            or hostname_is_blocked(parsed.hostname)
            or "\\" in url
            or any(ord(char) < 33 for char in url)
        ):
            raise ValueError("untrusted destination")
        return parsed
    except (TypeError, ValueError) as exc:
        raise CollectorFailure("unsafe_url", "invalid public source URL") from exc


def origin(url: str) -> str:
    parsed = public_url(url)
    port = parsed.port
    suffix = f":{port}" if port and port != (443 if parsed.scheme == "https" else 80) else ""
    return f"{parsed.scheme}://{parsed.hostname.lower()}{suffix}"


def url_scope(row: dict, fetch_url: str):
    """Default to the admitted origin; extra origins must be curator supplied."""
    allowed = {origin(fetch_url)}
    extra = row.get("allowed_fetch_origins") or []
    if not isinstance(extra, list):
        raise CollectorFailure("blocked_by_policy", "allowed_fetch_origins must be a list")
    for value in extra:
        parsed = public_url(value)
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise CollectorFailure("blocked_by_policy", "allowed_fetch_origins requires origins")
        allowed.add(origin(value))

    def check(url: str) -> None:
        if origin(url) not in allowed:
            raise CollectorFailure("blocked_by_policy", "destination is outside admitted source origins")

    return check


def github_username(row: dict) -> str:
    parsed = public_url(row["canonical_url"])
    username = parsed.path.strip("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.query or parsed.fragment
        or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username)
        or "--" in username
        or (row.get("external_id") and row["external_id"].casefold() != username.casefold())
    ):
        raise CollectorFailure("blocked_by_policy", "GitHub source must match its admitted profile identity")
    return username


def openalex_author(row: dict) -> str:
    parsed = public_url(row["canonical_url"])
    query = parse_qs(parsed.query, keep_blank_values=True)
    filters = query.get("filter", [])
    match = re.fullmatch(r"authorships\.author\.id:(A[0-9]+)", filters[0]) if len(filters) == 1 else None
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.openalex.org"
        or parsed.path != "/works" or parsed.fragment
        or set(query) != {"filter"} or match is None
    ):
        raise CollectorFailure("blocked_by_policy", "OpenAlex source requires one exact author filter")
    author = match.group(1)
    if row.get("external_id") and row["external_id"] != author:
        raise CollectorFailure("blocked_by_policy", "OpenAlex author filter disagrees with admitted identity")
    return author
