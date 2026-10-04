"""Coverage funnel for a versioned cohort.

A registered feed, an academic identifier, a source item, and a usable
forecast are counted separately. Organization headquarters country stays on
the organization. Collection scores are a fetch budget, not a ranking of people.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from pdoom_pipeline.seed.build import load_jsonl

ACADEMIC_SOURCE_TYPES = {"openalex_works", "preprint", "research_paper"}
ATTRIBUTABLE_ROLES = {"author", "speaker", "guest"}
PUBLIC_REVIEW = {"needs_review", "machine_validated", "human_verified"}
RESEARCH_REVIEW = {"machine_validated", "human_verified"}
FAILED_COLLECTION = {"rate_limited", "invalid_content", "unauthorized", "not_found", "temporarily_unavailable", "blocked_by_policy", "content_too_large", "collector_bug", "unsafe_url"}
UNSUPPORTED_PARSER = {"parser_unsupported", "pdf_not_in_collector", "markdown_api_stub_only"}


def build_coverage(
    *,
    seed_dir: Path,
    collection_dirs: list[Path] | None = None,
    legacy_failures: list[dict] | None = None,
) -> dict:
    people = load_jsonl(seed_dir / "people.jsonl")
    orgs = {row["id"]: row for row in load_jsonl(seed_dir / "organizations.jsonl")}
    affiliations = load_jsonl(seed_dir / "affiliations.jsonl")
    identities = load_jsonl(seed_dir / "external_identities.jsonl")
    sources = load_jsonl(seed_dir / "sources.jsonl")
    ambiguities = load_jsonl(seed_dir / "ambiguities.jsonl")
    priority = load_jsonl(seed_dir / "collection_priority.jsonl") if (seed_dir / "collection_priority.jsonl").exists() else []
    cohort = json.loads((seed_dir / "cohort.json").read_text(encoding="utf-8"))
    observations = _load_many(collection_dirs or [], "source_observations.jsonl")
    candidates = _load_many(collection_dirs or [], "candidate_statements.jsonl")
    runs = _load_many(collection_dirs or [], "collector_runs.jsonl")
    leads = _load_many(collection_dirs or [], "source_leads.jsonl")

    identity_by_person: dict[str, list[dict]] = defaultdict(list)
    for row in identities:
        identity_by_person[row["person_id"]].append(row)
    source_by_person: dict[str, list[dict]] = defaultdict(list)
    for row in sources:
        if row.get("owner_person_id"):
            source_by_person[row["owner_person_id"]].append(row)
    current_aff = {}
    for row in affiliations:
        if row.get("basis") == "current" and row["person_id"] not in current_aff:
            current_aff[row["person_id"]] = row
    obs_by_person: dict[str, list[dict]] = defaultdict(list)
    for row in observations:
        if row.get("person_id"):
            obs_by_person[row["person_id"]].append(row)
    cand_by_person: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        if row.get("person_id"):
            cand_by_person[row["person_id"]].append(row)
    url_owner: dict[str, str] = {}
    for row in observations:
        if row.get("canonical_url") and row.get("person_id"):
            url_owner.setdefault(row["canonical_url"], row["person_id"])
    for row in sources:
        if row.get("canonical_url") and row.get("owner_person_id"):
            url_owner.setdefault(row["canonical_url"], row["owner_person_id"])
    failure_by_person: dict[str, list[str]] = defaultdict(list)
    for row in list(legacy_failures or []) + leads + runs:
        person_id = row.get("person_id")
        if not person_id and row.get("person_slug"):
            person_id = f"person:{row['person_slug']}"
        if not person_id and row.get("url"):
            person_id = url_owner.get(row["url"])
        error = row.get("error_class") or row.get("reason_not_admitted") or row.get("status")
        if person_id and error and error not in {"success", None, "succeeded"}:
            failure_by_person[person_id].append(str(error))

    attempted = {row.get("person_slug") for row in priority if row.get("in_fetch_budget", True)}
    if not priority:
        attempted = set()

    stages = Counter()
    gaps = Counter()
    by_reason = Counter()
    reason_usable = Counter()
    org_counts = Counter()
    country_counts = Counter()
    channel_people = Counter()
    language_people = Counter()
    topic_people = Counter()
    recency = Counter()
    review_people = Counter()
    identity_band = Counter()
    people_rows = []
    usable_people = set()
    for person in people:
        person_id = person["id"]
        by_reason[person.get("inclusion_reason") or "unspecified"] += 1
        org = orgs.get((current_aff.get(person_id) or {}).get("organization_id", ""), {})
        org_name = org.get("name") or "no_current_organization"
        country = org.get("country_code") or "unknown"
        org_counts[org_name] += 1
        country_counts[country] += 1
        band = _identity_band(identity_by_person.get(person_id, []), person_id in {row.get("person_id") for row in ambiguities})
        identity_band[band] += 1
        person_sources = source_by_person.get(person_id, [])
        person_obs = obs_by_person.get(person_id, [])
        person_cands = cand_by_person.get(person_id, [])
        attributable = [row for row in person_obs if _attributable(row)]
        usable = [row for row in attributable if _usable(row)]
        public_cands = [row for row in person_cands if row.get("review_state") in PUBLIC_REVIEW and row.get("evidence_text") and row.get("source_url")]
        research_cands = [row for row in person_cands if row.get("review_state") in RESEARCH_REVIEW and row.get("evidence_text") and row.get("source_url")]
        stage = _stage(
            has_identity=band in {"high_confidence_external_id", "medium_confidence_external_id"},
            sources=person_sources,
            observations=person_obs,
            attributable=attributable,
            usable=usable,
            candidates=person_cands,
            public_candidates=public_cands,
            research_candidates=research_cands,
        )
        stages[stage] += 1
        has_usable = bool(usable) or any(
            row.get("evidence_text") and row.get("source_url") and row.get("review_state") != "rejected" for row in person_cands
        )
        if has_usable:
            usable_people.add(person_id)
            reason_usable[person.get("inclusion_reason") or "unspecified"] += 1
        gap = _gap(
            person=person,
            sources=person_sources,
            attempted=person["slug"] in attempted or bool(person_obs) or bool(failure_by_person.get(person_id)),
            failures=failure_by_person.get(person_id, []),
            attributable=attributable,
            usable=usable,
            candidates=person_cands,
            research_candidates=research_cands,
        )
        gaps[gap] += 1
        channels = sorted({row.get("source_type") or "unspecified" for row in person_sources} or {"no_source"})
        for channel in channels:
            channel_people[channel] += 1
        languages = sorted({_language(row) for row in person_obs} or {"no_observation"})
        for language in languages:
            language_people[language] += 1
        topics = sorted({row.get("topic_slug") or "no_candidate" for row in person_cands} or {"no_candidate"})
        for topic in topics:
            topic_people[topic] += 1
        review_people[_review_bucket(person_cands)] += 1
        recency[_recency(person_obs)] += 1
        people_rows.append(
            {
                "person_slug": person["slug"],
                "inclusion_reason": person.get("inclusion_reason"),
                "organization": org_name,
                "organization_hq_country": country,
                "identity_band": band,
                "funnel_stage": stage,
                "primary_gap": gap,
                "source_types": channels,
                "usable_evidence": has_usable,
            }
        )

    duplicate_ids = sum(1 for row in ambiguities if row.get("kind") == "duplicate_external_id" or row.get("reason") == "duplicate_external_id")
    observed_urls = [row.get("canonical_url") for row in observations if row.get("canonical_url")]
    duplicate_urls = len(observed_urls) - len(set(observed_urls))
    published = [row.get("published_at") for row in observations if row.get("published_at")]
    failure_runs = [row for row in runs if row.get("status") == "failure" or row.get("error_class")]
    run_failures = Counter(row.get("error_class") or row.get("status") for row in failure_runs)
    return {
        "cohort_id": cohort.get("cohort_id"),
        "cohort_version": cohort.get("version"),
        "not_a_census": True,
        "wording": "Coverage counts are for this reviewed cohort. They are not the distribution of the field and they are not a consensus.",
        "organization_country_note": "organization_hq_country is a property of the current organization. It is not a person's nationality.",
        "priority_note": "collection_score is a fetch budget. It is not a ranking of people.",
        "funnel_people": {
            "tracked_person": len(people),
            "verified_external_identity": identity_band["high_confidence_external_id"] + identity_band["medium_confidence_external_id"],
            "high_confidence_external_identity": identity_band["high_confidence_external_id"],
            "accessible_source": sum(1 for person in people if _accessible(source_by_person.get(person["id"], []))),
            "nonacademic_accessible_source": sum(1 for person in people if _nonacademic_accessible(source_by_person.get(person["id"], []))),
            "observed_item": sum(1 for person in people if obs_by_person.get(person["id"])),
            "attributable_evidence": sum(1 for person in people if any(_attributable(row) for row in obs_by_person.get(person["id"], []))),
            "usable_evidence": len(usable_people),
            "statement_candidate": sum(1 for person in people if cand_by_person.get(person["id"])),
            "public_review_eligible_statement": sum(1 for person in people if any(row.get("review_state") in PUBLIC_REVIEW and row.get("evidence_text") for row in cand_by_person.get(person["id"], []))),
            "research_export_eligible_statement": sum(1 for person in people if any(row.get("review_state") in RESEARCH_REVIEW and row.get("evidence_text") for row in cand_by_person.get(person["id"], []))),
        },
        "furthest_stage_counts": dict(stages),
        "primary_gap_counts": dict(gaps),
        "identity_band": dict(identity_band),
        "ambiguous_records": len(ambiguities),
        "duplicate_external_id_groups": duplicate_ids,
        "duplicate_observation_url_count": duplicate_urls,
        "duplicate_observation_rate": round(duplicate_urls / len(observed_urls), 4) if observed_urls else 0,
        "inclusion_reasons": dict(by_reason),
        "inclusion_reasons_with_usable_evidence": dict(reason_usable),
        "organizations": dict(org_counts.most_common()),
        "organization_hq_country": dict(country_counts),
        "people_by_source_channel": dict(channel_people),
        "people_by_observation_language": dict(language_people),
        "people_by_candidate_topic": dict(topic_people),
        "people_by_evidence_recency": dict(recency),
        "people_by_candidate_review_state": dict(review_people),
        "source_shape": dict(Counter(_source_shape(source_by_person.get(person["id"], [])) for person in people)),
        "sources_by_type": dict(Counter(row.get("source_type") for row in sources)),
        "observations": len(observations),
        "candidates": len(candidates),
        "candidate_review_states": dict(Counter(row.get("review_state") for row in candidates)),
        "collector_runs": len(runs),
        "collector_failure_runs": len(failure_runs),
        "collector_failure_rate": round(len(failure_runs) / len(runs), 4) if runs else None,
        "collector_failure_classes": dict(run_failures),
        "legacy_failure_events": len(legacy_failures or []),
        "legacy_failure_classes": dict(Counter(row.get("error_class") for row in (legacy_failures or []) if row.get("error_class"))),
        "freshness": {
            "observations_with_published_at": len(published),
            "observations_missing_published_at": sum(1 for row in observations if not row.get("published_at")),
            "newest_published_at": max(published) if published else None,
            "oldest_published_at": min(published) if published else None,
        },
        "people": people_rows,
    }


def render_coverage_markdown(report: dict) -> str:
    funnel = report["funnel_people"]
    lines = [
        f"# Coverage funnel {report['cohort_version']}",
        "",
        report["wording"],
        "",
        report["organization_country_note"],
        "",
        report["priority_note"],
        "",
        "## Funnel, unique people",
        "",
        f"- Tracked person: {funnel['tracked_person']}",
        f"- Verified external identity (high or medium): {funnel['verified_external_identity']}",
        f"- High-confidence external identity: {funnel['high_confidence_external_identity']}",
        f"- Accessible source, including academic feeds: {funnel['accessible_source']}",
        f"- Accessible non-academic source: {funnel['nonacademic_accessible_source']}",
        f"- Observed item: {funnel['observed_item']}",
        f"- Attributable evidence: {funnel['attributable_evidence']}",
        f"- Usable evidence: {funnel['usable_evidence']}",
        f"- Statement candidate: {funnel['statement_candidate']}",
        f"- Public or review-eligible statement: {funnel['public_review_eligible_statement']}",
        f"- Research-export-eligible statement: {funnel['research_export_eligible_statement']}",
        "",
        "Usable evidence means an attributable observation of the person's own text, or a statement candidate with evidence text and a source URL. An academic identifier alone is not usable evidence.",
        "",
        "## Source shape",
        "",
    ]
    for key, value in sorted(report["source_shape"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Primary gap", ""])
    for key, value in sorted(report["primary_gap_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Identity", ""])
    for key, value in sorted(report["identity_band"].items()):
        lines.append(f"- {key}: {value}")
    lines.append(f"- Ambiguous records: {report['ambiguous_records']}")
    lines.append(f"- Duplicate external-id groups: {report['duplicate_external_id_groups']}")
    lines.append(f"- Duplicate observation URLs: {report['duplicate_observation_url_count']} (rate {report['duplicate_observation_rate']})")
    lines.extend(["", "## Inclusion reason", ""])
    for key, value in sorted(report["inclusion_reasons"].items()):
        usable = report["inclusion_reasons_with_usable_evidence"].get(key, 0)
        lines.append(f"- {key}: {value} people, {usable} with usable evidence")
    lines.extend(["", "## Organization headquarters country", ""])
    for key, value in sorted(report["organization_hq_country"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## People by source channel", ""])
    for key, value in sorted(report["people_by_source_channel"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## People by observation language", ""])
    for key, value in sorted(report["people_by_observation_language"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## People by candidate topic", ""])
    for key, value in sorted(report["people_by_candidate_topic"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Evidence recency", ""])
    for key, value in sorted(report["people_by_evidence_recency"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Candidate review state", ""])
    for key, value in sorted(report["people_by_candidate_review_state"].items()):
        lines.append(f"- {key}: {value}")
    freshness = report["freshness"]
    lines.extend(
        [
            "",
            "## Freshness and collection",
            "",
            f"- Observations: {report['observations']}",
            f"- Candidates: {report['candidates']}",
            f"- Observations with a publication time: {freshness['observations_with_published_at']}",
            f"- Observations missing a publication time: {freshness['observations_missing_published_at']}",
            f"- Newest publication time: {freshness['newest_published_at']}",
            f"- Oldest publication time: {freshness['oldest_published_at']}",
            f"- Collector runs in these directories: {report['collector_runs']}",
            f"- Collector failure runs: {report['collector_failure_runs']}",
            f"- Collector failure rate: {report['collector_failure_rate']}",
            f"- Collector failure classes: {report['collector_failure_classes']}",
            f"- Legacy failure events joined by URL: {report['legacy_failure_events']}",
            f"- Legacy failure classes: {report['legacy_failure_classes']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_coverage(report: dict, *, json_path: Path, markdown_path: Path) -> None:
    public = {key: value for key, value in report.items() if key != "people"}
    public["people_counted"] = len(report["people"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_coverage_markdown(report), encoding="utf-8")
    detail_path = json_path.with_name(json_path.stem + "-people.jsonl")
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in report["people"]]
    detail_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _load_many(directories: list[Path], name: str) -> list[dict]:
    rows = []
    for directory in directories:
        path = directory / name
        if path.exists():
            rows.extend(load_jsonl(path))
    return rows


def _identity_band(rows: list[dict], ambiguous: bool) -> str:
    if any(row.get("confidence") == "high" for row in rows):
        return "high_confidence_external_id"
    if rows:
        return "medium_confidence_external_id"
    if ambiguous:
        return "ambiguous_unresolved"
    return "no_external_identity"


def _source_shape(sources: list[dict]) -> str:
    if not sources:
        return "no_known_source"
    kinds = {row.get("source_type") for row in sources}
    if kinds <= ACADEMIC_SOURCE_TYPES:
        return "academic_source_only"
    return "has_nonacademic_source"


def _accessible(sources: list[dict]) -> bool:
    return any(row.get("enabled") and (row.get("continuously_collectible") or row.get("collection_method") in {"html_page", "rss_feed", "github_api", "openalex_api", "forum_magnum_api", "bluesky_api"}) for row in sources)


def _nonacademic_accessible(sources: list[dict]) -> bool:
    return any(_accessible([row]) and row.get("source_type") not in ACADEMIC_SOURCE_TYPES for row in sources)


def _excerpt(row: dict) -> str:
    text = row.get("text") or row.get("evidence_text") or ""
    segments = row.get("segments") or []
    if not text and segments and isinstance(segments[0], dict):
        text = segments[0].get("text") or ""
    return str(text or "")


def _attributable(row: dict) -> bool:
    role = row.get("role") or ""
    if role not in ATTRIBUTABLE_ROLES:
        return False
    if row.get("claim_level") == "institution":
        return False
    locator = row.get("canonical_url") or row.get("source_url")
    return bool(locator) and bool(_excerpt(row) or row.get("title"))


def _usable(row: dict) -> bool:
    if row.get("sole_author") is False or row.get("shared_authorship") is True:
        return False
    if row.get("claim_level") == "institution":
        return False
    role = row.get("role") or ""
    locator = row.get("canonical_url") or row.get("source_url")
    return role in ATTRIBUTABLE_ROLES and bool(locator) and bool(_excerpt(row).strip())


def _stage(*, has_identity, sources, observations, attributable, usable, candidates, public_candidates, research_candidates) -> str:
    if research_candidates:
        return "research_export_eligible_statement"
    if public_candidates:
        return "public_review_eligible_statement"
    if candidates:
        return "statement_candidate"
    if usable:
        return "usable_evidence"
    if attributable:
        return "attributable_evidence"
    if observations:
        return "observed_item"
    if _nonacademic_accessible(sources):
        return "accessible_nonacademic_source"
    if _accessible(sources) or sources:
        return "accessible_or_registered_source"
    if has_identity:
        return "verified_external_identity"
    return "tracked_person"


def _gap(*, person, sources, attempted, failures, attributable, usable, candidates, research_candidates) -> str:
    """Primary reason this person does not yet have a research-export statement.

    `academic_source_only` is reported in addition to the six collection gaps.
    An OpenAlex works feed is not an attributable statement.
    """
    del person
    if research_candidates:
        return "research_export_eligible"
    if candidates:
        return "awaiting_review"
    if usable:
        return "no_attributable_statement_found"
    if any(item in UNSUPPORTED_PARSER or item == "speaker_labels_absent" for item in failures):
        return "unsupported_parser"
    if any(item in FAILED_COLLECTION or item == "attribution_unresolved" for item in failures):
        return "failed_collection"
    if attributable:
        return "no_attributable_statement_found"
    if not sources:
        return "no_known_source"
    if _source_shape(sources) == "academic_source_only":
        return "academic_source_only"
    if not attempted:
        return "not_attempted"
    return "no_attributable_statement_found"


def _language(row: dict) -> str:
    language = row.get("language") or (row.get("metadata") or {}).get("language")
    return language or "language_unknown"


def _review_bucket(candidates: list[dict]) -> str:
    if not candidates:
        return "no_candidate"
    states = {row.get("review_state") for row in candidates}
    if "human_verified" in states:
        return "human_verified"
    if "machine_validated" in states:
        return "machine_validated"
    if "needs_review" in states:
        return "needs_review"
    if "unreviewed" in states:
        return "unreviewed"
    return "other"


def _recency(observations: list[dict]) -> str:
    stamps = [row.get("published_at") for row in observations if row.get("published_at")]
    if not stamps:
        return "no_published_item" if not observations else "published_at_unknown"
    newest = max(stamps)
    try:
        year = datetime.fromisoformat(newest.replace("Z", "+00:00")).year
    except ValueError:
        return "published_at_unknown"
    if year >= 2026:
        return "published_2026_or_later"
    if year >= 2024:
        return "published_2024_2025"
    return "published_before_2024"


def render_comparison(before: dict, after: dict) -> str:
    lines = [
        "# Coverage funnel, before and after cohort 2026.10.0",
        "",
        "Counts are unique people. A registered feed, an academic identifier, a source item, and a usable statement are separate stages.",
        "",
        before["organization_country_note"],
        "",
        before["priority_note"],
        "",
        "| Stage | Before | After |",
        "| --- | ---: | ---: |",
    ]
    labels = {
        "tracked_person": "Tracked person",
        "verified_external_identity": "Verified external identity",
        "high_confidence_external_identity": "High-confidence external identity",
        "accessible_source": "Accessible source, including academic feeds",
        "nonacademic_accessible_source": "Accessible non-academic source",
        "observed_item": "Observed item",
        "attributable_evidence": "Attributable evidence",
        "usable_evidence": "Usable evidence",
        "statement_candidate": "Statement candidate",
        "public_review_eligible_statement": "Public or review-eligible statement",
        "research_export_eligible_statement": "Research-export-eligible statement",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {before['funnel_people'][key]} | {after['funnel_people'][key]} |")
    lines.extend(["", "## Primary gap", "", "| Gap | Before | After |", "| --- | ---: | ---: |"])
    keys = sorted(set(before["primary_gap_counts"]) | set(after["primary_gap_counts"]))
    for key in keys:
        lines.append(f"| {key} | {before['primary_gap_counts'].get(key, 0)} | {after['primary_gap_counts'].get(key, 0)} |")
    lines.extend(
        [
            "",
            "## Quality",
            "",
            f"- Ambiguous records: {before['ambiguous_records']} before, {after['ambiguous_records']} after.",
            f"- Duplicate external-id groups: {before['duplicate_external_id_groups']} before, {after['duplicate_external_id_groups']} after.",
            f"- Duplicate observation URL count: {before['duplicate_observation_url_count']} before, {after['duplicate_observation_url_count']} after.",
            f"- Duplicate observation rate: {before['duplicate_observation_rate']} before, {after['duplicate_observation_rate']} after.",
            f"- Collector failure rate: {before['collector_failure_rate']} before, {after['collector_failure_rate']} after.",
            f"- Freshness before: {before['freshness']}",
            f"- Freshness after: {after['freshness']}",
            "",
        ]
    )
    return "\n".join(lines)


def load_legacy_failures(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        belief = payload.get("belief_corpus") or {}
        rows = belief.get("failure_urls") or payload.get("failure_urls") or []
        if isinstance(rows, list):
            return rows
    raise ValueError(f"unrecognized legacy failure file: {path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write a coverage funnel report.")
    parser.add_argument("--seed", required=True)
    parser.add_argument("--collections", nargs="*", default=[])
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    parser.add_argument("--legacy-failures", default="")
    args = parser.parse_args()
    legacy = []
    if args.legacy_failures:
        legacy = load_legacy_failures(Path(args.legacy_failures))
    report = build_coverage(
        seed_dir=Path(args.seed),
        collection_dirs=[Path(path) for path in args.collections],
        legacy_failures=legacy,
    )
    write_coverage(report, json_path=Path(args.json_out), markdown_path=Path(args.markdown_out))
    funnel = report["funnel_people"]
    print(json.dumps({"cohort_version": report["cohort_version"], "usable_evidence": funnel["usable_evidence"], "tracked_person": funnel["tracked_person"]}, indent=2))


if __name__ == "__main__":
    main()
