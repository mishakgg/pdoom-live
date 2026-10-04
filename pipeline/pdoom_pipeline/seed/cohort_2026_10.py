"""Build cohort 2026.10.0 from the frozen 2026.09.0 registry plus reviewed additions.

The historical directory is read and never written.
"""

from __future__ import annotations

import json
from pathlib import Path

from pdoom_pipeline.belief.priority import priority_table
from pdoom_pipeline.identity.confirm import confirm_linked_profile, drop_duplicate_external_ids
from pdoom_pipeline.seed.additions_2026_10 import (
    ADDITIONAL_AFFILIATIONS,
    BASE_SHA,
    BASE_VERSION,
    CHANNEL_EVALUATION,
    COHORT_ID,
    COHORT_VERSION,
    IDENTITY_REJECTIONS,
    NEW_IDENTITIES,
    NEW_ORGANIZATIONS,
    NEW_PEOPLE,
    NEW_SOURCES,
    PLATFORM_PROFILES,
    PRESS_EXCERPTS,
    VERIFIED_AT,
)
from pdoom_pipeline.seed.build import SEED_DIR, load_jsonl

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS_DIR = SEED_DIR
TARGET_DIR = ROOT / "data" / "seed" / "cohort" / "v2026-10"


def build_cohort(previous: Path | None = None) -> dict:
    source = previous or PREVIOUS_DIR
    people = load_jsonl(source / "people.jsonl")
    organizations = load_jsonl(source / "organizations.jsonl")
    affiliations = load_jsonl(source / "affiliations.jsonl")
    identities = load_jsonl(source / "external_identities.jsonl")
    sources = load_jsonl(source / "sources.jsonl")
    ambiguities = load_jsonl(source / "ambiguities.jsonl")
    previous_slugs = {row["slug"] for row in people}
    org_slugs = {row["slug"] for row in organizations}

    for org in NEW_ORGANIZATIONS:
        if org["slug"] in org_slugs:
            raise ValueError(f"organization already exists: {org['slug']}")
        organizations.append({key: value for key, value in org.items() if key != "country_note"})
        org_slugs.add(org["slug"])

    for person in NEW_PEOPLE:
        if person["slug"] in previous_slugs:
            raise ValueError(f"person already in the historical cohort: {person['slug']}")
        people.append(_person_record(person))
        for affiliation in person["affiliations"]:
            if affiliation["organization_slug"] not in org_slugs:
                raise ValueError(f"missing org {affiliation['organization_slug']}")
            affiliations.append(_affiliation_record(person["slug"], affiliation, verification_method="institutional_profile"))

    for affiliation in ADDITIONAL_AFFILIATIONS:
        if affiliation["organization_slug"] not in org_slugs:
            raise ValueError(affiliation["organization_slug"])
        affiliations.append(
            {
                "id": f"aff:{affiliation['person_slug']}:{affiliation['organization_slug']}:{affiliation['basis']}",
                "person_id": f"person:{affiliation['person_slug']}",
                "organization_id": f"org:{affiliation['organization_slug']}",
                "role": affiliation["role"],
                "basis": affiliation["basis"],
                "confidence": affiliation["confidence"],
                "verification_method": affiliation["verification_method"],
                "review_state": affiliation["review_state"],
                "cohort_version": COHORT_VERSION,
                "evidence_url": affiliation["evidence_url"],
                "note": affiliation["note"],
            }
        )

    people_by_slug = {row["slug"]: row for row in people}
    profile_rows = []
    for profile in PLATFORM_PROFILES:
        person = people_by_slug[profile["person_slug"]]
        decision = confirm_linked_profile(
            person=person,
            profile_names=profile["profile_names"],
            linked_from_owned_source=profile["linked_from_owned_source"],
        )
        if not decision["accepted"]:
            raise ValueError(f"profile for {profile['person_slug']} was not confirmed: {decision['reason']}")
        profile_rows.append({**profile, "confirmation": decision, "verified_at": VERIFIED_AT, "cohort_version": COHORT_VERSION})

    new_identity_rows = []
    for row in NEW_IDENTITIES:
        new_identity_rows.append(
            {
                "id": f"eid:person:{row['person_slug']}:{row['namespace']}",
                "person_id": f"person:{row['person_slug']}",
                "namespace": row["namespace"],
                "external_id": row["external_id"],
                "canonical_url": row["canonical_url"],
                "handle": row["handle"],
                "verification_method": row["verification_method"],
                "confidence": row["confidence"],
                "verified_at": VERIFIED_AT,
                "review_state": row["review_state"],
                "evidence": row["evidence"],
                "cohort_version": COHORT_VERSION,
            }
        )
    identities.extend(new_identity_rows)
    identities, duplicate_ambiguities = drop_duplicate_external_ids(identities)
    for row in duplicate_ambiguities:
        row["cohort_version"] = COHORT_VERSION
    ambiguities.extend(duplicate_ambiguities)
    ambiguities.extend(IDENTITY_REJECTIONS)

    for source in sources:
        if source.get("canonical_url") == "https://coai.cs.tsinghua.edu.cn/hml":
            source["language"] = "zh"
            source["language_source"] = "html_lang_zh_CN"
            source["language_note"] = "Homepage is zh-CN. This is a profile page, not a personal forecast."

    existing_urls = {row["canonical_url"] for row in sources}
    for source in NEW_SOURCES:
        if source["canonical_url"] in existing_urls and source["source_type"] != "press":
            raise ValueError(f"duplicate source url {source['canonical_url']}")
        sources.append(_source_record(source))

    _reject_duplicate_affiliation_keys(affiliations)
    priority = _priority(people, sources)
    added = [person["slug"] for person in NEW_PEOPLE]
    removed = sorted(previous_slugs - {row["slug"] for row in people})
    if removed:
        raise ValueError(f"historical members missing: {removed}")
    return {
        "organizations": organizations,
        "people": people,
        "affiliations": affiliations,
        "external_identities": identities,
        "sources": sources,
        "ambiguities": ambiguities,
        "platform_profiles": profile_rows,
        "collection_priority": priority,
        "press_excerpts": PRESS_EXCERPTS,
        "channel_evaluation": CHANNEL_EVALUATION,
        "cohort": _cohort_document(),
        "membership_diff": {
            "base_version": BASE_VERSION,
            "version": COHORT_VERSION,
            "base_sha": BASE_SHA,
            "base_sha_note": "Built by copying data/seed/cohort/v2026-09 at this origin/main SHA without editing that directory.",
            "added_people": added,
            "removed_people": [],
            "added_organizations": [org["slug"] for org in NEW_ORGANIZATIONS],
            "removed_organizations": [],
            "new_people_review_state": "needs_review",
            "historical_membership_unchanged": True,
        },
    }


