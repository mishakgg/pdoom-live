#!/usr/bin/env python3
"""Validate and normalize one supplied, manually curated BARN 2024 Table II.

This is an offline JSON review helper, not an HTML/PDF extractor, collector,
source-truth check, robot controller, ranking system or canonical importer.
Only arXiv 2407.01862v1 is supported. A new/reordered source version requires
explicit reconciliation; displayed positions are not cross-version trial IDs.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_BYTES = 64 * 1024
MAX_DEPTH = 12
MAX_ROWS = 120
MAX_SUMMARIES = 8
MAX_STRING_BYTES = 2048
MAX_TIME_SECONDS = 86400
SCHEMA_VERSION = 'barn-2024-curated-table-v1'
EVENT_ID = 'barn-2024-physical-finals'
SOURCE_VERSION = '2407.01862v1'
SOURCE_URL = 'https://arxiv.org/html/2407.01862v1'
ABSTRACT_URL = 'https://arxiv.org/abs/2407.01862v1'
PDF_URL = 'https://arxiv.org/pdf/2407.01862v1'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
TEAM_IDS = {'LiCS-KI': 'lics-ki', 'MLDA_EEE': 'mlda-eee', 'AIMS': 'aims', 'EIT-NUS': 'eit-nus'}
ROW_FIELDS = ['team_raw', 'course_number', 'reported_position_in_course_cell', 'outcome_raw']
FIXTURE_ID = 'barn_2024_physical_table_ii_v1'
FIXTURE_KIND = 'manually_verified_derived_table_transcription_not_full_source_bytes'
INTERPRETATION = {
    'numeric_values': 'successful completion times in seconds',
    'X': 'reported failure, cause unspecified',
    'reported_position_in_course_cell': '1-based left-to-right position in the slash-delimited source cell; chronological order unverified',
    'cell_locator_template': 'Table II / row={team_raw} / column=Course {course_number} / slash_position={reported_position_in_course_cell}',
    'outcome_count': 60,
    'chronological_attempt_number': None,
}


class TableInputError(ValueError):
    """The supplied input exceeds the bounded curated-table review contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TableInputError(message)


def _keys(value: object, expected: set[str], label: str) -> None:
    _require(type(value) is dict and set(value) == expected,
             f'{label} has missing, unknown, or invalid fields')


def _text(value: object, label: str) -> None:
    _require(type(value) is str and bool(value.strip()) and len(value) <= MAX_STRING_BYTES,
             f'{label} must be bounded nonempty text')
    try:
        encoded = value.encode('utf-8')
    except UnicodeEncodeError as exc:
        raise TableInputError(f'{label} contains invalid Unicode') from exc
    _require(len(encoded) <= MAX_STRING_BYTES and not any(ord(c) < 32 or ord(c) == 127 for c in value),
             f'{label} contains excessive text or control characters')


def _integer(value: object, low: int, high: int, label: str) -> None:
    _require(type(value) is int and low <= value <= high,
             f'{label} must be a bounded integer, not a boolean')


def _time_token(value: object, label: str) -> int:
    _text(value, label)
    _require(re.fullmatch(r'[1-9][0-9]{0,4}', value, re.ASCII) is not None,
             f'{label} must be a positive integer-seconds string')
    seconds = int(value)
    _require(seconds <= MAX_TIME_SECONDS, f'{label} exceeds the seconds bound')
    return seconds


def _preflight(text: str) -> None:
    # Bound nesting before allocation. All other JSON work is bounded by bytes.
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
    raise TableInputError('floating-point and nonfinite numbers are not accepted')


