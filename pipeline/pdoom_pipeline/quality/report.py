"""Dataset quality report for the versioned seed cohort."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pdoom_pipeline.seed.build import SEED_DIR, load_jsonl

ACADEMIC_NAMESPACES = {"orcid", "openalex", "openreview", "semantic_scholar"}
PROFILE_NAMESPACES = {"personal_website", "lab_profile"}


def build_report(seed_dir: Path | None = None, collector_runs: list[dict] | None = None, corpus: dict | None = None) -> dict:
    directory = seed_dir or SEED_DIR
    people = load_jsonl(directory / "people.jsonl")
    orgs = load_jsonl(directory / "organizations.jsonl")
    affiliations = load_jsonl(directory / "affiliations.jsonl")
    identities = load_jsonl(directory / "external_identities.jsonl")
    sources = load_jsonl(directory / "sources.jsonl")
    ambiguities = load_jsonl(directory / "ambiguities.jsonl")
    cohort = json.loads((directory / "cohort.json").read_text(encoding="utf-8"))
    org_by_id = {org["id"]: org for org in orgs}
    current_aff = [row for row in affiliations if row["basis"] == "current"]
    org_counts = Counter(org_by_id[row["organization_id"]]["name"] for row in current_aff)
    country_counts = Counter((org_by_id[row["organization_id"]].get("country_code") or "unknown") for row in current_aff)
    reason_counts = Counter(person["inclusion_reason"] for person in people)
    focus_counts = Counter(person.get("focus") or "unspecified" for person in people)
    identity_by_person: dict[str, list[dict]] = {}
    for identity in identities:
        identity_by_person.setdefault(identity["person_id"], []).append(identity)
    confidence_counts = Counter(identity["confidence"] for identity in identities)
    with_academic = 0
    with_profile = 0
    with_verified_profile = 0
    claimed_unconfirmed = 0
    with_collectible = 0
    source_by_person: dict[str, list[dict]] = {}
    for source in sources:
        if source.get("owner_person_id"):
            source_by_person.setdefault(source["owner_person_id"], []).append(source)
    missing_academic = []
    for person in people:
        rows = identity_by_person.get(person["id"], [])
        namespaces = {row["namespace"] for row in rows}
        if namespaces & ACADEMIC_NAMESPACES:
            with_academic += 1
        else:
            missing_academic.append(person["id"])
        if namespaces & PROFILE_NAMESPACES:
            with_verified_profile += 1
            with_profile += 1
        elif person.get("claimed_urls"):
            claimed_unconfirmed += 1
            with_profile += 1
        if any(source.get("enabled") and source.get("continuously_collectible") for source in source_by_person.get(person["id"], [])):
            with_collectible += 1
    n = len(people) or 1
    runs = collector_runs or []
    success = sum(1 for run in runs if run.get("status") == "success")
    failure = sum(1 for run in runs if run.get("status") != "success")
    failure_classes = Counter(run.get("error_class") or "none" for run in runs if run.get("status") != "success")
    return {
        "cohort_id": cohort["cohort_id"],
        "cohort_version": cohort["version"],
        "not_a_census": True,
        "wording": "This seed is a reviewed frontier-AI cohort. It is not all AI researchers, not a random sample, and not a measure of consensus.",
        "people": len(people),
        "organizations": len(orgs),
        "organizations_with_a_current_member": len(org_counts),
        "affiliations": len(affiliations),
        "external_identities": len(identities),
        "sources": len(sources),
        "ambiguities": len(ambiguities),
        "inclusion_reasons": dict(reason_counts),
        "focus": dict(focus_counts),
        "current_organization_distribution": dict(org_counts.most_common()),
        "current_organization_hq_country": dict(country_counts),
        "identity_confidence": dict(confidence_counts),
        "percent_with_academic_identifier": round(100 * with_academic / n, 1),
        "percent_with_profile_or_claimed_site": round(100 * with_profile / n, 1),
        "percent_with_verified_profile": round(100 * with_verified_profile / n, 1),
        "claimed_unconfirmed_profile_count": claimed_unconfirmed,
        "external_identities_by_namespace": dict(Counter(row["namespace"] for row in identities)),
        "percent_with_continuously_collectible_source": round(100 * with_collectible / n, 1),
        "sources_by_type": dict(Counter(source["source_type"] for source in sources)),
        "missing_academic_identifier_count": len(missing_academic),
        "ambiguous_match_count": len(ambiguities),
        "duplicate_candidate_count": sum(1 for row in ambiguities if row.get("kind") == "duplicate_external_id" or row.get("reason") == "duplicate_external_id"),
        "collector_runs": len(runs),
        "collector_success": success,
        "collector_failure": failure,
        "collector_failure_classes": dict(failure_classes),
        "belief_corpus": corpus or {},
        "biases": [
            "English-language public profiles and English-indexed academic graphs are over-represented.",
            "Organization headquarters country is not nationality and is not a place of birth.",
            "Industry frontier labs in the United States are easier to name from English-language sources than industry labs elsewhere.",
            "Researchers who rarely publish under a stable academic name, including some founders, will show missing ORCID and OpenAlex ids. That absence is not a failed identity.",
            "Social accounts are omitted unless a structured profile or confirmed page links them. Coverage of X, Bluesky, Mastodon, YouTube, and podcasts is therefore sparse in this version.",
            "The cohort is a purposive seed, so organization counts must not be read as the distribution of the field.",
        ],
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# Cohort quality report {report['cohort_version']}",
        "",
        report["wording"],
        "",
        f"- People: {report['people']}",
        f"- Organizations in registry: {report['organizations']}",
        f"- Organizations with a current member: {report['organizations_with_a_current_member']}",
        f"- Affiliations: {report['affiliations']}",
        f"- External identities: {report['external_identities']}",
        f"- Registered sources: {report['sources']}",
        f"- Ambiguous matches: {report['ambiguous_match_count']}",
        f"- Duplicate external-id candidates: {report['duplicate_candidate_count']}",
        f"- Academic identifier coverage: {report['percent_with_academic_identifier']}%",
        f"- Verified institution or personal profile: {report['percent_with_verified_profile']}%",
        f"- Profile or claimed personal site, including unverified claims: {report['percent_with_profile_or_claimed_site']}%",
        f"- Claimed sites not confirmed on the page: {report['claimed_unconfirmed_profile_count']}",
        f"- At least one continuously collectible source: {report['percent_with_continuously_collectible_source']}%",
        f"- People missing an academic identifier: {report['missing_academic_identifier_count']}",
        f"- Collector runs recorded: {report['collector_runs']} (success {report['collector_success']}, failure {report['collector_failure']})",
        "",
    ]
    corpus = report.get("belief_corpus") or {}
    if corpus:
        lines.extend(
            [
                "## Belief corpus",
                "",
                "Collection priority is a fetch budget. It is not a ranking of researchers.",
                "",
                f"- Priority people considered: {corpus.get('priority_people')}",
                f"- People with a collected non-academic item: {corpus.get('people_with_items')}",
                f"- People with a statement candidate: {corpus.get('people_with_statements')}",
                f"- Source items: {corpus.get('source_items')}",
                f"- Statement candidates: {corpus.get('statements')}",
                f"- By statement type: {corpus.get('by_type')}",
                f"- By forecast kind: {corpus.get('by_kind')}",
                f"- By question key: {corpus.get('by_question')}",
                f"- Explicit numeric / qualitative / model-inferred: {corpus.get('explicit_numeric')} / {corpus.get('explicit_qualitative')} / {corpus.get('model_inferred')}",
                f"- Numeric candidates missing a horizon: {corpus.get('missing_horizon')}",
                f"- Numeric candidates missing a definition: {corpus.get('missing_definition')}",
                f"- People on a podcast item: {corpus.get('podcast_people')}",
                f"- People with owned writing: {corpus.get('owned_people')}",
                f"- View-change candidates: {corpus.get('relationships')}",
                f"- Collector failures: {corpus.get('failures')}",
                "",
            ]
        )
    lines.extend(["", "## Inclusion reasons", ""])
    for key, value in sorted(report["inclusion_reasons"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Current organization headquarters country", ""])
    for key, value in sorted(report["current_organization_hq_country"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Sources by type", ""])
    if report["sources_by_type"]:
        for key, value in sorted(report["sources_by_type"].items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none recorded yet")
    lines.extend(["", "## Known biases", ""])
    for bias in report["biases"]:
        lines.append(f"- {bias}")
    lines.append("")
    return "\n".join(lines)


def write_report(seed_dir: Path | None = None, collector_runs: list[dict] | None = None, corpus: dict | None = None) -> dict:
    directory = seed_dir or SEED_DIR
    report_dir = directory.parents[2] / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(directory, collector_runs, corpus)
    (report_dir / "cohort-v2026-09-quality.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (report_dir / "cohort-v2026-09-quality.md").write_text(render_markdown(report), encoding="utf-8")
    return report
