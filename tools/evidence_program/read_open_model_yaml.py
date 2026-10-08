#!/usr/bin/env python3
"""Experimental, offline review of exactly two pinned OSAI annotation revisions.

This is not a collector, a canonical dataset adapter, or an access/license verdict.
Only the two byte-identical local fixtures are accepted by the public entry point.
PyYAML is used for bounded syntax events, never object construction. Untagged
non-null scalars remain strings (including numbers, booleans and dates); original
UTF-8 YAML is also retained so comments and scalar spelling remain auditable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import NamedTuple

import yaml
from yaml import events

MAX_BYTES = 64 * 1024
MAX_EVENTS = 4096
MAX_DEPTH = 32
MAX_SCALAR_BYTES = 16 * 1024
REPOSITORY = 'https://github.com/Language-Technology-Assessment/main-database'
SOURCE_PATH = 'llama-3.3.yaml'
FIXTURE_RETRIEVED_AT_UTC = '2026-10-08T00:20:44Z'
ANNOTATION_ATTRIBUTION = (
    'Liesenfeld, A. and Dingemanse, M., 2024. Rethinking open source generative AI: '
    'open-washing and the EU AI Act. In Proceedings of the 2024 ACM Conference '
    'on Fairness, Accountability, and Transparency (pp. 1774-1787).'
)


class ReviewInputError(ValueError):
    """An input is outside this deliberately narrow, offline review boundary."""


class RevisionPin(NamedTuple):
    commit: str
    git_blob: str
    sha256: str
    byte_count: int
    commit_time: str


BEFORE = RevisionPin(
    'e39b4edd41811e975f9262d77ee286796d7792e5',
    'ce4e77557ac41d97ec59d872a2d6b7f19229ecdb',
    '89d1f517d5171d832c59359e83d6c7b7577aaf0c14f8a06c08b01adbbcdfcc17',
    3648, '2026-03-12T13:10:33Z',
)
AFTER = RevisionPin(
    'ff85b6ff442035e41c9492cefa54f78be0b827fc',
    '855671b61e19ccdefa95879c0d85a4c5eb77dc5f',
    'cc93e48df6a72c3e15d05ae2a056fcf775d4ccf7c590bc26c13ebbdb9fea6ec8',
    3398, '2026-03-13T14:41:47Z',
)


def _parse_document(raw: bytes) -> dict:
    """Parse bounded review syntax; internal entry point for adversarial tests.

    Not an alternate public import path. No schema is asserted for unknown
    fields. Nulls are retained; all other scalar values retain their text.
    """
    if len(raw) > MAX_BYTES:
        raise ReviewInputError('input exceeds 64 KiB')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ReviewInputError('input must be UTF-8') from exc
    # PyYAML ignores unknown directives; this profile deliberately rejects all.
    if any(line.startswith('%') for line in text.lstrip('\ufeff').splitlines()):
        raise ReviewInputError('YAML directives are not allowed')
    parser = yaml.parse(text, Loader=yaml.BaseLoader)
    event_count = 0

    def next_event():
        nonlocal event_count
        event_count += 1
        if event_count > MAX_EVENTS:
            raise ReviewInputError('YAML event limit exceeded')
        event = next(parser)
        if isinstance(event, events.AliasEvent) or getattr(event, 'anchor', None) is not None:
            raise ReviewInputError('YAML anchors and aliases are not allowed')
        if getattr(event, 'tag', None) is not None:
            raise ReviewInputError('explicit YAML tags are not allowed')
        if isinstance(event, events.DocumentStartEvent) and (event.version or event.tags):
            raise ReviewInputError('YAML directives are not allowed')
        if isinstance(event, events.ScalarEvent) and len(event.value.encode('utf-8')) > MAX_SCALAR_BYTES:
            raise ReviewInputError('YAML scalar limit exceeded')
        return event

    def scalar(event):
        if event.style is None and event.value in ('', '~', 'null', 'Null', 'NULL'):
            return None
        return event.value

    def node(event, depth):
        if depth > MAX_DEPTH:
            raise ReviewInputError('YAML nesting limit exceeded')
        if isinstance(event, events.ScalarEvent):
            return scalar(event)
        if isinstance(event, events.SequenceStartEvent):
            result = []
            event = next_event()
            while not isinstance(event, events.SequenceEndEvent):
                result.append(node(event, depth + 1))
                event = next_event()
            return result
        if isinstance(event, events.MappingStartEvent):
            result = {}
            event = next_event()
            while not isinstance(event, events.MappingEndEvent):
                if not isinstance(event, events.ScalarEvent) or scalar(event) is None:
                    raise ReviewInputError('mapping keys must be non-null scalar strings')
                key = event.value
                if key == '<<':
                    raise ReviewInputError('YAML merge keys are not allowed')
                if key in result:
                    raise ReviewInputError('duplicate YAML mapping key')
                result[key] = node(next_event(), depth + 1)
                event = next_event()
            return result
        raise ReviewInputError('unsupported YAML structure')

    try:
        if not isinstance(next_event(), events.StreamStartEvent):
            raise ReviewInputError('expected YAML stream')
        if not isinstance(next_event(), events.DocumentStartEvent):
            raise ReviewInputError('expected one YAML document')
        document = node(next_event(), 1)
        if not isinstance(next_event(), events.DocumentEndEvent):
            raise ReviewInputError('expected YAML document end')
        if not isinstance(next_event(), events.StreamEndEvent):
            raise ReviewInputError('exactly one YAML document is allowed')
        if not isinstance(document, dict) or not document:
            raise ReviewInputError('document must be a nonempty mapping')
        return document
    except UnicodeError as exc:
        raise ReviewInputError('invalid YAML Unicode scalar') from exc
    except (yaml.YAMLError, StopIteration, RecursionError) as exc:
        raise ReviewInputError('invalid YAML syntax') from exc
    finally:
        parser.close()


def _read_local_bytes(path: str | Path) -> bytes:
    path = os.fspath(path)
    if not isinstance(path, str) or '://' in path or path == '-':
        raise ReviewInputError('only supplied local regular files are accepted')
    # Reject UNC/device paths before opening, including mixed slash spelling.
    # A drive path or POSIX path can still refer to an OS-mounted network
    # filesystem; this reader cannot prove the locality of arbitrary mounts.
    if path.startswith('\\') or path.replace('\\', '/').startswith('//'):
        raise ReviewInputError('UNC, device and network path prefixes are not accepted')
    # Nonblocking open prevents hanging on a FIFO. fstat checks the opened
    # descriptor, not a raceable earlier path lookup. Read size stays bounded
    # even if the file grows after the size check. Symlinks are rejected where
    # O_NOFOLLOW is available; their targets must still be regular files elsewhere.
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ReviewInputError('only supplied local regular files are accepted')
            if info.st_size > MAX_BYTES:
                raise ReviewInputError('input exceeds 64 KiB')
            raw = source.read(MAX_BYTES + 1)
    except (OSError, ValueError) as exc:
        if isinstance(exc, ReviewInputError):
            raise
        raise ReviewInputError('cannot read supplied local regular file') from exc
    if len(raw) > MAX_BYTES:
        raise ReviewInputError('input exceeds 64 KiB')
    return raw


def _read_revision(path: str | Path, pin: RevisionPin) -> dict:
    raw = _read_local_bytes(path)
    if len(raw) != pin.byte_count or hashlib.sha256(raw).hexdigest() != pin.sha256:
        raise ReviewInputError('supplied file does not match the fixed revision SHA-256 and size')
    git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    if git_blob != pin.git_blob:
        raise ReviewInputError('supplied file does not match the fixed Git blob')
    document = _parse_document(raw)
    if not isinstance(document.get('system'), dict) or not isinstance(document.get('org'), dict):
        raise ReviewInputError('pinned document is missing system or org mapping')
    release = document['system'].get('releasedate')
    criterion_keys = sorted(set(document) - {'system', 'org'})
    # This fingerprints this observed key set, not an official schema version.
    fingerprint = hashlib.sha256(
        json.dumps(criterion_keys, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    criterion_records = [{
        'record_id': f'osai-experimental:{pin.sha256}:{key}',
        'record_kind': 'experimental_open_model_criterion_review',
        'review_state': 'needs_review',
        'revision_sha256': pin.sha256,
        'criterion': key,
        'presence': 'present',
        'source_fields': document[key],
        'criteria_set_fingerprint_sha256': fingerprint,
    } for key in criterion_keys]
    return {
        'record_kind': 'experimental_open_model_annotation_revision',
        'review_state': 'needs_review',
        'provenance': {
            'source_url': f'{REPOSITORY}/blob/{pin.commit}/{SOURCE_PATH}',
            'source_path': SOURCE_PATH,
            'git_commit': pin.commit,
            'git_blob': pin.git_blob,
            'sha256': pin.sha256,
            'byte_count': len(raw),
            'commit_time': pin.commit_time,
            'commit_time_role': 'repository_revision_time_not_assessment_or_release_time',
            'assessment_time': None,
            'fixture_retrieved_at_utc': FIXTURE_RETRIEVED_AT_UTC,
            'fixture_retrieval_time_role': 'original_fixture_acquisition_not_reader_execution_or_assessment_time',
            'fixture_retrieval_method': 'GitHub connector fetch_file; exact base64-decoded bytes',
            'extraction_method': 'bounded_yaml_events_text_scalars_v1',
        },
        'original_yaml': raw.decode('utf-8'),
        'field_document': document,
        'criterion_keys': criterion_keys,
        'criterion_records': criterion_records,
        'criteria_set_fingerprint_sha256': fingerprint,
        'criteria_set_fingerprint_method': 'SHA-256 of sorted criterion-key compact UTF-8 JSON array; derived, not an official schema version',
        'release_date': {
            'raw': release,
            'precision': 'month' if isinstance(release, str) and re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', release) else 'uninterpreted',
        },
        'annotation_rights': {
            'license_identifier': 'CC-BY-4.0',
            'license_url': 'https://creativecommons.org/licenses/by/4.0/',
            'scope': 'the supplied annotation data only',
            'evidence': 'unchanged license and attribution header in original_yaml',
            'attribution_site': 'https://osai-index.eu/',
            'attribution_paper': ANNOTATION_ATTRIBUTION,
            'index_files_doi': 'https://doi.org/10.5281/zenodo.15386042',
            'permissions_inherited_by_model_weights_or_linked_works': False,
        },
        'model_license_text': document['system'].get('endmodellicense'),
    }


def read_pinned_pair(before_path: str | Path, after_path: str | Path) -> dict:
    """Review two local files matching the fixed before/after pins, in that order."""
    before = _read_revision(before_path, BEFORE)
    after = _read_revision(after_path, AFTER)
    old = before['field_document']
    new = after['field_document']
    old_keys = set(before['criterion_keys'])
    new_keys = set(after['criterion_keys'])
    added, removed = sorted(new_keys - old_keys), sorted(old_keys - new_keys)
    changed = sorted(key for key in old_keys & new_keys if old[key] != new[key])
    identity_changed = any(old[key] != new[key] for key in ('system', 'org'))
    # These are fixture invariants, not a generic event classifier. Changes to
    # the pins or claimed meaning require a separate reviewed implementation.
    if (len(old_keys), len(new_keys), added, removed, changed, identity_changed) != (
        14, 12, [], ['api', 'package'], [], False,
    ):
        raise ReviewInputError('pinned pair does not have the reviewed criteria-set-only change')
    return {
        'record_kind': 'experimental_open_model_two_revision_review',
        'status': 'experimental_review_records_not_admitted',
        'canonical_schema_claimed': False,
        'source_admission_enabled': False,
        'production_import_enabled': False,
        'network_access_performed': False,
        'network_access_flag_scope': 'reader-issued network requests only; OS filesystem mount locality is not established',
        'links_followed': False,
        'model_execution_performed': False,
        'annotation_assessments_are_external': True,
        'scalar_policy': 'preserve all non-null scalars as text; preserve YAML nulls; retain exact original_yaml',
        'revisions': [before, after],
        'revision_relation': 'before_is_immediate_parent_of_after',
        'criteria_set_changes': [{
            'record_kind': 'experimental_criteria_set_change',
            'before_commit': BEFORE.commit,
            'after_commit': AFTER.commit,
            'before_count': len(old_keys),
            'after_count': len(new_keys),
            'added': added,
            'removed': removed,
            'removed_field_documents': {key: old[key] for key in removed},
            'before_criteria_set_fingerprint_sha256': before['criteria_set_fingerprint_sha256'],
            'after_criteria_set_fingerprint_sha256': after['criteria_set_fingerprint_sha256'],
            'removed_criteria': [{
                'criterion': key,
                'before_presence': 'present',
                'after_presence': 'absent_from_schema',
                'before_source_fields': old[key],
                'after_source_fields': None,
            } for key in removed],
            'interpretation': 'annotation criterion removal; no model access or license change inferred',
        }],
        'criterion_alignment': {key: {
            'before_presence': 'present' if key in old_keys else 'absent_from_schema',
            'after_presence': 'present' if key in new_keys else 'absent_from_schema',
            'before_source_fields': old.get(key),
            'after_source_fields': new.get(key),
        } for key in sorted(old_keys | new_keys)},
        'surviving_criterion_value_changes': changed,
        'identity_changed': identity_changed,
        'inferred_model_access_or_license_changes': [],
        'limits': [
            'two acquired and vendored test fixtures only; no operational collection or admission',
            'no reader-issued network requests; arbitrary OS-mounted filesystems are not provably local',
            'source annotations are not independently verified model properties',
            'criterion removal is not evidence of a model access or license transition',
            'annotation license does not license model weights or linked works',
            'no diffusion, adoption, download, derivative or user-count inference',
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', help='local YAML matching the fixed before revision')
    parser.add_argument('after', help='local YAML matching the fixed after revision')
    args = parser.parse_args(argv)
    try:
        result = read_pinned_pair(args.before, args.after)
    except ReviewInputError as exc:
        parser.exit(2, f'error: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
