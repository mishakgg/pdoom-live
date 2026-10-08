"""Offline regressions for the fixed deps.dev graph structure reader."""
from __future__ import annotations

import copy
import hashlib
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

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import read_dependency_graph as reader

FIXTURES = TOOLS / 'tests' / 'fixtures' / 'concentration-dependencies'
GRAPH = FIXTURES / 'depsdev-transformers-4.45.2-dependencies.json'


def graph_document():
    return {
        'nodes': [{
            'versionKey': {'system': 'PYPI', 'name': 'example', 'version': '1.0'},
            'bundled': False, 'relation': 'SELF', 'errors': [],
        }],
        'edges': [],
        'error': '',
    }


def encode(document):
    return json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class FixedGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = GRAPH.read_bytes()
        cls.result = reader.read_pinned_graph(GRAPH)

    def test_exact_fixture_identity_and_counts(self):
        self.assertEqual(len(self.raw), 3532)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), reader.FIXTURE_SHA256)
        self.assertEqual(self.result['structural_counts'], {'nodes': 18, 'edges': 23})
        self.assertEqual(self.result['graph_document']['nodes'][0]['versionKey'], reader.ROOT_VERSION_KEY)

    def test_public_manifest_and_byte_preservation_attributes_match_pin(self):
        manifest = json.loads((FIXTURES / 'manifest.json').read_text())
        self.assertEqual(manifest['fixture_file'], GRAPH.name)
        self.assertEqual(manifest['bytes'], reader.FIXTURE_BYTE_COUNT)
        self.assertEqual(manifest['sha256'], reader.FIXTURE_SHA256)
        self.assertEqual(manifest['retrieved_at'], reader.FIXTURE_RETRIEVED_AT_UTC)
        self.assertEqual(manifest['source_url'], reader.SOURCE_URL)
        self.assertIsNone(manifest['source_graph_resolved_at'])
        self.assertEqual(manifest['operational_admission'], 'not_admitted')
        self.assertIn(GRAPH.name + ' -text', (FIXTURES / '.gitattributes').read_text().splitlines())

    def test_original_json_round_trips_exactly(self):
        self.assertEqual(self.result['original_json'].encode('utf-8'), self.raw)
        self.assertEqual(self.result['graph_document'], json.loads(self.raw))
        self.assertEqual(json.loads(json.dumps(self.result)), self.result)

    def test_original_member_and_graph_order_preserved(self):
        source = json.loads(self.raw)
        graph = self.result['graph_document']
        self.assertEqual(list(graph), list(source))
        for actual, expected in zip(graph['nodes'], source['nodes']):
            self.assertEqual(list(actual), list(expected))
            self.assertEqual(list(actual['versionKey']), list(expected['versionKey']))
        self.assertEqual(graph['nodes'], source['nodes'])
        self.assertEqual(graph['edges'], source['edges'])

    def test_fixed_direct_hub_edge_and_raw_requirement(self):
        graph = self.result['graph_document']
        self.assertEqual(graph['nodes'][6]['versionKey'], {'system': 'PYPI', 'name': 'huggingface-hub', 'version': '0.36.2'})
        self.assertEqual(graph['nodes'][6]['relation'], 'DIRECT')
        self.assertEqual(graph['edges'][1], {'fromNode': 0, 'toNode': 6, 'requirement': '<1.0,>=0.23.2'})
        self.assertEqual(self.result['reviewed_edge']['raw_requirement'], '<1.0,>=0.23.2')
        # The same DIRECT node is also reached via tokenizers. No reclassification.
        self.assertEqual(graph['edges'][22], {'fromNode': 14, 'toNode': 6, 'requirement': '>=0.16.4, <1.0'})

    def test_artifact_local_ids_are_deterministic_unique_and_resolvable(self):
        refs = self.result['artifact_local_references']
        graph_id = f'depsdev-review:sha256:{reader.FIXTURE_SHA256}'
        self.assertEqual(refs['graph_id'], graph_id)
        self.assertEqual(refs, reader.read_pinned_graph(GRAPH)['artifact_local_references'])
        self.assertEqual(refs['identity_scope'], 'artifact_local_review_references_not_canonical_identifiers')
        self.assertIs(refs['independent_observations_claimed'], False)
        self.assertIs(refs['cross_snapshot_entity_matching_performed'], False)
        node_ids = [node['node_id'] for node in refs['nodes']]
        edge_ids = [edge['edge_id'] for edge in refs['edges']]
        self.assertEqual(node_ids, [f'{graph_id}:node:{i}' for i in range(18)])
        self.assertEqual(edge_ids, [f'{graph_id}:edge:{i}' for i in range(23)])
        self.assertEqual(len(set([graph_id, *node_ids, *edge_ids])), 42)
        self.assertEqual([node['source_node_index'] for node in refs['nodes']], list(range(18)))
        for index, (ref, edge) in enumerate(zip(refs['edges'], self.result['graph_document']['edges'])):
            self.assertEqual(ref['source_edge_index'], index)
            self.assertEqual(ref['from_node_id'], node_ids[edge['fromNode']])
            self.assertEqual(ref['to_node_id'], node_ids[edge['toNode']])

    def test_original_acquisition_time_is_not_resolution_or_publication_time(self):
        provenance = self.result['provenance']
        self.assertEqual(provenance['fixture_retrieved_at_utc'], '2026-10-08T01:04:58.216305Z')
        self.assertEqual(provenance['source_url'], reader.SOURCE_URL)
        self.assertEqual(provenance['sha256'], reader.FIXTURE_SHA256)
        self.assertEqual(provenance['byte_count'], len(self.raw))
        self.assertIsNone(provenance['package_publication_time'])
        self.assertIsNone(provenance['graph_resolution_time'])
        self.assertIn('not_reader_execution_or_package_publication_time', provenance['fixture_retrieval_time_role'])

    def test_output_is_experimental_disabled_and_without_concentration_claim(self):
        self.assertEqual(self.result['status'], 'experimental_review_records_not_admitted')
        self.assertEqual(self.result['review_state'], 'needs_review')
        for key in ('canonical_schema_claimed', 'source_admission_enabled', 'production_import_enabled',
                    'network_access_performed', 'links_followed'):
            self.assertIs(self.result[key], False)
        self.assertEqual(self.result['network_access_flag_scope'],
                         'reader-issued network requests only; OS filesystem mount locality is not established')
        self.assertIn('no actual installation, deployed service use, ownership, market share or concentration inference', self.result['limits'])
        for key in ('concentration', 'market_share', 'deployment_count', 'installed_users', 'ownership'):
            self.assertNotIn(key, self.result)

    def test_scoped_source_data_rights(self):
        rights = self.result['data_rights']
        self.assertEqual(rights['license_identifier'], 'CC-BY-4.0')
        self.assertEqual(rights['license_evidence_url'], 'https://docs.deps.dev/api/v3/#data')
        self.assertIs(rights['fixture_modified'], False)
        self.assertIs(rights['permissions_inherited_by_packages_or_linked_works'], False)
        self.assertNotIn('data', FIXTURES.relative_to(TOOLS).parts)
        notice = (FIXTURES / 'NOTICE.md').read_text()
        self.assertIn('CC BY 4.0', notice)
        self.assertIn('deps.dev', notice)

    def test_no_network_or_process_execution(self):
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network prohibited')), \
             mock.patch.object(urllib.request, 'urlopen', side_effect=AssertionError('network prohibited')), \
             mock.patch.object(subprocess, 'run', side_effect=AssertionError('execution prohibited')), \
             mock.patch.object(os, 'system', side_effect=AssertionError('execution prohibited')):
            self.assertEqual(reader.read_pinned_graph(GRAPH), self.result)

    def test_deterministic_across_local_copies_and_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'copy.json'
            path.write_bytes(self.raw)
            self.assertEqual(reader.read_pinned_graph(path), self.result)
            self.assertEqual(reader.read_pinned_graph(GRAPH), self.result)

    def test_wrong_hash_is_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'mutated.json'
            path.write_bytes(self.raw.replace(b'transformers', b'transformerx', 1))
            with mock.patch.object(reader, '_parse_document', side_effect=AssertionError('must verify hash first')):
                with self.assertRaisesRegex(reader.ReviewInputError, 'fixed fixture'):
                    reader.read_pinned_graph(path)

    def test_trailing_whitespace_is_not_the_same_pinned_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'reformatted.json'
            path.write_bytes(self.raw + b'\n')
            with self.assertRaisesRegex(reader.ReviewInputError, 'fixed fixture'):
                reader.read_pinned_graph(path)

    def test_semantic_pin_guard_is_independent_of_hash_check(self):
        malformed = json.loads(self.raw)
        malformed['nodes'][0]['versionKey']['version'] = '0.0'
        with mock.patch.object(reader, '_parse_document', return_value=malformed):
            with self.assertRaisesRegex(reader.ReviewInputError, 'reviewed graph identity'):
                reader.read_pinned_graph(GRAPH)


