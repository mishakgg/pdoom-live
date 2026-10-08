"""Deterministic open-model catalog guard regressions; no live access."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from check_open_model_diffusion import check_catalog
ROOT = HERE.parents[1]


class OpenModelCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / 'data/evidence-program/research/open-model-diffusion.json').read_text())
        self.markdown = (ROOT / 'docs/evidence-program/research/open-model-diffusion.md').read_text()
        self.inventory_hash = hashlib.sha256((ROOT / 'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()

    def validate(self):
        return check_catalog(self.catalog, self.inventory_hash, self.markdown)

    def test_positive_catalog(self):
        self.assertEqual(self.validate()['open_model_collections'], 5)
        self.assertEqual(self.validate()['open_model_research_fixtures'], 2)

    def test_operational_admission_rejected(self):
        self.catalog['operational_admission'] = 'admitted'
        with self.assertRaisesRegex(ValueError, 'operational collection'):
            self.validate()

    def test_family_collection_rejected(self):
        self.catalog['collections'][1]['collector_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'family cannot'):
            self.validate()

    def test_inventory_drift_rejected(self):
        self.catalog['baseline_inventory']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'frozen inventory'):
            self.validate()

    def test_false_no_acquisition_rejected(self):
        self.catalog['fixture_acquisition']['count'] = 0
        with self.assertRaisesRegex(ValueError, 'acquisition'):
            self.validate()

    def test_duplicate_collections_rejected(self):
        self.catalog['collections'][1]['candidate_id'] = 'OM001'
        with self.assertRaisesRegex(ValueError, 'IDs/count'):
            self.validate()

    def test_epoch_duplicate_family_rejected(self):
        self.catalog['collections'][2]['inventory_source_id'] = None
        with self.assertRaisesRegex(ValueError, 'source identity'):
            self.validate()

    def test_downloads_not_adoption(self):
        self.catalog['interpretation_guards']['download_count_implies_unique_adopters'] = True
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_reproduction_materials_not_success(self):
        self.catalog['interpretation_guards']['materials_imply_successful_reproduction'] = True
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_signed_link_rejected(self):
        self.catalog['collections'][0]['artifacts'][0]['url'] += '?token=secret'
        with self.assertRaisesRegex(ValueError, 'Signed or credential'):
            self.validate()

    def test_finding_missing_provenance_rejected(self):
        self.catalog['collections'][0]['findings'][0]['evidence_artifact_ids'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'unique provenance'):
            self.validate()

    def test_unbacked_license_rejected(self):
        a = self.catalog['collections'][0]['artifacts'][0]
        a['rights_status'] = 'declared_license'; a['rights_evidence_artifact_ids'] = []
        with self.assertRaisesRegex(ValueError, 'declaration lacks provenance'):
            self.validate()

    def test_annotation_license_not_model_license(self):
        a = next(a for a in self.catalog['collections'][1]['artifacts'] if a['artifact_id'] == 'eu_before')
        a['rights_scope'] = 'all_models_and_linked_works'
        with self.assertRaisesRegex(ValueError, 'Annotation rights'):
            self.validate()

    def test_pin_drift_rejected(self):
        a = next(a for a in self.catalog['collections'][1]['artifacts'] if a['artifact_id'] == 'eu_after')
        a['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'integrity pins'):
            self.validate()

    def test_network_expansion_rejected(self):
        self.catalog['offline_reader']['network_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'bounded scope'):
            self.validate()

    def test_criteria_removal_not_revocation(self):
        self.catalog['offline_reader']['inferred_model_access_events'] = 2
        with self.assertRaisesRegex(ValueError, 'model access/license'):
            self.validate()

    def test_month_date_not_day(self):
        self.catalog['offline_reader']['release_date_raw'] = '2024-12-01'
        with self.assertRaisesRegex(ValueError, 'invent dates'):
            self.validate()

    def test_commit_date_not_assessment_date(self):
        self.catalog['offline_reader']['assessment_timestamp'] = '2026-03-13T14:41:47Z'
        with self.assertRaisesRegex(ValueError, 'invent dates'):
            self.validate()

    def test_completed_action_not_followup(self):
        target = self.catalog['focused_follow_up_prompts'][0]['action_id']
        next(a for a in self.catalog['next_actions'] if a['action_id'] == target)['status'] = 'completed'
        with self.assertRaisesRegex(ValueError, 'open action'):
            self.validate()

    def test_corrections_not_dropped(self):
        self.catalog['corrections'] = []
        with self.assertRaisesRegex(ValueError, 'corrections'):
            self.validate()

    def test_doc_titles_consistent(self):
        self.markdown = self.markdown.replace('## OM001 ', '## OM099 ')
        with self.assertRaisesRegex(ValueError, 'documentation IDs'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
