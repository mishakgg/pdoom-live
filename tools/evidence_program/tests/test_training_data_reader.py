"""Offline synthetic contract/security tests; real source byte acceptance is separate."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from decimal import localcontext
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import read_common_crawl_statistics as cc

FIXTURES = HERE / 'fixtures/training-data'
LANGUAGES = FIXTURES / 'synthetic-languages.csv'
MONTHLY = FIXTURES / 'synthetic-monthly.csv'


class TrainingDataReaderTests(unittest.TestCase):
    def setUp(self):
        self.languages = LANGUAGES.read_bytes()
        self.monthly = MONTHLY.read_bytes()

    def validate(self, languages=None, monthly=None, **kwargs):
        return cc.validate_statistics_bytes(self.languages if languages is None else languages,
                                            self.monthly if monthly is None else monthly,
                                            synthetic_fixture=True, **kwargs)

    def reject(self, languages=None, monthly=None, message='.'):
        with self.assertRaisesRegex(cc.StatisticsInputError, message):
            self.validate(languages, monthly)

    def test_synthetic_fixture_only_emits_three_selected_crawls(self):
        result = self.validate()
        self.assertTrue(result['synthetic'])
        self.assertEqual(result['crawl_count'], 3)
        self.assertEqual([row['crawl_id'] for row in result['crawl_summaries']], list(cc.ALLOWED_CRAWLS))
        self.assertEqual(len(result['language_observations']), 9)
        self.assertNotIn('CC-MAIN-2012', json.dumps(result))
        self.assertTrue(all(row['crawl_id'] in cc.ALLOWED_CRAWLS for row in result['language_observations']))

    def test_native_fields_are_preserved_without_renaming(self):
        result = self.validate()
        row = result['crawl_summaries'][0]
        self.assertEqual(row['native_fields'], {'crawl': 'CC-MAIN-2026-30', 'digest estim.': '101', 'page': '100', 'url': '95'})
        self.assertEqual(row['page_captures'], 100)
        self.assertEqual(row['url_cardinality'], 95)
        self.assertEqual(row['digest_estimated_cardinality'], 101)
        row = result['language_observations'][0]
        self.assertEqual(tuple(row['native_fields']), cc.LANGUAGES_HEADER)
        self.assertEqual(row['native_fields']['%pages/crawl'], '25.0000')
        self.assertEqual(row['pages_percent_of_crawl_decimal'], '25.0000')

    def test_unknown_bucket_is_a_real_bucket_not_missing_or_zero(self):
        result = self.validate()
        unknown = [row for row in result['language_observations'] if row['primary_language'] == '<unknown>']
        self.assertEqual([row['page_captures'] for row in unknown], [25, 1, 1])
        self.assertTrue(all(row['language_status'] == 'unknown' for row in unknown))
        self.assertEqual([row['language_page_sum_including_unknown'] for row in result['crawl_summaries']], [100, 3, 20000])

    def test_unknown_native_urls_is_page_residual_placeholder_not_cardinality(self):
        for row in self.validate()['language_observations']:
            if row['primary_language'] == '<unknown>':
                self.assertIsNone(row['url_cardinality'])
                self.assertEqual(int(row['native_fields']['urls']), row['page_captures'])
                self.assertEqual(row['page_count_basis'], 'residual_monthly_pages_after_labeled_buckets')
                self.assertEqual(row['url_count_basis'], 'page_residual_placeholder_not_measured_URL_cardinality')
            else:
                self.assertEqual(row['url_cardinality'], int(row['native_fields']['urls']))
                self.assertEqual(row['url_count_basis'], 'source_reported_URL_cardinality')

    def test_selected_unknown_native_urls_must_equal_page_residual_scalar(self):
        for original, mismatch in (
                (b'CC-MAIN-2026-30,<unknown>,25,25,25.0000', b'CC-MAIN-2026-30,<unknown>,25,24,25.0000'),
                (b'CC-MAIN-2026-34,<unknown>,1,1,33.3333', b'CC-MAIN-2026-34,<unknown>,1,0,33.3333'),
                (b'CC-MAIN-2026-39,<unknown>,1,1,0.0050', b'CC-MAIN-2026-39,<unknown>,1,0,0.0050')):
            with self.subTest(original=original):
                self.reject(self.languages.replace(original, mismatch), message='page-residual scalar')
        # This is a selected unknown-placeholder check, not cross-language URL
        # reconciliation or interpretation of filtered historical observations.
        historical = self.languages.replace(b'CC-MAIN-2012,<unknown>,10,10,100.0000',
                                            b'CC-MAIN-2012,<unknown>,10,9,100.0000')
        self.assertEqual(self.validate(historical)['crawl_count'], 3)

    def test_missing_unknown_bucket_fails_even_when_sum_matches(self):
        self.reject(self.languages.replace(b'<unknown>,25,25,25.0000', b'fra,25,24,25.0000'), message='unknown-language')

    def test_zero_unknown_bucket_is_preserved(self):
        raw = self.languages.replace(b'<unknown>,25,25,25.0000', b'<unknown>,0,0,0.0000').replace(b'eng,50,49,50.0000', b'eng,75,74,75.0000')
        self.assertEqual(self.validate(raw)['language_observations'][0]['page_captures'], 0)

    def test_page_sum_is_checked_against_monthly_including_unknown(self):
        self.reject(self.languages.replace(b'<unknown>,25,25,25.0000', b'<unknown>,24,24,24.0000'), message='page sum')
        self.reject(monthly=self.monthly.replace(b'101,100,95', b'101,101,95'), message='page sum')

    def test_measurement_units_estimate_flags_and_denominators_are_explicit(self):
        result = self.validate()
        for row in result['crawl_summaries']:
            self.assertFalse(row['page_is_estimate'])
            self.assertFalse(row['url_is_estimate'])
            self.assertTrue(row['digest_is_estimate'])
        totals = {row['crawl_id']: row['page_captures'] for row in result['crawl_summaries']}
        for row in result['language_observations']:
            self.assertEqual(row['denominator_metric'], 'page_captures')
            self.assertEqual(row['denominator_value'], totals[row['crawl_id']])
            self.assertFalse(row['page_is_estimate'])
            self.assertIsNone(row['language_detector'])
            self.assertIsNone(row['language_detector_version'])
            self.assertIsNone(row['language_detection_scope'])
            if row['primary_language'] == '<unknown>':
                self.assertIsNone(row['url_is_estimate'])
                self.assertEqual(row['language_assignment_basis'], 'residual_bucket_classification_unavailable')
            else:
                self.assertFalse(row['url_is_estimate'])
        definitions = result['measurement_definitions']
        self.assertEqual(definitions['page_captures']['unit'], 'captures')
        self.assertTrue(definitions['digest_estimated_cardinality']['is_estimate'])
        self.assertEqual(definitions['pages_percent_of_crawl_decimal']['decimal_places'], 4)
        self.assertTrue(all(cc.SOURCE_COMMIT in url for url in result['interpretation_evidence'].values()))

    def test_estimated_digest_is_not_given_false_exact_invariants(self):
        result = self.validate()
        self.assertGreater(result['crawl_summaries'][0]['digest_estimated_cardinality'], result['crawl_summaries'][0]['page_captures'])
        self.assertEqual(self.validate(monthly=self.monthly.replace(b'101,100,95', b'999999999999,100,95'))['crawl_summaries'][0]['digest_estimated_cardinality'], 999999999999)

    def test_url_cardinalities_are_not_summed_across_languages(self):
        result = self.validate()
        per_language = sum(int(row['native_fields']['urls']) for row in result['language_observations'] if row['crawl_id'] == cc.ALLOWED_CRAWLS[0])
        self.assertEqual(per_language, 98)
        self.assertEqual(result['crawl_summaries'][0]['url_cardinality'], 95)

    def test_url_cardinality_still_cannot_exceed_its_own_capture_count(self):
        self.reject(self.languages.replace(b'eng,50,49,50.0000', b'eng,50,51,50.0000'), message='URL cardinality')
        self.reject(monthly=self.monthly.replace(b'101,100,95', b'101,100,101'), message='URL cardinality')

    def test_rounded_percentages_need_not_sum_to_exactly_one_hundred(self):
        rows = [row for row in self.validate()['language_observations'] if row['crawl_id'] == cc.ALLOWED_CRAWLS[1]]
        self.assertEqual([row['pages_percent_of_crawl_decimal'] for row in rows], ['33.3333'] * 3)

    def test_percentage_tolerance_rejects_outside_half_unit(self):
        self.reject(self.languages.replace(b'33.3333', b'33.3334'), message='rounding tolerance')

    def test_percentage_tolerance_accepts_exact_boundary(self):
        raw = self.languages.replace(b'<unknown>,25,25,25.0000', b'<unknown>,0,0,0.0000')
        raw = raw.replace(b'eng,50,49,50.0000', b'eng,1,1,0.0001').replace(b'zho,25,24,25.0000', b'zho,1999999,1999999,99.9999')
        monthly = self.monthly.replace(b'101,100,95', b'2000001,2000000,2000000')
        self.assertEqual(self.validate(raw, monthly)['crawl_summaries'][0]['page_captures'], 2000000)

    def test_decimal_validation_is_independent_of_caller_precision(self):
        expected = self.validate()
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(self.validate(), expected)
            self.assertEqual(context.prec, 2)

    def test_repeated_import_is_idempotent(self):
        self.assertEqual(self.validate(), self.validate())
        first = self.validate()
        second = self.validate(observed_at_utc='2026-10-08T04:09:49Z')
        self.assertEqual(first['statistics_revision_id'], second['statistics_revision_id'])
        self.assertEqual(first['language_observations'], second['language_observations'])

    def test_changed_input_bytes_change_observation_revision_not_crawl_entity(self):
        first = self.validate()
        # Reordering leaves source-native values intact but changes supplied bytes.
        lines = self.languages.splitlines()
        second = self.validate(b'\n'.join([lines[0], *reversed(lines[1:])]) + b'\n')
        self.assertNotEqual(first['statistics_revision_id'], second['statistics_revision_id'])
        self.assertNotEqual(first['language_observations'][0]['observation_id'], second['language_observations'][0]['observation_id'])
        self.assertEqual([row['crawl_entity_id'] for row in first['crawl_summaries']], [row['crawl_entity_id'] for row in second['crawl_summaries']])
        self.assertEqual([row['native_fields'] for row in first['language_observations']], [row['native_fields'] for row in second['language_observations']])

    def test_synthetic_ids_are_explicitly_separate(self):
        result = self.validate()
        ids = [row['observation_id'] for row in result['language_observations'] + result['crawl_summaries']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(value.startswith('synthetic-commoncrawl:') for value in ids))
        self.assertTrue(all(row['crawl_entity_id'].startswith('synthetic-commoncrawl:') for row in result['crawl_summaries']))

    def test_default_mode_rejects_unpinned_synthetic_bytes(self):
        with self.assertRaisesRegex(cc.StatisticsInputError, 'pinned source SHA-256'):
            cc.validate_statistics_bytes(self.languages, self.monthly)

    def test_pins_paths_and_exact_commit_are_fixed(self):
        self.assertEqual(cc.SOURCE_COMMIT, '1053c982a91ba0bb4323c5f00ec3230d9cd54e4b')
        self.assertEqual(cc.SOURCE_SHA256, {
            'plots/languages.csv': '4f3b987a60d72a356c480d788a930388ebe05225307aec7fc280513f6f9b0cff',
            'plots/crawlsize/monthly.csv': 'b49fb0e4acd9cd3a4676cc4bad17eca9645e38dcecfea1dfc3f2436a1c7b98a7',
        })

    def test_synthetic_hashes_do_not_claim_source_byte_acquisition(self):
        result = self.validate()
        for artifact, raw in zip(result['source_artifacts'], (self.languages, self.monthly)):
            self.assertEqual(artifact['supplied_bytes_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(artifact['supplied_byte_count'], len(raw))
            self.assertIsNone(artifact['source_sha256'])
            self.assertIsNone(artifact['source_commit'])
            self.assertIsNone(artifact['source_path'])
            self.assertFalse(artifact['source_byte_pin_verified'])
            self.assertIsNone(artifact['source_acquired_at_utc'])
            self.assertIsNone(artifact['source_publication_at'])
            self.assertIn(cc.SOURCE_COMMIT, artifact['expected_source_url'])
        self.assertFalse(result['source_bytes_acquired_by_reader'])

    def test_synthetic_dates_are_unknown_despite_known_crawl_labels(self):
        for row in self.validate()['crawl_summaries']:
            for field in ('capture_started_on', 'capture_ended_on', 'released_on', 'date_precision', 'date_evidence_url', 'source_timezone', 'underlying_content_published_at', 'statistics_published_at'):
                self.assertIsNone(row[field], field)
            self.assertEqual(row['date_basis'], 'synthetic_dates_unknown')

    def test_verified_metadata_keeps_release_capture_and_publication_distinct(self):
        expected = [('2026-07-07', '2026-07-25', '2026-07-28'), ('2026-08-07', '2026-08-20', '2026-08-24'), ('2026-09-04', '2026-09-17', '2026-09-19')]
        for crawl, dates in zip(cc.ALLOWED_CRAWLS, expected):
            row = cc._dates(crawl, False)
            self.assertEqual((row['capture_started_on'], row['capture_ended_on'], row['released_on']), dates)
            self.assertEqual(row['date_precision'], 'day')
            self.assertIsNone(row['source_timezone'])
            self.assertIsNone(row['underlying_content_published_at'])
            self.assertIsNone(row['statistics_published_at'])
            self.assertTrue(row['date_evidence_url'].startswith('https://commoncrawl.org/blog/'))

    def test_invalid_or_reversed_pinned_dates_fail_closed(self):
        for dates in [('2026-02-30', '2026-07-25', '2026-07-28'), ('2026-07-26', '2026-07-25', '2026-07-28'), ('2026-07-07', '2026-07-25', '2026-07-24')]:
            with self.subTest(dates=dates), patch.dict(cc.CRAWL_DATES, {cc.ALLOWED_CRAWLS[0]: dates}):
                self.reject(message='pinned crawl date')

    def test_observation_timestamp_is_optional_separate_and_validated(self):
        self.assertIsNone(self.validate()['observed_at_utc'])
        self.assertEqual(self.validate(observed_at_utc='2026-10-08T04:09:49Z')['observed_at_basis'], 'caller_reported_not_source_publication')
        for timestamp in ('2026-02-30T00:00:00Z', '2026-10-08', '2026-10-08T00:00:00+00:00', '2026-10-08T00:00:00.000Z', True, 42):
            with self.subTest(timestamp=timestamp), self.assertRaises(cc.StatisticsInputError):
                self.validate(observed_at_utc=timestamp)

    def test_rights_stay_unknown_and_code_license_is_not_inherited(self):
        result = self.validate()
        self.assertEqual(result['rights']['repository_code_license'], 'Apache-2.0')
        self.assertFalse(result['rights']['code_license_applies_to_csv_or_underlying_pages'])
        self.assertIsNone(result['rights']['csv_specific_license'])
        self.assertEqual(result['rights']['csv_redistribution_rights'], 'unknown')
        self.assertEqual(result['rights']['underlying_pages_rights'], 'unknown')
        for row in result['source_artifacts']:
            self.assertIsNone(row['csv_specific_license'])
            self.assertEqual(row['csv_redistribution_rights'], 'unknown')

    def test_no_admission_or_unsupported_derived_quantities(self):
        result = self.validate()
        self.assertEqual(result['status'], 'experimental_review_records_not_admitted')
        self.assertFalse(result['canonical_import_enabled'])
        self.assertFalse(result['network_access_performed'])
        self.assertFalse(result['source_execution_performed'])
        forbidden = {'licensed_tokens', 'synthetic_fraction', 'human_fraction', 'unique_usable_supply', 'pdoom', 'usable_training_tokens'}
        def visit(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden & set(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(result)
        json.dumps(result, allow_nan=False)

    def test_exact_headers_reject_rename_reorder_duplicate_and_extra_columns(self):
        for raw in (self.languages.replace(b'%pages/crawl', b'percent', 1),
                    self.languages.replace(b'pages,urls', b'urls,pages', 1),
                    self.languages.replace(b'pages,urls', b'pages,pages', 1),
                    self.languages.replace(b'%pages/crawl\n', b'%pages/crawl,extra\n', 1)):
            with self.subTest(raw=raw[:80]):
                self.reject(raw, message='header')
        self.reject(monthly=self.monthly.replace(b'digest estim.', b'digest'), message='header')

    def test_row_missing_extra_empty_fields_and_blank_rows_rejected(self):
        for raw in (self.languages.replace(b'eng,50,49,50.0000', b'eng,50,49'),
                    self.languages.replace(b'eng,50,49,50.0000', b'eng,50,49,50.0000,extra'),
                    self.languages.replace(b'eng,50,49,50.0000', b'eng,,49,50.0000'),
                    self.languages + b'\n'):
            self.reject(raw)

    def test_duplicate_languages_rejected_even_when_identical(self):
        self.reject(self.languages + b'CC-MAIN-2026-30,eng,50,49,50.0000\n', message='duplicate')
        self.reject(self.languages + b'CC-MAIN-2026-30,eng,1,1,1.0000\n', message='duplicate')
        self.reject(self.languages + b'CC-MAIN-2012,<unknown>,10,9,100.0000\n', message='duplicate')

    def test_duplicate_monthly_crawl_rejected_even_when_identical(self):
        self.reject(monthly=self.monthly + b'CC-MAIN-2026-30,101,100,95\n', message='duplicate')
        self.reject(monthly=self.monthly + b'CC-MAIN-2012,12,10,9\n', message='duplicate')

    def test_missing_selected_crawl_in_either_input_rejected(self):
        self.reject(b'\n'.join(line for line in self.languages.splitlines() if b'2026-34' not in line) + b'\n', message='all three')
        self.reject(monthly=b'\n'.join(line for line in self.monthly.splitlines() if b'2026-34' not in line) + b'\n', message='all three')

    def test_historical_and_nonselected_rows_are_validated_but_filtered(self):
        result = self.validate(self.languages + b'CC-MAIN-2025-13,eng,1,1,100.0000\n', self.monthly + b'CC-MAIN-2025-13,2,1,1\n')
        self.assertEqual(result['crawl_count'], 3)
        self.assertEqual(len(result['language_observations']), 9)
        self.reject(self.languages.replace(b'CC-MAIN-2012,<unknown>,10,10', b'CC-MAIN-2012,<unknown>,NaN,9'))

    def test_native_crawl_identifier_validation(self):
        for token in (b'CC-MAIN-2026-00', b'CC-MAIN-2026-54', b'2026-30', b'cc-main-2026-30', b'=cmd()', b'CC-MAIN-2026-30 '):
            self.reject(self.languages.replace(b'CC-MAIN-2012', token), message='crawl identifier')

    def test_language_labels_are_inert_bounded_native_tokens(self):
        for token in (b'English', b'ENG', b'unknown', b'<script>', b'=cmd()', b'eng; rm -rf /'):
            self.reject(self.languages.replace(b',eng,', b',' + token + b','), message='language label')

    def test_counts_reject_nonfinite_decimal_exponent_signed_and_boolean_tokens(self):
        for token in (b'NaN', b'Infinity', b'-Infinity', b'1e2', b'50.0', b'-1', b'+50', b'050', b'true', b'False', b' 50', b'50 '):
            with self.subTest(token=token):
                self.reject(self.languages.replace(b'eng,50,49', b'eng,' + token + b',49'), message='integer')
                self.reject(monthly=self.monthly.replace(b'101,100,95', token + b',100,95'), message='integer')

    def test_decimal_percent_rejects_nonfinite_exponent_and_wrong_precision(self):
        for token in (b'NaN', b'Infinity', b'-0.0000', b'5e1', b'50', b'50.0', b'50.00000', b'100.0001', b'101.0000', b'050.0000', b'true'):
            self.reject(self.languages.replace(b'50.0000', token), message='percentage')

    def test_count_magnitude_and_zero_monthly_denominator_rejected(self):
        self.reject(self.languages.replace(b'eng,50,49', b'eng,1000000000001,49'), message='magnitude')
        self.reject(monthly=self.monthly.replace(b'101,100,95', b'1000000000001,100,95'), message='magnitude')
        self.reject(monthly=self.monthly.replace(b'101,100,95', b'0,0,0'), message='magnitude')

    def test_utf8_bom_control_characters_and_multiline_fields_rejected(self):
        for raw in (b'\xff' + self.languages, b'\xef\xbb\xbf' + self.languages,
                    self.languages.replace(b'eng', b'en\x00g'),
                    self.languages.replace(b'eng', b'"en\ng"'),
                    self.languages.replace(b'eng', b'en\tg')):
            self.reject(raw)

    def test_malformed_csv_and_empty_inputs_rejected(self):
        self.reject(self.languages.replace(b'eng,50', b'"eng,50'))
        self.reject(b'')
        self.reject(monthly=b'')
        self.reject(b','.join(value.encode() for value in cc.LANGUAGES_HEADER) + b'\n', message='data rows')
        self.reject('not bytes')

    def test_byte_row_field_line_and_language_count_limits(self):
        self.reject(b'x' * (cc.MAX_BYTES[cc.LANGUAGES_PATH] + 1), message='byte limit')
        self.reject(monthly=b'x' * (cc.MAX_BYTES[cc.MONTHLY_PATH] + 1), message='byte limit')
        self.reject(self.languages.replace(b'eng', b'e' * (cc.MAX_FIELD_BYTES + 1)), message='field')
        self.reject(self.languages.replace(b'eng', b'e' * (cc.MAX_PHYSICAL_LINE_BYTES + 1)), message='physical line')
        with patch.dict(cc.MAX_ROWS, {cc.LANGUAGES_PATH: 9}):
            self.reject(message='row count')
        with patch.dict(cc.MAX_ROWS, {cc.MONTHLY_PATH: 3}):
            self.reject(message='row count')
        with patch.object(cc, 'MAX_LANGUAGES_PER_CRAWL', 2):
            self.reject(message='languages per crawl')

    def test_synthetic_flag_is_not_truthiness_coerced(self):
        for value in (1, 0, 'true', None):
            with self.assertRaisesRegex(cc.StatisticsInputError, 'boolean'):
                cc.validate_statistics_bytes(self.languages, self.monthly, synthetic_fixture=value)

    def test_safe_read_agrees_with_byte_validation(self):
        self.assertEqual(cc.read_statistics(LANGUAGES, MONTHLY, synthetic_fixture=True), self.validate())

    def test_path_urls_traversal_stdio_control_and_network_style_rejected(self):
        for path in ('https://example.com/a.csv', '-', '../languages.csv', 'a/../b.csv', '//host/a.csv', '\\\\host\\a', '\x00bad', '/', '.', 'a' * 4097, '/'.join(['a'] * 65), b'bytes.csv', None):
            with self.subTest(path=path), self.assertRaises(cc.StatisticsInputError):
                cc.read_statistics(path, MONTHLY, synthetic_fixture=True)

    def test_symlink_file_and_ancestor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'file-link').symlink_to(LANGUAGES)
            (root / 'directory-link').symlink_to(FIXTURES, target_is_directory=True)
            for path in (root / 'file-link', root / 'directory-link' / LANGUAGES.name):
                with self.assertRaises(cc.StatisticsInputError):
                    cc.read_statistics(path, MONTHLY, synthetic_fixture=True)

    def test_directory_device_fifo_and_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.mkfifo(root / 'fifo')
            for path in (root, '/dev/null', root / 'fifo', root / 'missing'):
                with self.subTest(path=path), self.assertRaises(cc.StatisticsInputError):
                    cc.read_statistics(path, MONTHLY, synthetic_fixture=True)

    def test_socket_file_mode_is_rejected_without_creating_socket(self):
        with patch.object(cc.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFSOCK, st_size=1)):
            with self.assertRaisesRegex(cc.StatisticsInputError, 'regular file'):
                cc.read_statistics(LANGUAGES, MONTHLY, synthetic_fixture=True)

    def test_regular_file_byte_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'large.csv'
            with path.open('wb') as stream:
                stream.truncate(cc.MAX_BYTES[cc.LANGUAGES_PATH] + 1)
            with self.assertRaisesRegex(cc.StatisticsInputError, 'regular file'):
                cc.read_statistics(path, MONTHLY, synthetic_fixture=True)

    def test_file_growth_is_bounded_even_if_initial_stat_was_small(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'grown.csv'
            with path.open('wb') as stream:
                stream.truncate(cc.MAX_BYTES[cc.LANGUAGES_PATH] + 1)
            info = SimpleNamespace(st_mode=stat.S_IFREG, st_size=1)
            with patch.object(cc.os, 'fstat', return_value=info):
                with self.assertRaisesRegex(cc.StatisticsInputError, 'grew beyond'):
                    cc.read_statistics(path, MONTHLY, synthetic_fixture=True)

    def test_empty_regular_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'empty.csv'
            path.touch()
            with self.assertRaisesRegex(cc.StatisticsInputError, 'nonempty regular file'):
                cc.read_statistics(path, MONTHLY, synthetic_fixture=True)

    def test_unsupported_safe_open_platform_fails_closed(self):
        with patch.object(cc.os, 'name', 'nt'), self.assertRaisesRegex(cc.StatisticsInputError, 'safe regular-file'):
            cc.read_statistics(str(LANGUAGES), str(MONTHLY), synthetic_fixture=True)

    def test_no_network_or_process_execution(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), patch('subprocess.Popen', side_effect=AssertionError('process forbidden')):
            result = cc.read_statistics(LANGUAGES, MONTHLY, synthetic_fixture=True)
        self.assertEqual(result['crawl_count'], 3)

    def test_cli_success_and_fail_closed_default(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cc.main([str(LANGUAGES), str(MONTHLY), '--synthetic-fixture']), 0)
        self.assertTrue(json.loads(output.getvalue())['synthetic'])
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
            cc.main([str(LANGUAGES), str(MONTHLY)])
        self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
