"""Offline consistency of the curated robotics review; no network or admission."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

BASE = 'ee3e0d2fa2c5a594fec276f08f4c985147e9f130'
IDS = {f'RP{i:03}' for i in range(1, 6)}
CATALOGS = {'chinese-safety-evaluations.json', 'adoption-productivity.json',
            'organizational-safety.json', 'open-model-diffusion.json',
            'concentration-dependencies.json', 'historical-capability-backfills.json',
            'scientific-progress.json', 'persuasion-information.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_equal(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def safe_url(url):
    require(type(url) is str and len(url) <= 2048, 'Source URL must be bounded text')
    p = urlsplit(url)
    require(p.scheme == 'https' and p.hostname and not p.username and not p.password
            and not any(c.isspace() for c in url), 'Invalid source URL')
    require(not any(any(s in k.lower() for s in ['token', 'secret', 'credential', 'signature', 'api_key'])
                    for k, _ in parse_qsl(p.query)), 'Private source URL')


def check_catalog(catalog, inventory_hash, markdown, root=None):
    require(catalog['schema_version'] == '1.0' and catalog['reviewed_on'] == '2026-10-08'
            and catalog['repository_review_commit'] == BASE
            and catalog['status'] == 'review_prepared_with_curated_table_checks', 'Review identity changed')
    require(strict_equal(catalog['baseline_inventory'], dict(source_family_count=64, sha256=inventory_hash, unchanged=True)), 'Frozen inventory mismatch')
    require(catalog['operational_admission'] == 'not_admitted' and catalog['canonical_contract_mapping'] == 'pending_separate_review', 'Admission or mapping changed')
    for key in ['collector_enabled', 'robot_controls_enabled', 'source_code_execution',
                'personal_evaluator_fields_retained', 'raw_trajectories_or_videos_acquired', 'full_source_bodies_vendored']:
        require(catalog[key] is False, 'Scope expanded: ' + key)
    require(strict_equal(catalog['interpretation_guards'], GUARDS), 'Interpretation boundary changed')
    require(strict_equal(catalog['critical_qualifications'], QUALIFICATIONS), 'Critical measurement qualification changed')
    rows = catalog['collections']
    require(len(rows) == 5 and {r['candidate_id'] for r in rows} == IDS, 'Five distinct collections required')
    require(len({r['source_family_id'] for r in rows}) == 5, 'Five producer families required')
    by_id = {r['candidate_id']: r for r in rows}
    require([(r['rank'], r['candidate_id']) for r in catalog['priority_ranking']] == [(1, 'RP001'), (2, 'RP002'), (3, 'RP003')], 'Ranking changed')
    artifacts, findings = {}, []
    for cid, row in by_id.items():
        require(row['inventory_source_id'] is None and row['inventory_relationship'] == 'new_source_family_candidate', 'Family identity changed')
        require(row['operational_admission'] == 'not_admitted' and row['collector_enabled'] is False, 'Collection admitted')
        require(strict_equal(row['samples'], SAMPLES[cid]), 'Curated source sample changed: ' + cid)
        require(strict_equal(row['coverage'], COVERAGE[cid]), 'Coverage/denominator changed: ' + cid)
        require(row['measurement_regime'] == REGIMES[cid], 'Physical regime changed')
        require(row['limitations'] and row['duplicate_evidence'] and row['access_export'] and row['human_involvement'], 'Source limitations missing')
        for a in row['artifacts']:
            require(a['artifact_id'] not in artifacts, 'Duplicate artifact identity')
            artifacts[a['artifact_id']] = a
            safe_url(a['url'])
            require(a['observed_on'] == '2026-10-08' and a['access_status'] and a['rights_scope'], 'Artifact provenance missing')
            require(a['source_bytes_vendored'] is False, 'Source body vendored')
            require(a['rights_status'] in {'declared_license', 'unknown'}, 'Unknown rights status')
            if a['rights_status'] == 'declared_license':
                require(a['license_identifier'] and a['rights_evidence_url'], 'License evidence missing')
                safe_url(a['rights_evidence_url'])
            else:
                require(a['license_identifier'] is None, 'Unknown rights silently licensed')
            if a['artifact_sha256'] is not None:
                require(re.fullmatch('[0-9a-f]{64}', a['artifact_sha256']) and a['hash_scope'] == 'Exact acquired UTF-8 source file bytes', 'Unqualified source hash')
        for f in row['samples'] + row['findings']:
            require(f['qualification'] and f['evidence_artifact_ids'] and set(f['evidence_artifact_ids']) <= {a['artifact_id'] for a in row['artifacts']}, 'Missing/foreign evidence link')
        findings.extend(row['findings'])
    require(len({f['finding_id'] for f in findings}) == len(findings), 'Duplicate finding identity')
    require(artifacts['rp001_report']['license_identifier'] == 'CC-BY-4.0' and artifacts['rp001_report']['version'] == '2407.01862v1'
            and artifacts['rp001_report']['artifact_sha256'] is None, 'Report version/license/hash scope changed')
    require(artifacts['rp003_index']['license_identifier'] == 'CC-BY-NC-SA-4.0'
            and artifacts['rp003_index']['access_status'] == 'endpoint_reference_not_downloaded', 'RRC rights/access boundary changed')
    for aid in ['rp005_docs', 'rp005_sheet', 'rp005_archives', 'rp005_glitches', 'rp005_paper']:
        require(artifacts[aid]['rights_status'] == 'unknown', 'STRANDS rights hold removed')
    require({x['source_id'] for x in catalog['inventory_relationships']} == {'GL016', 'GL034', 'GL039', 'GL040'}, 'Inventory crosswalk incomplete')
    overlap = catalog['catalog_overlap_review']; prior = overlap['catalogs_compared']
    require(overlap['commit'] == BASE and len(prior) == 8 and overlap['prior_collection_count'] == 43
            and overlap['prior_artifact_reference_count'] == 327 and overlap['comparison_cell_count'] == 40, 'Overlap review incomplete')
    require({Path(x['path']).name for x in prior} == CATALOGS and sum(x['collection_count'] for x in prior) == 43, 'Prior catalogs missing')
    require(sum(x['artifact_count'] for x in prior) == 327, 'Prior artifact coverage mismatch')
    for item in prior:
        require(item['path'] == 'data/evidence-program/research/' + Path(item['path']).name, 'Unsafe catalog reference path')
        require(re.fullmatch('[0-9a-f]{40}', item['git_blob_sha']) and re.fullmatch('[0-9a-f]{64}', item['sha256']), 'Catalog pin missing')
        ids = [r['candidate_id'] for r in item['compared_collections']]
        require(len(ids) == item['collection_count'] and len(set(ids)) == len(ids) and set(item['candidate_checks']) == IDS, 'Overlap collection identities missing')
        for relation in item['candidate_checks'].values():
            require(all(relation[k] is False for k in ['family_match_established', 'artifact_match_established', 'study_match_established', 'measurement_match_established'])
                    and relation['reviewed_collection_ids'] == ids and relation['semantic_review'], 'Overlap distinction lost')
        if root is not None:
            raw = (Path(root) / item['path']).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == item['sha256']
                    and hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['git_blob_sha'], 'Reviewed prior catalog changed')
            prior_document = json.loads(raw)
            prior_rows = prior_document.get('collections', prior_document.get('families', []))
            require([r['candidate_id'] for r in prior_rows] == ids and sum(len(r['artifacts']) for r in prior_rows) == item['artifact_count'], 'Prior identity/artifact coverage differs')
    impl = catalog['offline_validator']
    require(impl['implemented'] is True and impl['input_kind'] == 'manually_curated_versioned_table_excerpt', 'Implementation status changed')
    require(all(impl[k] is False for k in ['source_html_parser_implemented', 'network_access', 'robot_or_harness_execution', 'source_script_execution', 'canonical_import', 'validation_is_source_truth_verification']), 'Proposed/implemented boundary changed')
    require(impl['source_artifact_sha256'] is None and (impl['expected_reported_attempts'], impl['expected_courses'], impl['expected_teams']) == (60, 12, 4), 'Attempt/summary identity changed')
    require(len(catalog['next_actions']) == 8 and [x['status'] for x in catalog['next_actions']] == ['completed', 'completed', 'held', 'held', 'held', 'held', 'held', 'pending_separate_review'], 'Action status changed')
    require(len(catalog['holds']) == 5 and {x['candidate_id'] for x in catalog['holds']} == IDS and all(x['status'] == 'held_for_separate_work' for x in catalog['holds']), 'Source holds missing')
    require(len(catalog['focused_follow_up_prompts']) == 6 and len(catalog['corrections']) == 7, 'Follow-up or correction missing')
    for p in catalog['focused_follow_up_prompts']:
        require('Read-only public-source research only.' in p['prompt']
                and 'No login, outreach, bulk download, access-control bypass' in p['prompt']
                and 'No repository edits, canonical admission' in p['prompt'], 'Follow-up scope boundary missing')
    for phrase in ['60', 'CC BY 4.0', 'Safety OR Stalled', '327', '40', 'not an HTML scraper']:
        require(phrase in markdown, 'Guide/catalog boundary mismatch: ' + phrase)
    return {'robotics_physical_collections': 5, 'unadmitted_robotics_physical_collections': 5,
            'robotics_artifact_references': len(artifacts), 'robotics_qualified_findings': len(findings),
            'robotics_prior_catalogs_compared': 8, 'robotics_overlap_comparison_cells': 40,
            'robotics_source_html_extractors': 0}

GUARDS = {'all_reported_and_credited_denominators_separate': True,
 'failure_x_is_missing_or_zero': False,
 'item_count_is_independent_episode_count': False,
 'live_collection_enabled': False,
 'physical_simulation_staged_sustained_separate': True,
 'protocol_prohibition_is_measured_intervention_count': False,
 'proxy_to_pdoom_allowed': False,
 'reported_position_is_chronological_trial_id': False,
 'requested_assistance_means_unattended_autonomy': False,
 'rights_unknown_implies_permission': False,
 'robot_controls_enabled': False,
 'snapshot_integrity_notice_proves_filtering': False,
 'source_artifact_rights_scoped': True,
 'source_code_execution_enabled': False,
 'source_version_url_is_full_byte_hash': False,
 'success_preference_partial_progress_separate': True,
 'universal_robot_capability_score_enabled': False,
 'unknown_reset_practice_checkpoint_preserved': True,
 'video_count_is_episode_count': False}

QUALIFICATIONS = {'barn': {'chronological_order_verified': False,
          'cross_year_pooling': False,
          'failures': 40,
          'individual_credit_membership_verified': False,
          'native_trial_ids_available': False,
          'published_averages_equal_fastest_three': False,
          'reported_cells': 60,
          'source_artifact_sha256': None,
          'successes': 20,
          'table': 'II',
          'version': '2407.01862v1'},
 'phail': {'appendix_claimed_denominator': 'episodes',
           'cohort_arithmetic_is_membership_proof': False,
           'cohort_membership_reconciled': False,
           'current_ui_horizon_s': 120,
           'paper_caption_definition': 'safety-stop episodes',
           'paper_horizon_s': 240,
           'sample_adds_new_episodes': False,
           'sample_episode_count': 1,
           'sample_item_count': 8,
           'separate_aggregate_denominator': 'operations',
           'table_2_matches_safety_only_definition': False,
           'table_builder_proxy': 'Safety OR Stalled'},
 'roboarena': {'current_notice_display_verified': False,
               'duration_unit': None,
               'integrity_exclusions_applied_to_snapshot': None,
               'notice_commented_out_in_current_source': True,
               'partial_success_normalized': None,
               'partial_success_raw': 0.1,
               'personal_evaluator_fields_retained': False,
               'policy_episodes': 10783,
               'raw_duration': 399,
               'sample_yaml_has_copy_marker': False,
               'sessions': 3883,
               'snapshot_overlap_established': True,
               'videos': 27148},
 'rrc2020': {'documented_cube_jobs': 2856,
             'documented_cuboid_jobs': 7422,
             'index_acquired': False,
             'index_row_count_reproduced': False,
             'later_rl_correction_applies_to_2020': False,
             'later_rl_same_underlying_runs_established': False,
             'license': 'CC-BY-NC-SA-4.0',
             'mixed_development_and_evaluation': True},
 'strands': {'bumper_successful_attempts': 177,
             'bumper_unsuccessful_attempts': 148,
             'continuous_runs_2014_2015': 43,
             'data_fraction_definition': None,
             'dataset_license': None,
             'distance_unit': None,
             'recovery_period': '2015 deployments',
             'requested_assistance_allowed': True,
             'spreadsheet_license': None,
             'unattended_autonomy_established': False}}

SAMPLES = {'RP001': [{'evidence_artifact_ids': ['rp001_report'],
            'fields': {'course': 1,
                       'reported_values': ['32', '31', '32', '27', '30'],
                       'team': 'LiCS-KI',
                       'time_unit': 'seconds'},
            'kind': 'observed_table_row',
            'qualification': 'Five displayed positions; chronological order unverified.',
            'source_locator': 'Table II, LiCS-KI, Course 1'},
           {'evidence_artifact_ids': ['rp001_report'],
            'fields': {'AIMS': {'denominator': 15, 'successes': 5},
                       'EIT-NUS': {'denominator': 15, 'successes': 0},
                       'LiCS-KI': {'denominator': 15, 'successes': 10},
                       'MLDA_EEE': {'denominator': 15, 'successes': 5}},
            'kind': 'derived_all_reported_attempts',
            'qualification': 'Computed from all 60 published numeric/X cells; failures stay reported failed '
                             'attempts, with null time and unknown cause.',
            'source_locator': 'Table II, all four teams and three courses'},
           {'evidence_artifact_ids': ['rp001_report'],
            'fields': {'AIMS': {'denominator': 9, 'successes': 5},
                       'EIT-NUS': {'denominator': 9, 'successes': 0},
                       'LiCS-KI': {'denominator': 9, 'successes': 6},
                       'MLDA_EEE': {'denominator': 9, 'successes': 5}},
            'kind': 'reported_credited_contest_results',
            'qualification': 'Contest denominator is selected credit, not total attempts performed.',
            'source_locator': 'Table II, success-rate column and physical scoring rule'}],
 'RP002': [{'evidence_artifact_ids': ['rp002_session'],
            'fields': {'binary_success': [0, 0],
                       'duration_raw': [399, 399],
                       'duration_unit': None,
                       'exact_checkpoints': [None, None],
                       'partial_success_raw': [0.1, 0.1],
                       'partial_success_scale': None,
                       'policies': ['paligemma_fast_droid', 'paligemma_fast_specialist_droid'],
                       'preference': 'TIE',
                       'session_date': '2025-10-17',
                       'task': 'Open the fridge door'},
            'kind': 'observed_selected_session',
            'qualification': 'Personal evaluator information omitted. Partial scale and duration units '
                             'unverified.',
            'source_locator': 'Session metadata: task, preference and policy outcome fields'}],
 'RP003': [{'evidence_artifact_ids': ['rp003_docs'],
            'fields': {'database_rows_inspected': False,
                       'documented_max_height_unit': 'metres',
                       'fields': ['job_id',
                                  'start_time',
                                  'challenge_phase',
                                  'robot_name',
                                  'difficulty_level',
                                  'cumulative_reward',
                                  'baseline_reward',
                                  'initial_distance_to_goal',
                                  'min_distance_to_goal',
                                  'max_height']},
            'kind': 'observed_documented_schema',
            'qualification': 'Schema from documentation; no actual SQLite row or index checksum claimed.',
            'source_locator': 'Dataset documentation: index fields'}],
 'RP004': [{'derived_annotations': {'duration_unit': 'seconds',
                                    'duration_unit_basis': 'Dataset-card documentation; not a source JSON '
                                                           'key',
                                    'independent_episode_count': 1},
            'evidence_artifact_ids': ['rp004_sample'],
            'fields': {'eval.cap_per_item': 30,
                       'eval.duration': 193.2486054940091,
                       'eval.object': 'Wooden spoons',
                       'eval.outcome': 'Success',
                       'eval.successful_items': 8,
                       'eval.total_items': 8,
                       'model': 'groot',
                       'variant': '270226-ee_rot6d_rel:150000'},
            'kind': 'observed_selected_episode',
            'qualification': 'Dotted keys are literal JSON keys; derived unit and episode-count annotations '
                             'are separate from source fields. Eight items belong to one selected episode; '
                             'sample/ contains existing episodes.',
            'source_locator': 'static.json: model/variant and eval.* fields'},
           {'evidence_artifact_ids': ['rp004_paper',
                                      'rp004_builder',
                                      'rp004_table_aggregate',
                                      'rp004_operation_metric'],
            'fields': {'appendix_f_percent': 12.2,
                       'model': 'SmolVLA',
                       'reconciled': False,
                       'table_2_percent': 18.6},
            'kind': 'conflicting_published_intervention_rates',
            'qualification': 'Table 2 caption and Appendix F both claim episode-based safety-stop '
                             'percentages but conflict. Table 2 matches code-defined Safety OR Stalled '
                             'aggregates. Separate fig_intervention_meta uses per-operation drops+safety and '
                             'is not a replacement.',
            'source_locator': 'Table 2 versus Appendix F'}],
 'RP005': [{'evidence_artifact_ids': ['rp005_sheet'],
            'fields': {'Data': 0.5,
                       'Data available': 1,
                       'Data_fraction_definition': None,
                       'Distance': 2017.15,
                       'Distance_unit': None,
                       'Hours': 9.99,
                       'Robot active': 1,
                       'date': '2016-11-21'},
            'kind': 'observed_daily_aggregate',
            'qualification': 'Inactive available days and missing observations are different; exact Distance '
                             'unit and fractional Data definition are unverified.',
            'source_locator': 'Daily report, 21 November 2016 row and COL legend'},
           {'evidence_artifact_ids': ['rp005_paper'],
            'fields': {'independent_deployment_failures': None,
                       'period': '2015 deployments',
                       'requested_human_help': True,
                       'successful_attempts': 177,
                       'trigger': 'bumper',
                       'unit': 'recovery_attempt',
                       'unsuccessful_attempts': 148},
            'kind': 'observed_recovery_aggregate',
            'qualification': 'Recovery attempts can repeat after one failure. Count is not an '
                             'unattended-autonomy rate.',
            'source_locator': 'Recovery table and recovery-success definition'}]}

COVERAGE = {'RP001': {'date_roles_separate': True,
           'event_dates': ['2024-05-15', '2024-05-16'],
           'family_editions': '2022–2026 annual organizer collection',
           'report_published': '2024-07-02',
           'report_version': '2407.01862v1',
           'selected_edition': 2024},
 'RP002': {'count_units_separate': True,
           'earlier_snapshot': '2026-02-03',
           'february_dataset_commit': '1e7e7d092bf21eadec5816cc6603476cbe1eee10',
           'february_release_last_modified': '2026-02-04T20:52:35Z',
           'july_dataset_commit': '7931db81f3f6a48a3245427f7213a4c461f92ccc',
           'latest_paper_publication': '2025-11-29',
           'latest_verified_paper': '2506.18123v2',
           'paper_first_published': '2025-06',
           'policy_episodes': 10783,
           'selected_snapshot': '2026-07-17',
           'sessions': 3883,
           'videos': 27148},
 'RP003': {'challenge_period': '2020-08–2020-12',
           'mixed_development_and_weekly_evaluation': True,
           'phase_2_cube_jobs': 2856,
           'phase_3_cuboid_jobs': 7422,
           'simulator_qualification_in_archive': False},
 'RP004': {'cohorts_reconciled': False,
           'collection_is_synthetic': False,
           'collection_period': '2025-11–2026-05',
           'current_website_home_updated': '2026-10-05',
           'dataset_commit': '5bc590213c5d2615eefeb47bc23a700f8c57022a',
           'dataset_publication': '2026-05-06',
           'paper_publication': '2026-05-28',
           'paper_repo_commit': '18ce72d5703dcbbbb10a980336aa5a1622601fb4',
           'release': 'v1.0',
           'reported_cohorts': {'hf_card': {'human': 40, 'policy': 524, 'training': 449},
                                'paper_v1': {'human': 396, 'policy': 599, 'training': 449},
                                'website_release': {'human': None, 'policy': 594, 'training': 352}}},
 'RP005': {'earlier_continuous_runs': 43,
           'earlier_study': '2014–2015',
           'later_daily_dataset': '2016-11–2017-04',
           'recovery_table_period': '2015 deployments',
           'separate_deployment_artifacts': True}}

REGIMES = {'RP001': 'staged_physical_contest',
 'RP002': 'episodic_physical_comparison',
 'RP003': 'physical_development_and_evaluation_jobs',
 'RP004': 'episodic_physical_laboratory',
 'RP005': 'sustained_physical_deployment'}


def check_barn_fixture(catalog, root):
    from validate_barn_table import read_table, MAX_BYTES, MAX_DEPTH, MAX_ROWS, MAX_SUMMARIES, MAX_STRING_BYTES, MAX_TIME_SECONDS
    impl = catalog['offline_validator']
    expected_path = 'tools/evidence_program/tests/fixtures/robotics-physical/barn-2024-table-ii.json'
    expected_hash = 'f79a2b58fa8771b766890627bf59e9f710acb5af1da397510dfdf4763cc8bd5e'
    require(impl['fixture_path'] == expected_path and impl['fixture_sha256'] == expected_hash and impl['fixture_bytes'] == 6584, 'Derived fixture identity changed')
    expected_bounds = (65536, 12, 120, 8, 2048, 86400)
    require((MAX_BYTES, MAX_DEPTH, MAX_ROWS, MAX_SUMMARIES, MAX_STRING_BYTES, MAX_TIME_SECONDS) == expected_bounds, 'Reader bounds changed')
    require(tuple(impl[k] for k in ['maximum_input_bytes', 'maximum_nesting_depth', 'maximum_input_rows', 'maximum_input_summaries', 'maximum_string_bytes', 'maximum_time_seconds']) == expected_bounds, 'Documented reader bounds differ')
    result = read_table(Path(root) / expected_path)
    require(result['input_curated_json_sha256'] == expected_hash and result['attempt_count'] == 60
            and len(result['course_summaries']) == 12 and len(result['team_summaries']) == 4, 'Fixture content/shape differs')
    require(result['source']['manuscript_sha256'] is None and result['canonical_import_enabled'] is False, 'Full source hash or admission fabricated')
    require(sum(x['status'] == 'successful' for x in result['attempts']) == 20, 'Source success count differs')
    expected = {'LiCS-KI': (10, 6), 'MLDA_EEE': (5, 5), 'AIMS': (5, 5), 'EIT-NUS': (0, 0)}
    for row in result['team_summaries']:
        all_count, credit = expected[row['team_raw']]
        require(row['all_reported_attempts']['successful'] == all_count and row['all_reported_attempts']['denominator'] == 15
                and row['credited_subset'] == {'successful': credit, 'denominator': 9}, 'All-reported/credit denominators differ')
    return {'robotics_reported_attempts': 60, 'robotics_reported_successes': 20,
            'robotics_reported_failures': 40, 'robotics_course_summaries': 12,
            'robotics_team_summaries': 4, 'robotics_licensed_table_fixtures': 1}
