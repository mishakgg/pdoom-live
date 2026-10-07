#!/usr/bin/env python3
"""Offline validation for proposed pdataset 0.1.0. Never fetches URLs or imports data.

This checks structures and selected semantic invariants, not truth, scientific
comparability, legal permission, actual publication, or production integration.
Requires Python >=3.10 and jsonschema >=4 with Draft202012Validator support.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / 'contracts' / 'dataset.schema.json'
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
FORMAT_CHECKER = FormatChecker()
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMAT_CHECKER)
REF_TYPES = {
    'source_ref': {'source_artifact'}, 'original_ref': {'source_artifact'},
    'translation_ref': {'source_artifact'}, 'publisher_ref': {'actor'},
    'author_refs': {'actor'}, 'reviewer_ref': {'actor'},
    'organization_ref': {'actor'}, 'speaker_refs': {'actor'},
    'developer_refs': {'actor'}, 'evaluator_refs': {'actor'},
    'forecaster_refs': {'actor'}, 'adjudicator_refs': {'actor'},
    'population_ref': {'actor'}, 'aggregator_ref': {'actor'},
    'model_ref': {'model_version'}, 'parent_model_refs': {'model_version'},
    'statement_ref': {'statement'}, 'question_ref': {'forecast_question'},
    'subject_refs': {'actor', 'model_version'},
    'record_ref': set(SCHEMA['$defs']['record']['properties']['record_type']['enum']) - {'snapshot'},
}
NONNEGATIVE_UNITS = {'probability', 'percent', 'count', 'second', 'hour', 'token',
    'parameter', 'FLOP', 'FLOP/s', 'GPU_hour', 'watt', 'joule', 'kWh'}
INTEGER_UNITS = {'calendar_year'}
NUMERIC_KINDS = {'point', 'interval', 'lower_bound', 'upper_bound', 'quantiles'}
VALUE_KINDS = NUMERIC_KINDS | {'date_point', 'date_quantiles', 'category', 'boolean', 'missing'}

def key(ref):
    return ref['id'], ref['revision']

def iso(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def temporal_lower(value):
    if value['kind'] == 'unknown': return None
    if value['kind'] == 'instant': return iso(value['at'])
    return iso(value.get('date', value.get('start')) + 'T00:00:00Z')

def temporal_upper(value):
    if value['kind'] == 'unknown': return None
    if value['kind'] == 'instant': return iso(value['at'])
    return iso(value.get('date', value.get('end')) + 'T23:59:59.999999Z')

def canonical_bytes(value):
    """Project canonicalization, deliberately not advertised as RFC8785/JCS."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def iter_objects(value, path=()):
    if isinstance(value, dict):
        yield path, value
        for name, child in value.items():
            yield from iter_objects(child, path + (name,))
    elif isinstance(value, list):
        for n, child in enumerate(value):
            yield from iter_objects(child, path + (n,))

def references(record):
    for path, value in iter_objects(record):
        if set(value) == {'id', 'revision'}:
            field = next((p for p in reversed(path) if isinstance(p, str)), '')
            yield path, field, value

def numeric_values(value):
    kind = value['kind']
    if kind == 'point': return [Decimal(value['value'])]
    if kind == 'interval': return [Decimal(value['lower']), Decimal(value['upper'])]
    if kind in ('lower_bound', 'upper_bound'): return [Decimal(value['bound'])]
    if kind == 'quantiles': return [Decimal(p['value']) for p in value['quantiles']]
    return []

def path_text(path):
    return '/' + '/'.join(str(x) for x in path)

