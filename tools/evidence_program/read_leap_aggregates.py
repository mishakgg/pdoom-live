"""Bounded offline validator for a manually curated LEAP Wave 12 table ledger.

This is not an HTML extractor, respondent-data reader, network collector or
canonical importer. Manually supplied provenance is preserved, not authenticated
by a hash. Exact decimal strings avoid binary-float rounding. Four published
group summaries stay separate; no pooled forecast or participant sum is made.
"""
from __future__ import annotations
import argparse
import copy
from datetime import date, datetime
from decimal import Decimal, localcontext
import hashlib
import json
import os
import stat
from pathlib import Path
import re

MAX_BYTES = 32768
MAX_MANIFEST_BYTES = 8192
MAX_NODES = 1000
MAX_DEPTH = 12
MAX_DECIMAL_DIGITS = 32
SOURCE_URL = 'https://leap.forecastingresearch.org/reports/wave12'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
QUESTION_ID = 'leap-ai-catastrophe-by-2050-unconditional'
GROUPS = ('Expert', 'Public', 'Superforecaster', 'AI Risk Expert')
INSTRUMENT_SHA256 = '0ae58e0dce6de95247819a3ebbfd78be96602cc1ff0bdb418ceec03e4117b97a'
INTERPRETATION = {
    'statistic_type': 'published_group_forecast_summary',
    'interval_type': 'respondent_interquartile_range',
    'reported_n_role': 'reported_cell_n_semantics_not_fully_established',
    'weighting_provenance': 'unknown',
    'group_overlap': 'unknown',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def exact_keys(obj, keys, role):
    require(type(obj) is dict and set(obj) == set(keys), 'Invalid '+role+' fields')


def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def sha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'Invalid SHA256')
    return value


def strict_json(raw, limit):
    require(type(raw) is bytes and 0 < len(raw) <= limit, 'Input must be bounded nonempty bytes')
    def pairs(values):
        out = {}
        for k, v in values:
            require(k not in out, 'Duplicate JSON key')
            out[k] = v
        return out
    def no_float(token):
        raise ValueError('Decimals must be source strings; nonfinite/floating JSON numbers forbidden')
    def integer(token):
        require(len(token) <= 10, 'Integer token too long')
        return int(token)
    try:
        out = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                         parse_constant=no_float, parse_float=no_float, parse_int=integer)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON') from exc
    stack = [(out, 0)]; nodes = 0
    while stack:
        value, depth = stack.pop(); nodes += 1
        require(nodes <= MAX_NODES and depth <= MAX_DEPTH, 'JSON structure exceeds bounds')
        if type(value) is dict:
            require(all(len(k) <= 128 and not any(0xD800 <= ord(c) <= 0xDFFF for c in k) for k in value), 'Invalid or overlong key')
            stack.extend((v, depth + 1) for v in value.values())
        elif type(value) is list:
            stack.extend((v, depth + 1) for v in value)
        elif type(value) is str:
            require(len(value) <= 16000 and not any((ord(c) < 32 and c not in '\n\t') or 0xD800 <= ord(c) <= 0xDFFF for c in value), 'Invalid source string')
    return out


def percent(value):
    require(type(value) is str and 0 < len(value) <= MAX_DECIMAL_DIGITS
            and re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value), 'Strict decimal percentage string required')
    number = Decimal(value)
    require(0 <= number <= 100, 'Percentage outside 0–100')
    with localcontext() as context:
        context.prec = MAX_DECIMAL_DIGITS + 4
        normalized = format(number / Decimal(100), 'f')
    return number, normalized


def text(value, role):
    require(type(value) is str and value.strip() and len(value) <= 16000, role+' text required')


def iso_date(value):
    require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'ISO date required')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('Invalid calendar date') from exc


def timestamp(value):
    require(type(value) is str and len(value) <= 40, 'Timezone-qualified retrieval timestamp required')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid retrieval timestamp') from exc
    require(parsed.tzinfo is not None and 'T' in value, 'Retrieval timezone required')
    return parsed


def definition_version(instrument):
    return 'leap-definition:'+digest(instrument)


