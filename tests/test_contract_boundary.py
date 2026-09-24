"""The live seed stays outside the fixture import schema.

Application enums are read from the TypeScript contract. This test does not
import the seed into PostgreSQL.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENUMS = (ROOT / "packages/contracts/src/enums.ts").read_text(encoding="utf-8")
SCHEMA = json.loads(
    (ROOT / "packages/contracts/schema/canonical-import.schema.json").read_text(encoding="utf-8")
)
SEED = ROOT / "data/seed/cohort/v2026-09"


def _enum_block(name: str) -> set[str]:
    match = re.search(rf"export const {name} = \[(.*?)\] as const", ENUMS, re.S)
    assert match, name
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def _jsonl(name: str) -> list[dict]:
    path = SEED / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_fixture_schema_requires_synthetic_and_seed_does_not():
    assert SCHEMA["properties"]["synthetic"]["const"] is True
    for name in ("organizations.jsonl", "people.jsonl", "external_identities.jsonl", "sources.jsonl"):
        for row in _jsonl(name):
            assert row.get("synthetic") is not True
    cohort = json.loads((SEED / "cohort.json").read_text(encoding="utf-8"))
    assert cohort.get("synthetic") is not True
    assert cohort["not_a_census"] is True


def test_seed_vocabulary_differs_from_application_enums_in_known_places():
    org_types = _enum_block("ORGANIZATION_TYPES")
    source_types = _enum_block("SOURCE_TYPES")
    methods = _enum_block("COLLECTION_METHODS")
    verification = _enum_block("VERIFICATION_METHODS")
    roles = _enum_block("PARTICIPANT_ROLES")
    statements = _enum_block("STATEMENT_TYPES")

    used_orgs = {row["organization_type"] for row in _jsonl("organizations.jsonl")}
    assert used_orgs - org_types == {"research_lab", "infrastructure", "safety_org", "independent"}
    used_sources = {row["source_type"] for row in _jsonl("sources.jsonl")}
    assert used_sources - source_types == {
        "openalex_works",
        "personal_website",
        "lab_page",
        "rss",
        "github",
        "x",
    }
    assert used_sources & source_types == {"newsletter", "podcast"}
    used_methods = {row["collection_method"] for row in _jsonl("sources.jsonl")}
    assert used_methods == {"openalex_api", "rss_feed", "github_api", "reference_only"}
    assert used_methods.isdisjoint(methods)
    used_verification = {row["verification_method"] for row in _jsonl("external_identities.jsonl")}
    assert used_verification.isdisjoint(verification)
    assert {"author", "speaker", "mentioned"} <= roles
    assert statements == {"explicit_numeric", "explicit_qualitative", "model_inferred_signal"}


def test_seed_confidence_and_ids_are_not_application_shapes():
    identities = _jsonl("external_identities.jsonl")
    assert identities
    assert {row["confidence"] for row in identities} <= {"high", "medium", "low"}
    assert all(row["person_id"].startswith("person:") for row in identities)
    people = _jsonl("people.jsonl")
    assert people
    assert max(len(row["bio_short"]) for row in people) <= 600
