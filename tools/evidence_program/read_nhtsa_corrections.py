#!/usr/bin/env python3
"""Bounded, offline reader for two manually curated NHTSA publication corrections.

This is not a PDF/HTML parser, source fetcher, crash dataset or canonical importer.
The fixed regression fixture is a derived ledger, not original PDF bytes. Other
valid ledgers are unverified caller observations, never independent corroboration.
Replay is append-only in memory and writes nothing. Unsupported input fails closed.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA_VERSION = 'nhtsa-publication-correction-ledger-v1'
SOURCE_URL = 'https://static.nhtsa.gov/odi/ffdd/sgo-2021-01/SGO-2021-01_Data_Element_Definitions.pdf'
SOURCE_TITLE = 'Standing General Order (SGO) 2021-01 Data Dictionary'
WINDOW_START = '2026-05-01'
WINDOW_END = '2026-09-30'
MAX_BYTES = 64 * 1024
MAX_DEPTH = 8
MAX_NODES = 512
MAX_STRING_BYTES = 512
MAX_RECORDS = 2
MAX_SNAPSHOTS = 8
FIXTURE_SHA256 = 'ecc77475de7ef0dbe2117104317e04b18accff564b408bb24cf40e60d34c3323'
FIXTURE_BYTE_COUNT = 2568
SOURCE_SHA256 = 'c92e1bec238e757867d67ea5bf0b26f4a3e9223d0b92a9a7ce76d446518f4fa4'
SOURCE_BYTE_COUNT = 529128
SOURCE_RETRIEVED_AT_UTC = '2026-10-08T08:24:05.902306+00:00'
PRIOR_CLAIM_ID = 'ASI005-F04'
PRIOR_ARTIFACT_ID = 'asi005_dictionary'
PRIOR_CHAIN_ID = 'ASI-R02'

EXPECTED_RECORDS = {
    'report-34952-11803-v1-2026-08-27': {
        'correction_key': 'report-34952-11803-v1-2026-08-27',
        'correction_kind': 'report_field_publication_correction',
        'change_on': '2026-08-27', 'change_date_precision': 'day',
        'change_source_timezone': None,
        'report_id': '34952-11803', 'report_version': 1,
        'affected_field': 'narrative', 'affected_publication_on': None,
        'reports_received_on_or_before': None,
        'locator': {'physical_pdf_page': 4, 'table': 1,
                    'row_date': '2026-08-27', 'cross_reference_row_date': None},
        'prior_claim_id': PRIOR_CLAIM_ID, 'prior_artifact_id': PRIOR_ARTIFACT_ID,
        'prior_chain_id': PRIOR_CHAIN_ID,
    },
    'release-2026-05-15-restored-2026-06-15': {
        'correction_key': 'release-2026-05-15-restored-2026-06-15',
        'correction_kind': 'release_completeness_publication_correction',
        'change_on': '2026-06-15', 'change_date_precision': 'day',
        'change_source_timezone': None,
        'report_id': None, 'report_version': None,
        'affected_field': 'publication_membership',
        'affected_publication_on': '2026-05-15',
        'reports_received_on_or_before': '2026-04-15',
        'locator': {'physical_pdf_page': 4, 'table': 1,
                    'row_date': '2026-06-15', 'cross_reference_row_date': '2026-05-15'},
        'prior_claim_id': PRIOR_CLAIM_ID, 'prior_artifact_id': PRIOR_ARTIFACT_ID,
        'prior_chain_id': PRIOR_CHAIN_ID,
    },
}
SUMMARIES = {
    'report-34952-11803-v1-2026-08-27':
        'NHTSA records replacement of an unrelated narrative mistakenly associated with report 34952-11803, version 1, through internal processing. This is a publication correction.',
    'release-2026-05-15-restored-2026-06-15':
        'NHTSA records restoration in the June 15 publication of reports received on or before April 15 that internal processing had omitted from the May 15 publication.',
}


class CorrectionInputError(ValueError):
    """Unsupported or unsafe input; no partial successful result is returned."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CorrectionInputError(message)


