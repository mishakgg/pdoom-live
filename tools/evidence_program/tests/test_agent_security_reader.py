import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from read_agentdojo_metadata import (normalize_run, interpret_security, digest, git_blob,
    MAX_BYTES, MAX_MESSAGES, MAX_TOOL_CALLS, SYNTHETIC_PREDICATE)
F = Path(__file__).parent / 'fixtures/agent-security-incidents'


def materialize(row, **changes):
    raw = (json.dumps(row, separators=(',', ':')) + '\n').encode()
    manifest = json.loads((F / 'manifest.synthetic.json').read_text())
    manifest.update(sha256=digest(raw), git_blob_sha=git_blob(raw))
    if isinstance(row, dict):
        manifest['source_path'] = '/'.join(['runs',str(row.get('pipeline_name')),str(row.get('suite_name')),
            str(row.get('user_task_id')),str(row.get('injection_task_id') or 'none'),str(row.get('attack_type') or 'none')+'.json'])
    manifest.update(changes)
    return raw, manifest


class AgentMetadataTests(unittest.TestCase):
    def setUp(self):
        self.row = json.loads((F/'clean.synthetic.json').read_text())

    def read(self, **changes):
        return normalize_run(*materialize(self.row, **changes))

    def test_synthetic_fixture(self):
        raw=(F/'clean.synthetic.json').read_bytes();m=json.loads((F/'manifest.synthetic.json').read_text())
        out=normalize_run(raw,m)
        self.assertEqual(out['duration_seconds'],'4.5')
        self.assertEqual(out['assistant_origin_tool_calls'],2)
        self.assertEqual(out['security_interpretation'],{'status':'not_applicable_clean','attacker_goal_success':None})

    def test_clean_security_false_stays_not_applicable(self):
        self.row['security']=False
        self.assertEqual(self.read()['security_interpretation']['status'],'not_applicable_clean')

    def test_target_success_is_attacker_goal(self):
        self.row.update(injection_task_id='injection_task_0',attack_type='synthetic_target')
        out=self.read(semantics=SYNTHETIC_PREDICATE)
        self.assertTrue(out['security_interpretation']['attacker_goal_success'])

    def test_target_false_is_goal_false_not_measured_safety(self):
        self.row.update(injection_task_id='injection_task_0',attack_type='synthetic_target',security=False)
        self.assertFalse(self.read(semantics=SYNTHETIC_PREDICATE)['security_interpretation']['attacker_goal_success'])

    def test_historical_target_stays_unknown(self):
        self.row.update(injection_task_id='injection_task_0',attack_type='important_instructions')
        out=self.read(source_kind='agentdojo_archive')
        self.assertEqual(out['security_interpretation']['status'],'unverified_historical_predicate')
        self.assertIsNone(out['security_interpretation']['attacker_goal_success'])

    def test_archive_cannot_select_synthetic_semantics(self):
        with self.assertRaises(ValueError):self.read(source_kind='agentdojo_archive',semantics=SYNTHETIC_PREDICATE)

    def test_dos_is_not_target_goal(self):
        self.row.update(injection_task_id='injection_task_0',attack_type='dos')
        self.assertEqual(self.read(semantics=SYNTHETIC_PREDICATE)['security_interpretation']['status'],'dos_nonutility_predicate_not_target_goal')

    def test_error_default_flag_not_observation(self):
        self.row.update(injection_task_id='injection_task_0',attack_type='synthetic_target',error='Private error marker',utility=False,security=True)
        out=self.read(semantics=SYNTHETIC_PREDICATE)
        self.assertEqual(out['security_interpretation']['status'],'error_flag_not_observed_outcome')
        self.assertEqual(out['utility_observation_status'],'error_flag_not_observed_outcome')
        self.assertNotIn('Private error marker',json.dumps(out))

    def test_empty_error_still_present(self):
        self.row['error']=''
        self.assertTrue(self.read()['error_present'])

    def test_echoed_tool_calls_ignored(self):
        self.row['messages'].extend([copy.deepcopy(self.row['messages'][2])] * 5)
        self.assertEqual(self.read()['assistant_origin_tool_calls'],2)

    def test_user_roles_do_not_imply_assistance(self):
        self.assertIsNone(self.read()['human_intervention'])

    def test_simulated_amount_not_cost(self):
        out=self.read()
        for k in ['actual_inference_cost','spending_cap','token_cap']:self.assertIsNone(out[k])

    def test_unknown_runtime_and_dates_remain_null(self):
        out=self.read()
        for k in ['historical_runtime_version','evaluation_timestamp','human_baseline_seconds']:self.assertIsNone(out[k])

    def test_payload_exclusion(self):
        self.row.update(injection_task_id='injection_task_0',attack_type='synthetic_target',injections={'synthetic_slot':'PRIVATE_PAYLOAD_MARKER'})
        self.row['messages'][0]['content']='PRIVATE_MESSAGE_MARKER'
        out=json.dumps(self.read())
        for text in ['PRIVATE_PAYLOAD_MARKER','PRIVATE_MESSAGE_MARKER','synthetic_amount','synthetic_tool','synthetic-call-1']:
            self.assertNotIn(text,out)

    def test_repeated_bytes_idempotent(self):
        self.assertEqual(self.read(),self.read())

    def test_retrieval_time_not_identity(self):
        a=self.read();b=self.read(retrieved_at='2026-10-09T06:10:00Z')
        self.assertEqual(a['observation_version_id'],b['observation_version_id'])

    def test_archive_revision_not_measurement_identity(self):
        a=self.read();b=self.read(archive_commit='1'*40)
        self.assertEqual(a['observation_version_id'],b['observation_version_id'])

    def test_changed_bytes_linked_version(self):
        a=self.read();self.row['duration']=5.0;b=self.read(previous_sha256=a['source_sha256'])
        self.assertNotEqual(a['observation_version_id'],b['observation_version_id'])
        self.assertEqual(a['source_key'],b['source_key'])
        self.assertEqual(b['previous_sha256'],a['source_sha256'])

    def test_identical_hash_cannot_supersede_itself(self):
        with self.assertRaises(ValueError):self.read(previous_sha256=self.read()['source_sha256'])

    def test_source_and_synthetic_namespaces_separate(self):
        self.assertNotEqual(self.read()['observation_version_id'],self.read(source_kind='agentdojo_archive')['observation_version_id'])

    def test_input_unmodified(self):
        before=copy.deepcopy(self.row);self.read();self.assertEqual(self.row,before)

    def test_no_source_url_for_synthetic(self):
        self.assertIsNone(self.read()['source_url'])

    def test_exact_source_url_construction(self):
        out=self.read(source_kind='agentdojo_archive')
        self.assertTrue(out['source_url'].startswith('https://github.com/ethz-spylab/agentdojo/blob/'+'0'*40+'/runs/'))

    def test_bounded_oversize(self):
        raw,m=materialize(self.row)
        with self.assertRaises(ValueError):normalize_run(b' '*(MAX_BYTES+1),m)

    def test_duplicate_keys(self):
        raw,m=materialize(self.row);raw=raw.replace(b'"security":true',b'"security":true,"security":false')
        m.update(sha256=digest(raw),git_blob_sha=git_blob(raw))
        with self.assertRaises(ValueError):normalize_run(raw,m)

    def test_bad_utf8(self):
        raw=b'\xff';m=materialize(self.row)[1];m.update(sha256=digest(raw),git_blob_sha=git_blob(raw))
        with self.assertRaises(ValueError):normalize_run(raw,m)

    def test_nonfinite_constant(self):
        raw,m=materialize(self.row);raw=raw.replace(b'4.5',b'NaN');m.update(sha256=digest(raw),git_blob_sha=git_blob(raw))
        with self.assertRaises(ValueError):normalize_run(raw,m)

    def test_depth_bound(self):
        value='placeholder'
        for _ in range(30):value=[value]
        self.row['messages'][0]['content']=value
        with self.assertRaises(ValueError):self.read()

    def test_message_bound(self):
        self.row['messages']=[{'role':'user','content':''}]*(MAX_MESSAGES+1)
        with self.assertRaises(ValueError):self.read()

    def test_tool_call_bound(self):
        self.row['messages']=[{'role':'assistant','tool_calls':[{'function':'synthetic_tool','args':{},'id':None}]*(MAX_TOOL_CALLS+1)}]
        with self.assertRaises(ValueError):self.read()

    def test_no_network_or_process_modules(self):
        import read_agentdojo_metadata as module
        source=Path(module.__file__).read_text()
        for name in ['import urllib','import requests','import socket','import subprocess','import os','eval(','exec(']:self.assertNotIn(name,source)


