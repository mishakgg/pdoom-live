"""Offline organizational-research consistency; not a collector or safety assessor."""
import re
from urllib.parse import parse_qsl, urlsplit

EXPECTED_IDS = {f'OS{i:03}' for i in range(1, 6)}
ACCESS_STATES = {'primary_opened', 'bounded_sample_opened', 'metadata_only',
                 'endpoint_only', 'index_only', 'access_blocked'}
STATEMENT_KINDS = {'declared_authority', 'formal_commitment', 'reported_completed_action',
                   'reported_current_practice', 'reported_release_decision',
                   'promotional_assertion', 'external_assessment', 'document_metadata'}
SUPPORT_KINDS = {'organization_reported', 'external_assessor_reported', 'official_document_metadata'}
SIGNED_QUERY_KEYS = {'signature', 'key-pair-id', 'expires', 'token', 'access_token',
                     'x-amz-signature', 'x-amz-credential', 'sig'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_url(value):
    require(isinstance(value, str), 'Organizational artifact URL must be text')
    parsed = urlsplit(value)
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password and not any(c.isspace() for c in value),
            'Invalid organizational artifact URL')
    require(not {key.lower() for key, _ in parse_qsl(parsed.query)} & SIGNED_QUERY_KEYS,
            'Signed or credential-bearing organizational URL')


