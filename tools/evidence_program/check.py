#!/usr/bin/env python3
"""Offline repository checks for the evidence program; never ingests or fetches.

Run from any directory: python tools/evidence_program/check.py
Optional --base-tree supplies GitHub tree JSON for checking an overlay without a
checkout. CI must omit it so documentation links resolve against the real tree.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / 'data/evidence-program'
DOCS = ROOT / 'docs/evidence-program'
BASELINE = 'f5274396885dbb654fc2861a78fa5be8f42fad38'
SOURCE_IDS = {f'GL{i:03}' for i in range(1, 41)} | {f'CN{i:03}' for i in range(1, 25)}
COUNTS = {'source_families': 64, 'contract_regression_tests': 71, 'chinese_cases': 25,
          'chinese_fragments': 41, 'alias_entries': 23, 'methodology_arithmetic_checks': 19}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check_url(value):
    require(isinstance(value, str), f'URL is not a string: {value!r}')
    parsed = urlsplit(value)
    require(parsed.scheme in {'https', 'http'} and bool(parsed.hostname)
            and parsed.username is None and parsed.password is None
            and not any(c.isspace() for c in value), f'Invalid URL: {value!r}')


def check_sources(inventory, global_rows, chinese_rows):
    rows = global_rows + chinese_rows
    ids = [r['source_id'] for r in rows]
    require(len(ids) == 64 and set(ids) == SOURCE_IDS, 'Expected unique GL001–GL040 / CN001–CN024')
    require(inventory['records'] == rows, 'Combined inventory differs from source partitions')
    require(len({r['primary_url'] for r in rows}) == len(rows), 'Duplicate primary source URL')
    fields = {'source_id', 'name', 'institution_region', 'languages', 'evidence_layer', 'primary_url',
              'data_url', 'access_method', 'available_content', 'historical_coverage', 'rights_status',
              'rights_url', 'rights_notes', 'verification_status', 'verified_date', 'collection_status',
              'priority', 'next_action', 'caveats'}
    for row in rows:
        require(fields <= row.keys(), f"Missing fields: {row.get('source_id')}")
        require(row['collection_status'] == 'candidate_not_collected', 'Inventory must not claim collection')
        require(row['rights_status'] in {'explicit-license', 'terms-restricted', 'unknown'}, 'Unknown rights status')
        require(row['verification_status'] in {'opened-primary', 'documentation-only', 'access-blocked'}, 'Unknown verification status')
        require(row['priority'] in {'P0', 'P1', 'P2'}, 'Unknown priority')
        require(row['languages'] and all(isinstance(v, str) for v in row['languages']), 'Missing language list')
        for key in fields - {'data_url', 'rights_url', 'languages'}:
            require(isinstance(row[key], str) and row[key].strip(), f"Invalid {key}: {row['source_id']}")
        for key in ['primary_url', 'data_url', 'rights_url']:
            if row[key] is not None:
                check_url(row[key])


def check_coverage(inventory, mapping, metrics, references):
    require(len(mapping) == 64 and {r['source_id'] for r in mapping} == SOURCE_IDS, 'Coverage IDs do not match inventory')
    require(inventory['repository_coverage'] == mapping, 'Combined inventory coverage diverges')
    require(inventory['coverage_baseline'] == metrics, 'Combined inventory baseline diverges')
    require(metrics['baseline_commit'] == references['baseline_commit'] == BASELINE, 'Audit baseline changed without review')
    prefix = f'https://github.com/mishakgg/pdoom-live/blob/{BASELINE}/'
    allowed = {r['url'] for r in references['references']}
    used = set()
    for ref in references['references']:
        require(ref['url'].startswith(prefix) and unquote(urlsplit(ref['url']).path.split('/blob/'+BASELINE+'/', 1)[1]) == ref['path'], 'Coverage reference URL/path mismatch')
        require(re.fullmatch(r'[0-9a-f]{40}', ref['git_blob_sha']), 'Invalid historical Git blob hash')
        require(not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts, 'Unsafe coverage path')
    names = {r['source_id']: r['name'] for r in inventory['records']}
    for row in mapping:
        require(row['name'] == names[row['source_id']], 'Coverage name mismatch')
        require(row['artifact_links'], 'Coverage entry has no evidence links')
        for link in row['artifact_links']:
            check_url(link)
            require(link in allowed, f'Unrecognized pinned coverage link: {link}')
            used.add(link)
    for row in metrics['metrics']:
        require(row['source_url'] in allowed, 'Metric source missing from pinned references')
        used.add(row['source_url'])
        require(row['unit'] and row['scope'] and row['interpretation'], 'Metric lacks interpretation')
        require(row['value'] >= 0, 'Negative count metric')
        if row.get('denominator') is not None:
            require(row['denominator'] > 0 and row['value'] <= row['denominator'], 'Invalid metric denominator')
    require(used == allowed, 'Unreferenced/missing pinned coverage reference')


def csv_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return '' if value is None else str(value)


def check_csv(path, rows):
    with path.open(encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        actual = list(reader)
        fields = reader.fieldnames
    require(bool(fields), f'Empty CSV: {path.name}')
    expected = [{key: csv_value(row.get(key)) for key in fields} for row in rows]
    require(actual == expected, f'CSV diverges from JSON: {path.name}')


def schema_for_fragment(schema, path):
    """Resolve the actual field path; old/new benchmark names are fixture labels."""
    parts = path.split('.')
    if parts[0] in {'old_benchmark_run', 'new_benchmark_run'}:
        parts[0] = 'benchmark_run'
    if parts[0] == 'times':
        node = schema['$defs']['times']
        parts = parts[1:]
    else:
        require(len(parts) >= 3 and parts[1] == 'data', f'Unsupported fragment path: {path}')
        node = schema['$defs'].get(parts[0] + '_data')
        require(node is not None, f'Unknown record type: {path}')
        parts = parts[2:]
    for part in parts:
        while '$ref' in node:
            ref = node['$ref']
            require(ref.startswith('#/$defs/'), 'Nonlocal schema reference')
            node = schema['$defs'][ref.rsplit('/', 1)[1]]
        require(part in node.get('properties', {}), f'Unknown schema field: {path}')
        node = node['properties'][part]
    return dict(node, **{'$defs': schema['$defs']})


def check_chinese(aliases, lexicon, cases, schema, validator, format_checker):
    cn_ids = {sid for sid in SOURCE_IDS if sid.startswith('CN')}
    require(aliases['human_review_required'] is True and aliases['policy']['automatic_merging_allowed'] is False, 'Alias policy weakened')
    entries = aliases['entries']
    require(len(entries) == 23 and len({e['lookup_key'] for e in entries}) == 23, 'Alias entry count/keys changed')
    for entry in entries:
        require(entry['human_review_required'] is True and entry['automatic_merge_allowed'] is False, 'Alias review/merge guard weakened')
        require(set(entry['source_ids']) <= cn_ids, 'Alias refers to unknown source ID')
        if entry['entry_class'] != 'verified_mapping':
            require(not entry['verified_mappings'], 'Unresolved alias has verified mappings')
        for evidence in entry.get('evidence', []):
            check_url(evidence['url'])
    require(len(lexicon['concepts']) == 30 and len(lexicon['query_templates']) == 14, 'Lexicon counts changed')
    for query in lexicon['query_templates']:
        require(query['source_ids'] and set(query['source_ids']) <= cn_ids, 'Query refers to unknown source ID')
    require(cases['synthetic'] is True and cases['status'] == 'preparation_only_not_production_records', 'Chinese fixture isolation weakened')
    require(len(cases['cases']) == 25 and {c['case_id'] for c in cases['cases']} == {f'ZH{i:03}' for i in range(1, 26)}, 'Chinese case IDs/count changed')
    fragments = 0
    for case in cases['cases']:
        require(case['synthetic'] is True and case['expected']['requires_human_review'] is True, 'Chinese case guard weakened')
        source = case['input']['original_text']
        span = case['input']['quote_span']
        require(span['coordinate_system'] == 'unicode_codepoints_zero_based_half_open', 'Unexpected span coordinates')
        require(isinstance(span['start'], int) and isinstance(span['end'], int)
                and 0 <= span['start'] < span['end'] <= len(source), 'Invalid Chinese span range')
        require(source[span['start']:span['end']] == span['text'], 'Chinese code-point span does not match original')
        for fragment in case['expected'].get('contract_fragments', []):
            field = schema_for_fragment(schema, fragment['path'])
            if 'schema_definition' in fragment:
                require(field.get('$ref') == '#/$defs/' + fragment['schema_definition'], 'Fragment shortcut does not match actual schema path')
            errors = list(validator(field, format_checker=format_checker).iter_errors(fragment['value']))
            require(not errors, f"Invalid fragment {case['case_id']} {fragment['path']}: " + '; '.join(e.message for e in errors))
            fragments += 1
    require(fragments == 41, 'Chinese fragment count changed')
    return fragments


def check_task_plan(plan, recipes, markdown, base_paths=None):
    """Check planning references and dependencies, never execute the task pack."""
    require(re.fullmatch(r'implementation-plan/\d+\.\d+\.\d+', plan.get('plan_version', '')),
            'Invalid implementation plan version')
    require(plan.get('status') == 'proposed_unexecuted_plan', 'Task pack must remain an unexecuted plan')
    require(re.fullmatch(r'[0-9a-f]{40}', plan.get('baseline_commit', '')),
            'Invalid task baseline commit')
    require(plan.get('audit_baseline_commit') == BASELINE, 'Task audit baseline mismatch')
    require(isinstance(plan.get('execution_policy'), str) and plan['execution_policy'].strip(),
            'Task execution policy missing')
    require(isinstance(plan.get('global_boundaries'), list) and plan['global_boundaries']
            and all(isinstance(v, str) and v.strip() for v in plan['global_boundaries']),
            'Task global boundaries missing')
    known_recipes = {recipe['id'] for recipe in recipes['recipes']}

    def unique_strings(values, label):
        require(isinstance(values, list) and all(isinstance(v, str) and v.strip() for v in values),
                f'{label} must be a list of nonempty strings')
        require(len(values) == len(set(values)), f'Duplicate {label}')
        return set(values)

    require(unique_strings(plan.get('source_ids'), 'task-pack source IDs') == SOURCE_IDS,
            'Task-pack source IDs differ from inventory')
    require(unique_strings(plan.get('recipes'), 'task-pack recipe IDs') == known_recipes,
            'Task-pack recipe IDs differ from methodology')
    tasks = plan.get('tasks')
    require(isinstance(tasks, list) and tasks, 'Task pack has no tasks')
    ids = []
    existing_paths = set()
    proposed_paths = set()
    for task in tasks:
        require(isinstance(task, dict) and re.fullmatch(r'EP[0-9]{2,}', task.get('id', '')),
                'Invalid implementation task ID')
        ids.append(task['id'])
        for field in ['title', 'phase', 'owner_role', 'scope', 'authorization_gate']:
            require(isinstance(task.get(field), str) and task[field].strip(),
                    f"Task {task['id']} missing {field}")
        require(task.get('priority') in {'P0', 'P1', 'P2'}, 'Invalid task priority')
        require(task.get('status') in {'planned', 'deferred'}, 'Task falsely claims execution')
        unique_strings(task.get('depends_on'), 'task dependencies')
        require(unique_strings(task.get('source_ids'), 'task source IDs') <= SOURCE_IDS,
                'Task refers to unknown source ID')
        require(unique_strings(task.get('recipe_ids'), 'task recipe IDs') <= known_recipes,
                'Task refers to unknown recipe ID')
        unique_strings(task.get('non_goals'), 'task non-goals')
        for field in ['acceptance_tests', 'completion_evidence']:
            require(unique_strings(task.get(field), field), f'Task missing {field}')
        for field in ['existing_paths', 'proposed_paths']:
            paths = unique_strings(task.get(field), field)
            for value in paths:
                path = Path(value)
                require(value != '.' and not path.is_absolute() and value == path.as_posix() and
                        '..' not in path.parts and ':' not in value and '\\' not in value,
                        f'Unsafe task path: {value}')
                resolved = (ROOT / path).resolve()
                require(resolved.is_relative_to(ROOT), f'Task path escapes repository: {value}')
                if field == 'existing_paths':
                    require(resolved.exists() or (base_paths is not None and value in base_paths),
                            f'Task existing path not found: {value}')
            (existing_paths if field == 'existing_paths' else proposed_paths).update(paths)
    require(len(ids) == len(set(ids)), 'Duplicate implementation task ID')
    require(not (existing_paths & proposed_paths), 'Task path classified as both existing and proposed')
    by_id = {task['id']: task for task in tasks}
    for task in tasks:
        require(set(task['depends_on']) <= by_id.keys(), 'Task depends on unknown task')
        require(task['id'] not in task['depends_on'], 'Task depends on itself')
    active, visited = set(), set()

    def visit(task_id):
        require(task_id not in active, 'Task dependency cycle')
        if task_id in visited:
            return
        active.add(task_id)
        for dependency in by_id[task_id]['depends_on']:
            visit(dependency)
        active.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id)
    headings = re.findall(r'^## (EP[0-9]{2,}) (.+)$', markdown, flags=re.MULTILINE)
    require(len(headings) == len(ids) and len({item[0] for item in headings}) == len(ids),
            'Task documentation heading count/IDs mismatch')
    require(dict(headings) == {task['id']: task['title'] for task in tasks},
            'Task documentation IDs/titles differ from JSON')
    # Proposed paths describe the historical baseline. Do not require them to
    # remain absent forever: later, authorized implementations may create them.
    return {'implementation_tasks': len(tasks),
            'planned_implementation_tasks': sum(t['status'] == 'planned' for t in tasks),
            'deferred_implementation_tasks': sum(t['status'] == 'deferred' for t in tasks)}


def check_research_catalog(catalog, inventory_hash, markdown):
    """Validate research metadata only; no retrieval, admission or adapter execution."""
    require(catalog.get('catalog_version') == 'chinese-safety-research/1.0.0', 'Unknown research catalog version')
    require(catalog.get('catalog_state') == 'research_only_not_admitted' and
            catalog.get('operational_admission') == 'not_admitted' and
            catalog.get('collector_enabled') is False, 'Research catalog cannot enable admission')
    require(not ({'records', 'observations'} & catalog.keys()), 'Research catalog cannot embed observation records')
    baseline = catalog['baseline_inventory']
    require(baseline['repo_path'] == 'data/evidence-program/source_inventory.json' and
            baseline['record_count'] == len(SOURCE_IDS) and baseline['version'] == '1.1' and
            baseline['audit_commit'] == BASELINE and baseline['sha256'] == inventory_hash,
            'Research catalog frozen inventory mismatch')
    families = catalog['families']
    ids = [f['candidate_id'] for f in families]
    require(len(ids) == 8 and set(ids) == {f'ZHS{i:03}' for i in range(1, 9)}, 'Research candidate IDs/count mismatch')
    require(sum(f['classification'] == 'new_relative_to_frozen_inventory' for f in families) == 7 and
            sum(f['classification'] == 'existing_family_enrichment' for f in families) == 1,
            'Research catalog must retain seven new candidates plus one enrichment')
    all_artifacts = {}
    for family in families:
        require(family['collection_status'] == 'candidate_not_collected' and
                family['operational_admission'] == 'not_admitted' and family['collector_enabled'] is False,
                'Research family cannot enable collection/admission')
        require(family['research_status'] in {'primary_research_verified', 'index_only_direct_access_blocked'},
                'Unknown research verification status')
        for field in ['name', 'summary', 'rights_summary']:
            require(isinstance(family.get(field), str) and family[field].strip(), f'Missing research {field}')
        artifacts = family['artifacts']
        by_id = {a['artifact_id']: a for a in artifacts}
        require(artifacts and len(by_id) == len(artifacts) and not (by_id.keys() & all_artifacts.keys()),
                'Missing/duplicate research artifact ID')
        for artifact in artifacts:
            check_url(artifact['url'])
            require(artifact['raw_content_in_catalog'] is False, 'Research catalog cannot embed raw artifacts')
            require(artifact['access_status'] in {'primary_opened', 'bounded_sample_opened', 'access_blocked',
                                                  'index_only', 'index_only_direct_timeout'}, 'Invalid artifact access status')
            require(artifact['reviewed_on'] == catalog['reviewed_on'] and artifact['provenance_locator'],
                    'Research artifact lacks dated provenance')
            require(artifact['rights_status'] in {'declared_license', 'restricted_use', 'unknown'} and
                    artifact['rights_note'], 'Research artifact lacks scoped rights')
            refs = artifact['rights_evidence_artifact_ids']
            require(set(refs) <= by_id.keys(), 'Unknown rights evidence artifact')
            if artifact['rights_status'] != 'unknown':
                require(artifact.get('license_identifier') and refs, 'Declared rights lack evidence/scope')
            for field, length in [('git_commit', 40), ('identified_commit', 40), ('git_blob_sha', 40), ('sha256', 64)]:
                if field in artifact:
                    require(isinstance(artifact[field], str) and re.fullmatch('[0-9a-f]{'+str(length)+'}', artifact[field]),
                            f'Invalid research artifact {field}')
            if 'git_commit' in artifact:
                require('/blob/' + artifact['git_commit'] + '/' in artifact['url'], 'Artifact URL/pin mismatch')
        for relation in family['inventory_relationships']:
            require(relation['source_id'] in SOURCE_IDS and relation['evidence_artifact_id'] in by_id,
                    'Unknown research inventory/evidence reference')
        findings = family['findings']
        require(findings and len({f['finding_id'] for f in findings}) == len(findings), 'Missing/duplicate research finding')
        for finding in findings:
            require(finding['text'] and finding['evidence_artifact_ids'] and
                    set(finding['evidence_artifact_ids']) <= by_id.keys(), 'Research finding lacks artifact provenance')
            require(finding['verification_level'] in {'primary_source_reported', 'index_only_inconclusive'},
                    'Unknown finding verification level')
        if family['research_status'] == 'index_only_direct_access_blocked':
            require(all(a['access_status'] not in {'primary_opened', 'bounded_sample_opened'} for a in artifacts) and
                    all(f['verification_level'] == 'index_only_inconclusive' for f in findings),
                    'Index-only evidence cannot become opened-primary verification')
        all_artifacts.update(by_id)
    by_family = {f['candidate_id']: f for f in families}
    require(any(r['source_id'] == 'CN019' and r['relationship'] == 'documented_integration'
                for r in by_family['ZHS001']['inventory_relationships']), 'FLAMES/CN019 relationship missing')
    require(by_family['ZHS008']['classification'] == 'existing_family_enrichment' and
            any(r['source_id'] == 'CN020' and r['relationship'] == 'same_family_component'
                for r in by_family['ZHS008']['inventory_relationships']), 'C-SEM must remain CN020 enrichment')
    spec = catalog['proposed_adapter']
    require(spec['status'] == 'proposed_not_implemented' and spec['candidate_id'] == 'ZHS001', 'Research adapter must remain a specification')
    require(set(spec['artifact_ids']) == {'flames_readme', 'flames_license'} and len(spec['artifact_ids']) == 2 and
            spec['content_fetches_max'] == 2 and 0 < spec['bytes_per_file_max'] <= 131072 and
            spec['reject_unexpected_redirects'] is True, 'FLAMES adapter bounds changed')
    for artifact_id in spec['artifact_ids']:
        artifact = all_artifacts[artifact_id]
        require(all(artifact.get(k) for k in ['git_commit', 'git_blob_sha', 'sha256']) and
                0 < artifact['size_bytes'] <= spec['bytes_per_file_max'], 'FLAMES specification lacks bounded integrity pins')
    require(spec['numeric_representation'] == 'exact_decimal_strings' and
            set(spec['unknown_fields']) == {'model_checkpoint', 'evaluated_at', 'denominator', 'fully_specified_protocol'} and
            all(v is None for v in spec['unknown_fields'].values()) and spec['independent_experiment_count'] is None,
            'FLAMES specification must preserve unknowns/exact decimals')
    require(spec['parse_section'] == 'Leaderboard' and spec['expected_unique_model_labels'] == 17 and
            spec['expected_scalar_cells'] == 187 and len(spec['spot_checks']) == 3,
            'FLAMES historical table scope/cardinality changed')
    for spot in spec['spot_checks']:
        require(isinstance(spot['decimal_value'], str) and re.fullmatch(r'\d+(?:\.\d+)?', spot['decimal_value']),
                'Research numeric spot checks require decimal strings')
        require(spot['unit'] in {'percent', 'source_defined_score'} and
                spot['raw_value'] == spot['decimal_value'] + ('%' if spot['unit'] == 'percent' else ''),
                'Research spot-check value/unit mismatch')
    headings = re.findall(r'^## (ZHS[0-9]{3}) (.+)$', markdown, flags=re.MULTILINE)
    require(len(headings) == len(ids) and dict(headings) == {f['candidate_id']: f['name'] for f in families},
            'Research catalog documentation IDs/titles mismatch')
    return {'research_candidates': len(families), 'research_artifact_references': len(all_artifacts),
            'unadmitted_research_candidates': len(families)}


def check_fingerprints():
    manifest = read_json(HERE / 'frozen_contract_manifest.json')
    require(manifest['contract_version'] == '0.1.0', 'Frozen version changed without review')
    for rel, expected in manifest['sha256'].items():
        path = (HERE / rel).resolve()
        require(path.is_relative_to(HERE), 'Unsafe frozen-contract path')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'Frozen contract drift: {rel}')
    for ref in read_json(DATA / 'chinese/reference_manifest.json')['references'].values():
        path = (ROOT / ref['repo_path']).resolve()
        require(path.is_relative_to(ROOT), 'Unsafe reference path')
        payload = path.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == ref['sha256'] and len(payload) == ref['bytes'], f"Reference drift: {ref['repo_path']}")


def check_doc_links(base_paths=None):
    # Only introduced program docs and root README; existing docs are untouched.
    files = [ROOT / 'README.md'] + list(DOCS.rglob('*.md')) + list(DATA.rglob('*.md')) + list(HERE.glob('*.md'))
    checked = 0
    for file in files:
        text = file.read_text(encoding='utf-8')
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
            target = target.split(' "', 1)[0]
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = (file.parent / unquote(parsed.path)).resolve()
            require(path.is_relative_to(ROOT), f'Documentation link escapes repository: {file.name} {target}')
            rel = path.relative_to(ROOT).as_posix()
            exists = path.exists() or (base_paths is not None and (rel in base_paths or any(p.startswith(rel.rstrip('/')+'/') for p in base_paths)))
            require(exists, f'Broken documentation link: {file.relative_to(ROOT)} -> {target}')
            checked += 1
    return checked


def run(base_paths=None):
    # Missing dependencies are a clear error; this check never installs packages.
    from validate_dataset import check_contracts, validate_bundle, SCHEMA, Draft202012Validator, FORMAT_CHECKER
    from check_methodology_examples import verify_examples
    from check_adoption_productivity import check_catalog as check_adoption_catalog
    from check_organizational_safety import check_catalog as check_organizational_catalog
    from check_research_queue import check_queue
    from check_open_model_diffusion import check_catalog as check_open_model_catalog
    inventory = read_json(DATA / 'source_inventory.json')
    mapping = read_json(DATA / 'coverage_mapping.json')
    metrics = read_json(DATA / 'baseline_metrics.json')
    check_sources(inventory, read_json(DATA / 'global_sources.json'), read_json(DATA / 'chinese_sources.json'))
    check_coverage(inventory, mapping, metrics, read_json(DATA / 'coverage_references.json'))
    check_csv(DATA / 'source_inventory.csv', inventory['records'])
    check_csv(DATA / 'coverage_mapping.csv', mapping)
    check_csv(DATA / 'baseline_metrics.csv', metrics['metrics'])
    check_fingerprints()
    schemas, _ = check_contracts()
    require(len(schemas) == 14, 'Expected 14 frozen schemas')
    bundle = read_json(HERE / 'examples/synthetic_dataset.json')
    require(not validate_bundle(bundle), 'Synthetic contract bundle is invalid')
    fragments = check_chinese(read_json(DATA / 'chinese/aliases.json'), read_json(DATA / 'chinese/query_lexicon.json'), read_json(DATA / 'chinese/test_cases.json'), SCHEMA, Draft202012Validator, FORMAT_CHECKER)
    arithmetic = verify_examples()
    require(arithmetic == read_json(DATA / 'methodology_example_checks.json') and arithmetic['checks_passed'] == 19, 'Methodology arithmetic report diverges')
    recipes = read_json(DATA / 'analysis_recipes.json')
    require(recipes['status'] == 'proposed_methodology_not_implemented', 'Recipes must remain proposed')
    record_types = set(SCHEMA['$defs']['record']['properties']['record_type']['enum'])
    for recipe in recipes['recipes']:
        require(set(recipe['record_types']) <= record_types, 'Recipe refers to unknown record types')
    task_counts = check_task_plan(read_json(DATA / 'implementation_tasks.json'), recipes,
                                  (DOCS / 'implementation_tasks.md').read_text(encoding='utf-8'), base_paths)
    research_counts = check_research_catalog(read_json(DATA / 'research/chinese-safety-evaluations.json'),
                                            hashlib.sha256((DATA / 'source_inventory.json').read_bytes()).hexdigest(),
                                            (DOCS / 'research/chinese-safety-evaluations.md').read_text(encoding='utf-8'))
    adoption_counts = check_adoption_catalog(read_json(DATA / 'research/adoption-productivity.json'),
                                            hashlib.sha256((DATA / 'source_inventory.json').read_bytes()).hexdigest(),
                                            (DOCS / 'research/adoption-productivity.md').read_text(encoding='utf-8'))
    organizational_counts = check_organizational_catalog(read_json(DATA / 'research/organizational-safety.json'),
                                            hashlib.sha256((DATA / 'source_inventory.json').read_bytes()).hexdigest(),
                                            (DOCS / 'research/organizational-safety.md').read_text(encoding='utf-8'))
    open_model_counts = check_open_model_catalog(read_json(DATA / 'research/open-model-diffusion.json'),
                                            hashlib.sha256((DATA / 'source_inventory.json').read_bytes()).hexdigest(),
                                            (DOCS / 'research/open-model-diffusion.md').read_text(encoding='utf-8'))
    queue_counts = check_queue((DOCS / 'research/research-session-review-queue.md').read_text(encoding='utf-8'))
    links = check_doc_links(base_paths)
    loader = unittest.TestLoader()
    contract_suite = loader.discover(str(HERE / 'tests'), pattern='test_contract.py')
    require(contract_suite.countTestCases() == 71, 'Frozen contract test count changed')
    result = unittest.TextTestRunner(verbosity=1).run(contract_suite)
    require(result.wasSuccessful(), 'Frozen contract regression suite failed')
    integration_suite = unittest.TestLoader().discover(str(HERE / 'tests'), pattern='test_integration.py')
    require(integration_suite.countTestCases() > 0, 'Integration regression tests missing')
    integration_result = unittest.TextTestRunner(verbosity=1).run(integration_suite)
    require(integration_result.wasSuccessful(), 'Integration regression suite failed')
    open_model_suite = unittest.TestLoader().discover(str(HERE / 'tests'), pattern='test_open_model*.py')
    require(open_model_suite.countTestCases() > 0, 'Open-model regression tests missing')
    open_model_result = unittest.TextTestRunner(verbosity=1).run(open_model_suite)
    require(open_model_result.wasSuccessful(), 'Open-model regression suite failed')
    return {'status': 'passed', **COUNTS, **task_counts, **research_counts, **adoption_counts, **organizational_counts, **open_model_counts, **queue_counts, 'schemas': len(schemas), 'synthetic_contract_records': len(bundle['records']),
            'documentation_relative_links': links, 'integration_regression_tests': integration_result.testsRun,
            'open_model_regression_tests': open_model_result.testsRun,
            'scope': 'Offline consistency, synthetic regression and two pinned licensed annotation-fixture checks only. No live fetch, operational collection, production import, deployment, rights approval or language-accuracy evaluation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-tree', type=Path, help='GitHub tree JSON for an overlay-only local check; omit in CI')
    args = parser.parse_args()
    paths = None
    if args.base_tree:
        tree = read_json(args.base_tree)
        paths = {r['path'] for r in tree}
    try:
        print(json.dumps(run(paths), indent=2))
    except (ValueError, KeyError, OSError, ImportError) as exc:
        print(f'Evidence program check failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
