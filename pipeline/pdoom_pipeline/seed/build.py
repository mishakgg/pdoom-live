"""Build reviewable JSONL seed files from the curated roster."""

from __future__ import annotations

import json
from pathlib import Path

from pdoom_pipeline.contracts import COLLECTABLE_SOURCE_TYPES, INCLUSION_REASONS
from pdoom_pipeline.seed.roster_core import COHORT_ID, COHORT_VERSION, ORGS, RESOLVER_VERSION, _rows
from pdoom_pipeline.seed.roster_more import more_people

SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "seed" / "cohort" / "v2026-09"


def all_people() -> list[dict]:
    people = _rows() + more_people()
    slugs = [person["slug"] for person in people]
    if len(slugs) != len(set(slugs)):
        dupes = sorted({slug for slug in slugs if slugs.count(slug) > 1})
        raise ValueError(f"duplicate person slugs: {dupes}")
    return people


def all_orgs() -> list[dict]:
    orgs = []
    for slug, name, organization_type, url, country in ORGS:
        orgs.append(
            {
                "id": f"org:{slug}",
                "slug": slug,
                "name": name,
                "organization_type": organization_type,
                "canonical_url": url,
                "country_code": country,
            }
        )
    return orgs


def validate_roster() -> None:
    orgs = {org["slug"] for org in all_orgs()}
    for person in all_people():
        if person["primary_inclusion_reason"] not in INCLUSION_REASONS:
            raise ValueError(person["slug"])
        for reason in person["inclusion_reasons"]:
            if reason not in INCLUSION_REASONS:
                raise ValueError(person["slug"])
        if not person["inclusion_notes"] or not person["affiliations"]:
            raise ValueError(person["slug"])
        for affiliation in person["affiliations"]:
            if affiliation["organization_slug"] not in orgs:
                raise ValueError(f"{person['slug']} missing org {affiliation['organization_slug']}")


def people_records() -> list[dict]:
    records = []
    for person in all_people():
        current = next(item for item in person["affiliations"] if item["basis"] == "current")
        records.append(
            {
                "id": f"person:{person['slug']}",
                "slug": person["slug"],
                "display_name": person["display_name"],
                "given_name": person["given_name"],
                "family_name": person["family_name"],
                "name_variants": person["name_variants"],
                "name_distinctiveness": person["name_distinctiveness"],
                "bio_short": person["inclusion_notes"],
                "current_affiliation_id": f"org:{current['organization_slug']}",
                "inclusion_reason": person["primary_inclusion_reason"],
                "inclusion_reasons": person["inclusion_reasons"],
                "cohort_tags": [person["focus"], COHORT_ID],
                "status": person["status"],
                "focus": person["focus"],
                "institution_keywords": person["institution_keywords"],
                "claimed_urls": person["claimed_urls"],
                "review_state": "human_verified",
                "verification_method": "curator_reviewed",
                "cohort_version": COHORT_VERSION,
            }
        )
    return records


def affiliation_records() -> list[dict]:
    rows = []
    for person in all_people():
        for affiliation in person["affiliations"]:
            rows.append(
                {
                    "id": f"aff:{person['slug']}:{affiliation['organization_slug']}:{affiliation['basis']}",
                    "person_id": f"person:{person['slug']}",
                    "organization_id": f"org:{affiliation['organization_slug']}",
                    "role": affiliation["role"],
                    "basis": affiliation["basis"],
                    "confidence": affiliation["confidence"],
                    "verification_method": "curator_reviewed",
                    "review_state": "human_verified",
                    "cohort_version": COHORT_VERSION,
                }
            )
    return rows


