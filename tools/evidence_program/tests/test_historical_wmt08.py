"""Synthetic-only, offline regressions; no acquired WMT bytes are in CI."""
from __future__ import annotations

import gzip
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request
import zlib

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import read_wmt08_scores as reader

FIXTURES = TOOLS / 'tests' / 'fixtures' / 'historical-backfills'
SYNTHETIC_TEXT = FIXTURES / 'synthetic-wmt08-scores.txt'


def score_row(metric='Rank', language='fr-en', test_set='test2008',
              system='synthetic-system', score='0.2710', kind='rbmt'):
    return f'{metric} {language} {test_set} {system} {score} {kind}'.encode('ascii')


def compressed(raw: bytes) -> bytes:
    return gzip.compress(raw, mtime=0)


class SyntheticReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'synthetic.gz'
        self.raw = SYNTHETIC_TEXT.read_bytes()
        self.gzip = compressed(self.raw)
        self.path.write_bytes(self.gzip)
        self.result = reader.read_synthetic_scores(self.path)

    def test_fixed_real_pin_is_review_metadata_not_synthetic_data_identity(self):
        self.assertEqual(reader.PINNED_SHA256, 'f49c4f058173c45b0c3ff455be8024ed13d98656810127297d815a502587cbac')
        self.assertEqual(reader.PINNED_COMPRESSED_BYTES, 16071)
        self.assertEqual(reader.PINNED_DECOMPRESSED_BYTES, 113529)
        self.assertEqual(reader.PINNED_ROW_COUNT, 2584)
        self.assertEqual(len(reader.PINNED_METRIC_LABELS), 17)
        self.assertEqual(reader.PINNED_SYSTEM_TYPE_COUNTS, {'smt': 1703, 'rbmt': 843, 'syscomb': 38})
        self.assertNotEqual(self.result['provenance']['compressed_sha256'], reader.PINNED_SHA256)

    def test_synthetic_source_and_date_provenance_cannot_masquerade_as_real(self):
        self.assertEqual(self.result['dataset_kind'], 'synthetic')
        provenance = self.result['provenance']
        for key in ('source_family', 'benchmark_edition', 'source_url', 'schema_url', 'paper_url'):
            self.assertIsNone(provenance[key])
        self.assertEqual(provenance['pin_status'], 'synthetic_unpinned_not_source_evidence')
        self.assertEqual(provenance['transport_observation'], {
            'status': 'not_applicable_synthetic', 'observed_at': None, 'http_last_modified': None})
        for item in self.result['historical_dates'].values():
            self.assertIsNone(item['value'])
            self.assertIn('status', item)
        for row in self.result['rows']:
            self.assertEqual(row['dataset_kind'], 'synthetic')
            self.assertIsNone(row['direction_as_published'])
            self.assertIn('synthetic', row['metric_semantics'])
            self.assertTrue(row['system_id_raw'].startswith('synthetic-'))

    def test_hashes_and_source_line_locators(self):
        provenance = self.result['provenance']
        self.assertEqual(provenance['compressed_sha256'], hashlib.sha256(self.gzip).hexdigest())
        self.assertEqual(provenance['compressed_byte_count'], len(self.gzip))
        self.assertEqual(provenance['decompressed_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(provenance['decompressed_byte_count'], len(self.raw))
        for number, row in enumerate(self.result['rows'], 1):
            self.assertEqual(row['line_number'], number)
            offset = row['decompressed_byte_offset']
            self.assertEqual(self.raw[offset:offset + len(row['raw_row'])], row['raw_row'].encode('ascii'))

    def test_exact_decimal_lexemes_and_unusual_raw_labels_survive(self):
        rows = self.result['rows']
        self.assertEqual([row['score_numeric'] for row in rows], ['0.2710', '+0.0400', '47.125', '1.250e-2', '-0.000'])
        self.assertEqual(rows[1]['metric_raw'], 'mter')
        self.assertEqual(rows[1]['language_pair_raw'], 'cz-en')
        self.assertEqual(rows[1]['test_set_raw'], 'nc-test2008')
        self.assertEqual(rows[2]['language_pair_raw'], 'xx-en')
        self.assertEqual(rows[3]['language_pair_raw'], 'en-hu')
        self.assertEqual(rows[4]['language_pair_raw'], 'es-de')
        for row in rows:
            self.assertEqual(row['score_raw'], row['score_numeric'])

    def test_json_round_trip_contains_no_float_values(self):
        self.assertEqual(json.loads(json.dumps(self.result, allow_nan=False)), self.result)
        pending = [self.result]
        while pending:
            value = pending.pop()
            self.assertIsNot(type(value), float)
            if isinstance(value, dict):
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)

    def test_unknowns_and_relationships_remain_explicit(self):
        for row in self.result['rows']:
            for key in ('resolved_system_identity', 'denominator', 'uncertainty', 'evaluation_execution_time'):
                self.assertIsNone(row[key]['value'])
                self.assertTrue(row[key]['status'])
            self.assertEqual(row['duplicate_report_links'], [])
            self.assertEqual(row['revision_links'], [])
        self.assertIsNone(self.result['independent_evaluations_count']['value'])
        self.assertIn('not_independent', self.result['independent_evaluations_count']['status'])

    def test_no_admission_canonical_import_publication_or_probability(self):
        self.assertEqual(self.result['status'], 'experimental_review_records_not_admitted')
        self.assertEqual(self.result['review_state'], 'needs_review')
        for key in ('canonical_schema_claimed', 'source_admission_enabled', 'production_import_enabled',
                    'network_access_performed', 'links_followed'):
            self.assertIs(self.result[key], False)
        for key in ('p_doom', 'capability_score', 'deployed', 'frontier_score', 'independent_experiment_count'):
            self.assertNotIn(key, self.result)
        self.assertTrue(any('All-English' in note for note in self.result['limits']))

    def test_rights_do_not_inherit_acl_or_repository_license(self):
        rights = self.result['data_rights']
        self.assertEqual(rights['rights_status'], 'synthetic_input_rights_not_assessed')
        self.assertIsNone(rights['license_identifier'])
        for key in ('paper_license_inherited', 'repository_license_inherited', 'redistribution_permission_established'):
            self.assertIs(rights[key], False)
        notice = (FIXTURES / 'NOTICE.md').read_text()
        self.assertIn('unknown', notice)
        self.assertIn('self-authored', notice)
        self.assertIn('not copied WMT data', notice)
        self.assertNotIn('data', FIXTURES.relative_to(TOOLS).parts)
        self.assertEqual(sorted(p.name for p in FIXTURES.iterdir()), ['NOTICE.md', 'synthetic-wmt08-scores.txt'])

    def test_stable_ids_across_copies_and_source_mtime_changes(self):
        copy = Path(self.temp.name) / 'copy.gz'
        copy.write_bytes(self.gzip)
        os.utime(copy, (0, 0))
        self.assertEqual(reader.read_synthetic_scores(copy), self.result)
        ids = [row['assertion_id'] for row in self.result['rows']]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertTrue(all(value.startswith('wmt08-synthetic:sha256:') for value in ids))

    def test_identity_changes_with_compressed_artifact_version(self):
        self.path.write_bytes(gzip.compress(self.raw, mtime=1))
        changed = reader.read_synthetic_scores(self.path)
        self.assertNotEqual(changed['provenance']['artifact_id'], self.result['provenance']['artifact_id'])
        self.assertEqual([r['score_raw'] for r in changed['rows']], [r['score_raw'] for r in self.result['rows']])
        self.assertNotEqual(changed['rows'][0]['assertion_id'], self.result['rows'][0]['assertion_id'])

    def test_system_groups_are_task_scoped_not_metric_or_global_identity(self):
        self.path.write_bytes(compressed(b'\n'.join([
            score_row(metric='Rank'), score_row(metric='mter'),
            score_row(language='de-en'), score_row(test_set='nc-test2008'), score_row(system='synthetic-other'),
        ])))
        rows = reader.read_synthetic_scores(self.path)['rows']
        self.assertEqual(rows[0]['evaluation_group_id'], rows[1]['evaluation_group_id'])
        self.assertEqual(len({row['evaluation_group_id'] for row in rows}), 4)
        self.assertEqual(len({row['assertion_id'] for row in rows}), 5)
        self.assertTrue(all(row['resolved_system_identity']['value'] is None for row in rows))

    def test_inert_hostile_tokens_do_not_execute_or_fetch(self):
        hostile = '<script>__import__("os").system("false")</script>'
        self.path.write_bytes(compressed(score_row(system=hostile, metric='https://127.0.0.1/secret')))
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('no network')), \
             mock.patch.object(urllib.request, 'urlopen', side_effect=AssertionError('no network')), \
             mock.patch.object(subprocess, 'run', side_effect=AssertionError('no execution')), \
             mock.patch.object(os, 'system', side_effect=AssertionError('no execution')):
            result = reader.read_synthetic_scores(self.path)
        self.assertEqual(result['rows'][0]['system_id_raw'], hostile)

    def test_fixed_mode_rejects_synthetic_before_inflate(self):
        with mock.patch.object(reader, '_decompress_single_member', side_effect=AssertionError('verify pin first')):
            with self.assertRaisesRegex(reader.ReviewInputError, 'fixed WMT08 artifact pin'):
                reader.read_pinned_scores(self.path)

    def test_no_public_override_can_claim_real_pin_or_transport(self):
        self.assertEqual(set(inspect.signature(reader.read_pinned_scores).parameters), {'path', 'transport_observation'})
        self.assertEqual(set(inspect.signature(reader.read_synthetic_scores).parameters), {'path'})
        with self.assertRaises(TypeError):
            reader.read_pinned_scores(self.path, expected_sha256=hashlib.sha256(self.gzip).hexdigest())
        with self.assertRaises(TypeError):
            reader.read_synthetic_scores(self.path, transport_observation={})
        with self.assertRaisesRegex(reader.ReviewInputError, 'real review provenance'):
            reader._review_result(self.gzip, self.raw, reader._parse_rows(self.raw), synthetic=False, transport={})


