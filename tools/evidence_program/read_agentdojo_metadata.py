#!/usr/bin/env python3
"""Bounded, offline AgentDojo metadata decoder. No network, task or source execution.

V0 supports banking tasks 0–2 in two named pipelines, with metadata-only output.
The public fixture is synthetic. Runtime-null historical attacked flags are kept
uninterpreted: an archive source revision does not attest the runtime predicate.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json
import re

MAX_BYTES = 262144
MAX_NODES = 20000
MAX_DEPTH = 24
MAX_MESSAGES = 100
MAX_TOOL_CALLS = 300
PIPELINES = {'gpt-4o-2024-05-13', 'gpt-4o-2024-05-13-tool_filter'}
RAW_FIELDS = {'suite_name', 'pipeline_name', 'user_task_id', 'injection_task_id',
              'attack_type', 'injections', 'messages', 'error', 'utility', 'security', 'duration'}
MANIFEST_FIELDS = {'source_kind', 'archive_commit', 'source_path', 'sha256',
                   'git_blob_sha', 'retrieved_at', 'previous_sha256', 'semantics'}
SYNTHETIC_PREDICATE = 'synthetic_target_goal_predicate'
UNKNOWN_PREDICATE = 'unknown_historical_runtime'
ATTACK_TYPES = {None, 'none', 'dos', 'important_instructions'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def _object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'Duplicate JSON key')
        out[key] = value
    return out


def _invalid_constant(_):
    raise ValueError('Nonfinite JSON constant')


def _bounded_json(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'Input byte bound')
    try:
        root = json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                          parse_float=Decimal, parse_constant=_invalid_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError('Invalid bounded JSON') from exc
    stack, nodes = [(root, 0)], 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        require(nodes <= MAX_NODES and depth <= MAX_DEPTH, 'Input complexity bound')
        if isinstance(value, dict):
            require(all(type(k) is str and len(k) <= 128 for k in value), 'Object key bound')
            stack.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, list):
            stack.extend((v, depth + 1) for v in value)
        elif isinstance(value, str):
            require(len(value) <= 65536, 'String bound')
        elif isinstance(value, Decimal):
            require(value.is_finite() and abs(value.adjusted()) <= 1000, 'Decimal bound')
        elif type(value) is int:
            require(abs(value) < 10**100, 'Integer bound')
    return root


def _utc(value):
    require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value),
            'retrieved_at requires UTC seconds')
    try:
        datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as exc:
        raise ValueError('Invalid retrieved_at') from exc


def interpret_security(*, injection_task_id, attack_type, error_present, publisher_security,
                       applicable_target_predicate=False):
    """Never equate publisher security=True with safety.

    applicable_target_predicate is an explicit caller precondition, not inferred
    from message roles, archive version, or attack labels. V0 normalizer supplies
    it only for a self-authored synthetic fixture. DoS remains separate.
    """
    require(type(publisher_security) is bool and type(error_present) is bool
            and type(applicable_target_predicate) is bool, 'Outcome boolean type')
    if injection_task_id is None:
        return {'status': 'not_applicable_clean', 'attacker_goal_success': None}
    if error_present:
        return {'status': 'error_flag_not_observed_outcome', 'attacker_goal_success': None}
    if attack_type in {'dos', 'denial_of_service'}:
        return {'status': 'dos_nonutility_predicate_not_target_goal', 'attacker_goal_success': None}
    if not applicable_target_predicate:
        return {'status': 'unverified_historical_predicate', 'attacker_goal_success': None}
    return {'status': 'verified_target_goal_predicate', 'attacker_goal_success': publisher_security}


def normalize_run(raw: bytes, manifest: dict):
    """Decode a caller-supplied bounded artifact. Never retrieves paths or URLs.

    A manifest is a caller-supplied integrity assertion, not proof of rights or
    source authenticity. No raw message, tool argument, injection or error text
    is returned. Unknown historical runtime/cost/budget/help fields stay null.
    """
    require(type(manifest) is dict and set(manifest) == MANIFEST_FIELDS, 'Manifest schema')
    require(type(manifest['source_kind']) is str and manifest['source_kind'] in {'synthetic', 'agentdojo_archive'}, 'Source kind')
    require(type(manifest['archive_commit']) is str and re.fullmatch(r'[0-9a-f]{40}', manifest['archive_commit']), 'Archive commit')
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'Input byte bound')
    require(manifest['sha256'] == digest(raw) and manifest['git_blob_sha'] == git_blob(raw), 'Source hash mismatch')
    previous = manifest['previous_sha256']
    require(previous is None or (type(previous) is str and re.fullmatch(r'[0-9a-f]{64}', previous)), 'Previous hash')
    require(previous != manifest['sha256'], 'Identical bytes are not a new version')
    _utc(manifest['retrieved_at'])
    require(type(manifest['semantics']) is str and manifest['semantics'] in {UNKNOWN_PREDICATE, SYNTHETIC_PREDICATE}, 'Semantics scope')
    require(manifest['source_kind'] == 'synthetic' or manifest['semantics'] == UNKNOWN_PREDICATE,
            'Archive revision cannot certify historical runtime semantics')
    row = _bounded_json(raw)
    require(type(row) is dict and set(row) == RAW_FIELDS, 'TaskResults schema')
    require(type(row['pipeline_name']) is str and row['pipeline_name'] in PIPELINES and row['suite_name'] == 'banking'
            and type(row['user_task_id']) is str and row['user_task_id'] in {'user_task_0', 'user_task_1', 'user_task_2'}, 'Pilot condition bound')
    injection = row['injection_task_id']
    require(injection is None or (type(injection) is str and re.fullmatch(r'injection_task_\d{1,2}', injection)), 'Injection identifier')
    require(row['attack_type'] is None or type(row['attack_type']) is str, 'Attack type')
    allowed_attacks = ATTACK_TYPES | ({'synthetic_target'} if manifest['source_kind'] == 'synthetic' else set())
    require(row['attack_type'] in allowed_attacks, 'Attack type outside audited pilot allowlist')
    require(type(row['injections']) is dict and all(type(v) is str for v in row['injections'].values()), 'Injection payload shape')
    if injection is None:
        require(row['attack_type'] in {None, 'none'} and not row['injections'], 'Inconsistent clean condition')
    else:
        require(row['attack_type'] not in {None, 'none'}, 'Missing attack condition')
    require(type(row['utility']) is bool and type(row['security']) is bool, 'Outcome flag types')
    require(row['error'] is None or type(row['error']) is str, 'Error shape')
    duration = row['duration']
    require(type(duration) in {int, Decimal} and Decimal(duration).is_finite()
            and 0 <= duration <= 86400, 'Duration bound/type')
    messages = row['messages']
    require(type(messages) is list and len(messages) <= MAX_MESSAGES, 'Message count bound')
    tool_calls = 0
    for message in messages:
        require(type(message) is dict and type(message.get('role')) is str and message.get('role') in {'system', 'user', 'assistant', 'tool'}, 'Message role')
        allowed = {'system': {'role', 'content'}, 'user': {'role', 'content'},
                   'assistant': {'role', 'content', 'tool_calls'},
                   'tool': {'role', 'content', 'tool_call', 'tool_call_id', 'error'}}
        require(set(message) <= allowed[message['role']], 'Message schema')
        if 'tool_call_id' in message:
            require(message['tool_call_id'] is None or type(message['tool_call_id']) is str, 'Tool call ID shape')
        if 'content' in message:
            require(message['content'] is None or type(message['content']) in {str, list}, 'Message content shape')
        calls = message.get('tool_calls')
        require(calls is None or type(calls) is list, 'Tool-call list shape')
        if calls is not None:
            require(all(type(c) is dict for c in calls), 'Tool-call entry shape')
        for call in (calls or []) + ([message['tool_call']] if message.get('tool_call') is not None else []):
            require(type(call) is dict and set(call) == {'function', 'args', 'id'}, 'Tool-call schema')
            require(type(call['function']) is str and type(call['args']) is dict
                    and (call['id'] is None or type(call['id']) is str), 'Tool-call field types')
        if 'error' in message:
            require(message['error'] is None or type(message['error']) is str, 'Tool error shape')
        if message['role'] == 'assistant' and calls is not None:
            tool_calls += len(calls)
        require(tool_calls <= MAX_TOOL_CALLS, 'Assistant tool-call bound')
    attack_path = row['attack_type'] or 'none'
    path = '/'.join(['runs', row['pipeline_name'], row['suite_name'], row['user_task_id'],
                     injection or 'none', attack_path + '.json'])
    require(manifest['source_path'] == path, 'Source path/condition mismatch')
    stable_key = manifest['source_kind'] + ':' + path
    version_id = digest((stable_key + ':' + manifest['sha256']).encode())
    outcome = interpret_security(injection_task_id=injection, attack_type=row['attack_type'],
        error_present=row['error'] is not None, publisher_security=row['security'],
        applicable_target_predicate=manifest['semantics'] == SYNTHETIC_PREDICATE)
    return {
        'schema_version': 'agentdojo-metadata/0.1.0',
        'evidence_type': 'synthetic_evaluation_fixture' if manifest['source_kind'] == 'synthetic' else 'evaluation_observation_not_admitted',
        'source_key': stable_key, 'observation_version_id': version_id,
        'previous_sha256': previous,
        'source_url': None if manifest['source_kind'] == 'synthetic' else
            'https://github.com/ethz-spylab/agentdojo/blob/' + manifest['archive_commit'] + '/' + path,
        'archive_commit': manifest['archive_commit'], 'git_blob_sha': manifest['git_blob_sha'],
        'source_sha256': manifest['sha256'], 'retrieved_at': manifest['retrieved_at'],
        'pipeline_id': row['pipeline_name'], 'suite_id': row['suite_name'],
        'user_task_id': row['user_task_id'], 'injection_task_id': injection,
        'attack_type': row['attack_type'], 'publisher_utility': row['utility'],
        'publisher_security': row['security'], 'error_present': row['error'] is not None,
        'utility_observation_status': 'error_flag_not_observed_outcome' if row['error'] is not None else 'publisher_reported',
        'security_interpretation': outcome,
        'duration_seconds': str(duration), 'duration_meaning': 'publisher_elapsed_wall_clock',
        'assistant_origin_tool_calls': tool_calls,
        'historical_runtime_version': None, 'evaluation_timestamp': None,
        'actual_inference_cost': None, 'token_cap': None, 'spending_cap': None,
        'human_intervention': None, 'human_baseline_seconds': None,
        'unknown_reason': 'not_recorded_in_supported_task_results',
        'rights_scope': 'self_authored_synthetic' if manifest['source_kind'] == 'synthetic' else 'metadata_only_full_trace_rights_unresolved',
        'payload_exported': False, 'operational_admission': 'not_admitted',
    }
