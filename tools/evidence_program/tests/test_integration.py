"""Negative regression checks for the repository-native integration gates."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import check
from validate_dataset import SCHEMA, Draft202012Validator, FORMAT_CHECKER


class IntegrationTests(unittest.TestCase):
    def sources(self):
        return (check.read_json(check.DATA / 'source_inventory.json'),
                check.read_json(check.DATA / 'global_sources.json'),
                check.read_json(check.DATA / 'chinese_sources.json'))

    def chinese(self):
        return [check.read_json(check.DATA / 'chinese' / name)
                for name in ['aliases.json', 'query_lexicon.json', 'test_cases.json']]

    def check_chinese(self, inputs):
        return check.check_chinese(*inputs, SCHEMA, Draft202012Validator, FORMAT_CHECKER)

    def test_duplicate_source_ids_rejected(self):
        inv, global_rows, chinese = self.sources()
        global_rows[1]['source_id'] = global_rows[0]['source_id']
        inv['records'] = global_rows + chinese
        with self.assertRaisesRegex(ValueError, 'unique'):
            check.check_sources(inv, global_rows, chinese)

    def test_uncollected_status_cannot_be_promoted(self):
        inv, global_rows, chinese = self.sources()
        global_rows[0]['collection_status'] = 'collected'
        inv['records'] = global_rows + chinese
        with self.assertRaisesRegex(ValueError, 'claim collection'):
            check.check_sources(inv, global_rows, chinese)

    def test_credential_url_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid URL'):
            check.check_url('https://user:secret@example.com/path')

    def test_nonweb_url_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid URL'):
            check.check_url('file:///etc/passwd')

    def test_coverage_unknown_link_rejected(self):
        inventory, _, _ = self.sources()
        mapping = check.read_json(check.DATA / 'coverage_mapping.json')
        mapping[0]['artifact_links'][0] = 'https://example.com/unverified'
        inventory['repository_coverage'] = mapping
        with self.assertRaisesRegex(ValueError, 'Unrecognized pinned'):
            check.check_coverage(inventory, mapping,
                                 check.read_json(check.DATA / 'baseline_metrics.json'),
                                 check.read_json(check.DATA / 'coverage_references.json'))

    def test_misaligned_unicode_span_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['input']['quote_span']['start'] += 1
        with self.assertRaisesRegex(ValueError, 'span does not match'):
            self.check_chinese(inputs)

    def test_invalid_actual_fragment_field_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['expected']['contract_fragments'][0]['path'] = 'forecast.data.not_a_field'
        with self.assertRaisesRegex(ValueError, 'Unknown schema field'):
            self.check_chinese(inputs)

    def test_invalid_fragment_value_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['expected']['contract_fragments'][0]['value']['value'] = 0.155
        with self.assertRaisesRegex(ValueError, 'Invalid fragment'):
            self.check_chinese(inputs)

    def test_wrong_schema_shortcut_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['expected']['contract_fragments'][0]['schema_definition'] = 'temporal'
        with self.assertRaisesRegex(ValueError, 'shortcut'):
            self.check_chinese(inputs)

    def test_automatic_alias_merge_rejected(self):
        inputs = self.chinese()
        inputs[0]['entries'][0]['automatic_merge_allowed'] = True
        with self.assertRaisesRegex(ValueError, 'merge guard'):
            self.check_chinese(inputs)

    def test_unknown_query_source_rejected(self):
        inputs = self.chinese()
        inputs[1]['query_templates'][0]['source_ids'] = ['CN999']
        with self.assertRaisesRegex(ValueError, 'unknown source'):
            self.check_chinese(inputs)

    def test_fixture_local_old_new_benchmark_paths_resolve(self):
        field = check.schema_for_fragment(SCHEMA, 'old_benchmark_run.data.measurement.result')
        self.assertEqual(field['$ref'], '#/$defs/value')
        self.assertEqual(field, check.schema_for_fragment(SCHEMA, 'new_benchmark_run.data.measurement.result'))

    def test_csv_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rows.csv'
            path.write_text('source_id,name\nGL001,changed\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'CSV diverges'):
                check.check_csv(path, [{'source_id': 'GL001', 'name': 'original'}])


class TaskPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = check.read_json(check.DATA / 'implementation_tasks.json')
        self.recipes = check.read_json(check.DATA / 'analysis_recipes.json')
        self.markdown = (check.DOCS / 'implementation_tasks.md').read_text(encoding='utf-8')
        self.paths = {path for task in self.plan['tasks'] for path in task['existing_paths']}

    def validate(self):
        return check.check_task_plan(self.plan, self.recipes, self.markdown, self.paths)

    def test_task_pack_positive(self):
        result = self.validate()
        self.assertEqual(result['implementation_tasks'], len(self.plan['tasks']))

    def test_duplicate_task_id_rejected(self):
        self.plan['tasks'].append(dict(self.plan['tasks'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate implementation task ID'):
            self.validate()

    def test_unknown_dependency_rejected(self):
        self.plan['tasks'][0]['depends_on'] = ['EP99999']
        with self.assertRaisesRegex(ValueError, 'unknown task'):
            self.validate()

    def test_self_dependency_rejected(self):
        task = self.plan['tasks'][0]
        task['depends_on'] = [task['id']]
        with self.assertRaisesRegex(ValueError, 'itself'):
            self.validate()

    def test_dependency_cycle_rejected(self):
        first, second = self.plan['tasks'][:2]
        first['depends_on'] = [second['id']]
        second['depends_on'] = [first['id']]
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            self.validate()

    def test_unknown_task_source_rejected(self):
        self.plan['tasks'][0]['source_ids'] = ['GL999']
        with self.assertRaisesRegex(ValueError, 'unknown source ID'):
            self.validate()

    def test_unknown_task_recipe_rejected(self):
        self.plan['tasks'][0]['recipe_ids'] = ['R999']
        with self.assertRaisesRegex(ValueError, 'unknown recipe ID'):
            self.validate()

    def test_task_path_traversal_rejected(self):
        for path in ['../outside.py', '/tmp/outside.py', 'C:\\outside.py', '.']:
            with self.subTest(path=path):
                self.plan['tasks'][0]['proposed_paths'] = [path]
                with self.assertRaisesRegex(ValueError, 'Unsafe task path'):
                    self.validate()

    def test_task_missing_existing_path_rejected(self):
        self.plan['tasks'][0]['existing_paths'].append('missing-task-baseline-file.py')
        with self.assertRaisesRegex(ValueError, 'existing path not found'):
            self.validate()

    def test_conflicting_task_path_roles_rejected(self):
        self.plan['tasks'][0]['proposed_paths'].append(self.plan['tasks'][0]['existing_paths'][0])
        with self.assertRaisesRegex(ValueError, 'both existing and proposed'):
            self.validate()

    def test_later_creation_of_proposed_path_is_allowed(self):
        # Existence today does not change the proposed-at-baseline designation.
        self.paths.update(self.plan['tasks'][0]['proposed_paths'])
        self.validate()

    def test_task_doc_title_drift_rejected(self):
        task = self.plan['tasks'][0]
        self.markdown = self.markdown.replace('## ' + task['id'] + ' ' + task['title'],
                                               '## ' + task['id'] + ' Changed title', 1)
        with self.assertRaisesRegex(ValueError, 'IDs/titles'):
            self.validate()

    def test_task_doc_missing_heading_rejected(self):
        self.markdown = self.markdown.replace('## ' + self.plan['tasks'][0]['id'] + ' ', '## Removed ', 1)
        with self.assertRaisesRegex(ValueError, 'heading count'):
            self.validate()

    def test_plan_cannot_claim_execution(self):
        self.plan['tasks'][0]['status'] = 'completed'
        with self.assertRaisesRegex(ValueError, 'claims execution'):
            self.validate()

    def test_task_acceptance_evidence_required(self):
        self.plan['tasks'][0]['completion_evidence'] = []
        with self.assertRaisesRegex(ValueError, 'missing completion_evidence'):
            self.validate()


class ResearchCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = check.read_json(check.DATA / 'research/chinese-safety-evaluations.json')
        self.inventory_hash = check.hashlib.sha256((check.DATA / 'source_inventory.json').read_bytes()).hexdigest()
        self.markdown = (check.DOCS / 'research/chinese-safety-evaluations.md').read_text(encoding='utf-8')

    def validate(self):
        return check.check_research_catalog(self.catalog, self.inventory_hash, self.markdown)

    def test_research_catalog_positive(self):
        self.assertEqual(self.validate()['research_candidates'], 8)

    def test_research_duplicate_candidate_rejected(self):
        self.catalog['families'][1]['candidate_id'] = 'ZHS001'
        with self.assertRaisesRegex(ValueError, 'candidate IDs'):
            self.validate()

    def test_research_active_admission_rejected(self):
        self.catalog['collector_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'cannot enable admission'):
            self.validate()

    def test_research_family_collection_rejected(self):
        self.catalog['families'][0]['collection_status'] = 'collected'
        with self.assertRaisesRegex(ValueError, 'cannot enable collection'):
            self.validate()

    def test_research_frozen_inventory_drift_rejected(self):
        self.catalog['baseline_inventory']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'frozen inventory mismatch'):
            self.validate()

    def test_research_unknown_inventory_reference_rejected(self):
        self.catalog['families'][0]['inventory_relationships'][0]['source_id'] = 'CN999'
        with self.assertRaisesRegex(ValueError, 'Unknown research inventory'):
            self.validate()

    def test_research_missing_rights_provenance_rejected(self):
        self.catalog['families'][0]['artifacts'][0]['rights_evidence_artifact_ids'] = []
        with self.assertRaisesRegex(ValueError, 'Declared rights lack evidence'):
            self.validate()

    def test_research_index_only_cannot_be_upgraded(self):
        self.catalog['families'][6]['artifacts'][0]['access_status'] = 'primary_opened'
        with self.assertRaisesRegex(ValueError, 'Index-only evidence'):
            self.validate()

    def test_research_adapter_cannot_be_activated(self):
        self.catalog['proposed_adapter']['status'] = 'implemented'
        with self.assertRaisesRegex(ValueError, 'remain a specification'):
            self.validate()

    def test_research_adapter_fetch_expansion_rejected(self):
        self.catalog['proposed_adapter']['content_fetches_max'] = 3
        with self.assertRaisesRegex(ValueError, 'adapter bounds'):
            self.validate()

    def test_research_guessed_denominator_rejected(self):
        self.catalog['proposed_adapter']['unknown_fields']['denominator'] = 1000
        with self.assertRaisesRegex(ValueError, 'preserve unknowns'):
            self.validate()

    def test_research_float_spot_check_rejected(self):
        self.catalog['proposed_adapter']['spot_checks'][0]['decimal_value'] = 40.01
        with self.assertRaisesRegex(ValueError, 'decimal strings'):
            self.validate()

    def test_research_bad_pin_rejected(self):
        self.catalog['families'][0]['artifacts'][0]['git_blob_sha'] = 'main'
        with self.assertRaisesRegex(ValueError, 'Invalid research artifact git_blob_sha'):
            self.validate()

    def test_research_doc_title_drift_rejected(self):
        self.markdown = self.markdown.replace('## ZHS001 FLAMES', '## ZHS001 Wrong title')
        with self.assertRaisesRegex(ValueError, 'documentation IDs/titles'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
