"""Offline consistency checks for qualified dependency research, not source admission."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit

IDS = {f'CD{i:03}' for i in range(1, 6)}
BASE = '3a981281b59c91d29dd1b5157dfd90eac087c004'
FIXTURE_SHA256 = '9d11eaee99763097abb9bdc995fb03ad6e38d961c2110e711204ddd8cca32583'
RELATIONSHIPS = ['ownership_economic_rights', 'contractual_access', 'disclosed_operational_use',
                 'resolved_software_dependency', 'survey_concentration']
GUARDS = {
    'ownership_implies_operational_dependence': False,
    'contractual_access_implies_utilization': False,
    'disclosed_use_implies_measured_workload': False,
    'resolved_dependency_implies_installed_deployment': False,
    'sdk_dependency_implies_remote_service_use': False,
    'concentration_implies_failure_probability': False,
    'survey_nominations_imply_market_share': False,
    'multiple_providers_imply_working_failover': False,
    'missing_relationship_implies_independence': False,
    'anonymized_parties_may_be_inferred': False,
    'retrieval_dates_imply_graph_resolution_dates': False,
    'organization_fields_imply_corporate_ownership': False,
    'different_metadata_roles_imply_contradiction': False,
    'rights_inherit_across_linked_artifacts': False,
    'proxy_to_pdoom_allowed': False,
    'raw_fields_and_unknowns_preserved': True,
    'artifact_local_ids_imply_cross_snapshot_entity_identity': False,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_url(url):
    require(isinstance(url, str), 'Concentration URL must be text')
    p = urlsplit(url)
    require(p.scheme == 'https' and p.hostname and not p.username and not p.password and
            not any(c.isspace() for c in url), 'Unsafe concentration artifact URL')
    require(not any(any(word in key.lower() for word in ('signature', 'token', 'credential', 'secret', 'key'))
                    for key, _ in parse_qsl(p.query)), 'Signed or credential URL forbidden')


def check_catalog(catalog, inventory_hash, markdown):
    require(catalog['status'] == 'review_prepared_with_offline_reader' and
            catalog['operational_admission'] == 'not_admitted' and catalog['collector_enabled'] is False and
            catalog['canonical_contract_mapping'] == 'pending_separate_review',
            'Concentration research cannot enable collection or admission')
    require(catalog['repository_review_commit'] == BASE and
            catalog['baseline_inventory']['sha256'] == inventory_hash and
            catalog['baseline_inventory']['source_family_count'] == 64,
            'Concentration frozen inventory mismatch')
    require(catalog['relationship_classes'] == RELATIONSHIPS and catalog['interpretation_guards'] == GUARDS,
            'Concentration interpretation or relationship boundary changed')
    require(catalog['raw_source_content_in_catalog'] is False and catalog['participant_rows_in_catalog'] is False,
            'Concentration catalog cannot contain raw bodies or participant rows')
    require(catalog['ranking_basis'] == 'source_utility_not_risk_or_market_share' and
            [x['candidate_id'] for x in catalog['priority_ranking']] == ['CD001', 'CD002', 'CD003'],
            'Concentration ranking must remain source utility')
    require(catalog['fixture_acquisition'] == {'count': 1, 'candidate_id': 'CD002',
            'scope': 'one_generated_dependency_graph_only',
            'location': 'tools/evidence_program/tests/fixtures/concentration-dependencies',
            'license': 'CC-BY-4.0'}, 'Concentration fixture acquisition scope changed')
    rows = catalog['collections']; by_id = {r['candidate_id']: r for r in rows}
    require(len(rows) == len(by_id) == 5 and by_id.keys() == IDS, 'Concentration collection IDs/count mismatch')
    artifact_ids, finding_ids = set(), set()
    expected_basis = {'CD001': ['disclosed_operational_use'], 'CD002': ['resolved_software_dependency'],
                      'CD003': ['survey_concentration'], 'CD004': ['disclosed_operational_use'],
                      'CD005': ['ownership_economic_rights', 'contractual_access']}
    for cid, row in by_id.items():
        require(row['classification'] == 'new_relative_to_frozen_inventory' and row['inventory_source_id'] is None,
                'Concentration families must not allocate or duplicate inventory IDs')
        require(row['operational_admission'] == 'not_admitted' and row['collector_enabled'] is False,
                'Concentration family cannot enable collection or admission')
        require(row['relationship_basis'] == expected_basis[cid], 'Concentration evidence basis conflated')
        for key in ('name', 'summary', 'historical_coverage', 'update_frequency', 'access_method',
                    'rights_summary', 'duplicate_evidence_policy'):
            require(isinstance(row.get(key), str) and row[key].strip(), f'Missing concentration {key}')
        require(row['sample_fields'] and row['limitations'] and row['findings'], 'Missing concentration sample or limitation')
        arts = {a['artifact_id']: a for a in row['artifacts']}
        require(arts and len(arts) == len(row['artifacts']) and not arts.keys() & artifact_ids,
                'Duplicate concentration artifact identity')
        for a in arts.values():
            safe_url(a['url'])
            require(a['reviewed_on'] == catalog['reviewed_on'] and a['provenance_locator'] and a['inspection_note'],
                    'Concentration artifact lacks scoped dated provenance')
            require(a['access_status'] in {'primary_opened', 'pinned_bytes_verified', 'indexed_excerpt_only',
                                          'documentation_only', 'access_unverified', 'blocked'},
                    'Invalid concentration access state')
            require(a['rights_status'] in {'declared_license', 'government_material_policy', 'restricted_use', 'unknown'} and
                    a['rights_scope'] and a['rights_note'], 'Concentration artifact lacks scoped rights')
            require(set(a['rights_evidence_artifact_ids']) <= arts.keys(), 'Unknown concentration rights evidence')
            if a['rights_status'] != 'unknown':
                require(a['license_identifier'] and a['rights_evidence_artifact_ids'], 'Concentration rights declaration lacks evidence')
            require(a['raw_content_in_catalog'] is False, 'Raw concentration body cannot enter catalog')
            if a.get('sha256') is not None:
                require(re.fullmatch('[a-f0-9]{64}', a['sha256']), 'Invalid concentration hash')
        for f in row['findings']:
            require(f['finding_id'] not in finding_ids and f['text'] and f['qualification'] and
                    f['evidence_artifact_ids'] and set(f['evidence_artifact_ids']) <= arts.keys(),
                    'Concentration finding lacks unique scoped provenance')
            require(f['evidence_kind'] in {'disclosure', 'resolved_graph', 'survey_aggregate', 'administrative_metadata',
                                          'regulator_staff_finding', 'documentation', 'access_or_rights_qualification'},
                    'Concentration evidence kind invalid')
            finding_ids.add(f['finding_id'])
        artifact_ids.update(arts)
    q = catalog['critical_qualifications']
    require(q['atrs']['organization_roles'] == ['from_publishers', 'template_organization', 'body_operational_owner'] and
            q['atrs']['automatic_conflict_inference'] is False and q['atrs']['corporate_ownership_inference'] is False and
            q['atrs']['model_version_when_undisclosed'] is None and
            q['atrs']['redbox_publication_labels'] == {'page_published': '2025-04-28', 'body_date_published': '2025-04-29'},
            'ATRS metadata roles, missing versions or dates conflated')
    require(q['depsdev']['resolved_at'] is None and q['depsdev']['installed_at'] is None and
            q['depsdev']['root_package_publication_time'] == '2024-10-07T17:42:51Z' and
            q['depsdev']['package_license_is_dataset_license'] is False,
            'Dependency graph time or license inference forbidden')
    require(q['bank']['responding_firms_2024'] == 118 and
            q['bank']['top_three_share_percent_2024'] == {'cloud': 73, 'models': 44, 'data': 33} and
            q['bank']['denominator_raw'] == 'all named providers' and
            q['bank']['raw_category_denominator_counts'] is None and
            q['bank']['fixed_firm_panel_verified'] is False and q['bank']['report_ogl_verified'] is False,
            'Survey denominator, panel or rights boundary changed')
    require(q['omb']['rows'] == 900 and q['omb']['distinct_agency_labels'] == 45 and
            q['omb']['readme_submissions'] == 46 and q['omb']['count_discrepancy_resolved'] is False and
            q['omb']['all_flags_are_verbatim_agency_responses'] is False and
            q['omb']['per_product_user_band_allocation'] is None and q['omb']['csv_rights_status'] == 'unknown',
            'OMB counting units, normalized flags or rights conflated')
    require(q['ftc']['parity_parties'] == {'cloud_partner': None, 'model_developer': None} and
            q['ftc']['parity_evidence_origin'] == 'staff_summary_of_respondent_document_submissions' and
            q['ftc']['direct_contract_clause_inspected'] is False and
            q['ftc']['respondent_information_cutoff'] == '2024-09' and q['ftc']['public_information_cutoff'] == '2025-01' and
            q['ftc']['current_relationships_verified'] is False,
            'FTC anonymity, evidence origin or historical cutoff lost')
    spec = catalog['offline_reader']
    require(spec['status'] == 'implemented_offline_only' and spec['candidate_id'] == 'CD002' and
            spec['input_count'] == 1 and spec['maximum_bytes_per_file'] == 65536 and
            spec['fixed_hash_allowlist'] is True and spec['fixture_sha256'] == FIXTURE_SHA256 and
            spec['fixture_bytes'] == 3532 and spec['node_count'] == 18 and spec['edge_count'] == 23 and
            spec['network_enabled'] is False and spec['production_import'] is False and
            spec['output_status'] == 'experimental_review_records_not_admitted' and
            spec['preserve_raw_graph_and_unknown_fields'] is True and spec['canonical_schema_claim'] is False and
            spec['artifact_local_review_ids'] is True and spec['edge_id_references_resolve'] is True and
            spec['cross_snapshot_entity_merge'] is False,
            'Concentration reader bounded scope or fixture pins changed')
    require(len(spec['acceptance_tests']) >= 10, 'Concentration acceptance evidence missing')
    atrs = catalog['atrs_proposal']
    require(atrs['status'] == 'proposed_unimplemented' and atrs['record_count'] == 2 and
            atrs['automated_semantic_extractor'] is False and atrs['human_review_required'] is True and
            atrs['maximum_relationship_observations'] == 20 and atrs['network_enabled'] is False,
            'ATRS proposal cannot become automatic extraction or collection')
    graph = next(a for a in by_id['CD002']['artifacts'] if a['artifact_id'] == 'cd002_graph')
    require(graph['sha256'] == FIXTURE_SHA256 and graph['rights_status'] == 'declared_license' and
            graph['license_identifier'] == 'CC-BY-4.0' and graph['rights_scope'] == 'generated_dependency_data_only',
            'deps.dev generated-data rights must remain scoped')
    require(catalog['corrections'] and all(x['id'] and x['claim'] and x['qualification'] for x in catalog['corrections']),
            'Concentration review corrections missing')
    actions = catalog['next_actions']; ids = {a['action_id'] for a in actions}
    require(actions and len(ids) == len(actions), 'Duplicate concentration next action')
    for a in actions:
        require(a['candidate_ids'] and set(a['candidate_ids']) <= IDS and a['action'] and a['completion_evidence'] and
                a['status'] in {'completed', 'open', 'pending_rights_review', 'blocked_access', 'pending_contract_review'},
                'Concentration action needs status and completion evidence')
    prompts = catalog['focused_follow_up_prompts']
    require(len({p['action_id'] for p in prompts}) == len(prompts) and
            {p['action_id'] for p in prompts} == {a['action_id'] for a in actions if a['status'] != 'completed'},
            'Each open concentration action needs one focused prompt')
    require(all(p['why_needed'] and p['prompt'] for p in prompts), 'Empty concentration follow-up prompt')
    headings = re.findall(r'^## (CD[0-9]{3}) (.+)$', markdown, re.MULTILINE)
    require(len(headings) == 5 and dict(headings) == {k: v['name'] for k, v in by_id.items()},
            'Concentration guide IDs/titles mismatch')
    return {'concentration_collections': 5, 'concentration_artifact_references': len(artifact_ids),
            'concentration_findings': len(finding_ids), 'unadmitted_concentration_collections': 5,
            'concentration_research_fixtures': 1}
