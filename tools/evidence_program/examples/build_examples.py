#!/usr/bin/env python3
"""Rebuild fully fictional linked fixtures. No network access or real evidence."""
import copy
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validate_dataset import digest

KNOWN='2026-09-30T12:00:00Z'
REVIEW='2026-09-30T13:00:00Z'
def rr(t, slug, rev=1): return {'id':f'urn:pdataset:{t}:{slug}', 'revision':rev}
def unknown(reason='Not applicable to this fictional fixture.'): return {'kind':'unknown','reason':reason}
def day(d): return {'kind':'date','date':d}
def evidence(): return [{'source_ref':rr('source_artifact','fictional-original'), 'locator':'Fictional appendix, sections 1–9', 'relation':'supports','extraction_method':'synthetic','extractor_version':'fixture-generator-0.1.0'}]
def record(t,slug,data,event=None,evaluated=None):
    return {'schema_version':'0.1.0','record_type':t,**rr(t,slug),'synthetic':True,
      'times':{'known_at':KNOWN,'retrieved_at':KNOWN,'published':day('2026-09-28'),'event':event or unknown(),'evaluated':evaluated or unknown()},
      'governance':{'review_state':'machine_validated','reviewed_at':REVIEW,'rights_state':'redistribution_allowed','rights_basis':'Wholly fictional fixture authored for this design package; no real source content.','publication_state':'internal'},
      'evidence':[] if t in ('source_artifact','snapshot') else evidence(),'data':data}
def measure(value,unit,mode='reported',key='fixture-score-v1',definition='Number correct divided by number attempted in fictional tasks.',minimum=None,maximum=None):
    metric={'key':key,'definition':definition,'unit':unit,'direction':'neutral'}
    if minimum is not None: metric['minimum']=minimum
    if maximum is not None: metric['maximum']=maximum
    return {'metric':metric,'result':value,'observation_mode':mode,'method':'Synthetic data illustrating the contract; no evaluation was performed.','sample_size':100,'uncertainty_notes':'These values are made up, not empirical estimates.'}
def point(value,unit):return {'kind':'point','value':value,'unit':unit}
def actor(slug,kind,name):
    return record('actor',slug,{'actor_kind':kind,'name':name,'name_language':'zh-Hans' if slug=='fictional-lab' else 'en','aliases':[], 'jurisdictions':[], 'affiliations':[],'external_ids':[]})

