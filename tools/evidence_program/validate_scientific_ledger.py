#!/usr/bin/env python3
"""Validate a small, manually curated A-Lab aggregate ledger entirely offline.

No PDFs, source fetches, experimental protocols, structures, source execution,
canonical import or admission. A valid ledger is structurally consistent, not
independently verified. Artifact hashes stay null because bytes are not inputs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_BYTES = 64 * 1024
MAX_DEPTH = 12
MAX_RECORDS = 32
MAX_PROVENANCE = 3
MAX_STRING = 2048
MAX_COUNT = 1_000_000
SCHEMA_VERSION = 'alab-aggregate-ledger-v1'
REAL_DOI = '10.1038/s41586-023-06734-w'
SYNTHETIC_DOI = '10.0000/synthetic-alab-ledger'
ORIGINAL_URL = 'https://perssongroup.lbl.gov/papers/szymanski_autonomous_laboratory_2023.pdf'
CORRECTED_URL = 'https://bartel.cems.umn.edu/sites/bartel.cems.umn.edu/files/2026-02/szymanski.ceder_2023-nature.pdf'
CORRECTION_URL = 'https://www.nature.com/articles/s41586-025-09992-y'
REAL_SOURCES = {
    ORIGINAL_URL: REAL_DOI,
    CORRECTED_URL: REAL_DOI,
    CORRECTION_URL: '10.1038/s41586-025-09992-y',
}
SYNTHETIC_SOURCES = {
    f'https://example.invalid/scientific-progress/{name}': SYNTHETIC_DOI
    for name in ('original', 'corrected', 'correction')
}
KINDS = {
    'historical_target_summary': ('targets', 'superseded', {'successful', 'denominator'}),
    'corrected_target_partition': ('targets', 'current', {'successful', 'inconclusive', 'not_obtained', 'denominator'}),
    'recipe_summary': ('recipes', 'current', {'successful', 'denominator'}),
}


class LedgerInputError(ValueError):
    """The input is outside the bounded aggregate-only review contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LedgerInputError(message)


def _keys(value: object, expected: set[str], label: str) -> None:
    _require(type(value) is dict and set(value) == expected,
             f'{label} has missing, unknown, or invalid fields')


def _text(value: object, label: str) -> None:
    _require(type(value) is str and bool(value.strip()) and len(value) <= MAX_STRING,
             f'{label} must be bounded nonempty text')
    try:
        encoded = value.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise LedgerInputError(f'{label} contains invalid Unicode') from exc
    _require(len(encoded) <= MAX_STRING and not any(ord(c) < 32 or ord(c) == 127 for c in value),
             f'{label} contains excessive text or control characters')


def _identifier(value: object, label: str) -> None:
    _text(value, label)
    _require(re.fullmatch(r'[a-z][a-z0-9_-]{0,79}', value) is not None,
             f'{label} must be a bounded lowercase identifier')


def _integer(value: object, label: str, minimum: int = 0, maximum: int = MAX_COUNT) -> None:
    _require(type(value) is int and minimum <= value <= maximum,
             f'{label} must be a bounded integer (booleans are not counts)')


def _preflight(text: str) -> None:
    # Bound depth before json.loads allocates nested containers. Total work is
    # already limited by MAX_BYTES. JSON syntax remains the decoder's job.
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
    _require(not quoted and depth == 0, 'invalid JSON syntax')


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON object key')
        result[key] = value
    return result


def _parse_int(token: str) -> int:
    _require(len(token) <= 9, 'JSON integer length limit exceeded')
    return int(token)


def _reject_number(_token: str):
    raise LedgerInputError('floating-point and nonfinite numbers are not accepted')


