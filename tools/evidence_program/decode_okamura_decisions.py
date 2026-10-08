"""Provisional five-bit arithmetic on synthetic task rows, entirely in memory.

The bit mapping is a provisional convention inferred from the earlier field
order and code19 example, NOT independently checked
against the unavailable workbook dictionary. This is not a workbook reader or
source acceptance. No participant data, file I/O, network, execution, fitting,
identity linkage, or canonical import is performed. Only aggregate reports leave
summarize_synthetic; ephemeral integer row keys are neither returned nor logged.

NoTCC flags retain their raw operational meaning. Neither raw flag determines a
person's mental state or whether a cue was actually displayed. Checkpoints are
within one session, not delayed retention or independent participant samples.
"""
from __future__ import annotations

SCHEMA = "synthetic-okamura-decisions-v1"
STUDY_ID = "synthetic-okamura-task"
BIT_SCHEMA_STATUS = "inherited_unverified_source_schema"
GROUPS = ("NoTCC", "Visual", "Audio", "Verbal", "Anthro.")
PERIODS = (("baseline", 1, 6), ("transition", 7, 9), ("later_within_session", 10, 15))
CHECKPOINTS = 15
MAX_ROWS = 512
MAX_DEPTH = 6
MAX_NODES = 40000
MAX_TEXT_BYTES = 128
BIT_MASKS = (
    ("automatic_mode_raw", 16),
    ("judgment_positive_raw", 8),
    ("ground_truth_positive_raw", 4),
    ("overtrust_flag_raw", 2),
    ("tcc_flag_raw", 1),
)
METRICS = (
    "decision_count", "automatic_decisions", "manual_decisions",
    "judgment_matches_truth", "judgment_differs_truth",
    "judgment_positive_count", "ground_truth_positive_count",
    "raw_overtrust_flag_count", "raw_tcc_flag_count",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, expected, label):
    _require(type(value) is dict and set(value) == set(expected.split()),
             label + ": missing, unknown or invalid fields")


def _bounded(document):
    count = 0

    def walk(value, depth):
        nonlocal count
        count += 1
        _require(count <= MAX_NODES and depth <= MAX_DEPTH, "input size/depth limit")
        _require(type(value) in (dict, list, str, int, type(None)), "non-JSON or boolean value")
        if type(value) is str:
            try:
                size = len(value.encode("utf-8"))
            except UnicodeError as exc:
                raise ValueError("invalid Unicode") from exc
            _require(size <= MAX_TEXT_BYTES, "text size limit")
        elif type(value) is int:
            _require(0 <= value <= MAX_ROWS, "integer limit")
        elif type(value) is dict:
            for key, item in value.items():
                _require(type(key) is str, "non-string key")
                walk(key, depth + 1)
                walk(item, depth + 1)
        elif type(value) is list:
            for item in value:
                walk(item, depth + 1)
    walk(document, 0)


def decode_code(value):
    """Decode a provisional MSB-first 16/8/4/2/1 convention, never source-verified.

    Zero is valid; None and empty/ASCII-whitespace-only strings mean missing.
    Numeric strings, booleans, floats (even integral), nonfinite values and values
    outside 0..31 fail closed. A returned bit is raw, not a validated inference.
    """
    if value is None:
        return None
    if type(value) is str:
        _require(len(value) <= MAX_TEXT_BYTES and all(c in " \t\r\n" for c in value),
                 "code must be an integer 0..31 or a bounded blank")
        return None
    _require(type(value) is int and 0 <= value <= 31,
             "code must be an integer 0..31 or a bounded blank")
    return {name: bool(value & mask) for name, mask in BIT_MASKS}


def _empty_counts():
    return dict.fromkeys(METRICS, 0)


def _add(counts, bits):
    automatic = bits["automatic_mode_raw"]
    matches = bits["judgment_positive_raw"] == bits["ground_truth_positive_raw"]
    counts["decision_count"] += 1
    counts["automatic_decisions"] += int(automatic)
    counts["manual_decisions"] += int(not automatic)
    counts["judgment_matches_truth"] += int(matches)
    counts["judgment_differs_truth"] += int(not matches)
    counts["judgment_positive_count"] += int(bits["judgment_positive_raw"])
    counts["ground_truth_positive_count"] += int(bits["ground_truth_positive_raw"])
    counts["raw_overtrust_flag_count"] += int(bits["overtrust_flag_raw"])
    counts["raw_tcc_flag_count"] += int(bits["tcc_flag_raw"])


