"""Bounded metadata RSS pages with current robots checks and stable continuation.

One safe request attempt per cycle. A feed-hash-bound offset advances only after
that bounded page is consumed; whole-feed validators are saved only on its final
page. No body cache, evidence, extraction or public import.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Callable

from pdoom_pipeline.collectors.rss import (
    ALLOWED_TYPES, _entries, _date_text, _parse_timestamp,
)
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.refresh.admission import url_scope, public_url
from pdoom_pipeline.safe_xml import fromstring
from pdoom_pipeline.urls import canonicalize_url
from .continuous import SourceSlice, SOURCE_AUTHORS
from .scratch import StorageStop

USER_AGENT = "pdoom.live-collector/0.1 (+https://github.com/mishakgg/pdoom-live)"


class MetadataFeedProducer:
    def __init__(self, *, robots_allowed: Callable,
                 fetcher_factory: Callable[[], SafeFetcher] | None = None,
                 now: Callable[[], str] | None = None):
        self.robots_allowed = robots_allowed
        self.fetcher_factory = fetcher_factory or (lambda: SafeFetcher(
            max_bytes=1_000_000, max_attempts=1, allowed_content_types=ALLOWED_TYPES,
            user_agent=USER_AGENT))
        self.now = now or (lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def __call__(self, source, previous, max_items, stop):
        if source.get("collection_method") != "rss_feed":
            raise StorageStop("bounded feed producer supports only reviewed RSS pins")
        if source.get("owner_person_id") == "person:victoria-krakovna":
            raise StorageStop("statement-candidate source is incompatible with metadata-only collection")
        if stop():
            raise CollectorFailure("temporarily_unavailable", "slice cancelled", retryable=False)
        if self.robots_allowed(source, stop) is not True:
            raise CollectorFailure("blocked_by_policy", "current robots permission is required")
        fetcher = self.fetcher_factory()
        if (not isinstance(fetcher, SafeFetcher) or not 0 < fetcher.max_bytes <= 1_000_000
                or not 0 < fetcher.timeout <= 10 or not 0 <= fetcher.max_redirects <= 5):
            raise StorageStop("feed transport exceeds reviewed request bounds")
        fetcher.cancelled = stop
        fetcher.url_policy = url_scope(source, source["canonical_url"])
        fetcher.allowed_content_types = ALLOWED_TYPES
        fetcher.cache_get = fetcher.cache_put = None
        fetcher.header_provider = None
        # Continuations always refetch the bounded feed unconditionally. A hash
        # change resets the scan; committed logical IDs still prevent duplicates.
        continuation = None
        if previous.get("cursor") is not None:
            try:
                continuation = json.loads(previous["cursor"])
                if (set(continuation) != {"kind", "sha256", "offset"}
                        or continuation["kind"] != "rss-offset/1"
                        or not isinstance(continuation["sha256"], str)
                        or len(continuation["sha256"]) != 64
                        or not isinstance(continuation["offset"], int)
                        or not 0 < continuation["offset"] <= 10000):
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise StorageStop("invalid bounded RSS continuation") from None
        headers = {}
        if continuation is None:
            if previous.get("etag"):
                headers["If-None-Match"] = previous["etag"]
            if previous.get("last_modified"):
                headers["If-Modified-Since"] = previous["last_modified"]
        fetcher._before_attempt(source["canonical_url"])
        result = fetcher._get_once(source["canonical_url"], headers)
        if len(result.body) > 1_000_000:
            raise CollectorFailure("content_too_large", "feed response exceeds bound")
        if result.status == 304:
            if not headers or continuation is not None:
                raise CollectorFailure("invalid_content", "unconditional 304 cannot establish a cursor")
            return SourceSlice((), etag=previous.get("etag"),
                               last_modified=previous.get("last_modified"), not_modified=True)
        try:
            entries = _entries(fromstring(result.body))
        except Exception:
            raise CollectorFailure("invalid_content", "malformed bounded feed") from None
        if len(entries) > 10000:
            raise CollectorFailure("content_too_large", "feed entry-count bound exceeded")
        feed_hash = hashlib.sha256(result.body).hexdigest()
        offset = continuation["offset"] if continuation and continuation["sha256"] == feed_hash else 0
        if offset > len(entries):
            raise StorageStop("feed continuation lies beyond its identical response")
        end = min(len(entries), offset + max_items)
        feed_complete = end == len(entries)
        cursor = None if feed_complete else json.dumps({"kind": "rss-offset/1", "sha256": feed_hash,
                                                        "offset": end}, sort_keys=True, separators=(",", ":"))
        observed = self.now()
        expected_author = SOURCE_AUTHORS.get(source["owner_person_id"])
        def records():
            for index in range(offset, end):
                if stop():
                    raise CollectorFailure("temporarily_unavailable", "slice cancelled", retryable=False)
                entry = entries[index]
                record = _metadata_entry(entry, source, observed)
                if expected_author and record["author"] != expected_author:
                    continue  # All author declarations must agree with the reviewed pin.
                yield record
        return SourceSlice(records(), cursor_after=cursor, feed_complete=feed_complete,
                           etag=result.headers.get("etag") if feed_complete else None,
                           last_modified=result.headers.get("last-modified") if feed_complete else None)


ATOM = "http://www.w3.org/2005/Atom"
DC = "http://purl.org/dc/elements/1.1/"


def _tag(element):
    if element.tag.startswith("{") and "}" in element.tag:
        namespace, local = element.tag[1:].split("}", 1)
        return namespace, local.lower()
    return "", element.tag.lower()


def _text(element):
    return " ".join("".join(element.itertext()).split())


def _metadata_entry(entry, source, observed):
    """Metadata-only projection; no body/description extraction even transiently.

    Inspect all supported author declarations. A first-match parser can silently
    drop a guest coauthor, so a conflicting declaration never establishes the
    exact-author condition. Namespaces are handled explicitly, not via prefixed
    Element.find calls without a namespace map.
    """
    identities, links, authors, titles = [], [], [], []
    for child in entry:
        namespace, local = _tag(child)
        standard = namespace in {"", ATOM}
        if local in {"guid", "id"} and standard:
            value = _text(child)
            if value:
                identities.append(value)
        elif local == "link" and standard:
            # Atom self/enclosure links are not the canonical item page.
            if child.attrib.get("rel", "alternate") not in {"", "alternate"}:
                continue
            if child.attrib.get("type", "text/html") not in {"text/html", "application/xhtml+xml"}:
                continue
            value = child.attrib.get("href") or _text(child)
            if value:
                public_url(value)
                links.append(canonicalize_url(value))
        elif local == "title" and standard:
            titles.append(_text(child) or None)
        elif local in {"author", "creator"}:
            if namespace not in {"", ATOM, DC}:
                raise CollectorFailure("invalid_content", "unreviewed author namespace")
            names = [node for node in child if _tag(node) in {(ATOM, "name"), ("", "name")}]
            if len(child):
                allowed = {(ns, field) for ns in ("", ATOM) for field in ("name", "email", "uri")}
                if (not names or (child.text or "").strip()
                        or any(_tag(node) not in allowed or len(node) or (node.tail or "").strip()
                               for node in child)):
                    raise CollectorFailure("invalid_content", "ambiguous or unsupported author person construct")
                authors.extend(_text(node) for node in names)
            else:
                authors.append(_text(child))
    if len(set(identities)) > 1 or len(set(links)) > 1 or len(titles) > 1:
        raise CollectorFailure("invalid_content", "ambiguous item identity, link or title")
    guid = identities[0] if identities else None
    canonical = links[0] if links else source["canonical_url"]
    if not guid and (not links or canonical.rstrip("/") == source["canonical_url"].rstrip("/")):
        raise CollectorFailure("invalid_content", "feed item lacks stable GUID or individual link")
    published, _ = _parse_timestamp(_date_text(entry))
    declared = set(authors)
    author = next(iter(declared)) if len(declared) == 1 and "" not in declared else None
    return {"upstream_id": guid or canonical, "canonical_url": canonical,
            "title": titles[0] if titles else None, "published_at": published,
            "observed_at": observed, "author": author}
