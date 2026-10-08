"""Offline metadata consistency checks; neither source admission nor legal approval."""
from __future__ import annotations

import re
from urllib.parse import urlsplit, parse_qsl

IDS = {f'OM{i:03}' for i in range(1, 6)}
PINS = [
    ('e39b4edd41811e975f9262d77ee286796d7792e5', 'ce4e77557ac41d97ec59d872a2d6b7f19229ecdb',
     '89d1f517d5171d832c59359e83d6c7b7577aaf0c14f8a06c08b01adbbcdfcc17', 3648),
    ('ff85b6ff442035e41c9492cefa54f78be0b827fc', '855671b61e19ccdefa95879c0d85a4c5eb77dc5f',
     'cc93e48df6a72c3e15d05ae2a056fcf775d4ccf7c590bc26c13ebbdb9fea6ec8', 3398),
]
GUARDS = {
    'open_weights_implies_open_source': False,
    'artifact_listing_implies_successful_download': False,
    'metadata_license_implies_model_license': False,
    'criteria_removal_implies_access_revocation': False,
    'current_access_label_dates_first_availability': False,
    'download_count_implies_unique_adopters': False,
    'static_dependency_implies_execution': False,
    'materials_imply_successful_reproduction': False,
    'proxy_to_pdoom_allowed': False,
    'source_categories_preserved_without_our_verdict': True,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_url(url):
    require(isinstance(url, str), 'Open-model URL must be a string')
    u = urlsplit(url)
    require(u.scheme == 'https' and u.hostname and not u.username and not u.password and
            not any(c.isspace() for c in url), 'Unsafe open-model artifact URL')
    require(not any(any(s in k.lower() for s in ['signature', 'token', 'credential', 'secret', 'key'])
                    for k, _ in parse_qsl(u.query)), 'Signed or credential URL forbidden')


def check_catalog(catalog, inventory_hash, markdown):
    require(catalog['status'] == 'review_prepared_with_offline_reader' and
            catalog['operational_admission'] == 'not_admitted' and catalog['collector_enabled'] is False and
            catalog['canonical_contract_mapping'] == 'pending_separate_review',
            'Open-model catalog cannot enable operational collection or admission')
    require(catalog['repository_review_commit'] == '4ecece6abd322932f70f121aef2e99fc3be467bb' and
            catalog['baseline_inventory']['sha256'] == inventory_hash and
            catalog['baseline_inventory']['source_family_count'] == 64,
            'Open-model frozen inventory mismatch')
    require(catalog['raw_source_content_in_catalog'] is False and
            catalog['fixture_acquisition'] == {'status': 'two_pinned_annotation_files_only',
                                             'count': 2, 'candidate_id': 'OM002',
                                             'location': 'tools/evidence_program/tests/fixtures/open-model-yaml',
                                             'annotation_license': 'CC-BY-4.0'},
            'Open-model fixture acquisition must remain separate and scoped')
    require(catalog['ranking_basis'] == 'source_utility_for_diffusion_accessibility' and
            [x['candidate_id'] for x in catalog['priority_ranking']] == ['OM001', 'OM002', 'OM003'],
            'Open-model ranking must preserve source-utility scope')
    require(catalog['interpretation_guards'] == GUARDS, 'Open-model interpretation guard changed')
    rows = catalog['collections']
    by_id = {r['candidate_id']: r for r in rows}
    require(len(rows) == len(by_id) == 5 and by_id.keys() == IDS, 'Open-model collection IDs/count mismatch')
    all_artifacts, findings = set(), set()
    for cid, row in by_id.items():
        require(row['operational_admission'] == 'not_admitted' and row['collector_enabled'] is False,
                'Open-model family cannot enable collection or admission')
        require(row['classification'] == ('existing_family_enrichment' if cid == 'OM003' else 'new_relative_to_frozen_inventory'),
                'Open-model family classification changed')
        require(row['inventory_source_id'] == ('GL001' if cid == 'OM003' else None),
                'Open-model inventory source identity changed')
        for field in ['name', 'summary', 'historical_coverage', 'update_frequency', 'access_method',
                      'rights_summary', 'duplicate_evidence_policy']:
            require(isinstance(row.get(field), str) and row[field].strip(), f'Missing open-model {field}')
        require(row['sample_fields'] and row['limitations'] and row['findings'], 'Missing open-model sample or limitation')
        artifacts = {a['artifact_id']: a for a in row['artifacts']}
        require(artifacts and len(artifacts) == len(row['artifacts']) and not artifacts.keys() & all_artifacts,
                'Duplicate or missing open-model artifact')
        for a in artifacts.values():
            safe_url(a['url'])
            require(a['provenance_locator'] and a['inspection_note'] and a['reviewed_on'] == catalog['reviewed_on'],
                    'Open-model artifact lacks scoped dated verification')
            require(a['access_status'] in {'primary_opened', 'documentation_only', 'pointer_only',
                                          'access_unverified', 'blocked', 'pinned_bytes_verified'},
                    'Unknown open-model artifact access state')
            require(a['rights_status'] in {'declared_license', 'restricted_use', 'unknown'} and
                    a['rights_scope'] and a['rights_note'], 'Open-model artifact lacks scoped rights')
            require(set(a['rights_evidence_artifact_ids']) <= artifacts.keys(), 'Unknown open-model rights evidence')
            if a['rights_status'] != 'unknown':
                require(a['license_identifier'] and a['rights_evidence_artifact_ids'], 'Open-model rights declaration lacks provenance')
            require(a['raw_content_in_catalog'] is False, 'Open-model raw source material belongs only in scoped fixture files')
            if a.get('sha256') is not None:
                require(re.fullmatch('[a-f0-9]{64}', a['sha256']), 'Invalid open-model artifact hash')
        for f in row['findings']:
            require(f['finding_id'] not in findings and f['text'] and f['evidence_artifact_ids'] and
                    set(f['evidence_artifact_ids']) <= artifacts.keys(), 'Open-model finding lacks unique provenance')
            require(f['evidence_kind'] in {'source_reported_metadata', 'assessor_annotation', 'byte_verified_diff',
                                          'documentation', 'study_reported_measurement', 'access_or_rights_qualification'},
                    'Open-model finding evidence class invalid')
            findings.add(f['finding_id'])
        all_artifacts.update(artifacts)
    eu = by_id['OM002']
    lookup = {a['artifact_id']: a for a in eu['artifacts']}
    for key, expected in zip(['eu_before', 'eu_after'], PINS):
        a = lookup[key]
        require(tuple(a[k] for k in ['git_commit', 'git_blob_sha', 'sha256', 'size_bytes']) == expected,
                'Open-model fixture integrity pins changed')
        require(a['rights_status'] == 'declared_license' and a['license_identifier'] == 'CC-BY-4.0' and
                a['rights_scope'] == 'annotation_data_only_excludes_models_and_linked_works',
                'Annotation rights must not clear models or linked works')
    spec = catalog['offline_reader']
    require(spec['status'] == 'implemented_offline_only' and spec['candidate_id'] == 'OM002' and
            spec['input_count'] == 2 and spec['maximum_bytes_per_file'] == 65536 and
            spec['fixed_hash_allowlist'] is True and spec['network_enabled'] is False and
            spec['evidence_link_traversal'] is False and spec['production_import'] is False,
            'Open-model reader bounded scope changed')
    require(spec['output_status'] == 'experimental_review_records_not_admitted' and
            spec['criterion_counts'] == [14, 12] and spec['criteria_removed'] == ['api', 'package'] and
            spec['criteria_set_change_count'] == 1 and spec['surviving_value_changes'] == 0 and
            spec['inferred_model_access_events'] == 0 and spec['inferred_model_license_events'] == 0,
            'Criteria-set change cannot become model access/license events')
    require(spec['release_date_raw'] == '2024-12' and spec['release_date_precision'] == 'month' and
            spec['assessment_timestamp'] is None and spec['canonical_schema_claim'] is False and
            spec['preserve_nested_unknown_fields'] is True and spec['null_links_preserved'] is True,
            'Open-model reader cannot invent dates or discard source fields')
    require(len(spec['acceptance_tests']) >= 10, 'Open-model reader acceptance evidence missing')
    require({x['id'] for x in catalog['corrections']} == {'baseline_refresh', 'rights_attribution_expand', 'hf_observation_clock', 'peat_sample_size', 'no_false_access_events'} and
            all(x['claim'] and x['status'] for x in catalog['corrections']), 'Open-model review corrections must be retained')
    actions = catalog['next_actions']; action_ids = {a['action_id'] for a in actions}
    require(actions and len(action_ids) == len(actions), 'Duplicate or missing open-model action')
    for a in actions:
        require(a['candidate_ids'] and set(a['candidate_ids']) <= IDS and a['action'] and a['completion_evidence'] and
                a['status'] in {'completed', 'open', 'pending_rights_review', 'blocked_access', 'pending_contract_review'},
                'Open-model action must have status and completion condition')
    for p in catalog['focused_follow_up_prompts']:
        require(p['action_id'] in action_ids and p['why_needed'] and p['prompt'] and
                next(a for a in actions if a['action_id'] == p['action_id'])['status'] != 'completed',
                'Open-model follow-up must address an open action')
    headings = re.findall(r'^## (OM[0-9]{3}) (.+)$', markdown, re.MULTILINE)
    require(len(headings) == 5 and dict(headings) == {k: v['name'] for k, v in by_id.items()},
            'Open-model documentation IDs/titles mismatch')
    return {'open_model_collections': 5, 'open_model_artifact_references': len(all_artifacts),
            'open_model_findings': len(findings), 'unadmitted_open_model_collections': 5,
            'open_model_research_fixtures': 2}
