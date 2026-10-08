"""Offline package verification; source experiments and submitted acceptance cases stay unexecuted."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
checks=[]
def load(p): return json.loads((ROOT/p).read_text())
def check(name,ok):
 checks.append({'check':name,'passed':bool(ok)})
 if not ok: raise AssertionError(name)
def sha(b):return hashlib.sha256(b).hexdigest()
def gitsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def resolve_pointer(obj,pointer):
 for part in pointer.strip('/').split('/'):
  part=part.replace('~1','/').replace('~0','~');obj=obj[int(part)] if isinstance(obj,list) else obj[part]
 return obj
L=load('source-native-ledger.json'); O=load('original-context/submitted-ledger.json')
check('original ledger exact bytes retained',(ROOT/'source-native-ledger.json').read_bytes()==(ROOT/'original-context/submitted-ledger.json').read_bytes())
manifest=load('original-context/intake-manifest.json')
for f in manifest['files']:
 p=ROOT/'original-context'/('submitted-ledger.json' if f['file_name'].endswith('.json') else 'submitted-narrative.txt')
 check('input byte length '+f['file_name'],p.stat().st_size==f['size_bytes'])
 check('input sha256 '+f['file_name'],sha(p.read_bytes())==f['sha256'])
for key,n,idkey in [('artifacts',15,'artifact_id'),('assertions',40,'assertion_id'),('lineage_edges',17,'edge_id'),('comparability_decisions',18,'comparison_id'),('acceptance_cases',20,'case_id')]:
 check('preserved count '+key,len(L[key])==n);check('unique ids '+key,len({x[idkey] for x in L[key]})==n)
check('preserved nine rights records',len(L['rights_ledger'])==9)
check('original inspected baseline remains null',L['repository_context']['inspected_repository_commit'] is None)
check('original operational admission remains false',L['operational_admission'] is False)
check('acceptance case specifications preserved',load('acceptance-cases.json')['cases']==L['acceptance_cases'])
for case in L['acceptance_cases']:check('unexecuted '+case['case_id'],case['execution_status']=='not_executed')
for a in L['assertions']:
 for e in a['evidence']:check(a['assertion_id']+' artifact ref '+e['artifact_id'],e['artifact_id'] in {x['artifact_id'] for x in L['artifacts']})
for row in load('repository-files-manifest.json'):
 p=ROOT/'contract-work/pinned'/row['path'];b=p.read_bytes()
 check('repo blob '+row['path'],gitsha(b)==row['sha'])
 check('repo sha256 '+row['path'],sha(b)==row['sha256'])
M=load('contract-work/contract-mapping.json')
check('mapping current commit',M['repository_context']['inspected_commit']=='246f746e3a267363c7f6d2e0494eb72fb4c98bc9')
check('mapping preserves all source assertions',[x['source_native_assertion'] for x in M['assertion_mappings']]==L['assertions'])
for k,v in M['preserved_source_native_review_sections'].items():check('mapping preserved section '+k,v==L[k])
for topic,d in M['common_field_mappings'].items():
 for row in d['native_fields']:
  source=load('contract-work/pinned/'+row['schema']['file']);value=resolve_pointer(source,row['schema']['json_pointer'])
  check('native pointer '+topic+' '+row['record_path'],isinstance(value,dict))
for rec in M['native_record_types_reviewed']:
 schema=load('contract-work/pinned/'+rec['native_data_definition']['file']);d=resolve_pointer(schema,rec['native_data_definition']['json_pointer'])
 check('native required '+rec['record_type'],rec['required_data_fields']==d['required'])
 check('native fields '+rec['record_type'],rec['allowed_data_fields']==list(d['properties']))
R=load('contract-work/schema-probe-results.json')
check('20 distinct new probes',R['probe_count']==20)
check('probe expected outcomes matched',R['all_expected_schema_outcomes_matched'])
check('14 schema accepts and six rejects',R['schema_accepted_count']==14 and R['schema_rejected_count']==6)
check('no upstream code execution',R['upstream_code_executed'] is False)
check('original cases not executed by probes',R['original_acceptance_cases_executed'] is False)
check('offline probe registry',R['offline_registry_only'] is True)
check('no adapter or admission',R['adapter_implemented'] is False and R['operational_admission'] is False)
bindings=load('inspection/livesec-git-binding.json')
for f,path in [('inspection/livesec-readme-connector.json','README.md'),('inspection/livesec-user-guide-connector.json','docs/USER_GUIDE.md')]:
 r=load(f);b=r['content'].encode();t=next(x for x in bindings['entries'] if x['path']==path)
 check('upstream fresh blob '+path,gitsha(b)==r['reported_git_blob_sha']==t['sha'])
 check('upstream fresh sha256 '+path,sha(b)==r['sha256'])
 check('upstream fresh size '+path,len(b)==t['size']==r['size_bytes'])
A=load('arithmetic-review.json')['checks']
check('F007 no integer repair',A[0]['integer_counts_matching']==[])
check('SuperCLUE printed difference conflict',A[1]['computed_difference']=='2.76' and A[1]['reported_difference']=='-1.24')
check('LiveSec conditional exposure',A[2]['battles_divided_by_models']=='403.6' and A[2]['two_participations_per_battle_conditional']=='807.2')
check('LiveSec aggregates',A[3]['questions_sum']==852 and A[3]['battles_sum']==23005)
check('current artifact checks cover every original',{r['artifact_id'] for r in load('primary-verification.json')['current_artifact_checks']}=={r['artifact_id'] for r in L['artifacts']})
check('current assertion review covers every original',{r['assertion_id'] for r in load('assertion-review.json')['assertions']}=={r['assertion_id'] for r in L['assertions']})
check('lineage preserved',load('lineage-review.json')['original_edges']==L['lineage_edges'])
check('comparability preserved',load('comparability-review.json')['original_decisions']==L['comparability_decisions'])
check('rights preserved',load('rights-by-artifact.json')['original_rights_records']==L['rights_ledger'])
P=load('prior-catalog-preservation.json')
catalog=load('contract-work/pinned/data/evidence-program/research/chinese-safety-evaluations.json')
check('prior catalog exact selected families',P['families']==[f for f in catalog['families'] if f['candidate_id'] in ['ZHS001','ZHS006','ZHS004']])
for d in load('delta.json')['changes']:
 for p in d['evidence']:check('delta evidence file '+p,(ROOT/p).is_file())
result={'format':'documentary_review_integrity_checks','all_checks_passed':True,'check_count':len(checks),'checks':checks,'scope':'Original byte preservation, inventories, actual contract paths, new source blob pins, probe outcomes and arithmetic only. Not original-study execution, semantic acceptance, full native validator execution or independent review.'}
(ROOT/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'all_checks_passed':True,'check_count':len(checks)}))