def _keys(value: object, expected: set[str], label: str) -> None:
    _require(type(value) is dict and set(value) == expected,
             f'{label} has missing, unknown, or invalid fields')


def _same(value: object, expected: object) -> bool:
    """JSON equality without Python's True == 1 coercion."""
    if type(value) is not type(expected):
        return False
    if type(expected) is dict:
        return set(value) == set(expected) and all(_same(value[k], v) for k, v in expected.items())
    if type(expected) is list:
        return len(value) == len(expected) and all(_same(a, b) for a, b in zip(value, expected))
    return value == expected


def _day(value: object, label: str) -> date:
    _require(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is not None,
             f'{label} requires day precision YYYY-MM-DD')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CorrectionInputError(f'{label} is not a valid calendar date') from exc


def _utc(value: object, label: str) -> datetime:
    _require(type(value) is str and re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)', value) is not None,
        f'{label} requires explicit UTC, second through microsecond precision')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise CorrectionInputError(f'{label} is not a valid UTC date/time') from exc


def _sha(value: object, label: str) -> None:
    _require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None,
             f'{label} must be lowercase SHA-256')


def _preflight(text: str) -> None:
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            _require(depth <= MAX_DEPTH, 'JSON nesting limit exceeded')
        elif char in ']}':
            depth -= 1
            _require(depth >= 0, 'invalid JSON syntax')
    _require(depth == 0 and not quoted, 'invalid JSON syntax')


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON object key')
        result[key] = value
    return result


def _parse_int(token: str) -> int:
    _require(len(token) <= 10, 'JSON integer length limit exceeded')
    return int(token)


def _reject_number(_token: str):
    raise CorrectionInputError('floating-point and nonfinite numbers are unsupported')


def _parse(raw: bytes) -> dict:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES,
             'input must be nonempty bytes within the ledger byte limit')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise CorrectionInputError('input must be UTF-8 JSON') from exc
    _require(not text.startswith('\ufeff'), 'JSON byte-order mark is unsupported')
    _preflight(text)
    try:
        value = json.loads(text, object_pairs_hook=_unique_object,
                           parse_int=_parse_int, parse_float=_reject_number,
                           parse_constant=_reject_number)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise CorrectionInputError('invalid or unsupported JSON document') from exc
    stack, count = [value], 0
    while stack:
        item = stack.pop()
        count += 1
        _require(count <= MAX_NODES, 'JSON node limit exceeded')
        if type(item) is dict:
            stack.extend(item.keys())
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)
        elif type(item) is str:
            try:
                size = len(item.encode('utf-8'))
            except UnicodeEncodeError as exc:
                raise CorrectionInputError('invalid Unicode string') from exc
            _require(size <= MAX_STRING_BYTES and not any(ord(c) < 32 or ord(c) == 127 for c in item),
                     'JSON string has excessive bytes or control characters')
    return value


def _document(value: object) -> None:
    _keys(value, {'source_url', 'title', 'edition_on', 'edition_date_precision',
                 'edition_source_timezone', 'physical_pdf_page_count',
                 'source_retrieved_at_utc', 'original_source_sha256',
                 'original_source_byte_count', 'source_http_last_modified_at_utc'}, 'document')
    _require(_same(value['source_url'], SOURCE_URL), 'unsupported source document URL')
    _require(_same(value['title'], SOURCE_TITLE), 'unsupported source document title')
    edition = _day(value['edition_on'], 'document edition')
    _require(WINDOW_START <= value['edition_on'] <= WINDOW_END, 'document edition outside May-September 2026 window')
    _require(_same(value['edition_date_precision'], 'day') and value['edition_source_timezone'] is None,
             'document edition requires day precision and unknown source timezone')
    _require(_same(value['physical_pdf_page_count'], 33), 'unsupported document structure/page count')
    retrieved = _utc(value['source_retrieved_at_utc'], 'source retrieval')
    _require(retrieved.date() >= edition, 'source retrieval precedes document edition')
    if value['original_source_sha256'] is None:
        _require(value['original_source_byte_count'] is None, 'unknown source bytes require null hash and byte count')
    else:
        _sha(value['original_source_sha256'], 'original source hash')
        count = value['original_source_byte_count']
        _require(type(count) is int and 1 <= count <= 10 * 1024 * 1024,
                 'original source byte count must be a bounded integer, never boolean')
    modified = value['source_http_last_modified_at_utc']
    if modified is not None:
        modified_at = _utc(modified, 'HTTP Last-Modified')
        _require(edition <= modified_at.date() and modified_at <= retrieved,
                 'HTTP Last-Modified, edition and retrieval clocks are inconsistent')