def normalize_ledger(raw, manifest):
    exact_keys(manifest, ('source_url','original_page_sha256','original_page_bytes',
        'original_hash_basis','derivative_sha256','retrieved_at','license_identifier',
        'license_url','attribution','transformation_notice'), 'manifest')
    require(manifest['source_url'] == SOURCE_URL, 'Only reviewed Wave 12 URL allowed')
    require(manifest['license_identifier'] == 'CC-BY-4.0' and manifest['license_url'] == LICENSE_URL, 'Scoped report license required')
    require(manifest['original_hash_basis'] == 'exact_downloaded_html_body', 'Original hash must describe original bytes')
    require(type(manifest['original_page_bytes']) is int and 0 < manifest['original_page_bytes'] <= 2*1024*1024, 'Original page bound')
    original_hash = sha(manifest['original_page_sha256'])
    derivative_hash = sha(manifest['derivative_sha256'])
    require(original_hash != derivative_hash, 'Original page and derivative hashes must stay distinct')
    retrieved = timestamp(manifest['retrieved_at'])
    for key in ('attribution','transformation_notice'):
        text(manifest[key],key)
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'Ledger byte bound')
    require(hashlib.sha256(raw).hexdigest() == derivative_hash, 'Derivative hash mismatch')
    data = strict_json(raw, MAX_BYTES)
    exact_keys(data, ('schema_version','study','wave','instrument','dates','wave_counts',
                     'interpretation','records'), 'ledger')
    require(data['schema_version'] == 'leap-wave12-aggregate-ledger/1.0.0'
            and data['study'] == 'LEAP' and type(data['wave']) is int and data['wave'] == 12, 'Study/wave/schema selection')
    instrument = data['instrument']
    exact_keys(instrument, ('question_id','condition_key','horizon_year','question_text',
                           'shared_background','event_definition','causation_criteria','shared_policy_conditions',
                           'selected_condition_text','horizon_date','event_window'), 'instrument')
    require(instrument['question_id'] == QUESTION_ID and instrument['condition_key'] == 'unconditional'
            and type(instrument['horizon_year']) is int and instrument['horizon_year'] == 2050, 'Wrong question/condition/horizon')
    for key in ('question_text','shared_background','event_definition','causation_criteria','shared_policy_conditions','selected_condition_text'):
        text(instrument[key], key)
    require(instrument['horizon_date'] == '2050-12-31', 'Exact horizon date required')
    require(type(instrument['event_window']) is dict, 'Event window required')
    require(digest(instrument) == INSTRUMENT_SHA256, 'Unreviewed instrument definition; review and version explicitly')
    require(data['interpretation'] == INTERPRETATION, 'Summary/interval/denominator/weight/overlap meaning changed')
    dates = data['dates']
    exact_keys(dates, ('fieldwork_start','fieldwork_end','publication_date','publication_date_status',
                      'aggregate_generated_at_source','aggregate_generated_at','aggregate_generated_timezone',
                      'publication_source_field','source_revision_date_status'), 'dates')
    start,end = iso_date(dates['fieldwork_start']),iso_date(dates['fieldwork_end'])
    require(start <= end <= retrieved.date(), 'Fieldwork chronology')
    if dates['publication_date'] is None:
        require(dates['publication_date_status'] == 'not_reported', 'Unknown publication date reason required')
    else:
        require(dates['publication_date_status'] == 'reported', 'Publication date status mismatch')
        published = iso_date(dates['publication_date'])
        require(end <= published <= retrieved.date(), 'Publication chronology')
    text(dates['aggregate_generated_at_source'], 'Source export timestamp')
    generated = timestamp(dates['aggregate_generated_at'])
    require(dates['aggregate_generated_timezone'] == 'UTC' and generated.utcoffset().total_seconds() == 0, 'Source explicitly reports UTC')
    require(generated.second == 0 and generated.microsecond == 0, 'Source export clock has minute precision')
    require(dates['aggregate_generated_at_source'] == generated.strftime('%Y-%m-%d %H:%M UTC'), 'Source and normalized export clocks disagree')
    require(end <= generated.date() and generated <= retrieved, 'Aggregate export chronology')
    require(dates['publication_date'] is None or generated.date() <= published, 'Export after first publication')
    require(dates['publication_source_field'] == 'First released on; embedded lastUpdated', 'Publication field provenance')
    require(dates['source_revision_date_status'] == 'not_separately_reported', 'Do not invent revision clock')
    counts = data['wave_counts']
    exact_keys(counts, ('reported_expert_overall_n','reported_expert_category_counts','derived_expert_category_sum','category_label_normalization','discrepancy_status'), 'wave counts')
    require(type(counts['reported_expert_overall_n']) is int and counts['reported_expert_overall_n'] == 157
            and type(counts['derived_expert_category_sum']) is int and counts['derived_expert_category_sum'] == 149
            and counts['reported_expert_category_counts'] == {'computer_scientists':25,'industry_professionals':34,'economists':38,'policy_think_tank_staff':52}
            and all(type(v) is int for v in counts['reported_expert_category_counts'].values())
            and counts['category_label_normalization'] == 'descriptive_snake_case_not_native_ids'
            and counts['discrepancy_status'] == 'unresolved_source_discrepancy', 'Retain 157-versus-149 discrepancy')
    rows = data['records']
    require(type(rows) is list and len(rows) == 4, 'Exactly four published group cells required')
    require([r.get('group_label') if type(r) is dict else None for r in rows] == list(GROUPS), 'Exact group labels/order required')
    version = definition_version(instrument)
    out = []
    for row in rows:
        exact_keys(row, ('group_label','median_percent','q25_percent','q75_percent',
                         'reported_n','reported_n_missing_reason','source_locator','weighting_context'), 'group record')
        q25,p25 = percent(row['q25_percent']); median,pm = percent(row['median_percent']); q75,p75 = percent(row['q75_percent'])
        require(q25 <= median <= q75, 'Unordered respondent quartiles')
        if row['reported_n'] is None:
            require(row['reported_n_missing_reason'] in ('not_reported','not_retrieved','definition_unclear'), 'Missing n needs reason; no wave-total substitution')
        else:
            require(type(row['reported_n']) is int and 0 < row['reported_n'] <= 1000000 and row['reported_n_missing_reason'] is None, 'Invalid reported cell n')
        text(row['source_locator'], 'Source table locator')
        weighting = row['weighting_context']
        exact_keys(weighting, ('general_methodology_status','wave12_cell_specific_method_verified','source_url','description'), 'weighting context')
        expected_weighting = dict(zip(GROUPS, ('reweighted','reweighted','unweighted','unknown')))
        require(weighting['general_methodology_status'] == expected_weighting[row['group_label']]
                and weighting['wave12_cell_specific_method_verified'] is False, 'Do not assume Wave 12-specific weighting')
        require(weighting['source_url'] == 'https://forecastingresearch.org/research/longitudinal-expert-ai-panel-leap-working-paper', 'Weighting source')
        text(weighting['description'], 'Weighting description')
        stable = 'leap:w12:'+QUESTION_ID+':'+row['group_label']
        item = copy.deepcopy(row)
        item.update(observation_id=stable, definition_version=version,
                    result_version_id='leap-result:'+digest([stable,version,original_hash,derivative_hash]),
                    probability_median=pm, probability_q25=p25, probability_q75=p75,
                    unit='probability', source_unit='percent', interpretation=copy.deepcopy(INTERPRETATION),
                    question=copy.deepcopy(instrument), dates=copy.deepcopy(dates),
                    provenance=copy.deepcopy(manifest), review_state='manual_source_transcription_offline_validated')
        out.append(item)
    return dict(schema_version='leap-published-aggregate-output/1.0.0', records=out,
                wave_counts=copy.deepcopy(counts), source_revision=original_hash,
                derivative_revision=derivative_hash, collector_enabled=False,
                canonical_import=False, source_extraction_implemented=False)


