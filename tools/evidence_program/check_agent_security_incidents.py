"""Offline consistency gates for the combined item-13 review; no collection."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from read_agentdojo_metadata import normalize_run


def require(value, message):
    if not value:raise ValueError(message)


REVIEWED_CATALOG_SHA256 = 'a1674d8b915884dd843a84a01047b953cb4c8f40259a2008e42a933d16f212fe'


def check_catalog(catalog, inventory_hash, markdown, root):
    semantic = hashlib.sha256(json.dumps(catalog, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    require(semantic == REVIEWED_CATALOG_SHA256, 'Reviewed semantics changed; explicit source review and fingerprint refresh required')
    require(catalog['schema_version']=='agent-security-incidents-review/1.0.0','Catalog version')
    require(catalog['status']=='curated_research_not_admitted' and catalog['operational_admission']=='not_admitted'
            and catalog['collector_enabled'] is False and catalog['source_code_execution'] is False,'Admission gate')
    require(catalog['original_report_count']==1 and catalog['collection_count']==7,'One combined report/seven collections')
    require(catalog['repository_review_commit']=='088400574a33af144ec7ef7bf13ac88f68f1b86c','Review baseline')
    require(catalog['baseline_inventory']['sha256']==inventory_hash and catalog['baseline_inventory']['source_family_count']==64,'Frozen inventory')
    require(not ({'records','observations','pdoom','risk_score'} & catalog.keys()),'Catalog is not an observation dataset')
    cs=catalog['collections'];ids=[c['candidate_id']for c in cs]
    require(ids==['ASI%03d'%i for i in range(1,8)],'Candidate identity/order')
    require([c['inventory_source_id']for c in cs]==[None,None,None,'GL004',None,None,'GL014'],'Five new/two enrichment identity')
    all_artifacts=set();findings=0
    for c in cs:
        require(c['operational_admission']=='not_admitted' and c['collector_enabled'] is False,'Collection admission')
        for key in ['name','source_family_id','historical_coverage','update_frequency','access_export','measurement_regime','author_authority']:
            require(isinstance(c[key],str) and c[key].strip(),'Missing source scope')
        require(len(c['limitations'])>=4 and c['artifacts'] and c['findings'],'Missing evidence/limits')
        own={a['artifact_id']for a in c['artifacts']}
        require(len(own)==len(c['artifacts']) and not own & all_artifacts,'Artifact uniqueness')
        all_artifacts |= own
        for a in c['artifacts']:
            u=urlsplit(a['url'])
            require(u.scheme=='https' and u.hostname and u.username is None and u.password is None,'Source URL')
            require(a['source_bytes_vendored'] is False,'No real source payload fixtures')
            require(a['rights_status'] and a['rights_scope'] and a['evidence_locator'],'Artifact rights/locator')
            for key,n in [('git_commit',40),('git_blob_sha',40),('source_sha256',64)]:
                require(a[key] is None or re.fullmatch('[0-9a-f]{%d}'%n,a[key]),'Artifact hash/pin')
        fids=[f['finding_id']for f in c['findings']]
        require(len(fids)==len(set(fids)),'Finding uniqueness')
        for f in c['findings']:
            require(f['claim'] and f['qualification'] and f['evidence_artifact_ids']
                    and set(f['evidence_artifact_ids'])<=own,'Finding evidence/qualification')
        for f in c['findings']:
            require(f['claim'] + ' ' + f['qualification'] in markdown, 'Guide/finding semantic parity')
        findings+=len(c['findings'])
    headings=re.findall(r'^## (ASI\d{3}) (.+)$',markdown,re.M)
    require(dict(headings)=={c['candidate_id']:c['name']for c in cs} and len(headings)==7,'Guide/catalog heading parity')
    overlap=catalog['overlap_review']
    require(overlap['frozen_inventory_count']==64 and overlap['prior_catalog_count']==12
            and overlap['prior_candidate_collections']==63 and overlap['prior_artifact_references']==464,'Overlap scope')
    require(len(overlap['per_catalog_review'])==12 and len(overlap['per_collection_review'])==7,'Overlap completeness')
    pins=catalog['prior_catalog_fingerprints'];require(len(pins)==12,'Prior catalog pins')
    for p in pins:
        rel=p['path'];require(rel.startswith('data/evidence-program/research/') and '..'not in Path(rel).parts,'Prior path')
        raw=(root/rel).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==p['sha256'],'Prior catalog drift')
    impl=catalog['implementation']
    require(impl['status']=='implemented_offline_synthetic_public_fixtures' and impl['network_calls']==0
            and impl['model_calls']==0 and impl['source_execution'] is False and impl['task_execution'] is False
            and impl['public_real_trace_fixtures']==0,'Offline implementation gate')
    require(impl['actual_attacked_run_interpretation']=='unverified_historical_predicate'
            and impl['clean_interpretation']=='not_applicable_clean','Outcome semantics gate')
    require((impl['max_bytes'],impl['max_messages'],impl['max_assistant_tool_calls'],impl['max_json_nodes'],impl['max_json_depth'])==(262144,100,300,20000,24),'Parser bounds')
    require(impl['intake_acquisition_proposal_status']=='18_file_network_adapter_not_implemented_or_run','Proposed versus implemented')
    require(catalog['revision_chains'][0]['before']==70 and catalog['revision_chains'][0]['after']==63
            and catalog['revision_chains'][0]['found']==54 and catalog['revision_chains'][0]['correction_publication_date'] is None,'AIxCC revision')
    require(catalog['revision_chains'][3]['event_count']==1 and catalog['revision_chains'][3]['artifact_count']==2,'OpenAI event/artifact')
    prompts=catalog['follow_up_prompts'];actions=catalog['next_actions']
    require(len(prompts)==8 and len(actions)==10,'Actions/prompts separation')
    require([a['status']for a in actions[:2]]==['completed_bounded_review','completed_offline_implementation']
            and all(a['status']=='held_documentary_review'for a in actions[2:]),'Completion versus holds')
    for p in prompts:
        require(p['prompt'] in markdown,'Prompt parity')
        require(all(x in p['prompt']for x in ['Read-only','No login','Stop','No','payloads','artifact-specific rights']),'Prompt safety/boundary')
    require(len(catalog['holds'])>=9 and len(catalog['corrections'])>=13,'Holds/corrections')
    return dict(agent_security_collections=7,agent_security_artifact_references=len(all_artifacts),
        agent_security_qualified_findings=findings,agent_security_follow_up_prompts=8,agent_security_next_actions=10,
        agent_security_unadmitted_collections=7)


def check_fixtures(root):
    f=root/'tools/evidence_program/tests/fixtures/agent-security-incidents'
    out=normalize_run((f/'clean.synthetic.json').read_bytes(),json.loads((f/'manifest.synthetic.json').read_text()))
    require(out['evidence_type']=='synthetic_evaluation_fixture' and out['source_url'] is None,'Synthetic fixture isolation')
    require(out['assistant_origin_tool_calls']==2 and out['duration_seconds']=='4.5','Synthetic expected metadata')
    require(out['security_interpretation']==dict(status='not_applicable_clean',attacker_goal_success=None),'Synthetic clean outcome')
    return dict(agent_security_public_synthetic_fixtures=1,agent_security_public_real_trace_fixtures=0)
