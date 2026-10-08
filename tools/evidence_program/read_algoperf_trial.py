#!/usr/bin/env python3
"""Read one pinned AlgoPerf v0.5 trial from local research fixtures, offline.

No network, training, source-code execution, imported dataset or official score.
Public read_trial accepts only byte-identical copies of the four reviewed files.
Private parsers and crossing helpers support synthetic regression tests only.
Decimal measurements retain exact lexical strings, never binary floats.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys

FIXTURE = Path(__file__).resolve().parent / 'tests/fixtures/algorithmic-efficiency'
ARCHIVE_COMMIT = '834b09b27ed24d50cb7cbe07f0c83c7f7dc2076f'
EXECUTION_COMMIT = '4b01ee64c30dec442dd111abe31d40d80820fc70'
CSV_BLOB = '038e3ea5a3b86281d686f7712c9ca4117acd4447'
TRIAL_PATH = 'logs/algoperf_scoring_v05/external_tuning/Team_21/shampoo_submission/study_0/fastmri_pytorch/trial_1/'
SOURCE_PREFIX = 'https://github.com/mlcommons/algorithms_results_v0.5/blob/' + ARCHIVE_COMMIT + '/'
DUPLICATE_URL = 'https://github.com/mlcommons/submissions_algorithms/blob/e191c2bb2253bcb29804796cf9e36935aee70a0a/previous_leaderboards/algoperf_v05/logs/external_tuning/shampoo_submission/study_0/fastmri_pytorch/trial_1/eval_measurements.csv'
MAX_BYTES = 32768
MAX_ROWS = 100
MAX_COLUMNS = 15
MAX_NUMBER_CHARS = 64
MAX_PATH_CHARS = 4096
HEADER = ('accumulated_eval_time', 'accumulated_logging_time', 'accumulated_submission_time',
          'global_step', 'preemption_count', 'score', 'test/loss', 'test/num_examples',
          'test/ssim', 'total_duration', 'train/loss', 'train/ssim', 'validation/loss',
          'validation/num_examples', 'validation/ssim')
INTEGER_FIELDS = {'global_step', 'preemption_count', 'test/num_examples', 'validation/num_examples'}
CLOCKS = ('accumulated_eval_time', 'accumulated_logging_time', 'accumulated_submission_time', 'total_duration')
PINS = {
    'eval_measurements.csv': (16630, 'd113215fe011f988150591f47bbc665b6f202b173ae45334d7e97f30421d0226'),
    'meta_data_0.curated.json': (1115, '43ec460c9b304d2ca480cbf08f6774f505deda982dac2ad46c864e20b66b20b1'),
    'hparams.json': (693, '3894a9524cd3f56844098f0f1fa7ecd8951f8274799ad1cdbb5aee12ade8ab00'),
    'flags_0.curated.json': (858, '6a0aae54fbca381b336d5f86abb0cb02cacb8ff16ef4f31422eaed9c450325ec'),
}
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z')


class ReviewInputError(ValueError):
    """Outside the narrow research fixture contract."""


class NumberLexeme(str):
    """A JSON numeric token, retained as text without binary conversion."""


def require(condition, message):
    if not condition:
        raise ReviewInputError(message)


def decimal(token):
    require(type(token) in (str, NumberLexeme) and len(token) <= MAX_NUMBER_CHARS
            and NUMBER.fullmatch(token), 'invalid or unbounded numeric token')
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ReviewInputError('invalid decimal token') from exc
    require(value.is_finite() and abs(value.as_tuple().exponent) <= 100
            and value.adjusted() <= 100, 'decimal exponent outside bounded profile')
    return value


def _json_number(token):
    decimal(token)
    return NumberLexeme(token)


def _json_int(token):
    decimal(token)
    require(len(token.lstrip('-')) <= 16, 'invalid metadata integer')
    return int(token)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(_token):
    raise ReviewInputError('nonfinite JSON token')


def _text(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'invalid input byte bound')
    try:
        value = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ReviewInputError('input is not UTF-8') from exc
    require('\x00' not in value and not value.startswith('\ufeff'), 'NUL or BOM in input')
    return value


def _json(raw):
    text = _text(raw)
    # All four reviewed configuration files are flat scalar objects. Check
    # nesting before parsing so malicious deep input cannot exhaust the decoder.
    depth = tokens = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
            tokens += 1
        elif char in '[{':
            depth += 1
            tokens += 1
            require(depth <= 2, 'JSON nesting limit')
        elif char in ']}':
            depth -= 1
        require(tokens <= 256, 'JSON token limit')
    try:
        value = json.loads(text, parse_int=_json_int, parse_float=_json_number,
                           parse_constant=_reject_constant, object_pairs_hook=_unique)
    except (ValueError, RecursionError) as exc:
        raise ReviewInputError('invalid bounded JSON: ' + str(exc)) from exc
    require(type(value) is dict and 0 < len(value) <= 64, 'expected small JSON object')
    for key, item in value.items():
        require(type(key) is str and 0 < len(key) <= 128, 'invalid JSON key')
        require(type(item) in (str, NumberLexeme, int, bool, type(None)), 'non-scalar configuration')
        if type(item) in (str, NumberLexeme):
            try:
                encoded = item.encode('utf-8')
            except UnicodeEncodeError as exc:
                raise ReviewInputError('invalid Unicode scalar') from exc
            require(len(encoded) <= 1024 and not any(ord(x) < 32 for x in item), 'invalid configuration string')
    return value


def _parse_csv(raw):
    text = _text(raw)
    require(max(map(len, text.splitlines()), default=0) <= 4096, 'CSV line bound')
    reader = csv.reader(io.StringIO(text, newline=''), strict=True)
    try:
        header = next(reader)
        require(tuple(header) == HEADER, 'unexpected, missing or duplicate CSV header')
        rows = []
        previous = None
        for values in reader:
            require(len(rows) < MAX_ROWS and len(values) == MAX_COLUMNS, 'CSV row or column bound')
            row = {}
            for key, token in zip(HEADER, values):
                value = decimal(token)
                if key in INTEGER_FIELDS:
                    require(re.fullmatch(r'(?:0|[1-9][0-9]*)', token) and len(token) <= 12,
                            'invalid integer measurement')
                    row[key] = int(token)
                else:
                    require(-1 <= value <= 1 if key.endswith('/ssim') else value >= 0,
                            'measurement outside profile bounds')
                    row[key] = token
            require(row['global_step'] > 0 and row['test/num_examples'] > 0
                    and row['validation/num_examples'] > 0, 'zero step or denominator')
            if previous:
                require(row['global_step'] > previous['global_step'], 'duplicate or unordered step')
                require(row['preemption_count'] >= previous['preemption_count'], 'decreasing preemption count')
                for key in CLOCKS:
                    require(decimal(row[key]) >= decimal(previous[key]), 'decreasing clock: ' + key)
                for key in ('test/num_examples', 'validation/num_examples'):
                    require(row[key] == previous[key], 'changing evaluation denominator')
            require(all(decimal(row['total_duration']) >= decimal(row[key]) for key in CLOCKS),
                    'component clock exceeds total duration')
            rows.append(row)
            previous = row
    except (csv.Error, StopIteration) as exc:
        raise ReviewInputError('malformed CSV') from exc
    require(rows, 'no evaluations')
    return rows


def _crossing(rows, target, direction, metric='validation/ssim'):
    """Synthetic-testable retrospective inclusive criterion, not runtime stop."""
    require(direction in ('higher_is_better', 'lower_is_better'), 'unknown metric direction')
    threshold = decimal(target)
    require(type(rows) is list and 0 < len(rows) <= MAX_ROWS, 'invalid evaluation count')
    for i, row in enumerate(rows):
        require(type(row) is dict and metric in row, 'missing target metric')
        value = decimal(row[metric])
        reached = value >= threshold if direction == 'higher_is_better' else value <= threshold
        if reached:
            return dict(status='observed_validation_target_crossing',
                        derivation_version='algoperf-checkpoint-crossing/1',
                        criterion='retrospective_scoring_inclusive',
                        comparator='>=' if direction == 'higher_is_better' else '<=',
                        metric=metric, target=target, direction=direction,
                        row_index=i, observation=row.copy(),
                        preceding_observation=None if i == 0 else rows[i - 1].copy(),
                        interpolated=False, budget_exhausted=None)
    return dict(status='target_not_observed_before_last_available_evaluation',
                derivation_version='algoperf-checkpoint-crossing/1',
                criterion='retrospective_scoring_inclusive',
                comparator='>=' if direction == 'higher_is_better' else '<=',
                metric=metric, target=target, direction=direction, row_index=None,
                observation=None, preceding_observation=None,
                last_available_observation=rows[-1].copy(),
                interpolated=False, budget_exhausted=None)


def _runtime_predicates(row, validation_target, test_target):
    """Point predicates only; runner stops using latched cumulative goals."""
    return {'validation_strict_gt': decimal(row['validation/ssim']) > decimal(validation_target),
            'test_strict_gt': decimal(row['test/ssim']) > decimal(test_target),
            'is_runtime_stop_decision': False}


def _read_local(directory, name):
    require(name in PINS, 'artifact name outside fixed allowlist')
    try:
        rawpath = os.fspath(directory)
    except TypeError as exc:
        raise ReviewInputError('invalid local directory') from exc
    require(type(rawpath) is str and 0 < len(rawpath) <= MAX_PATH_CHARS
            and not any(c in rawpath for c in ('\x00', '\\', ':'))
            and not any(ord(c) < 32 for c in rawpath), 'invalid local path')
    components = rawpath.split('/')
    require('..' not in components and '.' not in components and len(components) <= 64,
            'path traversal or component limit')
    path = os.path.abspath(rawpath)
    fd = None
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        for part in [x for x in path.split('/') if x]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        filefd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            before = os.fstat(filefd)
            require(stat.S_ISREG(before.st_mode), 'expected regular file')
            expected_size, expected_sha = PINS[name]
            require(before.st_size == expected_size <= MAX_BYTES, 'fixture byte count mismatch')
            chunks, count = [], 0
            while count <= MAX_BYTES:
                chunk = os.read(filefd, min(8192, MAX_BYTES + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
            raw = b''.join(chunks)
            after = os.fstat(filefd)
            require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                    'file changed during read')
            require(len(raw) == expected_size and hashlib.sha256(raw).hexdigest() == expected_sha,
                    'fixture fingerprint mismatch')
            return raw
        finally:
            os.close(filefd)
    except OSError as exc:
        raise ReviewInputError('local fixture unavailable or unsafe') from exc
    finally:
        if fd is not None:
            os.close(fd)


def read_trial(directory=FIXTURE):
    """Read only the frozen trial, producing deterministic research output."""
    raw = {name: _read_local(directory, name) for name in PINS}
    rows = _parse_csv(raw['eval_measurements.csv'])
    metadata = _json(raw['meta_data_0.curated.json'])
    flags = _json(raw['flags_0.curated.json'])
    hparams = _json(raw['hparams.json'])
    require(len(rows) == 74, 'expected 74 checkpoints')
    require(metadata['git_commit_hash'] == EXECUTION_COMMIT != ARCHIVE_COMMIT,
            'execution revision drift')
    require(metadata['rng_seed'] == flags['rng_seed'] == 1236604812, 'seed mismatch')
    require(metadata['workload.num_validation_examples'] == 3554
            and all(x['validation/num_examples'] == 3554 and x['test/num_examples'] == 3581 for x in rows),
            'denominator mismatch')
    target = metadata['workload.validation_target_value']
    test_target = metadata['workload.test_target_value']
    require(type(target) is NumberLexeme and target == '0.723653'
            and type(test_target) is NumberLexeme and test_target == '0.740633', 'target mismatch')
    require(flags['framework'] == 'pytorch' and flags['torch_compile'] is True
            and flags['tuning_ruleset'] == 'external' and flags['num_tuning_trials'] == 5,
            'protocol mismatch')
    require(all(x['score'] == x['accumulated_submission_time'] for x in rows),
            'raw score/time relation changed')
    result = _crossing(rows, target, 'higher_is_better')
    require(result['row_index'] == 73 and result['observation']['global_step'] == 22353
            and result['preceding_observation']['global_step'] == 22044, 'crossing changed')
    for i, row in enumerate(rows):
        row['observation_id'] = CSV_BLOB + ':' + str(i)
    return dict(schema_version='algoperf-single-trial-review/1.0.0',
                input_kind='pinned_licensed_research_fixture', operational_admission='not_admitted',
                decimal_representation='exact_source_lexeme_strings_with_integer_count_fields',
                measurement_units=dict(clocks='seconds', raw_score='seconds', global_step='optimizer_step',
                    preemption_count='count', evaluation_denominators='examples', ssim='dimensionless',
                    loss='source_workload_mean_absolute_error'),
                trial_identity=dict(benchmark='AlgoPerf', benchmark_version='v0.5',
                    team='Team_21', submission='shampoo_submission', study_id=0, trial_id=1,
                    archive_commit=ARCHIVE_COMMIT, execution_code_commit=EXECUTION_COMMIT,
                    experiment_datetime=None, seed=1236604812),
                provenance=dict(source_csv_git_blob=CSV_BLOB,
                    source_csv_sha256=PINS['eval_measurements.csv'][1],
                    locations=[SOURCE_PREFIX + TRIAL_PATH + 'eval_measurements.csv', DUPLICATE_URL],
                    source_manifest='manifest.json', local_fixture_sha256={k: v[1] for k, v in PINS.items()},
                    license='Apache-2.0', source_fixture_cc0=False,
                    json_retention='allowlisted_derivatives_with_separate_original_hashes_in_manifest'),
                controlled_conditions=dict(workload='fastmri', architecture='U-Net',
                    metadata=metadata, execution_flags=flags,
                    metric='validation/ssim', direction='higher_is_better',
                    validation_target=target, comparison_clock='accumulated_submission_time',
                    tuning_ruleset='external', trials_per_study_allowance=5,
                    framework='pytorch', torch_compile=True),
                treatment=dict(optimizer='Distributed Shampoo', hyperparameters=hparams),
                observations=rows, observation_count=len(rows), trial_count=1,
                derived_result=result,
                runtime_predicates_at_crossing=_runtime_predicates(result['observation'], target, test_target),
                runtime_versus_scoring='Scoring is inclusive validation-only. Runtime uses strict validation/test predicates and latched goals; this reader does not emulate run termination.',
                raw_score_interpretation='CSV score is preserved raw submission-time field, not an official aggregate leaderboard score.',
                budget_exhausted=None, official_aggregate_score=None,
                efficiency_ratio=None, energy_joules=None, theoretical_flops=None,
                secular_scaling_rate=None, risk_probability=None,
                output_scope='Independent one-trial checkpoint analysis only; no training data, code execution, collection or canonical import.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir', type=str, default=str(FIXTURE), help='Local directory of exact reviewed fixtures')
    args = parser.parse_args()
    try:
        result = read_trial(args.fixture_dir)
    except (ReviewInputError, KeyError) as exc:
        print('AlgoPerf review failed: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
