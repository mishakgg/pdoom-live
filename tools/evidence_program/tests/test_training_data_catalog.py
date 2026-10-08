"""Source-review consistency regressions; no public API or real CSV acquisition."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from check_training_data_feedback import check_catalog, check_reader_fixtures, safe_url


class TrainingDataCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT / 'data/evidence-program/research/training-data-feedback.json').read_text())
        cls.markdown = (ROOT / 'docs/evidence-program/research/training-data-feedback.md').read_text()
        cls.inventory_hash = hashlib.sha256((ROOT / 'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()

    def check(self, value, root=None):
        return check_catalog(value, self.inventory_hash, self.markdown, root)

    def reject(self, modify):
        value = deepcopy(self.original)
        modify(value)
        with self.assertRaises((ValueError, KeyError)):
            self.check(value)

    def test_catalog_and_exact_prior_pins(self):
        result = self.check(self.original, ROOT)
        self.assertEqual(result['training_data_collections'], 5)
        self.assertEqual(result['training_data_overlap_comparison_cells'], 45)

    def test_synthetic_fixture_isolation(self):
        result = check_reader_fixtures(ROOT)
        self.assertEqual(result['training_data_real_source_csv_fixtures'], 0)

    def test_wrong_repository_revision(self):
        self.reject(lambda d: d.update(repository_review_commit='0' * 40))

    def test_source_admission(self):
        self.reject(lambda d: d.update(operational_admission='admitted'))

    def test_canonical_mapping(self):
        self.reject(lambda d: d.update(canonical_contract_mapping='complete'))

    def test_unsafe_scope_flags(self):
        for flag in ['collector_enabled', 'training_or_model_execution', 'source_code_execution', 'corpus_or_page_content_acquired', 'raw_source_files_vendored']:
            with self.subTest(flag=flag):
                self.reject(lambda d: d.update({flag: True}))

    def test_frozen_inventory(self):
        self.reject(lambda d: d['baseline_inventory'].update(source_family_count=69))

    def test_unsupported_proxies(self):
        for key in self.original['interpretation_guards']:
            with self.subTest(key=key):
                self.reject(lambda d: d['interpretation_guards'].update({key: True}))

    def test_collection_identity(self):
        self.reject(lambda d: d['collections'].pop())

    def test_epoch_is_distinct_product(self):
        self.reject(lambda d: d['collections'][4].update(inventory_relationship='existing_inventory_product'))

    def test_crawl_page_not_token(self):
        self.reject(lambda d: d['collections'][0].update(measurement_regime='licensed_token_supply'))

    def test_unknown_urls_qualification(self):
        self.reject(lambda d: d['collections'][0]['samples'][2].update(qualification='Independently counted URL cardinality.'))

    def test_percentage_rounding_qualification(self):
        self.reject(lambda d: d['collections'][0]['findings'][1].update(qualification='Shares must sum exactly 100.'))

    def test_capture_not_publication(self):
        self.reject(lambda d: d['collections'][0]['coverage']['dates'][0].update(content_publication_date='2026-07-07'))

    def test_source_license_not_csv_license(self):
        self.reject(lambda d: d['collections'][0]['artifacts'][0].update(rights_status='declared_license', license_identifier='Apache-2.0'))

    def test_unknown_rights_not_cleared(self):
        self.reject(lambda d: d['collections'][1]['artifacts'][1].update(license_identifier='Apache-2.0'))

    def test_source_hash_not_invented(self):
        self.reject(lambda d: d['collections'][2]['artifacts'][2].update(artifact_sha256='0' * 64, hash_scope='Exact acquired source file bytes'))

    def test_artifact_bytes_not_vendored(self):
        self.reject(lambda d: d['collections'][0]['artifacts'][0].update(source_bytes_vendored=True))

    def test_source_evidence_resolves(self):
        self.reject(lambda d: d['collections'][1]['samples'][0].update(evidence_artifact_ids=['missing']))

    def test_dpi_sample_container(self):
        self.reject(lambda d: d['collections'][1]['samples'][0].update(observed={'dataset_count': 109}))

    def test_real_data_role_not_authorship(self):
        self.reject(lambda d: d['collections'][2]['findings'][1].update(claim='The responses were human-authored.'))

    def test_export_grid_not_actual_rows(self):
        self.reject(lambda d: d['collections'][2]['coverage'].update(full_saved_rows_inspected=True))

    def test_covariance_discrepancy_preserved(self):
        self.reject(lambda d: d['collections'][2]['findings'][2].update(qualification='Code and paper agree.'))

    def test_fineweb_versions_not_joined(self):
        self.reject(lambda d: d['collections'][3]['coverage'].update(paper_language_script_denominator=1870))

    def test_missing_words_not_zero(self):
        self.reject(lambda d: d['collections'][3]['samples'][0]['observed'][2].update(words='0'))

    def test_stock_is_modeled_not_measured(self):
        self.reject(lambda d: d['collections'][4]['samples'][0]['observed'].update(evidence_type='observed_licensed_stock'))

    def test_stock_interval_and_tokenizer(self):
        for key, value in [('lower', '510'), ('tokenizer_basis', 'universal'), ('adjustment_state', 'repetition_adjusted')]:
            with self.subTest(key=key):
                self.reject(lambda d: d['collections'][4]['samples'][0]['observed'].update({key: value}))

    def test_stock_pivot_discrepancy(self):
        self.reject(lambda d: d['collections'][4]['coverage'].update(pivot_word_row_count=100))

    def test_all_nine_catalogs(self):
        self.reject(lambda d: d['catalog_overlap_review']['catalogs_compared'].pop())

    def test_all_five_candidate_cells(self):
        self.reject(lambda d: d['catalog_overlap_review']['catalogs_compared'][0]['candidate_checks'].pop('TD005'))

    def test_host_not_producer(self):
        self.reject(lambda d: d['catalog_overlap_review']['catalogs_compared'][0]['candidate_checks']['TD004'].update(same_producer_established=True))

    def test_existing_catalog_hash_drift(self):
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(OSError):
                self.check(self.original, path)

    def test_rights_holds_and_actions(self):
        self.reject(lambda d: d['holds'][0].update(status='cleared'))
        self.reject(lambda d: d['next_actions'][-1].update(status='completed'))

    def test_reader_scope_and_pins(self):
        self.reject(lambda d: d['offline_reader'].update(network_access=True))
        self.reject(lambda d: d['offline_reader']['source_paths'].append('WARC'))

    def test_source_correction_retention(self):
        self.reject(lambda d: d['corrections'].pop())

    def test_standalone_prompt_boundaries(self):
        self.reject(lambda d: d['focused_follow_up_prompts'][0].update(prompt='Download the corpus and run training.'))

    def test_guide_boundary(self):
        with self.assertRaises(ValueError):
            check_catalog(self.original, self.inventory_hash, self.markdown.replace('synthetic-only', 'real-only'))

    def test_signed_and_credential_urls(self):
        for url in ['https://user:pass@example.com/source', 'https://example.com/file?token=abc', 'http://example.com', 'https://example.com/a b']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                safe_url(url)

    def test_artifact_hash_scope(self):
        self.reject(lambda d: d['collections'][0]['artifacts'][0].update(hash_scope='Web text rendering'))

    def test_duplicate_artifact_identity(self):
        self.reject(lambda d: d['collections'][0]['artifacts'].append(deepcopy(d['collections'][0]['artifacts'][0])))


if __name__ == '__main__':
    unittest.main()
