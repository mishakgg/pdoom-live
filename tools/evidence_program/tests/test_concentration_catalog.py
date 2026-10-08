"""Source-qualified concentration catalog regressions; no live requests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from check_concentration_dependencies import check_catalog, GUARDS
ROOT = HERE.parents[1]


class ConcentrationCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / 'data/evidence-program/research/concentration-dependencies.json').read_text())
        self.markdown = (ROOT / 'docs/evidence-program/research/concentration-dependencies.md').read_text()
        self.inventory_hash = hashlib.sha256((ROOT / 'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()

    def validate(self):
        return check_catalog(self.catalog, self.inventory_hash, self.markdown)

    def reject(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.validate()

    def test_positive(self):
        result = self.validate()
        self.assertEqual(result['concentration_collections'], 5)
        self.assertEqual(result['concentration_research_fixtures'], 1)

    def test_admission_rejected(self):
        self.catalog['operational_admission'] = 'admitted'; self.reject('cannot enable')

    def test_family_admission_rejected(self):
        self.catalog['collections'][0]['collector_enabled'] = True; self.reject('family cannot')

    def test_inventory_drift_rejected(self):
        self.catalog['baseline_inventory']['sha256'] = '0' * 64; self.reject('inventory mismatch')

    def test_source_id_allocation_rejected(self):
        self.catalog['collections'][0]['inventory_source_id'] = 'GL041'; self.reject('allocate')

    def test_guards_cannot_be_relaxed(self):
        original = deepcopy(self.catalog)
        for key, value in GUARDS.items():
            with self.subTest(guard=key):
                self.catalog = deepcopy(original)
                self.catalog['interpretation_guards'][key] = not value
                self.reject('interpretation')

    def test_relationship_class_collapse_rejected(self):
        self.catalog['relationship_classes'].remove('contractual_access'); self.reject('relationship boundary')

    def test_graph_cannot_become_deployment_evidence(self):
        self.catalog['collections'][1]['relationship_basis'] = ['disclosed_operational_use']; self.reject('evidence basis')

    def test_raw_body_rejected(self):
        self.catalog['raw_source_content_in_catalog'] = True; self.reject('raw bodies')

    def test_participant_rows_rejected(self):
        self.catalog['participant_rows_in_catalog'] = True; self.reject('participant rows')

    def test_risk_ranking_rejected(self):
        self.catalog['ranking_basis'] = 'common_mode_failure_probability'; self.reject('source utility')

    def test_false_no_acquisition_rejected(self):
        self.catalog['fixture_acquisition']['count'] = 0; self.reject('acquisition scope')

    def test_signed_link_rejected(self):
        self.catalog['collections'][0]['artifacts'][0]['url'] += '?access_token=secret'; self.reject('Signed or credential')

    def test_unknown_artifact_reference_rejected(self):
        self.catalog['collections'][0]['findings'][0]['evidence_artifact_ids'] = ['absent']; self.reject('scoped provenance')

    def test_unqualified_finding_rejected(self):
        self.catalog['collections'][0]['findings'][0]['qualification'] = ''; self.reject('scoped provenance')

    def test_rights_inheritance_rejected(self):
        a = next(a for a in self.catalog['collections'][1]['artifacts'] if a['artifact_id'] == 'cd002_graph')
        a['rights_scope'] = 'all_upstream_package_metadata'; self.reject('rights must remain scoped')

    def test_unbacked_license_rejected(self):
        a = self.catalog['collections'][0]['artifacts'][0]
        a['rights_status'] = 'declared_license'; a['license_identifier'] = 'OGL'; a['rights_evidence_artifact_ids'] = []
        self.reject('declaration lacks evidence')

    def test_atrs_roles_not_automatic_contradiction(self):
        self.catalog['critical_qualifications']['atrs']['automatic_conflict_inference'] = True; self.reject('ATRS metadata')

    def test_atrs_undisclosed_version_remains_null(self):
        self.catalog['critical_qualifications']['atrs']['model_version_when_undisclosed'] = 'current'; self.reject('ATRS metadata')

    def test_redbox_date_labels_distinct(self):
        self.catalog['critical_qualifications']['atrs']['redbox_publication_labels']['body_date_published'] = '2025-04-28'; self.reject('ATRS metadata')

    def test_resolution_time_not_retrieval_time(self):
        self.catalog['critical_qualifications']['depsdev']['resolved_at'] = '2026-10-08T01:04:58Z'; self.reject('graph time')

    def test_package_license_not_dataset_license(self):
        self.catalog['critical_qualifications']['depsdev']['package_license_is_dataset_license'] = True; self.reject('license inference')

    def test_survey_denominator_not_firms(self):
        self.catalog['critical_qualifications']['bank']['denominator_raw'] = '118 responding firms'; self.reject('Survey denominator')

    def test_unknown_survey_count_not_imputed(self):
        self.catalog['critical_qualifications']['bank']['raw_category_denominator_counts'] = {'cloud': 354}; self.reject('Survey denominator')

    def test_bank_database_rights_not_report_rights(self):
        self.catalog['critical_qualifications']['bank']['report_ogl_verified'] = True; self.reject('rights boundary')

    def test_omb_counting_units_not_silently_reconciled(self):
        self.catalog['critical_qualifications']['omb']['count_discrepancy_resolved'] = True; self.reject('OMB counting')

    def test_omb_normalized_flags_not_verbatim(self):
        self.catalog['critical_qualifications']['omb']['all_flags_are_verbatim_agency_responses'] = True; self.reject('normalized flags')

    def test_omb_user_bands_not_split(self):
        self.catalog['critical_qualifications']['omb']['per_product_user_band_allocation'] = 1000; self.reject('OMB counting')

    def test_ftc_anonymity_not_inferred(self):
        self.catalog['critical_qualifications']['ftc']['parity_parties']['cloud_partner'] = 'named cloud'; self.reject('FTC anonymity')

    def test_ftc_staff_summary_not_inspected_clause(self):
        self.catalog['critical_qualifications']['ftc']['direct_contract_clause_inspected'] = True; self.reject('evidence origin')

    def test_ftc_cutoffs_not_current(self):
        self.catalog['critical_qualifications']['ftc']['current_relationships_verified'] = True; self.reject('historical cutoff')

    def test_reader_network_expansion_rejected(self):
        self.catalog['offline_reader']['network_enabled'] = True; self.reject('reader bounded')

    def test_reader_identity_scope_required(self):
        self.catalog['offline_reader']['artifact_local_review_ids'] = False; self.reject('reader bounded')

    def test_reader_pin_drift_rejected(self):
        self.catalog['offline_reader']['fixture_sha256'] = '0' * 64; self.reject('fixture pins')

    def test_atrs_not_implemented_by_graph_reader(self):
        self.catalog['atrs_proposal']['status'] = 'implemented'; self.reject('ATRS proposal')

    def test_corrections_preserved(self):
        self.catalog['corrections'] = []; self.reject('corrections missing')

    def test_open_action_needs_prompt(self):
        self.catalog['focused_follow_up_prompts'].pop(); self.reject('one focused prompt')

    def test_completed_action_not_assigned_again(self):
        target = self.catalog['focused_follow_up_prompts'][0]['action_id']
        next(a for a in self.catalog['next_actions'] if a['action_id'] == target)['status'] = 'completed'
        self.reject('one focused prompt')

    def test_guide_identity_matches(self):
        self.markdown = self.markdown.replace('## CD001 ', '## CD099 '); self.reject('guide IDs')


if __name__ == '__main__':
    unittest.main()
