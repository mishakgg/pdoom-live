from __future__ import annotations
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from check_forecast_surveys import check_catalog,check_fixtures
ROOT=HERE.parents[2]
CAT=json.loads((ROOT/'data/evidence-program/research/forecast-surveys.json').read_text())
GUIDE=(ROOT/'docs/evidence-program/research/forecast-surveys.md').read_text()
INV=hashlib.sha256((ROOT/'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()


class CatalogTests(unittest.TestCase):
    def test_reviewed_catalog(self):
        out=check_catalog(CAT,INV,GUIDE,ROOT)
        self.assertEqual(out['forecast_surveys_collections'],7)
        self.assertEqual(out['forecast_surveys_overlap_comparison_cells'],98)
    def test_fixture(self):self.assertEqual(check_fixtures(ROOT)['forecast_surveys_published_group_summaries'],4)
    def test_inventory_drift(self):
        with self.assertRaises(ValueError):check_catalog(CAT,'0'*64,GUIDE,ROOT)
    def test_missing_finding_in_guide(self):
        with self.assertRaises(ValueError):check_catalog(CAT,INV,GUIDE.replace(CAT['collections'][0]['findings'][0]['claim'],''),ROOT)
    def test_missing_qualification(self):
        with self.assertRaises(ValueError):check_catalog(CAT,INV,GUIDE.replace(CAT['collections'][1]['findings'][3]['qualification'],''),ROOT)
    def test_missing_prompt(self):
        with self.assertRaises(ValueError):check_catalog(CAT,INV,GUIDE.replace(CAT['follow_up_prompts'][0]['prompt'],''),ROOT)
    def test_missing_artifact_link(self):
        with self.assertRaises(ValueError):check_catalog(CAT,INV,GUIDE.replace(CAT['collections'][0]['artifacts'][0]['url'],''),ROOT)
    def test_prior_catalogs_are_all_checked(self):
        self.assertEqual(len(CAT['prior_catalog_fingerprints']),14)
        self.assertTrue(all(len(x['candidate_checks'])==7 for x in CAT['overlap_review']['catalogs']))

    def checkout_with_autocrlf(self, name):
        source=HERE/'fixtures'/name
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'fixture';shutil.copytree(source,target)
            original={p.relative_to(target):p.read_bytes()for p in target.rglob('*.json')}
            self.assertTrue(original)
            env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
            def git(*args):
                subprocess.run(['git','-c','core.autocrlf=true','-c','core.safecrlf=false','-c','core.attributesFile='+os.devnull,'-C',tmp,*args],check=True,capture_output=True,text=True,env=env,timeout=10)
            git('init','--quiet');git('add','--all')
            for rel in original:(target/rel).unlink()
            git('checkout-index','--all','--force')
            for rel,raw in original.items():self.assertEqual((target/rel).read_bytes(),raw,str(rel))
            if name=='forecast-surveys':
                from read_leap_aggregates import read_fixture
                self.assertEqual(len(read_fixture(target)['records']),4)
            else:
                from read_agentdojo_metadata import normalize_run
                out=normalize_run((target/'clean.synthetic.json').read_bytes(),json.loads((target/'manifest.synthetic.json').read_bytes()))
                self.assertEqual(out['duration_seconds'],'4.5')

    @unittest.skipUnless(shutil.which('git'),'Git is required for actual checkout regression')
    def test_leap_autocrlf_checkout_preserves_hashes(self):self.checkout_with_autocrlf('forecast-surveys')

    @unittest.skipUnless(shutil.which('git'),'Git is required for actual checkout regression')
    def test_agent_security_autocrlf_checkout_preserves_hashes(self):self.checkout_with_autocrlf('agent-security-incidents')


def mutation(name,fn):
    def test(self):
        d=copy.deepcopy(CAT);fn(d)
        with self.assertRaises(ValueError):check_catalog(d,INV,GUIDE,ROOT)
    setattr(CatalogTests,'test_reject_'+name,test)


mutation('admission',lambda d:d.update(operational_admission='admitted'))
mutation('collection',lambda d:d.update(collector_enabled=True))
mutation('execution',lambda d:d.update(source_code_execution=True))
mutation('respondent_acquisition',lambda d:d.update(respondent_data_acquired=True))
mutation('wrong_base',lambda d:d.update(repository_review_commit='0'*40))
mutation('inventory_count',lambda d:d['baseline_inventory'].update(source_family_count=68))
mutation('collection_missing',lambda d:d['collections'].pop())
mutation('new_espai_family',lambda d:d['collections'][0].update(inventory_source_id=None))
mutation('new_leap_family',lambda d:d['collections'][2].update(inventory_source_id=None))
mutation('pooled_forecast',lambda d:d.update(pooled_forecast='0.05'))
mutation('pdoom',lambda d:d.update(pdoom='0.05'))
mutation('rights',lambda d:d['collections'][1]['artifacts'][0].update(rights_scope='All respondent data may be reused'))
mutation('missing_rights',lambda d:d['collections'][2]['artifacts'][0].update(rights_status='unknown'))
mutation('unsafe_url',lambda d:d['collections'][0]['artifacts'][0].update(url='http://127.0.0.1'))
mutation('raw_original_fixture',lambda d:d['implementation'].update(original_page_vendored=True))
mutation('false_html_extractor',lambda d:d['implementation'].update(source_extraction_implemented=True))
mutation('fixture_hash',lambda d:d['implementation'].update(fixture_sha256='0'*64))
mutation('source_hash_equal_derivative',lambda d:d['implementation'].update(original_page_sha256=d['implementation']['fixture_sha256']))
mutation('network_calls',lambda d:d['implementation'].update(network_calls=1))
mutation('large_input',lambda d:d['implementation'].update(max_bytes=99999999))
mutation('canonical_import',lambda d:d['implementation'].update(canonical_import=True))
mutation('prior_fingerprint',lambda d:d['prior_catalog_fingerprints'][0].update(sha256='0'*64))
mutation('overlap_count',lambda d:d['overlap_review'].update(prior_catalog_count=13))
mutation('missing_comparison',lambda d:d['overlap_review']['catalogs'][0]['candidate_checks'].pop('FS004'))
mutation('missing_finding',lambda d:d['collections'][1]['findings'].pop())
mutation('missing_hold',lambda d:d['holds'].pop())
mutation('prompt_dispatched',lambda d:d['follow_up_prompts'][0].update(status='running'))
mutation('held_completed',lambda d:d['next_actions'][2].update(status='completed_bounded_review'))
mutation('xpt_default_as_forecast',lambda d:d['collections'][1]['sample_record'].update(default_is_observation=True))
mutation('xpt_timestamp_new_people',lambda d:d['collections'][1]['denominators'].update(analyzed_experts=236))
mutation('espai_horizon_imputed',lambda d:d['collections'][0]['sample_record'].update(horizon='2100-12-31'))
mutation('nlp_as_probability',lambda d:d['collections'][3]['sample_record'].update(kind='event_probability'))
mutation('nlp_item_n_imputed',lambda d:d['collections'][3]['sample_record'].update(item_n=327))
mutation('muller_unique_count',lambda d:d['collections'][4]['denominators'].update(unique_respondents=170))
mutation('muller_never_kept_as_date',lambda d:d['collections'][4]['sample_record'].update(never_treatment='year5001'))
mutation('swedish_translation',lambda d:d['collections'][5]['sample_record'].update(translation_status='original'))
mutation('swedish_renormalized',lambda d:d['collections'][5]['sample_record'].update(rounded_sum_percent='100.0'))
mutation('swedish_journal_n_imputed',lambda d:d['collections'][5]['denominators'].update(journal_item_n=937))
mutation('aifm_simulations_people',lambda d:d['collections'][6]['sample_record'].update(people_count=9612))
mutation('aifm_config_overwrites_export',lambda d:d['collections'][6]['sample_record'].update(total_rollouts=10000))
mutation('aifm_conditional_quantile',lambda d:d['collections'][6]['sample_record'].update(p50_semantics='achieved_only'))
mutation('aifm_export_timezone_imputed',lambda d:d['collections'][6]['sample_record'].update(export_timezone='UTC'))
mutation('source_body_vendored',lambda d:d['collections'][0]['artifacts'][0].update(source_bytes_vendored=True))

if __name__=='__main__':unittest.main()