def _provenance(value: object, input_kind: str, role: str) -> None:
    _require(type(value) is list and 1 <= len(value) <= MAX_PROVENANCE,
             'provenance must contain one to three locator records')
    allowed = REAL_SOURCES if input_kind == 'manual_aggregate' else SYNTHETIC_SOURCES
    urls = []
    for item in value:
        _keys(item, {'source_url', 'source_doi', 'claim_locator', 'capture_status', 'artifact_sha256'}, 'provenance')
        for field in ('source_url', 'source_doi', 'claim_locator', 'capture_status'):
            _text(item[field], f'provenance.{field}')
        url = item['source_url']
        # Exact strings, not substring/hostname matching: queries, redirects,
        # userinfo, alternate ports, fragments and encoded variants all fail.
        _require(url in allowed, 'source URL is not on the fixed allowlist')
        _require(item['source_doi'] == allowed[url], 'source DOI does not match the source URL')
        _require(url not in urls, 'duplicate provenance source URL')
        urls.append(url)
        _require(item['artifact_sha256'] is None,
                 'artifact hash must be null: source bytes were not acquired by this contract')
        statuses = {'text_observed_hash_unavailable', 'indexed_primary_excerpt'} if input_kind == 'manual_aggregate' else {'synthetic_fixture'}
        _require(item['capture_status'] in statuses, 'capture status does not match the input kind')
    if input_kind == 'manual_aggregate':
        required = ({ORIGINAL_URL} if role == 'historical_target_summary' else
                    {CORRECTED_URL} if role == 'campaign' else
                    {CORRECTION_URL} if role == 'correction' else
                    {CORRECTED_URL, CORRECTION_URL})
        _require(required <= set(urls), f'{role} lacks required primary-source provenance')
    # Locators are untrusted inert strings. They are never interpreted as code,
    # paths, commands or instructions; JSON output is not an HTML renderer.


