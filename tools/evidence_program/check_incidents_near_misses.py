#!/usr/bin/env python3
"""Offline catalog checks; documentary verification is separate from these tests."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

IDS = [f'INM{i:03}' for i in range(1, 9)]
ROLES = {'agency_publication_correction', 'agency_document_metadata', 'regulator_recall_metadata',
         'manufacturer_mechanism_and_regulator_category', 'manufacturer_report_with_qualification',
         'reported_absence_not_measured_zero', 'regulator_inquiry', 'regulator_estimate',
         'conflicting_regulator_publications', 'regulator_aggregate_with_repeat_units',
         'regulator_reviewed_case_aggregate', 'regulator_duplicate_identification',
         'regulator_hosted_media_allegation', 'regulator_investigation_finding',
         'regulator_multifactor_cause', 'agency_document_revision', 'stipulated_legal_remedy',
         'stipulated_procedural_qualification', 'respondent_reported_compliance',
         'provider_mechanism', 'provider_affected_request_fraction', 'provider_mechanism_and_remedy',
         'provider_deployment_regression', 'provider_causal_assessment', 'provider_conditional_potential_exposure'}
RIGHTS = {'unknown', 'agency_authored_portions', 'mixed_authorship_metadata_only',
          'documented_api_license_with_exclusions', 'explicit_license_agency_authored', 'court_order_metadata_only'}


def require(value, message):
    if not value:
        raise ValueError(message)


def text(value, label):
    require(type(value) is str and bool(value.strip()) and len(value) <= 6000, label)


def url(value):
    text(value, 'URL text')
    p = urlsplit(value)
    require(p.scheme == 'https' and p.hostname and p.username is None and p.password is None
            and not any(c.isspace() for c in value), 'Public HTTPS source URL required')


def check_catalog(d, inventory_sha256, guide, root):
    require(type(d) is dict and d['schema_version'] == 'incidents-near-misses-review/1.0.0', 'Schema')
    require(d['reviewed_on'] == '2026-10-08' and d['repository_review_commit'] == 'b5adbb5bb94146fb8c4ec74976f3efa0a24723de', 'Dated review base')
    require(d['status'] == 'curated_research_not_admitted' and d['operational_admission'] == 'not_admitted', 'Admission boundary')
    require(d['collector_enabled'] is False and d['source_code_execution'] is False, 'No collection/execution')
    require(type(d['original_report_count']) is int and d['original_report_count'] == 1, 'One separate submitted report')
    require(type(d['collection_count']) is int and d['collection_count'] == 8, 'Eight collections')
    require(d['baseline_inventory'] == {'path': 'data/evidence-program/source_inventory.json', 'source_family_count': 64, 'sha256': inventory_sha256}, 'Frozen inventory')
    require(d['canonical_contract_mapping'] == 'held_for_lossless_mapping_review', 'Canonical hold')
    require(d['priority_ranking'] == IDS[:3], 'Three ranked collections')
    collections = d['collections']
    require(type(collections) is list and [c['candidate_id'] for c in collections] == IDS, 'Unique ordered collection IDs')
    all_artifacts = set(); all_findings = set(); findings = 0; artifacts = 0
    for c in collections:
        require(c['operational_admission'] == 'not_admitted' and c['collector_enabled'] is False, 'Collection admission')
        for k in ('name', 'source_family_id', 'inventory_relationship', 'historical_coverage', 'update_frequency', 'access_export'):
            text(c[k], 'Collection ' + k)
        require(type(c['limitations']) is list and len(c['limitations']) >= 3, 'Collection limits')
        for t in c['limitations']: text(t, 'Limit text')
        require(type(c['artifacts']) is list and len(c['artifacts']) >= 3, 'Artifact references')
        local = set()
        for a in c['artifacts']:
            aid = a['artifact_id']; text(aid, 'Artifact ID')
            require(aid not in all_artifacts, 'Duplicate artifact ID'); all_artifacts.add(aid); local.add(aid)
            url(a['url'])
            for k in ('role', 'evidence_locator', 'rights_scope', 'verification_level'): text(a[k], 'Artifact ' + k)
            require(a['reviewed_on'] == '2026-10-08' and a['source_bytes_vendored'] is False, 'Artifact date/body exclusion')
            require(a['rights_status'] in RIGHTS, 'Artifact rights')
            if a['rights_evidence_url'] is not None: url(a['rights_evidence_url'])
            if a['license_identifier'] is not None:
                require(a['license_identifier'] in {'CC0-1.0', 'CC-BY-3.0-NZ'} and a['rights_evidence_url'], 'License evidence')
            if a['source_sha256'] is None:
                require(a['source_bytes'] is None, 'Unknown byte hash/size paired')
            else:
                require(type(a['source_sha256']) is str and re.fullmatch('[0-9a-f]{64}', a['source_sha256']), 'Source hash')
                require(type(a['source_bytes']) is int and 0 < a['source_bytes'] <= 10 * 1024 * 1024, 'Source byte count')
            artifacts += 1
        require(type(c['findings']) is list and len(c['findings']) >= 3, 'At least three qualified findings')
        for f in c['findings']:
            fid = f['finding_id']; require(fid not in all_findings, 'Duplicate finding ID'); all_findings.add(fid)
            require(re.fullmatch(c['candidate_id'] + '-F[0-9]{2}', fid), 'Scoped finding ID')
            text(f['claim'], 'Claim'); text(f['qualification'], 'Qualification')
            require(f['assertion_role'] in ROLES, 'Assertion-level attribution')
            refs = f['evidence_artifact_ids']; require(type(refs) is list and bool(refs) and len(refs) == len(set(refs)) and set(refs) <= local, 'Finding artifact reference')
            require(type(f['same_evidence_prior_finding_ids']) is list, 'Same-evidence links')
            findings += 1
    first, fda, nz, odi, ntsb, ftc, anthropic, openai = collections
    require(first['inventory_relationship'] == 'existing_collection_same_claim_enrichment' and first['prior_candidate_ids'] == ['ASI005'], 'SGO existing collection')
    require(all(f['same_evidence_prior_finding_ids'] == ['ASI005-F04'] for f in first['findings'][:2]), 'SGO same prior claims')
    require([x['scope'] for x in first['sample_records']] == ['single_report', 'release_wide'], 'Correction scopes')
    require(first['sample_records'][0]['report_id'] == '34952-11803' and type(first['sample_records'][0]['report_version']) is int and first['sample_records'][0]['report_version'] == 1, 'Report and exact integer version')
    require(first['sample_records'][1]['report_id'] is None and first['sample_records'][1]['report_version'] is None, 'No invented release report')
    require(all(x['previous_content_available'] is False for x in first['sample_records']), 'Unknown earlier content')
    s=fda['sample_records']; require(s[0]['quantity'] == 15 and type(s[0]['quantity']) is int and s[0]['unit'] == 'systems' and s[0]['patient_harm_count'] is None and s[0]['ai_in_product'] is True and s[0]['ai_caused_defect'] == 'not_established', 'FDA units/causality')
    require(s[1]['mechanism'] == 'unconfirmed' and s[1]['near_miss'] == 'unestablished' and s[1]['complications'] == 'none_reported' and s[1]['event_date'] == 'qualified_unknown', 'MAUDE qualification')
    s=nz['sample_records'][0]; require((s['estimated_up_to_failures'],s['misidentifications'],s['other_procedural_failures']) == (13,9,4) and [x['value']for x in s['alert_counts']] == [1735,1742] and s['alert_conflict'] == 'unresolved' and s['distinct_people'] is None, 'NZ estimates/conflicting units')
    s=odi['sample_records']; require((s[0]['reviewed_incidents'],s[0]['reviewed_crashes'],s[0]['reported_injuries'],s[0]['reported_fatalities']) == (367,109,1,0) and s[0]['scope'] == 'reviewed_case_set' and s[0]['fleet_risk_rate'] is None, 'ODI review-set denominator')
    require(s[1] == dict(record_type='duplicate_report_relation',from_report_id='30270-1220',to_report_id='30270-1160',relation='duplicate_of',authority='NHTSA_ODI'), 'Explicit duplicate direction')
    s=ntsb['sample_records'][0]; require(s['revision_scope'] == 'title_only' and s['causality'] == 'multifactor' and s['reissued_date'] == '2020-06-26' and s['aiid_incident_id'] == 4, 'NTSB event/revision')
    s=ftc['sample_records']; require(s[0]['allegations'] == 'neither_admit_nor_deny_except_jurisdiction' and s[0]['verified_victim_count'] is None and s[1]['authority'] == 'respondent_reported' and s[1]['independent_audit'] is False, 'FTC authority')
    s=anthropic['sample_records']; require([x['reported_percent']for x in s] == ['0.8','16'] and all(x['independently_verified'] is False for x in s) and s[1]['population'] == 'Sonnet_4_requests' and s[1]['window'] == 'worst_hour_2025-08-31', 'Anthropic fractions')
    s=openai['sample_records']; require(s[0]['same_evidence_prior_candidate_id'] == 'ASI007' and type(s[0]['independent_event_count']) is int and s[0]['independent_event_count'] == 1 and s[0]['harmed_user_count'] is None, 'OpenAI same event')
    require(s[1]['reported_percent'] == '1.2' and s[1]['population'] == 'Plus_subscribers_active_in_specified_nine_hour_window' and s[1]['exposure_status'] == 'potential' and s[1]['confirmed_harm_count'] is None, 'OpenAI conditional exposure')
    fingerprints=d['prior_catalog_fingerprints']; require(len(fingerprints)==15 and len({f['path']for f in fingerprints})==15,'All fifteen catalog fingerprints')
    prior_findings=set(); prior_candidates=set()
    for p in fingerprints:
        path=p['path']; require(path.startswith('data/evidence-program/research/') and '..' not in Path(path).parts and path.endswith('.json'), 'Prior catalog path')
        raw=(root/path).read_bytes(); require(hashlib.sha256(raw).hexdigest()==p['sha256'], 'Prior catalog content changed')
        require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==p['git_blob_sha'], 'Prior catalog Git blob changed')
        prior=json.loads(raw)
        for c in prior.get('collections',[]):
            prior_candidates.add(c['candidate_id']); prior_findings.update(f['finding_id']for f in c.get('findings',[]))
    for c in collections:
        require(set(c['prior_candidate_ids']) <= prior_candidates,'Prior candidate reference')
        for f in c['findings']: require(set(f['same_evidence_prior_finding_ids']) <= prior_findings, 'Prior finding reference')
    overlap=d['overlap_review']; require(overlap['prior_catalog_count']==15 and overlap['candidate_by_catalog_assessment_count']==120, 'Complete overlap comparison')
    require(set(overlap['comparison_levels']) >= {'family','artifact','event','claim'}, 'Overlap levels')
    require(len(overlap['catalogs'])==15 and {x['path']for x in overlap['catalogs']}=={x['path']for x in fingerprints}, 'Overlap catalog coverage')
    require(all(set(x['candidate_checks'])==set(IDS)for x in overlap['catalogs']), 'All candidate/catalog cells')
    require(d['novelty_summary']['new_producer_families']==['INM002','INM003','INM005'] and d['novelty_summary']['existing_producer_family_enrichments']==['INM001','INM004','INM006','INM007','INM008'], 'Layered novelty classification')
    impl=d['implementation']; require(impl['source_parser_implemented'] is False and impl['live_fetch'] is False and impl['source_document_bytes_vendored'] is False and impl['selected_change_count']==2 and impl['same_evidence_prior_finding_ids']==['ASI005-F04'], 'Honest bounded implementation')
    prompts=d['follow_up_prompts']; require(len(prompts)==8 and {p['prompt_id']for p in prompts}=={f'INM-P{i:02}'for i in range(1,9)}, 'Eight standalone prompts')
    for p in prompts:
        text(p['prompt'],'Prompt'); require(p['status']=='prepared_not_dispatched','Prompt dispatch boundary')
        for phrase in ['Read-only bounded','mishakgg/pdoom-live','source_inventory.json','incidents-near-misses.json','at most','Stop','No login','outreach','bypass','bulk download','patient/personnel','source code/model/target execution','canonical import','p(doom)']:
            require(phrase in p['prompt'],'Prompt missing boundary: '+phrase)
    actions=d['next_actions']; require(len(actions)==10 and len({x['action_id']for x in actions})==10, 'Ten separate actions')
    require({x['follow_up_prompt_id']for x in actions if 'follow_up_prompt_id'in x}=={p['prompt_id']for p in prompts}, 'Every prompt actionable')
    require(len(d['corrections'])>=14 and len(d['holds'])>=6,'Corrections and held work')
    for word in ['ASI005-F04','ASI007','not a PDF','15','1735','1742','1.2%','unknown','fifteen']:
        require(word in guide,'Guide missing boundary: '+word)
    serialized=json.dumps(d)
    for token in ['libfile_','Sentinel_','/workspace/','sediment://','source-receipts/','intake.json','input.txt']:
        require(token not in serialized and token not in guide,'Private receipt marker in public payload')
    return dict(incidents_near_misses_collections=8,incidents_near_misses_artifacts=artifacts,
                incidents_near_misses_findings=findings,incidents_near_misses_prior_catalogs=15,
                incidents_near_misses_overlap_cells=120,incidents_near_misses_followup_prompts=8)
