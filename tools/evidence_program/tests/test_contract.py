#!/usr/bin/env python3
"""Executable positive and negative regression cases; all data is synthetic."""
import copy
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from validate_dataset import validate_bundle, check_contracts, digest, Draft202012Validator, FORMAT_CHECKER
BASE=json.loads((ROOT/'examples/synthetic_dataset.json').read_text(encoding='utf-8'))

def base(snapshot=False):
    b=copy.deepcopy(BASE)
    if not snapshot:b['records']=[r for r in b['records'] if r['record_type']!='snapshot']
    return b

def get(b,typ,slug=None,rev=None):
    return next(r for r in b['records'] if r['record_type']==typ and (slug is None or r['id'].endswith(':'+slug)) and (rev is None or r['revision']==rev))

def rr(r):return {'id':r['id'],'revision':r['revision']}

class ContractTests(unittest.TestCase):
    def valid(self,b):self.assertEqual(validate_bundle(b),[])
    def invalid(self,b,code):
        errors=validate_bundle(b)
        self.assertIn(code,{e['code'] for e in errors},json.dumps(errors,ensure_ascii=False,indent=2))
    def test_full_linked_fixture(self):self.valid(BASE)
    def test_all_schemas_and_standalone_wrappers(self):
        docs,registry=check_contracts()
        self.assertEqual(len(docs),14)
        by_type={d['$id'].rsplit('/',1)[-1].removesuffix('.schema.json'):d for d in docs}
        for record in BASE['records']:
            Draft202012Validator(by_type[record['record_type']],registry=registry,format_checker=FORMAT_CHECKER).validate(record)
    def test_record_wrappers_reject_wrong_type(self):
        docs,registry=check_contracts()
        source=next(d for d in docs if d['$id'].endswith('/source_artifact.schema.json'))
        self.assertTrue(list(Draft202012Validator(source,registry=registry).iter_errors(get(BASE,'actor'))))
    def test_positive_numeric_value_shapes(self):
        values=[{'kind':'point','value':'0.2','unit':'probability'},
          {'kind':'interval','lower':'0.1','upper':'0.3','interval_kind':'reported_range','unit':'probability'},
          {'kind':'interval','lower':'0.1','upper':'0.3','interval_kind':'credible','level':'0.90','unit':'probability'},
          {'kind':'lower_bound','bound':'0.1','inclusive':False,'unit':'probability'},
          {'kind':'upper_bound','bound':'0.3','inclusive':True,'unit':'probability'},
          {'kind':'quantiles','unit':'probability','quantiles':[{'q':'0.1','value':'0.1'},{'q':'0.9','value':'0.3'}]},
          {'kind':'missing','reason':'not_reported'}]
        for v in values:
            with self.subTest(kind=v['kind']):
                b=base();get(b,'forecast','fictional-probability')['data']['answer']=v;self.valid(b)
    def test_positive_date_precisions(self):
        values=[{'kind':'date_point','date':'2040-06-01'},
          {'kind':'date_quantiles','quantiles':[{'q':'0.1','date':'2030-01-01'},{'q':'0.9','date':'2060-01-01'}]},
          {'kind':'point','value':'2040','unit':'calendar_year'},
          {'kind':'interval','lower':'2040','upper':'2050','unit':'calendar_year','interval_kind':'reported_range'},
          {'kind':'lower_bound','bound':'2040','inclusive':False,'unit':'calendar_year'}]
        for v in values:
            with self.subTest(kind=v['kind']):
                b=base();get(b,'forecast','fictional-timeline')['data']['answer']=v;self.valid(b)
    def test_positive_unknown_forecast_time_outside_as_known(self):
        b=base();get(b,'forecast','fictional-probability')['data']['as_of']={'kind':'unknown','reason':'Source omits forecast date.'};self.valid(b)
    def test_positive_qualitative(self):
        b=base();f=get(b,'forecast','fictional-probability');q=get(b,'forecast_question','fictional-milestone');st=get(b,'statement')
        f['data']['forecast_origin']='explicit_qualitative';f['data']['answer']={'kind':'category','label':'unlikely','vocabulary':'source_verbatim'}
        st['data']['statement_type']='explicit_qualitative';q['data']['answer_domain']='qualitative';del q['data']['answer_unit']
        # Aggregate still answers its original probability question; remove it for this isolated case.
        b['records']=[r for r in b['records'] if not r['id'].endswith(':fictional-survey-median')]
        self.valid(b)
    def test_positive_resolved_binary_case(self):
        b=base();r=get(b,'resolution');r['data'].update(status='resolved',outcome={'kind':'boolean','value':True},resolved_at='2026-09-29T12:00:00Z',adjudicator_refs=[rr(get(b,'actor','fictional-analyst'))])
        r['governance'].update(review_state='human_verified',reviewer_ref=rr(get(b,'actor','fictional-analyst')))
        self.valid(b) # Structural admissibility is not factual proof that the milestone happened.
    def test_positive_constant_currency(self):
        b=base();r=get(b,'resource_observation','fictional-training-cost')['data'];r['measurement']['metric']['unit']='currency_constant';r['measurement']['result']['unit']='currency_constant';r['currency_basis'].update(price_basis='constant',base_year=2025);self.valid(b)
    def test_reject_number_for_exact_decimal(self):
        b=base();get(b,'forecast')['data']['answer']['value']=0.2;self.invalid(b,'schema')
    def test_reject_nonfinite_decimal(self):
        b=base();get(b,'forecast')['data']['answer']['value']='NaN';self.invalid(b,'schema')
    def test_reject_extra_property(self):
        b=base();get(b,'forecast')['data']['guessed_probability']='0.7';self.invalid(b,'schema')
    def test_reject_impossible_date(self):
        b=base();get(b,'forecast')['data']['as_of']={'kind':'date','date':'2026-02-30'};self.invalid(b,'schema')
    def test_reject_timestamp_without_zone(self):
        b=base();get(b,'forecast')['times']['known_at']='2026-09-30T12:00:00';self.invalid(b,'schema')
    def test_reject_probability_over_one(self):
        b=base();get(b,'forecast')['data']['answer']['value']='20';self.invalid(b,'probability_range')
    def test_reject_negative_resource(self):
        b=base();get(b,'resource_observation')['data']['measurement']['result']['bound']='-1';self.invalid(b,'unit_range')
    def test_reject_reversed_value_interval(self):
        b=base();r=get(b,'benchmark_run')['data']['measurement']['result'];r['lower']='0.9';r['upper']='0.1';self.invalid(b,'value_range')
    def test_reject_unlabeled_confidence(self):
        b=base();del get(b,'benchmark_run')['data']['measurement']['result']['level'];self.invalid(b,'interval_level')
    def test_reject_level_on_reported_range(self):
        b=base();get(b,'benchmark_run')['data']['measurement']['result']['interval_kind']='reported_range';self.invalid(b,'interval_level')
    def test_reject_invalid_confidence_level(self):
        b=base();get(b,'benchmark_run')['data']['measurement']['result']['level']='1';self.invalid(b,'interval_level')
    def test_reject_quantile_order(self):
        b=base();get(b,'forecast','fictional-timeline')['data']['answer']['quantiles'][1]['q']='0.1';self.invalid(b,'quantile_order')
    def test_reject_quantile_values(self):
        b=base();get(b,'forecast','fictional-timeline')['data']['answer']['quantiles'][1]['value']='2020';self.invalid(b,'quantile_monotonicity')
    def test_reject_fractional_year(self):
        b=base();get(b,'forecast','fictional-timeline')['data']['answer']['quantiles'][1]['value']='2040.5';self.invalid(b,'integer_unit')
    def test_reject_metric_result_unit_mismatch(self):
        b=base();get(b,'benchmark_run')['data']['measurement']['result']['unit']='probability';self.invalid(b,'metric_unit')
    def test_reject_metric_scale_exceedance(self):
        b=base();get(b,'benchmark_run')['data']['measurement']['metric']['maximum']='0.5';self.invalid(b,'metric_scale')
    def test_reject_missing_currency_basis(self):
        b=base();del get(b,'resource_observation','fictional-training-cost')['data']['currency_basis'];self.invalid(b,'currency_basis')
    def test_reject_missing_constant_currency_year(self):
        b=base();r=get(b,'resource_observation','fictional-training-cost')['data'];r['measurement']['metric']['unit']='currency_constant';r['measurement']['result']['unit']='currency_constant';r['currency_basis']['price_basis']='constant';self.invalid(b,'currency_basis')
    def test_reject_dangling_reference(self):
        b=base();get(b,'forecast')['data']['question_ref']['revision']=99;self.invalid(b,'missing_reference')
    def test_reject_reference_wrong_type(self):
        b=base();get(b,'forecast')['data']['question_ref']=rr(get(b,'actor'));self.invalid(b,'reference_type')
    def test_reject_duplicate_revision(self):
        b=base();b['records'].append(copy.deepcopy(b['records'][0]));self.invalid(b,'duplicate_revision')
    def test_reject_id_record_type_mismatch(self):
        b=base();get(b,'forecast')['id']='urn:pdataset:actor:wrong-type';self.invalid(b,'schema')
    def test_reject_cross_entity_supersedes(self):
        b=base();get(b,'incident',rev=2)['supersedes']=rr(get(b,'model_version'));self.invalid(b,'revision_lineage')
    def test_reject_nonmonotone_revision_time(self):
        b=base();get(b,'incident',rev=2)['times']['known_at']=get(b,'incident',rev=1)['times']['known_at'];get(b,'incident',rev=2)['times']['retrieved_at']=get(b,'incident',rev=1)['times']['retrieved_at'];self.invalid(b,'revision_time')
    def test_reject_synthetic_live_mix(self):
        b=base();b['records'][0]['synthetic']=False;self.invalid(b,'mixed_synthetic')
    def test_reject_future_reference(self):
        b=base();get(b,'forecast_question')['times']['known_at']='2026-10-01T12:00:00Z';self.invalid(b,'future_reference')
    def test_reject_retrieval_after_known(self):
        b=base();get(b,'forecast')['times']['retrieved_at']='2026-10-01T12:00:00Z';self.invalid(b,'time_order')
    def test_reject_reversed_temporal_range(self):
        b=base();get(b,'forecast','fictional-survey-median')['data']['as_of']['end']='2026-08-01';self.invalid(b,'time_range')
    def test_reject_future_forecast_time(self):
        b=base();get(b,'forecast')['data']['as_of']={'kind':'date','date':'2026-10-01'};self.invalid(b,'forecast_time')
    def test_reject_translation_chain(self):
        b=base();r=get(b,'source_artifact','fictional-translation');r['data']['translation']['original_ref']=rr(r);self.invalid(b,'translation_lineage')
    def test_reject_missing_collective_definition(self):
        b=base();del get(b,'actor','fictional-panel')['data']['collective'];self.invalid(b,'collective_identity')
    def test_reject_publisher_as_respondents(self):
        b=base();get(b,'forecast','fictional-survey-median')['data']['forecaster_refs']=[rr(get(b,'actor','fictional-lab'))];self.invalid(b,'aggregate_attribution')
    def test_reject_organization_as_collective_population(self):
        b=base();r=get(b,'forecast','fictional-survey-median')['data'];r['aggregate_context']['population_ref']=rr(get(b,'actor','fictional-lab'));r['forecaster_refs']=[r['aggregate_context']['population_ref']];self.invalid(b,'aggregate_population')
    def test_reject_missing_aggregate_context(self):
        b=base();del get(b,'forecast','fictional-survey-median')['data']['aggregate_context'];self.invalid(b,'aggregate_context')
    def test_reject_incompatible_question_unit(self):
        b=base();get(b,'forecast')['data']['answer']['unit']='percent';self.invalid(b,'answer_domain')
    def test_reject_qualitative_precision(self):
        b=base();get(b,'forecast')['data']['forecast_origin']='explicit_qualitative';self.invalid(b,'invented_precision')
    def test_reject_open_resolution_with_outcome(self):
        b=base();get(b,'resolution')['data']['outcome']={'kind':'boolean','value':False};self.invalid(b,'resolution_state')
    def test_reject_resolved_without_human_review(self):
        b=base();get(b,'resolution')['data'].update(status='resolved',outcome={'kind':'boolean','value':False},resolved_at='2026-09-29T00:00:00Z');self.invalid(b,'resolution_review')
    def test_reject_unreviewed_publication(self):
        b=base();get(b,'statement')['governance']['publication_state']='eligible';self.invalid(b,'publication_gate')
    def test_reject_text_metadata_only_publication(self):
        b=base();r=get(b,'statement');r['governance'].update(publication_state='eligible',rights_state='metadata_only',review_state='human_verified',reviewer_ref=rr(get(b,'actor','fictional-analyst')));self.invalid(b,'content_rights')
    def test_reject_human_review_without_person(self):
        b=base();get(b,'statement')['governance'].update(review_state='human_verified',reviewer_ref=rr(get(b,'actor','fictional-lab')));self.invalid(b,'human_reviewer')
    def test_reject_review_state_without_time(self):
        b=base();del get(b,'statement')['governance']['reviewed_at'];self.invalid(b,'review_timestamp')
    def test_reject_missing_eval_time_for_full_reproducibility(self):
        b=base();r=get(b,'benchmark_run');r['times']['evaluated']={'kind':'unknown','reason':'Not reported.'};r['data']['protocol']['reproducibility']='full';self.invalid(b,'evaluation_time')
    def test_reject_snapshot_hash_mutation(self):
        b=base(True);get(b,'statement')['data']['normalized_text']+=' Changed.';self.invalid(b,'snapshot_hash')
    def test_reject_snapshot_unclosed_set(self):
        b=base(True);s=get(b,'snapshot');s['data']['members']=[m for m in s['data']['members'] if m['record_ref']['id']!=get(b,'source_artifact','fictional-original')['id']];self.invalid(b,'snapshot_closure')
    def test_reject_snapshot_future_knowledge(self):
        b=base(True);get(b,'snapshot')['data']['cutoff']='2026-09-29T23:59:59Z';self.invalid(b,'snapshot_cutoff')
    def test_reject_snapshot_future_review(self):
        b=base(True);get(b,'snapshot')['data']['cutoff']='2026-10-01T12:30:00Z';self.invalid(b,'snapshot_review')
    def test_reject_snapshot_unknown_forecast_time(self):
        b=base(True);get(b,'forecast')['data']['as_of']={'kind':'unknown','reason':'Unknown.'};self.invalid(b,'snapshot_forecast_time')
    def test_positive_signed_economic_change(self):
        b=base();r=get(b,'resource_observation','fictional-training-cost')['data']
        r['resource_kind']='investment';r['scope']='Quarterly change in fictional net investment.'
        r['measurement']['metric']['key']='net-investment-change-v1';r['measurement']['metric']['definition']='Signed quarter-on-quarter change in fictional net investment.'
        r['measurement']['result']['value']='-125000.00';self.valid(b)
    def test_positive_signed_percent_change(self):
        b=base();r=get(b,'resource_observation','fictional-training-cost')['data']
        del r['currency_basis'];r['resource_kind']='productivity';r['measurement']['metric']['unit']='percent_change';r['measurement']['result']={'kind':'point','value':'-12.5','unit':'percent_change'};self.valid(b)
    def test_positive_fractional_expected_token_count(self):
        b=base();r=get(b,'resource_observation')['data']['measurement'];r['metric']['unit']='token';r['metric']['definition']='Mean tokens per fictional response; fractional means are meaningful.';r['result']={'kind':'point','value':'120.5','unit':'token'};self.valid(b)
    def test_reject_forecaster_not_linked_speaker(self):
        b=base();get(b,'forecast','fictional-probability')['data']['forecaster_refs']=[rr(get(b,'actor','fictional-lab'))];self.invalid(b,'statement_attribution')
    def test_reject_collective_without_aggregate_context(self):
        b=base();f=get(b,'forecast','fictional-survey-median')['data'];f['aggregation']='none';del f['aggregate_context'];del f['aggregation_method'];self.invalid(b,'collective_aggregate')
    def test_reject_translation_original_not_cited(self):
        b=base();get(b,'statement')['evidence'][0]['source_ref']=rr(get(b,'source_artifact','fictional-translation'));self.invalid(b,'translation_evidence')
    def test_reject_empty_strict_probability_bounds(self):
        for kind, bound in [('lower_bound','1'),('upper_bound','0')]:
            with self.subTest(kind=kind):
                b=base();get(b,'forecast')['data']['answer']={'kind':kind,'bound':bound,'inclusive':False,'unit':'probability'};self.invalid(b,'empty_bound')
    def test_reject_empty_strict_metric_bound(self):
        b=base();r=get(b,'benchmark_run')['data']['measurement'];r['result']={'kind':'lower_bound','bound':'1','inclusive':False,'unit':'ratio'};self.invalid(b,'empty_bound')
    def test_reject_submicrosecond_timestamp(self):
        b=base();get(b,'forecast')['times'].update(retrieved_at='2026-09-30T12:00:00.0000009Z',known_at='2026-09-30T12:00:00.0000001Z');self.invalid(b,'schema')
    def test_cli_malformed_root_is_json_error_report(self):
        for value in [[], None, {'records':0}]:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'bad.json';path.write_text(json.dumps(value))
                result=subprocess.run([sys.executable,str(ROOT/'validate_dataset.py'),str(path)],capture_output=True,text=True)
                self.assertEqual(result.returncode,1,result.stderr)
                report=json.loads(result.stdout);self.assertFalse(report['valid']);self.assertEqual(report['records'],0);self.assertEqual(report['errors'][0]['code'],'schema')
    def test_positive_upstream_crosswalk_and_transform(self):
        b=base();r=get(b,'forecast','fictional-survey-median')
        self.assertEqual(r['upstream_refs'][0]['record_id'],'wave1/question1/median');self.valid(b)
    def test_reject_upstream_missing_original_record_id(self):
        b=base();del get(b,'forecast','fictional-survey-median')['upstream_refs'][0]['record_id'];self.invalid(b,'schema')
    def test_reject_upstream_blank_schema_version(self):
        b=base();get(b,'forecast','fictional-survey-median')['upstream_refs'][0]['schema_version']='';self.invalid(b,'schema')
    def test_dictionary_covers_core_fields(self):
        d=json.loads((ROOT/'contracts/field_dictionary.json').read_text(encoding='utf-8'))
        names={r['field'] for r in d['fields']}
        self.assertIn('forecast_data.aggregate_context.population_ref',names)
        self.assertIn('times.known_at',names)

if __name__=='__main__':unittest.main(verbosity=2)
