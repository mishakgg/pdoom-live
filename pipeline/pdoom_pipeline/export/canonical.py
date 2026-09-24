"""Map the reviewed seed registry into the canonical application import document.

Collector envelopes stay SourceObservation records. This module emits only
canonical product fields. Adapter names are preserved as provenance detail.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pdoom_pipeline.contracts import CONFIDENCE_LEVELS

ROOT = Path(__file__).resolve().parents[3]
MAP_PATH = ROOT / "packages/contracts/vocabulary-map.json"
DEFAULT_SEED = ROOT / "data/seed/cohort/v2026-09"
SCHEMA_VERSION = "1.0.0"
SLUG = __import__("re").compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_vocabulary() -> dict[str, dict[str, str]]:
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))


def map_vocabulary(kind: str, value: str, table: dict[str, dict[str, str]]) -> tuple[str, str | None]:
    mapped = table.get(kind, {}).get(value)
    if not mapped:
        raise ValueError(f"unmapped {kind}: {value}")
    return mapped, None if mapped == value else value


def normalize_prefixed_id(value: str, prefix: str) -> str:
    marker = f"{prefix}:"
    if not value.startswith(marker):
        raise ValueError(f"malformed {prefix} id: {value}")
    slug = value[len(marker) :]
    if not SLUG.fullmatch(slug) or len(slug) > 80:
        raise ValueError(f"malformed {prefix} id: {value}")
    return slug


def assert_prefixed_slug(value: str, prefix: str, slug: str) -> None:
    normalized = normalize_prefixed_id(value, prefix)
    if normalized != slug:
        raise ValueError(f"{prefix} id {value} does not match slug {slug}")


def source_slug(source_id: str) -> str:
    parts = source_id.split(":")
    if len(parts) != 4 or parts[0] != "src" or parts[1] != "person" or not parts[3]:
        raise ValueError(f"malformed source id: {source_id}")
    person = normalize_prefixed_id(f"person:{parts[2]}", "person")
    adapter = parts[3]
    if not SLUG.fullmatch(adapter):
        raise ValueError(f"malformed source id: {source_id}")
    slug = f"{person}-{adapter}"
    if not SLUG.fullmatch(slug) or len(slug) > 80:
        raise ValueError(f"source id {source_id} does not normalize to a slug")
    return slug


def cohort_slug(cohort_id: str) -> str:
    parts = cohort_id.split("_")
    if len(parts) != 3 or parts[0] != "cohort" or not parts[1].isdigit() or not parts[2].isdigit():
        raise ValueError(f"malformed cohort id: {cohort_id}")
    slug = f"cohort-{parts[1]}-{parts[2]}"
    if not SLUG.fullmatch(slug):
        raise ValueError(f"malformed cohort id: {cohort_id}")
    return slug


def _jsonl(directory: Path, name: str) -> list[dict[str, Any]]:
    path = directory / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _confidence(value: str) -> str:
    if value not in CONFIDENCE_LEVELS or value == "unknown":
        raise ValueError(f"confidence must be high, medium, or low, got {value}")
    return value


def export_seed(directory: Path | None = None) -> dict[str, Any]:
    seed = directory or DEFAULT_SEED
    vocabulary = load_vocabulary()
    organizations = _jsonl(seed, "organizations.jsonl")
    people = _jsonl(seed, "people.jsonl")
    affiliations = _jsonl(seed, "affiliations.jsonl")
    identities = _jsonl(seed, "external_identities.jsonl")
    sources = _jsonl(seed, "sources.jsonl")
    cohort = json.loads((seed / "cohort.json").read_text(encoding="utf-8"))

    org_slugs: dict[str, str] = {}
    for row in organizations:
        assert_prefixed_slug(row["id"], "org", row["slug"])
        if row["slug"] in org_slugs.values():
            raise ValueError(f"duplicate organization slug {row['slug']}")
        org_slugs[row["id"]] = row["slug"]

    person_slugs: dict[str, str] = {}
    for row in people:
        assert_prefixed_slug(row["id"], "person", row["slug"])
        if row["slug"] in person_slugs.values():
            raise ValueError(f"duplicate person slug {row['slug']}")
        person_slugs[row["id"]] = row["slug"]

    seen_sources: set[str] = set()
    canonical_sources = []
    for row in sources:
        slug = source_slug(row["id"])
        if slug in seen_sources:
            raise ValueError(f"source slug collision: {slug}")
        seen_sources.add(slug)
        owner = row.get("owner_person_id")
        if owner not in person_slugs:
            raise ValueError(f"source {row['id']} has unknown owner {owner}")
        source_type, _ = map_vocabulary("source_type", row["source_type"], vocabulary)
        method, adapter = map_vocabulary("collection_method", row["collection_method"], vocabulary)
        canonical_sources.append(
            {
                "slug": slug,
                "source_type": source_type,
                "name": row["name"][:200],
                "canonical_url": row["canonical_url"],
                "platform": row.get("platform"),
                "owner_person_slug": person_slugs[owner],
                "owner_organization_slug": None,
                "collection_method": method,
                "collection_adapter": adapter,
                "rights_notes": row.get("rights_notes"),
                "enabled": bool(row.get("enabled", True)),
                "review_state": row["review_state"],
                "last_checked_at": None,
                "last_success_at": None,
            }
        )

    generated_at = max(row["verified_at"] for row in identities)
    slug = cohort_slug(cohort["cohort_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": slug,
        "dataset_kind": "live",
        "generated_at": generated_at,
        "notice": cohort["description"],
        "producer": {"name": "pdoom-pipeline", "version": cohort["resolver_version"]},
        "organizations": [
            {
                "slug": row["slug"],
                "name": row["name"],
                "organization_type": map_vocabulary("organization_type", row["organization_type"], vocabulary)[0],
                "canonical_url": row.get("canonical_url"),
            }
            for row in organizations
        ],
        "people": [
            {
                "slug": row["slug"],
                "display_name": row["display_name"],
                "given_name": row.get("given_name"),
                "family_name": row.get("family_name"),
                "bio_short": row["bio_short"],
                "inclusion_reason": row["inclusion_reason"],
                "cohort_tags": row.get("cohort_tags") or [],
                "status": row["status"],
            }
            for row in people
        ],
        "affiliations": [
            {
                "person_slug": person_slugs[row["person_id"]],
                "organization_slug": org_slugs[row["organization_id"]],
                "role": row.get("role"),
                "start_date": None,
                "end_date": None,
                "source_slug": None,
                "confidence_level": _confidence(row["confidence"]),
                "verification_detail": map_vocabulary("verification_method", row["verification_method"], vocabulary)[1],
                "review_state": row["review_state"],
                "is_current": row["basis"] == "current",
            }
            for row in affiliations
        ],
        "external_identities": [
            {
                "person_slug": person_slugs[row["person_id"]],
                "namespace": row["namespace"],
                "external_id": row["external_id"],
                "canonical_url": row.get("canonical_url"),
                "handle": row.get("handle"),
                "verification_method": map_vocabulary("verification_method", row["verification_method"], vocabulary)[0],
                "verification_detail": map_vocabulary("verification_method", row["verification_method"], vocabulary)[1],
                "confidence_level": _confidence(row["confidence"]),
                "review_state": row["review_state"],
                "verified_at": row.get("verified_at"),
                "source_slug": None,
            }
            for row in identities
        ],
        "sources": canonical_sources,
        "source_items": [],
        "participants": [],
        "evidence_segments": [],
        "topics": [],
        "statements": [],
        "forecasts": [],
        "relationships": [],
        "cohorts": [
            {
                "slug": slug,
                "version": cohort["version"],
                "name": "Frontier seed cohort",
                "definition": cohort["description"],
                "member_slugs": [row["slug"] for row in people],
            }
        ],
        "ingestion_runs": [
            {
                "slug": f"canonical-export-{slug}",
                "collector": "canonical-export",
                "source_slug": None,
                "started_at": generated_at,
                "completed_at": generated_at,
                "status": "succeeded",
                "cursor_before": None,
                "cursor_after": None,
                "observed_count": len(canonical_sources),
                "new_count": len(canonical_sources),
                "changed_count": 0,
                "error_summary": None,
            }
        ],
        "extraction_runs": [],
        "trend_definitions": [],
    }
