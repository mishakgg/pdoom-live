"""Curated research boundaries and evidence-identity regressions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import check_algorithmic_efficiency as c
ROOT = HERE.parents[1]


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'data/evidence-program/research/algorithmic-efficiency.json').read_text())
        cls.guide = (ROOT / 'docs/evidence-program/research/algorithmic-efficiency.md').read_text()
        cls.inventory_hash = hashlib.sha256((ROOT / 'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()

    def check(self, d=None, guide=None):
        return c.check_catalog(self.catalog if d is None else d, self.inventory_hash,
                               self.guide if guide is None else guide, ROOT)

    def reject(self, mutate):
        d = deepcopy(self.catalog); mutate(d)
        with self.assertRaises(ValueError): self.check(d)

    def test_catalog(self):
        result = self.check()
        self.assertEqual((5, 35, 34, 55), tuple(result[k] for k in ['algorithmic_efficiency_collections', 'algorithmic_efficiency_artifact_references', 'algorithmic_efficiency_qualified_findings', 'algorithmic_efficiency_overlap_comparison_cells']))

    def test_fixtures(self): self.assertEqual(74, c.check_fixtures(ROOT)['algorithmic_efficiency_observations'])
    def test_status(self): self.reject(lambda d: d.update(operational_admission='admitted'))
    def test_collector(self): self.reject(lambda d: d.update(collector_enabled=True))
    def test_training(self): self.reject(lambda d: d.update(training_data_download=True))
    def test_execution(self): self.reject(lambda d: d.update(source_code_execution=True))
    def test_universal_curve(self): self.reject(lambda d: d.update(universal_efficiency_curve=True))
    def test_contract_mapping(self): self.reject(lambda d: d.update(canonical_contract_mapping='implemented'))
    def test_wrong_base(self): self.reject(lambda d: d.update(repository_review_commit='f'*40))
    def test_baseline_drift(self): self.reject(lambda d: d['baseline_inventory'].update(sha256='f'*64))
    def test_missing_collection(self): self.reject(lambda d: d['collections'].pop())
    def test_family_identity(self): self.reject(lambda d: d['collections'][1].update(source_family_id='algoperf-v05'))
    def test_inventory_conflation(self): self.reject(lambda d: d['collections'][0].update(inventory_source_id='GL008'))
    def test_rights_upgrade(self): self.reject(lambda d: d['collections'][1]['artifacts'][2].update(rights_status='declared_license',license_identifier='MIT'))
    def test_unknown_rights_vendoring(self): self.reject(lambda d: d['collections'][4]['artifacts'][1].update(source_bytes_vendored=True))
    def test_derivative_hash_conflation(self): self.reject(lambda d: d['collections'][0]['artifacts'][3].update(fixture_sha256=d['collections'][0]['artifacts'][3]['sha256']))
    def test_source_hash_corruption(self): self.reject(lambda d: d['collections'][0]['artifacts'][2].update(git_blob_sha='038e 3ea'))
    def test_missing_finding_evidence(self): self.reject(lambda d: d['collections'][0]['findings'][0].update(evidence_artifact_ids=[]))
    def test_comparator_role_loss(self): self.reject(lambda d: d['collections'][0]['findings'][6].update(qualification='One comparator everywhere'))
    def test_paper_target_loss(self): self.reject(lambda d: d['collections'][0]['sample'].update(validation_target='0.7344'))
    def test_rerun_loss(self): self.reject(lambda d: d['collections'][1]['sample'].update(explicit_seed_in_inspected_log=42))
    def test_nano_aggregate_repair(self): self.reject(lambda d: d['collections'][1]['sample'].update(published_mean_loss='3.278929'))
    def test_epoch_interval_loss(self): self.reject(lambda d: d['collections'][2]['estimates'][4].update(confidence_level=.90))
    def test_epoch_missingness_loss(self): self.reject(lambda d: d['collections'][2]['preprocessing'].pop())
    def test_sheet_access_promoted(self): self.reject(lambda d: d['collections'][2]['artifacts'][4].update(access_status='all_rows_retrieved'))
    def test_nested_source_references(self):
        for family in self.catalog['collections']:
            ids = {a['artifact_id'] for a in family['artifacts']}
            for conflict in family.get('source_conflicts', []):
                self.assertTrue(set(conflict.get('artifacts', [])) <= ids)
            for estimate in family.get('estimates', []):
                self.assertIn(estimate['evidence_artifact_id'], ids)

    def test_nested_source_reference_corruption(self):
        self.reject(lambda d: d['collections'][3]['source_conflicts'][0].update(artifacts=['openai_csv']))

    def test_openai_conflict_repair(self): self.reject(lambda d: d['collections'][3]['source_conflicts'][0].update(repair='divide_by_86.4'))
    def test_openai_dates_overwrite(self): self.reject(lambda d: d['collections'][3]['date_validations'][0].update(raw='2015-12-10'))
    def test_mit_method_conflation(self): self.reject(lambda d: d['collections'][4]['findings'][4].update(claim='The helper finds first crossing'))
    def test_mit_hardware_guess(self): self.reject(lambda d: d['collections'][4]['sample'].update(per_trace_hardware='8 V100'))
    def test_duplicate_as_replication(self): self.reject(lambda d: d['evidence_relationships'][0].update(relationship='independent_replication'))
    def test_prior_catalog_missing(self): self.reject(lambda d: d['catalog_overlap_review']['catalogs_compared'].pop())
    def test_prior_overlap_overclaim(self): self.reject(lambda d: d['catalog_overlap_review']['catalogs_compared'][0]['candidate_checks']['AE001'].update(same_artifact_established=True))
    def test_prompt_scope_expansion(self): self.reject(lambda d: d['focused_follow_up_prompts'][0].update(prompt='Run training now'))
    def test_missing_next_action(self): self.reject(lambda d: d['next_actions'].pop())
    def test_readiness_promotion(self): self.reject(lambda d: d['offline_reader'].update(official_aggregate_score=1))
    def test_guide_boundary_loss(self):
        with self.assertRaises(ValueError): self.check(guide=self.guide.replace('0.7344','unknown'))
    def test_private_url(self):
        for url in ['http://example.org/x','https://a:b@example.org','https://example.org?access_token=x']:
            with self.assertRaises(ValueError): c.safe_url(url)
    def test_source_full_bodies_not_in_data(self):
        self.assertFalse(list((ROOT / 'data/evidence-program/research').glob('*.csv')))
        self.assertFalse(self.catalog['training_data_download'])


if __name__ == '__main__': unittest.main()