def check_catalog(catalog, inventory_hash, markdown):
    require(catalog['catalog_version'] == 'organizational-safety-research/1.0.0',
            'Unknown organizational catalog version')
    require(catalog['catalog_state'] == 'research_only_not_admitted' and
            catalog['operational_admission'] == 'not_admitted' and
            catalog['collector_enabled'] is False and catalog['scoring_enabled'] is False,
            'Organizational catalog cannot enable admission, collection or scoring')
    require(not {'records', 'observations', 'raw_source_content', 'personal_profiles',
                 'company_safety_rankings'} & catalog.keys(),
            'Organizational catalog cannot embed operational, raw or profiling records')
    baseline = catalog['baseline_inventory']
    require(baseline['repo_path'] == 'data/evidence-program/source_inventory.json' and
            baseline['record_count'] == 64 and baseline['version'] == '1.1' and
            baseline['audit_commit'] == 'f5274396885dbb654fc2861a78fa5be8f42fad38' and
            baseline['sha256'] == inventory_hash, 'Organizational frozen inventory mismatch')
    require(re.fullmatch('[0-9a-f]{40}', catalog['repository_review_commit']),
            'Missing organizational repository review commit')
    families = catalog['collections']
    by_id = {family['candidate_id']: family for family in families}
    require(len(families) == len(by_id) == 5 and by_id.keys() == EXPECTED_IDS,
            'Organizational candidate IDs/count mismatch')
    require(catalog['ranking_basis'] == 'source_utility_not_organizational_safety' and
            [row['candidate_id'] for row in catalog['priority_ranking']] == ['OS001', 'OS002', 'OS003'] and
            all(row['reason'] for row in catalog['priority_ranking']),
            'Organizational source ranking must not become a safety ranking')
    all_artifacts, all_findings = set(), set()
    expected_relationships = {'OS002': 'GL015', 'OS004': 'GL014', 'OS005': 'GL016'}
    for key, family in by_id.items():
        require(family['collection_status'] == 'candidate_not_collected' and
                family['operational_admission'] == 'not_admitted' and family['collector_enabled'] is False,
                'Organizational family cannot enable collection or admission')
        expected = 'existing_family_enrichment' if key in expected_relationships else 'new_relative_to_frozen_inventory'
        require(family['classification'] == expected, 'Organizational inventory classification changed')
        for field in ['name', 'summary', 'historical_coverage', 'update_frequency', 'access_method',
                      'rights_summary', 'duplicate_evidence_policy']:
            require(isinstance(family.get(field), str) and family[field].strip(), f'Missing organizational {field}')
        artifacts = {a['artifact_id']: a for a in family['artifacts']}
        require(artifacts and len(artifacts) == len(family['artifacts']) and not all_artifacts & artifacts.keys(),
                'Missing or duplicate organizational artifact')
        for artifact in artifacts.values():
            safe_url(artifact['url'])
            require(artifact['access_status'] in ACCESS_STATES and artifact['inspection_note'] and
                    artifact['provenance_locator'] and artifact['reviewed_on'] == catalog['reviewed_on'],
                    'Organizational artifact lacks scoped dated verification')
            require(artifact['raw_content_in_catalog'] is False, 'Organizational raw artifacts must not be embedded')
            require(artifact['rights_status'] in {'declared_license', 'restricted_use', 'unknown'} and
                    artifact['rights_scope'] and artifact['rights_note'], 'Organizational artifact lacks scoped rights')
            require(set(artifact['rights_evidence_artifact_ids']) <= artifacts.keys(), 'Unknown organizational rights evidence')
            if artifact['rights_status'] != 'unknown':
                require(artifact['license_identifier'] and artifact['rights_evidence_artifact_ids'],
                        'Organizational rights declaration lacks provenance')
            if artifact.get('sha256') is not None:
                require(re.fullmatch('[0-9a-f]{64}', artifact['sha256']), 'Invalid organizational artifact hash')
        for relation in family['inventory_relationships']:
            require(relation['source_id'] in {'GL004', 'GL014', 'GL015', 'GL016', 'GL017', 'GL019', 'GL021', 'GL032'}
                    and relation['evidence_artifact_id'] in artifacts,
                    'Unknown organizational inventory/evidence relationship')
        if key in expected_relationships:
            require(any(r['source_id'] == expected_relationships[key] and r['relationship'] == 'same_family_enrichment'
                        for r in family['inventory_relationships']), 'Missing organizational family enrichment relationship')
        require(family['sample_fields'] and family['limitations'] and family['findings'],
                'Missing organizational sample fields, limitations or findings')
        ids = {f['finding_id'] for f in family['findings']}
        require(len(ids) == len(family['findings']) and not ids & all_findings, 'Duplicate organizational finding')
        for finding in family['findings']:
            require(finding['text'] and finding['evidence_artifact_ids'] and
                    set(finding['evidence_artifact_ids']) <= artifacts.keys(), 'Organizational finding lacks provenance')
            require(finding['statement_kind'] in STATEMENT_KINDS and finding['support_kind'] in SUPPORT_KINDS,
                    'Organizational statement and support classes must stay separate')
            if finding['statement_kind'] == 'external_assessment':
                require(finding['support_kind'] == 'external_assessor_reported', 'External assessment cannot become organizational proof')
            require(finding['verification_level'] in {'primary_source_reported', 'index_only_inconclusive',
                                                       'metadata_verified_content_uninspected'},
                    'Organizational finding lacks verification level')
        all_artifacts.update(artifacts)
        all_findings.update(ids)
    guards = catalog['interpretation_guards']
    for field in ['policy_implies_exercised_authority', 'reported_action_implies_effectiveness',
                  'external_review_implies_audit_pass', 'missing_disclosure_implies_absence',
                  'staff_counts_imply_safety', 'publication_date_implies_decision_date',
                  'changed_public_role_wording_implies_authority_transfer', 'proxy_to_pdoom_allowed']:
        require(guards[field] is False, 'Organizational interpretation guard changed')
    require(guards['evidence_classes_are_orthogonal'] is True and
            guards['metr_pilot_publication_veto_must_be_disclosed'] is True,
            'Organizational external-review qualification changed')
    require(guards['metr_two_textual_changes_currently_verified'] is True and
            guards['metr_text_changes_imply_effectiveness'] is False and
            guards['aisi_card_and_later_paper_relation'] == 'evolving_assessment_protocol' and
            guards['aisi_paper_license_clears_openai_cards'] is False,
            'Organizational completed follow-up boundary changed')
    artifact_lookup = {a['artifact_id']: a for f in families for a in f['artifacts']}
    require(artifact_lookup['aisi_astra_pdf']['rights_status'] == 'declared_license' and
            artifact_lookup['aisi_astra_pdf']['license_identifier'] == 'CC-BY-4.0' and
            artifact_lookup['openai_astra']['rights_status'] == 'unknown',
            'AISI paper license cannot clear OpenAI card rights')
    require(artifact_lookup['microsoft_2025_pdf']['general_terms_restrictions_observed'] is True and
            artifact_lookup['haip_36_pdf']['access_status'] == 'primary_opened',
            'Organizational updated access or rights qualification changed')
    spec = catalog['proposed_adapter']
    require(spec['status'] == 'proposed_not_implemented' and spec['candidate_id'] == 'OS001' and
            spec['canonical_contract_mapping'] == 'pending_separate_review' and
            spec['fixture_status'] == 'not_packaged_or_executed', 'Organizational adapter must remain a proposal')
    require(spec['report_ids'] == ['36', '204'] and spec['maximum_document_metadata_rows'] == 2 and
            spec['maximum_clause_records'] == 6 and spec['allow_bulk_download'] is False and
            spec['question_allowlist'] == {'36': ['4(a)', '4(d)'], '204': ['Q21', 'Q23', 'Q8.A']},
            'Organizational adapter bounded scope changed')
    require(spec['unknown_event_date'] is None and spec['unknown_effective_date'] is None and
            spec['unknown_framework_version'] is None and spec['authority_transfer_inference_allowed'] is False,
            'Organizational adapter cannot invent dates, instrument version or authority transfer')
    require(len(spec['acceptance_tests']) >= 10 and all(spec['acceptance_tests']),
            'Missing organizational adapter acceptance tests')
    actions = catalog['next_actions']
    action_ids = {a['action_id'] for a in actions}
    require(actions and len(action_ids) == len(actions), 'Missing or duplicate organizational next action')
    for action in actions:
        require(action['candidate_ids'] and set(action['candidate_ids']) <= EXPECTED_IDS and
                action['status'] in {'open', 'blocked_access', 'pending_rights_review', 'pending_contract_review', 'completed'} and
                action['action'] and action['completion_evidence'], 'Organizational next action lacks completion evidence')
    for prompt in catalog['focused_follow_up_prompts']:
        require(prompt['action_id'] in action_ids and prompt['prompt'] and prompt['why_needed'],
                'Organizational follow-up prompt lacks rationale')
        require(next(a for a in actions if a['action_id'] == prompt['action_id'])['status'] != 'completed',
                'Organizational follow-up must address an open gap')
    headings = re.findall(r'^## (OS[0-9]{3}) (.+)$', markdown, re.MULTILINE)
    require(len(headings) == 5 and dict(headings) == {k: v['name'] for k, v in by_id.items()},
            'Organizational documentation IDs/titles mismatch')
    return {'organizational_safety_collections': 5,
            'organizational_safety_artifact_references': len(all_artifacts),
            'organizational_safety_findings': len(all_findings),
            'unadmitted_organizational_safety_collections': 5}

# Backward-compatible import for the existing focused organizational test suite.
# Queue state is maintained independently of this source-specific catalog.
from check_research_queue import check_queue
