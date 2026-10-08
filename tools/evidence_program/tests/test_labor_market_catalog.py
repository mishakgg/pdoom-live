from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from check_labor_market import check_catalog, check_fixtures
ROOT=HERE.parents[2]
CAT=json.loads((ROOT/'data/evidence-program/research/labor-market.json').read_text())
GUIDE=(ROOT/'docs/evidence-program/research/labor-market.md').read_text()
INV=hashlib.sha256((ROOT/'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()

class CatalogTests(unittest.TestCase):
    def test_reviewed_catalog(self):
        result=check_catalog(CAT,INV,GUIDE,ROOT)
        self.assertEqual(result['labor_market_collections'],4)
        self.assertEqual(result['labor_market_qualified_findings'],26)
    def test_fixture(self):self.assertEqual(check_fixtures(ROOT)['labor_market_verified_observations'],10)
    def test_missing_finding_in_guide(self):
        f=CAT['collections'][0]['findings'][0]['claim']
        with self.assertRaises(ValueError):check_catalog(CAT,INV,GUIDE.replace(f,''),ROOT)
    def test_missing_prompt_in_guide(self):
        p=CAT['follow_up_prompts'][0]['prompt']
        with self.assertRaises(ValueError):check_catalog(CAT,INV,GUIDE.replace(p,''),ROOT)
    def test_inventory_drift(self):
        with self.assertRaises(ValueError):check_catalog(CAT,'0'*64,GUIDE,ROOT)
    def test_missing_source_link(self):
        u=CAT['collections'][0]['artifacts'][0]['url']
        with self.assertRaises(ValueError):check_catalog(CAT,INV,GUIDE.replace(u,''),ROOT)

def mutation(name,fn):
    def test(self):
        c=copy.deepcopy(CAT);fn(c)
        with self.assertRaises(ValueError):check_catalog(c,INV,GUIDE,ROOT)
    setattr(CatalogTests,'test_reject_'+name,test)
mutation('admission',lambda c:c.update(operational_admission='admitted'))
mutation('collection',lambda c:c.update(collector_enabled=True))
mutation('execution',lambda c:c.update(source_code_execution=True))
mutation('baseline',lambda c:c.update(repository_review_commit='0'*40))
mutation('inventory_count',lambda c:c['baseline_inventory'].update(source_family_count=68))
mutation('new_family',lambda c:c['collections'][2].update(inventory_source_id=None))
mutation('ranking',lambda c:c.update(priority_ranking=['LM004']))
mutation('source_rights',lambda c:c['collections'][1]['artifacts'][0].update(rights_scope='All advertisements'))
mutation('status',lambda c:c['implementation'].update(earlier_reference_years='all_previous_year'))
mutation('reference',lambda c:c['implementation']['verified_reference_years'].update({'2022':2021}))
mutation('population',lambda c:c['implementation']['selected_dimensions'].update(geo='FR'))
mutation('live_calls',lambda c:c['implementation'].update(network_calls=1))
mutation('max_bytes',lambda c:c['implementation'].update(max_bytes=99999999))
mutation('mapping',lambda c:c['implementation'].update(canonical_import=True))
mutation('source_hash',lambda c:c['implementation'].update(fixture_source_sha256='0'*64))
mutation('source_observations',lambda c:c['implementation'].update(fixture_observations=13))
mutation('pdoom',lambda c:c.update(pdoom=0.2))
mutation('exposure',lambda c:c.update(exposure_score=0.7))
mutation('btos_admission',lambda c:c['held_candidates'][0].update(status='admitted'))
mutation('btos_rights',lambda c:c['held_candidates'][0].update(data_rights='CC0'))
mutation('prior_pin',lambda c:c['prior_catalog_fingerprints'][0].update(sha256='0'*64))
mutation('overlap_count',lambda c:c['overlap_review'].update(prior_catalog_count=12))
mutation('lost_comparison',lambda c:c['overlap_review']['catalogs'][0]['candidate_checks'].pop('LM-H01'))
mutation('lost_finding',lambda c:c['collections'][1]['findings'].pop())
mutation('lost_hold',lambda c:c['holds'].pop())
mutation('prompt_dispatched',lambda c:c['follow_up_prompts'][0].update(status='running'))
mutation('held_completed',lambda c:c['next_actions'][2].update(status='completed'))
mutation('raw_other_source',lambda c:c['collections'][0]['artifacts'][0].update(source_bytes_vendored=True))
mutation('unsafe_url',lambda c:c['collections'][0]['artifacts'][0].update(url='http://127.0.0.1/'))
mutation('causal_claim',lambda c:c['collections'][0]['findings'][0].update(qualification='Causal AI job loss.'))
if __name__=='__main__':unittest.main()