def identities_from_resolution(resolution: dict) -> tuple[list[dict], list[dict], list[dict]]:
    identities: list[dict] = []
    sources: list[dict] = []
    ambiguities: list[dict] = []
    for person_id, decision in sorted(resolution.get("people", {}).items()):
        status = decision.get("status")
        if status == "ambiguous":
            ambiguities.append({"person_id": person_id, **decision, "cohort_version": COHORT_VERSION})
            continue
        if status != "accepted" or not decision.get("openalex_id"):
            continue
        openalex_id = decision["openalex_id"]
        identities.append(
            {
                "id": f"eid:{person_id}:openalex",
                "person_id": person_id,
                "namespace": "openalex",
                "external_id": openalex_id,
                "canonical_url": f"https://openalex.org/{openalex_id}",
                "handle": None,
                "verification_method": decision["verification_method"],
                "confidence": decision["confidence"],
                "verified_at": resolution.get("resolved_at"),
                "review_state": "machine_validated" if decision["confidence"] == "high" else "needs_review",
                "evidence": {
                    "matched_name": decision.get("matched_name"),
                    "matched_institutions": decision.get("matched_institutions"),
                    "works_count": decision.get("works_count"),
                    "candidate_count": decision.get("candidate_count"),
                    "resolver_version": RESOLVER_VERSION,
                },
            }
        )
        sources.append(
            {
                "id": f"src:{person_id}:openalex",
                "source_type": "openalex_works",
                "name": f"OpenAlex works for {person_id}",
                "canonical_url": f"https://api.openalex.org/works?filter=authorships.author.id:{openalex_id}",
                "platform": "openalex",
                "owner_person_id": person_id,
                "owner_organization_id": None,
                "collection_method": "openalex_api",
                "rights_notes": "OpenAlex public API metadata. Store excerpts and identifiers, not full text republication.",
                "enabled": True,
                "continuously_collectible": "openalex_works" in COLLECTABLE_SOURCE_TYPES,
                "external_id": openalex_id,
                "review_state": "machine_validated" if decision["confidence"] == "high" else "needs_review",
                "verification_method": decision["verification_method"],
            }
        )
        if decision.get("orcid"):
            orcid = decision["orcid"]
            identities.append(
                {
                    "id": f"eid:{person_id}:orcid",
                    "person_id": person_id,
                    "namespace": "orcid",
                    "external_id": orcid,
                    "canonical_url": f"https://orcid.org/{orcid}",
                    "handle": None,
                    "verification_method": "openalex_orcid_crosswalk",
                    "confidence": decision["confidence"],
                    "verified_at": resolution.get("resolved_at"),
                    "review_state": "machine_validated" if decision["confidence"] == "high" else "needs_review",
                    "evidence": {"source": "openalex.ids.orcid", "openalex_id": openalex_id, "resolver_version": RESOLVER_VERSION},
                }
            )
    for conflict in resolution.get("conflicts", []):
        ambiguities.append({"kind": "duplicate_external_id", **conflict, "cohort_version": COHORT_VERSION})
    _reject_duplicate_identities(identities, ambiguities)
    return identities, sources, ambiguities


def _reject_duplicate_identities(identities: list[dict], ambiguities: list[dict]) -> None:
    seen: dict[tuple[str, str], list[dict]] = {}
    for identity in identities:
        seen.setdefault((identity["namespace"], identity["external_id"]), []).append(identity)
    drop_ids = set()
    for (namespace, external_id), group in seen.items():
        if len(group) < 2:
            continue
        ambiguities.append(
            {
                "kind": "duplicate_external_id",
                "namespace": namespace,
                "external_id": external_id,
                "person_ids": [item["person_id"] for item in group],
                "cohort_version": COHORT_VERSION,
            }
        )
        drop_ids.update(item["id"] for item in group)
        if namespace == "openalex":
            for item in identities:
                if item.get("evidence", {}).get("openalex_id") == external_id:
                    drop_ids.add(item["id"])
    identities[:] = [item for item in identities if item["id"] not in drop_ids]


def cohort_document() -> dict:
    return {
        "cohort_id": COHORT_ID,
        "version": COHORT_VERSION,
        "methodology": "docs/COHORT_METHODOLOGY.md",
        "not_a_census": True,
        "description": "High-confidence seed of frontier-AI researchers, research leaders, and closely related safety, evaluation, and forecasting researchers. This is not all AI researchers and it is not a consensus sample.",
        "resolver_version": RESOLVER_VERSION,
        "inclusion_reasons": list(INCLUSION_REASONS),
    }


def write_seed(directory: Path | None = None, resolution: dict | None = None) -> dict[str, int]:
    validate_roster()
    target = directory or SEED_DIR
    target.mkdir(parents=True, exist_ok=True)
    identities, sources, ambiguities = identities_from_resolution(resolution or {"people": {}, "conflicts": []})
    files = {
        "organizations.jsonl": all_orgs(),
        "people.jsonl": people_records(),
        "affiliations.jsonl": affiliation_records(),
        "external_identities.jsonl": identities,
        "sources.jsonl": sources,
        "ambiguities.jsonl": ambiguities,
    }
    for name, rows in files.items():
        _write_jsonl(target / name, rows)
    (target / "cohort.json").write_text(json.dumps(cohort_document(), indent=2) + "\n", encoding="utf-8")
    if resolution is not None:
        (target / "resolution.json").write_text(json.dumps(resolution, indent=2) + "\n", encoding="utf-8")
    return {name: len(rows) for name, rows in files.items()}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