def summarize_synthetic(document):
    """Validate synthetic recruit rows and summarize declared completers only.

    Input has exactly schema_version/input_kind/study_id/rows. Each row has an
    ephemeral integer row_key, fixed group, completion_status complete/excluded,
    and exactly 15 checkpoint cells. A complete row cannot have missing cells.
    Excluded rows can have partial or full task data: no inference about why they
    were excluded is made. Counts of their cells remain outside author totals.
    Group/checkpoint/period output order is fixed, regardless of input ordering.
    """
    _bounded(document)
    _keys(document, "schema_version input_kind study_id rows", "document")
    _require(document["schema_version"] == SCHEMA and
             document["input_kind"] == "synthetic_fixture" and
             document["study_id"] == STUDY_ID, "only fixed synthetic study input is supported")
    rows = document["rows"]
    _require(type(rows) is list and 1 <= len(rows) <= MAX_ROWS, "row count limit")
    total = _empty_counts()
    by_group = {group: _empty_counts() for group in GROUPS}
    by_checkpoint = {checkpoint: _empty_counts() for checkpoint in range(1, CHECKPOINTS + 1)}
    by_period = {period: _empty_counts() for period, _, _ in PERIODS}
    by_group_period = {(group, period): _empty_counts() for group in GROUPS for period, _, _ in PERIODS}
    group_populations = {group: {"recruited_rows": 0, "completer_rows": 0, "excluded_rows": 0} for group in GROUPS}
    row_keys = set()
    complete = excluded_recorded = excluded_missing = 0
    for row in rows:
        _keys(row, "row_key group completion_status checkpoints", "row")
        key = row["row_key"]
        _require(type(key) is int and 1 <= key <= MAX_ROWS and key not in row_keys,
                 "invalid or duplicate ephemeral row key")
        row_keys.add(key)
        group, status = row["group"], row["completion_status"]
        _require(type(group) is str and group in GROUPS, "unknown task group")
        _require(type(status) is str and status in ("complete", "excluded"), "invalid completion status")
        cells = row["checkpoints"]
        _require(type(cells) is list and len(cells) == CHECKPOINTS, "exactly 15 checkpoint cells required")
        decoded = [decode_code(value) for value in cells]
        group_populations[group]["recruited_rows"] += 1
        if status == "excluded":
            group_populations[group]["excluded_rows"] += 1
            excluded_missing += sum(bits is None for bits in decoded)
            excluded_recorded += sum(bits is not None for bits in decoded)
            continue
        _require(all(bits is not None for bits in decoded), "complete row contains missing checkpoints")
        complete += 1
        group_populations[group]["completer_rows"] += 1
        for checkpoint, bits in enumerate(decoded, 1):
            period = next(name for name, start, end in PERIODS if start <= checkpoint <= end)
            for target in (total, by_group[group], by_checkpoint[checkpoint],
                           by_period[period], by_group_period[group, period]):
                _add(target, bits)
    # Author denominators are declared completers only, never all recruits or
    # surviving decisions from excluded rows. Missingness is not coded as zero.
    return {
        "schema_version": "synthetic-okamura-summary-v1",
        "input_kind": "synthetic_fixture",
        "study_id": STUDY_ID,
        "bit_schema_status": BIT_SCHEMA_STATUS,
        "actual_source_acceptance": "blocked",
        "analysis_population": "declared_completers_only",
        "time_window": "within_session_checkpoints_1_to_15",
        "raw_flag_interpretation": "operational_bits_not_mental_states_or_actual_cue_delivery",
        "participant_data_acquired": False,
        "source_extraction_performed": False,
        "statistical_reanalysis_performed": False,
        "canonical_import_enabled": False,
        "population": {"recruited_rows": len(rows), "completer_rows": complete,
                       "excluded_rows": len(rows) - complete},
        "author_population_counts": total,
        "excluded_rows_audit": {"recorded_checkpoints": excluded_recorded,
                                "missing_checkpoints": excluded_missing},
        "by_group": [{"group": group, **group_populations[group], **by_group[group]} for group in GROUPS],
        "by_checkpoint": [{"checkpoint": i, **by_checkpoint[i]} for i in range(1, CHECKPOINTS + 1)],
        "by_period": [{"period": name, "checkpoint_start": start, "checkpoint_end": end,
                       **by_period[name]} for name, start, end in PERIODS],
        "by_group_period": [{"group": group, "period": name, "checkpoint_start": start,
                             "checkpoint_end": end, **by_group_period[group, name]}
                            for group in GROUPS for name, start, end in PERIODS],
    }
