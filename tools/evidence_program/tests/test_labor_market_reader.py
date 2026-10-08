from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from read_eurostat_ict_training import normalize_slice, read_fixture, strict_json, MAX_BYTES, DIMENSIONS, SOURCE_URL
F = HERE / 'fixtures/labor-market'
RAW = (F/'de-ict-training.json').read_bytes()
DATA = json.loads(RAW)
MANIFEST = json.loads((F/'manifest.json').read_text())


def run(data=None, raw=None, manifest=None):
    payload = raw if raw is not None else json.dumps(DATA if data is None else data, separators=(',',':')).encode()
    m = dict(MANIFEST, sha256=hashlib.sha256(payload).hexdigest()) if manifest is None else manifest
    return normalize_slice(payload,m)


class ReaderTests(unittest.TestCase):
    def test_exact_source_acceptance(self):
        out=read_fixture(F)
        self.assertEqual([r['value'] for r in out['records']], [23.72,31.2,29.79,29.07,27.79,29.89,31.61,23.76,27.32,26.41])
        self.assertEqual(out['source_sha256'], MANIFEST['sha256'])
        self.assertEqual(len(out['records']),10)

    def test_missing_years(self):
        out=run();self.assertEqual(out['missing_survey_years'],[2013,2021,2023])
        self.assertFalse(any(r['survey_year'] in [2013,2021,2023] for r in out['records']))

    def test_reference_years(self):
        rs=run()['records'];self.assertEqual(rs[-1]['training_reference_year'],2023)
        self.assertTrue(all(r['training_reference_year'] is None for r in rs[:-1]))
        self.assertTrue(all(r['reference_year_source_url'] is None for r in rs[:-1]))

    def test_three_clocks(self):
        out=run();self.assertEqual(out['upstream_updated_at'],'2026-06-15T11:00:00+0200')
        self.assertEqual(out['retrieved_at'],MANIFEST['retrieved_at'])
        self.assertEqual(out['records'][-1]['survey_year'],2024)

    def test_status_absent(self):
        out=run();self.assertFalse(out['source_status_member_present'])
        self.assertTrue(all(r['status'] is None and r['status_state']=='absent_member' for r in out['records']))

    def test_sparse_missing_and_zero(self):
        d=copy.deepcopy(DATA);del d['value']['0'];d['value']['1']=None;d['value']['2']=0
        rs=run(d)['records'];self.assertEqual([(r['value'],r['value_state']) for r in rs[:3]],[(None,'absent_sparse_cell'),(None,'explicit_null'),(0,'observed')])

    def test_flags_preserved(self):
        d=copy.deepcopy(DATA);d['status']={'0':'b','1':'u','2':'c','3':'p e','4':None};d['value']['2']=None
        rs=run(d)['records'];self.assertEqual([r['status'] for r in rs[:5]],['b','u','c','p e',None])
        self.assertEqual(rs[4]['status_state'],'explicit_null');self.assertEqual(rs[5]['status_state'],'absent_cell')

    def test_dense_values_and_status(self):
        d=copy.deepcopy(DATA);d['value']=list(d['value'].values());d['status']=['b']+[None]*9
        rs=run(d)['records'];self.assertEqual(rs[-1]['value'],26.41);self.assertEqual(rs[0]['status'],'b')

    def test_reordered_dimensions(self):
        d=copy.deepcopy(DATA);d['id']=list(reversed(d['id']));d['size']=list(reversed(d['size']))
        rs=run(d)['records'];self.assertEqual([(r['survey_year'],r['value']) for r in rs],[(r['survey_year'],r['value']) for r in run()['records']])
        self.assertEqual(rs[0]['observation_key'],run()['records'][0]['observation_key'])

    def test_category_index_not_object_insertion(self):
        d=copy.deepcopy(DATA);c=d['dimension']['time']['category'];years=list(c['index']);c['index']={y:9-i for i,y in enumerate(years)}
        d['value']={str(9-int(k)):v for k,v in d['value'].items()}
        self.assertEqual([r['value'] for r in run(d)['records']],[r['value'] for r in run()['records']])

    def test_array_category_indices(self):
        d=copy.deepcopy(DATA)
        for dim in d['dimension'].values():dim['category']['index']=list(dim['category']['index'])
        self.assertEqual([r['value'] for r in run(d)['records']],[r['value'] for r in run()['records']])

    def test_revision_identity(self):
        a=run();d=copy.deepcopy(DATA);d['value']['9']=26.42;b=run(d)
        self.assertEqual(a['records'][-1]['observation_key'],b['records'][-1]['observation_key'])
        self.assertNotEqual(a['records'][-1]['snapshot_key'],b['records'][-1]['snapshot_key'])

    def test_retrieval_is_not_revision(self):
        m=dict(MANIFEST,retrieved_at='2026-10-09T00:00:00Z')
        a=normalize_slice(RAW,MANIFEST);b=normalize_slice(RAW,m)
        self.assertEqual(a['records'],b['records'])

    def test_labels_extensions_flags_retained(self):
        out=run();self.assertEqual(out['source_extension'],DATA['extension'])
        self.assertEqual(out['source_dimension_labels']['geo']['category_labels'],{'DE':'Germany'})

    def test_no_imputed_uncertainty_or_ai_exposure(self):
        out=run();self.assertTrue(all(r['uncertainty'] is None and r['ai_specific'] is False for r in out['records']))
        self.assertNotIn('pdoom',out);self.assertNotIn('exposure_score',out)
        self.assertFalse(out['collector_enabled']);self.assertEqual(out['operational_admission'],'not_admitted')

    def test_compatible_subset_keeps_missingness(self):
        d=copy.deepcopy(DATA);c=d['dimension']['time']['category'];c['index']={'2024':0};c['label']={'2024':'2024'};d['size'][-1]=1;d['value']={'0':26.41}
        out=run(d);self.assertEqual(len(out['records']),1);self.assertEqual(len(out['missing_survey_years']),12)

    def test_path_and_size_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'de-ict-training.json').write_bytes(b'x'*(MAX_BYTES+1));(p/'manifest.json').write_text('{}')
            with self.assertRaises(ValueError):read_fixture(p)
            (p/'de-ict-training.json').unlink();(p/'de-ict-training.json').symlink_to(F/'de-ict-training.json')
            with self.assertRaises(ValueError):read_fixture(p)
            (p/'alias').symlink_to(F,target_is_directory=True)
            with self.assertRaises(ValueError):read_fixture(p/'alias')

    def test_hash_rejected(self):
        with self.assertRaises(ValueError):normalize_slice(RAW,dict(MANIFEST,sha256='0'*64))

    def test_exact_decimal_guard(self):
        for token in [b'100.00000000000000001', b'-1e-999', b'1e-999', b'26.4100000000000000000001', b'1e99999999999999999999999999999999999999999', b'0e99999999999999999999999999999999999999999']:
            raw = RAW.replace(b'23.72', token, 1)
            with self.subTest(token=token), self.assertRaises(ValueError):run(raw=raw)
        self.assertEqual(run(raw=RAW.replace(b'23.72', b'23.7200', 1))['records'][0]['value'],23.72)

    def test_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):run(raw=b'{"a":1,"a":2}')

    def test_invalid_json(self):
        for raw in [b'',b'\xff',b'{',b'{"x":NaN}',b'{"x":1e999}',b'['*1000+b']'*1000]:
            with self.subTest(raw=raw[:20]),self.assertRaises(ValueError):run(raw=raw)

    def test_depth_node_bounds(self):
        for raw in [json.dumps([0]*4001).encode(), b'['*17+b'0'+b']'*17]:
            with self.assertRaises(ValueError):strict_json(raw,MAX_BYTES)

    def test_manifest_schema_and_routes(self):
        for key,value in [('source_url',SOURCE_URL+'&geo=FR'),('retrieved_at','2026-10-08'),('sha256',None),('extra',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError):normalize_slice(RAW,dict(MANIFEST,**{key:value}))


def bad(name, mutate):
    def test(self):
        d=copy.deepcopy(DATA);mutate(d)
        with self.assertRaises(ValueError):run(d)
    setattr(ReaderTests,'test_reject_'+name,test)

bad('wrong_source',lambda d:d.update(source='OTHER'))
bad('wrong_class',lambda d:d.update(**{'class':'collection'}))
bad('wrong_version',lambda d:d.update(version='1.0'))
bad('root_extra',lambda d:d.update(records=[]))
bad('missing_value',lambda d:d.pop('value'))
bad('invalid_updated',lambda d:d.update(updated='2026-06-15'))
bad('label_object',lambda d:d.update(label={}))
bad('duplicate_dimension',lambda d:d['id'].__setitem__(0,'geo'))
bad('missing_dimension',lambda d:d['dimension'].pop('unit'))
bad('unknown_dimension',lambda d:d['dimension'].update(person={}))
bad('zero_size',lambda d:d['size'].__setitem__(0,0))
bad('bool_size',lambda d:d['size'].__setitem__(0,True))
bad('oversize_dimension',lambda d:d['size'].__setitem__(-1,14))
bad('size_mismatch',lambda d:d['size'].__setitem__(-1,9))
bad('extra_population',lambda d:d['size'].__setitem__(0,2))
bad('duplicate_category_index',lambda d:d['dimension']['time']['category']['index'].__setitem__('2014',0))
bad('boolean_category_index',lambda d:d['dimension']['geo']['category']['index'].__setitem__('DE',False))
bad('invalid_category_index',lambda d:d['dimension']['geo']['category']['index'].__setitem__('DE',-1))
bad('wrong_country',lambda d:d['dimension']['geo']['category'].update(index={'FR':0},label={'FR':'France'}))
bad('wrong_unit',lambda d:d['dimension']['unit']['category'].update(index={'NR':0},label={'NR':'Count'}))
bad('wrong_size_class',lambda d:d['dimension']['size_emp']['category'].update(index={'LT10':0},label={'LT10':'Micro'}))
bad('wrong_indicator',lambda d:d['dimension']['indic_is']['category'].update(index={'AI':0},label={'AI':'AI'}))
bad('unknown_year',lambda d:d['dimension']['time']['category']['index'].__setitem__('2025',10))
bad('label_mismatch',lambda d:d['dimension']['time']['category']['label'].pop('2012'))
bad('sparse_negative',lambda d:d['value'].update({'-1':1}))
bad('sparse_leading_zero',lambda d:d['value'].update({'00':1}))
bad('sparse_out_of_range',lambda d:d['value'].update({'10':1}))
bad('percentage_over_100',lambda d:d['value'].update({'0':101}))
bad('percentage_below_zero',lambda d:d['value'].update({'0':-1}))
bad('percentage_bool',lambda d:d['value'].update({'0':True}))
bad('percentage_string',lambda d:d['value'].update({'0':'23.72'}))
bad('dense_wrong_length',lambda d:d.update(value=[1]))
bad('status_boolean',lambda d:d.update(status={'0':False}))
bad('status_control',lambda d:d.update(status={'0':'b\n'}))
bad('status_index',lambda d:d.update(status={'10':'b'}))
bad('status_type',lambda d:d.update(status='b'))
bad('extension_table',lambda d:d['extension'].update(id='ISOC_EB_AI'))
bad('extension_agency',lambda d:d['extension'].update(agencyId='OTHER'))
bad('extension_version',lambda d:d['extension'].update(version='2.0'))
bad('structure_version',lambda d:d['extension']['datastructure'].update(version='44.0'))
bad('extension_extra',lambda d:d['extension'].update(person=[]))
bad('no_data_index',lambda d:d['extension']['positions-with-no-data'].update(time=[10]))
bad('huge_integer',lambda d:d['value'].update({'0':10**100}))
bad('annotation_type',lambda d:d['extension'].update(annotation='text'))

if __name__=='__main__':unittest.main()