def validate_ledger_bytes(raw: bytes) -> dict:
    """Return one DOI-keyed review campaign; reject ambiguity instead of repair.

    Accepts only UTF-8 JSON bytes. Same record/observation identity with exactly
    equal content is idempotent. Reuse with any different content is rejected.
    Source claim truth is outside this structural validation API.
    """
    _require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'input must be at most 64 KiB of bytes')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise LedgerInputError('input must be UTF-8') from exc
    _preflight(text)
    try:
        document = json.loads(text, object_pairs_hook=_unique_object, parse_int=_parse_int,
                              parse_float=_reject_number, parse_constant=_reject_number)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise LedgerInputError('invalid JSON syntax') from exc
    _keys(document, {'schema_version', 'input_kind', 'campaign', 'records', 'corrections'}, 'ledger')
    _require(document['schema_version'] == SCHEMA_VERSION, 'unsupported schema version')
    kind = document['input_kind']
    _require(type(kind) is str and kind in {'manual_aggregate', 'synthetic_fixture'}, 'invalid input kind')
    campaign = document['campaign']
    null_fields = {'start_date', 'end_date', 'researcher_hours', 'researcher_hours_saved', 'robot_active_hours'}
    _keys(campaign, {'doi', 'elapsed_days', 'provenance'} | null_fields, 'campaign')
    _require(campaign['doi'] == (REAL_DOI if kind == 'manual_aggregate' else SYNTHETIC_DOI),
             'campaign DOI does not match the fixed input profile')
    _integer(campaign['elapsed_days'], 'campaign.elapsed_days', 1, 3650)
    _require(all(campaign[field] is None for field in null_fields),
             'unknown campaign dates and labor fields must remain null')
    _provenance(campaign['provenance'], kind, 'campaign')
    rows = document['records']
    _require(type(rows) is list and 3 <= len(rows) <= MAX_RECORDS, 'record row limit or minimum violated')
    by_id, by_observation = {}, {}
    for row in rows:
        _keys(row, {'record_id', 'observation_id', 'claim_kind', 'unit', 'status', 'counts', 'provenance'}, 'record')
        for field in ('record_id', 'observation_id'):
            _identifier(row[field], field)
        claim = row['claim_kind']
        _require(type(claim) is str and claim in KINDS, 'unknown claim kind')
        unit, status, count_keys = KINDS[claim]
        _require(row['unit'] == unit and row['status'] == status, 'claim unit/status mismatch')
        counts = row['counts']
        _keys(counts, count_keys, 'counts')
        for name, number in counts.items():
            _integer(number, f'counts.{name}', 1 if name == 'denominator' else 0)
        _require(counts['successful'] <= counts['denominator'], 'success count exceeds its denominator')
        if claim == 'corrected_target_partition':
            _require(sum(counts[name] for name in count_keys - {'denominator'}) == counts['denominator'],
                     'corrected target categories must partition the target denominator')
        _provenance(row['provenance'], kind, claim)
        for index, field in ((by_id, 'record_id'), (by_observation, 'observation_id')):
            identity = row[field]
            _require(identity not in index or index[identity] == row,
                     f'conflicting duplicate {field}')
            index[identity] = row
    records = sorted(by_id.values(), key=lambda row: (row['unit'], row['record_id']))
    _require(len(records) == 3 and {row['claim_kind'] for row in records} == set(KINDS),
             'exactly one historical target, one corrected target and one recipe claim are required')
    claims = {row['claim_kind']: row for row in records}
    corrections = document['corrections']
    _require(type(corrections) is list and len(corrections) == 1, 'exactly one correction edge is required')
    edge = corrections[0]
    _keys(edge, {'from_record_id', 'to_record_id', 'relation', 'provenance'}, 'correction')
    _require(edge['relation'] == 'corrects' and
             edge['from_record_id'] == claims['historical_target_summary']['record_id'] and
             edge['to_record_id'] == claims['corrected_target_partition']['record_id'],
             'correction must link the historical target claim to the current target claim')
    _provenance(edge['provenance'], kind, 'correction')
    current = [row for row in records if row['status'] == 'current']
    return {
        'schema_version': SCHEMA_VERSION,
        'input_kind': kind,
        'status': 'experimental_review_records_not_admitted',
        'canonical_import_enabled': False,
        'network_access_performed': False,
        'source_bytes_acquired': False,
        'campaign_count': 1,
        'campaign_key': campaign['doi'],
        'campaign': campaign,
        'records': records,
        'current_records': current,
        'corrections': corrections,
        'interpretation': {
            'current_evidence_basis': 'producer_reanalysis',
            'replication_status': 'independent_replication_not_established',
            'novelty_status': 'novelty_not_necessarily_new_to_science',
            'elapsed_days_measure': 'campaign_duration_not_labor',
            'recipe_remainder_inference': 'not_performed',
            'unit_denominators': 'targets_and_recipes_are_separate',
        },
    }


def read_ledger(path: str | Path) -> dict:
    """Read only a bounded regular local file; no symlink path components.

    Filesystem mount locality is not established. No URL/stdin/device route is
    supplied. Descriptor-relative opens avoid path-check/open races on POSIX.
    """
    try:
        path = os.fspath(path)
    except TypeError as exc:
        raise LedgerInputError('expected a bounded local regular-file path') from exc
    _require(type(path) is str and 0 < len(path) <= 4096 and '://' not in path and
             '\\' not in path and '\x00' not in path and not path.startswith('//') and path != '-',
             'expected a bounded local regular-file path')
    parts = [part for part in path.split('/') if part not in ('', '.')]
    _require(parts and len(parts) <= 64 and '..' not in parts, 'invalid local path components')
    _require(os.name == 'posix' and all(hasattr(os, key) for key in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')),
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
        _require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, 'expected a regular file at most 64 KiB')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            raw = stream.read(MAX_BYTES + 1)
        return validate_ledger_bytes(raw)
    except (OSError, UnicodeError) as exc:
        raise LedgerInputError('cannot read supplied no-symlink local regular file') from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', help='supplied local aggregate JSON file')
    args = parser.parse_args(argv)
    try:
        result = read_ledger(args.ledger)
    except LedgerInputError as exc:
        parser.exit(2, f'error: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