def _previous_content(value: object, retrieved_at: datetime) -> None:
    _keys(value, {'availability', 'captured_at_utc', 'content_sha256'}, 'previous content')
    availability = value['availability']
    _require(type(availability) is str and availability in {'not_captured', 'captured_private_not_emitted'},
             'unsupported previous content availability')
    if availability == 'not_captured':
        _require(value['captured_at_utc'] is None and value['content_sha256'] is None,
                 'uncaptured previous content must not invent a timestamp or hash')
    else:
        captured = _utc(value['captured_at_utc'], 'previous content capture')
        _require(captured <= retrieved_at, 'previous content capture follows source retrieval')
        _sha(value['content_sha256'], 'previous content hash')


def _validated(raw: bytes, synthetic_fixture: bool) -> dict:
    value = _parse(raw)
    _keys(value, {'schema_version', 'input_kind', 'scope', 'document', 'corrections'}, 'ledger')
    _require(_same(value['schema_version'], SCHEMA_VERSION), 'unsupported ledger schema')
    expected_kind = 'synthetic_test_ledger' if synthetic_fixture else 'manually_curated_agency_corrections'
    _require(_same(value['input_kind'], expected_kind), 'input kind does not match explicit synthetic mode')
    _require(_same(value['scope'], {'window_start': WINDOW_START, 'window_end': WINDOW_END}),
             'scope must be the fixed May-September 2026 window')
    _document(value['document'])
    if synthetic_fixture:
        _require(value['document']['original_source_sha256'] is None,
                 'synthetic fixture cannot claim original source bytes')
    records = value['corrections']
    _require(type(records) is list and len(records) == MAX_RECORDS,
             'exactly two known correction records are required; no silent truncation')
    seen = set()
    for row in records:
        _keys(row, set(next(iter(EXPECTED_RECORDS.values()))) | {'previous_content'}, 'correction')
        key = row['correction_key']
        _require(type(key) is str and key in EXPECTED_RECORDS, 'unsupported correction identity')
        _require(key not in seen, 'duplicate correction identity')
        seen.add(key)
        change = _day(row['change_on'], 'change date')
        _require(WINDOW_START <= row['change_on'] <= WINDOW_END, 'change date outside review window')
        _require(change <= _day(value['document']['edition_on'], 'document edition'),
                 'change date follows document edition')
        for field in ('affected_publication_on', 'reports_received_on_or_before'):
            if row[field] is not None:
                _day(row[field], field)
        facts = {field: row[field] for field in EXPECTED_RECORDS[key]}
        _require(_same(facts, EXPECTED_RECORDS[key]),
                 'correction differs from the two supported attributed facts, types, locators or prior claim links')
        _previous_content(row['previous_content'], _utc(value['document']['source_retrieved_at_utc'], 'source retrieval'))
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')).hexdigest()