def read_fixture(directory):
    """Descriptor-relative regular-file reads; reject symlink ancestors and traversal.

    Safe POSIX opening is required. A file replacement cannot make a FIFO block:
    O_NONBLOCK precedes fstat, and the opened descriptor must be a regular file.
    Filesystem mount locality is not established by this offline reader.
    """
    try:
        path = os.fspath(directory)
    except TypeError as exc:
        raise ValueError('Local directory path required') from exc
    require(type(path) is str and 0 < len(path) <= 4096 and '://' not in path
            and '\\' not in path and not path.startswith('//') and path != '-'
            and not any(ord(c) < 32 or ord(c) == 127 for c in path), 'Invalid directory path')
    try:
        require(len(path.encode('utf-8')) <= 4096, 'Directory path byte bound')
    except UnicodeEncodeError as exc:
        raise ValueError('Directory path must be UTF8') from exc
    parts = [x for x in path.split('/') if x not in ('', '.')]
    require('..' not in parts and len(parts) <= 64, 'Parent traversal or excessive path depth')
    require(os.name == 'posix' and all(hasattr(os,k) for k in ('O_NOFOLLOW','O_DIRECTORY','O_NONBLOCK')), 'Safe regular-file opening unavailable')
    fd = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open('/' if path.startswith('/') else '.', flags)
        for part in parts:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd); fd = child
        def read(name, limit):
            child = None
            try:
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os,'O_NOCTTY',0), dir_fd=fd)
                info = os.fstat(child)
                require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit, 'Bounded regular fixture file required')
                with os.fdopen(child, 'rb') as stream:
                    child = None
                    raw = stream.read(limit + 1)
                require(0 < len(raw) <= limit, 'Fixture file exceeds bound')
                return raw
            finally:
                if child is not None:
                    os.close(child)
        manifest = strict_json(read('manifest.json', MAX_MANIFEST_BYTES), MAX_MANIFEST_BYTES)
        return normalize_ledger(read('leap-wave12-catastrophe2050.json', MAX_BYTES), manifest)
    except (OSError, UnicodeError) as exc:
        raise ValueError('Cannot read no-symlink regular fixture files') from exc
    finally:
        if fd is not None:
            os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture_directory', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(read_fixture(args.fixture_directory), indent=2, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, 'LEAP ledger validation failed: '+str(exc)+'\n')


if __name__ == '__main__':
    main()
