"""Offline historical-research metadata checks; no source fetch or admission."""
from __future__ import annotations
import re
from urllib.parse import parse_qsl, urlsplit

BASE = 'bc00b609473c19c76869839598b63e1c8ace9ccc'
IDS = {f'HC{i:03}' for i in range(1, 6)}
PIN = 'f49c4f058173c45b0c3ff455be8024ed13d98656810127297d815a502587cbac'
DISTINCTIONS = ['original_run', 'repeated_report', 'corrected_assertion', 'rescoring_same_outputs', 'later_rerun', 'benchmark_dependence']
GUARDS = {
    'universal_capability_curve_enabled': False,
    'proxy_to_pdoom_allowed': False,
    'event_date_implies_publication_date': False,
    'transport_date_implies_first_publication': False,
    'archive_copy_date_implies_execution_date': False,
    'benchmark_vintage_implies_evaluation_date': False,
    'rescoring_implies_new_system_run': False,
    'planned_rerun_implies_observed_rerun': False,
    'absent_score_implies_zero_or_failure': False,
    'weak_result_implies_abandoned_system': False,
    'penalty_seconds_imply_measured_runtime': False,
    'multiple_metrics_imply_independent_experiments': False,
    'archival_coverage_implies_all_attempts': False,
    'paper_license_inherits_to_data': False,
    'government_hosting_implies_open_license': False,
    'unknown_system_identity_may_be_guessed': False,
    'raw_labels_and_exact_decimals_preserved': True,
    'artifact_specific_rights_and_access_required': True,
}
DATE_ROLES = {'competition_edition', 'event', 'result_publication', 'announcement', 'html_generated',
              'preservation', 'transport_last_modified', 'retrieval', 'paper_publication', 'preface_signature',
              'proposed_schedule', 'run_completion', 'catalog_publication_claim'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_url(url):
    require(isinstance(url, str), 'Historical artifact URL must be text')
    p = urlsplit(url)
    require(p.scheme == 'https' and p.hostname and not p.username and not p.password and
            not any(c.isspace() for c in url), 'Unsafe historical artifact URL')
    require(not any(any(x in k.lower() for x in ('token', 'secret', 'credential', 'signature', 'key'))
                    for k, _ in parse_qsl(p.query)), 'Signed historical artifact URL forbidden')


def check_catalog(catalog, inventory_hash, markdown):
    require(catalog['status'] == 'review_prepared_with_offline_reader' and
            catalog['operational_admission'] == 'not_admitted' and catalog['collector_enabled'] is False and
            catalog['canonical_contract_mapping'] == 'pending_separate_review', 'Historical admission boundary changed')
    require(catalog['repository_review_commit'] == BASE and
            catalog['baseline_inventory']['sha256'] == inventory_hash and
            catalog['baseline_inventory']['source_family_count'] == 64, 'Historical frozen inventory mismatch')
    require(catalog['record_distinctions'] == DISTINCTIONS and catalog['interpretation_guards'] == GUARDS,
            'Historical interpretation boundaries changed')
    require(catalog['full_source_bodies_in_catalog'] is False and catalog['full_score_results_in_repository'] is False and
            catalog['real_gzip_vendored'] is False, 'Historical raw-result redistribution is not approved')
    require(catalog['ranking_basis'] == 'source_utility_not_capability_or_risk' and
            [x['candidate_id'] for x in catalog['priority_ranking']] == ['HC001', 'HC002', 'HC003'],
            'Historical ranking basis changed')
    rows = catalog['collections']; by_id = {r['candidate_id']: r for r in rows}
    require(len(rows) == len(by_id) == 5 and by_id.keys() == IDS, 'Historical collection IDs/count mismatch')
    all_artifacts, all_findings = set(), set()
    for cid, row in by_id.items():
        require(row['classification'] == 'new_relative_to_frozen_inventory' and row['inventory_source_id'] is None and
                row['operational_admission'] == 'not_admitted' and row['collector_enabled'] is False,
                'Historical family cannot allocate source IDs or admission')
        for key in ('name', 'summary', 'historical_coverage', 'update_frequency', 'access_method', 'rights_summary', 'duplicate_evidence_policy'):
            require(isinstance(row.get(key), str) and row[key].strip(), f'Historical field missing: {key}')
        require(row['limitations'] and row['samples'] and row['findings'], 'Historical evidence/limitations missing')
        arts = {a['artifact_id']: a for a in row['artifacts']}
        require(len(arts) == len(row['artifacts']) and arts and not arts.keys() & all_artifacts,
                'Historical duplicate artifact identity')
        for a in arts.values():
            safe_url(a['url'])
            require(a['reviewed_on'] == catalog['reviewed_on'] and a['provenance_locator'] and a['inspection_note'],
                    'Historical artifact provenance missing')
            require(a['access_status'] in {'primary_opened', 'pinned_bytes_verified_private', 'link_verified_not_downloaded',
                                          'access_conditional_not_accessed', 'blocked_size_limit', 'access_unverified'},
                    'Historical artifact access state invalid')
            require(a['rights_status'] in {'unknown', 'declared_license', 'restricted_use'} and
                    a['rights_scope'] and a['rights_note'] and set(a['rights_evidence_artifact_ids']) <= arts.keys(),
                    'Historical artifact rights scope invalid')
            if a['rights_status'] != 'unknown':
                require(a['rights_evidence_artifact_ids'] and a['license_identifier'], 'Historical rights evidence missing')
            require(a['source_body_vendored'] is False, 'Historical third-party source body cannot be vendored')
            if a.get('sha256'):
                require(re.fullmatch(r'[a-f0-9]{64}', a['sha256']), 'Historical hash invalid')
        for sample in row['samples']:
            require(sample['fields'] and sample['qualification'] and sample['evidence_artifact_ids'] and
                    set(sample['evidence_artifact_ids']) <= arts.keys(), 'Historical sample provenance missing')
        for f in row['findings']:
            require(f['finding_id'] not in all_findings and f['text'] and f['qualification'] and
                    f['evidence_artifact_ids'] and set(f['evidence_artifact_ids']) <= arts.keys(),
                    'Historical finding provenance or identity invalid')
            all_findings.add(f['finding_id'])
        for date in row['date_observations']:
            require(date['role'] in DATE_ROLES and date['precision'] in {'year', 'month', 'day', 'second', 'range', 'source_string'} and
                    date['value'] and date['qualification'] and date['evidence_artifact_ids'] and
                    set(date['evidence_artifact_ids']) <= arts.keys(), 'Historical date role/provenance invalid')
        all_artifacts.update(arts)
    q = catalog['critical_qualifications']
    require(q['ipc']['rescored_2008_same_runs'] is True and q['ipc']['post_bugfix_2002_lpg_new_runs'] is True and
            q['ipc']['success_only_2002_files_imply_complete_failure_matrix'] is False and
            q['ipc']['compressed_archive_members_inspected'] is False, 'IPC evaluation or archive scope conflated')
    w = q['wmt']
    require(w['gzip_sha256'] == PIN and w['compressed_bytes'] == 16071 and w['decompressed_bytes'] == 113529 and
            w['row_count'] == 2584 and w['metric_count'] == 17 and w['system_type_counts'] == {'smt':1703,'rbmt':843,'syscomb':38} and
            w['rights_status'] == 'unknown' and w['paper_license_inherits_to_gzip'] is False and
            w['direction_as_published'] == 'higher_is_better' and w['mter_already_reversed'] is True and
            w['rank_is_ordinal_position'] is False and w['score_range_is_universal_zero_to_one'] is False and
            w['rows_are_independent_experiments'] is False and w['all_english_judgments_reused_in_news_pairs'] is True,
            'WMT score pin, rights, direction or dependence conflated')
    require(w['workshop_date'] == '2008-06-19' and w['paper_publication_month'] == '2008-06' and
            w['artifact_first_publication_at'] is None and w['execution_time'] is None and w['archive_capture_at'] is None and
            w['http_last_modified'] == '2008-08-20T15:25:44Z' and
            w['http_last_modified_role'] == 'transport_metadata_not_first_publication' and
            w['denominator'] is None and w['uncertainty'] is None and w['anonymized_identity_resolution'] == 'unresolved',
            'WMT unknowns or date roles changed')
    require(q['trec']['p10_conflict_resolved'] is False and q['trec']['raw_results_archive_access'] == 'signed_agreement_required_not_accessed' and
            q['trec']['paper_rights_status'] == 'unknown' and q['trec']['settled_publication_precision'] == 'year' and
            q['trec']['settled_publication_value'] == '1994' and q['trec']['facsimile_verified'] is False,
            'TREC correction, access or date qualification lost')
    require(q['sat']['blank_is_diagnosed_timeout'] is False and q['sat']['crash_penalty_is_runtime'] is False and
            q['sat']['planned_rerun_is_verified_result'] is False and q['sat']['may_6_and_9_dates_are_tentative_schedule'] is True,
            'SAT schedule, failure or runtime qualification lost')
    require(q['voc']['weak_score_proves_abandonment'] is False and q['voc']['modern_submission_backdated_to_benchmark_year'] is False and
            q['voc']['classification_ap_applies_to_all_tasks'] is False and q['voc']['result_table_rights_status'] == 'unknown' and
            q['voc']['metric_break_years'] == ['2007', '2010'], 'VOC task, date or rights qualification lost')
    spec = catalog['offline_reader']
    require(spec['status'] == 'implemented_offline_only' and spec['candidate_id'] == 'HC002' and spec['input_count'] == 1 and
            spec['fixed_hash_allowlist'] is True and spec['expected_sha256'] == PIN and
            spec['maximum_compressed_bytes'] == 32768 and spec['maximum_decompressed_bytes'] == 262144 and
            spec['maximum_rows'] == 4096 and spec['maximum_line_bytes'] == 1024 and spec['maximum_field_bytes'] == 128 and
            spec['maximum_score_characters'] == 64 and spec['finite_exact_decimal_strings'] is True and
            spec['reject_concatenated_members_and_trailing_bytes'] is True and spec['network_enabled'] is False and
            spec['production_import'] is False and spec['canonical_schema_claim'] is False and
            spec['ci_source'] == 'self_authored_synthetic_only' and spec['real_artifact_vendored'] is False and
            spec['output_status'] == 'experimental_review_records_not_admitted', 'Historical reader scope changed')
    require(spec['synthetic_real_provenance_separated'] is True and len(spec['acceptance_tests']) >= 10,
            'Historical synthetic isolation or acceptance coverage missing')
    require(catalog['verification_separation']['ci_reads_real_wmt_artifact'] is False and
            catalog['verification_separation']['private_real_acceptance']['status'] == 'passed' and
            catalog['verification_separation']['private_real_acceptance']['full_output_published'] is False,
            'Historical CI/private acceptance boundary changed')
    gzip = next(a for a in by_id['HC002']['artifacts'] if a['artifact_id'] == 'hc002_gzip')
    require(gzip['rights_status'] == 'unknown' and gzip['license_identifier'] is None and
            gzip['sha256'] == PIN and gzip['access_status'] == 'pinned_bytes_verified_private', 'WMT gzip rights cannot inherit paper license')
    trec_samples = by_id['HC003']['samples']
    require([(s['fields']['run_label_raw_ocr'], s['fields']['score_raw']) for s in trec_samples] ==
            [('isiasm', '.3018'), ('isial', '.1307'), ('lsial*', '.2505')],
            'TREC raw OCR labels and score lexemes must be preserved')
    holds = catalog['holds']
    require(len(holds) == 7 and {h['id'] for h in holds} == {f'HIST-H{i:02}' for i in range(1, 8)} and
            all(h['scope'] and h['reason'] and h['release_condition'] for h in holds),
            'Historical evidence holds missing')
    actions = catalog['next_actions']; action_ids = {a['action_id'] for a in actions}
    require(actions and len(action_ids) == len(actions), 'Historical action IDs invalid')
    for a in actions:
        require(a['candidate_ids'] and set(a['candidate_ids']) <= IDS and a['action'] and a['completion_evidence'] and
                a['status'] in {'completed', 'open', 'pending_rights_review', 'blocked_access', 'pending_contract_review'},
                'Historical next action needs scope/status/evidence')
    prompts = catalog['focused_follow_up_prompts']
    require(len({p['action_id'] for p in prompts}) == len(prompts) and
            {p['action_id'] for p in prompts} == {a['action_id'] for a in actions if a['status'] != 'completed'} and
            all(p['why_needed'] and p['prompt'] for p in prompts), 'Historical open actions need focused prompts')
    require(catalog['corrections'] and all(c['claim'] and c['qualification'] for c in catalog['corrections']),
            'Historical corrections missing')
    headings = re.findall(r'^## (HC[0-9]{3}) (.+)$', markdown, re.MULTILINE)
    require(len(headings) == 5 and dict(headings) == {k:v['name'] for k,v in by_id.items()},
            'Historical guide/catalog headings mismatch')
    return {'historical_backfill_collections':5, 'historical_backfill_artifact_references':len(all_artifacts),
            'historical_backfill_findings':len(all_findings), 'unadmitted_historical_backfill_collections':5,
            'historical_backfill_real_vendored_fixtures':0}