def invalid_case(field,value):
    def test(self):
        self.row[field]=value
        with self.assertRaises(ValueError):self.read()
    return test

for i,(field,value) in enumerate([
 ('duration',True),('duration',-1),('duration',86401),('duration','4.5'),
 ('utility',1),('security','true'),('error',{}),('injections',[]),
 ('messages',{}),('pipeline_name','other'),('suite_name','other'),
 ('user_task_id','user_task_3'),('injection_task_id','../../x'),('attack_type','bad name'),('attack_type','Jane_Doe'),('attack_type','account_1234'),('attack_type',[]),
 ('unexpected',1),('messages',[{'role':'other'}]),('messages',[{'role':'assistant','tool_calls':'x'}]),
 ('messages',[{'role':'assistant','tool_calls':[1]}]),('messages',[{'role':'tool','content':3}]),
 ('messages',[{'role':'user','unexpected':1}]),('injections',{'a':3}),('pipeline_name',[]),('user_task_id',[]),('messages',[{'role':[]}]),
]):
 setattr(AgentMetadataTests,'test_invalid_field_%02d'%i,invalid_case(field,value))


def invalid_manifest(field,value):
    def test(self):
        with self.assertRaises(ValueError):self.read(**{field:value})
    return test

for i,(field,value) in enumerate([
 ('source_kind','remote'),('archive_commit','main'),('source_path','../../file'),
 ('sha256','0'*64),('git_blob_sha','0'*40),('retrieved_at','2026-10-08'),
 ('retrieved_at','2026-13-08T06:10:00Z'),('previous_sha256','bad'),
 ('semantics','target_goal_verified'),('extra','payload'),
]):setattr(AgentMetadataTests,'test_invalid_manifest_%02d'%i,invalid_manifest(field,value))

if __name__=='__main__':unittest.main()
