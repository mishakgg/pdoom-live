"""Offline consistency of curated persuasion/information metadata and effects."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl
from validate_persuasion_ledger import validate_ledger, require
BASE='4fa67bdb36e27c8b144b54ba99d3a9396208cd24'
IDS={f'PI{i:03}' for i in range(1,6)}
CATALOGS={'adoption-productivity.json','chinese-safety-evaluations.json','concentration-dependencies.json','historical-capability-backfills.json','open-model-diffusion.json','organizational-safety.json','scientific-progress.json'}


def strict_equal(left, right):
    return json.dumps(left,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(right,sort_keys=True,separators=(',',':'),allow_nan=False)


def safe_url(url):
    require(type(url) is str, 'URL must be text')
    p=urlsplit(url)
    require(p.scheme=='https' and p.hostname and not p.username and not p.password and
            not any(c.isspace() for c in url), 'Unsafe source URL')
    require(not any(any(w in k.lower() for w in ['token','secret','credential','signature','api_key']) for k,_ in parse_qsl(p.query)), 'Private source URL')


def check_ledger(document):
    result=validate_ledger(document)
    require(result['input_kind']=='manual_aggregate', 'Factual ledger cannot be synthetic')
    expected={
      'human_comparison':('1.812','1.260','2.607','0.01','<','Results: personalized GPT-4 versus unpersonalized human; adjusted ordinal model'),
      'personalization_original':('1.487','0.971','2.276','0.04','=','Author Correction: superseded direct GPT-4 personalization comparison'),
      'personalization_corrected':('1.487','0.971','2.276','0.0678','=','Author Correction: corrected direct GPT-4 personalization comparison'),
    }
    for row in document['records']:
        observed=(row['estimate'],row['uncertainty']['lower'],row['uncertainty']['upper'],row['p_value'],row['p_relation'],row['source']['locator'])
        require(observed==expected[row['record_id']], 'Curated source result or locator changed')
    return {'persuasion_ledger_assertions':3,'persuasion_ledger_current_assertions':2,
            'persuasion_ledger_studies':1,'persuasion_source_extractors':0}


def check_catalog(catalog, inventory_hash, markdown, root=None):
    require(catalog['schema_version']=='1.0' and catalog['reviewed_on']=='2026-10-08' and
            catalog['repository_review_commit']==BASE and catalog['status']=='review_prepared_with_curated_aggregate_checks', 'Review identity changed')
    require(strict_equal(catalog['baseline_inventory'],dict(source_family_count=64,sha256=inventory_hash,unchanged=True)), 'Frozen64 baseline mismatch')
    require(catalog['operational_admission']=='not_admitted' and catalog['canonical_contract_mapping']=='pending_separate_review', 'Admission or canonical mapping boundary changed')
    for key in ['collector_enabled','source_bodies_vendored','participant_records_acquired','participant_records_vendored','source_code_execution']:
        require(catalog[key] is False, 'Aggregate-only boundary changed: '+key)
    require(strict_equal(catalog['interpretation_guards'],GUARDS) and strict_equal(catalog['critical_qualifications'],QUALIFICATIONS), 'Interpretation/critical qualification changed')
    rows=catalog['collections']; require(len(rows)==5 and {r['candidate_id'] for r in rows}==IDS,'Five collection identities required')
    by_id={r['candidate_id']:r for r in rows}; arts={}; findings=set()
    require(catalog['producer_family_count']==4 and catalog['empirical_collection_count']==5 and
            {r['producer_family_id'] for r in rows}=={'debategpt','spitale','ofcom','costello'} and
            by_id['PI003']['producer_family_id']==by_id['PI004']['producer_family_id']=='ofcom' and
            by_id['PI003']['study_id']!=by_id['PI004']['study_id'], 'Four families/five studies boundary changed')
    for row in rows:
        cid=row['candidate_id']
        require(row['inventory_source_id'] is None and row['operational_admission']=='not_admitted' and row['collector_enabled'] is False, 'Candidate admission changed')
        require(row['underlying_evidence_id']==row['study_id'] and row['privacy_ethics'] and row['limitations'] and row['coverage'], 'Study provenance missing')
        require('## '+cid+' ' in markdown,'Guide identity missing')
        local={}
        for a in row['artifacts']:
            require(a['artifact_id'] not in arts and a['artifact_id'] not in local, 'Duplicate artifact identity')
            safe_url(a['url']);require(a['source_bytes_vendored'] is False and a['rights_scope'] and a['access_status'] and a['observed_on']=='2026-10-08','Artifact provenance/scope missing')
            require(a['rights_status'] in {'unknown','declared_license','inherited_license_unreverified','policy_basis_not_artifact_license','mixed_file_specific_rights'},'Unknown rights classification')
            if a['rights_status']=='declared_license':
                require(a['license_identifier'] and a['rights_evidence_url'],'License evidence missing');safe_url(a['rights_evidence_url'])
            else:require(a['license_identifier'] is None,'Unknown rights promoted to license')
            expected_hash=SOURCE_HASHES.get(a['artifact_id'])
            require(a['artifact_sha256']==expected_hash,'Unknown or verified artifact hash changed')
            require(a['upstream_reported_sha256']==(SPITALE_ADVERTISED if a['artifact_id']=='pi002_file' else None),'Advertised hash cannot replace byte hash')
            local[a['artifact_id']]=a
        require(local,'No source artifacts')
        for item in row['samples']:
            require(item['kind'] in {'observed_published_aggregate','observed_metadata','observed_schema','observed_documented_schema','observed_aggregate_cells'} and item['fields'] and item['qualification'] and item['evidence_artifact_ids'] and set(item['evidence_artifact_ids'])<=local.keys() and item['source_locators'] and set(item['source_locators'])<=set(item['evidence_artifact_ids']),'Sample evidence missing')
        for f in row['findings']:
            require(f['finding_id'] not in findings and f['text'] and f['qualification'] and f['evidence_artifact_ids'] and set(f['evidence_artifact_ids'])<=local.keys(),'Finding evidence missing')
            findings.add(f['finding_id'])
        arts.update(local)
    for aid in ['pi002_workbook','pi002_license','pi003_collection','pi003_technical','pi003_guide','pi004_report','pi004_tables']:
        require(arts[aid]['license_identifier'] is None,'Unverified artifact rights changed')
    require(arts['pi002_workbook']['access_status']=='not_inspected_aggregate_scope_unverified' and arts['pi005_zenodo']['access_status']=='metadata_only_archive_not_acquired','Uninspected contents promoted')
    require(arts['pi001_article']['license_identifier']==arts['pi001_correction']['license_identifier']=='CC-BY-4.0' and
            arts['pi001_card']['license_identifier']==arts['pi001_csv']['license_identifier']=='CC-BY-SA-4.0' and
            arts['pi002_article']['license_identifier']=='CC-BY-NC-4.0' and arts['pi005_dryad']['license_identifier']=='CC0-1.0','Article/data license distinction changed')
    # These records are a curated factual review, not a general growing dataset.
    for cid in IDS:
        require(strict_equal(by_id[cid]['samples'],SAMPLES[cid]) and strict_equal(by_id[cid]['coverage'],COVERAGE[cid]), 'Curated measurement/denominator/provenance changed: '+cid)
    overlap=catalog['catalog_overlap_review']; comp=overlap['catalogs_compared']
    require(overlap['commit']==BASE and len(comp)==7 and overlap['prior_collection_count']==38 and overlap['comparison_cell_count']==35 and
            {Path(x['path']).name for x in comp}==CATALOGS, 'Seven-catalog overlap review incomplete')
    require(sum(x['collection_count'] for x in comp)==38,'Prior collection count mismatch')
    for row in comp:
        require(re.fullmatch('[0-9a-f]{40}',row['git_blob_sha']) and re.fullmatch('[0-9a-f]{64}',row['sha256']) and
                len(row['compared_collection_ids'])==row['collection_count'] and set(row['candidate_checks'])==IDS,'Overlap identity missing')
        for check in row['candidate_checks'].values():
            require(all(check[k] is False for k in ['artifact_match','study_match','measurement_match']) and check['semantic_review'],'Overlap distinction missing')
        if root is not None:
            raw=(Path(root)/row['path']).read_bytes()
            require(hashlib.sha256(raw).hexdigest()==row['sha256'] and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['git_blob_sha'],'Prior catalog bytes differ from reviewed baseline')
    require({r['source_id'] for r in catalog['inventory_relationships']}=={'GL011','GL014','GL015','GL016','GL034','GL039','GL040'},'Frozen inventory crosswalk incomplete')
    impl=catalog['offline_validator']
    require(impl['implemented'] is True and all(impl[k] is False for k in ['source_extractor_implemented','participant_csv_adapter_implemented','network_access','statistical_reanalysis','validation_is_source_truth_verification']) and
            (impl['maximum_depth'],impl['maximum_nodes'],impl['maximum_text_bytes'])==(8,512,1024),'Implemented/proposed distinction changed')
    require(len(catalog['next_actions'])==7 and len(catalog['focused_follow_up_prompts'])==5 and len(catalog['holds'])==5 and len(catalog['corrections'])==8,'Actions/prompts/holds/corrections missing')
    require([x['status'] for x in catalog['next_actions']]==['completed','completed','held','held','held','held','pending_separate_review'],'Action status promoted')
    for p in catalog['focused_follow_up_prompts']:
        require('Read-only public-source research only.' in p['prompt'] and 'No login, outreach, bulk download, access-control bypass' in p['prompt'] and 'No repository edits' in p['prompt'],'Follow-up scope boundary missing')
    return {'persuasion_information_collections':5,'persuasion_information_producer_families':4,
            'persuasion_information_artifact_references':len(arts),'persuasion_information_findings':len(findings),
            'persuasion_prior_catalogs_compared':7,'unadmitted_persuasion_information_collections':5}

GUARDS = {'aggregate_only': True,
 'artifact_specific_rights_required': True,
 'assigned_exposure_implies_population_reach': False,
 'author_deposit_clears_journal_concern': False,
 'corrected_p_transfers_between_comparisons': False,
 'correction_is_independent_replication': False,
 'odds_ratio_is_percent_people_persuaded': False,
 'participant_data_acquisition_enabled': False,
 'perceived_exposure_is_authenticated_exposure': False,
 'persuasion_optimization_enabled': False,
 'pooled_weekly_exposure_is_cumulative_reach': False,
 'population_causal_impact_established': False,
 'proxy_to_pdoom_allowed': False,
 'public_access_implies_reuse_rights': False,
 'source_code_execution_enabled': False}

QUALIFICATIONS = {'costello': {'corrected_effects_verified': False,
              'editorial_concern': 'active_resolution_unverified',
              'journal_resolution_verified': False,
              'participant_archive_acquired': False},
 'debategpt': {'corrected_p': '0.0678',
               'correction_applies_to': 'personalized_gpt4_vs_nonpersonalized_gpt4',
               'participant_csv_processed': False,
               'statistical_model_replicated': False},
 'ofcom': {'artifact_ogl_verified': False,
           'authenticated_exposure': False,
           'distinct_collections': 2,
           'election_copyright_holder': 'YouGov plc',
           'election_distinct_people_verified': False,
           'election_geography_resolved': False,
           'election_pooled_base': 8556,
           'item_base_equals_achieved_sample': False,
           'oet_within_person_longitudinal_verified': False,
           'producer_families': 1},
 'spitale': {'advertised_hash_is_locally_computed': False,
             'editorial_clearance_absolute': False,
             'static_encoding_verified': True,
             'static_wiki_linked_to_final_workbook': False,
             'workbook_contents_reverified': False,
             'workbook_means_recoded': False}}

SAMPLES = {'PI001': [{'evidence_artifact_ids': ['pi001_article'],
            'fields': {'ci': ['1.260', '2.607'],
                       'ci_method': 't_based_cluster_robust',
                       'comparison': 'personalized GPT-4 vs unpersonalized human',
                       'conditioning': 'pretreatment_agreement',
                       'confidence_level': '0.95',
                       'estimate': '1.812',
                       'metric': 'ordinal_model_odds_ratio',
                       'p_relation': '<',
                       'p_value': '0.01'},
            'kind': 'observed_published_aggregate',
            'qualification': 'Different estimand from the direct personalization contrast; published '
                             'p<.01 is not the corrected p=.0678.',
            'source_locators': {'pi001_article': 'Results: partial proportional odds model comparing '
                                                 'personalized GPT-4 against unpersonalized human'}},
           {'evidence_artifact_ids': ['pi001_correction'],
            'fields': {'ci': ['0.971', '2.276'],
                       'ci_method': 't_based_cluster_robust',
                       'comparison': 'personalized GPT-4 vs nonpersonalized GPT-4',
                       'conditioning': 'pretreatment_agreement',
                       'confidence_level': '0.95',
                       'corrected_p': '0.0678',
                       'correction_date': '2026-09-03',
                       'estimate': '1.487',
                       'metric': 'ordinal_model_odds_ratio',
                       'original_p': '0.04',
                       'p_relation': '='},
            'kind': 'observed_published_aggregate',
            'qualification': 'Interval includes 1; corrected result does not establish incremental '
                             'personalization benefit.',
            'source_locators': {'pi001_correction': 'Correction text: direct personalized versus '
                                                    'nonpersonalized GPT-4 comparison'}}],
 'PI002': [{'evidence_artifact_ids': ['pi002_article'],
            'fields': {'comparison_method': 'Tukey_multiple_comparisons',
                       'confidence_interval': None,
                       'figure_error_bar_statistic': 'SEM',
                       'gpt3_origin': '0.89',
                       'human_origin': '0.92',
                       'metric': 'mean_participant_correctness',
                       'outcome': 'false_information_recognition_score',
                       'p_value': '0.0032',
                       'participants': 697,
                       'scale': [0, 1]},
            'kind': 'observed_published_aggregate',
            'qualification': 'Published participant-level score summary. Not a workbook-mean recoding '
                             'or percentage of population misled.',
            'source_locators': {'pi002_article': 'Results: GPT-3 AI model informs and disinforms us '
                                                 'better; Figure 1C'}},
           {'evidence_artifact_ids': ['pi002_file'],
            'fields': {'bytes': 6068, 'filename': 'scored_survey_types.xlsx', 'version': '1'},
            'kind': 'observed_metadata',
            'qualification': 'Intake describes four rows/22 columns and 7,651 assessments; contents and '
                             'those totals were not reverified and are excluded from accepted numeric '
                             'examples.',
            'source_locators': {'pi002_file': 'OSF file metadata: attributes name, size, version, dates '
                                              'and hashes'}},
           {'evidence_artifact_ids': ['pi002_scoring_wiki'],
            'fields': {'accurate_label': 1,
                       'aggregation': 'equally averaged per-item response-label means',
                       'computer_label': 0,
                       'counts': 'summed item-assessment counts',
                       'dispersion': 'means of per-item SD/IQR',
                       'misinformation_label': 0,
                       'real_person_label': 1},
            'kind': 'observed_documented_schema',
            'qualification': 'Static documentation predates final workbook. No proven execution/version '
                             'linkage; not published participant-average correctness and not an '
                             'observed workbook sample.',
            'source_locators': {'pi002_scoring_wiki': 'Survey wiki version8: response recoding and '
                                                      'scored_survey_types aggregation documentation'}}],
 'PI003': [{'evidence_artifact_ids': ['pi003_q8', 'pi003_q9'],
            'fields': {'conditional_followup': 'Q32a1 when misinformation selected',
                       'item_denominator': None,
                       'multi_select_codes': {'11': 'misinformation',
                                              '24': 'fake/deceptive images or videos including '
                                                    'deepfakes',
                                              '98': 'prefer not to say',
                                              '99': 'none'},
                       'question': 'Q8',
                       'recall': 'previous_four_weeks',
                       'routed_when': 'Q8a=1'},
            'kind': 'observed_schema',
            'qualification': 'Item24 does not independently identify AI generation. Conditional '
                             'response bases differ from overall achieved sample. Selected codes '
                             'persist in Wave 9, but other categories change; entire questionnaires are '
                             'not identical.',
            'source_locators': {'pi003_q8': 'Printed pages11–13 and23–24: Q8a, Q8 and Q32a1',
                                'pi003_q9': 'Printed pages11–13 and23–24: same selected '
                                            'questions/routing'}}],
 'PI004': [{'evidence_artifact_ids': ['pi004_report', 'pi004_tables'],
            'fields': {'aggregation': 'pooled_cross_sections',
                       'confidence_interval': None,
                       'dont_know_percent_rounded': 46,
                       'estimate_percent_rounded': 27,
                       'outcome': 'believed_encountered_deepfake_at_least_once',
                       'pooled_base': 8556,
                       'question': 'Q22',
                       'recall': 'previous week'},
            'kind': 'observed_published_aggregate',
            'qualification': 'Workbook supplies verified base absent from the initial intake; no '
                             'confidence interval inferred.',
            'source_locators': {'pi004_report': 'Printed page9 and footnote5; design on printed page4',
                                'pi004_tables': 'Percents!A853:B855: Q22 question and bases'}},
           {'evidence_artifact_ids': ['pi004_tables'],
            'fields': {'confidence_interval': None,
                       'dont_know_cell': 'B866',
                       'dont_know_proportion': '0.4621',
                       'pooled_unweighted_base': 8556,
                       'pooled_weighted_base': 8556,
                       'positive_frequency_cells': ['B858', 'B860', 'B862', 'B864'],
                       'positive_frequency_proportions': ['0.1684', '0.0645', '0.0208', '0.0203'],
                       'positive_frequency_sum_derived': '0.2740',
                       'question': 'Q22',
                       'question_cell': 'A853',
                       'unweighted_bases_cells': 'B854:F854',
                       'wave_bases': [2129, 2109, 2156, 2162],
                       'weighted_bases_cells': 'B855:F855',
                       'worksheet': 'Percents'},
            'kind': 'observed_aggregate_cells',
            'qualification': 'Selected source-cached aggregate cells; no workbook recalculation. '
                             'Positive sum is reviewer-derived, not a source net cell. Four-decimal '
                             'precision preserved; binary XML serialization adds no survey precision.',
            'source_locators': {'pi004_tables': 'Percents!A853:F866; column mapB5:F7'}},
           {'evidence_artifact_ids': ['pi004_tables'],
            'fields': {'question': 'Q23X',
                       'unweighted_base': 2399,
                       'unweighted_base_cell': 'B869',
                       'weighted_base': '2344.33',
                       'weighted_base_cell': 'B870'},
            'kind': 'observed_aggregate_cells',
            'qualification': 'Conditional action-question base; never substitute the 8556 Q22 pooled '
                             'base or treat intentions as completed behavior.',
            'source_locators': {'pi004_tables': 'Percents!B869:B870'}}],
 'PI005': [{'evidence_artifact_ids': ['pi005_dryad'],
            'fields': {'aggregate_sample_counts': {'complete_cases': 2044, 'screened_rows': 2094},
                       'belief_scale': '0–100',
                       'corrected_confidence_interval': None,
                       'corrected_effect_estimate': None,
                       'corrected_p_value': None,
                       'followup_denominators': None,
                       'followup_population': 'Study 1',
                       'followup_windows': ['10 days', 'two months'],
                       'study_screened_counts': {'Study1': 748, 'Study2': 1346}},
            'kind': 'observed_documented_schema',
            'qualification': 'Documented counts not independently recomputed; corrected coefficients '
                             'withheld. No individual identifiers or rows published.',
            'source_locators': {'pi005_dryad': 'README: corrected release, primary table dimensions, '
                                               'complete cases, schema and follow-up definitions'}}]}

COVERAGE = {'PI001': {'agreement_scale': [1, 5],
           'country': 'United States',
           'date_precision': 'month',
           'debates_design': 600,
           'fieldwork': 'December 2023–April 2024',
           'inference': 'Partial proportional odds model, conditional on pretreatment opponent-aligned '
                        'agreement; published t-based 95% intervals with cluster-robust standard '
                        'errors.',
           'measurement_window': 'immediate pre/post within approximately ten-minute assigned debate',
           'participants_design': 900,
           'principal_analysis_observations': 750,
           'recruitment': 'Prolific adults'},
 'PI002': {'date_precision': 'month',
           'fieldwork': 'October–November 2022',
           'measurement_window': 'within-session truth and origin judgments',
           'respondents_retained': 697,
           'stimuli': 220,
           'topics': 11},
 'PI003': {'current_age_frame': '18+',
           'first_wave': 'November 2021',
           'including_boost_fieldwork_end': '2026-01-20',
           'latest_fieldwork': '5–20 January2026',
           'latest_interviews_including_boosts': 7494,
           'latest_release_date': '2026-04-16',
           'latest_released_wave': 'Wave 9 January2026',
           'main_fieldwork_end': '2026-01-12',
           'measurement_window': 'previous four weeks',
           'next_scheduled_release': '2026-10-15',
           'population': 'UK internet users; repeated tracking does not establish linked within-person '
                         'longitudinal outcomes',
           'previous_age_frame': '13–84',
           'reported_total_ess': 7458},
 'PI004': {'distinct_people_across_waves': None,
           'fieldwork': ['2024-06-19/2024-06-20',
                         '2024-06-26/2024-06-27',
                         '2024-07-03/2024-07-04',
                         '2024-07-10/2024-07-11'],
           'measurement_window': 'previous week in each cross-section',
           'pooled_base_unit': 'survey responses; unique people across waves unverified',
           'pooled_unweighted_base': 8556,
           'pooled_weighted_base': 8556,
           'population_label': 'source conflict: report UK adults, workbook cover GB adults; tables '
                               'include Northern Ireland',
           'wave_bases': [2129, 2109, 2156, 2162]},
 'PI005': {'author_deposit_date': '2026-09-27',
           'corrected_release': '2026-09-29',
           'editorial_concern_date': '2026-06-11',
           'fieldwork_dates': None,
           'followup_population': 'Study 1 only; Study 2b protest intentions are a separate outcome',
           'followup_windows': ['10 days', 'two months'],
           'measurement_scale': '0–100 belief rating',
           'original_publication_date': '2024-09-13',
           'publication_year': 2024,
           'reported_complete_cases': 2044,
           'reported_screened_rows': 2094}}

SOURCE_HASHES = {'pi002_scoring_wiki': '4a943df3e950fa3e7efd76a60cf2f1a908f31262c333415d2317bcc64d9ab4a9',
 'pi004_tables': '22ef1d16c21177043ae2b883e5fae9024da97ac3eee84c2d67cbacb2d4771748'}

SPITALE_ADVERTISED = '2c4e3e033634e5dfd49a9df47a63cd3104afc1502f092c94423d1a3990cb54ca'
