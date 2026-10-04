"""Score the source-to-statement path against a fixed corpus.

The score is errors by class. Emitting more statements is not a better result.
"""

from __future__ import annotations

import json
from pathlib import Path

import inspect

from pdoom_pipeline.belief import pages as page_mod
from pdoom_pipeline.belief.collect import collect_beliefs
from pdoom_pipeline.extract.statements import extract_statements
from pdoom_pipeline.fetch import USER_AGENT

CORPUS_PATH = Path("data/fixtures/evaluation/source-statement-review.json")
CLASSES = (
    "wrong_speaker",
    "third_party_quote",
    "negation",
    "hypothetical",
    "multiple_speakers",
    "multiple_timestamps",
    "timezone_offset",
    "numeric_range",
    "condition",
    "relative_horizon",
    "duplicate_passage",
    "hostile_text",
    "robots_policy",
)


def load_corpus(path: Path | None = None) -> dict:
    return json.loads((path or CORPUS_PATH).read_text(encoding="utf-8"))


def evaluate_corpus(corpus: dict | None = None) -> dict:
    document = corpus or load_corpus()
    cases = []
    for case in document["cases"]:
        actual = _run(case)
        errors = _errors(case, actual)
        cases.append(
            {
                "id": case["id"],
                "class": case["class"],
                "ok": not errors,
                "errors": errors,
                "actual": actual,
            }
        )
    by_class: dict[str, int] = {name: 0 for name in CLASSES}
    for row in cases:
        by_class[row["class"]] = by_class.get(row["class"], 0) + len(row["errors"])
    return {
        "schema_version": "source-statement-review-eval/1",
        "errors_by_class": by_class,
        "error_total": sum(by_class.values()),
        "case_count": len(cases),
        "failed_cases": sum(1 for row in cases if not row["ok"]),
        "cases": cases,
    }


def _robots_allows(body: str, path: str) -> bool:
    signature = inspect.signature(page_mod.robots_allows)
    if "user_agent" in signature.parameters:
        return page_mod.robots_allows(body, path, user_agent=USER_AGENT)
    return page_mod.robots_allows(body, path)


def _run(case: dict) -> dict:
    mode = case["mode"]
    if mode == "extract":
        return _extract(case["text"])
    if mode == "essay":
        return _essay(case)
    if mode == "transcript":
        return _transcript(case)
    if mode == "timezone":
        utc = page_mod.published_time(case["raw"])
        zone_fn = getattr(page_mod, "published_timezone", None)
        return {"utc": utc, "timezone": zone_fn(case["raw"]) if zone_fn else None}
    if mode == "robots":
        allows = _robots_allows(case["robots"], case["path"])
        return {"allows": allows}
    raise ValueError(f"unknown evaluation mode: {mode}")


def _extract(text: str) -> dict:
    rows = extract_statements(text)
    return _statement_view(rows, admitted=bool(rows))


def _essay(case: dict) -> dict:
    person = {"slug": "ada-lovelace", "display_name": "Ada Lovelace", "name_distinctiveness": "high"}
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        if url.endswith("/robots.txt"):
            return b"User-agent: *\nDisallow:\n"
        return case["html"].encode()

    result = collect_beliefs(
        people=[person],
        leads=[{"kind": "essay", "person_slug": person["slug"], "name": "Notes", "url": case["url"], "source_type": "blog"}],
        fetch_bytes=fetch,
        observed_at="2026-09-26T00:00:00Z",
        priority_slugs={person["slug"]},
    )
    view = _statement_view(result["statements"], admitted=bool(result["observations"]))
    if result["observations"]:
        view["role"] = result["observations"][0].get("role")
        view["ownership"] = result["observations"][0].get("ownership")
        view["source_type"] = result["observations"][0].get("source_type")
        view["roles_present"] = sorted({row.get("role") for row in result["observations"][0].get("participants") or []})
    view["fetched"] = fetched
    view["error_classes"] = sorted({row.get("error_class") for row in result["runs"] if row.get("error_class")})
    return view


