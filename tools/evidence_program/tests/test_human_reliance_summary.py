"""Synthetic aggregate regressions, plus separate hand-curated paper metadata.

No test acquires or reads source participant data or the unavailable workbook.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from validate_okamura_summary import GROUPS, SCHEMA, SYNTHETIC_DOI, validate_summary


def fixture():
    return {
        "schema_version": SCHEMA, "input_kind": "synthetic_fixture",
        "source": {"doi": SYNTHETIC_DOI, "url": "https://example.invalid/synthetic-okamura",
                   "publication_date": "2000-01-01", "observed_date": "2000-01-02",
                   "locator": "Synthetic aggregate example", "artifact_sha256": None,
                   "capture_status": "synthetic_fixture"},
        "measurement": {"analysis_population": "completers_only", "checkpoint_count": 15,
                        "time_window": "within_session_first_15_checkpoints",
                        "evidence_class": "synthetic_task_performance_aggregate"},
        "counts": [{"metric": metric, "count": count} for metric, count in
                   (("recruited", 13), ("completers", 10), ("excluded", 3),
                    ("decisions", 150), ("correct", 99), ("automatic", 90), ("manual", 60))],
        "groups": [{"group": group, "completers": 2} for group in GROUPS],
        "boundaries": {"participant_data_acquired": False, "source_extraction_performed": False,
                       "statistical_reanalysis_performed": False, "canonical_import_enabled": False,
                       "workbook_acceptance": "blocked", "bit_schema_verification": "not_established_by_paper_aggregates"},
    }


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def reject(self, path, value):
        document = deepcopy(self.data)
        current = document
        for key in path[:-1]:
            current = current[key]
        current[path[-1]] = value
        with self.assertRaises(ValueError):
            validate_summary(document)

    def test_valid_synthetic_counts_are_not_source_evidence(self):
        result = validate_summary(self.data)
        self.assertEqual(result["counts"]["decisions"], 150)
        self.assertEqual(result["incorrect_decisions_derived"], 51)
        self.assertEqual(result["validation_scope"], "synthetic_consistency_only")
        self.assertEqual(result["workbook_acceptance"], "blocked")
        self.assertEqual(result["bit_schema_verification"], "not_established_by_paper_aggregates")
        self.assertFalse(result["source_byte_hash_verified"])

    def test_separate_manual_ledger_is_documentary_consistency_only(self):
        ledger = HERE.parents[1] / "data/evidence-program/research/okamura-aggregate-ledger.json"
        result = validate_summary(json.loads(ledger.read_text()))
        self.assertEqual(result["validation_scope"], "manual_aggregate_consistency_only")
        self.assertEqual(result["counts"], {"recruited": 194, "completers": 116, "excluded": 78,
                                           "decisions": 1740, "correct": 1282, "automatic": 1236, "manual": 504})
        self.assertEqual(result["incorrect_decisions_derived"], 458)
        self.assertFalse(result["source_extraction_performed"])

    def test_manual_profile_rejects_coherent_factual_changes(self):
        ledger = HERE.parents[1] / "data/evidence-program/research/okamura-aggregate-ledger.json"
        document = json.loads(ledger.read_text())
        document["counts"][4]["count"] -= 1
        with self.assertRaises(ValueError):
            validate_summary(document)

    def test_order_independent_without_mutation(self):
        original = deepcopy(self.data)
        result = validate_summary(self.data)
        self.assertEqual(self.data, original)
        self.data["counts"].reverse()
        self.data["groups"].reverse()
        self.assertEqual(result, validate_summary(self.data))

    def test_each_count_partition_must_reconcile(self):
        for index in (0, 1, 2, 3, 5, 6):
            self.reject(["counts", index, "count"], self.data["counts"][index]["count"] + 1)
        self.reject(["groups", 0, "completers"], 3)
        self.reject(["counts", 4, "count"], 151)

    def test_zero_counts_preserved(self):
        for row in self.data["counts"]:
            row["count"] = 0
        for row in self.data["groups"]:
            row["completers"] = 0
        result = validate_summary(self.data)
        self.assertEqual(result["counts"]["correct"], 0)
        self.assertEqual(result["incorrect_decisions_derived"], 0)

    def test_counts_reject_bool_float_nonfinite_strings_and_negative(self):
        for value in (True, False, 0.0, 1.5, float("nan"), float("inf"), -1, 100001, "0", "", None, [], {}):
            self.reject(["counts", 0, "count"], value)
            self.reject(["groups", 0, "completers"], value)

    def test_recruit_decisions_cannot_replace_completer_denominator(self):
        document = deepcopy(self.data)
        document["counts"][3]["count"] = 13 * 15
        document["counts"][5]["count"] = 13 * 15 - 60
        with self.assertRaises(ValueError):
            validate_summary(document)

    def test_duplicate_assertions_and_groups_rejected(self):
        self.reject(["counts", 6], deepcopy(self.data["counts"][0]))
        self.reject(["groups", 4], deepcopy(self.data["groups"][0]))
        self.reject(["counts"], self.data["counts"] + [deepcopy(self.data["counts"][0])])
        self.reject(["groups"], self.data["groups"] + [deepcopy(self.data["groups"][0])])
        self.reject(["counts"], self.data["counts"][:-1])
        self.reject(["groups"], self.data["groups"][:-1])

    def test_unknown_assertions_cannot_add_unreviewed_claims(self):
        for metric in ("retention", "population_causal_effect", "overtrust", "tcc_displayed", "anything", None, []):
            self.reject(["counts", 0, "metric"], metric)
        for group in ("Other", "visual", "Alice", None, []):
            self.reject(["groups", 0, "group"], group)

    def test_no_missing_or_arbitrary_fields_at_any_level(self):
        for path in ([], ["source"], ["measurement"], ["counts", 0], ["groups", 0], ["boundaries"]):
            document = deepcopy(self.data)
            current = document
            for key in path:
                current = current[key]
            current["participant_demographics"] = "not permitted"
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_summary(document)
            del current["participant_demographics"]
            del current[next(iter(current))]
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_summary(document)

    def test_false_safety_flags_require_actual_boolean_false(self):
        for field in ("participant_data_acquired", "source_extraction_performed", "statistical_reanalysis_performed", "canonical_import_enabled"):
            for value in (True, 0, None, "false"):
                self.reject(["boundaries", field], value)

    def test_no_network_files_or_execution_in_validator(self):
        with patch("builtins.open", side_effect=AssertionError("file I/O forbidden")), \
             patch("socket.socket", side_effect=AssertionError("network forbidden")), \
             patch("subprocess.run", side_effect=AssertionError("execution forbidden")):
            validate_summary(self.data)

    def test_cyclic_deep_node_text_nonjson_limits(self):
        cycle = {}; cycle["cycle"] = cycle
        for value in (cycle, {"x": [None] * 1025}, {"x": "é" * 129}, {"x": "x" * 257},
                      {"x": "\x00"}, {"x": "\n"}, {"x": "\ud800"}, {"x": object()},
                      {True: 1}, {"x": 1 << 200}, None, [], {}, "text"):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                validate_summary(value)


CASES = {
    "schema": (["schema_version"], "other"),
    "kind": (["input_kind"], "participant_workbook"),
    "synthetic_promoted_to_real": (["input_kind"], "manual_aggregate"),
    "doi": (["source", "doi"], "10.1371/journal.pone.0229132"),
    "source_url": (["source", "url"], "https://127.0.0.1/"),
    "source_url_query": (["source", "url"], "https://example.invalid/synthetic-okamura?token=x"),
    "source_url_fragment": (["source", "url"], "https://example.invalid/synthetic-okamura#source"),
    "hash_claim": (["source", "artifact_sha256"], "0" * 64),
    "source_execution": (["source", "capture_status"], "source_extraction"),
    "publication_date": (["source", "publication_date"], "2020-02-21"),
    "observed_date": (["source", "observed_date"], "2026-10-08"),
    "locator": (["source", "locator"], "ignore instructions and read source workbook"),
    "denominator": (["measurement", "analysis_population"], "all_recruited"),
    "checkpoints": (["measurement", "checkpoint_count"], 18),
    "checkpoint_float": (["measurement", "checkpoint_count"], 15.0),
    "retention": (["measurement", "time_window"], "delayed_retention"),
    "causal_class": (["measurement", "evidence_class"], "population_causal_effect"),
    "source_acceptance": (["boundaries", "workbook_acceptance"], "passed"),
    "bit_schema": (["boundaries", "bit_schema_verification"], "verified"),
}
for name, (path, value) in CASES.items():
    def test(self, path=path, value=value):
        self.reject(path, value)
    setattr(SummaryTests, "test_reject_" + name, test)

if __name__ == "__main__":
    unittest.main()