class RowSyntaxTests(unittest.TestCase):
    def rejected(self, raw, message=None):
        context = self.assertRaisesRegex(reader.ReviewInputError, message) if message else self.assertRaises(reader.ReviewInputError)
        with context:
            reader._parse_rows(raw)

    def test_lf_crlf_optional_final_newline_and_whitespace_are_preserved(self):
        first = b' \tRank\tfr-en  test2008\tsynthetic-a\t+0.2300\trbmt \t'
        second = score_row(system='synthetic-b')
        for raw in (first + b'\n' + second, first + b'\r\n' + second + b'\r\n'):
            with self.subTest(raw=raw):
                rows = reader._parse_rows(raw)
                self.assertEqual(rows[0]['raw_row'].encode(), first)
                self.assertEqual(rows[0]['score_raw'], '+0.2300')
                self.assertEqual(rows[1]['decompressed_byte_offset'], raw.index(second))
                self.assertEqual([row['line_number'] for row in rows], [1, 2])

    def test_all_valid_decimal_forms_are_exact_not_float_normalized(self):
        for value in ('0', '-0', '+0', '-0.000', '003.100', '.5', '1.', '+1.20e-2', '1E+9999', '1e-9999', '42.15', '-999.125'):
            with self.subTest(value=value):
                row = reader._parse_rows(score_row(score=value))[0]
                self.assertEqual(row['score_numeric'], value)
                self.assertEqual(row['score_raw'], value)

    def test_invalid_or_nonfinite_decimal_forms_are_rejected(self):
        for value in ('NaN', 'sNaN', 'Infinity', '-Infinity', 'inf', 'nan', '1_000', '1,2', '0x1', '1/2', '1e', '.', '+', '--1', '1e+', '"0.2"'):
            with self.subTest(value=value):
                self.rejected(score_row(score=value), 'strict finite decimal')

    def test_decimal_length_boundary_and_exponent_work_bound(self):
        value = '1' * reader.MAX_NUMBER_CHARS
        self.assertEqual(reader._parse_rows(score_row(score=value))[0]['score_numeric'], value)
        self.rejected(score_row(score=value + '1'), 'number length limit')
        for value in ('1e10000', '1e-10000', '1e00000', '1e' + '9' * 30):
            self.rejected(score_row(score=value), 'exponent limit')

    def test_case_punctuation_unknown_labels_and_classification_not_rewritten(self):
        row = reader._parse_rows(score_row(metric='Future-Metric/2', language='xx-en', test_set='nc-test2008', kind='FUTURE-TYPE'))[0]
        self.assertEqual(row['metric_raw'], 'Future-Metric/2')
        self.assertEqual(row['language_pair_raw'], 'xx-en')
        self.assertEqual(row['system_type_raw'], 'FUTURE-TYPE')

    def test_schema_interpretation_keeps_rank_relative_and_mter_already_reversed(self):
        # Schema metadata tests, not purported observations from synthetic rows.
        self.assertEqual(reader.PUBLISHED_DIRECTION, 'higher_is_better')
        self.assertIn('not_ordinal', reader._published_metric_semantics('Rank'))
        self.assertIn('greater_or_equal', reader._published_metric_semantics('Rank'))
        self.assertIn('already_reversed', reader._published_metric_semantics('mter'))
        self.assertIn('do_not_reverse_again', reader._published_metric_semantics('mter'))
        for metric in set(reader.PINNED_METRIC_LABELS) - {'Rank', 'mter'}:
            self.assertEqual(reader._published_metric_semantics(metric), 'source_metric_scale_preserved_not_assumed_to_be_probability')

    def test_six_fields_strict_blank_rows_header_and_comments_fail(self):
        for raw in (b'', b'\n', b' \t', score_row() + b'\n\n', b'\n' + score_row(),
                    b'Rank fr-en test2008 system 0.2', score_row() + b' extra',
                    b'metric language test system score type', b'# a comment', score_row() + b'\n# comment'):
            with self.subTest(raw=raw):
                self.rejected(raw)

    def test_non_ascii_bom_and_control_characters_rejected(self):
        for hostile in (b'\x00', b'\xff', b'\x7f', b'\x0b', b'\x0c', b'\r', b'\xef\xbb\xbf', '中'.encode(), b'\xc2\xa0'):
            with self.subTest(hostile=hostile):
                self.rejected(hostile + score_row(), 'printable ASCII')

    def test_duplicate_keys_reject_identical_conflicting_value_and_type(self):
        for second in (score_row(), score_row(score='0.9'), score_row(kind='smt')):
            self.rejected(score_row() + b'\n' + second, 'duplicate four-field')

    def test_different_metric_language_set_or_system_is_not_duplicate(self):
        rows = [score_row(), score_row(metric='mter'), score_row(language='de-en'),
                score_row(test_set='newstest2008'), score_row(system='synthetic-other')]
        self.assertEqual(len(reader._parse_rows(b'\n'.join(rows))), 5)

    def test_field_byte_boundary(self):
        self.assertEqual(reader._parse_rows(score_row(system='x' * reader.MAX_FIELD_BYTES))[0]['system_id_raw'], 'x' * reader.MAX_FIELD_BYTES)
        self.rejected(score_row(system='x' * (reader.MAX_FIELD_BYTES + 1)), 'field byte limit')

    def test_line_byte_boundary_checked_before_splitting(self):
        row = score_row()
        padded = row + b' ' * (reader.MAX_LINE_BYTES - len(row))
        self.assertEqual(len(reader._parse_rows(padded)[0]['raw_row']), reader.MAX_LINE_BYTES)
        self.rejected(padded + b' ', 'row byte limit')

    def test_row_count_boundary(self):
        rows = [score_row(system=f'synthetic-{index}') for index in range(reader.MAX_ROWS)]
        raw = b'\n'.join(rows)
        self.assertLess(len(raw), reader.MAX_DECOMPRESSED_BYTES)
        self.assertEqual(len(reader._parse_rows(raw)), reader.MAX_ROWS)
        self.rejected(raw + b'\n' + score_row(system='synthetic-overflow'), 'row count limit')

    def test_decompressed_byte_limit_precedes_row_decode(self):
        self.rejected(b'\xff' * (reader.MAX_DECOMPRESSED_BYTES + 1), 'decompressed byte limit')

    def test_row_parser_requires_actual_bytes(self):
        for value in (None, 'text', bytearray(score_row()), memoryview(score_row()), 1):
            self.rejected(value, 'must be bytes')

    def test_work_limit_is_enforced_before_excess_row_allocation(self):
        with mock.patch.object(reader, 'MAX_WORK_UNITS', 7):
            self.assertEqual(len(reader._parse_rows(score_row())), 1)
            self.rejected(score_row() + b'\n' + score_row(system='other'), 'work limit')


