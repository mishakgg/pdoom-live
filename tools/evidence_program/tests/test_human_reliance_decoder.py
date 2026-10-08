"""Self-authored synthetic task tests; no real workbook or participant rows."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from decode_okamura_decisions import (
    BIT_SCHEMA_STATUS, CHECKPOINTS, GROUPS, MAX_ROWS, METRICS, SCHEMA, STUDY_ID,
    decode_code, summarize_synthetic,
)


def fixture():
    rows = [{"row_key": index + 1, "group": group, "completion_status": "complete",
             "checkpoints": [(index * 5 + checkpoint) % 32 for checkpoint in range(15)]}
            for index, group in enumerate(GROUPS)]
    rows += [{"row_key": 6, "group": "NoTCC", "completion_status": "excluded",
              "checkpoints": [0, 19, None, "", " "] + [None] * 10},
             {"row_key": 7, "group": "Visual", "completion_status": "excluded",
              "checkpoints": [31] * 15}]
    return {"schema_version": SCHEMA, "input_kind": "synthetic_fixture",
            "study_id": STUDY_ID, "rows": rows}


class DecoderTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def reject(self, path, value):
        document = deepcopy(self.data)
        current = document
        for key in path[:-1]:
            current = current[key]
        current[path[-1]] = value
        with self.assertRaises(ValueError):
            summarize_synthetic(document)

    def test_exhaustive_32_inherited_bit_patterns(self):
        for code in range(32):
            decoded = decode_code(code)
            # Expected order is a provisional contract, not source verification.
            expected = tuple(character == "1" for character in format(code, "05b"))
            self.assertEqual(tuple(decoded.values()), expected)
            self.assertTrue(all(type(value) is bool for value in decoded.values()))

    def test_code_19_keeps_both_raw_flags(self):
        self.assertEqual(decode_code(19), {
            "automatic_mode_raw": True, "judgment_positive_raw": False,
            "ground_truth_positive_raw": False, "overtrust_flag_raw": True,
            "tcc_flag_raw": True})

    def test_zero_is_valid_and_blank_is_missing(self):
        self.assertEqual(set(decode_code(0).values()), {False})
        for blank in (None, "", " ", "\t\r\n"):
            self.assertIsNone(decode_code(blank))
        self.data["rows"][0]["checkpoints"] = [0] * 15
        result = summarize_synthetic(self.data)["by_group"][0]
        self.assertEqual(result["decision_count"], 15)
        self.assertEqual(result["judgment_matches_truth"], 15)
        self.assertEqual(result["manual_decisions"], 15)

    def test_strict_code_types_and_range(self):
        for value in (True, False, -1, 32, 1 << 200, 0.0, 19.0, 0.5,
                      float("nan"), float("inf"), float("-inf"),
                      "0", "19", "0x13", "NaN", "\u00a0", "\x00", "\ud800",
                      " " * 129, [], {}, object()):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                decode_code(value)

    def test_populations_and_excluded_cells_are_separate(self):
        result = summarize_synthetic(self.data)
        self.assertEqual(result["population"], {"recruited_rows": 7, "completer_rows": 5, "excluded_rows": 2})
        self.assertEqual(result["author_population_counts"]["decision_count"], 75)
        self.assertEqual(result["excluded_rows_audit"], {"recorded_checkpoints": 17, "missing_checkpoints": 13})
        self.assertEqual(result["by_group"][0]["recruited_rows"], 2)
        self.assertEqual(result["by_group"][0]["completer_rows"], 1)
        self.assertEqual(result["by_group"][0]["excluded_rows"], 1)

    def test_excluded_valid_decisions_never_enter_author_totals(self):
        first = summarize_synthetic(self.data)
        self.data["rows"][6]["checkpoints"] = [0] * 15
        second = summarize_synthetic(self.data)
        self.assertEqual(first, second)

    def test_every_complete_checkpoint_required(self):
        for blank in (None, "", " "):
            self.reject(["rows", 0, "checkpoints", 0], blank)

    def test_invalid_excluded_values_are_not_silently_skipped(self):
        self.reject(["rows", 5, "checkpoints", 0], 32)
        self.reject(["rows", 5, "checkpoints", 0], True)

    def test_no_completers_is_empty_author_population(self):
        for row in self.data["rows"]:
            row["completion_status"] = "excluded"
        result = summarize_synthetic(self.data)
        self.assertEqual(result["population"]["completer_rows"], 0)
        self.assertTrue(all(value == 0 for value in result["author_population_counts"].values()))

    def test_phase_boundaries_are_6_3_6_within_session(self):
        result = summarize_synthetic(self.data)
        self.assertEqual([(p["period"], p["checkpoint_start"], p["checkpoint_end"], p["decision_count"])
                          for p in result["by_period"]],
                         [("baseline", 1, 6, 30), ("transition", 7, 9, 15),
                          ("later_within_session", 10, 15, 30)])
        self.assertEqual(len(result["by_checkpoint"]), 15)
        self.assertTrue(all(row["decision_count"] == 5 for row in result["by_checkpoint"]))
        self.assertNotIn("retention", json.dumps(result))

    def test_no_tcc_raw_bits_are_not_cue_delivery_or_mental_state(self):
        self.data["rows"][0]["checkpoints"] = [19] * 15
        result = summarize_synthetic(self.data)
        group = result["by_group"][0]
        self.assertEqual(group["raw_tcc_flag_count"], 15)
        self.assertEqual(group["raw_overtrust_flag_count"], 15)
        self.assertEqual(group["judgment_matches_truth"], 15)
        self.assertEqual(result["raw_flag_interpretation"], "operational_bits_not_mental_states_or_actual_cue_delivery")

    def test_all_aggregate_partitions_reconcile(self):
        result = summarize_synthetic(self.data)
        total = result["author_population_counts"]
        for name in ("by_group", "by_checkpoint", "by_period", "by_group_period"):
            for metric in METRICS:
                self.assertEqual(sum(row[metric] for row in result[name]), total[metric])
            for row in result[name]:
                self.assertEqual(row["automatic_decisions"] + row["manual_decisions"], row["decision_count"])
                self.assertEqual(row["judgment_matches_truth"] + row["judgment_differs_truth"], row["decision_count"])
        for group in GROUPS:
            group_row = next(row for row in result["by_group"] if row["group"] == group)
            for metric in METRICS:
                self.assertEqual(sum(row[metric] for row in result["by_group_period"] if row["group"] == group), group_row[metric])

    def test_deterministic_without_mutating_input(self):
        original = deepcopy(self.data)
        first = summarize_synthetic(self.data)
        self.assertEqual(self.data, original)
        self.data["rows"].reverse()
        self.assertEqual(first, summarize_synthetic(self.data))

    def test_output_has_no_ephemeral_row_keys_or_individual_records(self):
        result = json.dumps(summarize_synthetic(self.data))
        for token in ('"row_key"', '"rows"', '"checkpoints"', '"participant_id"', '"completion_status"'):
            self.assertNotIn(token, result)

    def test_provisional_and_synthetic_claims_cannot_be_upgraded(self):
        result = summarize_synthetic(self.data)
        self.assertEqual(result["bit_schema_status"], BIT_SCHEMA_STATUS)
        self.assertEqual(result["actual_source_acceptance"], "blocked")
        for field in ("participant_data_acquired", "source_extraction_performed", "statistical_reanalysis_performed", "canonical_import_enabled"):
            self.assertIs(result[field], False)
        for field, value in (("input_kind", "manual_aggregate"), ("study_id", "10.1371/journal.pone.0229132"), ("schema_version", "verified-v1")):
            self.reject([field], value)

    def test_duplicate_row_keys_even_identical_rejected(self):
        self.data["rows"].append(deepcopy(self.data["rows"][0]))
        with self.assertRaises(ValueError):
            summarize_synthetic(self.data)

    def test_duplicate_row_key_across_groups_rejected(self):
        self.reject(["rows", 1, "row_key"], 1)

    def test_row_key_is_bounded_integer_and_never_real_identity_text(self):
        for value in (0, -1, MAX_ROWS + 1, True, 1.0, "1", "someone@example.com", "Alice", None):
            self.reject(["rows", 0, "row_key"], value)

    def test_unknown_and_missing_fields_at_both_object_levels(self):
        for path in ([], ["rows", 0]):
            for field in ("name", "demographics", "belief", "actual_cue_displayed", "source_url", "participant_id", "extra"):
                document = deepcopy(self.data)
                current = document
                for key in path:
                    current = current[key]
                current[field] = "forbidden"
                with self.subTest(path=path, field=field), self.assertRaises(ValueError):
                    summarize_synthetic(document)
            document = deepcopy(self.data)
            current = document
            for key in path:
                current = current[key]
            del current[next(iter(current))]
            with self.assertRaises(ValueError):
                summarize_synthetic(document)

    def test_no_arbitrary_group_or_status_text(self):
        for group in ("visual", "Other", "NoTCC<script>", "NoTCC\n", "Anthro", "", None, 1, []):
            self.reject(["rows", 0, "group"], group)
        for status in ("partial", "recruited", "survivor", "", None, 1, []):
            self.reject(["rows", 0, "completion_status"], status)

    def test_exact_checkpoint_slots(self):
        for cells in ([0] * 14, [0] * 16, {}, (), None):
            self.reject(["rows", 0, "checkpoints"], cells)

    def test_row_boundaries(self):
        self.reject(["rows"], [])
        self.reject(["rows"], [self.data["rows"][0]] * (MAX_ROWS + 1))
        self.data["rows"] = [{"row_key": key, "group": "NoTCC", "completion_status": "complete", "checkpoints": [0] * CHECKPOINTS}
                             for key in range(1, MAX_ROWS + 1)]
        self.assertEqual(summarize_synthetic(self.data)["author_population_counts"]["decision_count"], MAX_ROWS * 15)

    def test_cyclic_deep_nonjson_and_oversized_input(self):
        cycle = {}; cycle["cycle"] = cycle
        for value in (cycle, {"x": [None] * 40001}, {"x": "x" * 129}, {"x": "é" * 65},
                      {"x": "\ud800"}, {False: 1}, {"x": object()}, None, [], {}, "data"):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                summarize_synthetic(value)

    def test_no_io_network_or_execution(self):
        with patch("builtins.open", side_effect=AssertionError("file I/O forbidden")), \
             patch("socket.socket", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.run", side_effect=AssertionError("execution forbidden")):
            summarize_synthetic(self.data)


if __name__ == "__main__":
    unittest.main()
