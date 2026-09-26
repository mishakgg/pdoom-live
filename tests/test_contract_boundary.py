"""Canonical export of the live seed, and shared vocabulary drift checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pdoom_pipeline.contracts import (
    CONFIDENCE_LEVELS,
    PARTICIPANT_ROLES,
    PERSON_STATUSES,
    REVIEW_STATES,
    SOURCE_TYPES,
    STATEMENT_TYPES,
)
from pdoom_pipeline.errors import (
    BLOCKED_BY_POLICY,
    COLLECTOR_BUG,
    CONTENT_TOO_LARGE,
    INVALID_CONTENT,
    NOT_FOUND,
    PARSER_UNSUPPORTED,
    RATE_LIMITED,
    TEMPORARILY_UNAVAILABLE,
    UNAUTHORIZED,
    UNSAFE_URL,
)
from pdoom_pipeline.export.canonical import (
    assert_prefixed_slug,
    export_seed,
    map_vocabulary,
    normalize_prefixed_id,
    source_slug,
)

ROOT = Path(__file__).resolve().parents[1]
ENUMS = (ROOT / "packages/contracts/src/enums.ts").read_text(encoding="utf-8")
SHARED = json.loads((ROOT / "packages/contracts/shared-vocabulary.json").read_text(encoding="utf-8"))
VOCAB = json.loads((ROOT / "packages/contracts/vocabulary-map.json").read_text(encoding="utf-8"))
SEED = ROOT / "data/seed/cohort/v2026-09"


def _enum_block(name: str) -> list[str]:
    match = re.search(rf"export const {name} = \[(.*?)\] as const", ENUMS, re.S)
    assert match, name
    return re.findall(r'"([^"]+)"', match.group(1))


def test_shared_vocabulary_matches_both_stacks():
    assert list(STATEMENT_TYPES) == SHARED["statement_type"] == _enum_block("STATEMENT_TYPES")
    assert list(REVIEW_STATES) == SHARED["review_state"] == _enum_block("REVIEW_STATES")
    assert list(PARTICIPANT_ROLES) == SHARED["participant_role"] == _enum_block("PARTICIPANT_ROLES")
    assert list(CONFIDENCE_LEVELS) == SHARED["confidence_level"] == _enum_block("CONFIDENCE_LEVELS")
    assert list(PERSON_STATUSES) == SHARED["person_status"] == _enum_block("PERSON_STATUSES")
    assert SHARED["identity_namespace"] == _enum_block("IDENTITY_NAMESPACES")
    assert SHARED["relationship_type"] == _enum_block("RELATIONSHIP_TYPES")
    product_sources = set(_enum_block("SOURCE_TYPES"))
    assert set(SHARED["source_type_shared"]) <= product_sources
    assert set(SHARED["source_type_shared"]) <= set(SOURCE_TYPES)
    assert "openalex_works" not in product_sources
    product_statuses = set(_enum_block("COLLECTION_STATUSES"))
    collector_statuses = {
        NOT_FOUND,
        RATE_LIMITED,
        UNAUTHORIZED,
        BLOCKED_BY_POLICY,
        PARSER_UNSUPPORTED,
        CONTENT_TOO_LARGE,
        INVALID_CONTENT,
        COLLECTOR_BUG,
    }
    assert set(SHARED["collection_status_shared"]) == collector_statuses
    assert collector_statuses <= product_statuses
    assert TEMPORARILY_UNAVAILABLE not in product_statuses
    assert UNSAFE_URL not in product_statuses


def test_export_maps_seed_without_claiming_synthetic():
    document = export_seed(SEED)
    assert document["dataset_kind"] == "live"
    assert document["schema_version"] == "1.0.0"
    assert "synthetic" not in document
    assert document["statements"] == []
    assert document["source_items"] == []
    org_types = {row["organization_type"] for row in document["organizations"]}
    assert {"research_lab", "infrastructure", "safety_org", "independent"} <= org_types
    source_types = {row["source_type"] for row in document["sources"]}
    assert "academic_works" in source_types
    assert source_types <= {
        "academic_works",
        "personal_site",
        "lab_post",
        "repository",
        "social_post",
        "blog",
        "newsletter",
        "podcast",
    }
    methods = {row["collection_method"] for row in document["sources"]}
    assert {"api", "rss", "manual"} <= methods
    adapters = {row["collection_adapter"] for row in document["sources"]}
    assert "openalex_api" in adapters
    assert "reference_only" in adapters
    details = {row["verification_detail"] for row in document["external_identities"]}
    assert "openalex_exact_name_and_institution" in details
    assert "openalex_orcid_crosswalk" in details
    methods = {row["verification_method"] for row in document["external_identities"]}
    assert methods <= {"structured_academic_source", "cross_link"}
    levels = {row["confidence_level"] for row in document["external_identities"]}
    assert levels <= {"high", "medium", "low"}
    assert all(not row["slug"].startswith("person:") for row in document["people"])
    assert document["generated_at"].endswith("Z") or "+" in document["generated_at"]
    assert len(document["cohorts"][0]["member_slugs"]) == len(document["people"])


def test_prefixed_ids_reject_malformed_and_mismatched_slugs():
    assert normalize_prefixed_id("person:ada-quill", "person") == "ada-quill"
    assert source_slug("src:person:ada-quill:openalex") == "ada-quill-openalex"
    assert source_slug("src:person:ada-quill:lab_page:abc123") == "ada-quill-lab-page-abc123"
    try:
        normalize_prefixed_id("ada-quill", "person")
    except ValueError as exc:
        assert "malformed" in str(exc)
    else:
        raise AssertionError("bare slug should be rejected")
    try:
        assert_prefixed_slug("person:other", "person", "ada-quill")
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("mismatch should be rejected")


def test_known_collector_strings_map_and_unknown_strings_do_not():
    assert map_vocabulary("collection_method", "arxiv_api", VOCAB) == ("api", "arxiv_api")
    assert map_vocabulary("collection_method", "rss_feed", VOCAB) == ("rss", "rss_feed")
    assert map_vocabulary("attribution_method", "arxiv_author_metadata", VOCAB) == ("metadata", "arxiv_author_metadata")
    assert map_vocabulary("verification_method", "curator_reviewed", VOCAB) == ("manual_review", "curator_reviewed")
    try:
        map_vocabulary("source_type", "huggingface", VOCAB)
    except ValueError as exc:
        assert "unmapped" in str(exc)
    else:
        raise AssertionError("unmapped source type should fail closed")
