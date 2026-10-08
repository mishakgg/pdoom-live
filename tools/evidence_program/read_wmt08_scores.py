#!/usr/bin/env python3
"""Bounded offline review of one pinned WMT08 gzip, or explicit synthetic data.

No fetcher, source admission, canonical import, identity resolution, or metric
aggregation is implemented. The real gzip is NOT distributed with this reader:
its reuse rights are unknown. Synthetic tests never impersonate acquired data.
Only one gzip member is accepted; CRC/ISIZE, truncation, concatenation, and all
trailing bytes (including zero padding) are checked, without unbounded inflate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import zlib

MAX_COMPRESSED_BYTES = 32 * 1024
MAX_DECOMPRESSED_BYTES = 256 * 1024
MAX_ROWS = 4096
MAX_LINE_BYTES = 1024
MAX_FIELD_BYTES = 128
MAX_NUMBER_CHARS = 64
MAX_ABS_EXPONENT = 9999
MAX_WORK_UNITS = 32768
MAX_PATH_COMPONENTS = 64
READ_CHUNK_BYTES = 1024
INFLATE_CHUNK_BYTES = 4096

SOURCE_URL = 'https://www.statmt.org/wmt08/wmt08-human-and-automatic-ranks.gz'
SCHEMA_URL = 'https://www.statmt.org/wmt08/results.html'
PAPER_URL = 'https://aclanthology.org/W08-0309/'
PINNED_SHA256 = 'f49c4f058173c45b0c3ff455be8024ed13d98656810127297d815a502587cbac'
PINNED_COMPRESSED_BYTES = 16071
PINNED_DECOMPRESSED_BYTES = 113529
PINNED_ROW_COUNT = 2584
PINNED_METRIC_LABELS = (
    'Const', 'DP', 'DR', 'Rank', 'SR', 'ULC', 'ULCh', 'Yes/No', 'bleu',
    'mbleu', 'meteor-baseline', 'meteor-ranking', 'mter', 'posF4gram-am',
    'posF4gram-gm', 'posbleu', 'svm-rank',
)
PINNED_SYSTEM_TYPE_COUNTS = {'rbmt': 843, 'smt': 1703, 'syscomb': 38}
PUBLISHED_DIRECTION = 'higher_is_better'
DECIMAL_TOKEN = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE]([+-]?[0-9]+))?\Z', re.ASCII)
UTC_TIMESTAMP = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z\Z', re.ASCII)


class ReviewInputError(ValueError):
    """Input is outside this deliberately narrow offline review boundary."""


class _Budget:
    """Count bounded read/inflate calls and each row/field parsing operation."""

    def __init__(self):
        self.used = 0

    def charge(self, units: int = 1) -> None:
        self.used += units
        if self.used > MAX_WORK_UNITS:
            raise ReviewInputError('reader work limit exceeded')


class _InflatedLineLimits:
    """Enforce row and physical-line bounds as each inflate chunk arrives.

    The only extra line byte allowed is CR immediately before LF (or EOF).
    Every byte is visited once, independently bounded by the decompressed cap;
    no unbounded split or buffer is used. Field syntax is checked afterwards.
    """

    def __init__(self):
        self.completed_rows = 0
        self.line_bytes = 0

    def feed(self, chunk: bytes) -> None:
        for byte in chunk:
            if byte == 10:
                self.completed_rows += 1
                if self.completed_rows > MAX_ROWS:
                    raise ReviewInputError('row count limit exceeded during inflation')
                self.line_bytes = 0
            else:
                if self.completed_rows >= MAX_ROWS:
                    raise ReviewInputError('row count limit exceeded during inflation')
                self.line_bytes += 1
                if self.line_bytes > MAX_LINE_BYTES and not (self.line_bytes == MAX_LINE_BYTES + 1 and byte == 13):
                    raise ReviewInputError('row byte limit exceeded during inflation')


def _read_local_bytes(path: str | Path, budget: _Budget | None = None) -> bytes:
    """Descriptor-relative no-symlink traversal; bounded regular-file reads.

    POSIX support is mandatory. No URLs, stdin, devices, FIFOs, parent traversal
    or UNC routes are accepted. OS-mounted remote filesystems are not detectable.
    The snapshot read is hashed; local file mtimes never become source dates.
    """
    budget = budget if budget is not None else _Budget()
    try:
        path = os.fspath(path)
    except TypeError as exc:
        raise ReviewInputError('only supplied local regular files are accepted') from exc
    if not isinstance(path, str) or not path or '://' in path or path == '-' or '\x00' in path:
        raise ReviewInputError('only supplied local regular files are accepted')
    if path.startswith('\\') or path.replace('\\', '/').startswith('//'):
        raise ReviewInputError('UNC, device and network path prefixes are not accepted')
    try:
        if len(path.encode('utf-8')) > 4096:
            raise ReviewInputError('local path length limit exceeded')
    except UnicodeEncodeError as exc:
        raise ReviewInputError('local path must be UTF-8') from exc
    parts = [part for part in path.split('/') if part not in ('', '.')]
    if '..' in parts:
        raise ReviewInputError('parent-traversal path components are not accepted')
    if not parts or len(parts) > MAX_PATH_COMPONENTS:
        raise ReviewInputError('local path component limit exceeded')
    if os.name != 'posix' or not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise ReviewInputError('safe no-symlink regular-file opening is unavailable')
    directory = descriptor = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory = os.open('/' if path.startswith('/') else '.', flags)
        for component in parts[:-1]:
            child = os.open(component, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | getattr(os, 'O_NOCTTY', 0), dir_fd=directory)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ReviewInputError('only supplied local regular files are accepted')
        if info.st_size > MAX_COMPRESSED_BYTES:
            raise ReviewInputError('compressed byte limit exceeded')
        chunks = []
        size = 0
        while size <= MAX_COMPRESSED_BYTES:
            budget.charge()
            chunk = os.read(descriptor, min(READ_CHUNK_BYTES, MAX_COMPRESSED_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_COMPRESSED_BYTES:
            raise ReviewInputError('compressed byte limit exceeded')
        return b''.join(chunks)
    except OSError as exc:
        raise ReviewInputError('cannot read supplied no-symlink local regular file') from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def _decompress_single_member(raw: bytes, budget: _Budget) -> bytes:
    """Never call gzip.decompress/read or zlib.flush with unbounded output."""
    if type(raw) is not bytes:
        raise ReviewInputError('compressed input must be bytes')
    if len(raw) > MAX_COMPRESSED_BYTES:
        raise ReviewInputError('compressed byte limit exceeded')
    if not raw:
        raise ReviewInputError('empty gzip input')
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    output = bytearray()
    line_limits = _InflatedLineLimits()
    cursor = 0
    pending = b''
    while True:
        budget.charge()
        if not pending and cursor < len(raw):
            pending = raw[cursor:cursor + READ_CHUNK_BYTES]
            cursor += len(pending)
        # A one-byte sentinel detects overflow without allocating the bomb.
        limit = min(INFLATE_CHUNK_BYTES, MAX_DECOMPRESSED_BYTES + 1 - len(output))
        try:
            chunk = decoder.decompress(pending, limit)
        except zlib.error as exc:
            raise ReviewInputError('invalid gzip stream, header, CRC or size trailer') from exc
        if len(output) + len(chunk) > MAX_DECOMPRESSED_BYTES:
            raise ReviewInputError('decompressed byte limit exceeded')
        line_limits.feed(chunk)
        output.extend(chunk)
        pending = decoder.unconsumed_tail
        if decoder.eof:
            if decoder.unused_data or pending or cursor != len(raw):
                raise ReviewInputError('gzip concatenated members or trailing bytes are not accepted')
            return bytes(output)
        if not chunk and not pending and cursor == len(raw):
            raise ReviewInputError('truncated gzip stream')


def _score(token: str) -> str:
    if len(token) > MAX_NUMBER_CHARS:
        raise ReviewInputError('score number length limit exceeded')
    match = DECIMAL_TOKEN.fullmatch(token)
    if not match:
        raise ReviewInputError('score must be a strict finite decimal')
    exponent = match.group(1)
    if exponent is not None and (len(exponent.lstrip('+-')) > 4 or abs(int(exponent)) > MAX_ABS_EXPONENT):
        raise ReviewInputError('score exponent limit exceeded')
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ReviewInputError('score must be a strict finite decimal') from exc
    if not value.is_finite():
        raise ReviewInputError('score must be a strict finite decimal')
    # Do not quantize, round, convert to float, reverse, or strip trailing zeros.
    return token


def _parse_rows(raw: bytes, budget: _Budget | None = None) -> list[dict]:
    """Testable syntax layer; emits no real-source provenance or admission claim.

    Six ASCII whitespace-delimited fields, with LF/CRLF and optional final LF.
    Blank rows, comments, headers and control characters fail closed. Label
    vocabularies are not rewritten. Duplicate four-field keys require review,
    including identical rows; no value is silently overwritten or averaged.
    """
    budget = budget if budget is not None else _Budget()
    if type(raw) is not bytes:
        raise ReviewInputError('decompressed input must be bytes')
    if len(raw) > MAX_DECOMPRESSED_BYTES:
        raise ReviewInputError('decompressed byte limit exceeded')
    if not raw:
        raise ReviewInputError('score file must contain at least one row')
    lines = raw.split(b'\n', MAX_ROWS + 1)
    if lines[-1] == b'':
        lines.pop()
    if len(lines) > MAX_ROWS:
        raise ReviewInputError('row count limit exceeded')
    rows = []
    seen = set()
    offset = 0
    for number, encoded in enumerate(lines, 1):
        budget.charge()
        line = encoded[:-1] if encoded.endswith(b'\r') else encoded
        if len(line) > MAX_LINE_BYTES:
            raise ReviewInputError('row byte limit exceeded')
        if any(byte != 9 and not 32 <= byte <= 126 for byte in line):
            raise ReviewInputError('rows must use printable ASCII and space/tab delimiters')
        fields = line.split(None, 6)
        if len(fields) != 6:
            raise ReviewInputError('each row must have exactly six fields')
        budget.charge(6)
        if any(len(field) > MAX_FIELD_BYTES for field in fields):
            raise ReviewInputError('field byte limit exceeded')
        metric, language, test_set, system, score, system_type = [field.decode('ascii') for field in fields]
        score = _score(score)
        key = (metric, language, test_set, system)
        if key in seen:
            raise ReviewInputError('duplicate four-field measurement key requires review')
        seen.add(key)
        rows.append({
            'line_number': number,
            'decompressed_byte_offset': offset,
            'raw_row': line.decode('ascii'),
            'metric_raw': metric,
            'language_pair_raw': language,
            'test_set_raw': test_set,
            'system_id_raw': system,
            'score_raw': score,
            'score_numeric': score,
            'score_numeric_representation': 'exact_finite_decimal_string',
            'system_type_raw': system_type,
        })
        offset += len(encoded) + (1 if offset + len(encoded) < len(raw) else 0)
    return rows


def _transport_metadata(observation: dict | None) -> dict:
    """Accept explicit operator-supplied observations; do not attest a fetch."""
    if observation is None:
        return {'status': 'not_supplied', 'observed_at': None, 'http_last_modified': None}
    expected = {'source_url', 'artifact_sha256', 'observed_at', 'http_last_modified'}
    if type(observation) is not dict or set(observation) != expected:
        raise ReviewInputError('transport observation must contain only the four required fields')
    if observation['source_url'] != SOURCE_URL or observation['artifact_sha256'] != PINNED_SHA256:
        raise ReviewInputError('transport observation must identify the pinned source and artifact')
    for key in ('observed_at', 'http_last_modified'):
        value = observation[key]
        if key == 'http_last_modified' and value is None:
            continue
        if type(value) is not str or not UTC_TIMESTAMP.fullmatch(value):
            raise ReviewInputError('transport times must be explicit UTC ISO timestamps')
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ReviewInputError('transport times must be valid UTC ISO timestamps') from exc
    return {
        **observation,
        'status': 'operator_supplied_observed_transport_metadata_not_verified_by_reader',
        'time_role': 'transport_only_not_first_publication_execution_or_independent_archive_capture',
    }


def _unknown(status: str = 'unknown_not_reported_in_score_file') -> dict:
    return {'value': None, 'status': status}


def _published_metric_semantics(metric: str) -> str:
    """Schema interpretation only, never evidence that an evaluation occurred."""
    if metric == 'Rank':
        return 'relative_human_greater_or_equal_comparison_aggregate_not_ordinal_rank'
    if metric == 'mter':
        return 'mter_direction_already_reversed_in_source_do_not_reverse_again'
    return 'source_metric_scale_preserved_not_assumed_to_be_probability'


def _review_result(compressed: bytes, expanded: bytes, rows: list[dict], *, synthetic: bool,
                   transport: dict) -> dict:
    sha256 = hashlib.sha256(compressed).hexdigest()
    if not synthetic and (sha256 != PINNED_SHA256 or len(compressed) != PINNED_COMPRESSED_BYTES):
        raise ReviewInputError('real review provenance requires the fixed WMT08 artifact pin')
    prefix = 'wmt08-synthetic' if synthetic else 'wmt08-review'
    artifact_id = f'{prefix}:sha256:{sha256}'
    for row in rows:
        # Review identities are artifact scoped. A same-name system in another
        # language/task or artifact is not a globally resolved model identity.
        task_tuple = [row['language_pair_raw'], row['test_set_raw'], row['system_id_raw']]
        task_hash = hashlib.sha256(json.dumps(task_tuple, separators=(',', ':')).encode('ascii')).hexdigest()
        row.update({
            'assertion_id': f'{artifact_id}:row:{row["line_number"]}',
            'evaluation_group_id': f'{artifact_id}:task-system:{task_hash}',
            'measurement_key_raw': [row[key] for key in ('metric_raw', 'language_pair_raw', 'test_set_raw', 'system_id_raw')],
            'dataset_kind': 'synthetic' if synthetic else 'pinned_historical_artifact_review',
            'direction_as_published': None if synthetic else PUBLISHED_DIRECTION,
            'direction_status': 'synthetic_test_value_not_source_claim' if synthetic else 'official_schema_no_rescaling_or_reversal',
            'metric_semantics': 'synthetic_test_value_not_an_observed_result' if synthetic else _published_metric_semantics(row['metric_raw']),
            'resolved_system_identity': _unknown('unresolved_no_cross_source_identity_matching'),
            'denominator': _unknown(),
            'uncertainty': _unknown(),
            'evaluation_execution_time': _unknown(),
            'duplicate_report_links': [],
            'duplicate_report_status': 'not_resolved_no_independent_evaluation_claim',
            'revision_links': [],
            'revision_status': 'not_resolved_no_revision_chronology_inferred',
        })
    return {
        'record_kind': 'experimental_wmt08_score_review',
        'status': 'experimental_review_records_not_admitted',
        'review_state': 'needs_review',
        'dataset_kind': 'synthetic' if synthetic else 'pinned_historical_artifact_review',
        'canonical_schema_claimed': False,
        'source_admission_enabled': False,
        'production_import_enabled': False,
        'network_access_performed': False,
        'network_access_flag_scope': 'reader-issued requests only; OS filesystem mount locality is not established',
        'links_followed': False,
        'provenance': {
            'artifact_id': artifact_id,
            'source_family': None if synthetic else 'WMT historical shared-task results',
            'benchmark_edition': None if synthetic else 'WMT08',
            'source_url': None if synthetic else SOURCE_URL,
            'schema_url': None if synthetic else SCHEMA_URL,
            'paper_url': None if synthetic else PAPER_URL,
            'compressed_sha256': sha256,
            'compressed_byte_count': len(compressed),
            'decompressed_sha256': hashlib.sha256(expanded).hexdigest(),
            'decompressed_byte_count': len(expanded),
            'pin_status': 'synthetic_unpinned_not_source_evidence' if synthetic else 'matches_fixed_reviewed_artifact',
            'extraction_method': 'bounded_offline_single_member_gzip_six_field_decimal_v1',
            'reader_execution_time': _unknown('not_recorded_no_clock_or_file_mtime_inference'),
            'transport_observation': transport,
        },
        'historical_dates': {
            'workshop_date': _unknown('not_applicable_synthetic') if synthetic else {'value': '2008-06-19', 'precision': 'day', 'status': 'official_workshop_date', 'evidence_url': SCHEMA_URL},
            'paper_publication_date': _unknown('not_applicable_synthetic') if synthetic else {'value': '2008-06', 'precision': 'month', 'status': 'publisher_metadata', 'evidence_url': PAPER_URL},
            'artifact_first_publication_at': _unknown('not_established'),
            'archive_capture_at': _unknown('independent_dated_capture_not_verified'),
            'evaluation_execution_time': _unknown(),
        },
        'data_rights': {
            'rights_status': 'synthetic_input_rights_not_assessed' if synthetic else 'unknown',
            'license_identifier': None,
            'scope': 'synthetic_input_only_no_real_source_rights_claim' if synthetic else 'selected_gzip_artifact_only',
            'paper_license_inherited': False,
            'repository_license_inherited': False,
            'redistribution_permission_established': False,
        },
        'structural_counts': {
            'rows': len(rows),
            'metric_labels': sorted({row['metric_raw'] for row in rows}),
            'system_type_counts': dict(sorted(Counter(row['system_type_raw'] for row in rows).items())),
        },
        'identity_scope': 'artifact_local_review_references_not_canonical_system_or_experiment_identifiers',
        'independent_evaluations_count': _unknown('score_rows_are_not_independent_experiments'),
        'schema_documentation_note': ('not_applicable_synthetic' if synthetic else
            'published_examples_are_narrower_than_artifact_labels_original_cz-en_xx-en_en-hu_es-de_nc-test2008_are_preserved'),
        'rows': rows,
        'limits': [
            'single local gzip; exactly one member; no trailing bytes or concatenation',
            'all numeric lexemes retained as finite Decimal strings; no floats or universal [0,1] range',
            'no cross-year comparison, trend, probability, p(doom), deployment or capability frontier inference',
            'rows are reported scores, not independent experiments or a complete participant census',
            'WMT08 paper reports All-English judgments reused in individual News language pairs; row-level reuse links are not resolved here',
            'no vendor, checkpoint, hardware, training-budget or globally resolved system identities',
            'no paper/file duplicate-report linking or corrected-versus-new-evaluation inference',
            'rights unresolved for real gzip; no automatic redistribution or publication',
            'safe POSIX regular-file opening cannot establish OS filesystem mount locality',
        ],
    }


def read_pinned_scores(path: str | Path, *, transport_observation: dict | None = None) -> dict:
    """Read only the fixed historical artifact. There is no caller-set pin."""
    transport = _transport_metadata(transport_observation)
    budget = _Budget()
    raw = _read_local_bytes(path, budget)
    if len(raw) != PINNED_COMPRESSED_BYTES or hashlib.sha256(raw).hexdigest() != PINNED_SHA256:
        raise ReviewInputError('input does not match the fixed WMT08 artifact pin; drift requires separate review')
    expanded = _decompress_single_member(raw, budget)
    rows = _parse_rows(expanded, budget)
    if (len(expanded) != PINNED_DECOMPRESSED_BYTES or len(rows) != PINNED_ROW_COUNT
            or tuple(sorted({row['metric_raw'] for row in rows})) != PINNED_METRIC_LABELS
            or dict(Counter(row['system_type_raw'] for row in rows)) != PINNED_SYSTEM_TYPE_COUNTS):
        raise ReviewInputError('fixed artifact does not match reviewed structural identity')
    return _review_result(raw, expanded, rows, synthetic=False, transport=transport)


def read_synthetic_scores(path: str | Path) -> dict:
    """Explicit test mode: arbitrary bounded syntax-valid bytes stay synthetic."""
    budget = _Budget()
    raw = _read_local_bytes(path, budget)
    if hashlib.sha256(raw).hexdigest() == PINNED_SHA256:
        raise ReviewInputError('the real pinned artifact cannot be relabeled synthetic')
    expanded = _decompress_single_member(raw, budget)
    rows = _parse_rows(expanded, budget)
    return _review_result(raw, expanded, rows, synthetic=True,
                          transport={'status': 'not_applicable_synthetic', 'observed_at': None, 'http_last_modified': None})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scores', help='one supplied local gzip; real mode requires the fixed SHA-256')
    parser.add_argument('--synthetic', action='store_true', help='explicitly label self-authored test input synthetic')
    parser.add_argument('--observed-at', help='explicit source acquisition observation in UTC ISO format')
    parser.add_argument('--http-last-modified', help='explicit observed HTTP header time in UTC ISO format; transport only')
    args = parser.parse_args(argv)
    try:
        if args.synthetic and (args.observed_at is not None or args.http_last_modified is not None):
            raise ReviewInputError('synthetic mode cannot claim source transport observations')
        if args.http_last_modified is not None and args.observed_at is None:
            raise ReviewInputError('HTTP last-modified requires explicit observed-at evidence')
        observation = None if args.observed_at is None else {
            'source_url': SOURCE_URL, 'artifact_sha256': PINNED_SHA256,
            'observed_at': args.observed_at, 'http_last_modified': args.http_last_modified,
        }
        result = read_synthetic_scores(args.scores) if args.synthetic else read_pinned_scores(args.scores, transport_observation=observation)
    except ReviewInputError as exc:
        parser.exit(2, f'error: {exc}\n')
    print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
