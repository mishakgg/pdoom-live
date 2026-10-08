"""Negative regression checks for the repository-native integration gates."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import check
from validate_dataset import SCHEMA, Draft202012Validator, FORMAT_CHECKER


class IntegrationTests(unittest.TestCase):
    def sources(self):
        return (check.read_json(check.DATA / 'source_inventory.json'),
                check.read_json(check.DATA / 'global_sources.json'),
                check.read_json(check.DATA / 'chinese_sources.json'))

    def chinese(self):
        return [check.read_json(check.DATA / 'chinese' / name)
                for name in ['aliases.json', 'query_lexicon.json', 'test_cases.json']]

    def check_chinese(self, inputs):
        return check.check_chinese(*inputs, SCHEMA, Draft202012Validator, FORMAT_CHECKER)

    def test_duplicate_source_ids_rejected(self):
        inv, global_rows, chinese = self.sources()
        global_rows[1]['source_id'] = global_rows[0]['source_id']
        inv['records'] = global_rows + chinese
        with self.assertRaisesRegex(ValueError, 'unique'):
            check.check_sources(inv, global_rows, chinese)

    def test_uncollected_status_cannot_be_promoted(self):
        inv, global_rows, chinese = self.sources()
        global_rows[0]['collection_status'] = 'collected'
        inv['records'] = global_rows + chinese
        with self.assertRaisesRegex(ValueError, 'claim collection'):
            check.check_sources(inv, global_rows, chinese)

    def test_credential_url_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid URL'):
            check.check_url('https://user:secret@example.com/path')

    def test_nonweb_url_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid URL'):
            check.check_url('file:///etc/passwd')

    def test_coverage_unknown_link_rejected(self):
        inventory, _, _ = self.sources()
        mapping = check.read_json(check.DATA / 'coverage_mapping.json')
        mapping[0]['artifact_links'][0] = 'https://example.com/unverified'
        inventory['repository_coverage'] = mapping
        with self.assertRaisesRegex(ValueError, 'Unrecognized pinned'):
            check.check_coverage(inventory, mapping,
                                 check.read_json(check.DATA / 'baseline_metrics.json'),
                                 check.read_json(check.DATA / 'coverage_references.json'))

    def test_misaligned_unicode_span_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['input']['quote_span']['start'] += 1
        with self.assertRaisesRegex(ValueError, 'span does not match'):
            self.check_chinese(inputs)

    def test_invalid_actual_fragment_field_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['expected']['contract_fragments'][0]['path'] = 'forecast.data.not_a_field'
        with self.assertRaisesRegex(ValueError, 'Unknown schema field'):
            self.check_chinese(inputs)

    def test_invalid_fragment_value_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['expected']['contract_fragments'][0]['value']['value'] = 0.155
        with self.assertRaisesRegex(ValueError, 'Invalid fragment'):
            self.check_chinese(inputs)

    def test_wrong_schema_shortcut_rejected(self):
        inputs = self.chinese()
        inputs[2]['cases'][0]['expected']['contract_fragments'][0]['schema_definition'] = 'temporal'
        with self.assertRaisesRegex(ValueError, 'shortcut'):
            self.check_chinese(inputs)

    def test_automatic_alias_merge_rejected(self):
        inputs = self.chinese()
        inputs[0]['entries'][0]['automatic_merge_allowed'] = True
        with self.assertRaisesRegex(ValueError, 'merge guard'):
            self.check_chinese(inputs)

    def test_unknown_query_source_rejected(self):
        inputs = self.chinese()
        inputs[1]['query_templates'][0]['source_ids'] = ['CN999']
        with self.assertRaisesRegex(ValueError, 'unknown source'):
            self.check_chinese(inputs)

    def test_fixture_local_old_new_benchmark_paths_resolve(self):
        field = check.schema_for_fragment(SCHEMA, 'old_benchmark_run.data.measurement.result')
        self.assertEqual(field['$ref'], '#/$defs/value')
        self.assertEqual(field, check.schema_for_fragment(SCHEMA, 'new_benchmark_run.data.measurement.result'))

    def test_csv_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rows.csv'
            path.write_text('source_id,name\nGL001,changed\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'CSV diverges'):
                check.check_csv(path, [{'source_id': 'GL001', 'name': 'original'}])


class TaskPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = check.read_json(check.DATA / 'implementation_tasks.json')
        self.recipes = check.read_json(check.DATA / 'analysis_recipes.json')
        self.markdown = (check.DOCS / 'implementation_tasks.md').read_text(encoding='utf-8')
        self.paths = {path for task in self.plan['tasks'] for path in task['existing_paths']}

    def validate(self):
        return check.check_task_plan(self.plan, self.recipes, self.markdown, self.paths)

    def test_task_pack_positive(self):
        result = self.validate()
        self.assertEqual(result['implementation_tasks'], len(self.plan['tasks']))

    def test_duplicate_task_id_rejected(self):
        self.plan['tasks'].append(dict(self.plan['tasks'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate implementation task ID'):
            self.validate()

    def test_unknown_dependency_rejected(self):
        self.plan['tasks'][0]['depends_on'] = ['EP99999']
        with self.assertRaisesRegex(ValueError, 'unknown task'):
            self.validate()

    def test_self_dependency_rejected(self):
        task = self.plan['tasks'][0]
        task['depends_on'] = [task['id']]
        with self.assertRaisesRegex(ValueError, 'itself'):
            self.validate()

    def test_dependency_cycle_rejected(self):
        first, second = self.plan['tasks'][:2]
        first['depends_on'] = [second['id']]
        second['depends_on'] = [first['id']]
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            self.validate()

    def test_unknown_task_source_rejected(self):
        self.plan['tasks'][0]['source_ids'] = ['GL999']
        with self.assertRaisesRegex(ValueError, 'unknown source ID'):
            self.validate()

    def test_unknown_task_recipe_rejected(self):
        self.plan['tasks'][0]['recipe_ids'] = ['R999']
        with self.assertRaisesRegex(ValueError, 'unknown recipe ID'):
            self.validate()

    def test_task_path_traversal_rejected(self):
        for path in ['../outside.py', '/tmp/outside.py', 'C:\\outside.py', '.']:
            with self.subTest(path=path):
                self.plan['tasks'][0]['proposed_paths'] = [path]
                with self.assertRaisesRegex(ValueError, 'Unsafe task path'):
                    self.validate()

    def test_task_missing_existing_path_rejected(self):
        self.plan['tasks'][0]['existing_paths'].append('missing-task-baseline-file.py')
        with self.assertRaisesRegex(ValueError, 'existing path not found'):
            self.validate()

    def test_conflicting_task_path_roles_rejected(self):
        self.plan['tasks'][0]['proposed_paths'].append(self.plan['tasks'][0]['existing_paths'][0])
        with self.assertRaisesRegex(ValueError, 'both existing and proposed'):
            self.validate()

    def test_later_creation_of_proposed_path_is_allowed(self):
        # Existence today does not change the proposed-at-baseline designation.
        self.paths.update(self.plan['tasks'][0]['proposed_paths'])
        self.validate()

    def test_task_doc_title_drift_rejected(self):
        task = self.plan['tasks'][0]
        self.markdown = self.markdown.replace('## ' + task['id'] + ' ' + task['title'],
                                               '## ' + task['id'] + ' Changed title', 1)
        with self.assertRaisesRegex(ValueError, 'IDs/titles'):
            self.validate()

    def test_task_doc_missing_heading_rejected(self):
        self.markdown = self.markdown.replace('## ' + self.plan['tasks'][0]['id'] + ' ', '## Removed ', 1)
        with self.assertRaisesRegex(ValueError, 'heading count'):
            self.validate()

    def test_plan_cannot_claim_execution(self):
        self.plan['tasks'][0]['status'] = 'completed'
        with self.assertRaisesRegex(ValueError, 'claims execution'):
            self.validate()

    def test_task_acceptance_evidence_required(self):
        self.plan['tasks'][0]['completion_evidence'] = []
        with self.assertRaisesRegex(ValueError, 'missing completion_evidence'):
            self.validate()


class ResearchCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = check.read_json(check.DATA / 'research/chinese-safety-evaluations.json')
        self.inventory_hash = check.hashlib.sha256((check.DATA / 'source_inventory.json').read_bytes()).hexdigest()
        self.markdown = (check.DOCS / 'research/chinese-safety-evaluations.md').read_text(encoding='utf-8')

    def validate(self):
        return check.check_research_catalog(self.catalog, self.inventory_hash, self.markdown)

    def test_research_catalog_positive(self):
        self.assertEqual(self.validate()['research_candidates'], 8)

    def test_research_duplicate_candidate_rejected(self):
        self.catalog['families'][1]['candidate_id'] = 'ZHS001'
        with self.assertRaisesRegex(ValueError, 'candidate IDs'):
            self.validate()

    def test_research_active_admission_rejected(self):
        self.catalog['collector_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'cannot enable admission'):
            self.validate()

    def test_research_family_collection_rejected(self):
        self.catalog['families'][0]['collection_status'] = 'collected'
        with self.assertRaisesRegex(ValueError, 'cannot enable collection'):
            self.validate()

    def test_research_frozen_inventory_drift_rejected(self):
        self.catalog['baseline_inventory']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'frozen inventory mismatch'):
            self.validate()

    def test_research_unknown_inventory_reference_rejected(self):
        self.catalog['families'][0]['inventory_relationships'][0]['source_id'] = 'CN999'
        with self.assertRaisesRegex(ValueError, 'Unknown research inventory'):
            self.validate()

    def test_research_missing_rights_provenance_rejected(self):
        self.catalog['families'][0]['artifacts'][0]['rights_evidence_artifact_ids'] = []
        with self.assertRaisesRegex(ValueError, 'Declared rights lack evidence'):
            self.validate()

    def test_research_index_only_cannot_be_upgraded(self):
        self.catalog['families'][6]['artifacts'][0]['access_status'] = 'primary_opened'
        with self.assertRaisesRegex(ValueError, 'Index-only evidence'):
            self.validate()

    def test_research_adapter_cannot_be_activated(self):
        self.catalog['proposed_adapter']['status'] = 'implemented'
        with self.assertRaisesRegex(ValueError, 'remain a specification'):
            self.validate()

    def test_research_adapter_fetch_expansion_rejected(self):
        self.catalog['proposed_adapter']['content_fetches_max'] = 3
        with self.assertRaisesRegex(ValueError, 'adapter bounds'):
            self.validate()

    def test_research_guessed_denominator_rejected(self):
        self.catalog['proposed_adapter']['unknown_fields']['denominator'] = 1000
        with self.assertRaisesRegex(ValueError, 'preserve unknowns'):
            self.validate()

    def test_research_float_spot_check_rejected(self):
        self.catalog['proposed_adapter']['spot_checks'][0]['decimal_value'] = 40.01
        with self.assertRaisesRegex(ValueError, 'decimal strings'):
            self.validate()

    def test_research_bad_pin_rejected(self):
        self.catalog['families'][0]['artifacts'][0]['git_blob_sha'] = 'main'
        with self.assertRaisesRegex(ValueError, 'Invalid research artifact git_blob_sha'):
            self.validate()

    def test_research_doc_title_drift_rejected(self):
        self.markdown = self.markdown.replace('## ZHS001 FLAMES', '## ZHS001 Wrong title')
        with self.assertRaisesRegex(ValueError, 'documentation IDs/titles'):
            self.validate()


class AdoptionProductivityCatalogTests(unittest.TestCase):
    def setUp(self):
        from check_adoption_productivity import check_catalog
        self.check_catalog = check_catalog
        self.catalog = check.read_json(check.DATA / 'research/adoption-productivity.json')
        self.inventory_hash = check.hashlib.sha256((check.DATA / 'source_inventory.json').read_bytes()).hexdigest()
        self.markdown = (check.DOCS / 'research/adoption-productivity.md').read_text(encoding='utf-8')

    def validate(self):
        return self.check_catalog(self.catalog, self.inventory_hash, self.markdown)

    def test_adoption_catalog_positive(self):
        result = self.validate()
        self.assertEqual(result['adoption_productivity_collections'], 5)
        self.assertEqual(result['adoption_productivity_evidence_units'], 8)

    def test_adoption_duplicate_candidate_rejected(self):
        self.catalog['collections'][1]['candidate_id'] = 'AP001'
        with self.assertRaisesRegex(ValueError, 'candidate IDs'):
            self.validate()

    def test_adoption_admission_rejected(self):
        self.catalog['collector_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'cannot enable admission'):
            self.validate()

    def test_adoption_family_promotion_rejected(self):
        self.catalog['collections'][0]['collection_status'] = 'collected'
        with self.assertRaisesRegex(ValueError, 'family cannot enable'):
            self.validate()

    def test_adoption_inventory_drift_rejected(self):
        self.catalog['baseline_inventory']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'frozen inventory'):
            self.validate()

    def test_adoption_participant_rows_rejected(self):
        self.catalog['participant_rows'] = []
        with self.assertRaisesRegex(ValueError, 'participant records'):
            self.validate()

    def test_adoption_signed_artifact_url_rejected(self):
        self.catalog['collections'][0]['artifacts'][0]['url'] += '?Signature=do-not-retain'
        with self.assertRaisesRegex(ValueError, 'Signed or credential'):
            self.validate()

    def test_adoption_rights_provenance_required(self):
        self.catalog['collections'][0]['artifacts'][0]['rights_evidence_artifact_ids'] = []
        with self.assertRaisesRegex(ValueError, 'rights declaration lacks'):
            self.validate()

    def test_adoption_missing_findings_provenance_rejected(self):
        self.catalog['collections'][0]['findings'][0]['evidence_artifact_ids'] = ['unknown']
        with self.assertRaisesRegex(ValueError, 'finding lacks'):
            self.validate()

    def test_adoption_metrology_class_conflation_rejected(self):
        self.catalog['collections'][0]['evidence_units'][0]['measurement_type'] = 'administrative_productivity'
        with self.assertRaisesRegex(ValueError, 'measurement/causal/deployment'):
            self.validate()

    def test_adoption_routine_use_inference_rejected(self):
        self.catalog['collections'][4]['evidence_units'][0]['deployment_maturity'] = 'routine'
        with self.assertRaisesRegex(ValueError, 'measurement/causal/deployment'):
            self.validate()

    def test_adoption_metr_reverse_coding_rejected(self):
        self.catalog['interpretation_guards']['metr_treatment_coding']['1'] = 'AI disallowed'
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_adoption_metr_speedup_sign_rejected(self):
        self.catalog['interpretation_guards']['metr_positive_time_ratio_minus_one_means'] = 'faster'
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_adoption_cui_estimand_collapse_rejected(self):
        self.catalog['interpretation_guards']['cui_iv_and_itt_may_be_collapsed'] = True
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_adoption_census_date_conflation_rejected(self):
        self.catalog['interpretation_guards']['census_revised_wording_first_reference_window'] = ['2025-11-17', '2025-11-30']
        with self.assertRaisesRegex(ValueError, 'dates conflated'):
            self.validate()

    def test_adoption_census_must_remain_enrichment(self):
        self.catalog['collections'][4]['classification'] = 'new_relative_to_frozen_inventory'
        with self.assertRaisesRegex(ValueError, 'classification boundary'):
            self.validate()

    def test_adoption_adapter_activation_rejected(self):
        self.catalog['proposed_adapter']['status'] = 'implemented'
        with self.assertRaisesRegex(ValueError, 'remain a proposal'):
            self.validate()

    def test_adoption_adapter_expansion_rejected(self):
        self.catalog['proposed_adapter']['maximum_output_points'] = 4
        with self.assertRaisesRegex(ValueError, 'bounded scope'):
            self.validate()

    def test_adoption_invented_standard_error_rejected(self):
        self.catalog['proposed_adapter']['unknown_standard_error'] = '1.25'
        with self.assertRaisesRegex(ValueError, 'unknown uncertainty'):
            self.validate()

    def test_adoption_paper_license_cannot_clear_csv(self):
        artifact = self.catalog['collections'][1]['artifacts'][1]
        artifact.update(rights_status='declared_license', license_identifier='CC-BY-4.0',
                        rights_evidence_artifact_ids=['metr_early_paper'])
        with self.assertRaisesRegex(ValueError, 'cannot inherit a paper license'):
            self.validate()

    def test_adoption_uninspected_workbook_cannot_be_upgraded(self):
        self.catalog['collections'][4]['artifacts'][4]['access_status'] = 'bounded_sample_opened'
        with self.assertRaisesRegex(ValueError, 'cannot become verified content'):
            self.validate()

    def test_adoption_review_samples_are_not_tested_fixtures(self):
        self.catalog['proposed_adapter']['fixture_status'] = 'tested'
        with self.assertRaisesRegex(ValueError, 'not executable fixture'):
            self.validate()

    def test_adoption_all_industry_value_cannot_replace_private_value(self):
        self.catalog['proposed_adapter']['reviewed_private_values'][2]['decimal_value'] = '19.2'
        with self.assertRaisesRegex(ValueError, 'private-sector values'):
            self.validate()

    def test_adoption_float_value_rejected(self):
        self.catalog['proposed_adapter']['reviewed_private_values'][0]['decimal_value'] = 6.2
        with self.assertRaisesRegex(ValueError, 'decimal representation'):
            self.validate()

    def test_adoption_source_pin_must_match_url(self):
        self.catalog['collections'][1]['artifacts'][1]['git_commit'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'URL/pin mismatch'):
            self.validate()

    def test_adoption_next_action_required(self):
        self.catalog['next_actions'] = []
        with self.assertRaisesRegex(ValueError, 'next action'):
            self.validate()

    def test_adoption_doc_drift_rejected(self):
        self.markdown = self.markdown.replace('## AP001 Statistics Canada', '## AP001 Changed title')
        with self.assertRaisesRegex(ValueError, 'documentation IDs/titles'):
            self.validate()


class OrganizationalSafetyTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        from check_organizational_safety import check_catalog, check_queue
        self.check_catalog = check_catalog
        self.check_queue = check_queue
        self.catalog = check.read_json(check.DATA / 'research/organizational-safety.json')
        self.markdown = (check.DOCS / 'research/organizational-safety.md').read_text()
        self.queue = (check.DOCS / 'research/research-session-review-queue.md').read_text()
        self.inventory_hash = hashlib.sha256((check.DATA / 'source_inventory.json').read_bytes()).hexdigest()

    def validate(self):
        return self.check_catalog(self.catalog, self.inventory_hash, self.markdown)

    def test_organizational_catalog_positive(self):
        self.assertEqual(self.validate()['organizational_safety_collections'], 5)
        self.assertEqual(self.check_queue(self.queue)['research_queue_sessions'], 26)

    def test_organizational_admission_rejected(self):
        self.catalog['collector_enabled'] = True
        with self.assertRaisesRegex(ValueError, 'cannot enable admission'):
            self.validate()

    def test_organizational_family_promotion_rejected(self):
        self.catalog['collections'][0]['collection_status'] = 'collected'
        with self.assertRaisesRegex(ValueError, 'cannot enable collection'):
            self.validate()

    def test_organizational_duplicate_candidates_rejected(self):
        self.catalog['collections'][1]['candidate_id'] = 'OS001'
        with self.assertRaisesRegex(ValueError, 'candidate IDs'):
            self.validate()

    def test_organizational_inventory_drift_rejected(self):
        self.catalog['baseline_inventory']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'frozen inventory'):
            self.validate()

    def test_organizational_company_ranking_rejected(self):
        self.catalog['ranking_basis'] = 'company_safety'
        with self.assertRaisesRegex(ValueError, 'safety ranking'):
            self.validate()

    def test_organizational_raw_records_rejected(self):
        self.catalog['raw_source_content'] = []
        with self.assertRaisesRegex(ValueError, 'raw or profiling'):
            self.validate()

    def test_organizational_signed_url_rejected(self):
        self.catalog['collections'][0]['artifacts'][0]['url'] += '?Signature=unsafe'
        with self.assertRaisesRegex(ValueError, 'Signed or credential'):
            self.validate()

    def test_organizational_rights_inheritance_rejected(self):
        self.catalog['collections'][0]['artifacts'][0]['rights_status'] = 'declared_license'
        with self.assertRaisesRegex(ValueError, 'rights declaration'):
            self.validate()

    def test_organizational_missing_provenance_rejected(self):
        self.catalog['collections'][0]['findings'][0]['evidence_artifact_ids'] = ['unknown']
        with self.assertRaisesRegex(ValueError, 'lacks provenance'):
            self.validate()

    def test_organizational_collapsed_statement_support_rejected(self):
        self.catalog['collections'][0]['findings'][0]['support_kind'] = 'formal_commitment'
        with self.assertRaisesRegex(ValueError, 'classes must stay separate'):
            self.validate()

    def test_organizational_external_assessment_attribution_rejected(self):
        finding = self.catalog['collections'][0]['findings'][0]
        finding['statement_kind'] = 'external_assessment'
        finding['support_kind'] = 'organization_reported'
        with self.assertRaisesRegex(ValueError, 'External assessment'):
            self.validate()

    def test_organizational_mandate_is_not_action(self):
        self.catalog['interpretation_guards']['policy_implies_exercised_authority'] = True
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_organizational_staffing_is_not_safety(self):
        self.catalog['interpretation_guards']['staff_counts_imply_safety'] = True
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_organizational_missing_disclosure_is_not_absence(self):
        self.catalog['interpretation_guards']['missing_disclosure_implies_absence'] = True
        with self.assertRaisesRegex(ValueError, 'interpretation guard'):
            self.validate()

    def test_organizational_external_review_not_unqualified(self):
        self.catalog['interpretation_guards']['metr_pilot_publication_veto_must_be_disclosed'] = False
        with self.assertRaisesRegex(ValueError, 'external-review qualification'):
            self.validate()

    def test_organizational_textual_correction_not_effectiveness(self):
        self.catalog['interpretation_guards']['metr_text_changes_imply_effectiveness'] = True
        with self.assertRaisesRegex(ValueError, 'completed follow-up boundary'):
            self.validate()

    def test_organizational_aisi_paper_cannot_license_card(self):
        artifact = next(a for a in self.catalog['collections'][3]['artifacts'] if a['artifact_id'] == 'openai_astra')
        artifact.update(rights_status='declared_license', license_identifier='CC-BY-4.0', rights_evidence_artifact_ids=['aisi_astra_arxiv_v1'])
        with self.assertRaisesRegex(ValueError, 'license cannot clear'):
            self.validate()

    def test_organizational_revised_protocol_not_duplicate_rows(self):
        self.catalog['interpretation_guards']['aisi_card_and_later_paper_relation'] = 'identical_results'
        with self.assertRaisesRegex(ValueError, 'completed follow-up boundary'):
            self.validate()

    def test_organizational_closed_action_not_reassigned(self):
        self.catalog['focused_follow_up_prompts'][0]['action_id'] = 'OS-A04'
        with self.assertRaisesRegex(ValueError, 'open gap'):
            self.validate()

    def test_organizational_adapter_not_implemented(self):
        self.catalog['proposed_adapter']['status'] = 'implemented'
        with self.assertRaisesRegex(ValueError, 'remain a proposal'):
            self.validate()

    def test_organizational_reviewed_source_is_not_fixture(self):
        self.catalog['proposed_adapter']['fixture_status'] = 'tested'
        with self.assertRaisesRegex(ValueError, 'remain a proposal'):
            self.validate()

    def test_organizational_adapter_expansion_rejected(self):
        self.catalog['proposed_adapter']['maximum_clause_records'] = 7
        with self.assertRaisesRegex(ValueError, 'bounded scope'):
            self.validate()

    def test_organizational_question_expansion_rejected(self):
        self.catalog['proposed_adapter']['question_allowlist']['204'].append('Q9')
        with self.assertRaisesRegex(ValueError, 'bounded scope'):
            self.validate()

    def test_organizational_publication_is_not_effective_date(self):
        self.catalog['proposed_adapter']['unknown_effective_date'] = '2026-10-02'
        with self.assertRaisesRegex(ValueError, 'cannot invent dates'):
            self.validate()

    def test_organizational_authority_transfer_not_inferred(self):
        self.catalog['proposed_adapter']['authority_transfer_inference_allowed'] = True
        with self.assertRaisesRegex(ValueError, 'authority transfer'):
            self.validate()

    def test_organizational_known_family_remains_enrichment(self):
        self.catalog['collections'][1]['classification'] = 'new_relative_to_frozen_inventory'
        with self.assertRaisesRegex(ValueError, 'classification changed'):
            self.validate()

    def test_organizational_next_actions_required(self):
        self.catalog['next_actions'] = []
        with self.assertRaisesRegex(ValueError, 'next action'):
            self.validate()

    def test_organizational_doc_drift_rejected(self):
        self.markdown = self.markdown.replace('## OS001 ', '## OS099 ')
        with self.assertRaisesRegex(ValueError, 'documentation IDs'):
            self.validate()

    def test_research_queue_missing_session_rejected(self):
        self.queue = '\n'.join(line for line in self.queue.splitlines() if not line.startswith('| 26 |'))
        with self.assertRaisesRegex(ValueError, '26 ordered'):
            self.check_queue(self.queue)

    def test_research_queue_premature_merge_rejected(self):
        from test_open_model_queue import synthetic_snapshot
        self.queue = synthetic_snapshot(25, 1)
        valid = self.check_queue(self.queue)
        self.assertEqual(valid['research_queue_reviews_integrated_at_snapshot'], 25)
        self.assertEqual(valid['research_queue_reviews_prepared_at_snapshot'], 1)
        self.queue = self.queue.replace('| Review prepared; integration pending |', '| Review integrated |')
        with self.assertRaisesRegex(ValueError, 'promote unfinished'):
            self.check_queue(self.queue)

    def test_research_queue_snapshot_required(self):
        self.queue = self.queue.replace('Status snapshot:', 'Current status:')
        with self.assertRaisesRegex(ValueError, 'dated snapshot'):
            self.check_queue(self.queue)


if __name__ == '__main__':
    unittest.main()