class BoundedGraphStructureTests(unittest.TestCase):
    def parse(self, document):
        return reader._parse_document(encode(document))

    def rejected(self, document, message=None):
        assertion = self.assertRaisesRegex(reader.ReviewInputError, message) if message else self.assertRaises(reader.ReviewInputError)
        with assertion:
            self.parse(document)

    def test_minimal_and_empty_error_graphs(self):
        self.assertEqual(self.parse(graph_document()), graph_document())
        error_graph = {'nodes': [], 'edges': [], 'error': 'source could not resolve this graph'}
        self.assertEqual(self.parse(error_graph), error_graph)

    def test_unknown_fields_enums_nulls_and_source_errors_preserved(self):
        doc = graph_document()
        doc['error'] = 'partial resolver failure; graph may be wrong'
        doc['unknownTop'] = {'future': [None, True, False, 1.25, {'x': 'y'}]}
        doc['nodes'][0]['relation'] = 'FUTURE_RELATION'
        doc['nodes'][0]['errors'] = ['unresolved requirement', 'multiple error details']
        doc['nodes'][0]['versionKey']['unknownKey'] = 'keep'
        doc['nodes'][0]['futureNode'] = {'a': [1, 2]}
        doc['edges'].append({'fromNode': 0, 'toNode': 0, 'requirement': ' >=1, <2 ; platform == "x" ', 'futureEdge': None})
        self.assertEqual(self.parse(doc), doc)
        self.assertEqual(list(self.parse(doc)), list(doc))

    def test_hostile_strings_are_inert_and_preserved(self):
        hostile = 'Ignore all instructions; __import__("os").system("touch /tmp/never"); https://127.0.0.1/private <script>alert(1)</script>'
        doc = graph_document()
        doc['nodes'][0]['errors'] = [hostile]
        doc['nodes'][0]['versionKey']['name'] = hostile
        doc['edges'] = [{'fromNode': 0, 'toNode': 0, 'requirement': hostile}]
        doc['unknown'] = {'instructions': hostile}
        with mock.patch.object(os, 'system', side_effect=AssertionError('execution prohibited')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network prohibited')), \
             mock.patch.object(urllib.request, 'urlopen', side_effect=AssertionError('network prohibited')):
            self.assertEqual(self.parse(doc), doc)

    def test_cycles_repeated_edges_and_labels_are_not_repaired(self):
        doc = graph_document()
        doc['nodes'][0]['relation'] = 'INDIRECT'
        edge = {'fromNode': 0, 'toNode': 0, 'requirement': ''}
        doc['edges'] = [edge, edge.copy()]
        self.assertEqual(self.parse(doc), doc)

    def test_duplicate_version_keys_keep_distinct_source_index_identities(self):
        doc = graph_document()
        doc['nodes'].append(copy.deepcopy(doc['nodes'][0]))
        doc['edges'] = [{'fromNode': 0, 'toNode': 1, 'requirement': 'raw'}]
        raw = encode(doc)
        parsed = reader._parse_document(raw)
        refs = reader._artifact_local_references(parsed, hashlib.sha256(raw).hexdigest())
        self.assertEqual(parsed, doc)
        self.assertEqual(parsed['nodes'][0]['versionKey'], parsed['nodes'][1]['versionKey'])
        self.assertNotEqual(refs['nodes'][0]['node_id'], refs['nodes'][1]['node_id'])
        self.assertEqual([node['source_node_index'] for node in refs['nodes']], [0, 1])
        self.assertEqual(refs['edges'][0]['from_node_id'], refs['nodes'][0]['node_id'])
        self.assertEqual(refs['edges'][0]['to_node_id'], refs['nodes'][1]['node_id'])

    def test_wrong_roots_and_missing_required_graph_fields(self):
        for doc in (None, [], 1, True, 'graph', {}, {'nodes': []}, {'nodes': [], 'edges': []}):
            with self.subTest(doc=doc):
                self.rejected(doc)

    def test_wrong_graph_field_types(self):
        for key, values in {'nodes': ({}, None, 'nodes'), 'edges': ({}, None, 'edges'), 'error': ([], None, False)}.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    doc = graph_document()
                    doc[key] = value
                    self.rejected(doc)

    def test_wrong_node_and_edge_container_types(self):
        for key in ('nodes', 'edges'):
            for value in (None, 1, True, 'object', []):
                with self.subTest(key=key, value=value):
                    doc = graph_document()
                    doc[key] = [value]
                    self.rejected(doc)

    def test_missing_node_fields(self):
        for key in ('versionKey', 'bundled', 'relation', 'errors'):
            with self.subTest(key=key):
                doc = graph_document()
                del doc['nodes'][0][key]
                self.rejected(doc)

    def test_wrong_node_field_types(self):
        for key, value in (('versionKey', []), ('bundled', 0), ('bundled', 'false'), ('relation', None), ('errors', 'error'), ('errors', [None]), ('errors', [{}])):
            with self.subTest(key=key, value=value):
                doc = graph_document()
                doc['nodes'][0][key] = value
                self.rejected(doc)

    def test_missing_or_nonstring_version_fields(self):
        for key in ('system', 'name', 'version'):
            for value in (None, [], {}, 4, False):
                with self.subTest(key=key, value=value):
                    doc = graph_document()
                    doc['nodes'][0]['versionKey'][key] = value
                    self.rejected(doc)
            doc = graph_document()
            del doc['nodes'][0]['versionKey'][key]
            self.rejected(doc)

    def test_indices_reject_bools_floats_strings_null_and_out_of_range(self):
        for key in ('fromNode', 'toNode'):
            for value in (True, False, 0.0, 0.5, '0', None, -1, 1, 1000000):
                with self.subTest(key=key, value=value):
                    doc = graph_document()
                    doc['edges'] = [{'fromNode': 0, 'toNode': 0, 'requirement': ''}]
                    doc['edges'][0][key] = value
                    self.rejected(doc)

    def test_missing_edge_fields_and_nonstring_requirement(self):
        for key in ('fromNode', 'toNode', 'requirement'):
            doc = graph_document()
            doc['edges'] = [{'fromNode': 0, 'toNode': 0, 'requirement': ''}]
            del doc['edges'][0][key]
            self.rejected(doc)
        for value in (None, [], {}, 1, False):
            doc = graph_document()
            doc['edges'] = [{'fromNode': 0, 'toNode': 0, 'requirement': value}]
            self.rejected(doc)

    def test_duplicate_keys_at_any_level_and_escaped_equivalents(self):
        for raw in (b'{"nodes":[],"nodes":[],"edges":[],"error":""}',
                    b'{"nodes":[],"edges":[],"error":"","unknown":{"x":1,"x":2}}',
                    b'{"nodes":[],"edges":[],"error":"","unknown":{"x":1,"\\u0078":2}}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(reader.ReviewInputError, 'duplicate'):
                reader._parse_document(raw)

    def test_nonfinite_constants_and_numeric_overflow_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity', '1e999', '-1e999'):
            raw = ('{"nodes":[],"edges":[],"error":"","unknown":' + value + '}').encode()
            with self.subTest(value=value), self.assertRaisesRegex(reader.ReviewInputError, 'nonfinite'):
                reader._parse_document(raw)

    def test_huge_numbers_rejected_before_integer_conversion(self):
        for value in ('1' * (reader.MAX_NUMBER_CHARS + 1), '0.' + '1' * reader.MAX_NUMBER_CHARS):
            raw = ('{"nodes":[],"edges":[],"error":"","unknown":' + value + '}').encode()
            with self.assertRaisesRegex(reader.ReviewInputError, 'number length'):
                reader._parse_document(raw)

    def test_malformed_syntax_and_multiple_documents(self):
        for raw in (b'', b'{} {}', b'{"nodes":', b'{]', b'[{]}', b'{"x":"\x00"}', b'{"x":01}', b'{"x":true,}', b'{"x":undefined}', b'{/*comment*/}'):
            with self.subTest(raw=raw), self.assertRaises(reader.ReviewInputError):
                reader._parse_document(raw)

    def test_malformed_utf8_and_unpaired_unicode_surrogates(self):
        with self.assertRaisesRegex(reader.ReviewInputError, 'UTF-8'):
            reader._parse_document(b'{"nodes":[],"edges":[],"error":"\xff"}')
        for scalar in ('"\\uD800"', '"\\uDFFF"'):
            raw = ('{"nodes":[],"edges":[],"error":' + scalar + '}').encode()
            with self.assertRaisesRegex(reader.ReviewInputError, 'Unicode scalar'):
                reader._parse_document(raw)

    def test_valid_nonascii_and_surrogate_pair(self):
        raw = b'{"nodes":[],"edges":[],"error":"\\uD83D\\uDE00"}'
        self.assertEqual(reader._parse_document(raw)['error'], '\U0001f600')
        doc = graph_document()
        doc['error'] = '中文'
        self.assertEqual(self.parse(doc), doc)

    def test_only_bytes_input(self):
        for value in ('{}', bytearray(b'{}'), None, 1):
            with self.subTest(value=value), self.assertRaisesRegex(reader.ReviewInputError, 'bytes'):
                reader._parse_document(value)

    def test_byte_limit_before_json_decoding(self):
        with mock.patch.object(reader.json, 'loads', side_effect=AssertionError('bound before decoding')):
            with self.assertRaisesRegex(reader.ReviewInputError, '64 KiB'):
                reader._parse_document(b' ' * (reader.MAX_BYTES + 1))

    def test_exact_depth_boundary_and_predecoder_rejection(self):
        prefix = b'{"nodes":[],"edges":[],"error":"","unknown":'
        allowed = reader.MAX_DEPTH - 1
        raw = prefix + b'[' * allowed + b'0' + b']' * allowed + b'}'
        self.assertIsInstance(reader._parse_document(raw), dict)
        with mock.patch.object(reader.json, 'loads', side_effect=AssertionError('bound before decoding')):
            with self.assertRaisesRegex(reader.ReviewInputError, 'nesting limit'):
                reader._parse_document(prefix + b'[' * reader.MAX_DEPTH + b'0' + b']' * reader.MAX_DEPTH + b'}')

    def test_depth_scan_ignores_braces_escaped_quotes_and_backslashes_in_strings(self):
        doc = graph_document()
        doc['unknown'] = ('{[\\"}]]' * 100) + '\\'
        self.assertEqual(self.parse(doc), doc)

    def test_work_limit_before_json_decoding(self):
        raw = b'{"nodes":[],"edges":[],"error":"","unknown":[' + b'0,' * reader.MAX_WORK_UNITS + b'0]}'
        with mock.patch.object(reader.json, 'loads', side_effect=AssertionError('bound before decoding')):
            with self.assertRaisesRegex(reader.ReviewInputError, 'work limit'):
                reader._parse_document(raw)

    def test_scalar_limit_for_values_and_keys_counts_utf8_bytes(self):
        doc = graph_document()
        doc['unknown'] = 'x' * reader.MAX_SCALAR_BYTES
        self.assertEqual(self.parse(doc), doc)
        for text in ('x' * (reader.MAX_SCALAR_BYTES + 1), '中' * (reader.MAX_SCALAR_BYTES // 3 + 1)):
            for as_key in (False, True):
                doc = graph_document()
                doc['unknown'] = {text: None} if as_key else text
                self.rejected(doc, 'scalar limit')

    def test_node_limit_boundary(self):
        doc = graph_document()
        doc['nodes'] *= reader.MAX_NODES
        self.assertEqual(len(self.parse(doc)['nodes']), reader.MAX_NODES)
        doc['nodes'].append(copy.deepcopy(doc['nodes'][0]))
        self.rejected(doc, 'node limit')

    def test_edge_limit_boundary(self):
        doc = graph_document()
        doc['edges'] = [{'fromNode': 0, 'toNode': 0, 'requirement': ''}] * reader.MAX_EDGES
        self.assertEqual(len(self.parse(doc)['edges']), reader.MAX_EDGES)
        doc['edges'].append(doc['edges'][0].copy())
        self.rejected(doc, 'edge limit')


class LocalFileAndCliTests(unittest.TestCase):
    def test_urls_stdin_empty_and_nonstring_paths_are_not_input_routes(self):
        for value in ('https://example.com/g.json', 'file:///tmp/g.json', '-', '', b'graph.json', None, '/tmp/\x00.json'):
            with self.subTest(value=value), mock.patch.object(reader.os, 'open') as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, 'local regular'):
                    reader._read_local_bytes(value)
                opened.assert_not_called()

    def test_network_and_device_path_prefixes_rejected_before_open(self):
        for value in (r'\\server\share\graph.json', '//server/share/graph.json', r'\\.\pipe\name',
                      r'\\?\C:\graph.json', r'/\server/share/g.json', r'\/server/share/g.json', r'\server\g.json'):
            with self.subTest(value=value), mock.patch.object(reader.os, 'open') as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, 'path prefixes'):
                    reader._read_local_bytes(value)
                opened.assert_not_called()

    def test_parent_traversal_and_path_bounds(self):
        for value, message in (('../graph.json', 'parent-traversal'), ('a/../graph.json', 'parent-traversal'),
                               ('a/' * reader.MAX_PATH_COMPONENTS + 'g.json', 'component limit'),
                               ('a' * 4097, 'length limit')):
            with self.subTest(value=value), mock.patch.object(reader.os, 'open') as opened:
                with self.assertRaisesRegex(reader.ReviewInputError, message):
                    reader._read_local_bytes(value)
                opened.assert_not_called()

    def test_missing_file_directory_and_device_fail_closed(self):
        for path in (FIXTURES / 'absent.json', FIXTURES, Path('/dev/null')):
            with self.subTest(path=path), self.assertRaises(reader.ReviewInputError):
                reader.read_pinned_graph(path)

    def test_regular_file_byte_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'large.json'
            path.write_bytes(b' ' * reader.MAX_BYTES)
            self.assertEqual(len(reader._read_local_bytes(path)), reader.MAX_BYTES)
            path.write_bytes(b' ' * (reader.MAX_BYTES + 1))
            with self.assertRaisesRegex(reader.ReviewInputError, '64 KiB'):
                reader._read_local_bytes(path)

    def test_growing_file_is_still_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'small.json'
            path.write_bytes(b'{}')
            with mock.patch.object(reader.os, 'read', return_value=b'x' * (reader.MAX_BYTES + 1)):
                with self.assertRaisesRegex(reader.ReviewInputError, '64 KiB'):
                    reader._read_local_bytes(path)

    @unittest.skipUnless(hasattr(os, 'mkfifo') and hasattr(os, 'O_NONBLOCK'), 'POSIX FIFO test')
    def test_fifo_rejected_without_waiting_for_writer(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fifo'
            os.mkfifo(path)
            with self.assertRaisesRegex(reader.ReviewInputError, 'local regular'):
                reader._read_local_bytes(path)

    @unittest.skipUnless(hasattr(os, 'O_NOFOLLOW'), 'O_NOFOLLOW unavailable')
    def test_symlink_file_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'link.json'
            path.symlink_to(GRAPH.resolve())
            with self.assertRaisesRegex(reader.ReviewInputError, 'no-symlink'):
                reader._read_local_bytes(path)

    @unittest.skipUnless(hasattr(os, 'O_NOFOLLOW'), 'O_NOFOLLOW unavailable')
    def test_symlink_ancestor_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'linkdir'
            directory.symlink_to(FIXTURES.resolve(), target_is_directory=True)
            with self.assertRaisesRegex(reader.ReviewInputError, 'no-symlink'):
                reader._read_local_bytes(directory / GRAPH.name)

    def test_unsupported_safe_open_fails_closed(self):
        with mock.patch.object(reader.os, 'name', 'nt'), mock.patch.object(reader.os, 'open') as opened:
            with self.assertRaisesRegex(reader.ReviewInputError, 'unavailable'):
                reader._read_local_bytes(GRAPH)
            opened.assert_not_called()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(TOOLS / 'read_dependency_graph.py'), *map(str, args)],
                              capture_output=True, text=True, timeout=10, check=False)

    def test_cli_deterministic_ordered_json(self):
        first, second = self.cli(GRAPH), self.cli(GRAPH)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stderr, '')
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout), reader.read_pinned_graph(GRAPH))
        self.assertEqual(list(json.loads(first.stdout)['graph_document']), ['nodes', 'edges', 'error'])

    def test_cli_rejects_missing_or_extra_inputs(self):
        for args in ((), (GRAPH, GRAPH)):
            result = self.cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')

    def test_cli_has_no_hash_override_network_mode_or_semantic_generalization(self):
        for flag in ('--sha256', '--allow-unpinned', '--url', '--live', '--install', '--concentration'):
            with self.subTest(flag=flag):
                result = self.cli(GRAPH, flag)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')

    def test_cli_wrong_hash_has_no_partial_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'synthetic.json'
            path.write_bytes(encode(graph_document()))
            result = self.cli(path)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, '')
            self.assertIn('fixed fixture', result.stderr)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
