"""Offline catalog consistency only; no source fetch, scientific or rights approval."""
import re
from urllib.parse import parse_qsl, urlsplit


CATALOG_VERSION = 'adoption-productivity-research/1.0.0'
EXPECTED_IDS = {f'AP{i:03}' for i in range(1, 6)}
SIGNED_QUERY_KEYS = {'signature', 'key-pair-id', 'expires', 'token', 'access_token',
                     'x-amz-signature', 'x-amz-credential', 'sig'}
ACCESS_STATES = {'primary_opened', 'bounded_sample_opened', 'metadata_only',
                 'endpoint_only', 'index_only', 'access_blocked'}
MEASUREMENT_TYPES = {'self_reported_adoption', 'administrative_productivity',
                     'recorded_task_duration', 'administrative_work_output'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_url(value):
    require(isinstance(value, str), 'Adoption artifact URL must be text')
    parsed = urlsplit(value)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password and not any(c.isspace() for c in value),
            'Invalid adoption artifact URL')
    keys = {key.lower() for key, _ in parse_qsl(parsed.query)}
    require(not keys & SIGNED_QUERY_KEYS, 'Signed or credential-bearing artifact URL')


def check_catalog(catalog, inventory_hash, markdown):
    require(catalog['catalog_version'] == CATALOG_VERSION, 'Unknown adoption catalog version')
    require(catalog['catalog_state'] == 'research_only_not_admitted' and
            catalog['operational_admission'] == 'not_admitted' and
            catalog['collector_enabled'] is False and catalog['scoring_enabled'] is False,
            'Adoption catalog cannot enable admission, collection or scoring')
    require(not {'records', 'observations', 'participant_rows', 'raw_source_content'} & catalog.keys(),
            'Adoption catalog cannot embed observation or participant records')
    baseline = catalog['baseline_inventory']
    require(baseline['repo_path'] == 'data/evidence-program/source_inventory.json' and
            baseline['record_count'] == 64 and baseline['version'] == '1.1' and
            baseline['audit_commit'] == 'f5274396885dbb654fc2861a78fa5be8f42fad38' and
            baseline['sha256'] == inventory_hash, 'Adoption frozen inventory mismatch')
    families = catalog['collections']
    by_id = {family['candidate_id']: family for family in families}
    require(len(families) == len(by_id) == 5 and by_id.keys() == EXPECTED_IDS,
            'Adoption candidate IDs/count mismatch')
    require([row['candidate_id'] for row in catalog['priority_ranking']] == ['AP001', 'AP002', 'AP003']
            and all(row['reason'] for row in catalog['priority_ranking']), 'Adoption ranking mismatch')
    all_artifacts = set()
    all_units = set()
    for family in families:
        require(family['collection_status'] == 'candidate_not_collected' and
                family['operational_admission'] == 'not_admitted' and family['collector_enabled'] is False,
                'Adoption family cannot enable collection or admission')
        require(family['classification'] in {'new_relative_to_frozen_inventory', 'existing_family_enrichment'},
                'Unknown adoption inventory classification')
        for field in ['name', 'summary', 'historical_coverage', 'update_frequency', 'access_method',
                      'rights_summary', 'duplicate_evidence_policy']:
            require(isinstance(family.get(field), str) and family[field].strip(), f'Missing adoption {field}')
        artifacts = {artifact['artifact_id']: artifact for artifact in family['artifacts']}
        require(artifacts and len(artifacts) == len(family['artifacts']) and not all_artifacts & artifacts.keys(),
                'Missing or duplicate adoption artifact')
        for artifact in artifacts.values():
            safe_url(artifact['url'])
            require(artifact['access_status'] in ACCESS_STATES and artifact['inspection_note'] and
                    artifact['provenance_locator'] and artifact['reviewed_on'] == catalog['reviewed_on'],
                    'Adoption artifact lacks scoped dated verification')
            require(artifact['raw_content_in_catalog'] is False, 'Adoption catalog cannot embed raw artifacts')
            require(artifact['rights_status'] in {'declared_license', 'restricted_use', 'unknown'} and
                    artifact['rights_scope'] and artifact['rights_note'], 'Adoption artifact lacks scoped rights')
            refs = artifact['rights_evidence_artifact_ids']
            require(set(refs) <= artifacts.keys(), 'Unknown adoption rights evidence')
            if artifact['rights_status'] != 'unknown':
                require(artifact['license_identifier'] and refs, 'Adoption rights declaration lacks provenance')
            for field, length in [('git_commit', 40), ('git_blob_sha', 40), ('sha256', 64)]:
                if field in artifact:
                    require(isinstance(artifact[field], str) and re.fullmatch('[0-9a-f]{' + str(length) + '}', artifact[field]) is not None,
                            'Invalid adoption artifact pin')
            if 'git_commit' in artifact:
                require('/blob/' + artifact['git_commit'] + '/' in artifact['url'], 'Adoption URL/pin mismatch')
        for relation in family['inventory_relationships']:
            require(relation['source_id'] in {'GL004', 'GL023'} and relation['evidence_artifact_id'] in artifacts,
                    'Unknown adoption inventory/evidence relationship')
        units = family['evidence_units']
        unit_ids = {unit['unit_id'] for unit in units}
        require(units and len(unit_ids) == len(units) and not all_units & unit_ids, 'Duplicate adoption evidence unit')
        for unit in units:
            require(unit['measurement_type'] in MEASUREMENT_TYPES and unit['causal_status'] and
                    unit['deployment_maturity'] and unit['population_or_sample'] and
                    unit['publication_or_wave_identity'] and unit['comparability_limitations'] and
                    unit['artifact_ids'] and set(unit['artifact_ids']) <= artifacts.keys(),
                    'Adoption evidence unit lacks interpretation or provenance')
        require(family['findings'], 'Missing adoption findings')
        for finding in family['findings']:
            require(finding['text'] and finding['evidence_artifact_ids'] and
                    set(finding['evidence_artifact_ids']) <= artifacts.keys() and
                    finding['verification_level'] in {'primary_source_reported', 'index_only_inconclusive',
                                                       'metadata_verified_content_uninspected'},
                    'Adoption finding lacks verification/provenance')
        require(family['sample_fields'] and family['limitations'], 'Missing adoption fields/limitations')
        all_artifacts.update(artifacts)
        all_units.update(unit_ids)
    require(all(by_id[key]['classification'] == 'new_relative_to_frozen_inventory'
                for key in ['AP001', 'AP002', 'AP003', 'AP004']) and
            by_id['AP005']['classification'] == 'existing_family_enrichment', 'Adoption classification boundary changed')
    require(any(r['source_id'] == 'GL023' and r['relationship'] == 'same_family_enrichment'
                for r in by_id['AP005']['inventory_relationships']), 'Census must remain GL023 enrichment')
    require(any(r['source_id'] == 'GL004' and r['relationship'] == 'same_publisher_distinct_evidence_family'
                for r in by_id['AP002']['inventory_relationships']), 'METR productivity must stay distinct from GL004 horizons')
    units = {u['unit_id']: u for f in families for u in f['evidence_units']}
    required_boundaries = {
        'statcan_csbc_ai_use': ('self_reported_adoption', 'descriptive', 'unspecified'),
        'statcan_sdtiu_linked_productivity': ('administrative_productivity', 'observational_association', 'not_established'),
        'metr_early_2025': ('recorded_task_duration', 'randomized_access_effect', 'experimental_access_real_tasks'),
        'metr_late_2025': ('recorded_task_duration', 'selection_limited_randomized_access', 'experimental_access_real_tasks'),
        'generative_ai_at_work_rollout': ('administrative_productivity', 'nonrandom_staggered_rollout', 'routine_customer_support'),
        'cui_three_site_experiments': ('administrative_work_output', 'randomized_access_with_distinct_iv_and_itt', 'experimental_access_workplace'),
        'census_btos_core': ('self_reported_adoption', 'descriptive', 'unspecified'),
        'census_btos_ai_supplement': ('self_reported_adoption', 'descriptive', 'unspecified'),
    }
    for key, expected in required_boundaries.items():
        require(key in units and tuple(units[key][field] for field in
                ['measurement_type', 'causal_status', 'deployment_maturity']) == expected,
                'Adoption measurement/causal/deployment boundary changed')
    artifact_lookup = {a['artifact_id']: a for f in families for a in f['artifacts']}
    for key in ['metr_early_csv', 'metr_early_code', 'metr_late_csv', 'metr_late_code',
                'qje_replication', 'cui_manuscript', 'cui_supplement', 'btos_national']:
        require(artifact_lookup[key]['rights_status'] == 'unknown', 'Unresolved artifact rights cannot inherit a paper license')
    require(artifact_lookup['btos_national']['access_status'] == 'access_blocked' and
            artifact_lookup['btos_catalogue']['access_status'] == 'index_only' and
            artifact_lookup['qje_replication']['access_status'] == 'access_blocked',
            'Uninspected/index-only artifacts cannot become verified content')
    semantics = catalog['interpretation_guards']
    require(semantics['metr_treatment_coding'] == {'1': 'AI allowed', '0': 'AI disallowed'} and
            semantics['metr_positive_time_ratio_minus_one_means'] == 'longer_time' and
            semantics['cui_iv_and_itt_may_be_collapsed'] is False and
            semantics['csbc_and_sdtiu_may_be_joined_as_one_study'] is False and
            semantics['census_wording_regimes_may_be_pooled_without_break'] is False and
            semantics['labor_market_outcomes_in_scope'] is False,
            'Adoption interpretation guard changed')
    require(semantics['census_revised_wording_first_collection_window'] == ['2025-11-17', '2025-11-30'] and
            semantics['census_revised_wording_first_reference_window'] == ['2025-11-03', '2025-11-16'] and
            semantics['census_revised_wording_first_release'] == '2025-12-04', 'Census collection/reference/release dates conflated')
    spec = catalog['proposed_adapter']
    require(spec['status'] == 'proposed_not_implemented' and spec['candidate_id'] == 'AP001' and
            spec['canonical_contract_mapping'] == 'pending_separate_review', 'Adoption adapter must remain a proposal')
    require(spec['maximum_output_points'] == 3 and spec['product_ids'] == ['33100825', '33101004', '33101167']
            and spec['coordinate'] == '1.25.1.0.0.0.0.0.0.0' and spec['allow_bulk_download'] is False,
            'Adoption adapter bounded scope changed')
    require(spec['numeric_representation'] == 'exact_decimal_strings' and
            spec['measurement_type'] == 'reported_adoption' and spec['causal_status'] == 'descriptive' and
            spec['deployment_maturity'] == 'unspecified' and spec['unknown_standard_error'] is None,
            'Adoption adapter must preserve interpretation and unknown uncertainty')
    require(spec['fixture_status'] == 'not_packaged_or_executed' and
            spec['sample_verification_status'] == 'independently_rechecked_primary_values',
            'Source verification is not executable fixture validation')
    require(spec['reviewed_private_values'] == [
        {'product_id': '33100825', 'decimal_value': '6.2', 'unit': 'percent'},
        {'product_id': '33101004', 'decimal_value': '12.4', 'unit': 'percent'},
        {'product_id': '33101167', 'decimal_value': '19.0', 'unit': 'percent'}],
        'Reviewed StatCan private-sector values/decimal representation changed')
    require(len(spec['acceptance_tests']) >= 10 and all(spec['acceptance_tests']), 'Missing adoption adapter acceptance tests')
    actions = catalog['next_actions']
    action_ids = {action['action_id'] for action in actions}
    require(actions and len(action_ids) == len(actions), 'Missing or duplicate adoption next action')
    for action in actions:
        require(action['candidate_ids'] and set(action['candidate_ids']) <= EXPECTED_IDS and
                action['status'] in {'open', 'blocked_access', 'pending_rights_review', 'pending_contract_review', 'completed'} and
                action['action'] and action['completion_evidence'], 'Adoption next action lacks scope or completion evidence')
    for prompt in catalog['focused_follow_up_prompts']:
        require(prompt['action_id'] in action_ids and prompt['prompt'] and prompt['why_needed'],
                'Adoption follow-up prompt lacks open-action rationale')
    headings = re.findall(r'^## (AP[0-9]{3}) (.+)$', markdown, re.MULTILINE)
    require(len(headings) == 5 and dict(headings) == {k: v['name'] for k, v in by_id.items()},
            'Adoption documentation IDs/titles mismatch')
    return {'adoption_productivity_collections': 5, 'adoption_productivity_artifact_references': len(all_artifacts),
            'adoption_productivity_evidence_units': len(all_units), 'unadmitted_adoption_productivity_collections': 5}