def _transcript(case: dict) -> dict:
    person = {"slug": "ada-lovelace", "display_name": "Ada Lovelace", "name_distinctiveness": "high"}
    fetched: list[str] = []
    feed = f"""<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Ada Lovelace on machines</title><link>{case["episode_url"]}</link>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate><description>show notes</description>
      <transcript url="{case["transcript_url"]}"/></item></channel></rss>"""

    def fetch(url: str) -> bytes:
        fetched.append(url)
        if url.endswith("/robots.txt"):
            return case["robots"].encode()
        if url == case["url"]:
            return feed.encode()
        if url == case["transcript_url"]:
            return case["transcript"].encode()
        return b""

    result = collect_beliefs(
        people=[person],
        leads=[{
            "kind": "show_feed",
            "show_slug": "show-example",
            "name": "Example Show",
            "url": case["url"],
            "source_type": "podcast",
            "pages": 1,
        }],
        fetch_bytes=fetch,
        observed_at="2026-09-26T00:00:00Z",
        priority_slugs=set(),
    )
    view = _statement_view(result["statements"], admitted=bool(result["observations"]))
    if result["observations"]:
        item = result["observations"][0]
        view["role"] = item.get("role")
        view["ownership"] = item.get("ownership")
        view["source_type"] = item.get("source_type")
        view["roles_present"] = sorted({row.get("role") for row in item.get("participants") or [] if row.get("role")})
    view["fetched_transcript"] = case["transcript_url"] in fetched
    view["error_classes"] = sorted({row.get("error_class") for row in result["runs"] if row.get("error_class")})
    return view


def _statement_view(rows: list[dict], *, admitted: bool) -> dict:
    horizons = [row.get("horizon_text") for row in rows]
    return {
        "admitted": admitted,
        "statement_count": len(rows),
        "values": [row.get("value_numeric") for row in rows if row.get("value_numeric") is not None],
        "horizons": horizons,
        "distinct_horizons": sorted({horizon for horizon in horizons if horizon}),
        "question_keys": [row.get("question_key") for row in rows],
        "question_key": rows[0].get("question_key") if len(rows) == 1 else None,
        "value_numeric": rows[0].get("value_numeric") if len(rows) == 1 else None,
        "value_min": rows[0].get("value_min") if len(rows) == 1 else None,
        "value_max": rows[0].get("value_max") if len(rows) == 1 else None,
        "value_type": rows[0].get("value_type") if len(rows) == 1 else None,
        "unit": rows[0].get("unit") if len(rows) == 1 else None,
        "horizon_text": rows[0].get("horizon_text") if len(rows) == 1 else None,
        "target_date_end": rows[0].get("target_date_end") if len(rows) == 1 else None,
        "condition_text": rows[0].get("condition_text") if len(rows) == 1 else None,
        "start_ms": [row.get("start_ms") for row in rows],
        "review_states": [row.get("review_state") for row in rows],
        "evidence": [row.get("evidence_text") or "" for row in rows],
        "context": [row.get("context_text") or "" for row in rows],
        "role": rows[0].get("role") if len(rows) == 1 else None,
    }