def validate_bundle(bundle):
    """Return ordered diagnostic dictionaries. A nonempty result fails validation."""
    errors = []
    def err(code, message, path=()):
        errors.append({'code': code, 'path': path_text(path), 'message': message})
    structural = sorted(VALIDATOR.iter_errors(bundle), key=lambda e: tuple(str(x) for x in e.absolute_path))
    if structural:
        for e in structural:
            err('schema', e.message, tuple(e.absolute_path))
        return errors  # Do not try semantic traversal on malformed shapes.
    records = bundle['records']
    index = {}
    for i, record in enumerate(records):
        k = key(record)
        if k in index: err('duplicate_revision', 'Duplicate (id, revision).', ('records', i))
        index[k] = record
    if errors: return errors
    generated = iso(bundle['generated_at'])
    for i, r in enumerate(records):
        root = ('records', i)
        data, typ, gov = r['data'], r['record_type'], r['governance']
        known = iso(r['times']['known_at'])
        if r['synthetic'] != (bundle['dataset_kind'] == 'synthetic'):
            err('mixed_synthetic', 'Every record must match dataset_kind; fixture and real data must not mix.', root)
        if iso(r['times']['retrieved_at']) > known:
            err('time_order', 'retrieved_at must not follow known_at for this evidence revision.', root + ('times',))
        if known > generated:
            err('time_order', 'known_at must not follow export generated_at.', root + ('times', 'known_at'))
        if 'reviewed_at' in gov and iso(gov['reviewed_at']) > generated:
            err('time_order', 'Review cannot occur after the bundle was exported.', root + ('governance',))
        if gov['review_state'] in ('machine_validated', 'human_verified') and 'reviewed_at' not in gov:
            err('review_timestamp', 'Validated and verified states need reviewed_at.', root + ('governance',))
        if gov['review_state'] == 'human_verified' and 'reviewer_ref' not in gov:
            err('human_reviewer', 'Human verification requires an identified reviewer.', root + ('governance',))
        if gov['publication_state'] == 'eligible':
            if gov['review_state'] != 'human_verified' or gov['rights_state'] not in ('metadata_only', 'redistribution_allowed'):
                err('publication_gate', 'Proposed eligible tier requires human verification and cleared metadata/content rights.', root + ('governance',))
        if gov['rights_state'] in ('restricted', 'unknown', 'link_only', 'metadata_only'):
            has_excerpt = any('excerpt' in e for e in r['evidence'])
            if gov['publication_state'] == 'eligible' and (has_excerpt or typ == 'statement') and gov['rights_state'] != 'redistribution_allowed':
                err('content_rights', 'Statement text or excerpts need explicit content redistribution clearance for eligible export.', root)
        for path, field, target_ref in references(r):
            target = index.get(key(target_ref))
            if target is None:
                err('missing_reference', f'Reference not present in this self-contained bundle: {key(target_ref)}.', root + path)
                continue
            if field in REF_TYPES and target['record_type'] not in REF_TYPES[field]:
                err('reference_type', f'{field} cannot reference {target["record_type"]}.', root + path)
            if field not in ('record_ref',) and iso(target['times']['known_at']) > known:
                err('future_reference', 'A revision cannot cite a reference revision not yet known to this dataset.', root + path)
            if field == 'organization_ref' and target['data'].get('actor_kind') != 'organization':
                err('organization_type', 'Affiliation target must be an organization actor.', root + path)
            if field == 'reviewer_ref' and gov['review_state'] == 'human_verified' and target['data'].get('actor_kind') != 'person':
                err('human_reviewer', 'Human verification reviewer must resolve to a person actor.', root + path)
        if 'supersedes' in r:
            prev = r['supersedes']
            if prev['id'] != r['id'] or prev['revision'] != r['revision'] - 1:
                err('revision_lineage', 'supersedes must be the immediately preceding revision of the same id.', root + ('supersedes',))
            prior = index.get(key(prev))
            if prior and iso(prior['times']['known_at']) >= known:
                err('revision_time', 'A new revision must become known strictly later than its predecessor.', root)
        if r['revision'] == 1 and 'supersedes' in r:
            err('revision_lineage', 'Revision 1 cannot supersede another revision.', root)
        # Values and temporal ranges are reusable; validate them everywhere.
        for path, value in iter_objects(r):
            full = root + path
            kind = value.get('kind')
            if kind == 'range' and 'start' in value and value['start'] > value['end']:
                err('time_range', 'Temporal start exceeds end.', full)
            if kind not in VALUE_KINDS: continue
            if kind == 'interval':
                if Decimal(value['lower']) > Decimal(value['upper']):
                    err('value_range', 'Interval lower exceeds upper.', full)
                statistical = value['interval_kind'] in ('confidence', 'credible')
                if statistical != ('level' in value):
                    err('interval_level', 'Only confidence/credible intervals require and allow level.', full)
                if 'level' in value and not Decimal('0') < Decimal(value['level']) < Decimal('1'):
                    err('interval_level', 'Coverage level must be strictly between zero and one.', full)
            if kind in ('quantiles', 'date_quantiles'):
                qs = [Decimal(p['q']) for p in value['quantiles']]
                xs = [Decimal(p['value']) if kind == 'quantiles' else p['date'] for p in value['quantiles']]
                if any(q < 0 or q > 1 for q in qs) or any(a >= b for a, b in zip(qs, qs[1:])):
                    err('quantile_order', 'q must be in [0,1] and strictly increasing.', full)
                if any(a > b for a, b in zip(xs, xs[1:])):
                    err('quantile_monotonicity', 'Quantile values must be nondecreasing.', full)
            unit = value.get('unit')
            if kind in ('lower_bound', 'upper_bound') and not value['inclusive']:
                n = Decimal(value['bound'])
                intrinsic_min = Decimal(1) if unit == 'calendar_year' else (Decimal(0) if unit in NONNEGATIVE_UNITS else None)
                intrinsic_max = {'probability': Decimal(1), 'percent': Decimal(100), 'calendar_year': Decimal(9999)}.get(unit)
                if kind == 'upper_bound' and intrinsic_min is not None and n <= intrinsic_min or kind == 'lower_bound' and intrinsic_max is not None and n >= intrinsic_max:
                    err('empty_bound', 'Strict bound leaves no possible value within the unit domain.', full)
            for n in numeric_values(value):
                if unit in NONNEGATIVE_UNITS and n < 0:
                    err('unit_range', f'{unit} cannot be negative.', full)
                if unit == 'probability' and n > 1:
                    err('probability_range', 'Probability is a fraction in [0,1], not a percentage.', full)
                if unit == 'percent' and n > 100:
                    err('unit_range', 'percent is a bounded proportion; use percent_change for signed/unbounded change.', full)
                if unit in INTEGER_UNITS and n != n.to_integral_value():
                    err('integer_unit', f'{unit} requires an integer-valued decimal.', full)
                if unit == 'calendar_year' and not 1 <= n <= 9999:
                    err('unit_range', 'calendar_year must lie in 1..9999.', full)
        # Measurement definitions must agree with result units and scale limits.
        for path, value in iter_objects(data):
            if 'metric' not in value or 'result' not in value: continue
            metric, result = value['metric'], value['result']
            full = root + ('data',) + path
            if result['kind'] not in NUMERIC_KINDS | {'missing'}:
                err('measurement_type', 'Measurement result must be numeric or explicitly missing.', full)
            if 'unit' in result and result['unit'] != metric['unit']:
                err('metric_unit', 'Result and metric units must match.', full)
            low, high = metric.get('minimum'), metric.get('maximum')
            if low is not None and high is not None and Decimal(low) > Decimal(high):
                err('metric_scale', 'Metric minimum exceeds maximum.', full)
            if result['kind'] in ('lower_bound', 'upper_bound') and not result['inclusive']:
                n = Decimal(result['bound'])
                if result['kind'] == 'upper_bound' and low is not None and n <= Decimal(low) or result['kind'] == 'lower_bound' and high is not None and n >= Decimal(high):
                    err('empty_bound', 'Strict bound leaves no possible value within declared metric limits.', full)
            for n in numeric_values(result):
                if low is not None and n < Decimal(low) or high is not None and n > Decimal(high):
                    err('metric_scale', 'Value lies outside the declared metric scale.', full)
        if typ in ('benchmark_run', 'safety_evaluation') and r['times']['evaluated']['kind'] == 'unknown':
            # Unknown is allowed, but cannot make this a fully reproducible measured run.
            if data['protocol']['reproducibility'] == 'full':
                err('evaluation_time', 'Full reproducibility requires an actual evaluation time.', root)
        if typ == 'safety_evaluation' and 'threshold' in data:
            threshold = data['threshold']
            if threshold['kind'] not in NUMERIC_KINDS or threshold.get('unit') != data['measurement']['metric']['unit']:
                err('threshold_unit', 'Safety threshold must be numeric in the measurement unit.', root)
        if typ == 'resource_observation':
            money = data['measurement']['metric']['unit'] in ('currency_nominal', 'currency_constant')
            if money != ('currency_basis' in data):
                err('currency_basis', 'Currency basis is required only for currency-valued observations.', root)
            if money and 'currency_basis' in data:
                b = data['currency_basis']
                expected = 'constant' if data['measurement']['metric']['unit'] == 'currency_constant' else 'nominal'
                if b['price_basis'] != expected or (expected == 'constant' and 'base_year' not in b):
                    err('currency_basis', 'Price basis must match unit; constant prices require base_year.', root)
        if typ == 'source_artifact' and 'translation' in data:
            original = index.get(key(data['translation']['original_ref']))
            if original and (original['id'] == r['id'] or 'translation' in original['data']):
                err('translation_lineage', 'Translation must point directly to a distinct original, not another translation.', root)
        if typ == 'actor':
            if (data['actor_kind'] == 'collective') != ('collective' in data):
                err('collective_identity', 'Only collective actors require and allow collective population metadata.', root)
        if typ == 'statement' and 'translation_ref' in data:
            translated = index.get(key(data['translation_ref']))
            if translated and 'translation' not in translated['data']:
                err('translation_type', 'translation_ref must reference a translation artifact.', root)
            elif translated:
                originals = {key(e['source_ref']) for e in r['evidence']}
                if key(translated['data']['translation']['original_ref']) not in originals:
                    err('translation_evidence', 'Statement must cite the original artifact underlying its linked translation.', root)
        if typ == 'forecast_question':
            needs_unit = data['answer_domain'] in ('probability', 'quantity')
            if needs_unit != ('answer_unit' in data):
                err('question_unit', 'Only probability and quantity questions require and allow answer_unit.', root)
            if data['answer_domain'] == 'probability' and data.get('answer_unit') != 'probability':
                err('question_unit', 'Probability question unit must be probability.', root)
        if typ == 'forecast':
            question = index.get(key(data['question_ref']))
            if question and question['record_type'] == 'forecast_question':
                answer_matches(question['data'], data['answer'], root, err, resolved=False)
            if temporal_lower(data['as_of']) is not None and temporal_lower(data['as_of']) > known:
                err('forecast_time', 'Forecast as_of cannot be wholly after dataset knowledge time.', root)
            answer_kind = data['answer']['kind']
            if data['forecast_origin'] == 'explicit_qualitative' and answer_kind not in ('category', 'missing'):
                err('invented_precision', 'An explicitly qualitative statement cannot become a numeric forecast.', root)
            if data['forecast_origin'] == 'explicit_numeric' and answer_kind in ('category', 'boolean'):
                err('forecast_origin', 'Explicit numeric origin requires a numeric/date answer or explicit missingness.', root)
            if (data['aggregation'] != 'none') != ('aggregation_method' in data):
                err('aggregation_method', 'Aggregate forecasts require a method; nonaggregates must omit it.', root)
            collective_forecaster = any(index.get(key(ref), {}).get('data', {}).get('actor_kind') == 'collective' for ref in data['forecaster_refs'])
            if collective_forecaster and data['aggregation'] != 'source_aggregate':
                err('collective_aggregate', 'Collective forecasts require source_aggregate and its attribution context.', root)
            aggregate = data['aggregation'] == 'source_aggregate'
            if aggregate != ('aggregate_context' in data):
                err('aggregate_context', 'Only source aggregates require and allow structured population context.', root)
            if aggregate and 'aggregate_context' in data:
                context = data['aggregate_context']
                population = index.get(key(context['population_ref']))
                publisher = index.get(key(context['aggregator_ref']))
                if not population or population['data'].get('actor_kind') != 'collective':
                    err('aggregate_population', 'Aggregate population must resolve to a collective actor.', root)
                if publisher and publisher['data'].get('actor_kind') not in ('person', 'organization'):
                    err('aggregate_publisher', 'Aggregator is a person/organization, not the respondent population.', root)
                if data['forecaster_refs'] != [context['population_ref']]:
                    err('aggregate_attribution', 'A source aggregate must attribute the population, not the publisher.', root)
                if key(context['population_ref']) == key(context['aggregator_ref']):
                    err('aggregate_attribution', 'Population and aggregator must be distinct.', root)
            if 'statement_ref' in data:
                st = index.get(key(data['statement_ref']))
                if st and st['record_type'] == 'statement' and st['data']['statement_type'] != data['forecast_origin']:
                    err('statement_origin', 'Forecast origin must preserve linked statement type.', root)
                if st and st['record_type'] == 'statement' and not aggregate and data['forecast_origin'] != 'model_inferred_signal':
                    speakers = {key(ref) for ref in st['data']['speaker_refs']}
                    if any(key(ref) not in speakers for ref in data['forecaster_refs']):
                        err('statement_attribution', 'Explicit statement-derived forecast must attribute its actual speaker(s).', root)
        if typ == 'resolution':
            resolved = data['status'] == 'resolved'
            if resolved != ('outcome' in data and 'resolved_at' in data):
                err('resolution_state', 'Only resolved cases require both outcome and resolved_at.', root)
            if not resolved and ('outcome' in data or 'resolved_at' in data):
                err('resolution_state', 'Open, ambiguous and void cases must not carry an outcome.', root)
            if resolved:
                if not data['adjudicator_refs'] or gov['review_state'] != 'human_verified':
                    err('resolution_review', 'Resolved cases require an adjudicator and human verification.', root)
                if iso(data['resolved_at']) > known:
                    err('resolution_time', 'Resolution cannot be later than when this revision became known.', root)
                q = index.get(key(data['question_ref']))
                if q and q['record_type'] == 'forecast_question':
                    answer_matches(q['data'], data['outcome'], root, err, resolved=True)
        if typ == 'snapshot':
            cut = iso(data['cutoff'])
            if cut > iso(data['created_at']) or iso(data['created_at']) > known:
                err('snapshot_time', 'Require cutoff <= created_at <= snapshot known_at.', root)
            keys = [key(member['record_ref']) for member in data['members']]
            if len(keys) != len(set(keys)):
                err('snapshot_duplicate', 'Snapshot members must be unique exact revisions.', root)
            selected = set(keys)
            for j, member in enumerate(data['members']):
                target = index.get(key(member['record_ref']))
                if not target: continue
                full = root + ('data', 'members', j)
                if member['sha256'] != digest(target):
                    err('snapshot_hash', 'Member hash differs from the canonical record bytes.', full)
                if iso(target['times']['known_at']) > cut:
                    err('snapshot_cutoff', 'Member was not known at cutoff.', full)
                if data['snapshot_kind'] == 'as_known' and target['record_type'] == 'forecast':
                    upper = temporal_upper(target['data']['as_of'])
                    if upper is None or upper > cut:
                        err('snapshot_forecast_time', 'Forecast time is unknown or its possible upper bound exceeds as-known cutoff.', full)
                review = target['governance'].get('reviewed_at')
                if data['snapshot_kind'] == 'as_known' and review and iso(review) > cut:
                    err('snapshot_review', 'Member review occurred after as-known cutoff; use an earlier revision.', full)
                for _, _, dep in references(target):
                    if key(dep) not in selected:
                        err('snapshot_closure', 'Snapshot omits a member dependency or its prior revision.', full)
    return errors

