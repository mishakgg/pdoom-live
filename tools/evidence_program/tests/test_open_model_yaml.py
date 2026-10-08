"""Offline real-fixture regressions plus synthetic hostile/preservation cases."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import read_open_model_yaml as reader

FIXTURES = Path(__file__).parent / 'fixtures' / 'open-model-yaml'
BEFORE = FIXTURES / 'before-llama-3.3.yaml'
AFTER = FIXTURES / 'after-llama-3.3.yaml'


class RealPinnedPairTests(unittest.TestCase):
    def setUp(self):
        self.result = reader.read_pinned_pair(BEFORE, AFTER)
        self.before, self.after = self.result['revisions']

    def test_fixture_scoped_attributes_preserve_pinned_lf_bytes(self):
        self.assertEqual((FIXTURES / '.gitattributes').read_text(encoding='ascii').splitlines(),
                         ['before-llama-3.3.yaml text eol=lf',
                          'after-llama-3.3.yaml text eol=lf'])

    def test_real_fixture_byte_sizes_hashes_and_git_blobs(self):
        for path, pin in ((BEFORE, reader.BEFORE), (AFTER, reader.AFTER)):
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                self.assertEqual(len(raw), pin.byte_count)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), pin.sha256)
                self.assertEqual(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(), pin.git_blob)

    def test_26_criterion_records_with_complete_source_fields(self):
        records = [item for revision in self.result['revisions'] for item in revision['criterion_records']]
        self.assertEqual(len(records), 26)
        self.assertEqual(len({item['record_id'] for item in records}), 26)
        for revision in self.result['revisions']:
            self.assertEqual([item['criterion'] for item in revision['criterion_records']], revision['criterion_keys'])
            for item in revision['criterion_records']:
                self.assertEqual(item['source_fields'], revision['field_document'][item['criterion']])
                self.assertEqual(item['revision_sha256'], revision['provenance']['sha256'])
                self.assertEqual(item['presence'], 'present')
                self.assertEqual(item['review_state'], 'needs_review')

    def test_deterministic_record_ids_bind_exact_revision_and_criterion(self):
        for revision in self.result['revisions']:
            for item in revision['criterion_records']:
                self.assertEqual(item['record_id'], 'osai-experimental:' + revision['provenance']['sha256'] + ':' + item['criterion'])

    def test_derived_criteria_fingerprints_reproduce_and_differ(self):
        for revision in self.result['revisions']:
            expected = hashlib.sha256(json.dumps(revision['criterion_keys'], ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
            self.assertEqual(revision['criteria_set_fingerprint_sha256'], expected)
            self.assertIn('not an official schema version', revision['criteria_set_fingerprint_method'])
            for item in revision['criterion_records']:
                self.assertEqual(item['criteria_set_fingerprint_sha256'], expected)
        self.assertNotEqual(self.before['criteria_set_fingerprint_sha256'], self.after['criteria_set_fingerprint_sha256'])
        event = self.result['criteria_set_changes'][0]
        self.assertEqual(event['before_criteria_set_fingerprint_sha256'], self.before['criteria_set_fingerprint_sha256'])
        self.assertEqual(event['after_criteria_set_fingerprint_sha256'], self.after['criteria_set_fingerprint_sha256'])

    def test_removed_criteria_are_absent_never_reclassified_closed(self):
        removed = self.result['criteria_set_changes'][0]['removed_criteria']
        self.assertEqual([item['criterion'] for item in removed], ['api', 'package'])
        for item in removed:
            self.assertEqual(item['before_presence'], 'present')
            self.assertEqual(item['after_presence'], 'absent_from_schema')
            self.assertEqual(item['before_source_fields'], self.before['field_document'][item['criterion']])
            self.assertIsNone(item['after_source_fields'])
        self.assertFalse({'api', 'package'} & {item['criterion'] for item in self.after['criterion_records']})

    def test_full_criterion_alignment_preserves_absence_and_source_documents(self):
        alignment = self.result['criterion_alignment']
        self.assertEqual(len(alignment), 14)
        self.assertEqual(list(alignment), self.before['criterion_keys'])
        for key, item in alignment.items():
            self.assertEqual(item['before_presence'], 'present')
            self.assertEqual(item['before_source_fields'], self.before['field_document'][key])
            if key in ('api', 'package'):
                self.assertEqual(item['after_presence'], 'absent_from_schema')
                self.assertIsNone(item['after_source_fields'])
            else:
                self.assertEqual(item['after_presence'], 'present')
                self.assertEqual(item['after_source_fields'], self.after['field_document'][key])

    def test_original_fixture_acquisition_time_is_distinct(self):
        for revision in self.result['revisions']:
            provenance = revision['provenance']
            self.assertEqual(provenance['fixture_retrieved_at_utc'], '2026-10-08T00:20:44Z')
            self.assertEqual(provenance['fixture_retrieval_time_role'], 'original_fixture_acquisition_not_reader_execution_or_assessment_time')
            self.assertIsNone(provenance['assessment_time'])
            self.assertNotEqual(provenance['fixture_retrieved_at_utc'], provenance['commit_time'])

    def test_exact_original_yaml_round_trip_including_license_header(self):
        for path, revision in ((BEFORE, self.before), (AFTER, self.after)):
            with self.subTest(path=path.name):
                self.assertEqual(revision['original_yaml'].encode('utf-8'), path.read_bytes())
                self.assertIn('licensed under CC-BY 4.0', revision['original_yaml'])
                self.assertIn('Liesenfeld, A. and Dingemanse, M., 2024.', revision['original_yaml'])

    def test_single_criteria_set_event_only(self):
        self.assertEqual(len(self.result['criteria_set_changes']), 1)
        event = self.result['criteria_set_changes'][0]
        self.assertEqual((event['before_count'], event['after_count']), (14, 12))
        self.assertEqual(event['removed'], ['api', 'package'])
        self.assertEqual(event['added'], [])
        self.assertEqual(self.result['surviving_criterion_value_changes'], [])
        self.assertFalse(self.result['identity_changed'])
        self.assertEqual(self.result['inferred_model_access_or_license_changes'], [])

    def test_nested_metaprompt_remains_nested_and_removed_documents_preserved(self):
        old = self.before['field_document']
        self.assertEqual(old['api']['metaprompt'], 'closed')
        self.assertNotIn('metaprompt', old)
        self.assertNotIn('metaprompt', self.before['criterion_keys'])
        self.assertEqual(self.result['criteria_set_changes'][0]['removed_field_documents'],
                         {key: old[key] for key in ('api', 'package')})

    def test_all_identity_and_surviving_field_documents_unchanged(self):
        old, new = self.before['field_document'], self.after['field_document']
        self.assertEqual(set(new), set(old) - {'api', 'package'})
        for key in new:
            with self.subTest(key=key):
                self.assertEqual(old[key], new[key])

    def test_exact_five_null_links_per_revision(self):
        for revision in self.result['revisions']:
            links = [revision['field_document'][key]['link'] for key in revision['criterion_keys']]
            self.assertEqual(sum(value is None for value in links), 5)

    def test_raw_assessments_notes_and_model_license(self):
        fields = self.before['field_document']
        self.assertEqual(fields['weights_endmodel']['class'], 'partial')
        self.assertEqual(fields['package']['class'], 'open')
        self.assertEqual(fields['api']['notes'], 'API not available in EU.')
        self.assertEqual(fields['system']['endmodellicense'], 'Llama 3.3 Community License Agreement')
        self.assertEqual(self.before['model_license_text'], fields['system']['endmodellicense'])

    def test_month_precision_and_time_roles_do_not_invent_dates(self):
        for revision, pin in zip(self.result['revisions'], (reader.BEFORE, reader.AFTER)):
            self.assertEqual(revision['release_date'], {'raw': '2024-12', 'precision': 'month'})
            self.assertIsNone(revision['provenance']['assessment_time'])
            self.assertEqual(revision['provenance']['commit_time'], pin.commit_time)
            self.assertIn('not_assessment_or_release', revision['provenance']['commit_time_role'])

    def test_annotation_rights_are_distinct_from_model_rights(self):
        for revision in self.result['revisions']:
            rights = revision['annotation_rights']
            self.assertEqual(rights['license_identifier'], 'CC-BY-4.0')
            self.assertEqual(rights['attribution_site'], 'https://osai-index.eu/')
            self.assertEqual(rights['index_files_doi'], 'https://doi.org/10.5281/zenodo.15386042')
            self.assertFalse(rights['permissions_inherited_by_model_weights_or_linked_works'])
            self.assertNotEqual(rights['license_identifier'], revision['model_license_text'])

    def test_output_remains_experimental_and_disabled(self):
        self.assertEqual(self.result['status'], 'experimental_review_records_not_admitted')
        for key in ('canonical_schema_claimed', 'source_admission_enabled', 'production_import_enabled',
                    'network_access_performed', 'links_followed', 'model_execution_performed'):
            self.assertIs(self.result[key], False)
        self.assertIs(self.result['annotation_assessments_are_external'], True)
        self.assertEqual(self.result['network_access_flag_scope'],
                         'reader-issued network requests only; OS filesystem mount locality is not established')
        self.assertIn('no reader-issued network requests; arbitrary OS-mounted filesystems are not provably local',
                      self.result['limits'])
        for revision in self.result['revisions']:
            self.assertEqual(revision['review_state'], 'needs_review')
            self.assertTrue(revision['record_kind'].startswith('experimental_'))

    def test_complete_documents_json_round_trip(self):
        self.assertEqual(json.loads(json.dumps(self.result)), self.result)

    def test_no_network_or_yaml_object_construction(self):
        with mock.patch('socket.socket', side_effect=AssertionError('network prohibited')), \
             mock.patch('urllib.request.urlopen', side_effect=AssertionError('network prohibited')), \
             mock.patch.object(reader.yaml, 'load', side_effect=AssertionError('object construction prohibited')), \
             mock.patch.object(reader.yaml, 'safe_load', side_effect=AssertionError('object construction prohibited')):
            self.assertEqual(reader.read_pinned_pair(BEFORE, AFTER), self.result)

    def test_deterministic_across_copied_local_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            before, after = Path(temp) / 'one', Path(temp) / 'two'
            before.write_bytes(BEFORE.read_bytes())
            after.write_bytes(AFTER.read_bytes())
            self.assertEqual(reader.read_pinned_pair(before, after), self.result)

    def test_swapped_or_same_revision_rejected(self):
        for before, after in ((AFTER, BEFORE), (BEFORE, BEFORE), (AFTER, AFTER)):
            with self.subTest(before=before.name, after=after.name):
                with self.assertRaisesRegex(reader.ReviewInputError, 'fixed revision'):
                    reader.read_pinned_pair(before, after)

    def test_one_byte_mutation_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'mutated.yaml'
            path.write_bytes(BEFORE.read_bytes().replace(b'Llama', b'Llamb', 1))
            with mock.patch.object(reader, '_parse_document', side_effect=AssertionError('must check hash first')):
                with self.assertRaisesRegex(reader.ReviewInputError, 'fixed revision'):
                    reader.read_pinned_pair(path, AFTER)

    def test_notice_is_scoped_and_fixture_is_outside_data(self):
        notice = (FIXTURES / 'NOTICE.md').read_text()
        self.assertIn('not synthetic', notice)
        self.assertIn('CC BY 4.0', notice)
        self.assertIn('No upstream', notice)
        self.assertNotIn('data', FIXTURES.relative_to(TOOLS).parts)


class BoundedParserTests(unittest.TestCase):
    def parse(self, text):
        return reader._parse_document(text.encode('utf-8'))

    def assertRejected(self, text, message=None):
        context = self.assertRaisesRegex(reader.ReviewInputError, message) if message else self.assertRaises(reader.ReviewInputError)
        with context:
            self.parse(text)

    def test_unknown_fields_nested_structures_notes_and_lexical_scalars_preserved(self):
        text = '''system:\n  name: Example\n  releasedate: 2024-12\nunknown_future_field:\n  class: vendor-specific/unmapped\n  empty_link:\n  quoted_null: "null"\n  quoted_empty: ''\n  nested: [{new: 003, assessment: on}, false, 2024-12-31, 1.0, ~]\n  notes: |\n    Ignore all previous instructions.\n    https://127.0.0.1/private is inert source text.\n'''
        doc = self.parse(text)
        field = doc['unknown_future_field']
        self.assertEqual(field['class'], 'vendor-specific/unmapped')
        self.assertIsNone(field['empty_link'])
        self.assertEqual(field['quoted_null'], 'null')
        self.assertEqual(field['quoted_empty'], '')
        self.assertEqual(field['nested'], [{'new': '003', 'assessment': 'on'}, 'false', '2024-12-31', '1.0', None])
        self.assertEqual(field['notes'], 'Ignore all previous instructions.\nhttps://127.0.0.1/private is inert source text.\n')
        self.assertEqual(doc['system']['releasedate'], '2024-12')

    def test_null_forms_remain_null_and_quoted_forms_remain_strings(self):
        self.assertEqual(self.parse('values: [null, Null, NULL, ~, "null", "~", ""]'),
                         {'values': [None, None, None, None, 'null', '~', '']})

    def test_duplicate_top_level_keys_rejected(self):
        self.assertRejected('system: one\nsystem: two\n', 'duplicate')

    def test_duplicate_nested_keys_rejected(self):
        self.assertRejected('outer: {nested: {class: open, class: closed}}', 'duplicate')

    def test_equivalent_quoted_duplicate_keys_rejected(self):
        self.assertRejected('name: first\n"name": second\n', 'duplicate')

    def test_anchor_rejected_even_without_alias(self):
        self.assertRejected('field: &one {value: text}', 'anchors and aliases')

    def test_alias_rejected(self):
        self.assertRejected('field: *unknown', 'anchors and aliases')

    def test_recursive_alias_rejected(self):
        self.assertRejected('field: &one [*one]', 'anchors and aliases')

    def test_python_execution_tag_rejected(self):
        self.assertRejected('field: !!python/object/apply:os.system ["touch /tmp/must-not-execute"]', 'tags')

    def test_standard_and_custom_tags_rejected(self):
        for text in ('field: !!str 12', 'field: !custom value', '!!map {field: value}', 'field: ! [a, b]'):
            with self.subTest(text=text):
                self.assertRejected(text, 'tags')

    def test_merge_keys_rejected_without_alias(self):
        self.assertRejected('field: {<<: {a: one}, b: two}', 'merge keys')

    def test_all_directives_rejected(self):
        for directive in ('%YAML 1.1', '%TAG !e! tag:example.com,2000:app/', '%UNKNOWN ignored'):
            with self.subTest(directive=directive):
                self.assertRejected(directive + '\n---\nfield: text', 'directives')

    def test_directive_text_inside_notes_is_preserved(self):
        self.assertEqual(self.parse('notes: |\n  %UNKNOWN inert\n'), {'notes': '%UNKNOWN inert\n'})

    def test_multiple_documents_rejected(self):
        self.assertRejected('---\nfield: one\n---\nfield: two', 'exactly one')

    def test_empty_document_and_non_mapping_roots_rejected(self):
        for text in ('', '---\n', '{}', '[one, two]', 'plain string', 'null'):
            with self.subTest(text=text):
                self.assertRejected(text)

    def test_complex_and_null_keys_rejected(self):
        for text in ('? [a, b]\n: c', '? {a: b}\n: c', 'null: x', ': x'):
            with self.subTest(text=text):
                self.assertRejected(text)

    def test_malformed_yaml_rejected(self):
        for text in ('field: [unclosed', 'field: "unterminated', 'field:\n\tchild: value', 'field: a\x00b'):
            with self.subTest(text=text):
                self.assertRejected(text, 'invalid YAML')

    def test_invalid_utf8_rejected(self):
        with self.assertRaisesRegex(reader.ReviewInputError, 'UTF-8'):
            reader._parse_document(b'field: \xff')

    def test_escaped_surrogate_is_rejected_cleanly(self):
        self.assertRejected('field: \"\\uD800\"', 'Unicode scalar')

    def test_byte_limit_is_enforced_before_parser(self):
        with mock.patch.object(reader.yaml, 'parse', side_effect=AssertionError('must bound bytes first')):
            with self.assertRaisesRegex(reader.ReviewInputError, '64 KiB'):
                reader._parse_document(b'x' * (reader.MAX_BYTES + 1))

    def test_nesting_limit(self):
        self.parse('x: ' + '[' * 30 + 'leaf' + ']' * 30)
        self.assertRejected('x: ' + '[' * 31 + 'leaf' + ']' * 31, 'nesting limit')

    def test_event_limit(self):
        self.assertRejected(''.join(f'key{i}: value\n' for i in range(2100)), 'event limit')

    def test_scalar_limit(self):
        self.parse('field: ' + 'x' * reader.MAX_SCALAR_BYTES)
        self.assertRejected('field: ' + 'x' * (reader.MAX_SCALAR_BYTES + 1), 'scalar limit')

    def test_scalar_limit_counts_utf8_bytes(self):
        self.assertRejected('field: ' + '中' * (reader.MAX_SCALAR_BYTES // 3 + 1), 'scalar limit')


class LocalFileAndCliTests(unittest.TestCase):
    def test_url_and_stdin_are_not_input_routes(self):
        for value in ('https://example.com/a.yaml', 'file:///tmp/a.yaml', '-'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(reader.ReviewInputError, 'local regular'):
                    reader.read_pinned_pair(value, AFTER)

    def test_unc_device_and_mixed_network_prefixes_rejected_before_open(self):
        paths = (
            r'\\server\share\file.yaml', '//server/share/file.yaml',
            r'\\.\pipe\name', r'\\?\C:\file.yaml',
            r'/\server/share/file.yaml', r'\/server/share/file.yaml',
            r'\server\share\file.yaml', '///server/share/file.yaml',
        )
        for path in paths:
            with self.subTest(path=path), mock.patch.object(reader.os, 'open') as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, 'path prefixes'):
                    reader._read_local_bytes(path)
                opened.assert_not_called()

    def test_drive_posix_and_relative_paths_pass_prefix_screen(self):
        for path in (r'F:\fixtures\before.yaml', 'F:/fixtures/before.yaml',
                     '/tmp/before.yaml', 'fixtures/before.yaml'):
            with self.subTest(path=path), mock.patch.object(reader.os, 'open', side_effect=FileNotFoundError) as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, 'cannot read supplied'):
                    reader._read_local_bytes(path)
                opened.assert_called_once()
                self.assertEqual(opened.call_args.args[0], path)

    def test_missing_file_and_directory_fail_closed(self):
        for path in (FIXTURES / 'missing.yaml', FIXTURES):
            with self.subTest(path=path):
                with self.assertRaises(reader.ReviewInputError):
                    reader.read_pinned_pair(path, AFTER)

    def test_regular_file_size_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'large.yaml'
            path.write_bytes(b'x' * reader.MAX_BYTES)
            self.assertEqual(len(reader._read_local_bytes(path)), reader.MAX_BYTES)
            path.write_bytes(b'x' * (reader.MAX_BYTES + 1))
            with self.assertRaisesRegex(reader.ReviewInputError, '64 KiB'):
                reader.read_pinned_pair(path, AFTER)

    @unittest.skipUnless(hasattr(os, 'mkfifo') and hasattr(os, 'O_NONBLOCK'), 'POSIX FIFO test')
    def test_fifo_rejected_without_waiting_for_a_writer(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'pipe'
            os.mkfifo(path)
            with self.assertRaisesRegex(reader.ReviewInputError, 'local regular'):
                reader.read_pinned_pair(path, AFTER)

    @unittest.skipUnless(hasattr(os, 'O_NOFOLLOW'), 'O_NOFOLLOW unavailable')
    def test_symbolic_link_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'link'
            path.symlink_to(BEFORE.resolve())
            with self.assertRaises(reader.ReviewInputError):
                reader.read_pinned_pair(path, AFTER)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(TOOLS / 'read_open_model_yaml.py'), *map(str, args)],
                              capture_output=True, text=True, timeout=10, check=False)

    def test_cli_deterministic_json(self):
        first, second = self.cli(BEFORE, AFTER), self.cli(BEFORE, AFTER)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stderr, '')
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout), reader.read_pinned_pair(BEFORE, AFTER))

    def test_cli_rejects_extra_inputs(self):
        result = self.cli(BEFORE, AFTER, BEFORE)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')

    def test_cli_has_no_hash_override_or_network_mode(self):
        for flag in ('--sha256', '--allow-unpinned', '--url', '--live'):
            with self.subTest(flag=flag):
                result = self.cli(BEFORE, AFTER, flag)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')

    def test_cli_rejects_hash_mismatch_without_partial_output(self):
        result = self.cli(AFTER, BEFORE)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertIn('fixed revision', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