def write_cohort(target: Path | None = None, previous: Path | None = None) -> dict[str, int]:
    directory = target or TARGET_DIR
    if directory.resolve() == PREVIOUS_DIR.resolve():
        raise ValueError("refusing to write cohort 2026.10.0 over the historical directory")
    payload = build_cohort(previous)
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "organizations.jsonl": payload["organizations"],
        "people.jsonl": payload["people"],
        "affiliations.jsonl": payload["affiliations"],
        "external_identities.jsonl": payload["external_identities"],
        "sources.jsonl": payload["sources"],
        "ambiguities.jsonl": payload["ambiguities"],
        "platform_profiles.jsonl": payload["platform_profiles"],
        "collection_priority.jsonl": payload["collection_priority"],
        "press_excerpts.jsonl": payload["press_excerpts"],
    }
    for name, rows in files.items():
        _write_jsonl(directory / name, rows)
    (directory / "cohort.json").write_text(json.dumps(payload["cohort"], indent=2) + "\n", encoding="utf-8")
    (directory / "membership_diff.json").write_text(json.dumps(payload["membership_diff"], indent=2) + "\n", encoding="utf-8")
    (directory / "channel_evaluation.json").write_text(json.dumps(payload["channel_evaluation"], indent=2) + "\n", encoding="utf-8")
    return {name: len(rows) for name, rows in files.items()}


