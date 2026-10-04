"""Bluesky public author-feed collector.

Uses the unauthenticated AppView at public.api.bsky.app. That host's robots.txt
allows public reads and asks callers to back off on HTTP 429. Reposts are not
the account's own words and are dropped. Quote text is not copied into the
author's evidence. Source text is data, not instructions.

This adapter is callable on its own. It is not wired into the recurring
belief runner.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "bluesky-0.1.0"
APPVIEW = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
ALLOWED_TYPES = ("application/json", "text/plain", "application/octet-stream")
MAX_LIMIT = 100


class BlueskyCollector:
    collector = "bluesky"
    platform = "bluesky"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(allowed_content_types=ALLOWED_TYPES, max_bytes=1_000_000)

    def collect_author_feed(
        self,
        *,
        source_identity: str,
        actor: str,
        observed_at: str,
        limit: int = 25,
        max_pages: int = 2,
        feed_filter: str = "posts_no_replies",
    ) -> list[SourceObservation]:
        _validate_actor(actor)
        if limit < 1 or limit > MAX_LIMIT:
            raise CollectorFailure("invalid_content", "limit out of range")
        if max_pages < 1 or max_pages > 10:
            raise CollectorFailure("invalid_content", "max_pages out of range")
        if feed_filter not in {"posts_no_replies", "posts_with_replies", "posts_and_author_threads", "posts_with_media"}:
            raise CollectorFailure("invalid_content", "unsupported feed filter")
        observations: list[SourceObservation] = []
        seen_urls: set[str] = set()
        cursor = ""
        seen_cursors: set[str] = set()
        for _page in range(max_pages):
            url = _feed_url(actor=actor, limit=limit, feed_filter=feed_filter, cursor=cursor)
            result = self.fetcher.get(url, headers={"Accept": "application/json"})
            batch, next_cursor = self.parse_feed(
                result.body,
                source_identity=source_identity,
                actor=actor,
                observed_at=observed_at,
            )
            for observation in batch:
                if observation.canonical_url in seen_urls:
                    continue
                seen_urls.add(observation.canonical_url)
                observations.append(observation)
            if not next_cursor or next_cursor in seen_cursors:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        return observations

    def parse_feed(
        self,
        payload: bytes,
        *,
        source_identity: str,
        actor: str,
        observed_at: str,
    ) -> tuple[list[SourceObservation], str | None]:
        _validate_actor(actor)
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CollectorFailure("invalid_content", f"malformed bluesky payload: {exc}") from exc
        if not isinstance(data, dict):
            raise CollectorFailure("invalid_content", "bluesky payload was not an object")
        if data.get("error"):
            message = str(data.get("message") or data.get("error"))
            if "RateLimit" in message or data.get("error") == "RateLimitExceeded":
                raise CollectorFailure("rate_limited", message)
            raise CollectorFailure("invalid_content", message)
        feed = data.get("feed")
        if not isinstance(feed, list):
            raise CollectorFailure("parser_unsupported", "bluesky payload has no feed list")
        observations: list[SourceObservation] = []
        for item in feed:
            if not isinstance(item, dict):
                continue
            parsed = _item_to_observation(item, source_identity=source_identity, actor=actor, observed_at=observed_at)
            if parsed is not None:
                observations.append(parsed)
        cursor = data.get("cursor")
        return observations, str(cursor) if cursor else None


def _validate_actor(actor: str) -> None:
    if not actor or any(char.isspace() for char in actor) or "/" in actor:
        raise CollectorFailure("invalid_content", "invalid bluesky actor")
    if actor.startswith("did:"):
        if not actor.startswith(("did:plc:", "did:web:")):
            raise CollectorFailure("invalid_content", "unsupported did method")
        return
    if "@" in actor or actor.startswith("."):
        raise CollectorFailure("invalid_content", "invalid bluesky handle")


def _feed_url(*, actor: str, limit: int, feed_filter: str, cursor: str) -> str:
    params = {"actor": actor, "filter": feed_filter, "limit": str(limit)}
    if cursor:
        params["cursor"] = cursor
    return f"{APPVIEW}?{urlencode(params)}"


def _item_to_observation(item: dict, *, source_identity: str, actor: str, observed_at: str) -> SourceObservation | None:
    reason = item.get("reason")
    if isinstance(reason, dict):
        reason_type = str(reason.get("$type") or "")
        if "Repost" in reason_type or reason_type.endswith("#reasonRepost"):
            return None
        if reason:
            return None
    post = item.get("post") or {}
    if not isinstance(post, dict):
        return None
    author = post.get("author") or {}
    handle = str(author.get("handle") or "")
    did = str(author.get("did") or "")
    if not _actor_matches(actor, handle=handle, did=did):
        return None
    record = post.get("record") or {}
    if not isinstance(record, dict):
        return None
    uri = str(post.get("uri") or "")
    rkey = uri.rsplit("/", 1)[-1] if uri else ""
    if not rkey or not handle:
        return None
    canonical = canonicalize_url(f"https://bsky.app/profile/{quote(handle)}/post/{quote(rkey)}")
    text, truncated = excerpt(str(record.get("text") or ""), 1500)
    langs = [str(code) for code in (record.get("langs") or []) if isinstance(code, str) and code]
    language = langs[0] if len(langs) == 1 else None
    embed = record.get("embed") or {}
    quote_uri = None
    if isinstance(embed, dict) and "embed.record" in str(embed.get("$type") or ""):
        quoted = embed.get("record") if isinstance(embed.get("record"), dict) else {}
        quote_uri = quoted.get("uri") or ((quoted.get("record") or {}) if isinstance(quoted.get("record"), dict) else {}).get("uri")
    is_reply = isinstance(record.get("reply"), dict)
    display = str(author.get("displayName") or handle)
    observation = SourceObservation(
        source_identity=source_identity,
        platform="bluesky",
        upstream_id=uri,
        canonical_url=canonical,
        observed_at=observed_at,
        published_at=_as_utc(record.get("createdAt")),
        author_candidates=[
            AuthorCandidate(name=display, role="author", attribution_method="bluesky_repo_author", confidence="medium")
        ],
        title=None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "actor": actor,
            "handle": handle,
            "did": did,
            "language": language,
            "languages": langs,
            "language_source": "record.langs" if langs else "absent",
            "translation": None,
            "is_reply": is_reply,
            "quote_uri": quote_uri,
            "quoted_text_stored": False,
            "truncated": truncated,
            "upstream_version": str(record.get("createdAt") or ""),
            "rights": "Public Bluesky post text via the AppView. Reposts are dropped. Quoted posts are not copied.",
        },
        collection_method="bluesky_api",
        collector="bluesky",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def _actor_matches(actor: str, *, handle: str, did: str) -> bool:
    if actor.startswith("did:"):
        return actor == did
    return actor.lower() == handle.lower()


def _as_utc(value) -> str | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
