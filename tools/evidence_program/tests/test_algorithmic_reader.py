"""Bounded licensed AlgoPerf fixture and adversarial synthetic regressions."""
from copy import deepcopy
import csv
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import read_algoperf_trial as r


class TrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = r.read_trial()
        cls.raw = (r.FIXTURE / 'eval_measurements.csv').read_bytes()
        cls.rows = r._parse_csv(cls.raw)

    def csv(self, rows=None, header=None):
        out = io.StringIO(newline='')
        w = csv.writer(out)
        keys = list(header or r.HEADER)
        w.writerow(keys)
        for row in rows if rows is not None else self.rows[:2]:
            w.writerow([row.get(k, '') for k in keys])
        return out.getvalue().encode()

    def bad_cell(self, key, value):
        rows = deepcopy(self.rows[:2])
        rows[0][key] = value
        with self.assertRaises(r.ReviewInputError):
            r._parse_csv(self.csv(rows))

    def test_observation_counts_not_replicates(self):
        self.assertEqual((74, 1), (self.result['observation_count'], self.result['trial_count']))

    def test_pinned_bytes(self):
        import hashlib
        for name, (size, digest) in r.PINS.items():
            raw = (r.FIXTURE / name).read_bytes()
            self.assertEqual((size, digest), (len(raw), hashlib.sha256(raw).hexdigest()))

    def test_exact_crossing(self):
        d = self.result['derived_result']
        self.assertEqual(73, d['row_index'])
        self.assertEqual(22353, d['observation']['global_step'])
        self.assertEqual('0.7237818797921356', d['observation']['validation/ssim'])
        self.assertEqual('5945.58318734169', d['observation']['accumulated_submission_time'])

    def test_preceding_below(self):
        p = self.result['derived_result']['preceding_observation']
        self.assertEqual(22044, p['global_step'])
        self.assertEqual('0.7227431486749085', p['validation/ssim'])
        self.assertLess(Decimal(p['validation/ssim']), Decimal('0.723653'))

    def test_clocks_distinct_and_unforced_sum(self):
        row = self.result['derived_result']['observation']
        self.assertEqual('681.8499503135681', row['accumulated_eval_time'])
        self.assertEqual('3.499904155731201', row['accumulated_logging_time'])
        self.assertEqual('6715.6014840602875', row['total_duration'])
        self.assertNotEqual(sum(Decimal(row[k]) for k in r.CLOCKS[:3]), Decimal(row['total_duration']))

    def test_measurement_units(self):
        self.assertEqual('seconds', self.result['measurement_units']['clocks'])
        self.assertEqual('dimensionless', self.result['measurement_units']['ssim'])
        self.assertEqual('examples', self.result['measurement_units']['evaluation_denominators'])

    def test_score_raw_not_aggregate(self):
        self.assertTrue(all(x['score'] == x['accumulated_submission_time'] for x in self.result['observations']))
        self.assertIsNone(self.result['official_aggregate_score'])

    def test_no_unsupported_outputs(self):
        for key in ['efficiency_ratio', 'energy_joules', 'theoretical_flops', 'secular_scaling_rate', 'risk_probability', 'budget_exhausted']:
            self.assertIsNone(self.result[key])

    def test_archive_execution_distinct(self):
        i = self.result['trial_identity']
        self.assertEqual(r.ARCHIVE_COMMIT, i['archive_commit'])
        self.assertEqual(r.EXECUTION_COMMIT, i['execution_code_commit'])
        self.assertNotEqual(i['archive_commit'], i['execution_code_commit'])
        self.assertIsNone(i['experiment_datetime'])

    def test_metadata(self):
        m = self.result['controlled_conditions']['metadata']
        expected = {'workload.num_train_examples': 34742, 'workload.num_validation_examples': 3554,
                    'workload.num_test_examples': 3581, 'workload.max_allowed_runtime_sec': 8859,
                    'workload.num_channels': 32, 'workload.num_pool_layers': 4,
                    'gpu_count': 8, 'rng_seed': 1236604812}
        for key, value in expected.items():
            self.assertEqual(value, m[key])
        self.assertEqual('Tesla V100-SXM2-16GB', m['gpu_model_name'])

    def test_full_hyperparams_exact_lexemes(self):
        h = self.result['treatment']['hyperparameters']
        self.assertEqual(23, len(h))
        self.assertEqual('1e-08', h['epsilon'])
        self.assertEqual('0.0017486387539278373', h['learning_rate'])
        self.assertEqual(-1, h['start_preconditioning_step'])
        self.assertIs(False, h['use_momentum'])
        self.assertNotIn('hyperparameters', self.result['controlled_conditions'])

    def test_deterministic_and_duplicate_locations(self):
        self.assertEqual(self.result, r.read_trial())
        self.assertEqual(2, len(self.result['provenance']['locations']))
        self.assertEqual(74, len({x['observation_id'] for x in self.result['observations']}))

    def test_output_json_serializable_without_float_conversion(self):
        out = json.loads(json.dumps(self.result, allow_nan=False))
        self.assertEqual('0.7237818797921356', out['derived_result']['observation']['validation/ssim'])

    def test_truncated_no_exhaustion_or_success(self):
        rows = r._parse_csv(self.csv(self.rows[:-1]))
        out = r._crossing(rows, '0.723653', 'higher_is_better')
        self.assertEqual('target_not_observed_before_last_available_evaluation', out['status'])
        self.assertIsNone(out['observation'])
        self.assertIsNone(out['budget_exhausted'])
        self.assertEqual(22044, out['last_available_observation']['global_step'])

    def test_synthetic_no_crossing_at_late_time_not_exhausted(self):
        rows = deepcopy(self.rows[:1])
        rows[0]['total_duration'] = '99999'
        out = r._crossing(rows, '0.723653', 'higher_is_better')
        self.assertIsNone(out['budget_exhausted'])

    def test_equality_scoring_and_runtime_separate(self):
        row = deepcopy(self.rows[0])
        row['validation/ssim'] = '0.723653'
        row['test/ssim'] = '0.740633'
        out = r._crossing([row], '0.723653', 'higher_is_better')
        self.assertEqual(0, out['row_index'])
        self.assertEqual('>=', out['comparator'])
        self.assertIsNone(out['preceding_observation'])
        self.assertEqual({'validation_strict_gt': False, 'test_strict_gt': False, 'is_runtime_stop_decision': False},
                         r._runtime_predicates(row, '0.723653', '0.740633'))

    def test_lower_is_better_inclusive(self):
        rows = [{'validation/ssim': '0.8'}, {'validation/ssim': '0.7'}]
        out = r._crossing(rows, '0.7', 'lower_is_better')
        self.assertEqual((1, '<='), (out['row_index'], out['comparator']))

    def test_decimal_near_threshold_exact(self):
        rows = [{'validation/ssim': '0.7236529999999999999999999999999999999'},
                {'validation/ssim': '0.723653'}]
        self.assertEqual(1, r._crossing(rows, '0.723653', 'higher_is_better')['row_index'])

    def test_validation_only_test_below(self):
        row = deepcopy(self.rows[-1]); row['test/ssim'] = '0.1'
        self.assertEqual(0, r._crossing([row], '0.723653', 'higher_is_better')['row_index'])
        self.assertFalse(r._runtime_predicates(row, '0.723653', '0.740633')['test_strict_gt'])

    def test_no_interpolation(self):
        self.assertFalse(self.result['derived_result']['interpolated'])
        self.assertEqual('5945.58318734169', self.result['derived_result']['observation']['accumulated_submission_time'])

    def test_bad_direction(self):
        with self.assertRaises(r.ReviewInputError): r._crossing(self.rows, '0.7', 'guess')

    def test_invalid_target(self):
        for x in ['nan', 'Infinity', '1e999', '', True, .7]:
            with self.subTest(x=x), self.assertRaises(r.ReviewInputError): r._crossing(self.rows, x, 'higher_is_better')

    def test_csv_nonfinite(self):
        for x in ['NaN', 'nan', 'Infinity', '-inf']: self.bad_cell('validation/ssim', x)

    def test_csv_exponent_and_length_bound(self):
        for x in ['1e101', '1e-101', '1' * 65]: self.bad_cell('validation/ssim', x)

    def test_csv_whitespace_plus_and_quoted_numeric_formula(self):
        for x in [' 0.5', '0.5 ', '+0.5', '=1/2', '0,5', '01', '1_0']: self.bad_cell('validation/ssim', x)

    def test_csv_int_lexemes(self):
        for x in ['1.0', '1e0', '-1', '01', 'True', '1000000000000']: self.bad_cell('global_step', x)

    def test_csv_negative_loss_clock(self):
        self.bad_cell('validation/loss', '-0.1')
        self.bad_cell('total_duration', '-1')

    def test_csv_ssim_bounds(self):
        for x in ['1.1', '-1.1']: self.bad_cell('validation/ssim', x)

    def test_zero_denominator(self): self.bad_cell('validation/num_examples', '0')

    def test_clock_monotonic(self):
        for key in r.CLOCKS:
            rows = deepcopy(self.rows[:2]); rows[1][key] = '-1' if key == 'accumulated_logging_time' else '0'
            with self.subTest(key=key), self.assertRaises(r.ReviewInputError): r._parse_csv(self.csv(rows))

    def test_denominator_change(self):
        rows = deepcopy(self.rows[:2]); rows[1]['validation/num_examples'] = 3553
        with self.assertRaises(r.ReviewInputError): r._parse_csv(self.csv(rows))

    def test_step_duplicate_or_unordered(self):
        for value in [1, 0]:
            rows = deepcopy(self.rows[:2]); rows[1]['global_step'] = value
            with self.assertRaises(r.ReviewInputError): r._parse_csv(self.csv(rows))

    def test_preemption_decrease(self):
        rows = deepcopy(self.rows[:2]); rows[0]['preemption_count'] = 1
        with self.assertRaises(r.ReviewInputError): r._parse_csv(self.csv(rows))

    def test_clock_exceeds_total(self): self.bad_cell('accumulated_eval_time', '10000')

    def test_csv_header_unknown_duplicate_missing_order(self):
        headers = [list(r.HEADER[:-1]), list(reversed(r.HEADER)), list(r.HEADER[:-1]) + [r.HEADER[0]], list(r.HEADER[:-1]) + ['unknown']]
        for h in headers:
            with self.assertRaises(r.ReviewInputError): r._parse_csv(self.csv(header=h))

    def test_csv_empty_and_oversized_and_encoding(self):
        for raw in [b'', b'x' * (r.MAX_BYTES + 1), b'\xff', b'\xef\xbb\xbf' + self.raw, b'\0' + self.raw]:
            with self.assertRaises(r.ReviewInputError): r._parse_csv(raw)

    def test_csv_row_limit(self):
        rows = deepcopy(self.rows[:1]) * 101
        with self.assertRaises(r.ReviewInputError): r._parse_csv(self.csv(rows))

    def test_csv_no_data_extra_column_blank_and_partial(self):
        for raw in [','.join(r.HEADER).encode(), self.raw + b'\n', self.raw.replace(b',1,0,', b',1,0,extra,', 1), self.raw[:-20]]:
            with self.assertRaises(r.ReviewInputError): r._parse_csv(raw)

    def test_json_duplicate_nested_and_nonfinite(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":[1]}', b'{"a":{"b":1}}', b'{"a":NaN}', b'{"a":1e999}', b'{"a":'+b'['*100+b'0'+b']'*100+b'}']:
            with self.assertRaises(r.ReviewInputError): r._json(raw)

    def test_json_invalid_unicode_and_control(self):
        for raw in [b'{"a":"\\ud800"}', b'{"a":"\\u0000"}', b'{"a":"\\n"}', b'\xff', b'{}']:
            with self.assertRaises(r.ReviewInputError): r._json(raw)

    def test_json_preserves_tokens_and_negative_int(self):
        d = r._json(b'{"x":1e-08,"minus":-1,"zero":0.0,"flag":false,"null":null}')
        self.assertEqual(('1e-08', -1, '0.0', False, None), tuple(d.values()))
        self.assertIs(type(d['x']), r.NumberLexeme)

    def test_only_pinned_files_public(self):
        with tempfile.TemporaryDirectory() as td:
            shutil.copytree(r.FIXTURE, Path(td) / 'fixture')
            path = Path(td) / 'fixture/eval_measurements.csv'
            path.write_bytes(self.csv(self.rows[:-1]))
            with self.assertRaises(r.ReviewInputError): r.read_trial(Path(td) / 'fixture')

    def test_same_length_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            shutil.copytree(r.FIXTURE, Path(td) / 'fixture')
            path = Path(td) / 'fixture/eval_measurements.csv'
            path.write_bytes(path.read_bytes().replace(b'0.723781', b'0.123781'))
            with self.assertRaises(r.ReviewInputError): r.read_trial(Path(td) / 'fixture')

    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(r.ReviewInputError): r.read_trial(td)

    def test_unsafe_paths(self):
        for path in ['../x', '/tmp/../x', 'file:///tmp/x', 'https://example.org/x', 'C:\\x', '/tmp/./x', '\x00', 'x/' * 65, 'x' * 4097, b'/tmp']:
            with self.subTest(path=str(path)), self.assertRaises(r.ReviewInputError): r.read_trial(path)

    def test_unknown_filename(self):
        with self.assertRaises(r.ReviewInputError): r._read_local(r.FIXTURE, '../LICENSE')

    def test_symlink_file(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / 'fixture'; shutil.copytree(r.FIXTURE, d)
            p = d / 'eval_measurements.csv'; p.unlink(); p.symlink_to(r.FIXTURE / p.name)
            with self.assertRaises(r.ReviewInputError): r.read_trial(d)

    def test_symlink_directory_and_parent(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'link'; p.symlink_to(r.FIXTURE, target_is_directory=True)
            with self.assertRaises(r.ReviewInputError): r.read_trial(p)
            ancestor = Path(td) / 'ancestor'; ancestor.symlink_to(r.FIXTURE.parent, target_is_directory=True)
            with self.assertRaises(r.ReviewInputError): r.read_trial(ancestor / r.FIXTURE.name)

    def test_fifo_not_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            os.mkfifo(Path(td) / 'eval_measurements.csv')
            with self.assertRaises(r.ReviewInputError): r.read_trial(td)

    def test_directory_not_file(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / 'eval_measurements.csv').mkdir()
            with self.assertRaises(r.ReviewInputError): r.read_trial(td)

    def test_no_network_or_source_execution_dependencies(self):
        import ast
        tree = ast.parse((HERE / 'read_algoperf_trial.py').read_text())
        imports = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
        self.assertFalse(imports & {'requests', 'socket', 'urllib', 'subprocess', 'pickle', 'torch'})
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                             and n.func.id in {'exec', 'eval', 'compile', '__import__'} for n in ast.walk(tree)))


if __name__ == '__main__': unittest.main()