def _errors(case: dict, actual: dict) -> list[str]:
    expect = case["expect"]
    errors = []

    def check(name: str, ok: bool, detail: str) -> None:
        if not ok:
            errors.append(f"{name}: {detail}")

    if "admitted" in expect:
        check("admitted", actual.get("admitted") is expect["admitted"], f"expected {expect['admitted']} got {actual.get('admitted')}")
    if "statement_count" in expect:
        check("statement_count", actual.get("statement_count") == expect["statement_count"], f"expected {expect['statement_count']} got {actual.get('statement_count')}")
    if "min_statements" in expect:
        check("min_statements", actual.get("statement_count", 0) >= expect["min_statements"], f"expected at least {expect['min_statements']} got {actual.get('statement_count')}")
    if "question_key" in expect:
        check("question_key", actual.get("question_key") == expect["question_key"], f"expected {expect['question_key']} got {actual.get('question_key')}")
    if "value_numeric" in expect:
        check("value_numeric", actual.get("value_numeric") == expect["value_numeric"], f"expected {expect['value_numeric']} got {actual.get('value_numeric')}")
    if "value_min" in expect:
        check("value_min", actual.get("value_min") == expect["value_min"], f"expected {expect['value_min']} got {actual.get('value_min')}")
    if "value_max" in expect:
        check("value_max", actual.get("value_max") == expect["value_max"], f"expected {expect['value_max']} got {actual.get('value_max')}")
    if "value_type" in expect:
        check("value_type", actual.get("value_type") == expect["value_type"], f"expected {expect['value_type']} got {actual.get('value_type')}")
    if "unit" in expect:
        check("unit", actual.get("unit") == expect["unit"], f"expected {expect['unit']} got {actual.get('unit')}")
    if "horizon_text" in expect:
        check("horizon_text", actual.get("horizon_text") == expect["horizon_text"], f"expected {expect['horizon_text']} got {actual.get('horizon_text')}")
    if "target_date_end" in expect:
        check("target_date_end", actual.get("target_date_end") == expect["target_date_end"], f"expected {expect['target_date_end']} got {actual.get('target_date_end')}")
    if "condition_contains" in expect:
        text = actual.get("condition_text") or ""
        check("condition_contains", expect["condition_contains"] in text, f"{expect['condition_contains']!r} not in {text!r}")
    if "values" in expect:
        check("values", sorted(actual.get("values") or [], key=_sort_key) == sorted(expect["values"], key=_sort_key), f"expected {expect['values']} got {actual.get('values')}")
    if "excluded_values" in expect:
        present = set(actual.get("values") or [])
        leaked = [value for value in expect["excluded_values"] if value in present]
        check("excluded_values", not leaked, f"attributed someone else's numbers {leaked}")
    if "distinct_horizons" in expect:
        check("distinct_horizons", set(actual.get("distinct_horizons") or []) == set(expect["distinct_horizons"]), f"expected {expect['distinct_horizons']} got {actual.get('distinct_horizons')}")
    if "start_ms" in expect:
        check("start_ms", sorted([item for item in actual.get("start_ms") or []], key=_sort_key) == sorted(expect["start_ms"], key=_sort_key), f"expected {expect['start_ms']} got {actual.get('start_ms')}")
    if "context_contains" in expect:
        blob = " ".join(actual.get("context") or [])
        check("context_contains", expect["context_contains"] in blob, f"{expect['context_contains']!r} missing from context")
    if "evidence_excludes" in expect:
        blob = " ".join(actual.get("evidence") or [])
        check("evidence_excludes", expect["evidence_excludes"] not in blob, f"evidence still contains {expect['evidence_excludes']!r}")
    if "review_states_exclude" in expect:
        leaked = [state for state in actual.get("review_states") or [] if state in expect["review_states_exclude"]]
        check("review_states_exclude", not leaked, f"machine path set {leaked}")
    if "role" in expect:
        check("role", actual.get("role") == expect["role"], f"expected role {expect['role']} got {actual.get('role')}")
    if "ownership" in expect:
        check("ownership", actual.get("ownership") == expect["ownership"], f"expected ownership {expect['ownership']} got {actual.get('ownership')}")
    if "source_type" in expect:
        check("source_type", actual.get("source_type") == expect["source_type"], f"expected source_type {expect['source_type']} got {actual.get('source_type')}")
    if "roles_present" in expect:
        check("roles_present", set(expect["roles_present"]) <= set(actual.get("roles_present") or []), f"expected roles {expect['roles_present']} got {actual.get('roles_present')}")
    if "utc" in expect:
        check("utc", actual.get("utc") == expect["utc"], f"expected {expect['utc']} got {actual.get('utc')}")
    if "timezone" in expect:
        check("timezone", actual.get("timezone") == expect["timezone"], f"expected {expect['timezone']} got {actual.get('timezone')}")
    if "allows" in expect:
        check("allows", actual.get("allows") is expect["allows"], f"expected allows={expect['allows']} got {actual.get('allows')}")
    if "fetched_transcript" in expect:
        check("fetched_transcript", actual.get("fetched_transcript") is expect["fetched_transcript"], f"expected fetched_transcript={expect['fetched_transcript']} got {actual.get('fetched_transcript')}")
    if "error_class" in expect:
        check("error_class", expect["error_class"] in (actual.get("error_classes") or []), f"expected {expect['error_class']} in {actual.get('error_classes')}")
    return errors


def _sort_key(value):
    return (value is None, str(value))


def main() -> None:
    report = evaluate_corpus()
    print(json.dumps({"errors_by_class": report["errors_by_class"], "error_total": report["error_total"], "failed_cases": report["failed_cases"]}, indent=2))


if __name__ == "__main__":
    main()
