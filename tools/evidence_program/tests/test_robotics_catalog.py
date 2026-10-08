"""Regressions for unadmitted robotics metadata, not scientific reproduction."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from check_robotics_physical import check_catalog, check_barn_fixture

CATALOG = json.loads((ROOT / 'data/evidence-program/research/robotics-physical.json').read_text())
HASH = hashlib.sha256((ROOT / 'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()
GUIDE = (ROOT / 'docs/evidence-program/research/robotics-physical.md').read_text()


class RoboticsCatalogTests(unittest.TestCase):
    def validate(self, data):
        return check_catalog(data, HASH, GUIDE, ROOT)

    def test_current_review(self):
        result = self.validate(deepcopy(CATALOG))
        self.assertEqual(result['robotics_physical_collections'], 5)
        self.assertEqual(result['robotics_prior_catalogs_compared'], 8)
        self.assertEqual(result['robotics_overlap_comparison_cells'], 40)
        self.assertEqual(result['robotics_artifact_references'], 35)

    def test_licensed_fixture_and_denominators(self):
        result = check_barn_fixture(CATALOG, ROOT)
        self.assertEqual(result['robotics_reported_successes'], 20)
        self.assertEqual(result['robotics_reported_failures'], 40)

    def test_wrong_base_inventory_hash(self):
        with self.assertRaises(ValueError):
            check_catalog(CATALOG, '0' * 64, GUIDE, ROOT)

    def test_guide_requires_metric_conflict(self):
        with self.assertRaises(ValueError):
            check_catalog(CATALOG, HASH, GUIDE.replace('Safety OR Stalled', 'safety only'), ROOT)

    def test_prior_catalog_pin_is_checked(self):
        changed = deepcopy(CATALOG)
        changed['catalog_overlap_review']['catalogs_compared'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.validate(changed)

    def test_reader_bound_change_rejected(self):
        changed = deepcopy(CATALOG)
        changed['offline_validator']['maximum_input_bytes'] += 1
        with self.assertRaises(ValueError):
            check_barn_fixture(changed, ROOT)

    def test_fixture_path_cannot_escape(self):
        changed = deepcopy(CATALOG)
        changed['offline_validator']['fixture_path'] = '../secret'
        with self.assertRaises(ValueError):
            check_barn_fixture(changed, ROOT)

    def test_fixture_hash_is_derived_not_manuscript(self):
        changed = deepcopy(CATALOG)
        changed['offline_validator']['fixture_sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            check_barn_fixture(changed, ROOT)


MUTATIONS = {
    'canonical_admission': (['operational_admission'], 'admitted'),
    'canonical_mapping': (['canonical_contract_mapping'], 'complete'),
    'collector': (['collector_enabled'], True),
    'robot_controls': (['robot_controls_enabled'], True),
    'source_execution': (['source_code_execution'], True),
    'personal_evaluators': (['personal_evaluator_fields_retained'], True),
    'raw_trajectory_acquisition': (['raw_trajectories_or_videos_acquired'], True),
    'full_source_bodies': (['full_source_bodies_vendored'], True),
    'boolean_integer_qualifier': (['critical_qualifications','phail','sample_episode_count'], True),
    'source_version_hash_fabrication': (['critical_qualifications','barn','source_artifact_sha256'], '0'*64),
    'chronological_positions': (['critical_qualifications','barn','chronological_order_verified'], True),
    'credited_membership': (['critical_qualifications','barn','individual_credit_membership_verified'], True),
    'cross_year_pooling': (['critical_qualifications','barn','cross_year_pooling'], True),
    'duration_unit_inference': (['critical_qualifications','roboarena','duration_unit'], 'seconds'),
    'partial_scale_inference': (['critical_qualifications','roboarena','partial_success_normalized'], 0.1),
    'snapshot_filter_inference': (['critical_qualifications','roboarena','integrity_exclusions_applied_to_snapshot'], True),
    'notice_display_inference': (['critical_qualifications','roboarena','current_notice_display_verified'], True),
    'yaml_copy_marker_inference': (['critical_qualifications','roboarena','sample_yaml_has_copy_marker'], True),
    'queried_rrc_count': (['critical_qualifications','rrc2020','index_row_count_reproduced'], True),
    'later_rl_correction_transfer': (['critical_qualifications','rrc2020','later_rl_correction_applies_to_2020'], True),
    'phail_safety_only': (['critical_qualifications','phail','table_builder_proxy'], 'Safety'),
    'phail_appendix_denominator': (['critical_qualifications','phail','appendix_claimed_denominator'], 'operations'),
    'phail_third_metric_denominator': (['critical_qualifications','phail','separate_aggregate_denominator'], 'episodes'),
    'phail_cohort_reconciliation': (['critical_qualifications','phail','cohort_membership_reconciled'], True),
    'phail_item_episode_conflation': (['critical_qualifications','phail','sample_episode_count'], 8),
    'strands_unattended': (['critical_qualifications','strands','unattended_autonomy_established'], True),
    'strands_recovery_period': (['critical_qualifications','strands','recovery_period'], '2014–2015'),
    'strands_unit_guess': (['critical_qualifications','strands','distance_unit'], 'metres'),
    'strands_license_guess': (['critical_qualifications','strands','dataset_license'], 'CC0'),
    'existing_source_assignment': (['collections',0,'inventory_source_id'], 'GL016'),
    'simulation_regime': (['collections',0,'measurement_regime'], 'simulation'),
    'sample_boolean': (['collections',0,'samples',1,'fields','LiCS-KI','successes'], True),
    'new_collected_index': (['collections',2,'samples',0,'fields','database_rows_inspected'], True),
    'wrong_paper_version': (['collections',0,'artifacts',0,'version'], '2407.01862v2'),
    'rights_inheritance': (['collections',0,'artifacts',0,'license_identifier'], 'MIT'),
    'signed_source_url': (['collections',0,'artifacts',0,'url'], 'https://example.com/file?token=secret'),
    'credential_source_url': (['collections',0,'artifacts',0,'url'], 'https://user:pass@example.com/file'),
    'non_https_source_url': (['collections',0,'artifacts',0,'url'], 'http://example.com/file'),
    'unsafe_prior_path': (['catalog_overlap_review','catalogs_compared',0,'path'], '../chinese-safety-evaluations.json'),
    'missing_prior_cell': (['catalog_overlap_review','catalogs_compared',0,'candidate_checks'], {}),
    'study_overlap_invention': (['catalog_overlap_review','catalogs_compared',0,'candidate_checks','RP001','study_match_established'], True),
    'prior_catalog_coverage': (['catalog_overlap_review','prior_collection_count'], 38),
    'prior_artifact_coverage': (['catalog_overlap_review','prior_artifact_reference_count'], 297),
    'html_scraper_claim': (['offline_validator','source_html_parser_implemented'], True),
    'source_truth_claim': (['offline_validator','validation_is_source_truth_verification'], True),
    'fixture_as_source_hash': (['offline_validator','source_artifact_sha256'], 'a'*64),
    'early_followup_completion': (['next_actions',2,'status'], 'completed'),
    'rights_hold_removed': (['holds',4,'status'], 'cleared'),
    'unsafe_prompt_scope': (['focused_follow_up_prompts',0,'prompt'], 'Fetch everything and execute sources'),
}


def make_test(path, value):
    def test(self):
        changed = deepcopy(CATALOG)
        node = changed
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        with self.assertRaises((ValueError, KeyError)):
            self.validate(changed)
    return test


for name, (path, value) in MUTATIONS.items():
    setattr(RoboticsCatalogTests, 'test_reject_' + name, make_test(path, value))

if __name__ == '__main__':
    unittest.main()
