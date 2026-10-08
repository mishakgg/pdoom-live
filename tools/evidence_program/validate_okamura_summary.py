"""Validate a manually transcribed Okamura paper aggregate or synthetic ledger.

Pure in-memory consistency checks, not extraction, participant-data reading,
workbook acceptance, bit-schema verification, reanalysis, or source admission.
Manual paper counts and synthetic examples never validate one another.
"""
from __future__ import annotations

SCHEMA = "okamura-paper-aggregate-ledger-v1"
DOI = "10.1371/journal.pone.0229132"
SYNTHETIC_DOI = "10.0000/synthetic-okamura"
GROUPS = ("NoTCC", "Visual", "Audio", "Verbal", "Anthro.")
MAX_DEPTH = 8
MAX_NODES = 1024
MAX_TEXT_BYTES = 256
MAX_COUNT = 100000
FACTUAL_COUNTS = {"recruited": 194, "completers": 116, "excluded": 78,
                  "decisions": 1740, "correct": 1282, "automatic": 1236, "manual": 504}
FACTUAL_GROUPS = {"NoTCC": 28, "Visual": 18, "Audio": 22, "Verbal": 29, "Anthro.": 19}
COUNT_KEYS = tuple(FACTUAL_COUNTS)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, expected, label):
    _require(type(value) is dict and set(value) == set(expected.split()),
             label + ": missing, unknown or invalid fields")


def _bounded(document):
    nodes = 0

    def walk(value, depth):
        nonlocal nodes
        nodes += 1
        _require(nodes <= MAX_NODES and depth <= MAX_DEPTH, "ledger size/depth limit")
        _require(type(value) in (dict, list, str, int, bool, type(None)), "non-JSON value")
        if type(value) is str:
            try:
                size = len(value.encode("utf-8"))
            except UnicodeError as exc:
                raise ValueError("invalid Unicode") from exc
            _require(size <= MAX_TEXT_BYTES and not any(ord(c) < 32 or ord(c) == 127 for c in value),
                     "invalid or excessive text")
        elif type(value) is int:
            _require(0 <= value <= MAX_COUNT, "integer limit")
        elif type(value) is dict:
            for key, item in value.items():
                _require(type(key) is str, "non-string key")
                walk(key, depth + 1)
                walk(item, depth + 1)
        elif type(value) is list:
            for item in value:
                walk(item, depth + 1)
    walk(document, 0)


def _count(value):
    _require(type(value) is int and 0 <= value <= MAX_COUNT, "count must be a bounded nonnegative integer")
    return value


def validate_summary(document):
    """Check one study's paper counts and return aggregate-only confirmation.

    The manual profile is pinned to separately reviewed published totals. The
    synthetic profile uses a reserved fictional DOI and freely varying bounded
    counts subject to the same arithmetic. Passing confirms this narrow ledger,
    not an independently reproduced participant-data result or causal finding.
    """
    _bounded(document)
    _keys(document, "schema_version input_kind source measurement counts groups boundaries", "ledger")
    _require(document["schema_version"] == SCHEMA, "unsupported schema")
    kind = document["input_kind"]
    _require(type(kind) is str and kind in ("manual_aggregate", "synthetic_fixture"), "invalid input kind")
    real = kind == "manual_aggregate"
    source = document["source"]
    _keys(source, "doi url publication_date observed_date locator artifact_sha256 capture_status", "source")
    expected_source = {
        "doi": DOI if real else SYNTHETIC_DOI,
        "url": "https://doi.org/" + DOI if real else "https://example.invalid/synthetic-okamura",
        "publication_date": "2020-02-21" if real else "2000-01-01",
        "observed_date": "2026-10-08" if real else "2000-01-02",
        "locator": "Materials and methods / Participants; Procedure; Results; Performance: Sensitivity d-prime and accuracy" if real else "Synthetic aggregate example",
        "artifact_sha256": None,
        "capture_status": "manual_transcription_not_source_extraction" if real else "synthetic_fixture",
    }
    _require(source == expected_source, "source identity, date, locator or capture boundary mismatch")
    measurement = document["measurement"]
    _keys(measurement, "analysis_population checkpoint_count time_window evidence_class", "measurement")
    _require(type(measurement["checkpoint_count"]) is int and measurement == {
        "analysis_population": "completers_only", "checkpoint_count": 15,
        "time_window": "within_session_first_15_checkpoints",
        "evidence_class": "published_task_performance_aggregate" if real else "synthetic_task_performance_aggregate",
    }, "measurement or denominator boundary mismatch")
    boundaries = document["boundaries"]
    _keys(boundaries, "participant_data_acquired source_extraction_performed statistical_reanalysis_performed canonical_import_enabled workbook_acceptance bit_schema_verification", "boundaries")
    for key in ("participant_data_acquired", "source_extraction_performed",
                "statistical_reanalysis_performed", "canonical_import_enabled"):
        _require(boundaries[key] is False, "prohibited operational claim")
    _require(boundaries["workbook_acceptance"] == "blocked" and
             boundaries["bit_schema_verification"] == "not_established_by_paper_aggregates",
             "paper aggregates do not validate the source workbook or bit schema")
    records = document["counts"]
    _require(type(records) is list and len(records) == len(COUNT_KEYS), "exactly seven count assertions required")
    counts = {}
    for row in records:
        _keys(row, "metric count", "count assertion")
        metric = row["metric"]
        _require(type(metric) is str and metric in COUNT_KEYS and metric not in counts,
                 "unknown or duplicate count assertion")
        counts[metric] = _count(row["count"])
    groups = document["groups"]
    _require(type(groups) is list and len(groups) == len(GROUPS), "exactly five group counts required")
    group_counts = {}
    for row in groups:
        _keys(row, "group completers", "group assertion")
        group = row["group"]
        _require(type(group) is str and group in GROUPS and group not in group_counts,
                 "unknown or duplicate group assertion")
        group_counts[group] = _count(row["completers"])
    _require(counts["recruited"] == counts["completers"] + counts["excluded"], "recruit population does not reconcile")
    _require(sum(group_counts.values()) == counts["completers"], "group completers do not reconcile")
    _require(counts["decisions"] == counts["completers"] * 15, "decisions must use completers-only denominator")
    _require(counts["automatic"] + counts["manual"] == counts["decisions"], "decision-mode partition does not reconcile")
    _require(counts["correct"] <= counts["decisions"], "correct decisions exceed decision denominator")
    if real:
        _require(counts == FACTUAL_COUNTS and group_counts == FACTUAL_GROUPS, "reviewed paper counts changed")
    return {
        "input_kind": kind,
        "study_count": 1,
        "count_assertion_count": 7,
        "group_assertion_count": 5,
        "counts": {name: counts[name] for name in COUNT_KEYS},
        "groups": [{"group": name, "completers": group_counts[name]} for name in GROUPS],
        "incorrect_decisions_derived": counts["decisions"] - counts["correct"],
        "analysis_population": "completers_only",
        "time_window": "within_session_first_15_checkpoints",
        "validation_scope": "manual_aggregate_consistency_only" if real else "synthetic_consistency_only",
        "source_byte_hash_verified": False,
        **boundaries,
    }
