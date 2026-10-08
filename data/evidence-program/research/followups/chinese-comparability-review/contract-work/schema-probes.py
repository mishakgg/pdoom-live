#!/usr/bin/env python3
"""Review-authored, offline, wholly synthetic JSON Schema probes.

Read pinned schemas and fixture JSON as data only. Never import or execute pinned
validator/source code. No source access, model execution, adapter or ingestion.
SP identifiers are independent of the original ledger's 20 unexecuted AC cases.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource

ROOT = Path(__file__).resolve().parent
PINNED = ROOT / 'pinned'
CONTRACTS = PINNED / 'tools/evidence_program/contracts'
SCHEMAS = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(CONTRACTS.glob('*.schema.json'))]
BY_NAME = {s['$id'].rsplit('/', 1)[-1]: s for s in SCHEMAS}

def deny_retrieve(uri):
    raise NoSuchResource(ref=uri)

REGISTRY = Registry(retrieve=deny_retrieve).with_resources([(s['$id'], Resource.from_contents(s)) for s in SCHEMAS])
for schema in SCHEMAS:
    Draft202012Validator.check_schema(schema)

FORMAT = FormatChecker()

def validator(name):
    return Draft202012Validator(BY_NAME[name], registry=REGISTRY, format_checker=FORMAT)

def errors(name, value):
    return [{'instance_path': '/' + '/'.join(map(str, e.absolute_path)),
             'schema_path': '/' + '/'.join(map(str, e.absolute_schema_path)),
             'message': e.message}
            for e in sorted(validator(name).iter_errors(value), key=lambda x: str(list(x.absolute_path)))]

def ref(record_type, slug='probe'):
    return {'id': f'urn:pdataset:{record_type}:{slug}', 'revision': 1}

def unknown(reason='Not established in this wholly fictional fixture.'):
    return {'kind': 'unknown', 'reason': reason}

def envelope(record_type, data, slug='probe'):
    return {'schema_version': '0.1.0', 'record_type': record_type,
            'id': ref(record_type, slug)['id'], 'revision': 1, 'synthetic': True,
            'times': {'known_at': '2026-10-08T12:00:00Z', 'retrieved_at': '2026-10-08T12:00:00Z',
                      'published': {'kind': 'date', 'date': '2026-09-30'},
                      'event': unknown(), 'evaluated': unknown()},
            'governance': {'review_state': 'needs_review', 'rights_state': 'unknown',
                           'rights_basis': 'Wholly fictional diagnostic; rights claims below are not legal grants.',
                           'publication_state': 'internal'},
            'evidence': [] if record_type in ('source_artifact', 'snapshot') else [
                {'source_ref': ref('source_artifact'), 'locator': 'Fictional appendix A, table 1, row A',
                 'relation': 'supports', 'extraction_method': 'synthetic', 'extractor_version': 'local-schema-probes-v1'}],
            'data': data}

SOURCE = envelope('source_artifact', {'canonical_url': 'https://example.invalid/fictional/source-v1',
    'title': 'Wholly fictional schema-probe source', 'source_type': 'report', 'language': 'en',
    'author_refs': [], 'availability': 'unknown'})
ACTOR = envelope('actor', {'actor_kind': 'organization', 'name': 'Fictional Developer Lab',
    'name_language': 'en', 'aliases': [], 'jurisdictions': [], 'affiliations': [], 'external_ids': []})
MODEL = envelope('model_version', {'developer_refs': [ref('actor')], 'family': 'Fictional Model',
    'version_label': 'fictional-v1', 'modality': ['text'], 'access': 'unknown',
    'parent_model_refs': [], 'version_certainty': 'unknown'})
PROTOCOL = {'name': 'Fictional probe protocol', 'version': 'fictional-v1',
    'configuration': 'Fictional tasks; execution and judge settings not established.', 'reproducibility': 'partial'}
MEASUREMENT = {'metric': {'key': 'fictional-harmless-rate-v1', 'definition': '100 times harmless answers divided by completed answers in this fictional task.',
    'unit': 'percent', 'direction': 'higher_better', 'minimum': '0', 'maximum': '100'},
    'result': {'kind': 'point', 'value': '50.00', 'unit': 'percent'}, 'observation_mode': 'reported',
    'method': 'Wholly fictional schema illustration. No evaluation was performed.', 'sample_size': 80}
SAFETY = envelope('safety_evaluation', {'model_ref': ref('model_version'), 'evaluator_refs': [ref('actor')],
    'risk_domain': 'other', 'protocol': deepcopy(PROTOCOL), 'measurement': deepcopy(MEASUREMENT),
    'conclusion': 'No empirical conclusion: wholly fictional fixture.',
    'limitations': 'Synthetic only; no source correctness, exact model, judge, independence or pooling established.',
    'disclosure_level': 'summary_only'})
BENCH = envelope('benchmark_run', {'model_ref': ref('model_version'), 'evaluator_refs': [ref('actor')],
    'benchmark': {'name': 'Fictional benchmark', 'version': 'fictional-v1', 'split': 'unknown',
                  'task': 'Fictional test only', 'contamination_status': 'unknown'},
    'protocol': deepcopy(PROTOCOL), 'measurement': deepcopy(MEASUREMENT), 'independence': 'developer_reported'})

def canonical_hash(record):
    return sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

BASE_RECORDS = [SOURCE, ACTOR, MODEL, SAFETY, BENCH]
SNAPSHOT = envelope('snapshot', {'snapshot_kind': 'observed_ledger', 'cutoff': '2026-10-08T12:00:00Z',
    'created_at': '2026-10-08T12:00:00Z',
    'members': [{'record_ref': {'id': r['id'], 'revision': r['revision']}, 'sha256': canonical_hash(r)} for r in BASE_RECORDS],
    'canonicalization': 'python-json-sort-utf8-v1', 'notice': 'Wholly fictional closed ledger; no claim of comparability, independence or rights clearance.'})

def bundle(records):
    return {'schema_version': '0.1.0', 'dataset_id': 'wholly-fictional-local-schema-probes',
            'dataset_kind': 'synthetic', 'generated_at': '2026-10-08T12:00:00Z', 'records': records}

PROBES = []
def add(number, title, candidate, expected, semantic, limitation, static_validator, schema=None, relevant_assertions=None):
    name = schema or (candidate['record_type'] + '.schema.json' if 'record_type' in candidate else 'dataset.schema.json')
    PROBES.append({'probe_id': f'SP{number:02}', 'title': title, 'schema': name, 'input': candidate,
        'expected_schema_acceptance': expected, 'semantic_disposition': semantic,
        'semantic_disposition_basis': 'Review-authored explanation; not an executed semantic acceptance test.',
        'limitation_demonstrated': limitation,
        'companion_validator_static_inspection': static_validator,
        'related_source_assertions_for_context_only': relevant_assertions or [],
        'executes_original_acceptance_case': False})

add(1, 'Positive shape control across the six relevant native record types', bundle(deepcopy(BASE_RECORDS + [SNAPSHOT])), True,
    'synthetic_shape_control_only', 'Shape success is not evidence adjudication.',
    'Not executed. Full validator result is deliberately not claimed.')
c = deepcopy(SAFETY); c['data']['measurement']['result']['value'] = '51.37'
add(2, 'Numerator/denominator consistency is not checked by schema', c, True, 'hold_denominator_semantics',
    'Fictional denominator 80 and 51.37 percent cannot arise from an integer harmless count rounded to two decimal places; schema has no count-rounding relation.',
    'Static inspection: numeric ranges are checked, but no metric-specific integer numerator/denominator rounding test is implemented (validate_dataset.py:150-214).', 'safety_evaluation.schema.json', ['F003', 'F005', 'F006', 'F007'])
c = deepcopy(BENCH); c['data']['measurement']['sample_size'] = 40; c['data']['measurement']['metric']['definition'] = 'Forty scheduled question pairs incorrectly treated as forty completed judged answers.'
add(3, 'Scheduled question pairs can be mislabeled as completed-answer denominators', c, True, 'reject_unit_substitution',
    'sample_size is an integer, with no structured sample unit or completion/exclusion accounting.',
    'Static inspection: no question/pair/turn/answer population consistency check.', relevant_assertions=['ZHS006-A1','ZHS006-A2','ZHS006-A5'])
c = deepcopy(SAFETY); c['times']['evaluated'] = deepcopy(c['times']['published']); c['data']['protocol']['reproducibility'] = 'full'
add(4, 'Publication date substituted for evaluation date remains valid shape', c, True, 'reject_date_role_substitution',
    'A syntactically valid date has no machine-verifiable provenance for its semantic role.',
    'Static inspection: full reproducibility only rejects evaluated.kind=unknown; it does not authenticate date-role provenance (215-218).', relevant_assertions=['ZHS006-A10','LS-A14'])
c = deepcopy(SAFETY); c['data']['protocol']['reproducibility'] = 'full'
add(5, 'Unknown evaluation time plus full reproducibility: schema versus companion check', c, True, 'reject_full_reproducibility_claim',
    'Schema accepts this combination; companion validator has an explicit additional check.',
    'Static inspection predicts evaluation_time at lines 215-218; not executed.')
c = deepcopy(SAFETY); c['data']['protocol']['configuration'] = 'Automated scoring; judge identity, checkpoint, rubric and instruction unknown.'
add(6, 'Undocumented judge passes required protocol string shape', c, True, 'hold_judge_binding',
    'Neither safety_evaluation nor benchmark_run has a judge-model reference or rubric/run binding.',
    'Static inspection: no judge identity, checkpoint, prompt, rating-scale-crosswalk or validation-transfer rule.', relevant_assertions=['F010','ZHS006-A3','ZHS006-A4','LS-A07','LS-A08'])
c = deepcopy(BENCH); c['data']['independence'] = 'third_party'
add(7, 'Developer equals evaluator while independence says third_party', bundle(deepcopy([SOURCE, ACTOR, MODEL]) + [c]), True,
    'reject_unsupported_independence', 'The same exact actor reference is both developer and evaluator; enum membership does not prove relationship.',
    'Static inspection: reference types are checked, but developer/evaluator overlap is not reconciled with independence.', relevant_assertions=['F009','ZHS006-A6'])
c = deepcopy(SAFETY); c['data']['independence'] = 'unknown'
add(8, 'Adding benchmark independence to safety_evaluation is rejected', c, False, 'reject_invented_native_field',
    'independence exists only in benchmark_run_data, not safety_evaluation_data.', 'Schema rejection occurs before companion traversal.')
c1 = deepcopy(BENCH); c2 = deepcopy(BENCH); c2['id'] = ref('benchmark_run','different-regime')['id']; c2['data']['benchmark']['version'] = 'fictional-v2'; c2['data']['benchmark']['task'] = 'Different population and domain'; c2['data']['measurement']['result']['value'] = '62.00'; c2['data']['measurement']['metric']['definition'] = 'A differently normalized tournament score on a changed cohort.'; c2['data']['measurement']['metric']['unit'] = 'score'; c2['data']['measurement']['result']['unit'] = 'score'
add(9, 'Changed releases and units coexist without a comparability gate', bundle(deepcopy([SOURCE,ACTOR,MODEL])+[c1,c2]), True,
    'reject_common_trend_without_bridge', 'Native envelope can retain both records, but has no typed comparability decision/bridge object. Acceptance of coexistence does not authorize pooling.',
    'Static inspection: checks per-record units/ranges, not cross-record benchmark equivalence.', relevant_assertions=['F012','LS-A15'])
c = deepcopy(SAFETY); c['governance']['publication_state'] = 'eligible'
add(10, 'Eligible with unresolved review/rights is schema-valid but validator-gated', c, True,
    'reject_publication_eligibility', 'Required strings/enums do not implement the publication prerequisite.',
    'Static inspection predicts publication_gate at lines 127-129; not executed.')
c = deepcopy(SAFETY); c['governance']['rights_state'] = 'redistribution_allowed'; c['governance']['rights_basis'] = 'Fictional incorrect assertion that a software license automatically licenses all result data.'
add(11, 'A legally unsupported rights-inheritance story is an accepted string', c, True, 'reject_rights_inheritance',
    'rights_basis and rights_url cannot verify artifact-specific license applicability. This fixture creates no rights.',
    'Static inspection: coarse review/export prerequisites exist; legal scope and veracity are not checked.', relevant_assertions=['F013','LS-A11','LS-A13'])
c = deepcopy(SNAPSHOT); c['data']['notice'] = 'Invalid fictional claim: all members now form a comparable independent trend.'
add(12, 'Snapshot shape cannot certify a comparable independent trend', c, True, 'reject_snapshot_as_semantic_approval',
    'A closed hash manifest represents selection at a cutoff, not comparability, truth, independent replication or publishability.',
    'Static inspection: closure/hash/cutoff checks exist at lines 306-331; scientific comparability is not checked.')
c = deepcopy(SAFETY); c['data']['measurement']['result']['value'] = 50.0
add(13, 'Empirical decimal JSON number is rejected', c, False, 'reject_wrong_numeric_representation',
    'Native empirical numeric values must be exact base-10 strings.', 'Schema rejection occurs before companion traversal.')
c = deepcopy(SAFETY); c['data']['measurement']['metric']['unit'] = 'pairwise_battle'; c['data']['measurement']['result']['unit'] = 'pairwise_battle'
add(14, 'Source-native population label is not an allowed unit enum', c, False, 'retain_native_unit_in_context_not_new_enum',
    'The enum supplies count/score/percent etc.; pairwise_battle must remain explicit metric/context text or review sidecar, not be inserted as a native unit.', 'Schema rejection occurs before companion traversal.')
c = deepcopy(SAFETY); c['data']['protocol']['judge_ref'] = ref('model_version')
add(15, 'Invented structured judge_ref is rejected', c, False, 'reject_invented_native_field',
    'protocol.additionalProperties=false; actual schema has no judge_ref.', 'Schema rejection occurs before companion traversal.')
c = deepcopy(MODEL); c['data']['version_label'] = 'Fictional Mutable Product'; c['data']['version_certainty'] = 'immutable'
add(16, 'Immutable identity claim needs no hash at schema level', c, True, 'hold_checkpoint_identity',
    'provider_model_id and artifact_digest are optional; an immutable label can be asserted without binding evidence.',
    'Static inspection: no digest-or-provider-id prerequisite for version_certainty=immutable.', relevant_assertions=['F008','F012','LS-A05'])
c = deepcopy(SAFETY); c['times']['evaluated'] = {'kind': 'date', 'date': '2026-02-30'}
add(17, 'Impossible date rejected with FormatChecker', c, False, 'reject_invalid_calendar_date',
    'Unlike incorrect date roles, impossible dates fail syntax/format validation.', 'Schema rejection occurs before companion traversal.')
c = deepcopy(SOURCE)
add(18, 'Wrong standalone wrapper rejected', c, False, 'reject_wrong_record_type',
    'Standalone wrappers bind record_type while referring to the shared record schema.', 'Schema rejection occurs before companion traversal.', schema='safety_evaluation.schema.json')
c = deepcopy(SAFETY); c['data']['measurement']['result']['unit'] = 'score'
add(19, 'Metric/result unit mismatch separates schema from companion check', c, True, 'reject_metric_result_unit_mismatch',
    'Both units are legal enum members but disagree.', 'Static inspection predicts metric_unit at lines 198-205; not executed.')
c = deepcopy(SNAPSHOT); c['data']['members'][0]['sha256'] = '0'*64
add(20, 'Syntactically valid wrong snapshot digest accepted by schema', c, True, 'reject_unverified_manifest',
    'The schema checks 64 hexadecimal characters, not canonical record hashing or closure.',
    'Static inspection predicts snapshot_hash for the corresponding complete bundle at lines 318-319; not executed.')

results = []
for probe in PROBES:
    es = errors(probe['schema'], probe['input'])
    results.append({k: v for k, v in probe.items() if k != 'input'} | {
        'schema_accepted': not es, 'expected_schema_outcome_matched': (not es) == probe['expected_schema_acceptance'],
        'errors': es, 'input_sha256': canonical_hash(probe['input']),
        'upstream_validator_executed': False, 'semantic_acceptance_executed': False})
wrapper_results = [{'record_type': r['record_type'], 'schema_accepted': not errors(r['record_type']+'.schema.json', r)} for r in BASE_RECORDS+[SNAPSHOT]]
original_fixture = json.loads((PINNED/'tools/evidence_program/examples/synthetic_dataset.json').read_text())
fixture_errors = errors('dataset.schema.json', original_fixture)
metadata = {'format': 'review_only_synthetic_schema_probes', 'version': '1.0',
    'repository_commit': '246f746e3a267363c7f6d2e0494eb72fb4c98bc9',
    'schemas_loaded_as_data': len(SCHEMAS), 'jsonschema_version': version('jsonschema'),
    'offline_registry_only': True, 'upstream_code_executed': False,
    'network_access': False, 'adapter_implemented': False, 'operational_admission': False,
    'original_acceptance_cases_executed': False,
    'notice': 'Twenty SP probes of fictional schema shapes are NOT the twenty original AC acceptance cases. Semantic dispositions are review explanations, not executed acceptance checks. No upstream validator or source code was executed; no research question is settled by schema success.'}
(ROOT/'schema-probes.json').write_text(json.dumps(metadata | {'probes': PROBES}, ensure_ascii=False, indent=2)+'\n')
report = metadata | {'run_at': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
    'probe_count': len(results), 'schema_accepted_count': sum(r['schema_accepted'] for r in results),
    'schema_rejected_count': sum(not r['schema_accepted'] for r in results),
    'all_expected_schema_outcomes_matched': all(r['expected_schema_outcome_matched'] for r in results),
    'six_type_baseline_wrapper_results': wrapper_results,
    'pinned_original_fixture_json_shape_check': {'record_count': len(original_fixture['records']), 'schema_accepted': not fixture_errors,
        'errors': fixture_errors, 'upstream_validator_executed': False}, 'results': results}
(ROOT/'schema-probe-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k: report[k] for k in ['probe_count','schema_accepted_count','schema_rejected_count','all_expected_schema_outcomes_matched']}))
raise SystemExit(0 if report['all_expected_schema_outcomes_matched'] and all(x['schema_accepted'] for x in wrapper_results) and not fixture_errors else 1)
