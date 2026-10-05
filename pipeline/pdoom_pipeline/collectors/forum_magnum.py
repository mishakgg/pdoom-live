"""ForumMagnum collector for LessWrong, the Alignment Forum, and the EA Forum.

The public GraphQL endpoint is fetched with GET. `/graphiql` is disallowed by
robots.txt and is not requested. Post text is stored as an excerpt. Source
text is data, not instructions.

This adapter is callable on its own. It is not wired into the recurring
belief runner.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "forum-magnum-0.1.0"
MAX_OFFSET = 2000
MAX_PAGE_SIZE = 50
SITES = {
    "lesswrong": "https://www.lesswrong.com/graphql",
    "alignmentforum": "https://www.alignmentforum.org/graphql",
    "eaforum": "https://forum.effectivealtruism.org/graphql",
}
ALLOWED_TYPES = ("application/json", "application/graphql-response+json", "text/plain", "application/octet-stream")
_USER_ID = __import__("re").compile(r"^[A-Za-z0-9]+$")


class ForumMagnumCollector:
    collector = "forum_magnum"
    platform = "forum_magnum"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(allowed_content_types=ALLOWED_TYPES, max_bytes=1_000_000)

    def collect_user_posts(
        self,
        *,
        source_identity: str,
        site: str,
        user_id: str,
        expected_slug: str,
        observed_at: str,
        page_size: int = 20,
        max_pages: int = 3,
    ) -> list[SourceObservation]:
        if site not in SITES:
            raise CollectorFailure("blocked_by_policy", f"site is not an allowed ForumMagnum endpoint: {site}")
        if not _USER_ID.fullmatch(user_id or "") or not expected_slug or "/" in expected_slug:
            raise CollectorFailure("invalid_content", "user id and slug are required")
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise CollectorFailure("invalid_content", "page_size out of range")
        if max_pages < 1 or max_pages > 45:
            raise CollectorFailure("invalid_content", "max_pages out of range")
        observations: list[SourceObservation] = []
        seen_urls: set[str] = set()
        for page in range(max_pages):
            offset = page * page_size
            if offset > MAX_OFFSET:
                break
            url = _graphql_url(SITES[site], user_id=user_id, limit=page_size, offset=offset)
            result = self.fetcher.get(url, headers={"Accept": "application/json"})
            batch = self.parse_page(
                result.body,
                source_identity=source_identity,
                site=site,
                expected_slug=expected_slug,
                observed_at=observed_at,
                page_offset=offset,
            )
            added = 0
            for observation in batch:
                if observation.canonical_url in seen_urls:
                    continue
                seen_urls.add(observation.canonical_url)
                observations.append(observation)
                added += 1
            if len(batch) < page_size:
                break
            if added == 0:
                break
        return observations

    def parse_page(
        self,
        payload: bytes,
        *,
        source_identity: str,
        site: str,
        expected_slug: str,
        observed_at: str,
        page_offset: int = 0,
    ) -> list[SourceObservation]:
        if site not in SITES:
            raise CollectorFailure("blocked_by_policy", f"site is not an allowed ForumMagnum endpoint: {site}")
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CollectorFailure("invalid_content", f"malformed forum payload: {exc}") from exc
        if not isinstance(data, dict):
            raise CollectorFailure("invalid_content", "forum payload was not an object")
        if data.get("errors") and not (data.get("data") or {}).get("posts"):
            raise CollectorFailure("invalid_content", "forum query returned errors")
        results = ((data.get("data") or {}).get("posts") or {}).get("results")
        if results is None:
            raise CollectorFailure("parser_unsupported", "forum payload has no posts.results")
        if not isinstance(results, list):
            raise CollectorFailure("invalid_content", "posts.results was not a list")
        observations: list[SourceObservation] = []
        for index, post in enumerate(results):
            if not isinstance(post, dict):
                continue
            parsed = _post_to_observation(
                post,
                source_identity=source_identity,
                site=site,
                expected_slug=expected_slug,
                observed_at=observed_at,
                page_offset=page_offset,
                index=index,
            )
            if parsed is not None:
                observations.append(parsed)
        return observations


def _graphql_url(endpoint: str, *, user_id: str, limit: int, offset: int) -> str:
    # GET is enough. The query document is built only from a validated user id
    # and integer page bounds, so it is not a place to interpolate source text.
    query = (
        "{ posts(input: {terms: {view: \"userPosts\", userId: \"%s\", limit: %d, offset: %d}}) "
        "{ results { _id title slug pageUrl postedAt url draft "
        "user { slug displayName fullName } coauthors { slug displayName fullName } "
        "contents { plaintextDescription } } } }"
    ) % (user_id, limit, offset)
    return f"{endpoint}?{urlencode({'query': query})}"


def _post_to_observation(
    post: dict,
    *,
    source_identity: str,
    site: str,
    expected_slug: str,
    observed_at: str,
    page_offset: int,
    index: int,
) -> SourceObservation | None:
    if post.get("draft") is True:
        return None
    user = post.get("user") or {}
    slug = str(user.get("slug") or "")
    if slug != expected_slug:
        return None
    page_url = str(post.get("pageUrl") or "")
    if not page_url:
        return None
    host = (urlparse(page_url).hostname or "").lower()
    if host not in {"www.lesswrong.com", "lesswrong.com", "www.alignmentforum.org", "alignmentforum.org", "forum.effectivealtruism.org"}:
        return None
    try:
        canonical = canonicalize_url(page_url)
    except ValueError:
        return None
    coauthors = [row for row in (post.get("coauthors") or []) if isinstance(row, dict)]
    names = _author_names(user, coauthors)
    description = ((post.get("contents") or {}) if isinstance(post.get("contents"), dict) else {}).get("plaintextDescription") or ""
    text, truncated = excerpt(str(description), 1500)
    linkpost = str(post.get("url") or "") or None
    published = _as_utc(post.get("postedAt"))
    observation = SourceObservation(
        source_identity=source_identity,
        platform=site,
        upstream_id=str(post.get("_id") or ""),
        canonical_url=canonical,
        observed_at=observed_at,
        published_at=published,
        author_candidates=names,
        title=str(post.get("title") or "") or None,
        segments=[Segment(segment_kind="text", sequence=0, text=text, start_char=0, end_char=len(text))],
        metadata={
            "site": site,
            "expected_slug": expected_slug,
            "author_slug": slug,
            "sole_author": not coauthors,
            "coauthor_slugs": [str(row.get("slug") or "") for row in coauthors if row.get("slug")],
            "linkpost_url": linkpost,
            "language": None,
            "language_source": "forum_payload_has_no_language_code",
            "truncated": truncated,
            "page_offset": page_offset,
            "page_index": index,
            "upstream_version": str(post.get("_id") or ""),
            "rights": "ForumMagnum public post metadata and a short excerpt. The full post is not stored.",
        },
        collection_method="forum_magnum_api",
        collector="forum_magnum",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def _author_names(user: dict, coauthors: list[dict]) -> list[AuthorCandidate]:
    candidates = []
    primary = user.get("fullName") or user.get("displayName") or user.get("slug")
    if primary:
        candidates.append(
            AuthorCandidate(name=str(primary), role="author", attribution_method="forum_author_field", confidence="medium")
        )
    for row in coauthors:
        name = row.get("fullName") or row.get("displayName") or row.get("slug")
        if name:
            candidates.append(
                AuthorCandidate(name=str(name), role="author", attribution_method="forum_author_field", confidence="low")
            )
    return candidates


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
