"""Offline checks for the pinned Cetic.br research note and evidence catalog.

These validate curated artifact integrity and interpretation safeguards only.
They do not fetch, parse the source workbooks, or admit production evidence.
Run alone: python -m unittest discover -s tools/evidence_program/tests -p test_cetic_adoption.py
"""
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[3]
NOTE = ROOT / 'docs/evidence-program/research/cetic_2025_ai_adoption_measurement.md'
CATALOG = ROOT / 'data/evidence-program/research/cetic_2025_ai_adoption_evidence.json'
VIEWS = {
    'percentage': ('proportion', 'Percentage (%)', '0c2f856d510fb2fc5d3c5b19b4e717e1b2c496c9d72a3859d950b4fe253ee131', '165', '0'),
    'percentage_margin': ('sampling_error', 'Margin of error (%)', 'e62997ffaad466a058c6032c6ec93024327a0dd9f90cca174c276f5e7dda25f0', '165', '0'),
    'total': ('total', 'Total', 'c60382c74857ab84b49e386a1ab285685f7a35e36acb4c7e1a01d75609f5add8', '3', '#,##0'),
    'total_margin': ('sampling_error_total', 'Margin of error for total', 'f51431c74407e0a13bbe8f923aac34d4107e8c3d339acc2b777b0db20dbfe1b6', '3', '#,##0'),
}
SCREENING = ('¹This indicator was collected only among enterprises with IT specialists, '
             'area or department. For dissemination purposes, the results are presented '
             'by the total number of enterprises.')


class CeticAdoptionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(CATALOG.read_text(encoding='utf-8'))
        self.note = NOTE.read_text(encoding='utf-8')

    def test_reviewed_artifact_bytes_unchanged(self):
        for path, expected in [
            (NOTE, '32677b19d4a2035f19a286d89c7d3db78484f3c30aa34954075116af9c602355'),
            (CATALOG, 'a8d0b76528a2ff158a18746f8dbe9df61691a7666bfb73d248c79c6b8e1e9edd'),
        ]:
            with self.subTest(path=path.name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_source_identity_and_attribution(self):
        data = self.data
        self.assertEqual(data['schema_version'], '1.0')
        self.assertEqual(data['dataset_id'], 'cetic-ict-enterprises-2025-ai-adoption-v1.0')
        self.assertEqual(data['reference_year'], 2025)
        self.assertEqual(data['release_version'], 'v1.0')
        self.assertEqual(data['source_url'], 'https://cetic.br/media/microdados/1039/ict_enterprises_2025_tables_xlsx_v1.0.zip')
        self.assertEqual(data['source_archive_filename'], 'ict_enterprises_2025_tables_xlsx_v1.0.zip')
        self.assertEqual(data['source_archive_bytes'], 446528)
        self.assertEqual(data['source_archive_sha256'], '3c929537c2f30fb24eacdc4d7fb31faf1b1b6862af9655d09b86d9a11ae4311b')
        attribution = data['attribution']
        self.assertEqual(attribution['creator'], 'Brazilian Network Information Center (NIC.br), Cetic.br')
        self.assertEqual(attribution['license'], 'Creative Commons Attribution 4.0 International (CC BY 4.0)')
        self.assertEqual(attribution['license_url'], 'https://creativecommons.org/licenses/by/4.0/deed.pt_BR')
        self.assertIn('derived analysis', attribution['modification_notice'])
        self.assertIn(data['source_url'], self.note)
        self.assertIn(data['source_archive_sha256'], self.note)
        self.assertIn(attribution['license_url'], self.note)

    def test_screening_denominator_and_unknown_methodology(self):
        definition = self.data['measurement_definition']
        self.assertEqual(definition['title_cell'], 'H9!A1')
        self.assertEqual(definition['published_denominator'], 'Total number of enterprises¹')
        self.assertEqual(definition['published_denominator_cell'], 'H9!A2')
        self.assertEqual(definition['screening_footnote'], SCREENING)
        self.assertEqual(definition['screening_footnote_cell'], 'H9!A23')
        self.assertIsNone(definition['full_methodology_population_eligibility'])
        self.assertIn('not a separately identified generative-AI or ChatGPT rate', definition['technology_scope'])
        self.assertIn(SCREENING, self.note)

    def assert_reading(self, reading, view, sheet, cell):
        suffix, unit, digest, format_id, format_code = VIEWS[view]
        self.assertEqual(reading['workbook'], f'ict_enterprises_2025_table_{suffix}_v1.0.xlsx')
        self.assertEqual(reading['workbook_sha256'], digest)
        self.assertEqual((reading['sheet'], reading['cell']), (sheet, cell))
        self.assertEqual((reading['unit_label'], reading['unit_label_cell']), (unit, 'A3'))
        self.assertEqual((reading['number_format_id'], reading['number_format_code']), (format_id, format_code))
        raw = reading['raw_numeric_value']
        self.assertIsInstance(raw, str)
        self.assertRegex(raw, r'^\d+(?:\.\d+)?$')
        value = Decimal(raw)
        self.assertTrue(value.is_finite())
        self.assertGreaterEqual(value, 0)
        if view.startswith('percentage'):
            self.assertLessEqual(value, 100)
        else:
            self.assertEqual(value, value.to_integral_value())
        if 'display_value_whole_number' in reading:
            self.assertEqual(reading['display_value_whole_number'], str(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)))

    def test_h9_rows_and_four_view_alignment(self):
        rows = self.data['adoption_evidence']
        self.assertEqual(len(rows), 17)
        self.assertEqual(Counter(row['row_group'] for row in rows), {'TOTAL': 1, 'SIZE': 3, 'REGION': 5, 'MARKET SEGMENT': 8})
        self.assertEqual(len({row['row_category'] for row in rows}), 17)
        for number, row in enumerate(rows, 5):
            with self.subTest(row=number):
                self.assertEqual(row['indicator'], 'H9')
                self.assertEqual(row['response'], 'Yes')
                self.assertEqual(row['response_header_cells'], ['C3', 'C4'])
                self.assertEqual((row['row_group_cell'], row['row_category_cell']), (f'A{number}', f'B{number}'))
                self.assertEqual(row['published_denominator'], 'Total number of enterprises¹')
                self.assertEqual((row['published_denominator_cell'], row['screening_footnote_cell']), ('A2', 'A23'))
                self.assertEqual(set(row['readings']), set(VIEWS))
                for view, reading in row['readings'].items():
                    self.assert_reading(reading, view, 'H9', f'C{number}')
        self.assertEqual([rows[0]['readings'][view]['raw_numeric_value'] for view in VIEWS], ['17.46', '1.72', '93475', '9211'])

    def test_h9a_remains_conditional_and_nonpartitioning(self):
        conditional = self.data['conditional_comparison']
        self.assertEqual(conditional['indicator'], 'H9A')
        self.assertEqual(conditional['published_denominator'], 'Total number of enterprises that used Artificial Intelligence technologies')
        self.assertEqual(conditional['published_denominator_cell'], 'H9A!A2')
        self.assertIn('not population-wide adoption rates', conditional['warning'])
        self.assertIn('must not be treated as a partition', conditional['warning'])
        rows = conditional['evidence']
        self.assertEqual(len(rows), 7)
        self.assertEqual(len({row['technology_type'] for row in rows}), 7)
        for column, row in zip('CDEFGHI', rows):
            self.assertEqual(row['technology_header_cells'], [f'{column}3', f'{column}4'])
            self.assertEqual((row['row_category'], row['row_category_cell']), ('Total', 'B5'))
            self.assertEqual(set(row['readings']), {'percentage', 'percentage_margin'})
            for view, reading in row['readings'].items():
                self.assert_reading(reading, view, 'H9A', f'{column}5')
        self.assertGreater(sum(Decimal(row['readings']['percentage']['raw_numeric_value']) for row in rows), 100)
        self.assertEqual(rows[5]['technology_type'], 'Workflow automation')
        self.assertEqual(rows[5]['readings']['percentage']['raw_numeric_value'], '67.511')
        self.assertEqual(rows[5]['readings']['percentage_margin']['raw_numeric_value'], '5.0724')

    def test_uncertainty_and_precision_limits(self):
        uncertainty = self.data['uncertainty_and_precision']
        for field in ['confidence_level', 'standard_error', 'unweighted_sample_size', 'design_covariance']:
            self.assertIsNone(uncertainty[field])
        for field in ['confidence_intervals_constructed', 'significance_tests_performed']:
            self.assertIs(uncertainty[field], False)
        self.assertEqual(uncertainty['percentage_margin_unit_as_published'], 'Margin of error (%)')
        self.assertIn('percentage points', uncertainty['percentage_margin_interpretation'])
        self.assertIn('not unweighted respondent counts', uncertainty['count_note'])
        self.assertIn('not changed to zero', uncertainty['missing_value_note'])
        self.assertIn('do not establish statistical precision', uncertainty['format_note'])
        self.assertIn('no 95% confidence interval is asserted', self.note)

    def test_coverage_counts_do_not_multiply_independent_evidence(self):
        coverage = self.data['coverage']
        expected = {'survey_families': 1, 'workbook_statistical_views': 4,
                    'distinct_table_ids': 48, 'worksheets': 192,
                    'matched_aggregate_cell_locations': 6069,
                    'numeric_locations': 6018, 'literal_hyphen_locations': 51}
        for field, value in expected.items():
            self.assertEqual(coverage[field], value)
        self.assertEqual(coverage['worksheets'], coverage['distinct_table_ids'] * coverage['workbook_statistical_views'])
        self.assertEqual(coverage['matched_aggregate_cell_locations'], coverage['numeric_locations'] + coverage['literal_hyphen_locations'])
        self.assertIs(coverage['publisher_release_completeness_beyond_archive_membership_verified'], False)
        self.assertIn('not independent samples', coverage['independence_warning'])
        self.assertIn('correlated', coverage['independence_warning'])
        self.assertEqual(len(self.data['analysis_limits']), 5)

    def test_only_public_source_links_and_no_delivery_metadata(self):
        text = self.note + '\n' + CATALOG.read_text(encoding='utf-8')
        links = re.findall(r'https?://[^\s\"<>\)]+', text)
        self.assertTrue(links)
        for link in links:
            parsed = urlsplit(link)
            self.assertEqual(parsed.scheme, 'https')
            self.assertIn(parsed.hostname, {'cetic.br', 'creativecommons.org'})
            self.assertIsNone(parsed.username)
            self.assertIsNone(parsed.password)
            self.assertFalse(parsed.query)
        self.assertIsNone(re.search(r'(?i)(?:file|sediment|sandbox)://|(?:/)(?:workspace|home|Users|tmp|mnt|root)/|(?<![A-Za-z0-9_])[A-Z]:[\\/]', text), 'Private locator in public artifact')
        self.assertIsNone(re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text), 'Email address in public artifact')
        self.assertIsNone(re.search(r'(?i)"(?:drive_id|drive_file_id|account|upload_receipt|handoff|local_path|workspace_path)"\s*:', text), 'Delivery metadata in public artifact')


if __name__ == '__main__':
    unittest.main()
