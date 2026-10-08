"""Bounded offline JSON-stat reader for one German ICT-training population.

No fetching, execution, filesystem writes or canonical admission. External labels
and annotations are inert data. The CLI reads only the two fixed fixture names
under an explicitly supplied directory; bytes API supports separately reviewed
snapshots. No status, uncertainty or reference-year imputation. Decimal tokens must be at
most 64 characters and preserve exact decimal value through JSON number
serialization; precision loss, overflow and underflow are rejected, never rounded.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re

MAX_BYTES = 32768
MAX_MANIFEST_BYTES = 4096
MAX_NODES = 4000
MAX_DEPTH = 16
TABLE = 'ISOC_SKE_ITTN2'
DIMENSIONS = {'freq': 'A', 'size_emp': 'GE10', 'nace_r2': 'C10-S951_X_K',
              'indic_is': 'E_ITT2', 'unit': 'PC_ENT', 'geo': 'DE'}
YEARS = tuple(str(y) for y in range(2012, 2025))
SOURCE_URL = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_ske_ittn2?lang=en&geo=DE&size_emp=GE10&nace_r2=C10-S951_X_K&indic_is=E_ITT2&unit=PC_ENT'
RIGHTS_URL = 'https://ec.europa.eu/eurostat/web/main/help/copyright-notice'
REFERENCE_URL = 'https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/40327.pdf'
ATTRIBUTION = 'Source: Eurostat, isoc_ske_ittn2, Germany; retrieved 8 October 2026. Normalized by pdoom.live; Eurostat has not endorsed this work.'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def strict_json(raw, limit):
    require(type(raw) is bytes and 0 < len(raw) <= limit, 'Input must be bounded nonempty bytes')
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, 'Duplicate JSON key')
            out[k] = v
        return out
    def constant(value):
        raise ValueError('Nonfinite JSON number')
    def decimal_number(token):
        # JSON decimal values must round-trip numerically without losing digits.
        # 31.20 -> 31.2 preserves its exact decimal value; underflow and 100+epsilon do not.
        require(len(token) <= 64, 'Numeric token exceeds precision bound')
        exact = Decimal(token)
        number = float(exact)
        require(math.isfinite(number) and Decimal(str(number)) == exact, 'Numeric precision loss or underflow')
        return number
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant, parse_float=decimal_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError, InvalidOperation) as exc:
        raise ValueError('Invalid JSON') from exc
    stack = [(value, 0)]; count = 0
    while stack:
        node, depth = stack.pop(); count += 1
        require(count <= MAX_NODES and depth <= MAX_DEPTH, 'JSON structure exceeds bounds')
        if isinstance(node, dict):
            stack.extend((v, depth + 1) for v in node.values())
        elif isinstance(node, list):
            stack.extend((v, depth + 1) for v in node)
        elif type(node) is int:
            require(abs(node) <= 10**20, 'Integer exceeds parser bound')
        elif isinstance(node, float):
            require(math.isfinite(node), 'Nonfinite JSON number')
        elif isinstance(node, str):
            require(len(node) <= 4096, 'Overlong source string')
    return value


def timestamp(value):
    require(isinstance(value, str) and len(value) <= 40, 'Timestamp string required')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid timestamp') from exc
    require(dt.tzinfo is not None, 'Timestamp timezone required')
    return value


def indexed_cells(value, total, status=False):
    require(isinstance(value, (dict, list)), 'Cell array or sparse index map required')
    if isinstance(value, list):
        require(len(value) == total, 'Dense cell count mismatch')
        items = enumerate(value)
    else:
        require(all(isinstance(k, str) and re.fullmatch(r'0|[1-9][0-9]*', k) for k in value), 'Invalid sparse index')
        require(all(int(k) < total for k in value), 'Sparse index out of range')
        items = ((int(k), v) for k, v in value.items())
    out = {}
    for k, v in items:
        if status:
            require(v is None or (isinstance(v, str) and len(v) <= 32 and not any(ord(c) < 32 for c in v)), 'Invalid observation status')
        else:
            require(v is None or (type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 100), 'Invalid percentage')
        out[k] = v
    return out


def normalize_slice(raw, manifest):
    require(type(manifest) is dict and set(manifest) == {'source_url', 'retrieved_at', 'sha256'}, 'Exact manifest schema required')
    require(manifest['source_url'] == SOURCE_URL, 'Only the reviewed filtered Eurostat query is allowed')
    retrieved = timestamp(manifest['retrieved_at'])
    require(isinstance(manifest['sha256'], str) and re.fullmatch('[0-9a-f]{64}', manifest['sha256']), 'SHA256 required')
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'Input byte bound')
    digest = hashlib.sha256(raw).hexdigest()
    require(digest == manifest['sha256'], 'Snapshot hash mismatch')
    data = strict_json(raw, MAX_BYTES)
    require(type(data) is dict and set(data) <= {'version', 'class', 'label', 'source', 'updated', 'value', 'status', 'id', 'size', 'dimension', 'extension'}, 'Unsupported root schema')
    require(data.get('version') == '2.0' and data.get('class') == 'dataset' and data.get('source') == 'ESTAT', 'Unsupported JSON-stat source/version/class')
    require(isinstance(data.get('label'), str) and data['label'], 'Dataset label required')
    updated = timestamp(data.get('updated'))
    ids, sizes, dims = data.get('id'), data.get('size'), data.get('dimension')
    require(type(ids) is list and len(ids) == 7 and all(isinstance(k,str) for k in ids) and set(ids) == set(DIMENSIONS) | {'time'}, 'Exact dimensions required')
    require(type(sizes) is list and len(sizes) == 7 and all(type(n) is int and 0 < n <= 13 for n in sizes), 'Invalid dimension sizes')
    require(type(dims) is dict and set(dims) == set(ids), 'Dimension metadata mismatch')
    categories = {}; labels = {}; total = math.prod(sizes)
    require(total <= 13, 'Additional populations are forbidden')
    for name, size in zip(ids, sizes):
        dim = dims[name]
        require(type(dim) is dict and set(dim) == {'label', 'category'} and isinstance(dim['label'], str), 'Unsupported dimension schema')
        cat = dim['category']
        require(type(cat) is dict and set(cat) == {'index', 'label'}, 'Unsupported category schema')
        index = cat['index']; label = cat['label']
        if type(index) is list:
            require(len(index) == size and all(isinstance(k,str) for k in index) and len(set(index)) == size, 'Category array must be a bijection')
            index = {code: i for i, code in enumerate(index)}
        require(type(index) is dict and len(index) == size and all(type(i) is int for i in index.values()) and set(index.values()) == set(range(size)), 'Category index must be a bijection')
        require(type(label) is dict and set(label) == set(index) and all(isinstance(v,str) for v in label.values()), 'Category labels mismatch')
        if name == 'time':
            require(set(index) <= set(YEARS), 'Survey year outside reviewed 2012–2024 range')
        else:
            require(size == 1 and set(index) == {DIMENSIONS[name]}, 'Additional or altered population is forbidden')
        categories[name] = [k for k, _ in sorted(index.items(), key=lambda x:x[1])]
        labels[name] = {'dimension_label': dim['label'], 'category_labels': label}
    ext = data.get('extension')
    require(type(ext) is dict and set(ext) <= {'lang','id','agencyId','version','datastructure','annotation','positions-with-no-data'}, 'Unsupported extension schema')
    require(ext.get('id') == TABLE and ext.get('agencyId') == 'ESTAT' and ext.get('lang') == 'EN' and ext.get('version') == '1.0', 'Wrong table/agency/language/extension version')
    require(ext.get('datastructure') == {'id':TABLE,'agencyId':'ESTAT','version':'43.0'}, 'Unreviewed data structure version')
    require(type(ext.get('annotation')) is list and len(ext['annotation']) <= 32 and all(type(a) is dict for a in ext['annotation']), 'Invalid annotations')
    no_data = ext.get('positions-with-no-data')
    require(type(no_data) is dict and set(no_data) == set(ids) and all(type(v) is list and len(v) <= 13 for v in no_data.values()), 'Invalid no-data positions')
    require(all(all(type(i) is int and 0 <= i < sizes[ids.index(k)] for i in v) for k,v in no_data.items()), 'Invalid no-data position index')
    # Preserve the upstream extension unchanged, but never execute/follow annotation XML or links.
    values = indexed_cells(data.get('value'), total)
    statuses = indexed_cells(data['status'], total, True) if 'status' in data else {}
    records = []
    for flat in range(total):
        position = flat; coordinates = {}
        for name, size in reversed(list(zip(ids, sizes))):
            coordinates[name] = categories[name][position % size]; position //= size
        year = coordinates['time']; value = values.get(flat)
        stable_key = 'eurostat:' + TABLE + ':' + ':'.join(DIMENSIONS[k] for k in DIMENSIONS) + ':' + year
        records.append({'observation_key': stable_key, 'snapshot_key': stable_key + ':sha256:' + digest,
            'dimensions': coordinates, 'survey_year': int(year), 'value': value,
            'value_state': 'absent_sparse_cell' if flat not in values else ('explicit_null' if value is None else 'observed'),
            'unit': 'percentage_of_enterprises', 'status': statuses.get(flat),
            'status_state': 'absent_member' if 'status' not in data else ('absent_cell' if flat not in statuses else ('explicit_null' if statuses[flat] is None else 'reported')),
            'training_reference_year': 2023 if year == '2024' else None,
            'reference_year_verification': 'documented_for_2024_survey' if year == '2024' else 'unknown_unverified_questionnaire',
            'reference_year_source_url': REFERENCE_URL if year == '2024' else None,
            'uncertainty': None, 'measurement_class': 'reported_enterprise_ict_training', 'ai_specific': False})
    records.sort(key=lambda r:r['survey_year'])
    return {'schema_version':'eurostat-ict-training-slice/1.0.0', 'parent_inventory_source_id':'GL022',
        'table': TABLE, 'source_url':SOURCE_URL, 'retrieved_at':retrieved, 'source_sha256':digest,
        'upstream_updated_at':updated, 'jsonstat_version':'2.0', 'datastructure_version':'43.0',
        'source_dimension_order':ids, 'source_sizes':sizes, 'source_dimension_labels':labels,
        'source_extension':ext, 'source_status_member_present':'status' in data,
        'population':'German enterprises with 10 or more employed persons; C10-S951_X_K; NACE Rev.2 scope as documented for each survey year',
        'comparability_warnings':['Activity coverage changed in 2021, including veterinary activities; unchanged broad codes do not imply unchanged populations.',
          'General ICT training is not AI-specific training, worker counts, hours, acquired competence or effectiveness.',
          'Aggregate training/AI-use alignment cannot identify the same enterprises or a causal AI effect.'],
        'missing_survey_years':[int(y) for y in YEARS if y not in categories['time']],
        'rights':{'status':'statistical_data_reuse_with_attribution', 'scope':'Selected German EU statistical-data slice only; third-party exceptions retained', 'url':RIGHTS_URL,
                  'attribution':'Source: Eurostat, isoc_ske_ittn2, Germany. Snapshot retrieval: ' + retrieved + '. Normalized by pdoom.live; Eurostat is not responsible for adaptations and does not endorse this work.'},
        'operational_admission':'not_admitted', 'collector_enabled':False, 'records':records}


def read_fixture(directory):
    root = Path(directory)
    require(root.is_dir() and not root.is_symlink(), 'Fixture directory must be a real directory')
    # Only fixed local filenames, with no symlink traversal in any path component.
    root = root.absolute()
    require(not any(p.is_symlink() for p in [root, *root.parents]), 'Symlink path components forbidden')
    require('..' not in root.parts, 'Parent traversal forbidden')
    def bounded(name, limit):
        p = root / name
        require(p.is_file() and not p.is_symlink(), 'Fixture must be a regular local file')
        with p.open('rb') as f:
            raw = f.read(limit + 1)
        require(len(raw) <= limit, 'File exceeds byte bound')
        return raw
    raw = bounded('de-ict-training.json', MAX_BYTES)
    manifest = strict_json(bounded('manifest.json', MAX_MANIFEST_BYTES), MAX_MANIFEST_BYTES)
    return normalize_slice(raw, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture_directory')
    args = parser.parse_args()
    print(json.dumps(read_fixture(args.fixture_directory), indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
