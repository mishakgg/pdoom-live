"""Pin curated facts and boundaries, not an independent source-truth test."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import sys,unittest
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from check_persuasion_information import check_catalog,check_ledger

class PersuasionCatalogTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'data/evidence-program/research/persuasion-information.json').read_text())
        self.guide=(ROOT/'docs/evidence-program/research/persuasion-information.md').read_text()
        self.inventory=hashlib.sha256((ROOT/'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()
        self.ledger=json.loads((ROOT/'data/evidence-program/research/debategpt-correction-ledger.json').read_text())
    def rejects(self,keys,value):
        d=deepcopy(self.data);at=d
        for k in keys[:-1]:at=at[k]
        at[keys[-1]]=value
        with self.assertRaises((ValueError,KeyError)):check_catalog(d,self.inventory,self.guide,ROOT)
    def test_catalog(self):
        r=check_catalog(self.data,self.inventory,self.guide,ROOT);self.assertEqual(r['persuasion_information_collections'],5)
    def test_curated_ledger(self):self.assertEqual(check_ledger(self.ledger)['persuasion_ledger_current_assertions'],2)
    def test_wrong_pvalue_cross_comparison(self):
        self.ledger['records'][0]['p_value']='0.0678'
        with self.assertRaises(ValueError):check_ledger(self.ledger)
    def test_every_factual_number_is_pinned(self):
        for i in range(3):
            for key in ['estimate','p_value']:
                d=deepcopy(self.ledger);d['records'][i][key]='0.5'
                with self.subTest(i=i,key=key),self.assertRaises(ValueError):check_ledger(d)
    def test_source_locators_pinned(self):
        for i in range(3):
            d=deepcopy(self.ledger);d['records'][i]['source']['locator']='Unrelated figure'
            with self.assertRaises(ValueError):check_ledger(d)
    def test_boolean_types_are_strict(self):
        self.rejects(['baseline_inventory','unchanged'],1)
        for key,value in self.data['interpretation_guards'].items():
            self.rejects(['interpretation_guards',key],int(value))
        for fam,fields in self.data['critical_qualifications'].items():
            for key,value in fields.items():
                if type(value) is bool:self.rejects(['critical_qualifications',fam,key],int(value))
    def test_all_guards(self):
        for key,value in self.data['interpretation_guards'].items():self.rejects(['interpretation_guards',key],not value)
    def test_all_critical_qualifications(self):
        for fam,fields in self.data['critical_qualifications'].items():
            for key,value in fields.items():self.rejects(['critical_qualifications',fam,key],not value if type(value) is bool else 'changed')
    def test_all_collection_admissions(self):
        for i in range(5):
            self.rejects(['collections',i,'collector_enabled'],True)
            self.rejects(['collections',i,'inventory_source_id'],'GL065')
    def test_every_measurement_coverage_and_sample_pinned(self):
        for i,r in enumerate(self.data['collections']):
            for key in r['coverage']:self.rejects(['collections',i,'coverage',key],'changed')
            for j,s in enumerate(r['samples']):
                for key in s['fields']:self.rejects(['collections',i,'samples',j,'fields',key],'changed')
    def test_all_artifact_hashes(self):
        for i,r in enumerate(self.data['collections']):
            for j,a in enumerate(r['artifacts']):self.rejects(['collections',i,'artifacts',j,'artifact_sha256'],'0'*64)
    def test_seven_catalog_hashes(self):
        for i in range(7):self.rejects(['catalog_overlap_review','catalogs_compared',i,'sha256'],'0'*64)
    def test_all_35_overlap_cells(self):
        for i,r in enumerate(self.data['catalog_overlap_review']['catalogs_compared']):
            for cid in r['candidate_checks']:self.rejects(['catalog_overlap_review','catalogs_compared',i,'candidate_checks',cid,'study_match'],True)
    def test_synthetic_fixture_only(self):
        p=HERE/'tests/fixtures/persuasion-information'
        self.assertEqual(sorted(x.name for x in p.iterdir() if x.is_file()),['NOTICE.md','synthetic-contrast-ledger.json'])
        d=json.loads((p/'synthetic-contrast-ledger.json').read_text());self.assertEqual(d['input_kind'],'synthetic_fixture');self.assertNotEqual(d['study']['doi'],self.ledger['study']['doi'])
    def test_guide_identity(self):
        with self.assertRaises(ValueError):check_catalog(self.data,self.inventory,self.guide.replace('## PI001 ','## PI999 '))

CASES={
 'base':(['repository_review_commit'],'0'*40), 'admitted':(['operational_admission'],'admitted'),
 'collector':(['collector_enabled'],True), 'participant_acquired':(['participant_records_acquired'],True),
 'participant_vendored':(['participant_records_vendored'],True), 'source_body':(['source_bodies_vendored'],True),
 'source_execution':(['source_code_execution'],True), 'canonical_mapping':(['canonical_contract_mapping'],'implemented'),
 'families':(['producer_family_count'],5), 'studies':(['empirical_collection_count'],4),
 'source_url':(['collections',0,'artifacts',0,'url'],'http://127.0.0.1'),
 'evidence':(['collections',0,'findings',0,'evidence_artifact_ids'],['wrong']),
 'unknown_rights':(['collections',3,'artifacts',1,'license_identifier'],'OGL-3.0'),
 'csv_parser_claim':(['offline_validator','participant_csv_adapter_implemented'],True),
 'source_parser_claim':(['offline_validator','source_extractor_implemented'],True),
 'missing_holds':(['holds'],[]),'missing_prompts':(['focused_follow_up_prompts'],[]),
 'missing_actions':(['next_actions'],[]),'missing_corrections':(['corrections'],[]),
 'promote_action':(['next_actions',4,'status'],'completed'),
 'missing_overlap':(['catalog_overlap_review','catalogs_compared'],[]),
}
for name,(keys,value) in CASES.items():
    def test(self,keys=keys,value=value):self.rejects(keys,value)
    setattr(PersuasionCatalogTests,'test_reject_'+name,test)
if __name__=='__main__':unittest.main()
