"""Fixed real manual-ledger acceptance, separate from synthetic/adversarial tests.

No network or original PDF is used. Mutation tests are invented input examples,
not evidence of an additional NHTSA correction or a captured historical narrative.
"""
from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import read_nhtsa_corrections as reader

FIXTURES = TOOLS / 'tests' / 'fixtures' / 'incidents-near-misses'
LEDGER = FIXTURES / 'nhtsa-publication-corrections.manual.json'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def manual_document():
    return json.loads(LEDGER.read_bytes())


def synthetic_document():
    value = manual_document()
    value['input_kind'] = 'synthetic_test_ledger'
    value['document']['original_source_sha256'] = None
    value['document']['original_source_byte_count'] = None
    return value


class FixedCuratedAcceptanceTests(unittest.TestCase):
    """The attributed, fixed curated fixture alone is real-source acceptance."""

    @classmethod
    def setUpClass(cls):
        cls.raw = LEDGER.read_bytes()
        cls.result = reader.read_corrections(LEDGER)

    def test_exact_fixture_bytes_and_manifest(self):
        manifest = json.loads((FIXTURES / 'manifest.json').read_bytes())
        self.assertEqual(len(self.raw), reader.FIXTURE_BYTE_COUNT)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), reader.FIXTURE_SHA256)
        self.assertEqual(manifest['sha256'], reader.FIXTURE_SHA256)
        self.assertEqual(manifest['bytes'], reader.FIXTURE_BYTE_COUNT)
        self.assertEqual(manifest['fixture_file'], LEDGER.name)
        self.assertTrue(self.result['fixed_curated_fixture_verified'])
        self.assertFalse(self.result['synthetic'])

    def test_original_pdf_hash_is_distinct_from_manual_fixture_hash(self):
        artifact = self.result['source_artifacts'][0]
        manifest = json.loads((FIXTURES / 'manifest.json').read_bytes())
        self.assertEqual(artifact['original_source_sha256'], reader.SOURCE_SHA256)
        self.assertEqual(artifact['original_source_byte_count'], 529128)
        self.assertEqual(manifest['original_source_sha256'], reader.SOURCE_SHA256)
        self.assertNotEqual(reader.SOURCE_SHA256, reader.FIXTURE_SHA256)
        self.assertFalse(self.result['source_bytes_acquired_by_reader'])
        self.assertFalse(self.result['source_hashes_verified_by_reader'])
        self.assertFalse(manifest['source_pdf_in_fixture'])

    def test_exact_two_known_publication_corrections(self):
        self.assertEqual(self.result['assertion_count'], 2)
        self.assertEqual(self.result['assertion_revision_count'], 2)
        rows = {row['revisions'][0]['correction_kind']: row['revisions'][0] for row in self.result['assertions']}
        report = rows['report_field_publication_correction']
        self.assertEqual((report['report_id'], report['report_version']), ('34952-11803', 1))
        self.assertEqual(report['affected_field'], 'narrative')
        self.assertEqual(report['change_on'], '2026-08-27')
        release = rows['release_completeness_publication_correction']
        self.assertIsNone(release['report_id'])
        self.assertIsNone(release['report_version'])
        self.assertEqual(release['change_on'], '2026-06-15')
        self.assertEqual(release['affected_publication_on'], '2026-05-15')
        self.assertEqual(release['reports_received_on_or_before'], '2026-04-15')

    def test_all_claims_link_existing_asi005_without_extra_events_or_evidence(self):
        self.assertEqual(self.result['event_count_increment'], 0)
        self.assertEqual(self.result['independent_evidence_increment'], 0)
        for row in self.result['assertions']:
            self.assertEqual(row['record_type'], 'source_correction')
            self.assertEqual(row['prior_claim_id'], 'ASI005-F04')
            self.assertEqual(row['prior_artifact_id'], 'asi005_dictionary')
            self.assertEqual(row['prior_chain_id'], 'ASI-R02')
            self.assertEqual(row['event_count_increment'], 0)
            self.assertEqual(row['independent_evidence_increment'], 0)

    def test_edition_change_and_retrieval_clocks_stay_distinct(self):
        artifact = self.result['source_artifacts'][0]
        self.assertEqual(artifact['edition_on'], '2026-09-15')
        self.assertEqual(artifact['edition_date_precision'], 'day')
        self.assertIsNone(artifact['edition_source_timezone'])
        self.assertEqual(artifact['observations'][0]['source_retrieved_at_utc'], reader.SOURCE_RETRIEVED_AT_UTC)
        self.assertEqual(artifact['observations'][0]['source_http_last_modified_at_utc'], '2026-09-15T12:30:24Z')
        for row in self.result['assertions']:
            revision = row['revisions'][0]
            self.assertNotEqual(revision['change_on'], artifact['edition_on'])
            self.assertEqual(revision['change_date_precision'], 'day')
            self.assertIsNone(revision['change_source_timezone'])
            self.assertEqual(revision['locator']['physical_pdf_page'], 4)
            self.assertEqual(revision['locator']['table'], 1)

    def test_prior_content_unavailable_is_preserved_without_reconstruction(self):
        for row in self.result['assertions']:
            revision = row['revisions'][0]
            self.assertEqual(revision['previous_content'], {
                'availability': 'not_captured', 'captured_at_utc': None, 'content_sha256': None})
            self.assertIsNone(revision['previous_assertion_revision_id'])
            self.assertIsNone(revision['relation_to_previous_capture'])

    def test_rights_do_not_grant_manufacturer_narrative_or_repository_license(self):
        rights = self.result['rights']
        self.assertFalse(rights['manufacturer_narrative_reuse_grant_established'])
        self.assertFalse(rights['repository_license_applies_to_source_material'])
        self.assertIn('Agency-authored', rights['material'])
        self.assertIn('17 USC 105', rights['basis'])
        self.assertEqual(self.result['status'], 'experimental_review_not_admitted')
        self.assertFalse(self.result['canonical_import_enabled'])

    def test_output_excludes_private_or_unsupported_fields(self):
        forbidden = {'narrative', 'before_narrative', 'after_narrative', 'narrative_text',
                     'vin', 'name', 'address', 'contact', 'injury_count', 'injury_severity',
                     'engaged', 'engagement', 'causality', 'population_rate', 'pdoom', 'crash_records'}
        stack = [self.result]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                self.assertFalse(set(value) & forbidden)
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
        json.dumps(self.result, allow_nan=False)

    def test_identical_input_is_idempotent(self):
        self.assertEqual(reader.validate_ledger_bytes(self.raw), self.result)
        self.assertEqual(reader.append_ledger_bytes(self.raw, self.raw), self.result)
        self.assertEqual(reader.replay_ledger_bytes([self.raw] * reader.MAX_SNAPSHOTS), self.result)

    def test_no_network_process_or_write_calls(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
             patch.object(Path, 'write_bytes', side_effect=AssertionError('write forbidden')), \
             patch.object(Path, 'write_text', side_effect=AssertionError('write forbidden')):
            result = reader.read_corrections(LEDGER)
        self.assertFalse(result['network_access_performed'])
        self.assertFalse(result['source_execution_performed'])

    def test_actual_git_autocrlf_checkout_preserves_byte_pinned_fixture(self):
        if shutil.which('git') is None:
            self.fail('git is required for the actual autocrlf checkout regression')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixtures = root / 'fixtures'
            shutil.copytree(FIXTURES, fixtures)
            def git(*args):
                return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=root,
                                      check=True, capture_output=True, text=True, timeout=15)
            git('init', '--quiet')
            git('config', 'core.autocrlf', 'true')
            git('config', 'core.safecrlf', 'false')
            git('add', 'fixtures')
            before = {path.name: path.read_bytes() for path in fixtures.iterdir() if path.is_file()}
            for path in fixtures.iterdir():
                path.unlink()
            git('checkout-index', '--all', '--force')
            self.assertEqual(git('config', 'core.autocrlf').stdout.strip(), 'true')
            for name, raw in before.items():
                self.assertEqual((fixtures / name).read_bytes(), raw, name)
            self.assertEqual(hashlib.sha256((fixtures / LEDGER.name).read_bytes()).hexdigest(), reader.FIXTURE_SHA256)
            self.assertEqual(reader.read_corrections(fixtures / LEDGER.name), self.result)

    def test_cli_fixed_fixture_success(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(reader.main([str(LEDGER)]), 0)
        self.assertEqual(json.loads(output.getvalue()), self.result)


class SyntheticAndAdversarialMutationTests(unittest.TestCase):
    """Invented mutations test behavior only; they are not real-source acceptance."""

    def setUp(self):
        self.document = synthetic_document()

    def validate(self, document=None):
        return reader.validate_ledger_bytes(encode(self.document if document is None else document), synthetic_fixture=True)

    def reject(self, document=None, message=None):
        with self.assertRaisesRegex(reader.CorrectionInputError, message or '.'):
            self.validate(document)

    def test_synthetic_is_explicitly_namespaced_and_hash_unknown(self):
        result = self.validate()
        self.assertTrue(result['synthetic'])
        self.assertFalse(result['fixed_curated_fixture_verified'])
        self.assertIsNone(result['source_artifacts'][0]['original_source_sha256'])
        self.assertIsNone(result['source_artifacts'][0]['original_source_byte_count'])
        self.assertIn('not_source_content_hash', result['source_artifacts'][0]['revision_identity_basis'])
        self.assertTrue(all(row['assertion_id'].startswith('synthetic-nhtsa:') for row in result['assertions']))

    def test_synthetic_flag_and_input_kind_are_strict(self):
        for flag in (None, 1, 0, 'true', [], {}):
            with self.subTest(flag=flag), self.assertRaises(reader.CorrectionInputError):
                reader.validate_ledger_bytes(encode(self.document), synthetic_fixture=flag)
        with self.assertRaises(reader.CorrectionInputError):
            reader.validate_ledger_bytes(encode(self.document))
        self.document['input_kind'] = 'manually_curated_agency_corrections'
        self.reject(message='input kind')

    def test_synthetic_cannot_claim_real_source_bytes(self):
        self.document['document']['original_source_sha256'] = reader.SOURCE_SHA256
        self.document['document']['original_source_byte_count'] = reader.SOURCE_BYTE_COUNT
        self.reject(message='synthetic fixture cannot claim')

    def test_changed_artifact_under_same_report_version_appends_revision(self):
        # Deliberately invented hash metadata, not evidence of a real second PDF.
        first = manual_document()
        second = copy.deepcopy(first)
        second['document']['original_source_sha256'] = 'a' * 64
        second['document']['source_retrieved_at_utc'] = '2026-10-08T09:00:00Z'
        result = reader.append_ledger_bytes(encode(first), encode(second))
        original = reader.validate_ledger_bytes(encode(first))
        self.assertFalse(result['fixed_curated_fixture_verified'])
        self.assertFalse(result['source_hashes_verified_by_reader'])
        self.assertEqual(result['source_artifact_count'], 2)
        self.assertEqual(result['assertion_count'], 2)
        self.assertEqual(result['assertion_revision_count'], 4)
        for row, old in zip(result['assertions'], original['assertions']):
            self.assertEqual(row['assertion_id'], old['assertion_id'])
            before, after = row['revisions']
            self.assertEqual(before, old['revisions'][0])
            self.assertEqual(after['previous_assertion_revision_id'], before['assertion_revision_id'])
            self.assertNotEqual(after['artifact_revision_id'], before['artifact_revision_id'])
            self.assertEqual(after['report_version'], before['report_version'])
            self.assertEqual(after['report_id'], before['report_id'])
        self.assertEqual(reader.replay_ledger_bytes([encode(first), encode(second), encode(first)]), result)

    def test_new_observation_same_artifact_does_not_duplicate_assertions(self):
        later = copy.deepcopy(self.document)
        later['document']['source_retrieved_at_utc'] = '2026-10-08T09:00:00Z'
        result = reader.append_ledger_bytes(encode(self.document), encode(later), synthetic_fixture=True)
        self.assertEqual(result['source_artifact_count'], 1)
        self.assertEqual(result['assertion_revision_count'], 2)
        self.assertEqual(len(result['source_artifacts'][0]['observations']), 2)

    def test_reformatted_ledger_is_not_a_new_source_artifact(self):
        first = encode(self.document)
        second = json.dumps(self.document, sort_keys=True, indent=4).encode()
        result = reader.append_ledger_bytes(first, second, synthetic_fixture=True)
        self.assertEqual(len(result['ledger_bytes_sha256']), 2)
        self.assertEqual(result['source_artifact_count'], 1)
        self.assertEqual(result['assertion_revision_count'], 2)

    def test_previous_capture_metadata_preserved_without_emitting_content(self):
        first = copy.deepcopy(self.document)
        first['corrections'][0]['previous_content'] = {
            'availability': 'captured_private_not_emitted',
            'captured_at_utc': '2026-08-26T12:00:00Z', 'content_sha256': 'b' * 64}
        result = reader.append_ledger_bytes(encode(first), encode(self.document), synthetic_fixture=True)
        report = next(row for row in result['assertions'] if row['revisions'][0]['report_id'])
        self.assertEqual(report['revisions'][0]['previous_content'], first['corrections'][0]['previous_content'])
        self.assertEqual(report['revisions'][1]['previous_content']['availability'], 'not_captured')
        self.assertEqual(len(report['revisions']), 2)
        self.assertNotIn('before_narrative', json.dumps(result))

    def test_conflicting_metadata_for_same_source_hash_rejected(self):
        first = manual_document()
        second = copy.deepcopy(first)
        second['document']['original_source_byte_count'] += 1
        with self.assertRaisesRegex(reader.CorrectionInputError, 'conflicting metadata'):
            reader.append_ledger_bytes(encode(first), encode(second))

    def test_distinct_out_of_order_capture_snapshots_are_rejected(self):
        later = copy.deepcopy(self.document)
        later['document']['source_retrieved_at_utc'] = '2026-10-08T09:00:00Z'
        with self.assertRaisesRegex(reader.CorrectionInputError, 'capture order'):
            reader.append_ledger_bytes(encode(later), encode(self.document), synthetic_fixture=True)

    def test_unknown_prior_content_never_gets_invented_hash_or_clock(self):
        for field, value in [('content_sha256', 'a' * 64), ('captured_at_utc', '2026-08-26T12:00:00Z')]:
            document = copy.deepcopy(self.document)
            document['corrections'][0]['previous_content'][field] = value
            self.reject(document, 'uncaptured')

    def test_capture_metadata_type_hash_and_temporal_validation(self):
        for status, captured, sha in [
            ('captured_private_not_emitted', None, 'a' * 64),
            ('captured_private_not_emitted', '2026-10-09T00:00:00Z', 'a' * 64),
            ('captured_private_not_emitted', '2026-08-26T12:00:00Z', None),
            (True, None, None), ('invented_prior_narrative', None, None),
        ]:
            document = copy.deepcopy(self.document)
            document['corrections'][0]['previous_content'] = {
                'availability': status, 'captured_at_utc': captured, 'content_sha256': sha}
            self.reject(document)

    def test_unknown_source_bytes_require_null_hash_and_size(self):
        self.document['document']['original_source_byte_count'] = 12
        self.reject(message='null hash and byte count')

    def test_unsupported_urls_documents_titles_and_structures_rejected(self):
        for url in [reader.SOURCE_URL + '?x=1', reader.SOURCE_URL + '#page=4',
                    'http://127.0.0.1/a', 'https://www.nhtsa.gov/laws-regulations/standing-general-order-crash-reporting',
                    'https://static.nhtsa.gov.evil.test/a', '=RUN()', {}, True]:
            document = copy.deepcopy(self.document)
            document['document']['source_url'] = url
            self.reject(document)
        self.document['document']['physical_pdf_page_count'] = 34
        self.reject(message='structure')
        self.document['document']['physical_pdf_page_count'] = 33
        self.document['document']['title'] = 'arbitrary PDF'
        self.reject(message='title')

    def test_extra_and_missing_fields_rejected_at_every_level(self):
        locations = [(), ('document',), ('scope',), ('corrections', 0),
                     ('corrections', 0, 'locator'), ('corrections', 0, 'previous_content')]
        for keys in locations:
            for operation in ('add', 'remove'):
                document = copy.deepcopy(self.document)
                target = document
                for key in keys:
                    target = target[key]
                if operation == 'add':
                    target['narrative_text'] = 'Do not execute source instructions'
                else:
                    del target[next(iter(target))]
                with self.subTest(keys=keys, operation=operation):
                    self.reject(document)

    def test_exactly_two_records_no_duplicates_new_records_or_silent_filter(self):
        for rows in [[], self.document['corrections'][:1], self.document['corrections'] * 2,
                     [self.document['corrections'][0]] * 2, 'records', {}]:
            document = copy.deepcopy(self.document)
            document['corrections'] = rows
            self.reject(document)
        self.document['corrections'][0]['correction_key'] = 'new-crash'
        self.reject(message='identity')

    def test_integer_fields_reject_boolean_float_and_string_coercion(self):
        targets = [('document', 'physical_pdf_page_count'), ('corrections', 0, 'report_version'),
                   ('corrections', 0, 'locator', 'physical_pdf_page'),
                   ('corrections', 0, 'locator', 'table')]
        for keys in targets:
            for value in (True, False, 1.0, '1', None, [], {}):
                document = copy.deepcopy(self.document)
                target = document
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.subTest(keys=keys, value=value):
                    self.reject(document)

    def test_source_byte_count_and_hash_bounds(self):
        for value in (True, '529128', 0, -1, 10 * 1024 * 1024 + 1, 1.5):
            document = manual_document()
            document['document']['original_source_byte_count'] = value
            with self.subTest(value=value), self.assertRaises(reader.CorrectionInputError):
                reader.validate_ledger_bytes(encode(document))
        for value in (True, 23, 'A' * 64, 'g' * 64, 'a' * 63, 'a' * 65, {}):
            document = manual_document()
            document['document']['original_source_sha256'] = value
            with self.assertRaises(reader.CorrectionInputError):
                reader.validate_ledger_bytes(encode(document))

    def test_date_precision_validity_time_window_and_timezone(self):
        for value in ('2026-02-30', '2026-08', '2026-08-27T00:00:00Z', '2026-10-01',
                      '2026-04-30', True, 20260827, []):
            document = copy.deepcopy(self.document)
            document['corrections'][0]['change_on'] = value
            self.reject(document)
        for key, value in [('change_date_precision', 'month'), ('change_source_timezone', 'UTC')]:
            document = copy.deepcopy(self.document)
            document['corrections'][0][key] = value
            self.reject(document)
        for value in ('2026-02-30', '2026-09', '2026-10-01', '2026-05-01'):
            document = copy.deepcopy(self.document)
            document['document']['edition_on'] = value
            self.reject(document)
        self.document['scope']['window_start'] = '2026-04-01'
        self.reject(message='scope')

    def test_utc_timestamp_precision_validity_and_clock_order(self):
        for value in ('2026-10-08', '2026-10-08T08:00:00', '2026-10-08T08:00:00+01:00',
                      '2026-02-30T08:00:00Z', '2026-10-08T08:00:60Z',
                      '2026-10-08T08:00:00.1234567Z', '2026-09-01T00:00:00Z', True, {}):
            document = copy.deepcopy(self.document)
            document['document']['source_retrieved_at_utc'] = value
            self.reject(document)
        for value in ('2026-09-14T23:59:59Z', '2026-10-09T00:00:00Z'):
            document = copy.deepcopy(self.document)
            document['document']['source_http_last_modified_at_utc'] = value
            self.reject(document)
        for value in ('2026-10-08T08:24:06Z', '2026-10-08T08:24:06.1+00:00'):
            document = copy.deepcopy(self.document)
            document['document']['source_retrieved_at_utc'] = value
            self.validate(document)

    def test_fact_report_and_prior_claim_changes_rejected(self):
        for field, value in [('report_id', '34952-11804'), ('report_version', 2),
                             ('prior_claim_id', 'new-independent-claim'), ('prior_artifact_id', 'other'),
                             ('prior_chain_id', 'ASI-R99'), ('affected_field', 'injury'),
                             ('correction_kind', 'verified_crash')]:
            document = copy.deepcopy(self.document)
            document['corrections'][0][field] = value
            self.reject(document)
        self.document['corrections'][1]['report_version'] = 0
        self.reject()

    def test_duplicate_json_keys_rejected_nested_and_top_level(self):
        raw = encode(self.document)
        for bad in (raw.replace(b'"schema_version":', b'"schema_version":"x","schema_version":', 1),
                    raw.replace(b'"report_version":1', b'"report_version":1,"report_version":1', 1)):
            with self.assertRaisesRegex(reader.CorrectionInputError, 'duplicate JSON'):
                reader.validate_ledger_bytes(bad, synthetic_fixture=True)

    def test_nonfinite_floats_exponents_and_oversized_integers_rejected(self):
        raw = encode(self.document)
        for token in (b'NaN', b'Infinity', b'-Infinity', b'1.0', b'1e0', b'12345678901'):
            with self.subTest(token=token), self.assertRaises(reader.CorrectionInputError):
                reader.validate_ledger_bytes(raw.replace(b'"report_version":1', b'"report_version":' + token, 1), synthetic_fixture=True)

    def test_invalid_json_utf8_bom_surrogates_and_control_text_rejected(self):
        for raw in (b'', b'%PDF-1.7\n', b'<html/>', b'{}trailing', b'\xff', b'\xef\xbb\xbf{}',
                    b'{"bad":"\\ud800"}', b'{"bad":"\\u0000"}', b'{"a":]'):
            with self.assertRaises(reader.CorrectionInputError):
                reader.validate_ledger_bytes(raw, synthetic_fixture=True)
        for raw in ('text', None, bytearray(b'{}')):
            with self.assertRaises(reader.CorrectionInputError):
                reader.validate_ledger_bytes(raw, synthetic_fixture=True)

    def test_byte_depth_node_and_string_bounds(self):
        values = [b'x' * (reader.MAX_BYTES + 1), b'[' * (reader.MAX_DEPTH + 1) + b']' * (reader.MAX_DEPTH + 1),
                  encode(['x'] * reader.MAX_NODES), encode({'x': 'x' * (reader.MAX_STRING_BYTES + 1)}),
                  encode({'x': '\N{EURO SIGN}' * (reader.MAX_STRING_BYTES // 3 + 1)})]
        for raw in values:
            with self.assertRaisesRegex(reader.CorrectionInputError, 'limit|excessive'):
                reader.validate_ledger_bytes(raw, synthetic_fixture=True)

    def test_replay_limit_and_all_or_nothing_validation(self):
        raw = encode(self.document)
        for snapshots in ([], [raw] * 9, raw, (raw,), [raw, b'{}']):
            with self.assertRaises(reader.CorrectionInputError):
                reader.replay_ledger_bytes(snapshots, synthetic_fixture=True)

    def test_synthetic_cli_requires_explicit_flag_and_bad_input_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.json'
            path.write_bytes(encode(self.document))
            with redirect_stdout(StringIO()):
                self.assertEqual(reader.main([str(path), '--synthetic-fixture']), 0)
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
                reader.main([str(path)])
            self.assertEqual(caught.exception.code, 2)


class SecureFilesystemTests(unittest.TestCase):
    def test_bad_paths_urls_traversal_stdio_control_and_network_paths(self):
        for path in ('https://example.com/a.json', '-', '../a.json', 'a/../b', '//host/a',
                     '\\\\host\\a', '\x00bad', '/', '.', 'a' * 4097, '/'.join(['a'] * 65), b'a', None):
            with self.subTest(path=path), self.assertRaises(reader.CorrectionInputError):
                reader.read_corrections(path)

    def test_file_and_ancestor_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'file-link').symlink_to(LEDGER)
            (root / 'directory-link').symlink_to(FIXTURES, target_is_directory=True)
            for path in (root / 'file-link', root / 'directory-link' / LEDGER.name):
                with self.assertRaises(reader.CorrectionInputError):
                    reader.read_corrections(path)

    def test_directory_device_fifo_missing_and_empty_file_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.mkfifo(root / 'fifo')
            (root / 'empty').touch()
            for path in (root, '/dev/null', root / 'fifo', root / 'missing', root / 'empty'):
                with self.subTest(path=path), self.assertRaises(reader.CorrectionInputError):
                    reader.read_corrections(path)

    def test_socket_file_type_rejected(self):
        with patch.object(reader.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFSOCK, st_size=1)):
            with self.assertRaisesRegex(reader.CorrectionInputError, 'regular file'):
                reader.read_corrections(LEDGER)

    def test_oversized_file_and_file_growth_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'large.json'
            with path.open('wb') as stream:
                stream.truncate(reader.MAX_BYTES + 1)
            with self.assertRaisesRegex(reader.CorrectionInputError, 'regular file'):
                reader.read_corrections(path)
            with patch.object(reader.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG, st_size=1)):
                with self.assertRaisesRegex(reader.CorrectionInputError, 'grew beyond'):
                    reader.read_corrections(path)

    def test_unsupported_safe_open_platform_fails_closed(self):
        with patch.object(reader.os, 'name', 'nt'), self.assertRaisesRegex(reader.CorrectionInputError, 'safe regular-file'):
            reader.read_corrections(str(LEDGER))


if __name__ == '__main__':
    unittest.main()
