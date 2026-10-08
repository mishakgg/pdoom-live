"""Offline curated BARN excerpt and adversarial in-memory mutation regressions."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import validate_barn_table as barn

FIXTURE = HERE / 'fixtures/robotics-physical/barn-2024-table-ii.json'


class BarnTableTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def validate(self, document=None):
        return barn.validate_table_bytes(json.dumps(self.document if document is None else document).encode())

    def reject(self, document=None, message=None):
        with self.assertRaisesRegex(barn.TableInputError, message or '.'):
            self.validate(document)

    def stable_result(self, result):
        return {key: value for key, value in result.items() if key != 'input_curated_json_sha256'}

    def course(self, team, course):
        return next(row for row in self.validate()['course_summaries']
                    if row['team_raw'] == team and row['course_number'] == course)

    def test_bundled_fixture_is_exact_curated_json_pin(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(len(raw), 6584)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         'f79a2b58fa8771b766890627bf59e9f710acb5af1da397510dfdf4763cc8bd5e')

    def test_all_sixty_cells_match_verified_transcription(self):
        expected = {
            'LiCS-KI': [['32', '31', '32', '27', '30'], ['37', '37', '40', '29', '32'], ['X'] * 5],
            'MLDA_EEE': [['68', 'X', '77', 'X', '70'], ['X', 'X', 'X', '85', '93'], ['X'] * 5],
            'AIMS': [['92', '88', 'X', 'X', 'X'], ['X'] * 5, ['119', '118', '126', 'X', 'X']],
            'EIT-NUS': [['X'] * 5, ['X'] * 5, ['X'] * 5],
        }
        actual = self.validate()['attempts']
        self.assertEqual(len(actual), 60)
        self.assertEqual(len({row['observation_id'] for row in actual}), 60)
        for row in actual:
            self.assertEqual(row['outcome_raw'], expected[row['team_raw']][row['course_number'] - 1]
                             [row['reported_position_in_course_cell'] - 1])
        self.assertEqual(sum(row['status'] == 'successful' for row in actual), 20)
        self.assertEqual(sum(row['status'] == 'failed' for row in actual), 40)

    def test_all_attempts_and_credit_denominators_stay_separate(self):
        expected = {'LiCS-KI': (10, 6), 'MLDA_EEE': (5, 5), 'AIMS': (5, 5), 'EIT-NUS': (0, 0)}
        result = self.validate()
        self.assertEqual(len(result['course_summaries']), 12)
        self.assertEqual(len(result['team_summaries']), 4)
        for row in result['team_summaries']:
            all_successful, credited = expected[row['team_raw']]
            self.assertEqual(row['all_reported_attempts'],
                             {'successful': all_successful, 'failed': 15 - all_successful, 'denominator': 15})
            self.assertEqual(row['credited_subset'], {'successful': credited, 'denominator': 9})
        for row in result['course_summaries']:
            self.assertEqual(row['all_reported_attempts']['denominator'], 5)
            self.assertEqual(row['credited_subset']['denominator'], 3)

    def test_failures_are_not_missing_or_zero_time(self):
        for row in self.validate()['attempts']:
            self.assertIsNone(row['failure_cause'])
            if row['outcome_raw'] == 'X':
                self.assertEqual(row['status'], 'failed')
                self.assertIsNone(row['completion_time_seconds'])
            else:
                self.assertEqual(row['status'], 'successful')
                self.assertEqual(row['completion_time_seconds'], int(row['outcome_raw']))
                self.assertGreater(row['completion_time_seconds'], 0)

    def test_positions_are_not_claimed_to_be_chronological_or_ranked(self):
        result = self.validate()
        first_course = [row for row in result['attempts'] if row['team_raw'] == 'LiCS-KI' and row['course_number'] == 1]
        self.assertEqual([row['completion_time_seconds'] for row in first_course], [32, 31, 32, 27, 30])
        self.assertTrue(all(row['chronological_attempt_number'] is None for row in result['attempts']))
        self.assertEqual(result['interpretation']['position_order'], 'source_display_order_not_established_chronological')

    def test_unknown_protocol_observations_stay_null(self):
        result = self.validate()
        for row in result['attempts']:
            for field in ('reset_count', 'practice_attempt_count', 'checkpoint_id', 'started_at',
                          'native_run_id', 'observed_intervention_count', 'hardware_instance_id',
                          'exact_system_version', 'reset_duration_seconds'):
                self.assertIsNone(row[field])
        self.assertEqual(result['interpretation']['protocol_no_human_intervention'],
                         'protocol_requirement_not_observed_intervention_measurement')

    def test_tied_cutoff_does_not_fabricate_selected_row_identity(self):
        credit = self.course('LiCS-KI', 2)['credited_subset']
        self.assertEqual(credit['selected_successful_times_seconds'], [29, 32, 37])
        self.assertEqual(credit['certain_successful_reported_positions'], [4, 5])
        self.assertEqual(credit['ambiguous_boundary_reported_positions'], [1, 2])
        self.assertEqual(credit['boundary_slots_to_choose'], 1)
        self.assertIsNone(credit['selected_successful_reported_positions'])
        self.assertTrue(credit['row_membership_ambiguous'])
        self.assertTrue(all('credited' not in row for row in self.validate()['attempts']))

    def test_unambiguous_reconstruction_is_explicitly_rule_derived(self):
        credit = self.course('LiCS-KI', 1)['credited_subset']
        self.assertEqual(credit['selected_successful_reported_positions'], [2, 4, 5])
        self.assertEqual(credit['selected_successful_times_seconds'], [27, 30, 31])
        self.assertEqual(credit['basis'], 'rule_reconstruction_not_published_run_membership')
        self.assertFalse(credit['row_membership_ambiguous'])

    def test_no_credit_failure_identities_are_invented(self):
        credit = self.course('EIT-NUS', 1)['credited_subset']
        self.assertEqual(credit['successful'], 0)
        self.assertEqual(credit['failed_credit_slots'], 3)
        self.assertEqual(credit['selected_successful_reported_positions'], [])
        self.assertIsNone(credit['selected_failed_reported_positions'])
        self.assertTrue(credit['row_membership_ambiguous'])
        credit = self.course('AIMS', 1)['credited_subset']
        self.assertEqual(credit['selected_successful_reported_positions'], [1, 2])
        self.assertEqual(credit['failed_credit_slots'], 1)

    def test_published_course_means_preserved_not_replaced_by_fastest_three(self):
        for course, mean, fastest_total in [(1, 30, 88), (2, 35, 98)]:
            row = self.course('LiCS-KI', course)
            self.assertEqual(row['published_average_raw'], str(mean))
            self.assertEqual(row['published_average_seconds'], mean)
            self.assertEqual(sum(row['credited_subset']['selected_successful_times_seconds']), fastest_total)
            self.assertNotEqual(mean * 3, fastest_total)
            self.assertEqual(row['published_average_basis'],
                             'source_reported_preserved_independently_not_recomputed_from_credit_subset')
        self.assertEqual(self.course('LiCS-KI', 3)['published_average_raw'], 'NA')
        self.assertIsNone(self.course('LiCS-KI', 3)['published_average_seconds'])

    def test_published_tiebreaks_and_rank_remain_raw_source_claims(self):
        rows = {row['team_raw']: row for row in self.validate()['team_summaries']}
        self.assertEqual(rows['MLDA_EEE']['published_summary']['success_total_raw'], '5/9 (79)')
        self.assertEqual(rows['AIMS']['published_summary']['success_total_raw'], '5/9 (109)')
        self.assertEqual(rows['MLDA_EEE']['published_parenthetical_time_seconds'], 79)
        self.assertEqual(rows['AIMS']['published_parenthetical_time_seconds'], 109)
        self.assertEqual(rows['AIMS']['published_summary']['rank'], 3)
        self.assertIsNone(rows['LiCS-KI']['published_parenthetical_time_seconds'])

    def test_no_admission_source_execution_or_generalization(self):
        result = self.validate()
        self.assertEqual(result['status'], 'experimental_review_records_not_admitted')
        self.assertFalse(result['canonical_import_enabled'])
        self.assertFalse(result['network_access_performed'])
        self.assertFalse(result['manuscript_bytes_acquired_by_reader'])
        self.assertEqual(result['event_count'], 1)
        self.assertEqual(result['interpretation']['comparison_scope'], 'one_physical_event_no_simulation_or_cross_year_pooling')
        for field in ('pdoom', 'score', 'simulation_trials', 'pooled_reliability'):
            self.assertNotIn(field, result)

    def test_rights_attribution_version_and_null_manuscript_hash_preserved(self):
        result = self.validate()
        self.assertEqual(result['source'], self.document['source'])
        self.assertEqual(result['source']['artifact_version'], barn.SOURCE_VERSION)
        self.assertEqual(result['source']['license_spdx'], 'CC-BY-4.0')
        self.assertEqual(result['source']['license_url'], barn.LICENSE_URL)
        self.assertEqual(len(result['source']['authors']), 19)
        self.assertIsNone(result['source']['manuscript_sha256'])
        self.assertTrue(result['source']['attribution'])
        self.assertTrue(result['source']['changes'])

    def test_hashes_are_qualified_as_curated_json_only(self):
        raw = FIXTURE.read_bytes()
        result = barn.validate_table_bytes(raw)
        self.assertEqual(result['input_curated_json_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['hash_scope'], 'curated_JSON_only_not_HTML_PDF_or_full_manuscript')
        self.assertEqual(len(result['normalized_curated_excerpt_sha256']), 64)
        self.document['source']['manuscript_sha256'] = result['input_curated_json_sha256']
        self.reject(message='manuscript hash must be null')

    def test_repeated_identical_rows_and_summaries_are_idempotent(self):
        expected = self.validate()
        self.document['rows'] += deepcopy(self.document['rows'])
        self.document['published_team_summaries'] += deepcopy(self.document['published_team_summaries'])
        actual = self.validate()
        self.assertEqual(self.stable_result(actual), self.stable_result(expected))
        self.assertNotEqual(actual['input_curated_json_sha256'], expected['input_curated_json_sha256'])
        self.assertEqual(len(actual['attempts']), 60)

    def test_serialized_row_order_and_whitespace_do_not_change_identity(self):
        expected = self.validate()
        self.document['rows'].reverse()
        self.document['published_team_summaries'].reverse()
        actual = barn.validate_table_bytes(json.dumps(self.document, indent=2).encode())
        self.assertEqual(self.stable_result(actual), self.stable_result(expected))

    def test_conflicting_coordinate_duplicate_rejected(self):
        extra = deepcopy(self.document['rows'][0])
        extra[3] = '33'
        self.document['rows'].append(extra)
        self.reject(message='conflicting duplicate event/version/team/course/reported-position')

    def test_missing_coordinate_cannot_be_replaced_by_duplicate(self):
        self.document['rows'][1] = deepcopy(self.document['rows'][0])
        self.reject(message='all 60 unique')

    def test_conflicting_team_summary_rejected(self):
        extra = deepcopy(self.document['published_team_summaries'][0])
        extra['course_average_times_raw'] = '29/35/NA'
        self.document['published_team_summaries'].append(extra)
        self.reject(message='conflicting duplicate team summary')

    def test_version_and_event_expansion_require_reconciliation(self):
        for field, value in [('artifact_version', '2407.01862v2'), ('artifact_version', '2407.01862'),
                             ('url', 'https://arxiv.org/html/2407.01862v2')]:
            altered = deepcopy(self.document)
            altered['source'][field] = value
            self.reject(altered)
        for event in ('barn-2025-physical-finals', 'barn-2024-simulation', None, True):
            altered = deepcopy(self.document)
            altered['event_id'] = event
            self.reject(altered, 'unsupported event')
        self.assertIn('new_versions_require_explicit_trial_reconciliation',
                      self.validate()['interpretation']['version_policy'])

    def test_coordinate_ids_include_event_and_pinned_source_version(self):
        for row in self.validate()['attempts']:
            self.assertEqual(row['observation_id'],
                             f"{barn.EVENT_ID}:{barn.SOURCE_VERSION}:{row['team_id']}:course-{row['course_number']}:position-{row['reported_position_in_course_cell']}")

    def test_changed_content_changes_excerpt_hash_not_trial_count(self):
        expected = self.validate()
        self.document['rows'][0][3] = '33'
        actual = self.validate()
        self.assertNotEqual(actual['normalized_curated_excerpt_sha256'], expected['normalized_curated_excerpt_sha256'])
        self.assertEqual([row['observation_id'] for row in actual['attempts']],
                         [row['observation_id'] for row in expected['attempts']])
        self.assertIn('not_native_run_ids_or_cross_version_trial_identity', actual['interpretation']['identity_scope'])
        # Structural validity does not certify changed content against a source.
        self.assertIn('does_not_verify_primary_source_truth', actual['interpretation']['source_verification'])

    def test_invalid_numbers_cells_and_coordinates(self):
        for index, values in [(1, (True, False, 1.0, '1', 0, -1, 4, None)),
                              (2, (True, False, 1.0, '1', 0, -1, 6, None)),
                              (3, (True, False, 32, 32.0, None, '', '0', '-1', '01', 'NA', 'x',
                                   '1e3', '1.1', 'Infinity', 'NaN', '86401', '９', [], {}))]:
            for value in values:
                with self.subTest(index=index, value=value):
                    altered = deepcopy(self.document)
                    altered['rows'][0][index] = value
                    self.reject(altered)

    def test_no_extra_or_missing_fields(self):
        selectors = [lambda d: d, lambda d: d['source'], lambda d: d['row_interpretation'],
                     lambda d: d['published_team_summaries'][0]]
        for select in selectors:
            altered = deepcopy(self.document)
            select(altered)['robot_control_command'] = 'do not execute'
            self.reject(altered, 'unknown')
            altered = deepcopy(self.document)
            selected = select(altered)
            del selected[next(iter(selected))]
            self.reject(altered, 'missing')

    def test_malformed_row_shape_and_container_types(self):
        for row in ([], self.document['rows'][0] + ['extra'], {}, 'row', None):
            altered = deepcopy(self.document)
            altered['rows'][0] = row
            self.reject(altered, 'four cells')
        for field, value in [('rows', {}), ('rows', None), ('published_team_summaries', {}),
                             ('source', []), ('row_interpretation', None), ('row_fields', list(reversed(barn.ROW_FIELDS)))]:
            altered = deepcopy(self.document)
            altered[field] = value
            self.reject(altered)

    def test_unknown_teams_and_summary_team_coverage(self):
        for team in ('LiCS KI', 'unknown', None, True, [], {}):
            altered = deepcopy(self.document)
            altered['rows'][0][0] = team
            self.reject(altered, 'unknown team')
            altered = deepcopy(self.document)
            altered['published_team_summaries'][0]['team_raw'] = team
            self.reject(altered, 'unknown summary team')
        self.document['published_team_summaries'][1] = deepcopy(self.document['published_team_summaries'][0])
        self.reject(message='one summary per team')

    def test_invalid_summary_numbers_and_counts(self):
        for value in ('10/15', '6/15', '5/9', '6/9 (0)', '6/9 (NaN)', '6/9 (86401)', 6, None, True):
            altered = deepcopy(self.document)
            altered['published_team_summaries'][0]['success_total_raw'] = value
            self.reject(altered)
        for value in (True, False, 1.0, 0, 5, '1', None):
            altered = deepcopy(self.document)
            altered['published_team_summaries'][0]['rank'] = value
            self.reject(altered)
        self.document['published_team_summaries'][0]['rank'] = 2
        self.reject(message='ranks must be distinct')

    def test_average_missingness_and_count_not_conflated(self):
        for value in ('30/35', '30/35/NA/NA', 'NA/35/NA', '30/35/0', '30/35/17',
                      '30/35/null', '30.4/35/NA', '30/35/', '', True):
            altered = deepcopy(self.document)
            altered['published_team_summaries'][0]['course_average_times_raw'] = value
            self.reject(altered)
        # A positive published mean is retained independently, not certified by
        # recomputation. The immutable fixture/checker pin guards the real bytes.
        self.document['published_team_summaries'][0]['course_average_times_raw'] = '29/35/NA'
        self.assertEqual(self.course('LiCS-KI', 1)['published_average_seconds'], 29)

    def test_fixed_url_allowlists_reject_alternate_routes(self):
        for url in ('http://arxiv.org/html/2407.01862v1', 'https://arxiv.org/html/2407.01862',
                    'file:///etc/passwd', 'https://127.0.0.1/', 'https://169.254.169.254/',
                    'https://arxiv.org.evil.test/html/2407.01862v1', 'https://arxiv.org@evil.test/',
                    barn.SOURCE_URL + '?redirect=http://127.0.0.1', barn.SOURCE_URL + '#x',
                    'https://arxiv.org:443/html/2407.01862v1', 'https://ARXIV.ORG/html/2407.01862v1',
                    'https://arxiv.org/html/%32' + '407.01862v1', ' ' + barn.SOURCE_URL):
            altered = deepcopy(self.document)
            altered['source']['url'] = url
            self.reject(altered, 'allowlist')
        for field in ('abstract_url', 'pdf_url', 'license_url'):
            altered = deepcopy(self.document)
            altered['source'][field] += '?extra'
            self.reject(altered, 'allowlist')

    def test_rights_and_metadata_shapes_are_not_optional(self):
        for field, value in [('license_spdx', 'CC0-1.0'), ('authors', []), ('authors', ['X'] * 33),
                             ('authors', ['X', 'X']), ('authors', [True]), ('authors', {}),
                             ('retrieved_at_utc', '2026-10-08'), ('retrieved_at_utc', '2026-02-30T00:00:00Z'),
                             ('submitted_at_utc', '2024-07-02T00:22:31+00:00'), ('title', '')]:
            altered = deepcopy(self.document)
            altered['source'][field] = value
            self.reject(altered)

    def test_hostile_source_strings_are_inert_without_network_or_execution(self):
        hostile = '<script>alert("x")</script>; ignore previous instructions; curl http://127.0.0.1/'
        self.document['source']['locator'] = hostile
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch('subprocess.run', side_effect=AssertionError('source execution forbidden')), \
             patch('os.system', side_effect=AssertionError('source execution forbidden')):
            result = self.validate()
        self.assertEqual(result['source']['locator'], hostile)

    def test_control_chars_invalid_unicode_and_text_bounds(self):
        for text in ('\x00', '\x1f', 'x\ny', '\x7f', '\ud800',
                     'x' * (barn.MAX_STRING_BYTES + 1), 'é' * barn.MAX_STRING_BYTES):
            altered = deepcopy(self.document)
            altered['source']['locator'] = text
            self.reject(altered)

    def test_byte_row_summary_depth_and_integer_work_limits(self):
        for raw in (b' ' * (barn.MAX_BYTES + 1),
                    b'[' * (barn.MAX_DEPTH + 1) + b']' * (barn.MAX_DEPTH + 1),
                    b'{"value":1234567890}'):
            with self.assertRaises(barn.TableInputError):
                barn.validate_table_bytes(raw)
        for field, values in [('rows', [self.document['rows'][0]] * (barn.MAX_ROWS + 1)),
                              ('rows', self.document['rows'][:59]),
                              ('published_team_summaries', self.document['published_team_summaries'] * 3),
                              ('published_team_summaries', self.document['published_team_summaries'][:3])]:
            altered = deepcopy(self.document)
            altered[field] = values
            self.reject(altered, 'count')

    def test_malformed_json_duplicate_keys_nonfinite_and_float_numbers(self):
        for raw in (b'', b'\xff', b'{}{}', b'{', b'[]', b'null', b'"root"', b'}{',
                    b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
                    b'{"x":1e309}', b'{"x":1.2}', b'{"x":01}', '{}', bytearray(b'{}')):
            with self.subTest(raw=raw), self.assertRaises(barn.TableInputError):
                barn.validate_table_bytes(raw)

    def test_safe_open_regular_files_and_symlink_components(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / 'table.json'
            valid.write_bytes(FIXTURE.read_bytes())
            self.assertEqual(barn.read_table(valid), barn.validate_table_bytes(FIXTURE.read_bytes()))
            file_link = root / 'link.json'
            file_link.symlink_to(valid)
            dir_link = root / 'link-dir'
            dir_link.symlink_to(root, target_is_directory=True)
            oversized = root / 'oversized.json'
            oversized.write_bytes(b' ' * (barn.MAX_BYTES + 1))
            for path in (file_link, dir_link / 'table.json', root, oversized, root / 'missing.json', '/dev/null'):
                with self.subTest(path=path), self.assertRaises(barn.TableInputError):
                    barn.read_table(path)

    @unittest.skipUnless(os.name == 'posix', 'safe-open contract requires POSIX')
    def test_fifo_and_special_file_modes_are_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fifo = root / 'pipe'
            os.mkfifo(fifo)
            with self.assertRaises(barn.TableInputError):
                barn.read_table(fifo)
            valid = root / 'table.json'
            valid.write_bytes(FIXTURE.read_bytes())
            info = os.stat(valid)
            for special_mode in (stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK):
                values = list(info)
                values[0] = special_mode | 0o600
                with patch.object(barn.os, 'fstat', return_value=os.stat_result(values)):
                    with self.assertRaises(barn.TableInputError):
                        barn.read_table(valid)

    def test_path_hazards_and_component_resource_limits(self):
        for path in ('https://example.invalid/table.json', '-', '', '/', '../table.json',
                     '/tmp/../table.json', '//host/table.json', '\\\\host\\table.json',
                     '/tmp/\x00file', '/tmp/new\nline', '/tmp/\x7f', '/tmp/\ud800', 'x' * 4097, 'é' * 3000,
                     '/'.join(['x'] * 65), None, b'/tmp/file', 123):
            with self.subTest(path=path), self.assertRaises(barn.TableInputError):
                barn.read_table(path)

    def test_safe_open_unavailable_fails_closed(self):
        with patch.object(barn.os, 'name', 'nt'):
            with self.assertRaisesRegex(barn.TableInputError, 'safe regular-file opening is unavailable'):
                barn.read_table(FIXTURE)

    def test_file_growth_after_stat_still_hits_byte_limit(self):
        real_fstat = os.fstat
        def report_small_file(descriptor):
            info = real_fstat(descriptor)
            values = list(info)
            values[6] = 1
            return os.stat_result(values)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'grew.json'
            path.write_bytes(b' ' * (barn.MAX_BYTES + 1))
            with patch.object(barn.os, 'fstat', side_effect=report_small_file):
                with self.assertRaisesRegex(barn.TableInputError, '64 KiB'):
                    barn.read_table(path)

    def test_cli_success_and_clean_invalid_input_failure(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(barn.main([str(FIXTURE)]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), barn.read_table(FIXTURE))
        stderr = StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            barn.main(['https://example.invalid/not-a-local-file.json'])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn('error:', stderr.getvalue())
        self.assertNotIn('Traceback', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
