"""Catalog boundaries only; source documentary checks are recorded separately."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from check_incidents_near_misses import check_catalog
ROOT=HERE.parents[2]
BASE=json.loads((ROOT/'data/evidence-program/research/incidents-near-misses.json').read_text())
SHA=hashlib.sha256((ROOT/'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()
GUIDE=(ROOT/'docs/evidence-program/research/incidents-near-misses.md').read_text()

class CatalogTests(unittest.TestCase):
    def check(self,d):return check_catalog(d,SHA,GUIDE,ROOT)
    def test_fixed_catalog(self):
        r=self.check(BASE);self.assertEqual(r['incidents_near_misses_collections'],8);self.assertEqual(r['incidents_near_misses_overlap_cells'],120)
    def test_prior_footprint_complete(self):
        self.assertEqual(len(BASE['prior_catalog_fingerprints']),15)
        self.assertEqual(BASE['overlap_review']['prior_collection_count'],81)
        self.assertEqual(BASE['overlap_review']['prior_artifact_count'],580)
    def test_real_source_hash_distinct_from_derivative(self):
        a=BASE['collections'][0]['artifacts'][1]
        self.assertEqual(a['source_bytes'],529128)
        self.assertEqual(a['source_sha256'],'c92e1bec238e757867d67ea5bf0b26f4a3e9223d0b92a9a7ce76d446518f4fa4')
        self.assertFalse(a['source_bytes_vendored'])
    def test_aliases_not_canonical_artifact_creation(self):
        c=BASE['collections']
        self.assertEqual(c[0]['artifacts'][1]['same_artifact_prior_id'],'asi005_dictionary')
        self.assertEqual(c[7]['artifacts'][0]['same_artifact_prior_id'],'asi007_initial')
    def test_no_sensitive_payload(self):
        raw=json.dumps(BASE)
        for key in ['patient_name','vin_number','home_address','clinical_history','personnel_record','conversation_payload']:
            self.assertNotIn('"'+key+'"',raw)

def mutation(path,value):
    def test(self):
        d=copy.deepcopy(BASE);where=d
        for k in path[:-1]:where=where[k]
        where[path[-1]]=value
        with self.assertRaises((ValueError,KeyError,TypeError)):self.check(d)
    return test
MUTATIONS=[
('admission',['operational_admission'],'admitted'),('live',['collector_enabled'],True),
('execution',['source_code_execution'],True),('report_bool',['original_report_count'],True),
('count_bool',['collection_count'],True),('canonical',['canonical_contract_mapping'],'approved'),
('baseline',['baseline_inventory','source_family_count'],65),
('sgonew',['collections',0,'inventory_relationship'],'new'),
('sgodup',['collections',0,'findings',0,'same_evidence_prior_finding_ids'],[]),
('reportversion',['collections',0,'sample_records',0,'report_version'],True),
('releaseid',['collections',0,'sample_records',1,'report_id'],'invented'),
('priorcontent',['collections',0,'sample_records',0,'previous_content_available'],True),
('systems',['collections',1,'sample_records',0,'unit'],'patients'),
('causation',['collections',1,'sample_records',0,'ai_caused_defect'],'confirmed'),
('maude',['collections',1,'sample_records',1,'near_miss'],'verified'),
('nzconflict',['collections',2,'sample_records',0,'alert_conflict'],'resolved'),
('odirate',['collections',3,'sample_records',0,'fleet_risk_rate'],'0.1'),
('duplicate',['collections',3,'sample_records',1,'relation'],'independent_event'),
('ntsb',['collections',4,'sample_records',0,'revision_scope'],'cause_changed'),
('adjudicated',['collections',5,'sample_records',0,'allegations'],'proved'),
('audit',['collections',5,'sample_records',1,'independent_audit'],True),
('requestpct',['collections',6,'sample_records',0,'reported_percent'],0.8),
('allusers',['collections',7,'sample_records',1,'population'],'all_users'),
('events',['collections',7,'sample_records',0,'independent_event_count'],2),
('claimrole',['collections',7,'findings',0,'assertion_role'],'independent_proof'),
('sourcehash',['collections',1,'artifacts',0,'source_sha256'],'a'*64),
('rights',['collections',1,'artifacts',0,'rights_status'],'universal_public_domain'),
('ref',['collections',0,'findings',0,'evidence_artifact_ids'],['not_real']),
('loc',['collections',0,'artifacts',0,'evidence_locator'],''),
('unsafeurl',['collections',0,'artifacts',0,'url'],'http://localhost/'),
('rawsource',['collections',0,'artifacts',1,'source_bytes_vendored'],True),
('missingprior',['prior_catalog_fingerprints'],BASE['prior_catalog_fingerprints'][:-1]),
('overlapcount',['overlap_review','candidate_by_catalog_assessment_count'],119),
('sourceparser',['implementation','source_parser_implemented'],True),
('prompt',['follow_up_prompts',0,'prompt'],'Search everything.'),
('dispatch',['follow_up_prompts',0,'status'],'sent'),
('private',['collections',0,'limitations',0],'Sentinel_private'),
]
for name,path,value in MUTATIONS:setattr(CatalogTests,'test_reject_'+name,mutation(path,value))
if __name__=='__main__':unittest.main()