def _source(source: object) -> None:
    _keys(source, {'title', 'authors', 'url', 'abstract_url', 'pdf_url', 'artifact_version',
                   'submitted_at_utc', 'retrieved_at_utc', 'locator', 'license_spdx',
                   'license_url', 'attribution', 'changes', 'manuscript_sha256'}, 'source')
    for field, value in source.items():
        if field not in {'authors', 'manuscript_sha256'}:
            _text(value, f'source.{field}')
    _require(source['artifact_version'] == SOURCE_VERSION,
             'unsupported source version: reconcile changed tables explicitly before admission')
    for field, value in [('url', SOURCE_URL), ('abstract_url', ABSTRACT_URL),
                         ('pdf_url', PDF_URL), ('license_url', LICENSE_URL)]:
        _require(source[field] == value, f'source.{field} does not match the fixed allowlist')
    _require(source['license_spdx'] == 'CC-BY-4.0', 'curated excerpt must retain its CC BY 4.0 attribution')
    _require(source['manuscript_sha256'] is None,
             'manuscript hash must be null; curated JSON is not full manuscript bytes')
    authors = source['authors']
    _require(type(authors) is list and 1 <= len(authors) <= 32, 'bounded source authors required')
    for author in authors:
        _text(author, 'author')
    _require(len(authors) == len(set(authors)), 'duplicate author')
    for field in ('submitted_at_utc', 'retrieved_at_utc'):
        _require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', source[field]) is not None,
                 f'{field} must be an explicit UTC timestamp')
        try:
            datetime.strptime(source[field], '%Y-%m-%dT%H:%M:%SZ')
        except ValueError as exc:
            raise TableInputError(f'invalid {field}') from exc


def _credit(successes: list[dict]) -> dict:
    """Reconstruct best-three successful values without breaking tied identities.

    This is a rule-derived subset description, not an organizer's run-ID ledger.
    Failed-credit membership is never assigned to specific source positions.
    """
    ranked = sorted(successes, key=lambda row: row['completion_time_seconds'])
    count = min(3, len(ranked))
    certain = sorted(row['reported_position_in_course_cell'] for row in ranked)
    tied, slots, selected = [], 0, certain
    if len(ranked) > 3:
        cutoff = ranked[2]['completion_time_seconds']
        certain = sorted(row['reported_position_in_course_cell'] for row in ranked
                         if row['completion_time_seconds'] < cutoff)
        boundary = sorted(row['reported_position_in_course_cell'] for row in ranked
                          if row['completion_time_seconds'] == cutoff)
        needed = 3 - len(certain)
        if len(boundary) > needed:
            tied, slots, selected = boundary, needed, None
        else:
            certain = sorted(certain + boundary)
            selected = certain
    return {
        'basis': 'rule_reconstruction_not_published_run_membership',
        'successful': count,
        'denominator': 3,
        'failed_credit_slots': 3 - count,
        'selected_successful_times_seconds': [row['completion_time_seconds'] for row in ranked[:3]],
        'certain_successful_reported_positions': certain,
        'ambiguous_boundary_reported_positions': tied,
        'boundary_slots_to_choose': slots,
        'selected_successful_reported_positions': selected,
        'selected_failed_reported_positions': None,
        'row_membership_ambiguous': bool(tied) or count < 3,
    }


