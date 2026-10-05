"""Read-only quality evaluation. Failures are reported and never repaired."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pdoom_pipeline.observability.catalog import load_catalog


def evaluate(partial: dict | None = None, baseline: dict | None = None, *, scope: str = "snapshot", run_id: str | None = None) -> dict:
    snapshot = complete_snapshot(partial or {})
    guardrails = load_catalog()["guardrails"]
    findings: list[dict] = []
    live = snapshot["dataset_kind"] == "live"
    if snapshot["database_checked"] and not snapshot["readiness"]["database"]:
        findings.append(_finding("database_unavailable", "error", "Database readiness check failed.", None))
    else:
        _dataset(snapshot, baseline, guardrails, live, findings)
    if not snapshot["canonical_valid"]:
        findings.append(_finding("canonical_validation_failed", "error", "Canonical import failed validation.", 1))
    streak = snapshot["import_failure_streak"]
    if streak >= guardrails["import_failure_streak"] and streak > 0:
        findings.append(_finding("imports_repeatedly_fail", "error", f"Imports failed {streak} times in a row.", streak))
    slos = _slos(snapshot, findings)
    alerts = _alerts(findings)
    status = public_status(snapshot)
    report = {
        "ok": not any(item["severity"] == "error" for item in findings),
        "run_id": run_id or uuid.uuid4().hex,
        "scope": scope,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset_kind": snapshot["dataset_kind"],
        "status": status,
        "findings": findings,
        "alerts": alerts,
        "slos": slos,
        "counts": _counts(snapshot),
        "summary": "",
    }
    report["summary"] = _summary(report)
    return report


def quality_exit_code(report: dict, strict: bool = False) -> int:
    if not report["ok"]:
        return 1
    if strict and any(item["severity"] == "warning" for item in report["findings"]):
        return 1
    return 0


def public_status(snapshot: dict) -> dict:
    if snapshot["database_checked"] and not snapshot["readiness"]["database"]:
        return {
            "app": "unavailable",
            "dataset": "unknown",
            "dataset_kind": snapshot["dataset_kind"],
            "dataset_generated_at": None,
            "latest_successful_observation": None,
            "freshness": {"current": 0, "aging": 0, "stale": 0, "never_checked": 0},
        }
    return {
        "app": "operational",
        "dataset": _dataset_state(snapshot),
        "dataset_kind": snapshot["dataset_kind"],
        "dataset_generated_at": snapshot["dataset_generated_at"],
        "latest_successful_observation": snapshot["latest_successful_observation"],
        "freshness": snapshot["freshness"],
    }


def complete_snapshot(partial: dict) -> dict:
    base = _defaults(partial.get("as_of") or "1970-01-01T00:00:00.000Z")
    merged = {**base, **partial}
    for key in ("readiness", "statements_by_review", "freshness", "enabled_freshness", "integrity", "slo"):
        merged[key] = {**base[key], **(partial.get(key) or {})}
    collection = {**base["collection"], **(partial.get("collection") or {})}
    incoming = partial.get("collection") or {}
    collection["failures_by_class"] = {**base["collection"]["failures_by_class"], **incoming.get("failures_by_class", {})}
    for key in ("runs_by_adapter", "failures_by_adapter", "rate_limits_by_adapter"):
        collection[key] = incoming[key] if key in incoming else base["collection"][key]
    merged["collection"] = collection
    extraction = {**base["extraction"], **(partial.get("extraction") or {})}
    extraction["candidates_by_type"] = {
        **base["extraction"]["candidates_by_type"],
        **((partial.get("extraction") or {}).get("candidates_by_type") or {}),
    }
    merged["extraction"] = extraction
    if "stale_by_source_type" not in partial:
        merged["stale_by_source_type"] = base["stale_by_source_type"]
    if "never_successful_by_source_type" not in partial:
        merged["never_successful_by_source_type"] = base["never_successful_by_source_type"]
    return merged


def snapshot_from_runs(
    *,
    runs: list[dict] | None = None,
    sources: list[dict] | None = None,
    statements: list[dict] | None = None,
    identities: list[dict] | None = None,
    as_of: str,
    dataset_kind: str = "live",
    window_hours: int = 168,
) -> dict:
    """Build a snapshot from pipeline records. Text bodies are not copied."""
    catalog = load_catalog()
    collection = complete_snapshot({})["collection"]
    end = _parse(as_of)
    start = end - window_hours * 3_600_000
    for run in runs or []:
        started = _parse(str(run.get("started_at") or "")) if run.get("started_at") else None
        if started is None or started < start or started > end:
            continue
        collection["attempted"] += 1
        status = str(run.get("status") or "")
        observed = int(run.get("observed_count") or 0)
        created = int(run.get("new_count") or 0)
        changed = int(run.get("changed_count") or 0)
        if run.get("unchanged_count") is None:
            unchanged = max(0, observed - created - changed)
        else:
            unchanged = int(run.get("unchanged_count") or 0)
        if status == "succeeded":
            collection["succeeded"] += 1
            collection["unchanged"] += unchanged
            collection["changed"] += changed
            collection["new"] += created
        elif status in {"failed", "partial"}:
            collection["failed"] += 1
            if status == "partial":
                collection["unchanged"] += unchanged
                collection["changed"] += changed
                collection["new"] += created
            klass = str(run.get("error_class") or run.get("error_summary") or "")
            if klass not in catalog["labels"]["failure_class"]:
                klass = "unclassified"
            collection["failures_by_class"][klass] = collection["failures_by_class"].get(klass, 0) + 1
            if klass == "rate_limited":
                collection["rate_limited"] += 1
    freshness = {"current": 0, "aging": 0, "stale": 0, "never_checked": 0}
    enabled_freshness = {"current": 0, "aging": 0, "stale": 0, "never_checked": 0}
    enabled = 0
    stale = 0
    never = 0
    for source in sources or []:
        state = _freshness(source.get("last_success_at"), as_of)
        freshness[state] += 1
        if not source.get("enabled", True):
            continue
        enabled += 1
        enabled_freshness[state] += 1
        if state == "stale":
            stale += 1
        if not source.get("last_success_at"):
            never += 1
    reviews = {"unreviewed": 0, "machine_validated": 0, "human_verified": 0, "rejected": 0, "needs_review": 0}
    by_type = {"explicit_numeric": 0, "explicit_qualitative": 0, "model_inferred_signal": 0}
    for statement in statements or []:
        review = str(statement.get("review_state") or "unreviewed")
        if review in reviews:
            reviews[review] += 1
        kind = str(statement.get("statement_type") or "")
        if review != "rejected" and kind in by_type:
            by_type[kind] += 1
    seen: dict[tuple, int] = {}
    for identity in identities or []:
        key = (str(identity.get("namespace")), str(identity.get("external_id")))
        seen[key] = seen.get(key, 0) + 1
    duplicates = sum(1 for count in seen.values() if count > 1)
    return complete_snapshot(
        {
            "as_of": as_of,
            "dataset_present": True,
            "dataset_kind": dataset_kind,
            "database_checked": False,
            "cohort_size": int((sources and 1) or 1),
            "source_count": len(sources or []),
            "enabled_source_count": enabled,
            "sources_stale": stale,
            "sources_never_successful": never,
            "freshness": freshness,
            "enabled_freshness": enabled_freshness,
            "collection": collection,
            "statements_by_review": reviews,
            "extraction": {"candidates_by_type": by_type, "explicit_numeric": by_type["explicit_numeric"]},
            "integrity": {"duplicate_identity_ids": duplicates},
            "collection_window_hours": window_hours,
        }
    )


def _dataset(snapshot, baseline, guardrails, live, findings) -> None:
    if not snapshot["dataset_present"]:
        findings.append(_finding("dataset_not_loaded", "warning", "No current dataset import is loaded.", None))
    elif snapshot["cohort_size"] == 0:
        findings.append(_finding("cohort_empty", "error", "The current dataset cohort has no members.", 0))
    enabled = snapshot["enabled_source_count"]
    fresh = snapshot["enabled_freshness"]
    all_stale = enabled > 0 and fresh["current"] == 0 and fresh["aging"] == 0
    if all_stale:
        findings.append(
            _finding(
                "all_sources_stale",
                "error" if live else "info",
                "Every enabled cohort source is stale or has never succeeded."
                if live
                else "Enabled sources are stale or unchecked. Synthetic and fixture timestamps are not a live incident.",
                enabled,
            )
        )
    if snapshot["slo"]["cadence_eligible"] > 0 and snapshot["collection"]["succeeded"] == 0:
        findings.append(
            _finding(
                "collection_stopped",
                "error" if live else "info",
                "No collection run succeeded inside the expected window."
                if live
                else "No collection run succeeded inside the window. This dataset is not on a live collection clock.",
                snapshot["collection"]["attempted"],
            )
        )
    if snapshot["collection"]["rate_limited"] > 0:
        findings.append(
            _finding(
                "collection_rate_limited",
                "warning" if live else "info",
                f"Rate limiting was recorded {snapshot['collection']['rate_limited']} times.",
                snapshot["collection"]["rate_limited"],
            )
        )
    for key, summary in (
        ("duplicate_identity_ids", "Duplicate external identity ids are present."),
        ("multiple_current_versions", "More than one current version exists for a source item."),
        ("human_verified_missing_evidence", "A human-verified statement is missing evidence."),
        ("numeric_without_numeric_evidence", "An explicit numeric statement has no numeric value or no digit in its evidence."),
        ("impossible_probability", "A probability forecast is outside 0–1 or has a minimum above its maximum."),
        ("public_statement_unavailable_source", "A public statement points at an unavailable source without an explicit availability state."),
    ):
        count = snapshot["integrity"][key]
        if count > 0:
            findings.append(_finding(key, "error", summary, count))
    if baseline:
        _drop("cohort_drop", "Cohort size", baseline.get("cohort_size"), snapshot["cohort_size"], guardrails["cohort_drop_ratio"], findings)
        _drop("source_count_drop", "Source count", baseline.get("source_count"), snapshot["source_count"], guardrails["source_drop_ratio"], findings)
        _drop("statement_count_drop", "Statement count", baseline.get("statement_count"), _statement_total(snapshot), guardrails["statement_drop_ratio"], findings)
        _drop(
            "human_verified_drop",
            "Human-verified statements",
            baseline.get("human_verified_statements"),
            snapshot["statements_by_review"]["human_verified"],
            guardrails["human_verified_drop_ratio"],
            findings,
        )
        public_now = snapshot["statements_by_review"]["human_verified"] + snapshot["statements_by_review"]["machine_validated"]
        public_base = (baseline.get("human_verified_statements") or 0) + (baseline.get("machine_validated_statements") or 0)
        if public_base > 0 and public_now == 0:
            findings.append(
                _finding(
                    "public_verified_dataset_empty",
                    "error",
                    "Human-verified and machine-validated statements dropped to zero from a non-empty baseline.",
                    0,
                )
            )
        grew = _greater(snapshot["cohort_size"], baseline.get("cohort_size")) or _greater(snapshot["source_count"], baseline.get("source_count")) or _greater(
            _statement_total(snapshot), baseline.get("statement_count")
        )
        if grew:
            findings.append(_finding("dataset_growth", "info", "Dataset counts grew relative to the baseline.", None))
    processed = snapshot["extraction"]["items_processed"]
    if processed >= guardrails["extractor_failure_min_processed"]:
        rate = snapshot["extraction"]["failures"] / processed
        if rate > guardrails["extractor_failure_ratio"]:
            findings.append(_finding("extractor_failure_rate", "warning", "Extraction failure rate is above the guardrail.", snapshot["extraction"]["failures"]))
    numeric = snapshot["extraction"]["explicit_numeric"]
    if numeric > 0:
        if snapshot["extraction"]["missing_horizon"] / numeric > guardrails["missing_horizon_ratio"]:
            findings.append(_finding("missing_horizon_rate", "warning", "Explicit numeric statements are missing horizons.", snapshot["extraction"]["missing_horizon"]))
        if snapshot["extraction"]["missing_definition"] / numeric > guardrails["missing_definition_ratio"]:
            findings.append(_finding("missing_definition_rate", "warning", "Explicit numeric statements are missing definitions.", snapshot["extraction"]["missing_definition"]))
    if live and enabled > 0 and not all_stale:
        ratio = snapshot["sources_stale"] / enabled
        spiked = baseline and baseline.get("stale_ratio") is not None and ratio - baseline["stale_ratio"] > guardrails["stale_ratio_increase"]
        if ratio > guardrails["stale_source_ratio"] or spiked:
            findings.append(_finding("stale_source_ratio", "warning", "The share of stale enabled sources is above the guardrail.", snapshot["sources_stale"]))
    findings.append(_finding("freshness_distribution", "info", "Freshness distribution.", snapshot["source_count"]))
    findings.append(_finding("coverage_summary", "info", "Coverage summary.", snapshot["cohort_size"]))
    if not baseline:
        findings.append(_finding("baseline_not_configured", "info", "No baseline file was provided, so relative dataset-size guardrails were not applied.", None))


def _slos(snapshot, findings) -> list[dict]:
    catalog = load_catalog()["slos"]
    live = snapshot["dataset_kind"] == "live" and snapshot["readiness"]["database"]
    results = []
    cadence_target = catalog["enabled_sources_within_cadence"]["target"]
    eligible = snapshot["slo"]["cadence_eligible"]
    cadence_ok = live and eligible > 0
    cadence_value = snapshot["slo"]["cadence_met"] / eligible if cadence_ok and eligible else None
    cadence = {
        "id": "enabled_sources_within_cadence",
        "status": "not_applicable" if not cadence_ok else "met" if cadence_value is not None and cadence_value + 1e-12 >= cadence_target else "breach",
        "target": cadence_target,
        "value": cadence_value,
        "summary": "Share of enabled rss, api, and sitemap sources successfully checked inside their cadence.",
    }
    age_target = catalog["latest_successful_collection_age_hours"]["target"]
    age_value = _hours(snapshot["latest_successful_observation"], snapshot["as_of"]) if cadence_ok else None
    age_breach = cadence_ok and (age_value is None or age_value > age_target)
    age = {
        "id": "latest_successful_collection_age_hours",
        "status": "not_applicable" if not cadence_ok else "breach" if age_breach else "met",
        "target": age_target,
        "value": age_value,
        "summary": "Age in hours of the latest successful collection. A stale source does not mean the researcher is inactive.",
    }
    fresh_target = catalog["statement_bearing_sources_fresh"]["target"]
    holders = snapshot["slo"]["statement_bearing_sources"]
    fresh_ok = live and holders > 0
    fresh_value = snapshot["slo"]["statement_bearing_sources_fresh"] / holders if fresh_ok and holders else None
    fresh = {
        "id": "statement_bearing_sources_fresh",
        "status": "not_applicable" if not fresh_ok else "met" if fresh_value is not None and fresh_value + 1e-12 >= fresh_target else "breach",
        "target": fresh_target,
        "value": fresh_value,
        "summary": "Share of statement-bearing cohort sources that are current or aging. A stale source does not mean the researcher is inactive.",
    }
    for slo in (cadence, age, fresh):
        if slo["status"] == "breach":
            findings.append(_finding(slo["id"], "warning", slo["summary"], None))
        results.append(slo)
    return results


def _alerts(findings) -> list[dict]:
    def has(identifier: str, severity: str | None = None) -> bool:
        return any(item["id"] == identifier and (severity is None or item["severity"] == severity) for item in findings)

    specs = {
        "collection_stopped": ("critical", has("collection_stopped", "error"), "Collection produced no successful run inside the expected window."),
        "database_unavailable": ("critical", has("database_unavailable", "error"), "The database readiness check failed."),
        "imports_repeatedly_fail": ("critical", has("imports_repeatedly_fail", "error"), "Canonical imports are failing repeatedly."),
        "stale_source_percentage_spike": (
            "warning",
            has("stale_source_ratio", "warning") or has("all_sources_stale", "error"),
            "The share of stale enabled sources is above the guardrail.",
        ),
        "extractor_failure_rate_spike": ("warning", has("extractor_failure_rate", "warning"), "The extraction failure rate is above the guardrail."),
        "canonical_validation_failed": ("critical", has("canonical_validation_failed", "error"), "A canonical dataset document failed validation."),
        "public_verified_dataset_empty": ("critical", has("public_verified_dataset_empty", "error"), "The public verified statement set dropped to empty."),
    }
    alerts = []
    for identifier in load_catalog()["labels"]["alert"]:
        severity, firing, summary = specs[identifier]
        alerts.append({"id": identifier, "severity": severity, "firing": firing, "summary": summary})
    return alerts


def _counts(snapshot) -> dict:
    reviews = snapshot["statements_by_review"]
    collection = snapshot["collection"]
    return {
        "cohort_size": snapshot["cohort_size"],
        "source_count": snapshot["source_count"],
        "human_verified": reviews["human_verified"],
        "machine_validated": reviews["machine_validated"],
        "collection_succeeded": collection["succeeded"],
        "collection_rate_limited": collection["rate_limited"],
        "statements": _statement_total(snapshot),
    }


def _summary(report) -> str:
    errors = sum(1 for item in report["findings"] if item["severity"] == "error")
    warnings = sum(1 for item in report["findings"] if item["severity"] == "warning")
    info = sum(1 for item in report["findings"] if item["severity"] == "info")
    lines = [f"quality check ({report['scope']}): {'ok' if report['ok'] else 'failed'}", f"errors: {errors}", f"warnings: {warnings}", f"info: {info}", ""]
    for item in report["findings"]:
        lines.append(f"{item['severity']} {item['id']} {item['summary']}")
    lines.append("")
    lines.append("alerts:")
    firing = [alert for alert in report["alerts"] if alert["firing"]]
    lines.append("none firing" if not firing else "")
    for alert in firing:
        lines.append(f"firing {alert['severity']} {alert['id']} {alert['summary']}")
    return "\n".join(line for line in lines if line is not None)


def _defaults(as_of: str) -> dict:
    return {
        "as_of": as_of,
        "dataset_present": False,
        "dataset_kind": "unknown",
        "dataset_generated_at": None,
        "latest_successful_observation": None,
        "database_checked": True,
        "readiness": {"database": True},
        "canonical_valid": True,
        "import_failure_streak": 0,
        "collection_window_hours": 168,
        "cohort_size": 0,
        "people_with_non_academic_source": 0,
        "statement_bearing_people": 0,
        "source_count": 0,
        "enabled_source_count": 0,
        "sources_due": 0,
        "sources_stale": 0,
        "sources_never_successful": 0,
        "statements_by_review": {"unreviewed": 0, "machine_validated": 0, "human_verified": 0, "rejected": 0, "needs_review": 0},
        "freshness": {"current": 0, "aging": 0, "stale": 0, "never_checked": 0},
        "enabled_freshness": {"current": 0, "aging": 0, "stale": 0, "never_checked": 0},
        "stale_by_source_type": {},
        "never_successful_by_source_type": {},
        "collection": {
            "attempted": 0,
            "succeeded": 0,
            "failed": 0,
            "unchanged": 0,
            "changed": 0,
            "new": 0,
            "rate_limited": 0,
            "failures_by_class": {},
            "runs_by_adapter": {},
            "failures_by_adapter": {},
            "rate_limits_by_adapter": {},
        },
        "extraction": {
            "items_processed": 0,
            "failures": 0,
            "candidates": 0,
            "candidates_by_type": {"explicit_numeric": 0, "explicit_qualitative": 0, "model_inferred_signal": 0},
            "missing_horizon": 0,
            "missing_definition": 0,
            "explicit_numeric": 0,
        },
        "integrity": {
            "duplicate_identity_ids": 0,
            "multiple_current_versions": 0,
            "human_verified_missing_evidence": 0,
            "numeric_without_numeric_evidence": 0,
            "impossible_probability": 0,
            "public_statement_unavailable_source": 0,
        },
        "slo": {"cadence_eligible": 0, "cadence_met": 0, "statement_bearing_sources": 0, "statement_bearing_sources_fresh": 0},
    }


def _dataset_state(snapshot) -> str:
    if not snapshot["dataset_present"]:
        return "not_loaded"
    enabled = snapshot["enabled_source_count"]
    if enabled == 0:
        return "unknown"
    fresh = snapshot["enabled_freshness"]
    if fresh["current"] / enabled >= 0.8:
        return "current"
    if (fresh["current"] + fresh["aging"]) / enabled >= 0.8:
        return "aging"
    return "stale"


def _drop(identifier, label, baseline, current, limit, findings) -> None:
    if baseline is None or baseline <= 0 or current >= baseline:
        return
    drop = (baseline - current) / baseline
    if drop > limit:
        findings.append(_finding(identifier, "warning", f"{label} fell from {baseline} to {current}.", current))


def _greater(current: int, baseline) -> bool:
    return baseline is not None and current > baseline


def _statement_total(snapshot) -> int:
    reviews = snapshot["statements_by_review"]
    return sum(reviews.values())


def _finding(identifier, severity, summary, count) -> dict:
    return {"id": identifier, "severity": severity, "summary": summary, "count": count}


def _parse(value: str) -> float | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp() * 1000


def _hours(timestamp, as_of) -> float | None:
    if not timestamp:
        return None
    start = _parse(str(timestamp))
    end = _parse(str(as_of))
    if start is None or end is None:
        return None
    return (end - start) / 3_600_000


def _freshness(timestamp, as_of) -> str:
    if not timestamp:
        return "never_checked"
    days = _hours(timestamp, as_of)
    if days is None:
        return "never_checked"
    days = days / 24
    catalog = load_catalog()["freshness_days"]
    if days <= catalog["current"]:
        return "current"
    if days <= catalog["aging"]:
        return "aging"
    return "stale"
