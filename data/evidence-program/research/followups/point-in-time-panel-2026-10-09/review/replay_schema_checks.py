#!/usr/bin/env python3
"""Reviewer-authored, offline-only checks. Uploaded JSON is parsed as data, never executed.
Mutation fixtures stay in memory; originals are never written. No source truth is verified.
Public note text includes documented source-locator redactions; numerical values and units are unchanged.
Run with an explicit new output directory and the installed jsonschema package.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import importlib.metadata
import platform
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

import argparse
parser = argparse.ArgumentParser(description='Offline research replay only; not a production admission gate.')
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
OUT = args.output_dir.resolve()
if OUT == ROOT or ROOT in OUT.parents:
    raise SystemExit('Choose an output directory outside the research package.')
if OUT.exists():
    raise SystemExit('Choose a new output directory; replay does not overwrite existing files.')
m = json.loads((ROOT / 'submission-provenance.json').read_text())
loaded, hashes = {}, []
for f in m['files']:
    b = (ROOT / f['package_path']).read_bytes()
    h = hashlib.sha256(b).hexdigest()
    assert h == f['package_sha256'] and len(b) == f['package_bytes'], f['package_path']
    hashes.append({'path': f['package_path'], 'sha256': h, 'bytes': len(b), 'matches_packaged_copy': True})
    if f['package_path'].endswith('.json'):
        seen_dups = []
        def hook(pairs):
            d = {}
            for k, v in pairs:
                if k in d: seen_dups.append(k)
                d[k] = v
            return d
        loaded[f['role']] = json.loads(b, object_pairs_hook=hook)
        assert not seen_dups
    else:
        narrative = b.decode('utf-8')
prompt_bytes = (ROOT / m['issued_assignment']['path']).read_bytes()
assert hashlib.sha256(prompt_bytes).hexdigest() == m['issued_assignment']['sha256']
schema = loaded['proposed_companion_json_schema']
examples = loaded['populated_candidate_panel_examples']
audit = loaded['source_linked_panel_audit']

def deny_retrieval(uri):
    raise RuntimeError('Offline validation forbids external retrieval: ' + uri)

def walk(x, p=''):
    yield p, x
    if isinstance(x, dict):
        for k, v in x.items(): yield from walk(v, p + '/' + k.replace('~', '~0').replace('/', '~1'))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from walk(v, p + '/' + str(i))
refs = [x['$ref'] for _, x in walk(schema) if isinstance(x, dict) and '$ref' in x]
assert all(x.startswith('#/') for x in refs)
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker(), registry=Registry(retrieve=deny_retrieval))
plain_validator = Draft202012Validator(schema, registry=Registry(retrieve=deny_retrieval))

def schema_errors(d, v=validator):
    return [{'instance_path': '/' + '/'.join(str(i) for i in e.absolute_path),
             'schema_path': '/' + '/'.join(str(i) for i in e.absolute_schema_path),
             'message': e.message} for e in v.iter_errors(d)]

def dt(x): return datetime.fromisoformat(x.replace('Z', '+00:00'))

def domain_errors(d):
    """Bounded reviewer checks, not a production adapter or an upstream truth oracle.
    Explicit audit extracts are the preservation oracle. Additional checks are local
    implications of the eight case specifications, not new claims about source content.
    """
    errs = []
    def err(code, path, detail): errs.append({'code': code, 'path': path, 'detail': detail})
    cutoff = dt(d['cutoff'])
    cs = d['candidate_records']
    by_id = {c['candidate_id']: c for c in cs}
    audit_by_id = {c['candidate_id']: c for c in audit['join_exclusion_table']}
    arts = {x['artifact_id'] for x in d['artifact_records']}
    specs = {x['evaluation_spec_id'] for x in d['protocol_records']}
    for collection, key, path in [(cs,'candidate_id','/candidate_records'),(cs,'evalplus_key','/candidate_records'),(d['artifact_records'],'artifact_id','/artifact_records'),(d['protocol_records'],'evaluation_spec_id','/protocol_records')]:
        counts = Counter(x[key] for x in collection)
        for value, count in counts.items():
            if count > 1: err('DUPLICATE_KEY',path, f'{key}={value!r} appears {count} times')
    for p, x in walk(d):
        if isinstance(x,dict) and set(('earliest','latest','evidence_kind','evidence_refs')) <= x.keys():
            if x['earliest'] and x['latest']:
                try:
                    if dt(x['earliest']) > dt(x['latest']): err('REVERSED_TIME_INTERVAL',p,'earliest > latest')
                except ValueError: pass # format validation is separate
    assertions = {c['candidate_id']+'/feature/'+f['name']: f for c in cs for f in c['features']}
    native_map = {'epoch_current.parameters':'Parameters','epoch_current.citations':'Citations','epoch_current.publication_date':'Publication date','epoch_current.last_modified':'Last modified','epoch_current.base_model':'Base model','epoch_current.training_compute_FLOP':'Training compute (FLOP)'}
    for ci, c in enumerate(cs):
        p = f'/candidate_records/{ci}'
        ref = audit_by_id.get(c['candidate_id'])
        ident = c['identity']
        if c['epoch_artifact_id'] not in arts: err('DANGLING_ARTIFACT',p,c['epoch_artifact_id'])
        if ref:
            if c['epoch_model'] != ref['epoch_native_key'] or c['evalplus_key'] != ref['evalplus_native_key']:
                err('CANDIDATE_NATIVE_KEY_MISMATCH',p,'Candidate names differ from supplied audit extract')
            if ident['executed_checkpoint_or_service_id'] != ref['executed_checkpoint_or_service_snapshot']:
                err('EXECUTION_UNSUPPORTED_BY_SUPPLIED_EVIDENCE',p+'/identity','Supplied audit has no executed checkpoint; promotion needs new evidence')
            if ref['join_status'] in ('rejected_direct_join','rejected_equivalence_ancestry_retained') and ident['relationship'] in ('same_executed_model','same_named_variant_only'):
                err('REJECTED_VARIANT_EQUIVALENCE',p+'/identity','Proposed equivalence conflicts with supplied join rejection')
        if ident['status'] != 'exact_execution_documented' and ident['executed_checkpoint_or_service_id'] is not None:
            err('IDENTITY_STATUS_CONTRADICTION',p+'/identity','Non-exact identity carries executed ID')
        feature_names = Counter(f['name'] for f in c['features'])
        for name,count in feature_names.items():
            if count>1: err('DUPLICATE_FEATURE_NAME',p+'/features',name)
        for fi,f in enumerate(c['features']):
            fp=p+f'/features/{fi}'
            q=f['value']
            if ref and f['name'] in native_map:
                raw=ref['raw_epoch_extract'][native_map[f['name']]]
                if q['raw'] != raw: err('NATIVE_RAW_CHANGED',fp,'Raw value differs from supplied audit extract')
                if f['name'] in ('epoch_current.parameters','epoch_current.citations','epoch_current.training_compute_FLOP'):
                    if raw == '' and q['point'] is not None: err('NATIVE_BLANK_NUMERICIZED',fp,'A notes extraction must not populate the native blank numeric field')
                    if raw != '' and q['point'] is not None and Decimal(str(q['point'])) != Decimal(raw): err('NUMERIC_INTERPRETATION_MISMATCH',fp,'Parsed point differs from native numeric string')
            if q['lower'] is not None and q['upper'] is not None and q['lower'] > q['upper']: err('REVERSED_QUANTITY_BOUNDS',fp,'lower > upper')
            if f['name']=='epoch_current.training_compute_FLOP' and ref:
                # This input reports a 90% interval only for GPT-4; other qualitative labels have no numeric confidence level.
                expected=0.9 if c['candidate_id']=='PIT-J01' else None
                if q['confidence_level'] != expected: err('UNSUPPORTED_CONFIDENCE_LEVEL',fp,'Numeric confidence level conflicts with the supplied audit preservation fixture')
            if f['included_by_cutoff']:
                if q['raw'] in (None, '') and all(q[k] is None for k in ('point','lower','upper')): err('INCLUDED_FEATURE_EMPTY_VALUE',fp,'An empty native string is not a substantive included feature value')
                t=f['input_information_availability'] if f['availability_basis']=='reconstructed_from_pre_cutoff_inputs' else f['public_availability']
                if not t or not t['latest']: err('MISSING_FEATURE_TIME',fp,'Included feature has no bounded latest availability')
                elif dt(t['latest'])>cutoff: err('FUTURE_FEATURE_INCLUDED',fp,'Relevant availability exceeds declared cutoff')
            if f['availability_basis']=='reconstructed_from_pre_cutoff_inputs':
                for dep in f['computation_dependency_assertion_ids']:
                    if dep not in assertions: err('DANGLING_FEATURE_DEPENDENCY',fp,dep)
                if f['name'].endswith('pretraining_compute_6ND_FLOP'):
                    inputs=[assertions[x]['value']['point'] for x in f['computation_dependency_assertion_ids'] if x in assertions]
                    if len(inputs)==2 and Decimal(str(q['point'])) != 6*Decimal(str(inputs[0]))*Decimal(str(inputs[1])): err('DERIVATION_VALUE_MISMATCH',fp,'6ND reconstruction does not equal recorded inputs')
            if ident['relationship']=='base_ancestor' and f['compute_scope']=='total_training' and q['point'] is not None:
                err('ANCESTRAL_COMPUTE_PROMOTED_TO_TOTAL',fp,'Supplied base-to-instruct fixture has no descendant total-compute evidence')
            if c['candidate_id']=='PIT-J08' and f['name'].endswith('pretraining_compute_6ND_FLOP') and f['compute_scope']!='ancestral_pretraining': err('COMPUTE_SCOPE_MISMATCH',fp,'Known base estimate must remain ancestral scope for instruct fixture')
        seen=[]
        for si,s in enumerate(c['snapshots']):
            sp=p+f'/snapshots/{si}'
            seen.append(s['artifact_id'])
            if s['artifact_id'] not in arts: err('DANGLING_ARTIFACT',sp,s['artifact_id'])
            if s['evaluation_spec_id'] is not None and s['evaluation_spec_id'] not in specs: err('DANGLING_PROTOCOL',sp,s['evaluation_spec_id'])
            if s['previous_artifact_id'] is not None and s['previous_artifact_id'] not in arts: err('DANGLING_PREDECESSOR',sp,s['previous_artifact_id'])
            if s['source_model_key'] != c['evalplus_key']: err('SNAPSHOT_CANDIDATE_KEY_MISMATCH',sp,'Native source key differs from parent candidate')
            for metric,value in s['source_pass_at_1_percent'].items():
                if (value is None) != (metric in s['missing_reasons']): err('NULL_REASON_MISMATCH',sp+'/'+metric,'Null and missing-reason presence must agree')
            if ref and s['artifact_id'] in ('evalplus-results-A','evalplus-results-B'):
                tag=s['artifact_id'][-1]; native=ref['evalplus_'+tag+'_native_object']
                mapping={'source_pass_at_1_percent':'pass@1','source_link':'link','source_open_data':'open-data','source_prompted':'prompted','source_size_billion_parameters':'size'}
                for f,n in mapping.items():
                    if s[f]!=native[n]: err('NATIVE_SNAPSHOT_CHANGED',sp+'/'+f,'Value differs from supplied audit native object')
            if s['revision_relationship']=='new_inference' and (not s['run_id'] or not s['output_set_id'] or not s['inference_time']['latest']): err('NEW_INFERENCE_WITHOUT_RUN',sp,'New inference requires run, output and time evidence')
            if s['revision_relationship']=='regrade_same_outputs' and not s['output_set_id']: err('REGRADE_WITHOUT_OUTPUT_ID',sp,'Regrading requires a documented output identity and reuse relation')
            if s['prospective_outcome'] is True and s['label_available_at_cutoff'] in ('repository_chronology_only','proven'): err('HISTORICAL_LABEL_MARKED_PROSPECTIVE',sp,'Already historical under the chosen chronology cannot be an unseen target')
            if s['label_available_at_cutoff']=='proven':
                t=s['result_public_availability']
                if not t['latest'] or t['evidence_kind']=='unknown' or dt(t['latest'])>cutoff: err('LABEL_PROVEN_WITHOUT_PRE_CUTOFF_EVIDENCE',sp,'Proven flag lacks matching dated availability')
        if len(seen)!=len(set(seen)): err('DUPLICATE_SNAPSHOT_SLOT',p+'/snapshots','Same candidate/artifact publication slot appears more than once')
        decisions=Counter(x['view'] for x in c['decisions'])
        if any(v>1 for v in decisions.values()): err('DUPLICATE_VIEW_DECISION',p+'/decisions','Multiple potentially contradictory decisions for one view')
        if 'family:'+c['family_group_id'] not in c['dependencies']['split_group_ids']: err('MISSING_CONSERVATIVE_FAMILY_GROUP',p+'/dependencies','This bounded panel promises one conservative family block')
        for dec in c['decisions']:
            if dec['included'] and dec['view']!='descriptive':
                if ident['status']!='exact_execution_documented' or ident['relationship']!='same_executed_model' or not ident['executed_checkpoint_or_service_id']: err('STRICT_IDENTITY_NOT_READY',p,'Strict view enabled without exact executed identity')
                for s in c['snapshots']:
                    if not s['run_id'] or not s['output_set_id'] or not s['evaluation_spec_id'] or not s['inference_time']['latest']: err('STRICT_RUN_NOT_READY',p,'Strict candidate decision has no assertion-level selection and unresolved snapshot run/protocol links')
                if dec['view']=='independent_compute_performance':
                    eligible=[f for f in c['features'] if f['included_by_cutoff'] and f['value']['unit']=='FLOP' and f['value']['point'] is not None]
                    if not eligible or all(f['provenance']=='benchmark_imputation' for f in eligible): err('INDEPENDENT_COMPUTE_NOT_AVAILABLE',p,'Only admitted compute is circular or no independent compute is selected')
    for pi,p in enumerate(d['protocol_records']):
        pp=f'/protocol_records/{pi}'; b=p['actual_run_binding']
        for a in p['applies_to_artifact_ids']:
            if a not in arts: err('DANGLING_PROTOCOL_ARTIFACT',pp,a)
        if set(b['metric_denominators']) != set(p['metric_names']): err('DENOMINATOR_METRIC_KEYS',pp,'Denominator keys differ from declared metric names')
        has_actual=any(v is not None for v in b['metric_denominators'].values())
        if has_actual and (not b['run_id'] or not b['task_manifest_hash']): err('DENOMINATOR_WITHOUT_RUN_EVIDENCE',pp,'Nominal task count cannot supply an actual-run denominator')
        if any(v is not None and v<=0 for v in b['metric_denominators'].values()): err('INVALID_ACTUAL_DENOMINATOR',pp,'An observed fraction requires positive denominator')
        if p['evidence_status']=='actual_run_documented' and any(b[k] is None for k in ('run_id','output_set_hash','task_manifest_hash','harness_commit','prompt_content_hash','scorer_commit','generation_configuration')): err('ACTUAL_RUN_STATUS_UNSUPPORTED',pp,'Documented status contradicts null actual run fields')
    return errs

# Declarative JSON Pointer mutations are applied only to in-memory copies.
def pointer_set(d,p,value):
    parts=[x.replace('~1','/').replace('~0','~') for x in p.strip('/').split('/')]
    cur=d
    for x in parts[:-1]: cur=cur[int(x)] if isinstance(cur,list) else cur[x]
    if isinstance(cur,list): cur[int(parts[-1])]=deepcopy(value)
    else: cur[parts[-1]]=deepcopy(value)

def C(n,suffix): return '/candidate_records/'+str(n-1)+'/'+suffix

def ready(n,view='training_data_known_at_cutoff'):
    idx=next(i for i,d in enumerate(examples['candidate_records'][n-1]['decisions']) if d['view']==view)
    return [(C(n,'decisions/'+str(idx)),{'view':view,'status':'ready','included':True,'hold_reasons':[]})]

def fake_exact(n):
    ident=examples['candidate_records'][n-1]['identity']
    return [(C(n,'identity/status'),'exact_execution_documented'),(C(n,'identity/relationship'),'same_executed_model'),(C(n,'identity/executed_checkpoint_or_service_id'),ident['candidate_checkpoint_or_service_id'])]

mutations=[]
def add(i,case,name,patches,expected_schema_accept):
    mutations.append({'test_id':i,'acceptance_case':case,'name':name,'expected_domain_result':'reject','expected_schema_accept':expected_schema_accept,'patches':[{'path':p,'value':v} for p,v in patches]})
add('01a','PIT-01','Include alias while unresolved',ready(1),False)
add('01b','PIT-01','Put documentary candidate ID in executed field without changing alias status',[(C(1,'identity/executed_checkpoint_or_service_id'),'gpt-4-0314')],True)
add('01c','PIT-01','Promote identity labels and mark strict view ready while every run/protocol binding remains null',fake_exact(1)+ready(1),True)
add('02a','PIT-02','Relabel rejected base-to-instruct ancestry as same named variant',[(C(8,'identity/relationship'),'same_named_variant_only')],True)
add('02b','PIT-02','Copy base compute into descendant total without supporting training evidence',[(C(8,'features/11/value/point'),8.04e22),(C(8,'features/11/value/missing_reason'),None)],True)
add('02c','PIT-02','Relabel included ancestral compute as total training',[(C(8,'features/9/compute_scope'),'total_training')],True)
add('03a','PIT-03','Promote documentary Hub ID with a post-cutoff inspected revision into exact historical execution',fake_exact(10)+ready(10)+[(C(10,'identity/inspected_repository_revision'),'synthetic-future-revision'),(C(10,'identity/revision_availability/earliest'),'2026-10-08T00:00:00Z'),(C(10,'identity/revision_availability/latest'),'2026-10-08T00:00:00Z')],True)
add('04a','PIT-04','Declare new inference with null run and output evidence',[(C(5,'snapshots/1/revision_relationship'),'new_inference')],True)
add('04b','PIT-04','Declare regrade of same outputs with null output ID',[(C(5,'snapshots/1/revision_relationship'),'regrade_same_outputs')],True)
add('04c','PIT-04','Populate actual-run denominator from nominal MBPP task population', [('/protocol_records/1/actual_run_binding/metric_denominators/mbpp',399)],True)
add('04d','PIT-04','Claim actual run documented while bindings remain null',[('/protocol_records/0/evidence_status','actual_run_documented')],True)
add('04e','PIT-04','Accept zero denominator and unrelated metric key',[('/protocol_records/1/actual_run_binding/metric_denominators',{'mbpp':0,'mbpp+':None,'fabricated_metric':378})],True)
add('05a','PIT-05','Replace publisher null MBPP with zero',[(C(5,'snapshots/1/source_pass_at_1_percent/mbpp'),0)],True)
add('05b','PIT-05','Forward-fill removed MBPP from snapshot A',[(C(5,'snapshots/1/source_pass_at_1_percent/mbpp'),65.4)],True)
add('05c','PIT-05','Populate blank native compute from notes',[(C(2,'features/5/value/point'),2.2e25),(C(2,'features/5/value/missing_reason'),None)],True)
add('05d','PIT-05','Reinterpret qualitative confidence as 95 percent interval',[(C(4,'features/5/value/uncertainty_kind'),'confidence_interval'),(C(4,'features/5/value/confidence_level'),0.95),(C(4,'features/5/value/lower'),5e23),(C(4,'features/5/value/upper'),6e23)],True)
add('05e','PIT-05','Remove source null explanation',[(C(5,'snapshots/1/missing_reasons'),{})],True)
metrics=deepcopy(examples['candidate_records'][4]['snapshots'][1]['source_pass_at_1_percent']); del metrics['mbpp']
add('05f','PIT-05','Delete required native metric slot',[(C(5,'snapshots/1/source_pass_at_1_percent'),metrics)],False)
add('05g','PIT-05','Set native percentage outside 0 to 100',[(C(5,'snapshots/1/source_pass_at_1_percent/mbpp'),101)],False)
add('05h','PIT-05','Admit empty-string native value with no numeric value by clearing missingness',[(C(2,'features/5/included_by_cutoff'),True),(C(2,'features/5/hold_reasons'),[]),(C(2,'features/5/value/missing_reason'),None),(C(2,'features/5/public_availability'),{'earliest':'2024-01-01T00:00:00Z','latest':'2024-01-01T00:00:00Z','evidence_kind':'publisher_publication_record','evidence_refs':['synthetic-test-only']})],True)
add('06a','PIT-06','Include a current 2026 citation count without changing future timestamp',[(C(1,'features/1/included_by_cutoff'),True),(C(1,'features/1/hold_reasons'),[])],True)
add('06b','PIT-06','Move included source-reported feature into future',[(C(10,'features/8/public_availability/latest'),'2026-01-01T00:00:00Z')],True)
add('06c','PIT-06','Move reconstruction input availability into future',[(C(7,'features/9/input_information_availability/latest'),'2026-01-01T00:00:00Z')],True)
add('06d','PIT-06','Reverse an availability interval',[(C(10,'features/8/public_availability/earliest'),'2025-01-01T00:00:00Z')],True)
add('06e','PIT-06','Call A an unseen prospective outcome despite repository-chronology historical flag',[(C(1,'snapshots/0/prospective_outcome'),True)],True)
add('06f','PIT-06','Call B cutoff-proven with unknown result availability',[(C(1,'snapshots/1/label_available_at_cutoff'),'proven'),(C(1,'snapshots/1/prospective_outcome'),False)],True)
add('06g','PIT-06','Call a proven historical label prospective',[(C(1,'snapshots/0/label_available_at_cutoff'),'proven'),(C(1,'snapshots/0/prospective_outcome'),True)],False)
add('06h','PIT-06','Admit source feature with missing availability',[(C(10,'features/8/public_availability/latest'),None)],False)
add('06i','PIT-06','Break reconstruction reference while leaving nonempty dependency list',[(C(7,'features/9/computation_dependency_assertion_ids'),['nonexistent/feature/N','nonexistent/feature/D'])],True)
add('06j','PIT-06','Alter 6ND calculation while inputs are unchanged',[(C(7,'features/9/value/point'),8.05e22)],True)
imputed=deepcopy(examples['candidate_records'][1]['features'][7]); imputed['included_by_cutoff']=True; imputed['hold_reasons']=[]; imputed['public_availability']={'earliest':'2024-01-01T00:00:00Z','latest':'2024-01-01T00:00:00Z','evidence_kind':'publisher_publication_record','evidence_refs':['synthetic-test-only']}
add('07a','PIT-07','Independent view marked ready with only benchmark-imputed eligible compute, even after giving it synthetic pre-cutoff timing',fake_exact(2)+ready(2,'independent_compute_performance')+[(C(2,'features'),[imputed])],True)
add('08a','PIT-08','Repeat candidate ID with nonidentical record',[(C(2,'candidate_id'),'PIT-J01')],True)
add('08b','PIT-08','Duplicate a native candidate key',[(C(2,'evalplus_key'),'GPT-4 (May 2023)')],True)
add('08c','PIT-08','Repeat candidate/artifact snapshot slot with nonidentical metadata',[(C(5,'snapshots/1/artifact_id'),'evalplus-results-A')],True)
add('08d','PIT-08','Repeat an identical whole snapshot',[(C(5,'snapshots/1'),examples['candidate_records'][4]['snapshots'][0])],False)
add('08e','PIT-08','Replace conservative family group on related instruct variant',[(C(8,'dependencies/split_group_ids'),['independent:test-fold'])],True)
add('08f','PIT-08','Reimport identical artifact as another artifact record',[('/artifact_records',examples['artifact_records']+[examples['artifact_records'][0]])],True)
add('08g','PIT-08','Duplicate protocol ID',[('/protocol_records',examples['protocol_records']+[examples['protocol_records'][0]])],True)
add('08h','PIT-08','Use nonexistent protocol link',[(C(5,'snapshots/1/evaluation_spec_id'),'missing-protocol')],True)
add('08i','PIT-08','Repeat feature name with divergent assertion',[(C(1,'features/1/name'),'epoch_current.parameters')],True)
add('08j','PIT-08','Duplicate a view decision',[(C(1,'decisions'),examples['candidate_records'][0]['decisions']+[examples['candidate_records'][0]['decisions'][0]])],True)

baseline_domain=domain_errors(examples)
results=[]
for spec in mutations:
    x=deepcopy(examples)
    for patch in spec['patches']: pointer_set(x,patch['path'],patch['value'])
    se=schema_errors(x); de=domain_errors(x)
    rec=dict(spec,schema_accepts=not se,schema_errors=se,reviewer_check_rejects=bool(de),reviewer_errors=de)
    assert (not se)==spec['expected_schema_accept'], spec['test_id']
    assert de, spec['test_id']
    results.append(rec)

snapshots=[s for c in examples['candidate_records'] for s in c['snapshots']]
slots=[v for s in snapshots for v in s['source_pass_at_1_percent'].values()]
counts={'candidates':len(examples['candidate_records']),'families':len({c['family_group_id'] for c in examples['candidate_records']}),'snapshot_objects':len(snapshots),'metric_slots':len(slots),'numeric_slots':sum(v is not None for v in slots),'null_slots':sum(v is None for v in slots),'features':sum(len(c['features']) for c in examples['candidate_records']),'included_features':sum(f['included_by_cutoff'] for c in examples['candidate_records'] for f in c['features']),'strict_views_included':sum(x['included'] for c in examples['candidate_records'] for x in c['decisions'] if x['view']!='descriptive'),'executed_id_known':sum(c['identity']['executed_checkpoint_or_service_id'] is not None for c in examples['candidate_records']),'known_snapshot_run_ids':sum(s['run_id'] is not None for s in snapshots)}
summary={'review_type':'independent_offline_schema_and_bounded_data_semantics','scope':'Packaged copies of four supplied artifacts and preserved issued assignment only; no source downloads or upstream verification. JSON parsed as data; reviewer-authored Python only.','python_version':platform.python_version(),'jsonschema_version':importlib.metadata.version('jsonschema'),'draft':'2020-12','format_checker_enabled':True,'remote_reference_retrieval':'disabled; all supplied schema refs are local','input_hashes':hashes,'issued_assignment_hash_verified':True,'schema_metaschema_valid':True,'examples_shape_errors':schema_errors(examples,plain_validator),'examples_format_checked_errors':schema_errors(examples),'baseline_reviewer_errors':baseline_domain,'baseline_counts':counts,'mutations_total':len(results),'unsafe_mutations_accepted_by_schema':sum(r['schema_accepts'] for r in results),'unsafe_mutations_rejected_by_schema':sum(not r['schema_accepts'] for r in results),'mutations_rejected_by_bounded_reviewer_checks':sum(r['reviewer_check_rejects'] for r in results),'case_summary':[{'case_id':case['case_id'],'name':case['name'],'tests':[r['test_id'] for r in results if r['acceptance_case']==case['case_id']],'schema_accepts_unsafe':sum(r['schema_accepts'] for r in results if r['acceptance_case']==case['case_id']),'schema_rejects_unsafe':sum(not r['schema_accepts'] for r in results if r['acceptance_case']==case['case_id'])} for case in audit['proposed_acceptance_cases']['cases']],'evidence_boundary':['Matching duplicated audit extracts demonstrates internal consistency, not upstream accuracy.','All 8 acceptance specifications exercised via bounded in-memory mutations; no production adapter was supplied or tested.','Reviewer checks are deliberately partial and fixture-specific; no claim of a complete domain validator.','Synthetic changes are negative test cases, not recovered source facts or validated execution evidence.']}
for f in m['files']:
    assert hashlib.sha256((ROOT/f['package_path']).read_bytes()).hexdigest()==f['package_sha256']
summary['packaged_hashes_unchanged_after_tests']=True
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'validation-results.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'mutation-test-results.json').write_text(json.dumps(results,indent=2)+'\n')
assert not baseline_domain, baseline_domain
print(json.dumps({'baseline_counts':counts,'baseline_domain_errors':len(baseline_domain),'mutation_total':len(results),'schema_accepts_unsafe':summary['unsafe_mutations_accepted_by_schema'],'schema_rejects_unsafe':summary['unsafe_mutations_rejected_by_schema'],'reviewer_rejects':summary['mutations_rejected_by_bounded_reviewer_checks']},indent=2))
