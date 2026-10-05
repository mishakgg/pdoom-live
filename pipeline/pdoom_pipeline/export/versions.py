"""Project retained adapter observations into the canonical document.

Belief export owns statements. This adds source-item versions and collector
excerpts that the belief pass did not already emit. It does not invent
statements or people.
"""

from __future__ import annotations

from pdoom_pipeline.export.canonical import source_slug
from pdoom_pipeline.export.identity import evidence_slug, source_item_slug
from pdoom_pipeline.ingest.store import ObservationStore

_SEGMENT_KINDS = {"text", "transcript", "caption", "table", "metadata"}
_ROLES = {"author", "speaker", "guest", "interviewer", "publisher", "mentioned"}


def merge_observation_store(document: dict, store: ObservationStore, registry_sources: list[dict]) -> None:
    by_identity = {}
    for row in registry_sources:
        try:
            by_identity[row["id"]] = source_slug(row["id"])
        except (KeyError, ValueError):
            continue
    source_slugs = {row["slug"] for row in document["sources"]}
    seen_items = {row["slug"] for row in document["source_items"]}
    seen_urls = {row["canonical_url"] for row in document["source_items"] if row.get("is_current")}
    seen_evidence = {row["slug"] for row in document["evidence_segments"]}
    people = {row["display_name"].casefold(): row["slug"] for row in document["people"]}
    ambiguous = _ambiguous_names(document["people"])
    for item in store.items.values():
        if item.canonical_url in seen_urls:
            continue
        current = _hex(item.current_hash)
        for version in item.versions:
            version_hash = _hex(version.get("content_hash"))
            if len(version_hash) != 64 or not version.get("observed_at") or not item.canonical_url:
                continue
            identity = version.get("source_identity")
            slug = by_identity.get(identity)
            if not slug or slug not in source_slugs:
                continue
            version_number = int(version.get("content_version") or 1)
            item_slug = source_item_slug(item.canonical_url, version_hash, version_number)
            if item_slug in seen_items:
                continue
            seen_items.add(item_slug)
            is_current = version_hash == current
            document["source_items"].append(
                {
                    "slug": item_slug,
                    "source_slug": slug,
                    "upstream_id": (version.get("upstream_id") or item.canonical_url)[:300],
                    "logical_key": item.canonical_url[:300],
                    "canonical_url": item.canonical_url,
                    "title": ((version.get("title") or "").strip()[:300] or None),
                    "published_at": version.get("published_at"),
                    "published_timezone": None,
                    "observed_at": version["observed_at"],
                    "updated_at_source": None,
                    "language": None,
                    "content_hash": version_hash,
                    "content_hash_input": None,
                    "content_version": version_number,
                    "content_reference": item.canonical_url[:300],
                    "metadata": {
                        "collector": version.get("collector"),
                        "collector_version": version.get("collector_version"),
                        "feed_url": (version.get("metadata") or {}).get("feed_url"),
                    },
                    "collection_status": "collected",
                    "availability": "available",
                    "is_current": is_current,
                    "ingestion_run_slug": "belief-corpus-2026-09",
                }
            )
            if not is_current:
                continue
            _participants(document, item_slug, version, people, ambiguous)
            _evidence(document, item_slug, item.canonical_url, version, seen_evidence)


def _participants(document: dict, item_slug: str, version: dict, people: dict[str, str], ambiguous: set[str]) -> None:
    for candidate in version.get("author_candidates") or []:
        name = (candidate.get("name") or "").strip()
        key = name.casefold()
        if not key or key in ambiguous or key not in people:
            continue
        role = candidate.get("role") if candidate.get("role") in _ROLES else "author"
        document["participants"].append(
            {
                "source_item_slug": item_slug,
                "person_slug": people[key],
                "organization_slug": None,
                "role": role,
                "attribution_method": "metadata",
                "attribution_detail": "feed_author_field",
                "confidence_level": "medium",
            }
        )


def _evidence(document: dict, item_slug: str, url: str, version: dict, seen: set[str]) -> None:
    sequence = 1
    for segment in version.get("segments") or []:
        text = (segment.get("text") or "")[:2000]
        if not text:
            continue
        kind = segment.get("segment_kind") if segment.get("segment_kind") in _SEGMENT_KINDS else "text"
        slug = evidence_slug(
            {
                "source_url": url,
                "evidence_text": text,
                "start_char": segment.get("start_char"),
                "start_ms": segment.get("start_ms"),
            }
        )
        if slug in seen:
            continue
        seen.add(slug)
        document["evidence_segments"].append(
            {
                "slug": slug,
                "source_item_slug": item_slug,
                "segment_kind": kind,
                "sequence": sequence,
                "start_char": segment.get("start_char"),
                "end_char": segment.get("end_char"),
                "start_ms": segment.get("start_ms"),
                "end_ms": segment.get("end_ms"),
                "text": text,
                "context_text": None,
            }
        )
        sequence += 1


def _ambiguous_names(people: list[dict]) -> set[str]:
    counts: dict[str, int] = {}
    for person in people:
        key = person["display_name"].casefold()
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count != 1}


def _hex(value: str | None) -> str:
    text = value or ""
    if text.startswith("sha256:"):
        text = text.split(":", 1)[1]
    return text
