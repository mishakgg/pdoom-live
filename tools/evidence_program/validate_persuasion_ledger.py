"""Check a hand-curated aggregate contrast ledger, without reading source files.

This deliberately exposes only an in-memory validation function. It is not a
participant-data reader, source parser, effect estimator or collection framework.
The caller owns JSON decoding; the repository checker supplies curated JSON.
"""
from __future__ import annotations
from decimal import Decimal
import re

SCHEMA = 'published-persuasion-contrasts-v1'
REAL_DOI = '10.1038/s41562-025-02194-6'
CORRECTION_DOI = '10.1038/s41562-026-02588-0'
SYNTHETIC_DOI = '10.0000/synthetic-persuasion'
SYNTHETIC_CORRECTION_DOI = '10.0000/synthetic-persuasion-correction'
MAX_DEPTH = 8
MAX_NODES = 512
MAX_TEXT = 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected.split()),
            label + ': missing, unknown or invalid fields')


def decimal(value, label):
    require(type(value) is str and re.fullmatch(r'(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,6})?', value),
            label + ': expected a bounded unsigned decimal string')
    return Decimal(value)


def bounded(document):
    # The API accepts plain JSON values only. Depth/node limits also reject
    # cycles, oversized strings and accidental participant tables before use.
    count = 0
    def walk(value, depth):
        nonlocal count
        count += 1
        require(count <= MAX_NODES and depth <= MAX_DEPTH, 'ledger size/depth limit')
        require(type(value) in (dict, list, str, int, bool, type(None)), 'non-JSON value')
        if type(value) is str:
            try:
                size = len(value.encode('utf-8'))
            except UnicodeError as exc:
                raise ValueError('invalid Unicode') from exc
            require(size <= MAX_TEXT and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'invalid or excessive text')
        elif type(value) is int:
            require(abs(value) <= 1000000, 'integer limit')
        elif type(value) is dict:
            for key, item in value.items():
                require(type(key) is str, 'non-string key')
                walk(key, depth + 1); walk(item, depth + 1)
        elif type(value) is list:
            for item in value:
                walk(item, depth + 1)
    walk(document, 0)


