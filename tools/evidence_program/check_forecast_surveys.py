"""Offline consistency gates for the forecast/survey review and LEAP ledger."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from read_leap_aggregates import read_fixture, digest, GROUPS, INSTRUMENT_SHA256

REVIEWED_CATALOG_SHA256 = '6637bacfbee3dcb62c145819a4d8a29fb08c24c6b3b7202c76b672916baa7898'
FIXTURE_SHA256 = '96179dd430710539c687a6122df198736748673bba550b3020889d852a9a0324'
BASE = '71df61f85bd8534f8fe95180cc13c9e31ded687c'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check_catalog(catalog, inventory_hash, markdown, root):
    require(digest(catalog) == REVIEWED_CATALOG_SHA256, 'Reviewed catalog semantics changed; explicit review and fingerprint update required')
    require(catalog['schema_version'] == 'forecast-surveys-review/1.0.0' and catalog['repository_review_commit'] == BASE, 'Exact schema/base')
    require(catalog['status'] == 'curated_research_not_admitted' and catalog['operational_admission'] == 'not_admitted', 'Admission gate')
    require(catalog['collector_enabled'] is False and catalog['source_code_execution'] is False and catalog['respondent_data_acquired'] is False, 'No collection/execution/respondent records')
    require(catalog['original_report_count'] == 1 and catalog['collection_count'] == 7, 'Seven collections/one report')
    require(catalog['baseline_inventory']['source_family_count'] == 64 and catalog['baseline_inventory']['sha256'] == inventory_hash, 'Frozen inventory drift')
    require(not {'records','observations','pdoom','pooled_forecast','total_participants'} & catalog.keys(), 'Research catalog is not canonical or pooled observations')
    cs = catalog['collections']; require([c['candidate_id'] for c in cs] == ['FS%03d'%i for i in range(1,8)], 'Candidate identity/order')
    require([c['inventory_source_id'] for c in cs] == ['GL010','GL011','GL038',None,None,None,None], 'Three enrichments/four new named collections')
    ids=set(); findings=0
    for c in cs:
        require(c['collector_enabled'] is False and c['operational_admission'] == 'not_admitted', 'Collection gate')
        for k in ('name','source_family_id','historical_coverage','update_frequency','access_export','measurement_regime','population'):
            require(isinstance(c[k],str) and c[k].strip(), 'Scope field required')
        require(len(c['limitations'])>=4 and c['sample_record'] and c['denominators'] and c['version_relationships'], 'Sample/denominator/lineage/limits required')
        own={a['artifact_id']for a in c['artifacts']};require(len(own)==len(c['artifacts']) and not own&ids, 'Artifact identity');ids|=own
        for a in c['artifacts']:
            u=urlsplit(a['url']);require(u.scheme=='https' and u.hostname and not u.username and not u.password and not any(ch.isspace()for ch in a['url']), 'Source URL')
            require(a['source_bytes_vendored'] is False and a['rights_status'] and a['rights_scope'] and a['access_status'] and a['evidence_locator'], 'Artifact-specific rights/access')
            require(a['url'] in markdown,'Source link parity')
            for k,n in [('git_commit',40),('git_blob_sha',40),('sha256',64)]:
                require(a[k] is None or re.fullmatch('[0-9a-f]{%d}'%n,a[k]),'Source pin')
            require(a['sha256'] is None or a['sha256_basis'] in ('exact_downloaded_html_body','exact_bytes_confirmed_by_git_blob'),'Honest byte-hash scope')
        for f in c['findings']:
            require(f['claim'] and f['qualification'] and set(f['evidence_artifact_ids'])<=own and f['evidence_artifact_ids'],'Finding provenance')
            require(f['claim']+' '+f['qualification'] in markdown,'Qualified finding parity')
        findings+=len(c['findings'])
    require(len(ids)==42 and findings==60,'Reviewed evidence coverage')
    require(dict(re.findall(r'^## (FS[0-9]{3}) (.+)$',markdown,re.M))=={c['candidate_id']:c['name']for c in cs},'Guide candidate headings')
    ov=catalog['overlap_review']
    require((ov['frozen_inventory_count'],ov['prior_catalog_count'],ov['prior_collection_count'],ov['prior_artifact_count'],ov['candidate_by_catalog_assessment_count'])==(64,14,74,538,98),'Complete baseline comparison counts')
    require(len(ov['catalogs'])==14 and all(set(x['candidate_checks'])=={c['candidate_id']for c in cs}for x in ov['catalogs']),'Complete comparison cells')
    pins=catalog['prior_catalog_fingerprints'];require(len(pins)==14,'Prior catalogs')
    for pin in pins:
        rel=pin['path'];require(rel.startswith('data/evidence-program/research/') and '..'not in Path(rel).parts,'Catalog path')
        raw=(root/rel).read_bytes();require(hashlib.sha256(raw).hexdigest()==pin['sha256'],'Prior catalog unchanged')
        require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==pin['git_blob_sha'],'Prior Git blob')
    impl=catalog['implementation'];require(impl['status']=='implemented_offline_manual_licensed_aggregate_ledger','Honest implementation boundary')
    require((impl['fixture_records'],impl['max_bytes'],impl['max_manifest_bytes'],impl['max_json_nodes'],impl['max_json_depth'],impl['max_decimal_token_characters'])==(4,32768,8192,1000,12,32),'Bounded selected input')
    require(impl['fixture_sha256']==FIXTURE_SHA256 and impl['original_page_sha256']!=FIXTURE_SHA256 and impl['original_page_bytes']==600997,'Original/derivative distinction')
    require(impl['network_calls']==0 and impl['model_calls']==0 and all(impl[k] is False for k in ['original_page_vendored','source_extraction_implemented','source_execution','collector_enabled','canonical_import']),'No execution/live import')
    require(len(catalog['corrections'])==18 and len(catalog['holds'])==8 and len(catalog['next_actions'])==10 and len(catalog['follow_up_prompts'])==8,'Actions and corrections')
    require([a['status']for a in catalog['next_actions'][:2]]==['completed_bounded_review','completed_offline_implementation'] and all(a['status']=='held_documentary_review'for a in catalog['next_actions'][2:]),'Completed versus held work')
    for p in catalog['follow_up_prompts']:
        require(p['status']=='prepared_not_dispatched' and p['prompt']in markdown,'Prompt parity/state')
        require(all(k in p['prompt']for k in ('Read-only','Stop','No login','artifact-specific rights','respondent CSV/Sheet','generic p(doom) conversion')),'Self-contained bounded prompt')
    return dict(forecast_surveys_collections=7,forecast_surveys_artifact_references=42,forecast_surveys_qualified_findings=60,forecast_surveys_follow_up_prompts=8,forecast_surveys_next_actions=10,forecast_surveys_prior_catalogs_compared=14,forecast_surveys_overlap_comparison_cells=98,forecast_surveys_unadmitted_collections=7)


def check_fixtures(root):
    f=root/'tools/evidence_program/tests/fixtures/forecast-surveys'
    raw=(f/'leap-wave12-catastrophe2050.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==FIXTURE_SHA256,'Reviewed fixture changed')
    d=json.loads(raw);require(digest(d['instrument'])==INSTRUMENT_SHA256,'Instrument drift')
    out=read_fixture(f);rows=out['records']
    require([r['group_label']for r in rows]==list(GROUPS),'Publisher group labels')
    require([(r['median_percent'],r['q25_percent'],r['q75_percent'],r['reported_n'])for r in rows]==[('2','0.9','7',157),('5','2','13',540),('1.6','0.3','3.3',49),('5.2','2','19',132)],'Published value fidelity')
    require([r['probability_median']for r in rows]==['0.02','0.05','0.016','0.052'],'Exact normalization')
    require(out['wave_counts']['derived_expert_category_sum']==149,'Keep discrepancy')
    for name in ('forecast-surveys','agent-security-incidents'):
        attributes=(root/'tools/evidence_program/tests/fixtures'/name/'.gitattributes').read_text()
        require('*.json text eol=lf' in attributes, 'Byte-pinned JSON requires explicit LF checkout')
    notice=(f/'NOTICE.md').read_text();require(all(x in notice for x in ['Forecasting Research Institute','CC BY 4.0','not relicensed','not an HTML extractor','Original HTML is not vendored','600,997']),'Attribution, scope and transformation notice')
    return dict(forecast_surveys_licensed_aggregate_fixtures=1,forecast_surveys_published_group_summaries=4,forecast_surveys_source_html_extractors=0,forecast_surveys_respondent_files=0,forecast_surveys_pooled_forecasts=0)