def answer_matches(question, value, root, err, resolved):
    domain, kind = question['answer_domain'], value['kind']
    if kind == 'missing':
        if resolved: err('resolution_outcome', 'A resolved outcome cannot be missing.', root)
        return
    if resolved and domain == 'probability':
        if kind != 'boolean': err('resolution_outcome', 'Binary event resolution must be boolean, not a forecast probability.', root)
    elif domain in ('probability', 'quantity'):
        if kind not in NUMERIC_KINDS or value.get('unit') != question.get('answer_unit'):
            err('answer_domain', 'Forecast answer kind/unit is incompatible with the exact question.', root)
    elif domain == 'date' and not (kind in ('date_point', 'date_quantiles') or kind in NUMERIC_KINDS and value.get('unit') == 'calendar_year'):
        err('answer_domain', 'Date question needs date values or integer calendar_year values; preserve source precision.', root)
    elif domain == 'qualitative' and kind != 'category':
        err('answer_domain', 'Qualitative question requires a category.', root)
    if resolved and kind in ('quantiles', 'date_quantiles', 'lower_bound', 'upper_bound', 'interval'):
        err('resolution_outcome', 'This prototype only admits exact resolved outcomes; ambiguous outcomes remain unscored.', root)

def check_contracts():
    paths = sorted((ROOT / 'contracts').glob('*.schema.json'))
    docs = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
    registry = Registry().with_resources([(d['$id'], Resource.from_contents(d)) for d in docs])
    for schema in docs:
        Draft202012Validator.check_schema(schema)
    return docs, registry

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', nargs='?', default=str(ROOT / 'examples' / 'synthetic_dataset.json'))
    parser.add_argument('--report', type=Path, help='Write JSON validation report to this local path.')
    args = parser.parse_args()
    try:
        docs, registry = check_contracts()
        bundle = json.loads(Path(args.dataset).read_text(encoding='utf-8'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f'Non-finite JSON value: {x}')))
        errors = validate_bundle(bundle)
        # Exercise the standalone wrappers offline too.
        if not errors:
            by_type = {d['$id'].rsplit('/', 1)[-1].removesuffix('.schema.json'): d for d in docs}
            for i, record in enumerate(bundle['records']):
                wrapper = by_type[record['record_type']]
                for e in Draft202012Validator(wrapper, registry=registry, format_checker=FORMAT_CHECKER).iter_errors(record):
                    errors.append({'code': 'wrapper_schema', 'path': f'/records/{i}', 'message': e.message})
        report = {'schema_version': '0.1.0', 'valid': not errors, 'records': len(bundle['records']) if isinstance(bundle, dict) and isinstance(bundle.get('records'), list) else 0,
                  'schemas_checked': len(docs), 'errors': errors,
                  'notice': 'Structure and selected invariants only. No source fetching, evidence adjudication, legal review, calibration or production integration performed.'}
    except (OSError, ValueError, KeyError) as exc:
        report = {'valid': False, 'errors': [{'code': 'input_error', 'message': str(exc)}]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0 if report['valid'] else 1

if __name__ == '__main__':
    sys.exit(main())