def _person_record(person: dict) -> dict:
    current = next(item for item in person["affiliations"] if item["basis"] == "current")
    return {
        "id": f"person:{person['slug']}",
        "slug": person["slug"],
        "display_name": person["display_name"],
        "given_name": person["given_name"],
        "family_name": person["family_name"],
        "name_variants": person["name_variants"],
        "name_distinctiveness": person["name_distinctiveness"],
        "bio_short": person["bio_short"],
        "current_affiliation_id": f"org:{current['organization_slug']}",
        "inclusion_reason": person["inclusion_reason"],
        "inclusion_reasons": person["inclusion_reasons"],
        "inclusion_evidence": person["inclusion_evidence"],
        "cohort_tags": [person["focus"], COHORT_ID],
        "status": person["status"],
        "focus": person["focus"],
        "institution_keywords": person["institution_keywords"],
        "claimed_urls": [],
        "review_state": "needs_review",
        "verification_method": "institutional_profile",
        "cohort_version": COHORT_VERSION,
    }


def _affiliation_record(person_slug: str, affiliation: dict, *, verification_method: str) -> dict:
    return {
        "id": f"aff:{person_slug}:{affiliation['organization_slug']}:{affiliation['basis']}",
        "person_id": f"person:{person_slug}",
        "organization_id": f"org:{affiliation['organization_slug']}",
        "role": affiliation["role"],
        "basis": affiliation["basis"],
        "confidence": affiliation["confidence"],
        "verification_method": verification_method,
        "review_state": "needs_review",
        "cohort_version": COHORT_VERSION,
    }


def _source_record(source: dict) -> dict:
    row = {
        "id": f"src:person:{source['person_slug']}:{source['id_suffix']}",
        "source_type": source["source_type"],
        "name": source["name"],
        "canonical_url": source["canonical_url"],
        "platform": source["platform"],
        "owner_person_id": f"person:{source['person_slug']}",
        "owner_organization_id": None,
        "collection_method": source["collection_method"],
        "rights_notes": source["rights_notes"],
        "enabled": source["enabled"],
        "continuously_collectible": source["continuously_collectible"],
        "runner_wired": False,
        "review_state": source["review_state"],
        "verification_method": source["verification_method"],
        "language": source.get("language"),
        "cohort_version": COHORT_VERSION,
    }
    for key in ("site", "user_id", "expected_slug", "actor", "claim_level"):
        if source.get(key) is not None:
            row[key] = source[key]
    return row


def _priority(people: list[dict], sources: list[dict]) -> list[dict]:
    covered = set()
    nonacademic = set()
    for source in sources:
        owner = source.get("owner_person_id")
        if not owner:
            continue
        slug = owner.split(":", 1)[1]
        if source.get("source_type") != "openalex_works":
            covered.add(slug)
            if source.get("continuously_collectible"):
                nonacademic.add(slug)
    missing = {person["slug"] for person in people if person["slug"] not in nonacademic}
    return priority_table(people, lead_slugs=set(), covered_slugs=covered, missing_nonacademic_slugs=missing, limit=120)


def _reject_duplicate_affiliation_keys(rows: list[dict]) -> None:
    seen = set()
    for row in rows:
        key = (row["person_id"], row["organization_id"], row["role"], row["basis"])
        if key in seen:
            raise ValueError(f"duplicate affiliation {key}")
        seen.add(key)


def _cohort_document() -> dict:
    return {
        "cohort_id": COHORT_ID,
        "version": COHORT_VERSION,
        "previous_version": BASE_VERSION,
        "base_sha": BASE_SHA,
        "methodology": "docs/COHORT_2026_10.md",
        "not_a_census": True,
        "description": "Cohort 2026.10.0 keeps every 2026.09.0 member and adds a reviewed set of frontier-lab researchers from undercovered organizations. New people are needs_review. This is not all AI researchers and it is not a consensus sample.",
        "resolver_version": "0.2.0",
        "new_people_review_state": "needs_review",
        "adapters_wired_into_recurring_runner": False,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> None:
    counts = write_cohort()
    print(json.dumps({"directory": str(TARGET_DIR), "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