class GzipSafetyTests(unittest.TestCase):
    def inflate(self, raw):
        return reader._decompress_single_member(raw, reader._Budget())

    def test_single_member_round_trip_with_tiny_chunking(self):
        raw = SYNTHETIC_TEXT.read_bytes()
        with mock.patch.object(reader, 'READ_CHUNK_BYTES', 1), mock.patch.object(reader, 'INFLATE_CHUNK_BYTES', 3):
            self.assertEqual(self.inflate(compressed(raw)), raw)

    def test_every_truncation_of_a_small_member_is_rejected(self):
        blob = compressed(score_row())
        for size in range(len(blob)):
            with self.subTest(size=size), self.assertRaises(reader.ReviewInputError):
                self.inflate(blob[:size])

    def test_bad_header_non_gzip_zlib_and_empty_input(self):
        for raw in (b'', b'not gzip', score_row(), zlib.compress(score_row()), b'\x1f\x8b\x09' + b'\x00' * 20):
            with self.subTest(raw=raw), self.assertRaises(reader.ReviewInputError):
                self.inflate(raw)

    def test_crc_and_isize_corruption_are_rejected(self):
        blob = compressed(score_row())
        for index in (-8, -4, -1):
            damaged = bytearray(blob)
            damaged[index] ^= 1
            with self.subTest(index=index), self.assertRaisesRegex(reader.ReviewInputError, 'CRC or size'):
                self.inflate(bytes(damaged))

    def test_concatenation_and_any_trailing_bytes_including_zero_padding_rejected(self):
        blob = compressed(score_row())
        for suffix in (compressed(score_row(system='other')), compressed(b''), b'\x00', b'\x00' * 100, b'junk', b'\n'):
            for chunk_size in (1, reader.READ_CHUNK_BYTES):
                with self.subTest(suffix=suffix[:10], chunk_size=chunk_size), \
                     mock.patch.object(reader, 'READ_CHUNK_BYTES', chunk_size), \
                     self.assertRaisesRegex(reader.ReviewInputError, 'concatenated members or trailing'):
                    self.inflate(blob + suffix)

    def test_optional_filename_header_is_inert(self):
        output = io.BytesIO()
        with gzip.GzipFile(filename='../../never-follow-this-source-name', mode='wb', fileobj=output, mtime=123) as stream:
            stream.write(score_row())
        self.assertEqual(self.inflate(output.getvalue()), score_row())

    def test_reserved_flags_and_header_crc_fail_closed(self):
        blob = compressed(score_row())
        for flag in (0x20, 0x40, 0x80):
            malformed = bytearray(blob)
            malformed[3] |= flag
            with self.assertRaises(reader.ReviewInputError):
                self.inflate(bytes(malformed))
        header = bytearray(blob[:10])
        header[3] |= 2  # FHCRC is then required and checked by zlib.
        with self.assertRaises(reader.ReviewInputError):
            self.inflate(bytes(header) + b'\x00\x00' + blob[10:])

    def test_compressed_size_boundary(self):
        blob = compressed(score_row())
        with mock.patch.object(reader, 'MAX_COMPRESSED_BYTES', len(blob)):
            self.assertEqual(self.inflate(blob), score_row())
            with self.assertRaisesRegex(reader.ReviewInputError, 'compressed byte limit'):
                self.inflate(blob + b'x')

    def test_decompressed_boundary_and_bomb_are_bounded_during_inflate(self):
        raw = (b'a' * 1023 + b'\n') * (reader.MAX_DECOMPRESSED_BYTES // 1024)
        self.assertEqual(self.inflate(compressed(raw)), raw)
        with self.assertRaisesRegex(reader.ReviewInputError, 'decompressed byte limit'):
            self.inflate(compressed(raw + b'a'))
        # 4 MiB expands well past the hard cap from a few KiB of compressed data.
        bomb = compressed((b'a' * 1023 + b'\n') * 4096)
        self.assertLess(len(bomb), reader.MAX_COMPRESSED_BYTES)
        with self.assertRaisesRegex(reader.ReviewInputError, 'decompressed byte limit'):
            self.inflate(bomb)

    def test_inflater_never_uses_unbounded_output_or_flush(self):
        real_factory = zlib.decompressobj
        calls = []
        class BoundedDecoder:
            def __init__(self, *args):
                self.inner = real_factory(*args)
            def decompress(self, data, max_length=0):
                if not 1 <= max_length <= reader.INFLATE_CHUNK_BYTES:
                    raise AssertionError('unbounded decompression')
                calls.append((len(data), max_length))
                return self.inner.decompress(data, max_length)
            def __getattr__(self, key):
                if key == 'flush':
                    raise AssertionError('unbounded flush')
                return getattr(self.inner, key)
        with mock.patch.object(reader.zlib, 'decompressobj', BoundedDecoder):
            raw = (b'a' * 999 + b'\n') * 20
            self.assertEqual(self.inflate(compressed(raw)), raw)
        self.assertGreater(len(calls), 1)

    def test_streaming_line_boundary_crlf_and_final_unterminated_row(self):
        full = b'a' * reader.MAX_LINE_BYTES
        for raw in (full, full + b'\r', full + b'\n', full + b'\r\n', full + b'\r\n' + full):
            with self.subTest(ending=raw[-3:]), mock.patch.object(reader, 'INFLATE_CHUNK_BYTES', 1):
                self.assertEqual(self.inflate(compressed(raw)), raw)
        for raw in (full + b'a', full + b'\ra', full + b'a\n', full + b'a\r\n'):
            with self.subTest(ending=raw[-3:]), self.assertRaisesRegex(reader.ReviewInputError, 'row byte limit.*inflation'):
                self.inflate(compressed(raw))

    def test_streaming_row_boundary_includes_final_unterminated_row(self):
        full = b'a\n' * reader.MAX_ROWS
        self.assertEqual(self.inflate(compressed(full)), full)
        self.assertEqual(self.inflate(compressed(full[:-1])), full[:-1])
        for suffix in (b'a', b'a\n', b'\n', b'\r\n'):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(reader.ReviewInputError, 'row count limit.*inflation'):
                self.inflate(compressed(full + suffix))

    def test_line_and_row_excess_stop_inflation_before_the_rest_of_the_file(self):
        real_factory = zlib.decompressobj
        produced = []
        class WatchedDecoder:
            def __init__(self, *args):
                self.inner = real_factory(*args)
            def decompress(self, data, max_length):
                value = self.inner.decompress(data, max_length)
                produced.append(len(value))
                return value
            def __getattr__(self, key):
                return getattr(self.inner, key)
        tail = (b'a' * 999 + b'\n') * 100
        for head, limit, error in ((b'a' * 1025, reader.MAX_ROWS, 'row byte'), (b'a\nb\nc\n', 2, 'row count')):
            produced.clear()
            with mock.patch.object(reader.zlib, 'decompressobj', WatchedDecoder), \
                 mock.patch.object(reader, 'MAX_ROWS', limit), \
                 self.assertRaisesRegex(reader.ReviewInputError, error + ' limit.*inflation'):
                self.inflate(compressed(head + tail))
            self.assertLessEqual(sum(produced), reader.INFLATE_CHUNK_BYTES)
            self.assertLess(sum(produced), len(tail))

    def test_inflate_work_limit(self):
        with mock.patch.object(reader, 'MAX_WORK_UNITS', 1), mock.patch.object(reader, 'READ_CHUNK_BYTES', 1):
            with self.assertRaisesRegex(reader.ReviewInputError, 'work limit'):
                self.inflate(compressed(score_row()))

    def test_inflater_requires_bytes(self):
        for value in (None, '', bytearray(compressed(score_row())), 1):
            with self.assertRaisesRegex(reader.ReviewInputError, 'must be bytes'):
                self.inflate(value)


class TransportMetadataTests(unittest.TestCase):
    def valid(self):
        # Entirely self-authored transport example, never attached to WMT rows.
        return {'source_url': reader.SOURCE_URL, 'artifact_sha256': reader.PINNED_SHA256,
                'observed_at': '2026-01-02T03:04:05.123Z', 'http_last_modified': '2008-01-01T00:00:00Z'}

    def test_no_transport_observation_is_invented(self):
        self.assertEqual(reader._transport_metadata(None), {
            'status': 'not_supplied', 'observed_at': None, 'http_last_modified': None})

    def test_explicit_transport_is_labeled_supplied_and_not_verified(self):
        value = self.valid()
        result = reader._transport_metadata(value)
        for key in value:
            self.assertEqual(result[key], value[key])
        self.assertIn('operator_supplied', result['status'])
        self.assertIn('not_verified_by_reader', result['status'])
        self.assertIn('not_first_publication', result['time_role'])
        self.assertNotIn('status', value)  # no caller mutation

    def test_header_can_be_unknown_but_observed_at_is_required(self):
        value = self.valid()
        value['http_last_modified'] = None
        self.assertIsNone(reader._transport_metadata(value)['http_last_modified'])
        value['observed_at'] = None
        with self.assertRaises(reader.ReviewInputError):
            reader._transport_metadata(value)

    def test_transport_requires_exact_source_and_artifact_and_only_supported_keys(self):
        variants = [None, [], 'x', {}, {**self.valid(), 'extra': 'unknown'}]
        for key in self.valid():
            changed = self.valid()
            del changed[key]
            variants.append(changed)
        variants.extend([{**self.valid(), 'source_url': 'https://example.invalid'},
                         {**self.valid(), 'artifact_sha256': '0' * 64}])
        for value in variants[1:]:
            with self.subTest(value=value), self.assertRaises(reader.ReviewInputError):
                reader._transport_metadata(value)

    def test_invalid_non_utc_and_imprecise_transport_times_rejected(self):
        for stamp in ('2026-01', '2026-01-01', '2026-01-01T00:00:00', '2026-01-01T00:00:00+01:00',
                      '2026-02-30T00:00:00Z', '2026-01-01T24:00:00Z', '2026-01-01T00:00:00.1234567Z', 1, True):
            for key in ('observed_at', 'http_last_modified'):
                with self.subTest(key=key, stamp=stamp), self.assertRaises(reader.ReviewInputError):
                    reader._transport_metadata({**self.valid(), key: stamp})


class LocalFileAndCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.path = self.directory / 'synthetic.gz'
        self.path.write_bytes(compressed(score_row()))

    def test_urls_stdin_empty_invalid_and_nonstring_paths_rejected_before_open(self):
        for path in ('https://example.com/file.gz', 'file:///tmp/file.gz', '-', '', None, b'file.gz', '/tmp/\x00.gz'):
            with self.subTest(path=path), mock.patch.object(reader.os, 'open') as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, 'local regular'):
                    reader._read_local_bytes(path)
                opened.assert_not_called()

    def test_unc_device_and_network_prefixes_rejected_before_open(self):
        for path in ('//host/share/file.gz', r'\\host\share\file.gz', r'\\.\pipe\file', r'\\?\C:\file', r'/\host/file', r'\host\file'):
            with self.subTest(path=path), mock.patch.object(reader.os, 'open') as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, 'path prefixes'):
                    reader._read_local_bytes(path)
                opened.assert_not_called()

    def test_parent_traversal_length_components_and_unicode_limits(self):
        for path, message in (('../file.gz', 'parent-traversal'), ('a/../file.gz', 'parent-traversal'),
                              ('a/' * reader.MAX_PATH_COMPONENTS + 'f', 'component limit'),
                              ('a' * 4097, 'length limit'), ('\ud800', 'UTF-8'), ('/', 'component limit')):
            with self.subTest(path=path), mock.patch.object(reader.os, 'open') as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, message):
                    reader._read_local_bytes(path)
                opened.assert_not_called()

    def test_file_and_parent_symlinks_are_rejected(self):
        link = self.directory / 'link.gz'
        link.symlink_to(self.path)
        sub = self.directory / 'sub'
        sub.mkdir()
        (sub / 'copy.gz').write_bytes(self.path.read_bytes())
        linked = self.directory / 'linked-dir'
        linked.symlink_to(sub, target_is_directory=True)
        for path in (link, linked / 'copy.gz'):
            with self.assertRaisesRegex(reader.ReviewInputError, 'no-symlink'):
                reader._read_local_bytes(path)

    def test_directory_missing_file_device_and_fifo_fail_closed(self):
        fifo = self.directory / 'fifo'
        os.mkfifo(fifo)
        for path in (self.directory, self.directory / 'absent', Path('/dev/null'), fifo):
            with self.subTest(path=path), self.assertRaises(reader.ReviewInputError):
                reader._read_local_bytes(path)

    def test_unsupported_platform_fails_closed_without_open(self):
        with mock.patch.object(reader.os, 'name', 'nt'), mock.patch.object(reader.os, 'open') as opened:
            with self.assertRaisesRegex(reader.ReviewInputError, 'unavailable'):
                reader._read_local_bytes(str(self.path))
            opened.assert_not_called()

    def test_large_compressed_file_is_rejected_before_read(self):
        self.path.write_bytes(b'x' * (reader.MAX_COMPRESSED_BYTES + 1))
        with mock.patch.object(reader.os, 'read', side_effect=AssertionError('stat should bound first')):
            with self.assertRaisesRegex(reader.ReviewInputError, 'compressed byte limit'):
                reader._read_local_bytes(self.path)

    def test_file_growth_is_caught_with_bounded_read_sentinel(self):
        calls = []
        def growing(_fd, count):
            calls.append(count)
            return b'x' * count
        with mock.patch.object(reader.os, 'read', side_effect=growing):
            with self.assertRaisesRegex(reader.ReviewInputError, 'compressed byte limit'):
                reader._read_local_bytes(self.path)
        self.assertEqual(sum(calls), reader.MAX_COMPRESSED_BYTES + 1)
        self.assertLessEqual(max(calls), reader.READ_CHUNK_BYTES)

    def test_descriptors_closed_on_validation_or_read_failure(self):
        closed = []
        real_close = os.close
        def closing(fd):
            closed.append(fd)
            real_close(fd)
        with mock.patch.object(reader.os, 'read', side_effect=OSError('failure')), \
             mock.patch.object(reader.os, 'close', side_effect=closing):
            with self.assertRaises(reader.ReviewInputError):
                reader._read_local_bytes(self.path)
        self.assertGreaterEqual(len(closed), 2)
        for fd in closed:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_cli_synthetic_is_complete_json_and_default_rejects_it(self):
        command = [sys.executable, str(TOOLS / 'read_wmt08_scores.py'), str(self.path)]
        result = subprocess.run(command + ['--synthetic'], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['dataset_kind'], 'synthetic')
        rejected = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(rejected.stdout, '')
        self.assertIn('fixed WMT08 artifact pin', rejected.stderr)

    def test_cli_transport_restrictions_and_absent_override_flag(self):
        command = [sys.executable, str(TOOLS / 'read_wmt08_scores.py'), str(self.path)]
        for extra in (['--synthetic', '--observed-at', '2026-01-01T00:00:00Z'],
                      ['--http-last-modified', '2008-01-01T00:00:00Z'],
                      ['--expected-sha256', '0' * 64]):
            with self.subTest(extra=extra):
                result = subprocess.run(command + extra, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
