"""Bounded in-process metrics for collection and extraction events."""

from __future__ import annotations

from pdoom_pipeline.observability.catalog import allowed, load_catalog

_counters: dict[tuple, float] = {}


def reset_metrics() -> None:
    _counters.clear()


def normalize_adapter(value: str | None) -> str:
    text = (value or "").lower()
    if "openalex" in text:
        return "openalex"
    if "arxiv" in text:
        return "arxiv"
    if "github" in text:
        return "github"
    if "rss" in text or "atom" in text:
        return "rss"
    if "fixture" in text or "synthetic" in text:
        return "fixture"
    if "sitemap" in text:
        return "sitemap"
    if "manual" in text:
        return "manual"
    if "api" in text:
        return "api"
    return "other"


def record_counter(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    catalog = load_catalog()
    known = {metric["name"]: metric for metric in catalog["metrics"]}
    if name not in known:
        name = "pdoom_collection_failures"
        labels = {"adapter": "other", "failure_class": "unclassified"}
    spec = known[name]
    safe: dict[str, str] = {}
    groups = {
        "adapter": "adapter",
        "outcome": "outcome",
        "failure_class": "failure_class",
        "statement_type": "statement_type",
        "source_type": "source_type",
        "review_state": "review_state",
        "state": "state",
    }
    for key in spec["labels"]:
        raw = (labels or {}).get(key)
        group = groups.get(key, key)
        fallback = "unclassified" if key == "failure_class" else "unknown" if key == "error_class" else "other"
        safe[key] = allowed(group, raw, fallback)
    _counters[(name, tuple(sorted(safe.items())))] = _counters.get((name, tuple(sorted(safe.items()))), 0) + value


def render() -> str:
    lines = []
    for (name, labels), value in sorted(_counters.items()):
        if labels:
            body = ",".join(f'{key}="{_escape(val)}"' for key, val in labels)
            lines.append(f"{name}{{{body}}} {value}")
        else:
            lines.append(f"{name} {value}")
    return "\n".join(lines) + ("\n" if lines else "")


def observe_collection_run(run: dict) -> None:
    adapter = normalize_adapter(str(run.get("adapter") or run.get("collector") or ""))
    status = str(run.get("status") or "")
    record_counter("pdoom_collection_attempted", 1)
    unchanged = _unchanged(run)
    if status == "succeeded":
        record_counter("pdoom_collection_succeeded", 1)
        record_counter("pdoom_collection_runs", 1, {"adapter": adapter, "outcome": "succeeded"})
        record_counter("pdoom_collection_unchanged", unchanged)
        record_counter("pdoom_collection_changed", _num(run.get("changed_count")))
        record_counter("pdoom_collection_new", _num(run.get("new_count")))
    elif status in {"failed", "partial"}:
        record_counter("pdoom_collection_failed", 1)
        record_counter("pdoom_collection_runs", 1, {"adapter": adapter, "outcome": "failed"})
        if status == "partial":
            record_counter("pdoom_collection_unchanged", unchanged)
            record_counter("pdoom_collection_changed", _num(run.get("changed_count")))
            record_counter("pdoom_collection_new", _num(run.get("new_count")))
        failure = allowed("failure_class", str(run.get("error_class") or ""), "unclassified")
        record_counter("pdoom_collection_failures", 1, {"adapter": adapter, "failure_class": failure})
        if failure == "rate_limited":
            record_counter("pdoom_collection_rate_limits", 1, {"adapter": adapter})


def observe_extraction(statement_type: str | None, *, failed: bool) -> None:
    record_counter("pdoom_extraction_items_processed", 1)
    if failed:
        record_counter("pdoom_extraction_failures", 1)
    if statement_type:
        record_counter("pdoom_extraction_candidates", 1, {"statement_type": statement_type})


def _unchanged(run: dict) -> float:
    if run.get("unchanged_count") is not None:
        return _num(run.get("unchanged_count"))
    return max(0, _num(run.get("observed_count")) - _num(run.get("new_count")) - _num(run.get("changed_count")))


def _num(value: object) -> float:
    try:
        return float(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "").replace('"', "")
