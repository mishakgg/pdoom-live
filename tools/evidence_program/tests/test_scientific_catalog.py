"""Metadata/claim mutations, not independent scientific truth or rights tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parents[1]; ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from check_scientific_progress import check_catalog, check_ledger
import validate_scientific_ledger as ledger

class ScientificCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((ROOT/'data/evidence-program/research/scientific-progress.json').read_text())
        self.markdown=(ROOT/'docs/evidence-program/research/scientific-progress.md').read_text()
        self.inventory=hashlib.sha256((ROOT/'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()
        self.ledger=(ROOT/'data/evidence-program/research/alab-correction-ledger.json').read_bytes()
    def rejects(self,keys,value):
        data=deepcopy(self.catalog);at=data
        for key in keys[:-1]:at=at[key]
        at[keys[-1]]=value
        with self.assertRaises((ValueError,KeyError,StopIteration)):check_catalog(data,self.inventory,self.markdown)
    def test_catalog(self):
        result=check_catalog(self.catalog,self.inventory,self.markdown,ROOT)
        self.assertEqual(result['scientific_progress_collections'],5)
        self.assertEqual(result['scientific_progress_prior_catalogs_compared'],6)
    def test_curated_ledger(self):
        self.assertEqual(check_ledger(self.ledger)['scientific_progress_current_ledger_claims'],2)
    def test_interpretation_guards(self):
        for key,value in self.catalog['interpretation_guards'].items():
            with self.subTest(key=key):self.rejects(['interpretation_guards',key],not value)
    def test_critical_qualifications(self):
        for family,fields in self.catalog['critical_qualifications'].items():
            for key,value in fields.items():
                with self.subTest(family=family,key=key):
                    self.rejects(['critical_qualifications',family,key],not value if type(value) is bool else 'changed')
    def test_every_family_admission(self):
        for i in range(5):
            self.rejects(['collections',i,'collector_enabled'],True)
            self.rejects(['collections',i,'inventory_source_id'],'GL065')
    def test_every_source_hash_null(self):
        for i,row in enumerate(self.catalog['collections']):
            for j in range(len(row['artifacts'])):
                self.rejects(['collections',i,'artifacts',j,'artifact_sha256'],'0'*64)
    def test_artifact_rights_cannot_inherit(self):
        for cid,aid in [('SP002','sp002_original'),('SP002','sp002_archive'),('SP005','sp005_14_txt')]:
            i=next(i for i,r in enumerate(self.catalog['collections']) if r['candidate_id']==cid)
            j=next(j for j,a in enumerate(self.catalog['collections'][i]['artifacts']) if a['artifact_id']==aid)
            self.rejects(['collections',i,'artifacts',j,'rights_status'],'declared_license')
    def test_provenance_references(self):
        for field in ('samples','findings'):self.rejects(['collections',0,field,0,'evidence_artifact_ids'],['missing'])
    def test_all_six_prior_catalog_hashes(self):
        data=deepcopy(self.catalog);data['catalog_overlap_review']['catalogs_compared'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):check_catalog(data,self.inventory,self.markdown,ROOT)
    def test_matrix_all_five_families(self):
        self.rejects(['catalog_overlap_review','comparison_matrix',0,'family_checks'],{})
    def test_guide_identity(self):
        with self.assertRaises(ValueError):check_catalog(self.catalog,self.inventory,self.markdown.replace('## SP001 ','## SP999 '))
    def test_validator_limits_match(self):
        spec=self.catalog['offline_validator']
        for k,v in [('maximum_bytes',ledger.MAX_BYTES),('maximum_depth',ledger.MAX_DEPTH),('maximum_input_records',ledger.MAX_RECORDS),('maximum_provenance_per_record',ledger.MAX_PROVENANCE)]:self.assertEqual(spec[k],v)
    def test_synthetic_only_fixture_directory(self):
        root=HERE/'tests/fixtures/scientific-progress'
        self.assertEqual(sorted(p.name for p in root.iterdir() if p.is_file()),['NOTICE.md','synthetic-alab-ledger.json'])
        synthetic=json.loads((root/'synthetic-alab-ledger.json').read_text());self.assertEqual(synthetic['input_kind'],'synthetic_fixture')
        self.assertNotEqual(synthetic['campaign']['doi'],json.loads(self.ledger)['campaign']['doi'])
    def test_real_counts_must_match_review(self):
        data=json.loads(self.ledger);data['records'][0]['counts']['successful']=40
        with self.assertRaises(ValueError):check_ledger(json.dumps(data).encode())
    def test_historical_access_not_promoted(self):
        data=json.loads(self.ledger);data['records'][0]['provenance'][0]['capture_status']='text_observed_hash_unavailable'
        with self.assertRaises(ValueError):check_ledger(json.dumps(data).encode())
    def test_duration_locator_separate(self):
        data=json.loads(self.ledger);data['campaign']['provenance'][0]['claim_locator']='Figure 2'
        with self.assertRaises(ValueError):check_ledger(json.dumps(data).encode())

CASES={
 'rebench_baseline':(['collections',2,'samples',0,'fields','starting_implementation_release'],'4.76'),
 'rebench_throughput':(['collections',2,'samples',1,'fields','scoring_calls_per_hour','human'],'36.8'),
 'alphatensor_field':(['collections',3,'samples',1,'fields','arithmetic'],'real_numbers'),
 'alphatensor_speedup':(['collections',3,'samples',2,'fields','expected_speedup_percent'],'10'),
 'admission':(['operational_admission'],'admitted'), 'collector':(['collector_enabled'],True),
 'mapping':(['canonical_contract_mapping'],'implemented'), 'inventory':(['baseline_inventory','sha256'],'0'*64),
 'base':(['repository_review_commit'],'0'*40), 'source_body':(['source_bodies_vendored'],True),
 'participants':(['participant_or_team_records_vendored'],True), 'unsafe_url':(['collections',0,'artifacts',0,'url'],'http://example.org'),
 'fake_hash':(['collections',0,'artifacts',0,'artifact_sha256'],'0'*64), 'missing_holds':(['holds'],[]),
 'missing_prompts':(['focused_follow_up_prompts'],[]), 'missing_catalog':(['catalog_overlap_review','catalogs_compared'],[]),
 'extraction_claim':(['offline_validator','pdf_or_web_extraction_implemented'],True),
 'casp_raw_rows':(['collections',4,'samples',0,'kind'],'observed_aggregate'),
 'i4r_completion_denominator':(['collections',0,'samples',0,'fields','completion_mean_denominators'],[33,35,35]),
 'recipe_remainder_failure':(['collections',1,'samples',0,'fields','recipe_outcomes','other_outcome_categories'],{'failed':248}),
}
for name,(keys,value) in CASES.items():
    def test(self,keys=keys,value=value):self.rejects(keys,value)
    setattr(ScientificCatalogTests,'test_reject_'+name,test)
if __name__=='__main__':unittest.main()
