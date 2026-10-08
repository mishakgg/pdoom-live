from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import read_leap_aggregates as reader
FIXTURE = HERE/'fixtures/forecast-surveys'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.raw = (FIXTURE/'leap-wave12-catastrophe2050.json').read_bytes()
        self.data = json.loads(self.raw)
        self.manifest = json.loads((FIXTURE/'manifest.json').read_bytes())

    def normalize(self, data=None, manifest=None):
        raw = self.raw if data is None else encoded(data)
        m = copy.deepcopy(self.manifest if manifest is None else manifest)
        m['derivative_sha256'] = hashlib.sha256(raw).hexdigest()
        return reader.normalize_ledger(raw, m)

    def test_four_exact_published_summaries(self):
        out = reader.read_fixture(FIXTURE)
        rows = out['records']
        self.assertEqual(len(rows),4)
        self.assertEqual([(r['group_label'],r['median_percent'],r['q25_percent'],r['q75_percent'],r['reported_n']) for r in rows],
            [('Expert','2','0.9','7',157),('Public','5','2','13',540),('Superforecaster','1.6','0.3','3.3',49),('AI Risk Expert','5.2','2','19',132)])
        self.assertEqual([r['probability_median'] for r in rows],['0.02','0.05','0.016','0.052'])
        self.assertEqual([r['probability_q25'] for r in rows],['0.009','0.02','0.003','0.02'])
        self.assertEqual([r['probability_q75'] for r in rows],['0.07','0.13','0.033','0.19'])

    def test_n_not_wave_total(self):
        d=copy.deepcopy(self.data);d['records'][1]['reported_n']=None;d['records'][1]['reported_n_missing_reason']='not_reported'
        self.assertIsNone(self.normalize(d)['records'][1]['reported_n'])

    def test_missing_n_different_valid_reasons(self):
        for reason in ('not_reported','not_retrieved','definition_unclear'):
            d=copy.deepcopy(self.data);d['records'][0].update(reported_n=None,reported_n_missing_reason=reason)
            self.assertEqual(self.normalize(d)['records'][0]['reported_n_missing_reason'],reason)

    def test_zero_percent_allowed(self):
        d=copy.deepcopy(self.data);d['records'][0].update(q25_percent='0',median_percent='0',q75_percent='0')
        self.assertEqual(self.normalize(d)['records'][0]['probability_median'],'0')

    def test_exact_long_decimal(self):
        value='1.2345678901234567890123456789'
        self.assertEqual(reader.percent(value)[1],'0.012345678901234567890123456789')

    def test_source_precision_retained(self):
        d=copy.deepcopy(self.data);d['records'][0]['median_percent']='2.00'
        r=self.normalize(d)['records'][0]
        self.assertEqual(r['median_percent'],'2.00');self.assertEqual(r['probability_median'],'0.02')

    def test_boundary_hundred(self):
        self.assertEqual(reader.percent('100')[1],'1')

    def test_idempotence(self):self.assertEqual(self.normalize(),self.normalize())

    def test_source_revision_keeps_observation_identity(self):
        a=self.normalize();m=copy.deepcopy(self.manifest);m['original_page_sha256']='a'*64;b=self.normalize(manifest=m)
        self.assertEqual([r['observation_id']for r in a['records']],[r['observation_id']for r in b['records']])
        self.assertNotEqual([r['result_version_id']for r in a['records']],[r['result_version_id']for r in b['records']])
        self.assertEqual(a['records'][0]['definition_version'],b['records'][0]['definition_version'])

    def test_derivative_correction_keeps_observation_identity(self):
        d=copy.deepcopy(self.data);d['records'][0]['median_percent']='2.1';a=self.normalize();b=self.normalize(d)
        self.assertEqual(a['records'][0]['observation_id'],b['records'][0]['observation_id'])
        self.assertNotEqual(a['records'][0]['result_version_id'],b['records'][0]['result_version_id'])

    def test_new_retrieval_is_not_new_source_revision(self):
        a=self.normalize();m=copy.deepcopy(self.manifest);m['retrieved_at']='2026-10-09T00:00:00Z';b=self.normalize(manifest=m)
        self.assertEqual(a['records'][0]['result_version_id'],b['records'][0]['result_version_id'])
        self.assertNotEqual(a['records'][0]['provenance']['retrieved_at'],b['records'][0]['provenance']['retrieved_at'])

    def test_definition_change_requires_review_and_changes_definition_hash(self):
        d=copy.deepcopy(self.data);d['instrument']['event_definition']+=' Changed.'
        self.assertNotEqual(reader.definition_version(d['instrument']),reader.definition_version(self.data['instrument']))
        with self.assertRaisesRegex(ValueError,'Unreviewed instrument'):self.normalize(d)

    def test_provenance_roundtrip(self):
        r=self.normalize()['records'][0]
        self.assertEqual(r['provenance'],self.manifest)
        self.assertEqual(r['dates'],self.data['dates'])
        self.assertEqual(r['question'],self.data['instrument'])
        self.assertNotEqual(r['provenance']['original_page_sha256'],r['provenance']['derivative_sha256'])

    def test_return_is_unaliased(self):
        m=copy.deepcopy(self.manifest);out=self.normalize(manifest=m);out['records'][0]['provenance']['source_url']='changed'
        self.assertEqual(out['records'][1]['provenance']['source_url'],reader.SOURCE_URL)
        self.assertEqual(m['source_url'],reader.SOURCE_URL)

    def test_interpretation_boundary(self):
        out=self.normalize();serialized=json.dumps(out)
        for key in ('pdoom','pooled_forecast','total_participants','confidence_interval','individual_probability'):
            self.assertNotIn('"'+key+'"',serialized)
        self.assertFalse(out['collector_enabled']);self.assertFalse(out['canonical_import']);self.assertFalse(out['source_extraction_implemented'])

    def test_discrepancy_preserved(self):
        c=self.normalize()['wave_counts'];self.assertEqual(c['reported_expert_overall_n'],157);self.assertEqual(c['derived_expert_category_sum'],149)
        self.assertEqual(c['discrepancy_status'],'unresolved_source_discrepancy')

    def test_unknown_publication_date_has_reason(self):
        d=copy.deepcopy(self.data);d['dates'].update(publication_date=None,publication_date_status='not_reported')
        self.assertIsNone(self.normalize(d)['records'][0]['dates']['publication_date'])

    def test_hash_mismatch(self):
        with self.assertRaisesRegex(ValueError,'Derivative hash mismatch'):reader.normalize_ledger(self.raw+b' ',self.manifest)

    def test_manifest_duplicate_key(self):
        with self.assertRaises(ValueError):reader.strict_json(b'{"a":1,"a":2}',100)

    def test_json_float_not_coerced(self):
        with self.assertRaises(ValueError):reader.strict_json(b'{"n":2.0}',100)

    def test_json_nonfinite_rejected(self):
        for token in (b'NaN',b'Infinity',b'-Infinity'):
            with self.assertRaises(ValueError):reader.strict_json(b'{"v":'+token+b'}',100)

    def test_json_integer_bound(self):
        with self.assertRaises(ValueError):reader.strict_json(b'12345678901234567890',100)

    def test_json_depth_bound(self):
        with self.assertRaises(ValueError):reader.strict_json(b'['*20+b'0'+b']'*20,100)

    def test_json_node_bound(self):
        with self.assertRaises(ValueError):reader.strict_json(encoded([0]*1001),10000)

    def test_json_string_bound(self):
        with self.assertRaises(ValueError):reader.strict_json(encoded('x'*16001),20000)

    def test_input_byte_bound(self):
        with self.assertRaises(ValueError):reader.normalize_ledger(b' '*(reader.MAX_BYTES+1),self.manifest)

    def test_unpaired_surrogate_rejected(self):
        with self.assertRaises(ValueError):reader.strict_json(b'"\\ud800"',100)

    def test_surrogate_key_rejected(self):
        with self.assertRaises(ValueError):reader.strict_json(b'{"\\ud800":1}',100)

    def test_invalid_utf8(self):
        with self.assertRaises(ValueError):reader.strict_json(b'\xff',100)

    def test_invalid_json(self):
        with self.assertRaises(ValueError):reader.strict_json(b'{',100)

    def test_empty_bytes(self):
        with self.assertRaises(ValueError):reader.strict_json(b'',100)

    def test_file_names_and_symlinks_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'manifest.json').write_bytes(encoded(self.manifest));(p/'leap-wave12-catastrophe2050.json').symlink_to(FIXTURE/'leap-wave12-catastrophe2050.json')
            with self.assertRaises(ValueError):reader.read_fixture(p)

    def test_oversize_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'manifest.json').write_bytes(b' '*(reader.MAX_MANIFEST_BYTES+1))
            with self.assertRaises(ValueError):reader.read_fixture(p)

    def test_ancestor_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'ancestor').symlink_to(FIXTURE.parent,target_is_directory=True)
            with self.assertRaises(ValueError):reader.read_fixture(p/'ancestor'/FIXTURE.name)

    def test_parent_traversal_rejected(self):
        with self.assertRaises(ValueError):reader.read_fixture(FIXTURE/'..'/FIXTURE.name)

    def test_fifo_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);os.mkfifo(p/'manifest.json')
            result=subprocess.run([sys.executable,str(HERE.parent/'read_leap_aggregates.py'),str(p)],capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode,1);self.assertNotIn('Traceback',result.stderr)

    def test_cli_success(self):
        result=subprocess.run([sys.executable,str(HERE.parent/'read_leap_aggregates.py'),str(FIXTURE)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(len(json.loads(result.stdout)['records']),4)

    def test_cli_missing_directory(self):
        result=subprocess.run([sys.executable,str(HERE.parent/'read_leap_aggregates.py'),str(FIXTURE/'absent')],capture_output=True,text=True)
        self.assertEqual(result.returncode,1);self.assertNotIn('Traceback',result.stderr)


def decimal_case(name,value):
    def test(self):
        with self.assertRaises(ValueError):reader.percent(value)
    setattr(ReaderTests,'test_invalid_decimal_'+name,test)


for name,value in {'bool':True,'integer':2,'float':0.1,'none':None,'negative':'-1','plus':'+1','exponent':'1e-2','nan':'NaN','infinity':'Infinity','over100':'100.00000000000000000000000001','leadingzero':'01','leadingdot':'.1','trailingdot':'1.','whitespace':' 1','comma':'1,2','unicode':'１','overprecision':'0.'+'1'*32,'empty':''}.items():
    decimal_case(name,value)


def mutation(name,fn,manifest=False):
    def test(self):
        d=copy.deepcopy(self.manifest if manifest else self.data);fn(d)
        with self.assertRaises(ValueError):
            self.normalize(manifest=d) if manifest else self.normalize(d)
    setattr(ReaderTests,'test_reject_'+name,test)


mutation('other_wave',lambda d:d.update(wave=11))
mutation('bool_wave',lambda d:d.update(wave=True))
mutation('other_study',lambda d:d.update(study='XPT'))
mutation('extra_root',lambda d:d.update(pdoom='0.02'))
mutation('missing_root',lambda d:d.pop('dates'))
mutation('wrong_condition',lambda d:d['instrument'].update(condition_key='status_quo'))
mutation('wrong_question',lambda d:d['instrument'].update(question_id='ai-risk'))
mutation('wrong_horizon',lambda d:d['instrument'].update(horizon_year=2100))
mutation('horizon_bool',lambda d:d['instrument'].update(horizon_year=True))
mutation('changed_wording',lambda d:d['instrument'].update(question_text='What if policy stays unchanged?'))
mutation('missing_background',lambda d:d['instrument'].update(shared_background=''))
mutation('missing_causation',lambda d:d['instrument'].pop('causation_criteria'))
mutation('few_records',lambda d:d['records'].pop())
mutation('many_records',lambda d:d['records'].append(d['records'][0]))
mutation('renamed_group',lambda d:d['records'][0].update(group_label='Experts'))
mutation('duplicate_group',lambda d:d['records'][1].update(group_label='Expert'))
mutation('group_reordered',lambda d:d['records'].reverse())
mutation('bool_n',lambda d:d['records'][0].update(reported_n=True))
mutation('decimal_n',lambda d:d['records'][0].update(reported_n='157'))
mutation('zero_n',lambda d:d['records'][0].update(reported_n=0))
mutation('negative_n',lambda d:d['records'][0].update(reported_n=-1))
mutation('large_n',lambda d:d['records'][0].update(reported_n=1000001))
mutation('missing_n_reason',lambda d:d['records'][0].update(reported_n=None))
mutation('reason_with_n',lambda d:d['records'][0].update(reported_n_missing_reason='not_reported'))
mutation('reverse_quantiles',lambda d:d['records'][0].update(q25_percent='9'))
mutation('median_above_q75',lambda d:d['records'][0].update(median_percent='8'))
mutation('confidence_interval',lambda d:d['interpretation'].update(interval_type='confidence_interval'))
mutation('pooled_overlap',lambda d:d['interpretation'].update(group_overlap='disjoint'))
mutation('assumed_weights',lambda d:d['interpretation'].update(weighting_provenance='unweighted'))
mutation('replace_cell_n',lambda d:d['interpretation'].update(reported_n_role='wave_total'))
mutation('no_locator',lambda d:d['records'][0].update(source_locator=''))
mutation('extra_individual',lambda d:d['records'][0].update(individual_id='person'))
mutation('repair_discrepancy',lambda d:d['wave_counts'].update(reported_expert_overall_n=149))
mutation('discrepancy_bool',lambda d:d['wave_counts'].update(derived_expert_category_sum=True))
mutation('hide_discrepancy',lambda d:d['wave_counts'].update(discrepancy_status='resolved'))
mutation('bad_date',lambda d:d['dates'].update(fieldwork_start='2026-02-30'))
mutation('reversed_fieldwork',lambda d:d['dates'].update(fieldwork_start='2026-09-30'))
mutation('publication_before_fieldwork',lambda d:d['dates'].update(publication_date='2025-10-05'))
mutation('missing_publication_reason',lambda d:d['dates'].update(publication_date=None,publication_date_status='reported'))
mutation('unknown_export_timezone_invented',lambda d:d['dates'].update(aggregate_generated_timezone='America/New_York'))
mutation('export_wrong_offset',lambda d:d['dates'].update(aggregate_generated_at='2026-09-19T03:32:00+05:00'))
mutation('export_unreported_seconds',lambda d:d['dates'].update(aggregate_generated_at='2026-09-19T03:32:59Z'))
mutation('export_unreported_fraction',lambda d:d['dates'].update(aggregate_generated_at='2026-09-19T03:32:00.123Z'))
mutation('empty_export',lambda d:d['dates'].update(aggregate_generated_at_source=''))
mutation('wrong_url',lambda m:m.update(source_url='https://example.com/'),True)
mutation('rights_inheritance',lambda m:m.update(license_identifier='MIT'),True)
mutation('missing_attribution',lambda m:m.update(attribution=''),True)
mutation('missing_change_notice',lambda m:m.update(transformation_notice=''),True)
mutation('bad_original_hash',lambda m:m.update(original_page_sha256='unknown'),True)
mutation('duplicate_hashes',lambda m:m.update(original_page_sha256=m['derivative_sha256']),True)
mutation('fake_hash_basis',lambda m:m.update(original_hash_basis='curated_text'),True)
mutation('bool_original_bytes',lambda m:m.update(original_page_bytes=True),True)
mutation('excess_original_bytes',lambda m:m.update(original_page_bytes=2*1024*1024+1),True)
mutation('missing_retrieval_timezone',lambda m:m.update(retrieved_at='2026-10-08T07:31:00'),True)
mutation('retrieval_before_fieldwork',lambda m:m.update(retrieved_at='2020-10-08T07:31:00Z'),True)

if __name__=='__main__':unittest.main()