def replay_ledger_bytes(snapshots: list[bytes], *, synthetic_fixture: bool = False) -> dict:
    """Return bounded append-only review history, without writing or fetching.

    Every snapshot must contain exactly the same two supported correction claims.
    Repeated bytes are idempotent. A changed source hash creates a separate artifact
    revision even when report ID/version are unchanged. Unknown source hashes stay
    null: metadata revision fingerprints do not establish byte-level differences.
    All snapshots are validated before any result is returned.
    """
    _require(type(synthetic_fixture) is bool, 'synthetic_fixture must be a boolean')
    _require(type(snapshots) is list and 1 <= len(snapshots) <= MAX_SNAPSHOTS,
             'replay requires one to eight bounded ledger snapshots')
    validated = [_validated(raw, synthetic_fixture) for raw in snapshots]
    prefix = 'synthetic-nhtsa:' if synthetic_fixture else 'nhtsa:'
    artifacts, assertions, ledger_inputs = {}, {}, []
    last_retrieved = None
    for raw, ledger in zip(snapshots, validated):
        raw_hash = hashlib.sha256(raw).hexdigest()
        if raw_hash in ledger_inputs:
            continue
        ledger_inputs.append(raw_hash)
        doc = ledger['document']
        retrieved = _utc(doc['source_retrieved_at_utc'], 'source retrieval')
        _require(last_retrieved is None or retrieved >= last_retrieved,
                 'distinct snapshots must be supplied in nondecreasing capture order')
        last_retrieved = retrieved
        source_hash = doc['original_source_sha256']
        identity_metadata = {key: doc[key] for key in ('source_url', 'title', 'edition_on', 'physical_pdf_page_count')}
        fingerprint = source_hash or _digest(identity_metadata)
        artifact_id = prefix + ('source-bytes:' if source_hash else 'source-metadata:') + fingerprint
        metadata = {key: value for key, value in doc.items() if key not in {'source_retrieved_at_utc', 'source_http_last_modified_at_utc'}}
        observation = {key: doc[key] for key in ('source_retrieved_at_utc', 'source_http_last_modified_at_utc')}
        if artifact_id not in artifacts:
            artifacts[artifact_id] = {
                'artifact_revision_id': artifact_id,
                'revision_identity_basis': 'claimed_original_source_bytes_sha256' if source_hash else 'metadata_fingerprint_not_source_content_hash',
                **metadata, 'observations': [],
            }
        else:
            previous_metadata = {key: artifacts[artifact_id][key] for key in metadata}
            _require(_same(previous_metadata, metadata), 'conflicting metadata for the same artifact identity')
        if observation not in artifacts[artifact_id]['observations']:
            artifacts[artifact_id]['observations'].append(observation)
        for row in sorted(ledger['corrections'], key=lambda entry: entry['correction_key']):
            key = row['correction_key']
            assertion_id = prefix + 'publication-correction:' + key
            if assertion_id not in assertions:
                assertions[assertion_id] = {
                    'assertion_id': assertion_id, 'record_type': 'source_correction',
                    'source_family': 'nhtsa-automated-driving',
                    'prior_claim_id': PRIOR_CLAIM_ID, 'prior_artifact_id': PRIOR_ARTIFACT_ID,
                    'prior_chain_id': PRIOR_CHAIN_ID,
                    'independent_evidence_increment': 0, 'event_count_increment': 0,
                    'revisions': [],
                }
            revision_id = prefix + 'assertion-revision:' + _digest([assertion_id, artifact_id, row])
            revisions = assertions[assertion_id]['revisions']
            if any(revision['assertion_revision_id'] == revision_id for revision in revisions):
                continue
            revisions.append({
                'assertion_revision_id': revision_id,
                'previous_assertion_revision_id': revisions[-1]['assertion_revision_id'] if revisions else None,
                'relation_to_previous_capture': 'next_supplied_capture' if revisions else None,
                'artifact_revision_id': artifact_id,
                **row, 'attributed_factual_summary': SUMMARIES[key],
                'attribution': 'NHTSA agency-authored publication change log',
                'review_status': 'experimental_review_not_admitted',
            })
    return {
        'schema_version': SCHEMA_VERSION, 'status': 'experimental_review_not_admitted',
        'synthetic': synthetic_fixture,
        'canonical_import_enabled': False, 'network_access_performed': False,
        'source_execution_performed': False, 'source_bytes_acquired_by_reader': False,
        'source_hashes_verified_by_reader': False,
        'fixed_curated_fixture_verified': all(value == FIXTURE_SHA256 for value in ledger_inputs),
        'source_hash_basis': 'separate_verifier_receipt_for_fixed_fixture_otherwise_unverified_caller_metadata',
        'scope': {'window_start': WINDOW_START, 'window_end': WINDOW_END},
        'ledger_bytes_sha256': ledger_inputs,
        'assertion_count': len(assertions), 'source_artifact_count': len(artifacts),
        'assertion_revision_count': sum(len(row['revisions']) for row in assertions.values()),
        'independent_evidence_increment': 0, 'event_count_increment': 0,
        'source_artifacts': list(artifacts.values()), 'assertions': list(assertions.values()),
        'rights': {
            'material': 'Agency-authored publication-correction facts and factual identifiers only',
            'basis': 'US government work scope under 17 USC 105; no blanket grant for submitted material',
            'basis_url': 'https://www.govinfo.gov/content/pkg/USCODE-2024-title17/html/USCODE-2024-title17-chap1-sec105.htm',
            'manufacturer_narrative_reuse_grant_established': False,
            'repository_license_applies_to_source_material': False,
        },
        'limitations': [
            'Manual ledger validation does not parse or independently verify the source PDF.',
            'These two claims already occur in ASI005-F04; this is not additional independent evidence.',
            'No crash records, narrative bodies, identities, engagement, injury quantities, causality or rates are emitted.',
            'Previously uncaptured content remains unavailable; no earlier narrative is reconstructed.',
            'Replay preserves supplied revisions, not completeness or chronological ordering of missing history.',
        ],
    }


