"""Offline review consistency for labor-market candidates and one licensed slice."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from read_eurostat_ict_training import read_fixture, DIMENSIONS, SOURCE_URL

REVIEWED_CATALOG_SHA256 = 'ad50005f8744b2c694579d1a5a2b99540bf18838b32acfc4660f5ad119fd0f65'
FIXTURE_SHA256 = 'dab0f8f8f445839ac883543729ebb006118de10dc5893b9a1bed77bddf640c61'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check_catalog(catalog, inventory_hash, markdown, root):
    semantic=hashlib.sha256(json.dumps(catalog,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    require(semantic==REVIEWED_CATALOG_SHA256,'Reviewed semantics changed; explicit source review and fingerprint refresh required')
    require(catalog['schema_version']=='labor-market-review/1.0.0','Schema version')
    require(catalog['repository_review_commit']=='ab1434f30114df6784409d84069e9a8f785a45b1','Exact baseline')
    require(catalog['status']=='curated_research_not_admitted' and catalog['operational_admission']=='not_admitted' and catalog['collector_enabled'] is False and catalog['source_code_execution'] is False,'Admission/execution gate')
    require(catalog['original_report_count']==1 and catalog['collection_count']==4,'One report/four collections')
    require(catalog['baseline_inventory']['source_family_count']==64 and catalog['baseline_inventory']['sha256']==inventory_hash,'Frozen64 drift')
    require(not {'records','observations','pdoom','exposure_score'}&catalog.keys(),'Catalog is not observed data or a score')
    cs=catalog['collections'];require([c['candidate_id']for c in cs]==['LM001','LM002','LM003','LM004'],'Identity/order')
    require([c['inventory_source_id']for c in cs]==[None,None,'GL022',None],'Three new families/one enrichment')
    aids=set();findings=0
    for c in cs:
        require(c['operational_admission']=='not_admitted' and c['collector_enabled'] is False,'Source admission')
        require(len(c['limitations'])>=4 and c['artifacts'] and c['findings'],'Evidence/limitations')
        for key in ['name','source_family_id','historical_coverage','update_frequency','access_export','measurement_regime','population']:
            require(isinstance(c[key],str) and c[key].strip(),'Required scope field')
        own={a['artifact_id']for a in c['artifacts']};require(len(own)==len(c['artifacts']) and not own&aids,'Unique artifacts');aids|=own
        for a in c['artifacts']:
            url=urlsplit(a['url']);require(url.scheme=='https' and url.hostname and not url.username and not url.password,'Safe source URL')
            require(a['rights_status'] and a['rights_scope'] and a['evidence_locator'] and a['access_status'],'Source rights/access/locator')
            require(a['source_bytes_vendored']==(a['artifact_id']=='lm003_slice'),'Only one licensed source fixture')
            for key,n in [('git_commit',40),('git_blob_sha',40),('sha256',64)]:
                require(a[key] is None or re.fullmatch('[0-9a-f]{%d}'%n,a[key]),'Artifact pin')
            require(a['url'] in markdown,'Guide artifact link parity')
        for f in c['findings']:
            require(f['claim'] and f['qualification'] and f['evidence_artifact_ids'] and set(f['evidence_artifact_ids'])<=own,'Finding evidence')
            require(f['claim']+' '+f['qualification'] in markdown,'Guide finding parity')
        findings+=len(c['findings'])
    require(dict(re.findall(r'^## (LM[0-9]{3}) (.+)$',markdown,re.M))=={c['candidate_id']:c['name']for c in cs},'Guide headings')
    ov=catalog['overlap_review'];require((ov['frozen_inventory_count'],ov['prior_catalog_count'],ov['prior_collection_count'],ov['prior_artifact_count'],ov['candidate_by_catalog_assessment_count'])==(64,13,70,505,65),'Overlap count')
    require(len(ov['catalogs'])==13 and all(set(x['candidate_checks'])=={'LM001','LM002','LM003','LM004','LM-H01'}for x in ov['catalogs']),'Complete comparison matrix')
    pins=catalog['prior_catalog_fingerprints'];require(len(pins)==13,'Prior fingerprints')
    for p in pins:
        rel=p['path'];require(rel.startswith('data/evidence-program/research/') and '..'not in Path(rel).parts,'Prior path')
        raw=(root/rel).read_bytes();require(hashlib.sha256(raw).hexdigest()==p['sha256'],'Prior catalog drift')
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();require(blob==p['git_blob_sha'],'Prior blob drift')
    held=catalog['held_candidates'];require(len(held)==1 and held[0]['inventory_source_id']=='GL023' and held[0]['related_prior_candidate']=='AP005' and held[0]['status']=='held_documentary_follow_up_not_fifth_collection','BTOS hold')
    impl=catalog['implementation'];require(impl['status']=='implemented_offline_licensed_aggregate_fixture' and impl['selected_dimensions']==DIMENSIONS and impl['source_url']==SOURCE_URL,'Implementation scope')
    require((impl['max_bytes'],impl['max_manifest_bytes'],impl['max_json_nodes'],impl['max_json_depth'],impl['max_cells'])==(32768,4096,4000,16,13),'Input bounds')
    require(impl['network_calls']==0 and impl['model_calls']==0 and not impl['source_execution'] and not impl['collector_enabled'] and not impl['canonical_import'],'No live adapter/admission')
    require(impl['verified_reference_years']=={'2024':2023} and impl['earlier_reference_years']=='unknown','Reference year boundary')
    require(impl['fixture_observations']==10 and impl['fixture_bytes']==3506 and impl['fixture_source_sha256']==FIXTURE_SHA256,'Exact fixture')
    require(len(catalog['next_actions'])==9 and len(catalog['follow_up_prompts'])==7,'Actions/prompts')
    require([x['status']for x in catalog['next_actions'][:2]]==['completed_bounded_review','completed_offline_implementation'] and all(x['status']=='held_documentary_review'for x in catalog['next_actions'][2:]),'Implemented versus held work')
    for p in catalog['follow_up_prompts']:
        require(p['status']=='prepared_not_dispatched' and p['prompt'] in markdown,'Prompt parity/status')
        require(all(x in p['prompt']for x in ['Read-only','No login','Stop','artifact-specific rights','No causal AI']),'Standalone prompt guard')
    require(len(catalog['corrections'])>=13 and len(catalog['holds'])==7,'Corrections/holds')
    return dict(labor_market_collections=4,labor_market_artifact_references=len(aids),labor_market_qualified_findings=findings,labor_market_follow_up_prompts=7,labor_market_next_actions=9,labor_market_held_candidates=1,labor_market_unadmitted_collections=4)


def check_fixtures(root):
    f=root/'tools/evidence_program/tests/fixtures/labor-market'
    raw=(f/'de-ict-training.json').read_bytes();require(len(raw)==3506 and hashlib.sha256(raw).hexdigest()==FIXTURE_SHA256,'Fixture drift')
    out=read_fixture(f);require(len(out['records'])==10 and out['records'][-1]['value']==26.41,'Source value fidelity')
    require(out['missing_survey_years']==[2013,2021,2023] and out['source_status_member_present'] is False,'Missingness/status fidelity')
    require(out['records'][-1]['training_reference_year']==2023 and all(r['training_reference_year'] is None for r in out['records'][:-1]),'Reference mapping')
    notice=(f/'NOTICE.md').read_text();require(all(x in notice for x in ['Eurostat','8 October 2026','copyright-notice','not relicensed','not responsible','does not endorse']),'Scoped license notice')
    return dict(labor_market_real_aggregate_fixtures=1,labor_market_verified_observations=10,labor_market_ai_specific_observations=0)