source=record('source_artifact','fictional-original',{'canonical_url':'https://example.invalid/fictional-ai-observatory/report-zh','title':'虚构 AI 数据示例','source_type':'report','language':'zh-Hans','publisher_ref':rr('actor','fictional-lab'),'author_refs':[rr('actor','fictional-analyst')],'availability':'available'})
translation=record('source_artifact','fictional-translation',{'canonical_url':'https://example.invalid/fictional-ai-observatory/report-en','title':'Fictional AI dataset example','source_type':'report','language':'en','publisher_ref':rr('actor','fictional-lab'),'author_refs':[rr('actor','fictional-analyst')],'availability':'available','translation':{'original_ref':rr('source_artifact','fictional-original'),'method':'machine_human_reviewed','translator':'Fictional translator fixture, not an actual translation workflow','review_status':'checked','notes':'Demonstrates preservation of probability, condition and date precision.'}})
lab=actor('fictional-lab','organization','示例研究所（虚构）')
lab['data']['jurisdictions']=[{'code':'CN','relationship':'based_in','valid_time':{'kind':'range','start':'2026-01-01','end':'2026-12-31','precision':'year'}}]
analyst=actor('fictional-analyst','person','Avery Example, fictional analyst')
analyst['data']['affiliations']=[{'organization_ref':rr('actor','fictional-lab'),'role':'Fictional researcher','valid_time':unknown('Fictional affiliation dates are not specified.')}]
collective=actor('fictional-panel','collective','Fictional survey panel, September wave')
collective['data']['collective']={'collective_kind':'survey_respondents','population_scope':'100 fictional volunteer respondents to one synthetic survey wave; not representative of researchers or the public.','anonymity':'anonymous'}
model=record('model_version','fictional-orbit-1',{'developer_refs':[rr('actor','fictional-lab')],'family':'Fictional Orbit','version_label':'fictional-1.0','provider_model_id':'fixture-only-orbit-1.0','modality':['text'],'access':'api','parent_model_refs':[],'version_certainty':'provider_label'})
release=record('release_event','fictional-orbit-announcement',{'model_ref':rr('model_version','fictional-orbit-1'),'release_kind':'announcement','availability_scope':'Fictional announcement only; no real service exists.','release_url':'https://example.invalid/fictional-ai-observatory/announcement'},event=day('2026-09-05'))
protocol={'name':'fictional-task-harness','version':'fixture-v1','configuration':'Fictional zero-shot prompt; no tools; temperature 0; maximum 1000 output tokens; 100 synthetic tasks.','reproducibility':'partial'}
benchmark=record('benchmark_run','fictional-score',{'model_ref':rr('model_version','fictional-orbit-1'),'evaluator_refs':[rr('actor','fictional-lab')],'benchmark':{'name':'FictionalCheck','version':'fixture-v1','split':'fictional-test','task':'Fictional exact-match correctness.','contamination_status':'not_tested'},'protocol':protocol,'measurement':measure({'kind':'interval','lower':'0.61','upper':'0.79','unit':'ratio','interval_kind':'confidence','level':'0.95'},'ratio',minimum='0',maximum='1'),'independence':'developer_reported'},evaluated=day('2026-09-10'))
compute=record('resource_observation','fictional-training-compute',{'subject_refs':[rr('model_version','fictional-orbit-1')],'resource_kind':'training_compute','measurement':measure({'kind':'upper_bound','bound':'1200000000000000000000000','inclusive':True,'unit':'FLOP'},'FLOP',mode='estimated',key='training-flop-v1',definition='Total fictional pretraining floating-point operations; estimates depend on omitted hardware utilization.'),'scope':'One fictional pretraining run; excludes experiments, post-training and inference.'},event=day('2026-09-03'))
cost=record('resource_observation','fictional-training-cost',{'subject_refs':[rr('model_version','fictional-orbit-1')],'resource_kind':'training_cost','measurement':measure(point('1500000.00','currency_nominal'),'currency_nominal',mode='estimated',key='training-cost-v1',definition='Fictional compute bill; excludes salaries and failed experiments.'),'scope':'One fictional run.','currency_basis':{'currency':'CNY','price_basis':'nominal','conversion_method':'Original fictional CNY amount; no exchange-rate conversion applied.'}},event=day('2026-09-03'))
safety=record('safety_evaluation','fictional-safety',{'model_ref':rr('model_version','fictional-orbit-1'),'evaluator_refs':[rr('actor','fictional-lab')],'risk_domain':'robustness','protocol':protocol,'measurement':measure(point('0.08','ratio'),'ratio',key='fictional-policy-failure-rate-v1',definition='Failures divided by 100 fictional benign robustness test cases.',minimum='0',maximum='1'),'threshold':point('0.10','ratio'),'conclusion':'Fictional result lies below this fictional protocol threshold; no real safety conclusion follows.','limitations':'Synthetic values cannot establish real-world safety or catastrophe risk.','disclosure_level':'summary_only'},evaluated=day('2026-09-10'))
incident=record('incident','fictional-routing-error',{'title':'Fictional automated routing error','subject_refs':[rr('model_version','fictional-orbit-1')],'incident_kind':'fixture:service_error-v1','verification':'alleged','causal_attribution':'unestablished','severity':'unknown','severity_rubric':'fixture-only-v1','description':'A made-up service routed a made-up request incorrectly. No real person or event is described.','deduplication_key':'fictional-routing-error-2026-09'},event=day('2026-09-18'))
statement=record('statement','fictional-probability',{'speaker_refs':[rr('actor','fictional-analyst')],'statement_type':'explicit_numeric','original_text':'这是虚构示例：达到指定标准的概率是 20%。','language':'zh-Hans','normalized_text':'Fictional statement: a 20% probability of reaching the specified milestone by 2030.','topic_keys':['capabilities:v1'],'translation_ref':rr('source_artifact','fictional-translation'),'relationships':[]},event=day('2026-09-15'))
question=record('forecast_question','fictional-milestone',{'question_key':'fictional_milestone_by_2030_v1','question_text':'Will the precisely specified fictional milestone occur by 31 December 2030?','event_family':'capability','outcome_definition':'At least 90 correct answers on the fixed FictionalCheck v2 test under the declared no-tools protocol. This is not an AGI or catastrophe definition.','population':'One fictional model family under one frozen evaluation protocol.','conditioning':'unconditional','horizon':day('2030-12-31'),'answer_domain':'probability','answer_unit':'probability','resolution_rule':'A fictional independent evaluator publishes a qualifying run before 2031-01-01T00:00:00Z; missing evidence remains ambiguous rather than false.','resolution_policy':'judgment_required'})
forecast=record('forecast','fictional-probability',{'question_ref':rr('forecast_question','fictional-milestone'),'forecaster_refs':[rr('actor','fictional-analyst')],'statement_ref':rr('statement','fictional-probability'),'forecast_origin':'explicit_numeric','elicitation_method':'statement','answer':point('0.20','probability'),'as_of':day('2026-09-15'),'aggregation':'none'})
aggregate=record('forecast','fictional-survey-median',{'question_ref':rr('forecast_question','fictional-milestone'),'forecaster_refs':[rr('actor','fictional-panel')],'forecast_origin':'explicit_numeric','elicitation_method':'survey','answer':point('0.35','probability'),'as_of':{'kind':'range','start':'2026-09-01','end':'2026-09-20','precision':'uncertain'},'aggregation':'source_aggregate','aggregation_method':'Median of 100 fictional respondents answering the exact same question. No independence, calibration or representativeness is asserted.','aggregate_context':{'population_ref':rr('actor','fictional-panel'),'aggregator_ref':rr('actor','fictional-lab'),'wave':'synthetic-2026-09-wave1','sample_size':100,'sampling_notes':'Fictional volunteer sample. Nonresponse is unspecified; no individual answers are available.'}})
aggregate['upstream_refs']=[{'dataset_id':'fictional-survey-results','release':'synthetic-2026-09-wave1','record_id':'wave1/question1/median','schema_name':'fictional-survey-table','schema_version':'fixture-1','schema_url':'https://example.invalid/fictional-survey/schema-v1','source_ref':rr('source_artifact','fictional-original'),'transformations':[{'operation':'percent_to_probability','version':'fixture-transform-1','description':'Fictional upstream median of 35 percent divided exactly by 100 to produce 0.35. Original question, wave and collective are retained.'}]}]
timeline_question=record('forecast_question','fictional-timeline',{'question_key':'fictional_milestone_year_v1','question_text':'In which year will the specified fictional milestone first occur?','event_family':'capability','outcome_definition':question['data']['outcome_definition'],'population':question['data']['population'],'conditioning':'unconditional','horizon':unknown('No terminal horizon was stated; do not infer one.'),'answer_domain':'date','resolution_rule':'Use the date of the first independently documented qualifying fictional run; never-happens mass is not specified.','resolution_policy':'judgment_required'})
timeline=record('forecast','fictional-timeline',{'question_ref':rr('forecast_question','fictional-timeline'),'forecaster_refs':[rr('actor','fictional-analyst')],'forecast_origin':'explicit_numeric','elicitation_method':'statement','answer':{'kind':'quantiles','unit':'calendar_year','quantiles':[{'q':'0.1','value':'2030'},{'q':'0.5','value':'2040'},{'q':'0.9','value':'2060'}]},'as_of':day('2026-09-15'),'aggregation':'none'})
resolution=record('resolution','fictional-open',{'question_ref':rr('forecast_question','fictional-milestone'),'status':'open','adjudicator_refs':[],'rationale':'The fictional deadline has not passed. There is no observed outcome and no public score.'})
# Revision example shows correction history, not overwriting a prior model identity.
revision=copy.deepcopy(incident)
revision['revision']=2
revision['supersedes']=rr('incident','fictional-routing-error')
revision['times']['known_at']='2026-10-01T12:00:00Z'
revision['times']['retrieved_at']='2026-10-01T12:00:00Z'
revision['governance']['reviewed_at']='2026-10-01T13:00:00Z'
revision['data']['verification']='disputed'
revision['data']['description']+=' A later fictional review disputes the original allegation.'
records=[source,translation,lab,analyst,collective,model,release,benchmark,compute,cost,safety,incident,statement,question,forecast,aggregate,timeline_question,timeline,resolution,revision]
snapshot=record('snapshot','fictional-as-known',{'snapshot_kind':'as_known','cutoff':'2026-10-01T23:59:59Z','created_at':'2026-10-02T00:00:00Z','members':[{'record_ref':{'id':r['id'],'revision':r['revision']},'sha256':digest(r)} for r in records],'canonicalization':'python-json-sort-utf8-v1','notice':'All records are fictional fixtures. Closed history includes the original and disputed incident revisions; consumers must select revisions explicitly. No operational collection or valid scientific finding is represented.'})
snapshot['times']['known_at']='2026-10-02T00:00:00Z'
snapshot['times']['retrieved_at']='2026-10-02T00:00:00Z'
snapshot['governance']['reviewed_at']='2026-10-02T00:00:00Z'
records.append(snapshot)
bundle={'schema_version':'0.1.0','dataset_id':'synthetic-contract-demo-2026-10-07','dataset_kind':'synthetic','generated_at':'2026-10-02T00:00:00Z','records':records}
(ROOT/'examples/synthetic_dataset.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'examples/synthetic_records.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in records),encoding='utf-8')
print(f'Wrote {len(records)} fictional records across {len(set(r["record_type"] for r in records))} types.')