def validate_ledger_bytes(raw: bytes, *, synthetic_fixture: bool = False) -> dict:
    return replay_ledger_bytes([raw], synthetic_fixture=synthetic_fixture)


def append_ledger_bytes(previous: bytes, current: bytes, *, synthetic_fixture: bool = False) -> dict:
    return replay_ledger_bytes([previous, current], synthetic_fixture=synthetic_fixture)


def _read_regular_file(path: str | Path) -> bytes:
    """Descriptor-relative no-follow reads reject symlink ancestors and devices."""
    try:
        path = os.fspath(path)
    except TypeError as exc:
        raise CorrectionInputError('expected a bounded local regular-file path') from exc
    _require(type(path) is str and 0 < len(path) <= 4096 and '://' not in path and
             '\\' not in path and not any(ord(char) < 32 or ord(char) == 127 for char in path) and
             not path.startswith('//') and path != '-', 'expected a bounded local regular-file path')
    try:
        _require(len(path.encode('utf-8')) <= 4096, 'local path byte limit exceeded')
    except UnicodeEncodeError as exc:
        raise CorrectionInputError('path must be valid UTF-8') from exc
    parts = [part for part in path.split('/') if part not in ('', '.')]
    _require(parts and len(parts) <= 64 and '..' not in parts, 'invalid local path components')
    _require(os.name == 'posix' and all(hasattr(os, name) for name in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')),
             'safe regular-file opening is unavailable')
    directory = descriptor = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory = os.open('/' if path.startswith('/') else '.', flags)
        for part in parts[:-1]:
            child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                             getattr(os, 'O_NOCTTY', 0), dir_fd=directory)
        info = os.fstat(descriptor)
        _require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_BYTES,
                 'expected a nonempty regular file within the ledger byte limit')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            raw = stream.read(MAX_BYTES + 1)
        _require(0 < len(raw) <= MAX_BYTES, 'file grew beyond the ledger byte limit')
        return raw
    except (OSError, UnicodeError) as exc:
        raise CorrectionInputError('cannot read supplied no-symlink local regular file') from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def read_corrections(path: str | Path, *, synthetic_fixture: bool = False) -> dict:
    return validate_ledger_bytes(_read_regular_file(path), synthetic_fixture=synthetic_fixture)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', nargs='+', help='One to eight local manual JSON ledger snapshots in capture order')
    parser.add_argument('--synthetic-fixture', action='store_true')
    args = parser.parse_args(argv)
    try:
        _require(len(args.ledger) <= MAX_SNAPSHOTS, 'at most eight ledger snapshots are supported')
        result = replay_ledger_bytes([_read_regular_file(path) for path in args.ledger],
                                     synthetic_fixture=args.synthetic_fixture)
    except CorrectionInputError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
