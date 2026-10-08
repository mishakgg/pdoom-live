"""Negative tests protect reviewed provenance and evidence-strength boundaries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from check_human_reliance import check_catalog, check_aggregate_ledger, safe_url
ROOT = HERE.parents[1]
CAT = json.loads((ROOT / "data/evidence-program/research/human-reliance.json").read_text())
DOC = (ROOT / "docs/evidence-program/research/human-reliance.md").read_text()
HASH = hashlib.sha256((ROOT / "data/evidence-program/source_inventory.json").read_bytes()).hexdigest()


class HumanRelianceCatalog(unittest.TestCase):
    def run_check(self, c=None, doc=None, root=ROOT):
        return check_catalog(CAT if c is None else c, HASH, DOC if doc is None else doc, root)

    def rejects(self, mutate):
        c = deepcopy(CAT); mutate(c)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            self.run_check(c)

    def test_catalog_passes(self):
        out = self.run_check()
        self.assertEqual(out["human_reliance_collections"], 5)
        self.assertEqual(out["human_reliance_prior_catalogs_compared"], 10)
        self.assertEqual(out["human_reliance_overlap_comparison_cells"], 50)

    def test_aggregate_and_synthetic_examples_pass(self):
        out = check_aggregate_ledger(ROOT)
        self.assertEqual(out["human_reliance_real_workbook_acceptance_passes"], 0)

    def test_operational_scope_cannot_expand(self):
        for key in ["collector_enabled", "source_code_execution", "simulator_or_model_execution", "clinical_decision_tool",
                    "participant_rows_acquired_current_review", "participant_rows_vendored", "workbook_acquired_current_review", "raw_source_files_vendored"]:
            with self.subTest(key=key):
                self.rejects(lambda c: c.__setitem__(key, True))

    def test_guard_truths_cannot_change(self):
        for key in CAT["interpretation_guards"]:
            with self.subTest(key=key):
                self.rejects(lambda c: c["interpretation_guards"].__setitem__(key, True))

    def test_catalog_fields_are_closed(self):
        self.rejects(lambda c: c.__setitem__("participant_rows", []))

    def test_base_identity_is_pinned(self):
        self.rejects(lambda c: c.__setitem__("repository_review_commit", "0" * 40))

    def test_inventory_hash_required(self):
        with self.assertRaises(ValueError):
            check_catalog(CAT, "0" * 64, DOC)

    def test_family_set_cannot_shrink(self):
        self.rejects(lambda c: c["collections"].pop())

    def test_family_ids_cannot_merge(self):
        self.rejects(lambda c: c["collections"][0].__setitem__("candidate_id", "HR002"))

    def test_licenses_do_not_propagate(self):
        self.rejects(lambda c: c["collections"][0]["artifacts"][3].update(rights_status="declared_license", license_identifier="CC-BY-4.0"))

    def test_metadata_hash_is_not_byte_acceptance(self):
        self.rejects(lambda c: c["collections"][3]["artifacts"][4].__setitem__("sha256", "a" * 64))

    def test_inherited_bit_schema_stays_inherited(self):
        self.rejects(lambda c: c["offline_work"].__setitem__("decoder_schema_status", "verified"))

    def test_actual_acceptance_stays_blocked(self):
        self.rejects(lambda c: c["offline_work"].__setitem__("actual_data_acceptance", "passed"))

    def test_paper_targets_cannot_be_mutated(self):
        self.rejects(lambda c: c["offline_work"]["real_acceptance_targets"].__setitem__("correct", 1740))

    def test_bastani_denominators_keep_units(self):
        self.rejects(lambda c: c["collections"][0]["aggregate_denominators"].__setitem__("unique_main_regression_students", 2848))

    def test_bansal_conflicting_count_not_repaired(self):
        self.rejects(lambda c: c["collections"][1]["aggregate_denominators"].__setitem__("retained_unique_people", 178))

    def test_gaube_count_conflict_preserved(self):
        self.rejects(lambda c: c["collections"][3]["aggregate_denominators"].__setitem__("table3_total", 265))

    def test_gaube_adviser_not_real_model(self):
        self.rejects(lambda c: c["collections"][3]["context"].__setitem__("model_checkpoint", "CHEST-AI"))

    def test_glickman_cohorts_preserved(self):
        self.rejects(lambda c: c["collections"][4]["cohorts"][0].__setitem__("reported_analyzed_n", 1401))

    def test_glickman_estimands_not_collapsed(self):
        self.rejects(lambda c: c["collections"][4]["measures"][1].__setitem__("definition", "mean(response−evidence)"))

    def test_findings_need_exact_provenance(self):
        self.rejects(lambda c: c["collections"][0]["findings"][0].__setitem__("evidence_artifact_ids", []))

    def test_inherited_claim_cannot_upgrade(self):
        self.rejects(lambda c: c["collections"][2]["findings"][4].__setitem__("verification_level", "current_documentary_verification"))

    def test_all_prior_catalogs_required(self):
        self.rejects(lambda c: c["catalog_overlap_review"]["catalogs_compared"].pop())

    def test_overlap_count_types_are_strict(self):
        for key in ["prior_collection_count", "prior_artifact_reference_count", "comparison_cell_count"]:
            for value in [float(CAT["catalog_overlap_review"][key]), True, str(CAT["catalog_overlap_review"][key])]:
                with self.subTest(key=key, value=value):
                    self.rejects(lambda c: c["catalog_overlap_review"].__setitem__(key, value))

    def test_prior_comparison_cells_required(self):
        self.rejects(lambda c: c["catalog_overlap_review"]["catalogs_compared"][0]["candidate_checks"].pop("HR005"))

    def test_shared_cohort_cannot_be_inferred(self):
        self.rejects(lambda c: c["catalog_overlap_review"]["catalogs_compared"][0]["candidate_checks"]["HR001"].__setitem__("shared_participant_cohort_established", True))

    def test_prior_hash_cannot_change(self):
        self.rejects(lambda c: c["catalog_overlap_review"]["catalogs_compared"][0].__setitem__("sha256", "a" * 64))

    def test_hold_cannot_disappear(self):
        self.rejects(lambda c: c["holds"].pop())

    def test_prompt_scope_cannot_expand(self):
        self.rejects(lambda c: c["focused_follow_up_prompts"][0].__setitem__("prompt", "Download the workbook now"))

    def test_static_read_is_not_execution(self):
        self.rejects(lambda c: c.__setitem__("static_source_read", False))

    def test_guide_required_semantics(self):
        with self.assertRaises(ValueError):
            self.run_check(doc=DOC.replace("0.14", "0.15"))

    def test_guide_headings_match(self):
        with self.assertRaises(ValueError):
            self.run_check(doc=DOC.replace("## HR001", "## HR099"))

    def test_source_url_syntax(self):
        for url in ["http://example.org", "https://a:b@example.org", "https://example.org/?api_key=secret", "https://example.org/a b"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                safe_url(url)


if __name__ == "__main__":
    unittest.main()
