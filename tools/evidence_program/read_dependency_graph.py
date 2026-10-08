#!/usr/bin/env python3
"""Review one fixed deps.dev dependency-graph fixture, entirely offline.

This is a bounded JSON structure reader, not a collector, package resolver,
installation detector, concentration metric, or canonical dataset adapter.
Only byte-identical copies of the reviewed fixture are public inputs. Source
strings and URLs are inert data. The original UTF-8 JSON is retained unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys

MAX_BYTES = 64 * 1024
MAX_DEPTH = 32
MAX_WORK_UNITS = 8192
MAX_SCALAR_BYTES = 16 * 1024
MAX_NUMBER_CHARS = 128
MAX_NODES = 128
MAX_EDGES = 512
MAX_PATH_COMPONENTS = 64
SOURCE_URL = 'https://api.deps.dev/v3/systems/pypi/packages/transformers/versions/4.45.2:dependencies'
FIXTURE_SHA256 = '9d11eaee99763097abb9bdc995fb03ad6e38d961c2110e711204ddd8cca32583'
FIXTURE_BYTE_COUNT = 3532
FIXTURE_RETRIEVED_AT_UTC = '2026-10-08T01:04:58.216305Z'
ROOT_VERSION_KEY = {'system': 'PYPI', 'name': 'transformers', 'version': '4.45.2'}


class ReviewInputError(ValueError):
    """Input is outside this deliberately narrow review boundary."""


def _preflight(text: str) -> None:
    """Bound nesting and lexical work before the JSON decoder allocates a tree.

    Work units count containers, strings (including keys), and non-string
    primitive tokens. This scan is not a replacement JSON syntax validator.
    Its total character work is independently bounded by MAX_BYTES.
    """
    depth = work = 0
    quoted = escaped = primitive = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
            primitive = False
            work += 1
        elif char in '[{':
            depth += 1
            work += 1
            primitive = False
            if depth > MAX_DEPTH:
                raise ReviewInputError('JSON nesting limit exceeded')
        elif char in ']}':
            depth -= 1
            primitive = False
            if depth < 0:
                raise ReviewInputError('invalid JSON syntax')
        elif char in ':, \t\r\n':
            primitive = False
        elif not primitive:
            primitive = True
            work += 1
        if work > MAX_WORK_UNITS:
            raise ReviewInputError('JSON work limit exceeded')
    if quoted or depth:
        raise ReviewInputError('invalid JSON syntax')


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReviewInputError('duplicate JSON object key')
        result[key] = value
    return result


def _number(token: str, *, integer: bool):
    if len(token) > MAX_NUMBER_CHARS:
        raise ReviewInputError('JSON number length limit exceeded')
    value = int(token) if integer else float(token)
    if not integer and not math.isfinite(value):
        raise ReviewInputError('nonfinite JSON numbers are not allowed')
    return value


def _invalid_constant(_token: str):
    raise ReviewInputError('nonfinite JSON constants are not allowed')


def _check_scalars(document: object) -> None:
    # Preflight has bounded both tree depth and cardinality. Preserve unknown
    # fields, but reject invalid Unicode and excessive decoded scalar sizes.
    pending = [document]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str):
            try:
                size = len(value.encode('utf-8'))
            except UnicodeEncodeError as exc:
                raise ReviewInputError('invalid JSON Unicode scalar') from exc
            if size > MAX_SCALAR_BYTES:
                raise ReviewInputError('JSON scalar limit exceeded')


def _required(mapping: dict, key: str, expected: type, label: str):
    if key not in mapping or type(mapping[key]) is not expected:
        raise ReviewInputError(f'{label}.{key} must be {expected.__name__}')
    return mapping[key]


def _parse_document(raw: bytes) -> dict:
    """Validate a small JSON graph's structure without interpreting its truth.

    Private test entry point; not an alternate admission/import route. Unknown
    fields and unknown string enum values are retained in insertion order.
    All documented fields are required by this narrow local review profile.
    Graph cycles, duplicate edges, errors and inconsistent relation labels are
    not repaired or interpreted. Standard JSON scalar types are retained; the
    public result also retains original bytes as UTF-8 text for exact spelling.
    """
    if type(raw) is not bytes:
        raise ReviewInputError('input must be bytes')
    if len(raw) > MAX_BYTES:
        raise ReviewInputError('input exceeds 64 KiB')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ReviewInputError('input must be UTF-8') from exc
    _preflight(text)
    try:
        document = json.loads(
            text, object_pairs_hook=_unique_object,
            parse_int=lambda token: _number(token, integer=True),
            parse_float=lambda token: _number(token, integer=False),
            parse_constant=_invalid_constant,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ReviewInputError('invalid JSON syntax') from exc
    _check_scalars(document)
    if type(document) is not dict:
        raise ReviewInputError('graph must be a JSON object')
    nodes = _required(document, 'nodes', list, 'graph')
    edges = _required(document, 'edges', list, 'graph')
    _required(document, 'error', str, 'graph')
    if len(nodes) > MAX_NODES:
        raise ReviewInputError('graph node limit exceeded')
    if len(edges) > MAX_EDGES:
        raise ReviewInputError('graph edge limit exceeded')
    for index, node in enumerate(nodes):
        label = f'nodes[{index}]'
        if type(node) is not dict:
            raise ReviewInputError(f'{label} must be dict')
        version = _required(node, 'versionKey', dict, label)
        for key in ('system', 'name', 'version'):
            _required(version, key, str, f'{label}.versionKey')
        _required(node, 'bundled', bool, label)
        _required(node, 'relation', str, label)
        errors = _required(node, 'errors', list, label)
        if any(type(error) is not str for error in errors):
            raise ReviewInputError(f'{label}.errors entries must be str')
    for index, edge in enumerate(edges):
        label = f'edges[{index}]'
        if type(edge) is not dict:
            raise ReviewInputError(f'{label} must be dict')
        for key in ('fromNode', 'toNode'):
            value = _required(edge, key, int, label)  # bool is deliberately not int
            if not 0 <= value < len(nodes):
                raise ReviewInputError(f'{label}.{key} index out of bounds')
        _required(edge, 'requirement', str, label)
    return document


def _read_local_bytes(path: str | Path) -> bytes:
    """Open a bounded regular file without following any symlink components.

    POSIX descriptor-relative traversal prevents a check/open race. It is
    deliberately fail-closed on systems without the necessary flags. There is
    no stdin, URI, device, UNC, parent-traversal or network-fetch input route.
    The operating system's mount locality cannot be established by this reader.
    """
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
    components = [part for part in path.split('/') if part not in ('', '.')]
    if '..' in components:
        raise ReviewInputError('parent-traversal path components are not accepted')
    if not components or len(components) > MAX_PATH_COMPONENTS:
        raise ReviewInputError('local path component limit exceeded')
    if os.name != 'posix' or not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise ReviewInputError('safe no-symlink regular-file opening is unavailable')
    directory = descriptor = None
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory = os.open('/' if path.startswith('/') else '.', directory_flags)
        for component in components[:-1]:
            child = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(components[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | getattr(os, 'O_NOCTTY', 0), dir_fd=directory)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ReviewInputError('only supplied local regular files are accepted')
        if info.st_size > MAX_BYTES:
            raise ReviewInputError('input exceeds 64 KiB')
        parts = []
        size = 0
        while size <= MAX_BYTES:
            part = os.read(descriptor, MAX_BYTES + 1 - size)
            if not part:
                break
            parts.append(part)
            size += len(part)
        if size > MAX_BYTES:
            raise ReviewInputError('input exceeds 64 KiB')
        return b''.join(parts)
    except OSError as exc:
        raise ReviewInputError('cannot read supplied no-symlink local regular file') from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)



def _artifact_local_references(graph: dict, sha256: str) -> dict:
    """Name source positions in an already bounded graph, without merging nodes."""
    graph_id = f'depsdev-review:sha256:{sha256}'
    return {
        'graph_id': graph_id,
        'identity_scope': 'artifact_local_review_references_not_canonical_identifiers',
        'independent_observations_claimed': False,
        'cross_snapshot_entity_matching_performed': False,
        'nodes': [{
            'node_id': f'{graph_id}:node:{index}',
            'source_node_index': index,
        } for index in range(len(graph['nodes']))],
        'edges': [{
            'edge_id': f'{graph_id}:edge:{index}',
            'source_edge_index': index,
            'from_node_id': f"{graph_id}:node:{edge['fromNode']}",
            'to_node_id': f"{graph_id}:node:{edge['toNode']}",
        } for index, edge in enumerate(graph['edges'])],
    }


def read_pinned_graph(path: str | Path) -> dict:
    """Review only a supplied regular-file copy of the fixed acquired graph."""
    raw = _read_local_bytes(path)
    if len(raw) != FIXTURE_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ReviewInputError('supplied file does not match the fixed fixture SHA-256 and size')
    graph = _parse_document(raw)
    # Fixed evidence invariants, not a general graph-analysis/resolution engine.
    if (len(graph['nodes']) != 18 or len(graph['edges']) != 23
            or graph['nodes'][0]['versionKey'] != ROOT_VERSION_KEY
            or graph['nodes'][0]['relation'] != 'SELF'
            or graph['nodes'][6]['versionKey'] != {'system': 'PYPI', 'name': 'huggingface-hub', 'version': '0.36.2'}
            or graph['nodes'][6]['relation'] != 'DIRECT'
            or graph['edges'][1] != {'fromNode': 0, 'toNode': 6, 'requirement': '<1.0,>=0.23.2'}):
        raise ReviewInputError('fixed fixture does not match the reviewed graph identity')
    return {
        'record_kind': 'experimental_dependency_graph_review',
        'status': 'experimental_review_records_not_admitted',
        'review_state': 'needs_review',
        'canonical_schema_claimed': False,
        'source_admission_enabled': False,
        'production_import_enabled': False,
        'network_access_performed': False,
        'network_access_flag_scope': 'reader-issued network requests only; OS filesystem mount locality is not established',
        'links_followed': False,
        'provenance': {
            'source_url': SOURCE_URL,
            'source_root_version_key': ROOT_VERSION_KEY.copy(),
            'sha256': FIXTURE_SHA256,
            'byte_count': len(raw),
            'fixture_retrieved_at_utc': FIXTURE_RETRIEVED_AT_UTC,
            'fixture_retrieval_time_role': 'original_fixture_acquisition_not_reader_execution_or_package_publication_time',
            'package_publication_time': None,
            'graph_resolution_time': None,
            'extraction_method': 'bounded_offline_json_graph_structure_v1',
        },
        'data_rights': {
            'license_identifier': 'CC-BY-4.0',
            'license_url': 'https://creativecommons.org/licenses/by/4.0/',
            'attribution': 'Open Source Insights (deps.dev), Google',
            'license_evidence_url': 'https://docs.deps.dev/api/v3/#data',
            'scope': 'deps.dev-generated dependency graph data in this supplied fixture',
            'fixture_modified': False,
            'permissions_inherited_by_packages_or_linked_works': False,
        },
        'original_json': raw.decode('utf-8'),
        'graph_document': graph,
        'artifact_local_references': _artifact_local_references(graph, FIXTURE_SHA256),
        'structural_counts': {'nodes': len(graph['nodes']), 'edges': len(graph['edges'])},
        'reviewed_edge': {
            'source_edge_index': 1,
            'from_node_index': 0,
            'to_node_index': 6,
            'raw_requirement': graph['edges'][1]['requirement'],
            'target_relation_as_reported': graph['nodes'][6]['relation'],
        },
        'limits': [
            'one fixed acquired fixture only; no operational collection or admission',
            'structure validation is not evidence that the graph is correct; graph and node errors remain intact',
            'source node, edge and object-member order is preserved; no graph repair or requirement normalization',
            'deps.dev resolution is an approximation for a clean generic 64-bit Linux environment',
            'no actual installation, deployed service use, ownership, market share or concentration inference',
            'no historical release-time dependency-resolution inference from this later snapshot',
            'DIRECT may also be reached indirectly; it is the source label rather than an exclusive path classification',
            'no reader-issued network requests; arbitrary OS-mounted filesystems are not provably local',
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph', help='local JSON matching the fixed graph fixture')
    args = parser.parse_args(argv)
    try:
        result = read_pinned_graph(args.graph)
    except ReviewInputError as exc:
        parser.exit(2, f'error: {exc}\n')
    # Do not sort source object members or node/edge arrays.
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