def validate_table_bytes(raw: bytes) -> dict:
    """Normalize bounded UTF-8 JSON; structural validity is not source verification.

    Exactly 60 unique source coordinates are required. Equal duplicate rows are
    idempotent; unequal duplicates fail. IDs are excerpt/version scoped. Different
    raw formatting or duplicates change the input-byte hash, not normalized IDs.
    """
    _require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'input must be at most 64 KiB of bytes')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise TableInputError('input must be UTF-8') from exc
    _preflight(text)
    try:
        document = json.loads(text, object_pairs_hook=_unique_object, parse_int=_parse_int,
                              parse_float=_reject_number, parse_constant=_reject_number)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise TableInputError('invalid JSON syntax') from exc
    _keys(document, {'schema_version', 'event_id', 'fixture_id', 'fixture_kind', 'source',
                     'row_fields', 'row_interpretation', 'rows', 'published_team_summaries'}, 'table')
    _require(document['schema_version'] == SCHEMA_VERSION, 'unsupported schema version')
    _require(document['event_id'] == EVENT_ID, 'unsupported event: physical BARN 2024 only')
    _require(document['fixture_id'] == FIXTURE_ID and document['fixture_kind'] == FIXTURE_KIND,
             'unsupported curated fixture identity or kind')
    _source(document['source'])
    _require(document['row_fields'] == ROW_FIELDS, 'source row fields or order differ')
    _keys(document['row_interpretation'], set(INTERPRETATION), 'row_interpretation')
    _require(document['row_interpretation'] == INTERPRETATION, 'reported-position and outcome semantics must be retained')
    _integer(document['row_interpretation']['outcome_count'], 60, 60, 'outcome_count')
    rows = document['rows']
    _require(type(rows) is list and 60 <= len(rows) <= MAX_ROWS, 'row count limit or minimum violated')
    by_coordinate = {}
    for row in rows:
        _require(type(row) is list and len(row) == 4, 'each source row must have exactly four cells')
        team, course, position, outcome = row
        _require(type(team) is str and team in TEAM_IDS, 'unknown team')
        _integer(course, 1, 3, 'course_number')
        _integer(position, 1, 5, 'reported_position_in_course_cell')
        if outcome != 'X':
            _time_token(outcome, 'outcome_raw')
        key = (team, course, position)
        _require(key not in by_coordinate or by_coordinate[key] == row,
                 'conflicting duplicate event/version/team/course/reported-position identity')
        by_coordinate[key] = row
    required = {(team, course, position) for team in TEAM_IDS for course in range(1, 4) for position in range(1, 6)}
    _require(set(by_coordinate) == required, 'all 60 unique source coordinates must be present')
    ordered_rows = [by_coordinate[key] for key in sorted(required)]
    attempts = []
    for team, course, position, outcome in ordered_rows:
        attempts.append({
            'observation_id': f'{EVENT_ID}:{SOURCE_VERSION}:{TEAM_IDS[team]}:course-{course}:position-{position}',
            'event_id': EVENT_ID,
            'source_version': SOURCE_VERSION,
            'team_id': TEAM_IDS[team],
            'team_raw': team,
            'course_number': course,
            'reported_position_in_course_cell': position,
            'outcome_raw': outcome,
            'status': 'failed' if outcome == 'X' else 'successful',
            'completion_time_seconds': None if outcome == 'X' else int(outcome),
            'failure_cause': None,
            'chronological_attempt_number': None,
            'native_run_id': None,
            'hardware_instance_id': None,
            'exact_system_version': None,
            'started_at': None,
            'reset_count': None,
            'reset_duration_seconds': None,
            'practice_attempt_count': None,
            'checkpoint_id': None,
            'observed_intervention_count': None,
            'evidence_locator': f'Table II / row={team} / column=Course {course} / slash_position={position}',
        })
    summaries = document['published_team_summaries']
    _require(type(summaries) is list and 4 <= len(summaries) <= MAX_SUMMARIES, 'team summary count limit violated')
    by_team = {}
    for summary in summaries:
        _keys(summary, {'team_raw', 'rank', 'success_total_raw', 'course_average_times_raw'}, 'team summary')
        team = summary['team_raw']
        _require(type(team) is str and team in TEAM_IDS, 'unknown summary team')
        _integer(summary['rank'], 1, 4, 'published rank')
        _text(summary['success_total_raw'], 'success_total_raw')
        _text(summary['course_average_times_raw'], 'course_average_times_raw')
        _require(team not in by_team or by_team[team] == summary, 'conflicting duplicate team summary')
        by_team[team] = summary
    _require(set(by_team) == set(TEAM_IDS), 'one summary per team required')
    _require({row['rank'] for row in by_team.values()} == {1, 2, 3, 4}, 'published ranks must be distinct')
    course_summaries, team_summaries = [], []
    for team in sorted(TEAM_IDS):
        published = by_team[team]
        match = re.fullmatch(r'([0-9])/9(?: \(([1-9][0-9]{0,4})\))?', published['success_total_raw'], re.ASCII)
        _require(match is not None, 'invalid published success-total cell')
        averages = published['course_average_times_raw'].split('/')
        _require(len(averages) == 3, 'three published course averages required')
        all_successful = credited_successful = 0
        for course, average in enumerate(averages, 1):
            group = [row for row in attempts if row['team_raw'] == team and row['course_number'] == course]
            successful = [row for row in group if row['status'] == 'successful']
            average_seconds = None if average == 'NA' else _time_token(average, 'published course average')
            _require((average == 'NA') == (not successful), 'published NA must match no successful course times')
            credit = _credit(successful)
            all_successful += len(successful)
            credited_successful += credit['successful']
            course_summaries.append({
                'course_observation_id': f'{EVENT_ID}:{SOURCE_VERSION}:{TEAM_IDS[team]}:course-{course}',
                'team_id': TEAM_IDS[team], 'team_raw': team, 'course_number': course,
                'all_reported_attempts': {'successful': len(successful), 'failed': 5 - len(successful), 'denominator': 5},
                'credited_subset': credit,
                'published_average_raw': average,
                'published_average_seconds': average_seconds,
                'published_average_basis': 'source_reported_preserved_independently_not_recomputed_from_credit_subset',
            })
        _require(int(match[1]) == credited_successful, 'published credited successes conflict with course counts')
        parenthetical = None if match[2] is None else _time_token(match[2], 'published parenthetical time')
        team_summaries.append({
            'team_observation_id': f'{EVENT_ID}:{SOURCE_VERSION}:{TEAM_IDS[team]}',
            'team_id': TEAM_IDS[team], 'team_raw': team,
            'all_reported_attempts': {'successful': all_successful, 'failed': 15 - all_successful, 'denominator': 15},
            'credited_subset': {'successful': credited_successful, 'denominator': 9},
            'published_summary': published,
            'published_parenthetical_time_seconds': parenthetical,
            'published_parenthetical_time_basis': 'source_reported_tiebreak_time_not_recomputed',
        })
    canonical_document = dict(document, rows=ordered_rows,
                              published_team_summaries=[by_team[team] for team in sorted(by_team)])
    canonical_bytes = json.dumps(canonical_document, sort_keys=True, separators=(',', ':'),
                                ensure_ascii=True, allow_nan=False).encode('utf-8')
    return {
        'schema_version': SCHEMA_VERSION,
        'status': 'experimental_review_records_not_admitted',
        'canonical_import_enabled': False,
        'network_access_performed': False,
        'manuscript_bytes_acquired_by_reader': False,
        'event_count': 1,
        'event_id': EVENT_ID,
        'source': document['source'],
        'input_curated_json_sha256': hashlib.sha256(raw).hexdigest(),
        'normalized_curated_excerpt_sha256': hashlib.sha256(canonical_bytes).hexdigest(),
        'hash_scope': 'curated_JSON_only_not_HTML_PDF_or_full_manuscript',
        'attempt_count': len(attempts),
        'attempts': attempts,
        'course_summaries': course_summaries,
        'team_summaries': team_summaries,
        'interpretation': {
            'position_order': 'source_display_order_not_established_chronological',
            'version_policy': 'only_pinned_v1_accepted_new_versions_require_explicit_trial_reconciliation',
            'identity_scope': 'source_version_coordinates_not_native_run_ids_or_cross_version_trial_identity',
            'protocol_no_human_intervention': 'protocol_requirement_not_observed_intervention_measurement',
            'practice_reset_checkpoint_data': 'not_reported_in_table_remain_null',
            'success_denominators': 'all_five_reported_attempts_and_three_credited_slots_per_course_kept_separate',
            'failure_marker': 'X_is_failure_with_unknown_time_and_cause_not_missing_or_zero',
            'success_definition': 'source_reported_goal_reached_without_collision',
            'comparison_scope': 'one_physical_event_no_simulation_or_cross_year_pooling',
            'source_verification': 'structural_validation_does_not_verify_primary_source_truth_or_rights',
        },
    }


def read_table(path: str | Path) -> dict:
    """Bounded POSIX regular-file input with descriptor-relative no-symlink opens.

    URLs, stdin, device/FIFO/socket paths, parent traversal and symlink components
    are not accepted. Operating-system mounted filesystem locality is unknown.
    """
    try:
        path = os.fspath(path)
    except TypeError as exc:
        raise TableInputError('expected a bounded local regular-file path') from exc
    _require(type(path) is str and 0 < len(path) <= 4096 and '://' not in path and
             '\\' not in path and not any(ord(c) < 32 or ord(c) == 127 for c in path) and
             not path.startswith('//') and path != '-',
             'expected a bounded local regular-file path')
    try:
        _require(len(path.encode('utf-8')) <= 4096, 'local path byte limit exceeded')
    except UnicodeEncodeError as exc:
        raise TableInputError('path must be valid UTF-8') from exc
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
        return validate_table_bytes(raw)
    except (OSError, UnicodeError) as exc:
        raise TableInputError('cannot read supplied no-symlink local regular file') from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('table', help='supplied local manually curated Table II JSON')
    args = parser.parse_args(argv)
    try:
        result = read_table(args.table)
    except TableInputError as exc:
        parser.exit(2, f'error: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