def validate_ledger(document):
    """Validate one study, two current contrasts and one superseded assertion.

    Numeric consistency and provenance binding do not establish source truth or
    inferential replication. No averaging across contrasts or sources occurs.
    """
    bounded(document)
    keys(document, 'schema_version input_kind study records correction', 'ledger')
    require(document['schema_version'] == SCHEMA, 'unsupported schema')
    kind = document['input_kind']
    require(type(kind) is str and kind in {'manual_aggregate', 'synthetic_fixture'}, 'invalid input kind')
    real = kind == 'manual_aggregate'
    doi = REAL_DOI if real else SYNTHETIC_DOI
    correction_doi = CORRECTION_DOI if real else SYNTHETIC_CORRECTION_DOI
    article_url = 'https://www.nature.com/articles/s41562-025-02194-6' if real else 'https://example.invalid/persuasion/article'
    correction_url = 'https://www.nature.com/articles/s41562-026-02588-0' if real else 'https://example.invalid/persuasion/correction'
    study = document['study']
    keys(study, 'doi evidence_class outcome time_window population_causal_effect participant_data_acquired model_inference_performed', 'study')
    require(study['participant_data_acquired'] is False and study['model_inference_performed'] is False and study == dict(doi=doi, evidence_class='randomized_assigned_exposure',
                         outcome='post_debate_opponent_aligned_agreement', time_window='immediate_within_session',
                         population_causal_effect=None, participant_data_acquired=False, model_inference_performed=False),
            'study identity, measurement or safety boundary changed')
    rows = document['records']
    require(type(rows) is list and len(rows) == 3, 'exactly three published assertions required')
    by_id = {}
    expected = {
        'human_comparison': ('personalized_gpt4_vs_unpersonalized_human', 'unpersonalized_human', 'current', 'current_article'),
        'personalization_original': ('personalized_gpt4_vs_nonpersonalized_gpt4', 'nonpersonalized_gpt4', 'superseded', 'original_reported_in_correction'),
        'personalization_corrected': ('personalized_gpt4_vs_nonpersonalized_gpt4', 'nonpersonalized_gpt4', 'current', 'correction'),
    }
    for row in rows:
        keys(row, 'record_id comparison_id intervention comparator outcome time_window effect_metric estimate uncertainty p_value p_relation conditioning status source', 'record')
        rid = row['record_id']
        require(type(rid) is str and rid in expected and rid not in by_id, 'unknown or duplicate record identity')
        comparison, comparator, status, version = expected[rid]
        require(row['comparison_id'] == comparison and row['comparator'] == comparator and
                row['intervention'] == 'personalized_gpt4' and row['status'] == status and
                row['outcome'] == study['outcome'] and row['time_window'] == study['time_window'] and
                row['conditioning'] == 'pretreatment_agreement' and row['effect_metric'] == 'ordinal_model_odds_ratio', 'contrast/estimand/unit/status mismatch')
        estimate = decimal(row['estimate'], 'estimate')
        require(estimate > 0, 'odds ratio must be positive')
        uncertainty = row['uncertainty']
        keys(uncertainty, 'type level lower upper method', 'uncertainty')
        require(uncertainty['type'] == 'confidence_interval' and uncertainty['level'] == '0.95' and uncertainty['method'] == 't_based_cluster_robust', 'uncertainty type or level mismatch')
        lower, upper = decimal(uncertainty['lower'], 'lower'), decimal(uncertainty['upper'], 'upper')
        require(0 < lower <= estimate <= upper, 'invalid odds-ratio interval')
        p = row['p_value']
        if p is not None:
            require(0 <= decimal(p, 'p value') <= 1, 'p value outside unit interval')
        require(p is not None and row['p_relation'] == ('<' if rid == 'human_comparison' else '='), 'p-value relation does not match comparison')
        source = row['source']
        keys(source, 'doi url version locator artifact_sha256 capture_status', 'source')
        require(source['version'] == version and source['artifact_sha256'] is None and
                source['capture_status'] == ('text_observed_hash_unavailable' if real else 'synthetic_fixture'), 'source version/hash/capture mismatch')
        require(type(source['locator']) is str and bool(source['locator'].strip()), 'missing exact claim locator')
        required_url, required_doi = (article_url, doi) if rid == 'human_comparison' else (correction_url, correction_doi)
        require(source['url'] == required_url and source['doi'] == required_doi, 'source/DOI binding mismatch')
        by_id[rid] = row
    old, new = by_id['personalization_original'], by_id['personalization_corrected']
    same_estimand = ('comparison_id', 'intervention', 'comparator', 'outcome', 'time_window', 'effect_metric', 'conditioning')
    require(all(old[k] == new[k] for k in same_estimand), 'correction crosses estimands')
    require(old['estimate'] == new['estimate'] and old['uncertainty'] == new['uncertainty'],
            'p-value-only correction cannot silently change effect or interval')
    require(old['p_value'] is not None and new['p_value'] is not None and old['p_value'] != new['p_value'], 'correction lacks changed p value')
    edge = document['correction']
    keys(edge, 'from_record_id to_record_id relation changed_fields doi url publication_date journal_status', 'correction')
    require(edge['from_record_id'] == 'personalization_original' and edge['to_record_id'] == 'personalization_corrected' and
            edge['relation'] == 'corrects_same_comparison' and edge['changed_fields'] == ['p_value'] and
            edge['doi'] == correction_doi and edge['url'] == correction_url and
            edge['publication_date'] == ('2026-09-03' if real else '2000-01-02') and edge['journal_status'] == 'published_author_correction',
            'correction edge/provenance mismatch')
    return {'input_kind': kind, 'study_count': 1, 'comparison_count': 2, 'assertion_count': 3,
            'current_assertion_count': 2, 'canonical_import_enabled': False,
            'participant_data_acquired': False, 'source_extraction_performed': False,
            'statistical_reanalysis_performed': False}
