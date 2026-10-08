import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_agent_security_incidents import check_catalog,check_fixtures
ROOT=Path(__file__).resolve().parents[3]
CAT=ROOT/'data/evidence-program/research/agent-security-incidents.json'
GUIDE=ROOT/'docs/evidence-program/research/agent-security-incidents.md'

class AgentCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads(CAT.read_text());self.markdown=GUIDE.read_text()
        self.inventory=hashlib.sha256((ROOT/'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()
    def check(self):return check_catalog(self.catalog,self.inventory,self.markdown,ROOT)
    def test_reviewed_catalog(self):self.assertEqual(self.check()['agent_security_collections'],7)
    def test_synthetic_fixture(self):self.assertEqual(check_fixtures(ROOT)['agent_security_public_real_trace_fixtures'],0)
    def test_guide_claim_drift(self):
        self.markdown=self.markdown.replace(self.catalog['collections'][0]['findings'][0]['claim'],'changed')
        with self.assertRaises(ValueError):self.check()
    def test_guide_qualification_drift(self):
        self.markdown=self.markdown.replace(self.catalog['collections'][5]['findings'][1]['qualification'],'changed')
        with self.assertRaises(ValueError):self.check()
    def test_guide_prompt_drift(self):
        self.markdown=self.markdown.replace(self.catalog['follow_up_prompts'][0]['prompt'],'changed')
        with self.assertRaises(ValueError):self.check()
    def test_inventory_hash_drift(self):
        self.inventory='0'*64
        with self.assertRaises(ValueError):self.check()


def change(path,value):
    def test(self):
        node=self.catalog
        for key in path[:-1]:node=node[key]
        node[path[-1]]=value
        with self.assertRaises(ValueError):self.check()
    return test

MUTATIONS=[
 (['original_report_count'],2),(['collection_count'],8),(['collector_enabled'],True),
 (['operational_admission'],'admitted'),(['source_code_execution'],True),
 (['collections',0,'findings',1,'claim'],'security=True means safe'),
 (['collections',0,'artifacts',1,'rights_status'],'MIT_all_trace_payloads'),
 (['collections',0,'artifacts',1,'source_bytes_vendored'],True),
 (['collections',1,'findings',3,'qualification'],'No denominator ambiguity'),
 (['collections',2,'findings',1,'claim'],'pass^k is any successful attempt'),
 (['collections',3,'measurement_regime'],'Measured continuous autonomous agent runtime'),
 (['collections',3,'findings',5,'qualification'],'FAQ is current frontier maximum'),
 (['collections',4,'author_authority'],'Independent NHTSA causal finding'),
 (['collections',4,'findings',0,'claim'],'950 victims'),
 (['collections',5,'findings',1,'claim'],'All original findings permanently retained'),
 (['collections',5,'findings',3,'qualification'],'March decision supersedes February decision'),
 (['collections',5,'artifacts',2,'rights_status'],'OAIC license automatically covers all ART judgments'),
 (['collections',6,'findings',2,'claim'],'Memory proved to cause clinical harm'),
 (['collections',6,'findings',0,'evidence_artifact_ids'],['asi007_initial']),
 (['implementation','actual_attacked_run_interpretation'],'verified_success'),
 (['implementation','network_calls'],1),(['implementation','max_bytes'],9999999),
 (['implementation','public_real_trace_fixtures'],1),(['implementation','task_execution'],True),
 (['implementation','missing_fields'],[]),(['revision_chains',0,'after'],70),
 (['revision_chains',0,'correction_publication_date'],'2025-08-08'),
 (['revision_chains',3,'event_count'],2),(['overlap_review','prior_catalog_count'],11),
 (['next_actions',2,'status'],'completed'),(['follow_up_prompts',0,'prompt'],'Collect all attack traces'),
 (['holds'],[]),(['prior_catalog_fingerprints',0,'sha256'],'0'*64),
]
for i,(path,value)in enumerate(MUTATIONS):setattr(AgentCatalogTests,'test_semantic_drift_%02d'%i,change(path,value))
if __name__=='__main__':unittest.main()
