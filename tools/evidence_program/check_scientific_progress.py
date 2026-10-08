"""Offline scientific-progress catalog/ledger consistency; no source acquisition."""
from __future__ import annotations
import hashlib
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit
from validate_scientific_ledger import validate_ledger_bytes

BASE = 'e5121ee888393db656610be749dfc2d03897c751'
IDS = {f'SP{i:03}' for i in range(1,6)}
CATALOGS = {'adoption-productivity.json','chinese-safety-evaluations.json','concentration-dependencies.json',
            'historical-capability-backfills.json','open-model-diffusion.json','organizational-safety.json'}
GUARDS = {k: False for k in ('proxy_to_pdoom_allowed','universal_scientific_productivity_rate_enabled',
    'suggestion_implies_validated_discovery','reanalysis_implies_independent_replication',
    'assessment_implies_training_reproduction','feedback_calls_imply_discoveries',
    'best_of_k_implies_continuous_autonomy','public_link_implies_artifact_rights','code_license_inherits_to_dataset',
    'current_table_match_implies_regeneration','missing_outcome_implies_failure',
    'multiple_metrics_imply_independent_experiments','campaign_duration_implies_labor_saved',
    'historical_claim_contributes_to_current_totals','platform_novelty_implies_new_to_science')}
GUARDS.update(aggregate_only=True,artifact_specific_rights_required=True)
QUALIFICATIONS = {
 'i4r': {'current_table_means_match_paper':True,'current_regeneration_verified':False,
  'legacy_recomputation_independently_verified':False,'code_dispersion_statistic':'sample_SD',
  'published_dispersion_label':'standard_errors','uncertainty_ingestion':'held','participant_files_read':False,
  'virtual_2025_in_2024_sample':False},
 'alab': {'campaign_count':1,'corrected_target_partition':[36,4,17,57],'recipe_success_fraction':[105,353],
  'historical_target_success_fraction':[41,58],'historical_source_status':'indexed_primary_excerpt_only',
  'intermediate_40_of_57_is_published_version':False,'independent_experimental_replication':'not_established',
  'novelty_scope':'new_to_platform_not_necessarily_new_to_science','archive_members_inspected':False,
  'article_byte_pins_verified':False,'calendar_dates_known':False,'labor_hours_known':False,'human_rescue_outcomes_excluded':True},
 'rebench': {'release_starting_runtime_ms':'4.74','pinned_readme_starting_runtime_ms':'4.76',
  'partial_public_human_summaries_exist':True,'complete_original_export_verified':False,
  'human_baseline_ai_free':False,'task_commit_proven_original_run_version':False,
  'nominal_32_hour_budget_is_sustained_autonomy':False,'raw_human_rows_vendored':False},
 'alphatensor': {'headline_arithmetic':'F2_modulo_two','headline_multiplications':47,'baseline_multiplications':49,
  'numerical_arrays_inspected':False,'notebook_or_benchmark_executed':False,'certificate_independently_verified':False,
  'training_reproduced':False,'notebook_pickle_loader_used':False,'expected_speedup_is_observed_result':False,
  'quantum_2024_same_study':False},
 'casp': {'score_schema_observed':True,'raw_group_rows_vendored':False,'sequence_or_coordinate_files_acquired':False,
  'historical_raw_score_rights':'scope_unverified','casp17_final_results_verified':False,
  'independent_assessment_is_training_replication':False},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_url(url):
    require(isinstance(url,str),'Scientific URL must be text')
    p=urlsplit(url)
    require(p.scheme=='https' and p.hostname and not p.username and not p.password and
            not any(c.isspace() for c in url), 'Unsafe scientific URL')
    require(not any(any(word in key.lower() for word in ('token','credential','secret','signature','api_key'))
                    for key,_ in parse_qsl(p.query)), 'Signed scientific URL forbidden')


def check_catalog(catalog, inventory_hash, markdown, root=None):
    require(catalog['schema_version']=='1.0' and catalog['reviewed_on']=='2026-10-08' and
            catalog['repository_review_commit']==BASE and
            catalog['status']=='review_prepared_with_manual_aggregate_validator', 'Scientific review identity mismatch')
    require(catalog['operational_admission']=='not_admitted' and catalog['collector_enabled'] is False and
            catalog['canonical_contract_mapping']=='pending_separate_review', 'Scientific admission boundary changed')
    require(catalog['baseline_inventory']==dict(source_family_count=64,sha256=inventory_hash,unchanged=True),
            'Scientific frozen inventory mismatch')
    for field in ('source_bodies_vendored','participant_or_team_records_vendored',
                  'experimental_or_biological_material_vendored','source_code_or_model_execution'):
        require(catalog[field] is False, 'Scientific acquisition/execution boundary changed')
    require(catalog['interpretation_guards']==GUARDS and catalog['critical_qualifications']==QUALIFICATIONS,
            'Scientific interpretation or qualification changed')
    require(catalog['ranking_basis']=='source_utility_not_capability_or_risk' and
            [r['candidate_id'] for r in catalog['priority_ranking']]==['SP001','SP002','SP003'],
            'Scientific ranking basis/order changed')
    rows=catalog['collections']; by_id={r['candidate_id']:r for r in rows}
    require(len(rows)==len(by_id)==5 and set(by_id)==IDS,'Scientific collection IDs invalid')
    artifacts={};findings=set()
    for cid,row in by_id.items():
        require(row['inventory_source_id']==('GL004' if cid=='SP003' else None) and
                row['classification']==('existing_family_enrichment' if cid=='SP003' else 'new_relative_to_frozen_inventory') and
                row['operational_admission']=='not_admitted' and row['collector_enabled'] is False,
                'Scientific family admission/classification mismatch')
        for field in ('name','summary','historical_coverage','update_frequency','access_method',
                      'rights_summary','duplicate_evidence_policy','human_led_steps'):
            require(isinstance(row[field],str) and row[field].strip(),f'Scientific field missing: {field}')
        require(row['limitations'] and row['samples'] and row['findings'],'Scientific evidence/limits missing')
        local={a['artifact_id']:a for a in row['artifacts']}
        require(len(local)==len(row['artifacts']) and local and not local.keys() & artifacts.keys(),
                'Scientific artifact identity duplicate')
        for a in local.values():
            safe_url(a['url'])
            require(a['reviewed_on']==catalog['reviewed_on'] and a['provenance_locator'] and
                    a['artifact_role'] and a['source_body_vendored'] is False and a['artifact_sha256'] is None,
                    'Scientific source locator, body or byte-hash qualification changed')
            require(a['access_status'] in {'primary_opened','static_source_read','access_unverified',
              'metadata_only_not_downloaded','indexed_primary_excerpt_only','link_verified_not_downloaded',
              'application_shell_only','directory_only_not_downloaded','inherited_link_not_reverified'}, 'Scientific access state invalid')
            require(a['rights_status'] in {'declared_license','unknown'} and a['rights_scope'],
                    'Scientific rights status/scope invalid')
            if a['rights_status']=='declared_license':
                require(a['license_identifier'] and a['rights_evidence_url'],'Scientific rights evidence missing')
                safe_url(a['rights_evidence_url'])
            else:require(a['license_identifier'] is None,'Unknown rights cannot claim a license')
            if a['git_blob_sha'] is not None:require(re.fullmatch('[0-9a-f]{40}',a['git_blob_sha']), 'Scientific Git hash invalid')
        for sample in row['samples']:
            require(sample['kind'] in {'observed_aggregate','observed_schema'} and sample['fields'] and
                    sample['qualification'] and sample['evidence_artifact_ids'] and
                    set(sample['evidence_artifact_ids'])<=local.keys(),'Scientific sample provenance invalid')
        for finding in row['findings']:
            require(finding['finding_id'] not in findings and finding['text'] and finding['qualification'] and
                    finding['evidence_artifact_ids'] and set(finding['evidence_artifact_ids'])<=local.keys(),
                    'Scientific finding provenance invalid')
            findings.add(finding['finding_id'])
        artifacts.update(local)
    require(len(artifacts)==46 and len(findings)==20,'Scientific artifact/finding count changed')
    require(artifacts['sp002_original']['access_status']=='indexed_primary_excerpt_only' and
            artifacts['sp002_original']['rights_status']=='unknown','Historical A-Lab provenance cannot be promoted')
    require(artifacts['sp002_archive']['rights_status']=='unknown' and
            artifacts['sp005_14_txt']['rights_status']=='unknown','Unknown archive/raw-score rights cannot inherit')
    i=by_id['SP001']['samples'][0]['fields']
    require(i['mean_minutes_published']==i['mean_minutes_committed']==['82.0','93.3','179.7'] and
            i['team_denominators']==[33,35,35] and i['reproduction_successes']==[31,32,13] and
            i['rmst_minutes_without_success_committed']==['102','121','331'] and
            i['rmst_horizon_minutes']==420 and i['completion_mean_denominators'] is None,
            'I4R sample estimands or denominators changed')
    a=by_id['SP002']['samples'][0]['fields']
    require(a['target_outcomes']==dict(successful=36,inconclusive=4,not_obtained=17,denominator=57) and
            a['recipe_outcomes']==dict(successful=105,denominator=353,other_outcome_categories=None) and
            a['elapsed_days']==17 and all(a[k] is None for k in ('period_start','period_end','researcher_hours','researcher_hours_saved','robot_active_hours')),
            'A-Lab sample denominator or missingness changed')
    r=by_id['SP003']['samples'][0]['fields']
    require(r=={'task':'Optimize a Kernel','metric':'selected_solution_runtime','unit':'milliseconds',
                'o1_preview':'0.64','best_human':'0.67','starting_implementation_release':'4.74',
                'reference_implementation':'1.60','starting_implementation_pinned_readme':'4.76'},
            'RE-Bench selected outcome, version or unit changed')
    r=by_id['SP003']['samples'][1]['fields']
    require(r=={'environments':7,'human_attempts':71,'human_experts':61,'nominal_human_attempt_hours':8,
                'scoring_calls_per_hour':{'AIDE':'36.8','Modular':'25.3','human':'3.4'}},
            'RE-Bench feedback-rate construct changed')
    t=by_id['SP004']['samples']
    require(t[0]['kind']=='observed_schema' and t[0]['fields']['dimensions_key']=='3,4,5' and
            t[1]['fields']=={'matrix_dimensions':[4,4,4],'arithmetic':'F2 / modulo two',
                'scalar_multiplications':47,'baseline_multiplications':49,'baseline':'two recursive Strassen levels'} and
            t[2]['fields']=={'expected_speedup_percent':'8.5','baseline':'Strassen squared',
                'matrix_shape':[8192,8192],'dtype':'float32','hardware':'NVIDIA V100'},
            'AlphaTensor schema, arithmetic or expected-performance claim changed')
    casp=by_id['SP005']['samples'][0]
    require(casp['kind']=='observed_schema' and set(casp['fields'])=={'fields','metric_scales','coverage_formula','elapsed_compute','researcher_effort'} and
            casp['fields']['elapsed_compute'] is None and casp['fields']['researcher_effort'] is None,
            'CASP schema-only scope changed')
    overlap=catalog['catalog_overlap_review']; comps=overlap['catalogs_compared'];matrix=overlap['comparison_matrix']
    require(overlap['commit']==BASE and len(comps)==6 and overlap['collections_compared']==33 and
            {Path(r['path']).name for r in comps}==CATALOGS and len(matrix)==6,
            'All six prior catalogs must be compared')
    require({r['catalog'] for r in matrix}=={r['path'] for r in comps}, 'Scientific overlap matrix mismatch')
    for r in comps:
        require(re.fullmatch('[0-9a-f]{40}',r['git_blob_sha']) and re.fullmatch('[0-9a-f]{64}',r['sha256']) and
                r['result'] and r['same_study_duplicates']==r['exact_artifact_duplicates']==[],
                'Scientific overlap identity/provenance invalid')
        m=next(m for m in matrix if m['catalog']==r['path'])
        require(m['sha256']==r['sha256'] and m['git_blob_sha']==r['git_blob_sha'] and
                set(m['family_checks'])=={'i4r','alab','rebench','alphatensor','casp'}, 'Scientific overlap matrix family coverage invalid')
        require(all(v['artifact_match'] is False and v['study_match'] is False and v['measurement_match'] is False
                    for v in m['family_checks'].values()), 'Scientific duplicate finding drift')
        if root:
            path=(Path(root)/r['path']).resolve(); require(path.is_relative_to(Path(root).resolve()),'Unsafe catalog comparison path')
            raw=path.read_bytes()
            require(hashlib.sha256(raw).hexdigest()==r['sha256'] and
                    hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==r['git_blob_sha'],
                    'Prior catalog exact bytes differ from reviewed overlap baseline')
    v=catalog['offline_validator']
    require(v['status']=='implemented_offline_only' and v['kind']=='manual_aggregate_ledger_validator_not_source_extractor' and
            v['network_enabled'] is False and v['pdf_or_web_extraction_implemented'] is False and
            v['canonical_import'] is False and v['source_article_bytes_acquired'] is False and
            v['source_scientific_validation_performed'] is False and v['source_hashes_must_remain_null'] is True and
            v['maximum_bytes']==65536 and v['maximum_depth']==12 and v['maximum_input_records']==32 and
            v['maximum_unique_claims']==3 and v['maximum_provenance_per_record']==3,
            'Manual validator implementation boundary changed')
    holds=catalog['holds']; require(len(holds)==7 and {h['id'] for h in holds}=={f'SCI-H{i:02}' for i in range(1,8)} and
                                  all(h['reason'] and h['release_condition'] for h in holds),'Scientific holds missing')
    actions=catalog['next_actions']; require(len(actions)==8 and len({a['action_id'] for a in actions})==8,'Scientific actions invalid')
    for a in actions:require(a['candidate_ids'] and set(a['candidate_ids'])<=IDS and a['action'] and a['completion_evidence'] and
                            a['status'] in {'completed','open','pending_access_review','pending_rights_review','pending_contract_review'},'Scientific action incomplete')
    prompts=catalog['focused_follow_up_prompts']
    require(len(prompts)==6 and {p['action_id'] for p in prompts}=={a['action_id'] for a in actions if a['status']!='completed'} and
            all(p['why_needed'] and len(p['prompt'])>300 for p in prompts),'Scientific open actions need bounded prompts')
    require(len(catalog['corrections'])==9 and catalog['excluded_evidence'][0]['decision']=='excluded_from_productivity_evidence',
            'Scientific corrections or exclusion missing')
    headings=re.findall(r'^## (SP[0-9]{3}) (.+)$',markdown,re.MULTILINE)
    require(len(headings)==5 and dict(headings)=={k:v['name'] for k,v in by_id.items()},'Scientific guide headings mismatch')
    return {'scientific_progress_collections':5,'scientific_progress_artifact_references':46,'scientific_progress_findings':20,
            'unadmitted_scientific_progress_collections':5,'scientific_progress_prior_catalogs_compared':6}


def check_ledger(raw):
    result=validate_ledger_bytes(raw)
    require(result['input_kind']=='manual_aggregate' and result['campaign']['elapsed_days']==17,
            'Real ledger kind or campaign duration mismatch')
    rows={r['claim_kind']:r for r in result['records']}
    require(rows['historical_target_summary']['counts']=={'successful':41,'denominator':58} and
            rows['corrected_target_partition']['counts']=={'successful':36,'inconclusive':4,'not_obtained':17,'denominator':57} and
            rows['recipe_summary']['counts']=={'successful':105,'denominator':353}, 'Real ledger reviewed aggregates changed')
    require(all(p['capture_status']=='indexed_primary_excerpt' for p in rows['historical_target_summary']['provenance']),
            'Historical original must remain indexed-primary evidence')
    for name in ('corrected_target_partition','recipe_summary'):
        require(all(p['capture_status']=='text_observed_hash_unavailable' for p in rows[name]['provenance']) and
                any('Figure 2' in p['claim_locator'] for p in rows[name]['provenance']), 'Current ledger source locator missing')
    require(any('Abstract' in p['claim_locator'] and 'Outlook' in p['claim_locator'] for p in result['campaign']['provenance']),
            'Campaign duration needs separate locator')
    require(len(result['current_records'])==2 and result['campaign_count']==1,'Current ledger or campaign count mismatch')
    return {'scientific_progress_manual_ledger_claims':3,'scientific_progress_current_ledger_claims':2,
            'scientific_progress_campaigns':1,'scientific_progress_source_extractors':0}
