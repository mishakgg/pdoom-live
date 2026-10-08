"""Synthetic metadata mutations; not validation of historical truth or rights."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parents[1]; ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from check_historical_backfills import check_catalog
import read_wmt08_scores as reader


class HistoricalCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((ROOT/'data/evidence-program/research/historical-capability-backfills.json').read_text())
        self.markdown=(ROOT/'docs/evidence-program/research/historical-capability-backfills.md').read_text()
        self.inventory=hashlib.sha256((ROOT/'data/evidence-program/source_inventory.json').read_bytes()).hexdigest()

    def rejects(self, keys, value):
        data=deepcopy(self.catalog); at=data
        for key in keys[:-1]:at=at[key]
        at[keys[-1]]=value
        with self.assertRaises((ValueError,KeyError,StopIteration)):
            check_catalog(data,self.inventory,self.markdown)

    def test_reviewed_catalog(self):
        r=check_catalog(self.catalog,self.inventory,self.markdown)
        self.assertEqual(r['historical_backfill_collections'],5)
        self.assertEqual(r['historical_backfill_artifact_references'],46)
        self.assertEqual(r['historical_backfill_findings'],44)
        self.assertEqual(r['historical_backfill_real_vendored_fixtures'],0)

    def test_all_interpretation_guards(self):
        for key,value in self.catalog['interpretation_guards'].items():
            with self.subTest(key=key):self.rejects(['interpretation_guards',key],not value)

    def test_every_family_admission(self):
        for i in range(5):
            with self.subTest(i=i):
                self.rejects(['collections',i,'collector_enabled'],True)
                self.rejects(['collections',i,'inventory_source_id'],'GL065')

    def test_reader_limits_match_catalog(self):
        pairs=[('maximum_compressed_bytes','MAX_COMPRESSED_BYTES'),('maximum_decompressed_bytes','MAX_DECOMPRESSED_BYTES'),('maximum_rows','MAX_ROWS'),('maximum_line_bytes','MAX_LINE_BYTES'),('maximum_field_bytes','MAX_FIELD_BYTES'),('maximum_score_characters','MAX_NUMBER_CHARS')]
        for key,name in pairs:self.assertEqual(self.catalog['offline_reader'][key],getattr(reader,name))
        self.assertEqual(self.catalog['offline_reader']['expected_sha256'],reader.PINNED_SHA256)
        self.assertEqual(self.catalog['critical_qualifications']['wmt']['system_type_counts'],reader.PINNED_SYSTEM_TYPE_COUNTS)

    def test_only_authored_fixture_files(self):
        files=sorted(p.name for p in (HERE/'tests/fixtures/historical-backfills').iterdir() if p.is_file())
        self.assertEqual(files,['NOTICE.md','synthetic-wmt08-scores.txt'])
        raw=(HERE/'tests/fixtures/historical-backfills/synthetic-wmt08-scores.txt').read_bytes()
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(),reader.PINNED_SHA256)
        self.assertLess(len(raw),4096)

    def test_guide_heading_identity(self):
        text=self.markdown.replace('## HC001 International Planning Competition archives','## HC001 Changed title')
        with self.assertRaisesRegex(ValueError,'headings'):check_catalog(self.catalog,self.inventory,text)

    def test_gzip_license_does_not_inherit(self):
        i=next(i for i,a in enumerate(self.catalog['collections'][1]['artifacts']) if a['artifact_id']=='hc002_gzip')
        self.rejects(['collections',1,'artifacts',i,'rights_status'],'declared_license')

    def test_each_evidence_type_references_artifact(self):
        for key in ('findings','samples','date_observations'):
            self.rejects(['collections',0,key,0,'evidence_artifact_ids'],['missing'])


CASES={
 'trec_raw_lexeme':(['collections',2,'samples',0,'fields','score_raw'],'0.3018'),
 'trec_raw_label':(['collections',2,'samples',0,'fields','run_label_raw_ocr'],'lsiasm'),
 'holds':(['holds'],[]),
 'admission':(['operational_admission'],'admitted'),
 'collection':(['collector_enabled'],True),
 'mapping':(['canonical_contract_mapping'],'implemented'),
 'inventory':(['baseline_inventory','sha256'],'0'*64),
 'base':(['repository_review_commit'],'0'*40),
 'duplicate_family':(['collections',1,'candidate_id'],'HC001'),
 'unsafe_http':(['collections',0,'artifacts',0,'url'],'http://example.org/a'),
 'unsafe_auth':(['collections',0,'artifacts',0,'url'],'https://a:b@example.org/a'),
 'signed_url':(['collections',0,'artifacts',0,'url'],'https://example.org/?token=secret'),
 'whitespace_url':(['collections',0,'artifacts',0,'url'],'https://example.org/a b'),
 'missing_provenance':(['collections',0,'artifacts',0,'provenance_locator'],''),
 'missing_qualification':(['collections',0,'findings',0,'qualification'],''),
 'date_collapse':(['collections',0,'date_observations',0,'role'],'date'),
 'body_vendoring':(['collections',1,'artifacts',0,'source_body_vendored'],True),
 'gzip_vendoring':(['real_gzip_vendored'],True),
 'full_results':(['full_score_results_in_repository'],True),
 'rescore':(['critical_qualifications','ipc','rescored_2008_same_runs'],False),
 'rerun':(['critical_qualifications','ipc','post_bugfix_2002_lpg_new_runs'],False),
 'archive_inspection':(['critical_qualifications','ipc','compressed_archive_members_inspected'],True),
 'rank':(['critical_qualifications','wmt','rank_is_ordinal_position'],True),
 'mter':(['critical_qualifications','wmt','mter_already_reversed'],False),
 'unit_range':(['critical_qualifications','wmt','score_range_is_universal_zero_to_one'],True),
 'independence':(['critical_qualifications','wmt','rows_are_independent_experiments'],True),
 'reuse':(['critical_qualifications','wmt','all_english_judgments_reused_in_news_pairs'],False),
 'denominator':(['critical_qualifications','wmt','denominator'],5000),
 'uncertainty':(['critical_qualifications','wmt','uncertainty'],{'standard_error':0}),
 'identity':(['critical_qualifications','wmt','anonymized_identity_resolution'],'guessed'),
 'publication':(['critical_qualifications','wmt','artifact_first_publication_at'],'2008-06-19'),
 'capture':(['critical_qualifications','wmt','archive_capture_at'],'2008-08-20T15:25:44Z'),
 'execution':(['critical_qualifications','wmt','execution_time'],'2008-06-19'),
 'trec_p10':(['critical_qualifications','trec','p10_conflict_resolved'],True),
 'trec_date':(['critical_qualifications','trec','settled_publication_precision'],'day'),
 'trec_access':(['critical_qualifications','trec','raw_results_archive_access'],'public_open'),
 'trec_facsimile':(['critical_qualifications','trec','facsimile_verified'],True),
 'sat_missingness':(['critical_qualifications','sat','blank_is_diagnosed_timeout'],True),
 'sat_penalty':(['critical_qualifications','sat','crash_penalty_is_runtime'],True),
 'sat_rerun':(['critical_qualifications','sat','planned_rerun_is_verified_result'],True),
 'sat_schedule':(['critical_qualifications','sat','may_6_and_9_dates_are_tentative_schedule'],False),
 'voc_abandonment':(['critical_qualifications','voc','weak_score_proves_abandonment'],True),
 'voc_date':(['critical_qualifications','voc','modern_submission_backdated_to_benchmark_year'],True),
 'voc_metric':(['critical_qualifications','voc','classification_ap_applies_to_all_tasks'],True),
 'voc_breaks':(['critical_qualifications','voc','metric_break_years'],[]),
 'reader_inputs':(['offline_reader','input_count'],2),
 'reader_network':(['offline_reader','network_enabled'],True),
 'reader_import':(['offline_reader','production_import'],True),
 'reader_schema':(['offline_reader','canonical_schema_claim'],True),
 'reader_pin':(['offline_reader','fixed_hash_allowlist'],False),
 'reader_compressed':(['offline_reader','maximum_compressed_bytes'],99999999),
 'reader_decompressed':(['offline_reader','maximum_decompressed_bytes'],99999999),
 'reader_rows':(['offline_reader','maximum_rows'],99999999),
 'reader_decimals':(['offline_reader','finite_exact_decimal_strings'],False),
 'ci_private_boundary':(['verification_separation','ci_reads_real_wmt_artifact'],True),
 'private_output':(['verification_separation','private_real_acceptance','full_output_published'],True),
 'ci_source':(['offline_reader','ci_source'],'real_source_fixture'),
 'synthetic_isolation':(['offline_reader','synthetic_real_provenance_separated'],False),
 'prompts':(['focused_follow_up_prompts'],[]),
 'action_evidence':(['next_actions',1,'completion_evidence'],''),
 'ranking':(['ranking_basis'],'capability_or_risk'),
}
for name,(keys,value) in CASES.items():
    def test(self,keys=keys,value=value):self.rejects(keys,value)
    setattr(HistoricalCatalogTests,'test_reject_'+name,test)

if __name__=='__main__':unittest.main()
