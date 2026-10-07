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


if __name__ == '__main__':
    unittest.main()
