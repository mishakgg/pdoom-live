"""Offline consistency checks for the curated training-data review; no acquisition."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qsl

BASE = 'd196d9c89b8ba12d584a2f19e8ded1623ab0142a'
IDS = {f'TD{i:03}' for i in range(1, 6)}

def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def safe_url(url):
    require(type(url) is str and len(url) <= 2048, 'Unbounded source URL')
    p = urlsplit(url)
    require(p.scheme == 'https' and p.hostname and not p.username and not p.password
            and not any(c.isspace() for c in url), 'Invalid source URL')
    require(not any(any(v in k.lower() for v in ['token', 'secret', 'credential', 'signature', 'api_key'])
                    for k, _ in parse_qsl(p.query)), 'Private source URL')


def check_catalog(catalog, inventory_hash, markdown, root=None):
    require(catalog['schema_version'] == '1.0' and catalog['reviewed_on'] == '2026-10-08'
            and catalog['repository_review_commit'] == BASE
            and catalog['status'] == 'review_prepared_with_bounded_offline_reader', 'Review identity changed')
    require(same(catalog['baseline_inventory'], dict(source_family_count=64, sha256=inventory_hash, unchanged=True)), 'Frozen inventory mismatch')
    require(catalog['operational_admission'] == 'not_admitted' and catalog['canonical_contract_mapping'] == 'pending_separate_review', 'Admission or canonical mapping expanded')
    for key in ['collector_enabled', 'training_or_model_execution', 'source_code_execution', 'corpus_or_page_content_acquired', 'raw_source_files_vendored']:
        require(catalog[key] is False, 'Scope expanded: ' + key)
    require(same(catalog['interpretation_guards'], GUARDS), 'Interpretation guard changed')
    require([(x['rank'], x['candidate_id']) for x in catalog['priority_ranking']] == [(1, 'TD001'), (2, 'TD002'), (3, 'TD003')], 'Ranking identity changed')
    rows = catalog['collections']
    require(len(rows) == 5 and {r['candidate_id'] for r in rows} == IDS, 'Five unique candidate collections required')
    require(len({r['source_family_id'] for r in rows}) == 5, 'Source-family identities differ')
    refs, findings = {}, []
    for row in rows:
        cid = row['candidate_id']
        require(row['operational_admission'] == 'not_admitted' and row['collector_enabled'] is False, 'Collection admitted')
        require(same({k: row[k] for k in ['source_family_id', 'inventory_relationship', 'inventory_source_id', 'measurement_regime']}, IDENTITIES[cid]), 'Producer/product/measurement conflated')
        for key in ['samples', 'coverage', 'findings', 'limitations']:
            require(fingerprint(row[key]) == REVIEW_FINGERPRINTS[cid][key], 'Reviewed ' + key + ' changed: ' + cid)
        require(row['limitations'] and row['duplicate_evidence'] and row['access_export'], 'Access/limitations absent')
        local_ids = {a['artifact_id'] for a in row['artifacts']}
        for artifact in row['artifacts']:
            aid = artifact['artifact_id']
            require(aid not in refs, 'Duplicate artifact ID')
            refs[aid] = artifact
            safe_url(artifact['url'])
            require(artifact['observed_on'] == '2026-10-08' and artifact['access_status'] and artifact['rights_scope'], 'Artifact provenance missing')
            require(artifact['source_bytes_vendored'] is False, 'Source bytes vendored')
            require(artifact['rights_status'] in {'declared_license', 'unknown'}, 'Unknown rights vocabulary')
            if artifact['rights_status'] == 'declared_license':
                require(artifact['license_identifier'] and artifact['rights_evidence_url'], 'License lacks evidence')
                safe_url(artifact['rights_evidence_url'])
            else:
                require(artifact['license_identifier'] is None, 'Unknown rights promoted')
            if artifact['artifact_sha256'] is not None:
                require(re.fullmatch('[0-9a-f]{64}', artifact['artifact_sha256']) and artifact['hash_scope'] == 'Exact acquired source file bytes', 'Unqualified artifact hash')
            if artifact['git_blob_sha'] is not None:
                require(re.fullmatch('[0-9a-f]{40}', artifact['git_blob_sha']), 'Malformed Git blob pin')
        for item in row['samples'] + row['findings']:
            require(item['qualification'] and item['evidence_artifact_ids'] and set(item['evidence_artifact_ids']) <= local_ids, 'Unresolved evidence reference')
        findings.extend(row['findings'])
    require(set(refs) == set(ARTIFACT_FINGERPRINTS), 'Artifact set changed')
    for aid, artifact in refs.items():
        require(fingerprint(artifact) == ARTIFACT_FINGERPRINTS[aid], 'Artifact scope/version/rights/hash changed: ' + aid)
    require(len({r['finding_id'] for r in findings}) == len(findings), 'Duplicate finding ID')
    require(same(catalog['inventory_relationships'], INVENTORY_RELATIONS), 'Inventory relationship altered')
    require(same(catalog['evidence_relationships'], EVIDENCE_RELATIONS), 'Evidence ancestry/identity relationship changed')
    overlap = catalog['catalog_overlap_review']
    require(overlap['commit'] == BASE and overlap['prior_collection_count'] == 48
            and overlap['prior_artifact_reference_count'] == 362 and overlap['comparison_cell_count'] == 45, 'Incomplete prior-catalog comparison')
    prior = overlap['catalogs_compared']
    require(len(prior) == 9 and {x['path'] for x in prior} == set(PRIOR), 'Prior catalog missing or duplicated')
    for item in prior:
        require(fingerprint(item) == PRIOR[item['path']], 'Prior catalog comparison identity/semantics changed')
        require(set(item['candidate_checks']) == IDS, 'Missing candidate-by-catalog comparison')
        if root is not None:
            raw = (Path(root) / item['path']).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == item['sha256']
                    and hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['git_blob_sha'], 'Prior reviewed catalog drift')
            old = json.loads(raw); old_rows = old.get('collections', old.get('families', []))
            require([r['candidate_id'] for r in old_rows] == [r['candidate_id'] for r in item['compared_collections']]
                    and sum(len(r['artifacts']) for r in old_rows) == item['artifact_count'], 'Prior records/artifacts mismatch')
    require(same(catalog['offline_reader'], READER), 'Reader bounds or rights/implementation scope changed')
    require(same(catalog['next_actions'], ACTIONS) and same(catalog['holds'], HOLDS), 'Completed work or remaining holds changed')
    require(same(catalog['corrections'], CORRECTIONS), 'Source correction lost')
    prompts = catalog['focused_follow_up_prompts']
    require(len(prompts) == 6 and len({p['prompt_id'] for p in prompts}) == 6, 'Follow-up identity changed')
    for p in prompts:
        require('Read-only public-source research only.' in p['prompt']
                and 'No login, outreach, bulk download, access-control bypass' in p['prompt']
                and 'No repository edits, canonical admission or deployment.' in p['prompt'], 'Follow-up action boundary missing')
    for phrase in ['486', '45', '362', 'residual', '1870', '1868', '75', '105', 'synthetic-only', 'not independently measured unique URLs']:
        require(phrase in markdown, 'Guide loses critical boundary: ' + phrase)
    return {'training_data_collections': 5, 'unadmitted_training_data_collections': 5,
            'training_data_artifact_references': len(refs), 'training_data_qualified_findings': len(findings),
            'training_data_prior_catalogs_compared': 9, 'training_data_overlap_comparison_cells': 45,
            'training_data_operational_collectors': 0}


def check_reader_fixtures(root):
    from read_common_crawl_statistics import read_statistics, SOURCE_COMMIT, SOURCE_SHA256, LANGUAGES_PATH, MONTHLY_PATH
    require(SOURCE_COMMIT == READER['source_commit'], 'Reader source version drift')
    require(SOURCE_SHA256 == {LANGUAGES_PATH: SOURCE_PINS['td001_languages'],
                             MONTHLY_PATH: SOURCE_PINS['td001_monthly']}, 'Reader exact-byte pins drift')
    fixtures = Path(root) / 'tools/evidence_program/tests/fixtures/training-data'
    result = read_statistics(fixtures / 'synthetic-languages.csv', fixtures / 'synthetic-monthly.csv', synthetic_fixture=True)
    require(result['synthetic'] is True and result['crawl_count'] == 3 and result['canonical_import_enabled'] is False, 'Synthetic isolation lost')
    require(all(a['source_sha256'] is None and a['source_byte_pin_verified'] is False
                and a['csv_redistribution_rights'] == 'unknown' for a in result['source_artifacts']), 'Synthetic source claim or rights escalation')
    require(all(r['capture_started_on'] is None and r['released_on'] is None and r['underlying_content_published_at'] is None
                for r in result['crawl_summaries']), 'Synthetic/source/publication date conflation')
    unknown = [r for r in result['language_observations'] if r['primary_language'] == '<unknown>']
    require(len(unknown) == 3 and all(r['url_cardinality'] is None
                and r['url_count_basis'] == 'page_residual_placeholder_not_measured_URL_cardinality' for r in unknown), 'Unknown URL residual relabeled as measured cardinality')
    require(result['interpretation']['url_cardinalities_not_summed_across_language_buckets'] is True, 'URL partition assumption introduced')
    return {'training_data_synthetic_fixture_crawls': 3,
            'training_data_synthetic_fixture_language_rows': len(result['language_observations']),
            'training_data_real_source_csv_fixtures': 0}

GUARDS = {'audit_records_add_content_supply': False,
 'canonical_admission_implied': False,
 'copied_or_rehydrated_content_is_new_unique_supply': False,
 'experimental_generation_is_calendar_time': False,
 'experimental_real_role_is_human_authorship': False,
 'modeled_stock_is_empirical_annual_series': False,
 'proxies_are_catastrophe_probabilities': False,
 'public_visibility_is_redistribution_permission': False,
 'public_visibility_is_training_permission': False,
 'raw_captured_content_is_licensed_usable_stock': False,
 'restriction_absence_is_consent': False,
 'words_are_universal_tokens': False}

IDENTITIES = {'TD001': {'inventory_relationship': 'new_source_family_candidate',
           'inventory_source_id': None,
           'measurement_regime': 'observational_crawl_aggregate',
           'source_family_id': 'commoncrawl-crawl-statistics'},
 'TD002': {'inventory_relationship': 'new_source_family_candidate',
           'inventory_source_id': None,
           'measurement_regime': 'dataset_metadata_audit_and_restriction_study',
           'source_family_id': 'data-provenance-initiative'},
 'TD003': {'inventory_relationship': 'new_source_family_candidate',
           'inventory_source_id': None,
           'measurement_regime': 'controlled_synthetic_feedback_experiments',
           'source_family_id': 'collapse-or-thrive'},
 'TD004': {'inventory_relationship': 'new_curation_family_candidate',
           'inventory_source_id': None,
           'measurement_regime': 'curated_commoncrawl_derived_corpus_statistics',
           'source_family_id': 'fineweb2'},
 'TD005': {'inventory_relationship': 'known_producer_new_product',
           'inventory_source_id': 'GL001',
           'measurement_regime': 'modeled_stock_and_effective_repetition',
           'source_family_id': 'epoch-data-stock'}}

REVIEW_FINGERPRINTS = {'TD001': {'coverage': 'c3237cb3052b2876d55c4bbb218e4471d3c9847c0c4098953c4890254ba017f3',
           'findings': 'df6cf76a7c5f80cb87cad8e2f2284f3c433ca699b2cb0ce6045ae39dafa72928',
           'limitations': 'fdb5b93c92d83488ce0d5d8df95e7e23de6b61420cd48ddc05ae3ba2bbcf9db7',
           'samples': '0831552d4ea1eeaf3ca40765ede59d6a108c61ca9223fc0674822378c8820f2d'},
 'TD002': {'coverage': 'fd03cdd402e34efd2ef8e36127ebd912b9fcd5ffed452a43c1a61adf26512bf4',
           'findings': '6421b6268cbf15d4bdb7d26d6ac7e0a687693356d69f28ce81d1bf47cf96acad',
           'limitations': '581bb0fa2b8a6864a1a58605b77fcb69683fc31162d0b23dab00e77a83a3da08',
           'samples': 'e699ffaab27c89145b9a1e2b25b273fe7b8871f9c255171bd8fafe280aa95c8b'},
 'TD003': {'coverage': 'f8acf9086c8d4bece11c99a3d25bdcfadcdde5fd81c546f9e9d3bf4bd97c4f9c',
           'findings': 'b5c9a2a9274efaa2c92e5771f84de2577e3e72825a6c7a6752afef324deeb2fd',
           'limitations': 'ff03fde84b7c0a1cac80204450bb9bb57c2e1b6c4b639808c2146febb98bcaee',
           'samples': 'dd30bc60c957567827741f3911ea3db2b74e2a41562ccbb6187020e9bf85904f'},
 'TD004': {'coverage': '7a27bb110034671509b88a9606afbc1f8b9fe21cce75536341c0d2035bb0d3d8',
           'findings': '13fa35933f3769a496825154c57d9a833234712b7d48e5f84116b769a54abe85',
           'limitations': '73b6d5adcd82c5e86d93be3c0154bc1838a985f5e2624428d19dcfa56bd299ff',
           'samples': '2d262f9a43a47526edbd9154fd0c10e1f7d3c853bd7f4c403e48b2d591e8800e'},
 'TD005': {'coverage': '490229c183724c3fe8f335901e008d80f1f9194fe8138ed3c73c847d87da47f4',
           'findings': '6d87869c5dab4d3358e8f2181b5737d858de166aeee94704ff387b5db64054e8',
           'limitations': 'd5d840256ae440707a2178e644bde7432ea4123d1833667efff902918d03491f',
           'samples': 'be576360e7267281adab4caabffeb2143c7f00658e5acf4114c0181f6bbcddeb'}}

ARTIFACT_FINGERPRINTS = {'td001_august': '5fdca2d6a0c48fd1ae0abcdf95a8e40b9797ea8ee89c2e03a09c5a5733d33947',
 'td001_count_code': '78ac63fee91bb82b96c5d4be895989c787d4952308f4033a965019dc4000fc66',
 'td001_july': '74b8345458d75914d58299fd7e0b420f159c288798da745bd4e41194532f57df',
 'td001_language_methods': 'ae60d416e0ca82a9193cfadbae0585b495fc129d292d8d0dc5b3f38fd67486c2',
 'td001_languages': 'd84f0a4eeb57271d01b55e695d5b3f8ea5f72b982b2d17ebe9529068ebb4d7e2',
 'td001_license': '4c7d1d72bf12a8ce6c0de5f7eb79f2b0becc0959e7eca60a798bf9cd594f11bd',
 'td001_methods': '976b675ca2a1a9a608571bd616a0465f29df35e7673a9c4e290a45b3ab222c11',
 'td001_monthly': 'a927fb605ed77e2c7749ffd80d93274ed0841f1b4838d38a3d2ec88826aff043',
 'td001_multicount_code': '21bae10a6598f747cd2db48e505a93cce5dfe062516f87eb4986c507f3b0b853',
 'td001_new_urls': '32a8817c471238e4a79506f5a7b3d5549ae7149e04a6d74e6e29cb0a6be63cd7',
 'td001_residual_code': '7f50fc1682f90276cff5e0bf68a7e6827b6b9c1fb89a504aa75ed444bda9b48f',
 'td001_september': '6eafd173151dea488b629758d61d9c3ee155115553b3d3a187ff0b9c8e059db2',
 'td001_terms': '63664540646f20b82e26194e1230c2a413d6faebffa0ef28e49c5a59bedfbe69',
 'td002_alpaca': '0623a0e065a959cb96cf838d4162db02e2a00e98bd7ea8dd1909d53a3eee43a4',
 'td002_consent': '7a0a6e28dcd49b87d14983bb0c9277979ae8b67f7a6948d9ddd9c72ee8ae27ba',
 'td002_consent_pdf': 'bb0ba9755c292d2e1ea43ed8a0bc403cb84eeae2285218f2e6b85becabecdc66',
 'td002_paper': '59d3402540cf10547d14904eb2f3b64983c73a576d63fd9d8a3ccd255974298b',
 'td002_readme': '62035ce65e2f4b537acce06d1b8647aff995eaab154f70c296f94dcd214960f1',
 'td002_template': '8aea1e517dcd6fc55511d20d1d963657f4f82be9f331f45428d8df47451d23a3',
 'td002_web_docs': 'ed2f839e2310c63fe79f035c5d09aa14e8cfed9d87e065c89c34da615403cadf',
 'td003_analysis': '6c3951863274d5b005623c2b64e43e2d0ddc10a54c38c6383ed9671e15165aff',
 'td003_csv': '5a22bcd25366300beb3078ca1d591617aea93cd2164b4c6e3737d3f72e659609',
 'td003_current_helper': '1f3f8d8671180c8b453e0cefddca26b6c9364abaa31ca7d7a2414ade4a0ae134',
 'td003_export_helper': '08d4fa7a7f2fa3bd7feae35080ba1bc6eb9c1542bf1555c59a35f56891b9554a',
 'td003_export_producer': 'b995cb8b74812cab6f59a708a862763a010145dfdc12bdc9b2a70f107245130b',
 'td003_helpsteer': '583201970b64d027575590b646ace0bc8811edbafc5d15b2f420de2f88e1092d',
 'td003_manuscript': 'a3a6b857cf36afcd2adedf7fbf30c38430dada794575cbcd9e3f3674d6ed403f',
 'td003_parquet': '52a14e198c13055f22e0679832a9d0628505276b330bf0d4aa2f1c0374f71303',
 'td003_producer': '48cbf61fe37083d5fcc70b86a47f3d4c5f45f04cf2139f9c6d40a5618b4d6466',
 'td003_publication': '10478b919a1d2e1e95d7329c4ed5650d58412a5737d768f50d38a65c934d8c3a',
 'td003_sweep': '154bacf8db1ebf94ee8684035b3fd8011f81690e95af1ceabd5ea0c69092d44a',
 'td004_card': '6bcc23421b9d75c3b47541729b7f4707c46dff7348b896c8df91cd02e667a7dd',
 'td004_code_license': '47826a790ccf26950c8f03845486550598d6976e1e1937e15749bba95f55f3d0',
 'td004_csv': '79af7ddd170f3c4a4d684a824c62f0f792a6b995087f01907133bae5873113ee',
 'td004_paper': '8de902a46371c31c9635bb78cf45a344cfd38254e88cf6e8ed7add9f876e45f3',
 'td004_readme': '5d3915c8bc960c4cdab700315c593cd4e4ee410ac4f89c9c21d45c4af1b44b15',
 'td005_adjust': '125b73063303eb4c43398519e91288db4507e45c376fb987cc6969856256af2b',
 'td005_article': '7744193c3715831f9cda3dd69df6f491de2cdb3f8de4341ff36e3e5817e3bb26',
 'td005_indexed': '1139fe83284d585db0971b0a261b0480f785b8c321e4d3fe2d5250bd22cc773c',
 'td005_paper': '98082b83a107f8960fda7aa8d98d318ee1a27c7e9b32d0468a73c4e0b2a9bacc',
 'td005_pivot': '4d5ae8eda1560f70aac0a55c066b69b422e99af2798a27fffcab6eb4a896daf5',
 'td005_repo': '6b4cbb36998f6b789ba4aab9541128f1b7de56123bf34da2f795ef3110e92fee'}

SOURCE_PINS = {'td001_languages': '4f3b987a60d72a356c480d788a930388ebe05225307aec7fc280513f6f9b0cff',
 'td001_monthly': 'b49fb0e4acd9cd3a4676cc4bad17eca9645e38dcecfea1dfc3f2436a1c7b98a7',
 'td004_code_license': 'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4',
 'td004_csv': '0c6e6fbcef62cb034aff493187dee8d327c6bb2c08bb14a81a9c7221b091e0a5',
 'td005_adjust': '3b067ed0d4f39107b0d8def0189cf90181b05e178eabf358fc1d7bb891c08e88',
 'td005_indexed': '79c710ac27f4394065dcbf4cd67516607275d48a9d6fe5fa25438bb8a88c458a',
 'td005_pivot': 'a08e7d4d28f5d73ca89d4d56b99a1e4fcca276d34ca6faabd994ce1e4fd38d1b'}

INVENTORY_RELATIONS = [{'relationship': 'Epoch known producer; distinct data-stock product, not AI Models dataset enrichment',
  'source_id': 'GL001'},
 {'relationship': 'Epoch known producer; hardware product distinct', 'source_id': 'GL002'},
 {'relationship': 'Epoch known producer; facilities product distinct', 'source_id': 'GL003'},
 {'relationship': 'Stanford CRFM / HELM institutional context only; DPI is distinct provenance audit family',
  'source_id': 'GL006'},
 {'relationship': 'AI Index may synthesize upstream statistics; no independence inferred',
  'source_id': 'GL034'},
 {'relationship': 'OpenAlex discovery metadata for papers is not an observation within their datasets',
  'source_id': 'GL039'},
 {'relationship': 'arXiv discovery/manuscript representation is not new underlying evidence',
  'source_id': 'GL040'}]

EVIDENCE_RELATIONS = [{'exact_record_join_verified': False,
  'note': 'Common Crawl to FineWeb2; do not add supply totals.',
  'relationship': 'raw_source_ancestry',
  'source': 'TD001',
  'target': 'TD004'},
 {'exact_record_join_verified': False,
  'note': 'Audit describes source material and restrictions, not new supply.',
  'relationship': 'metadata_audit',
  'source': 'described_corpora',
  'target': 'TD002'},
 {'exact_record_join_verified': False,
  'note': 'Common Crawl-related model inputs, not independent content.',
  'relationship': 'derived_model_input',
  'source': 'TD001',
  'target': 'TD005'},
 {'exact_record_join_verified': False,
  'note': 'Named Gaussian sweep k3mipjqi; full row equality not verified.',
  'relationship': 'alternate_encoding_of_named_sweep',
  'source': 'TD003:csv',
  'target': 'TD003:parquet'},
 {'exact_record_join_verified': False,
  'note': 'Known producer; exact record-level dependency unresolved.',
  'relationship': 'possible_model_size_input_overlap',
  'source': 'GL001',
  'target': 'TD005'}]

PRIOR = {'data/evidence-program/research/adoption-productivity.json': '3b61f0dbf8ba5f96b714598c6e57d531f0efc0622d0e030f7999c29d7db8569e',
 'data/evidence-program/research/chinese-safety-evaluations.json': '9076b8cd8db7cc772e46ea5a6228981e506ac4343c6a9f489f2cb9027183aac5',
 'data/evidence-program/research/concentration-dependencies.json': '3bf1c36eb622ea40e53d2e927ad6ad68c6176c419dcdf36815bd13352221ed1b',
 'data/evidence-program/research/historical-capability-backfills.json': '7f489db558243af5f807ba5a2c3ac73ed1c840e9ecbb762d3ef731eba9db3faa',
 'data/evidence-program/research/open-model-diffusion.json': '2b2786df5eafdc18865a3549b56a5743f72e06fcc4b3057e2eab9fe1e90de7bb',
 'data/evidence-program/research/organizational-safety.json': '15e806e2d5355d84b72a2a05d8cfba23ec8449b0958aac81b5195103833ead37',
 'data/evidence-program/research/persuasion-information.json': '6ccda001feb08dd62f8f199e6c9a3a1dba98e39152d634a0742f2a78e85dfb19',
 'data/evidence-program/research/robotics-physical.json': 'cd0f7d5c99f53be5c57d45bb500ffdb28acca0f91374c38343a525db51bf2b87',
 'data/evidence-program/research/scientific-progress.json': 'fbbf6f1bbcf52aff8b45282dc5eabc0fe944d165857b2d00f4ace3aba6c39745'}

READER = {'allowed_crawls': ['CC-MAIN-2026-30', 'CC-MAIN-2026-34', 'CC-MAIN-2026-39'],
 'bounds': {'field_max_bytes': 128,
            'languages_max_bytes': 1048576,
            'languages_max_rows': 20000,
            'line_max_bytes': 1024,
            'max_categories_per_crawl': 512,
            'max_count': 1000000000000,
            'monthly_max_bytes': 65536,
            'monthly_max_rows': 256,
            'percentage_tolerance_points': '0.00005'},
 'canonical_import': False,
 'corpus_or_page_content_acquisition': False,
 'expected_real_language_rows': 486,
 'expected_real_output_crawls': 3,
 'implemented': True,
 'input_kind': 'two_pinned_local_aggregate_csv_files',
 'known_real_statistics': [{'all_language_keys_unique': True,
                            'crawl': 'CC-MAIN-2026-30',
                            'language_rows': 162,
                            'language_sum': 2149001456,
                            'language_url_sum_minus_monthly_url': 235851,
                            'max_rounding_error_percentage_points': '0.0000492785654027030124078240736',
                            'rounding_within_half_unit_4dp': True,
                            'size_record': {'crawl': 'CC-MAIN-2026-30',
                                            'digest estim.': '2108543089',
                                            'page': '2149001456',
                                            'url': '2135935679'},
                            'sum_equal': True,
                            'sum_language_urls': 2136171530,
                            'sum_published_percent': '99.9995',
                            'unknown_url_count_derivation': 'residual page count copied through scalar '
                                                            'MultiCount into urls; not independently '
                                                            'observed unique URL count',
                            'url_partition_reconciliation_required': False},
                           {'all_language_keys_unique': True,
                            'crawl': 'CC-MAIN-2026-34',
                            'language_rows': 162,
                            'language_sum': 2139617681,
                            'language_url_sum_minus_monthly_url': 215687,
                            'max_rounding_error_percentage_points': '0.00004963503570898001006003090699',
                            'rounding_within_half_unit_4dp': True,
                            'size_record': {'crawl': 'CC-MAIN-2026-34',
                                            'digest estim.': '2074297350',
                                            'page': '2139617681',
                                            'url': '2127461002'},
                            'sum_equal': True,
                            'sum_language_urls': 2127676689,
                            'sum_published_percent': '99.9998',
                            'unknown_url_count_derivation': 'residual page count copied through scalar '
                                                            'MultiCount into urls; not independently '
                                                            'observed unique URL count',
                            'url_partition_reconciliation_required': False},
                           {'all_language_keys_unique': True,
                            'crawl': 'CC-MAIN-2026-39',
                            'language_rows': 162,
                            'language_sum': 2171285702,
                            'language_url_sum_minus_monthly_url': 180735,
                            'max_rounding_error_percentage_points': '0.0000495361488821704588372037279',
                            'rounding_within_half_unit_4dp': True,
                            'size_record': {'crawl': 'CC-MAIN-2026-39',
                                            'digest estim.': '2117305135',
                                            'page': '2171285702',
                                            'url': '2158769646'},
                            'sum_equal': True,
                            'sum_language_urls': 2158950381,
                            'sum_published_percent': '100.0001',
                            'unknown_url_count_derivation': 'residual page count copied through scalar '
                                                            'MultiCount into urls; not independently '
                                                            'observed unique URL count',
                            'url_partition_reconciliation_required': False}],
 'module': 'tools/evidence_program/read_common_crawl_statistics.py',
 'network_access': False,
 'private_real_acceptance': True,
 'public_fixtures': 'self_authored_synthetic_only',
 'read_guard_details': 'Defined and tested in the bounded reader; public acceptance uses synthetic fixtures, '
                       'fixed real-byte acceptance is a separate local step.',
 'source_bytes_vendored': False,
 'source_commit': '1053c982a91ba0bb4323c5f00ec3230d9cd54e4b',
 'source_paths': ['plots/languages.csv', 'plots/crawlsize/monthly.csv'],
 'source_script_execution': False,
 'statistics_csv_rights': 'unknown',
 'synthetic_fixture_hashes': {'synthetic-languages.csv': 'f1095df8812c9317aa5c96c9c3986b51bff401bc6e192904d367008b6dc9809b',
                              'synthetic-monthly.csv': 'cf8f8c4572615502fe1d227ee7e1b71e45ff3eec0f8c161b9dc83b6d952d3907'},
 'underlying_page_rights': 'unknown',
 'unknown_language_url_semantics': 'native page-residual placeholder retained; normalized URL cardinality '
                                   'null; no URL-sum invariant',
 'validation_establishes_rights_or_source_truth': False}

ACTIONS = [{'action': 'Verify five source collections, current frozen64 and all nine prior catalogs; preserve scoped '
            'corrections and rights.',
  'action_id': 'TD-A01',
  'status': 'completed'},
 {'action': 'Implement/test bounded two-file offline Common Crawl reader with synthetic public fixtures and '
            'separate private real-artifact acceptance.',
  'action_id': 'TD-A02',
  'status': 'completed'},
 {'action': 'Aggregate CSV-specific rights and lossless canonical mapping remain unknown; retain private '
            'real acceptance and synthetic-only public CI.',
  'action_id': 'TD-A03',
  'candidate_id': 'TD001',
  'status': 'held'},
 {'action': 'Audit-metadata reuse rights, per-record ancestry assertions, and exact Consent historical-panel '
            'access/schema/rights remain unverified.',
  'action_id': 'TD-A04',
  'candidate_id': 'TD002',
  'status': 'held'},
 {'action': 'Saved export completeness, CSV/Parquet row equivalence, estimator/filename versions and '
            'code/results licenses remain unresolved; no history acquisition or model execution.',
  'action_id': 'TD-A05',
  'candidate_id': 'TD003',
  'status': 'held'},
 {'action': 'Statistics CSV rights, exact release-denominator bridge, per-subset processing differences and '
            'cross-corpus overlap remain unresolved; no corpus acquisition.',
  'action_id': 'TD-A06',
  'candidate_id': 'TD004',
  'status': 'held'},
 {'action': 'Replication-code/input rights, indexed-page/pivot-count discrepancy and exact GL001 input join '
            'remain unresolved; no model execution.',
  'action_id': 'TD-A07',
  'candidate_id': 'TD005',
  'status': 'held'},
 {'action': 'Review lossless canonical mapping and admission separately; no contract/runtime/collector '
            'changes are part of this review.',
  'action_id': 'TD-A08',
  'status': 'pending_separate_review'}]

HOLDS = [{'candidate_id': 'TD001',
  'reason': 'Aggregate CSV-specific rights and lossless canonical mapping remain unknown; retain private '
            'real acceptance and synthetic-only public CI.',
  'status': 'held_for_separate_work'},
 {'candidate_id': 'TD002',
  'reason': 'Audit-metadata reuse rights, per-record ancestry assertions, and exact Consent historical-panel '
            'access/schema/rights remain unverified.',
  'status': 'held_for_separate_work'},
 {'candidate_id': 'TD003',
  'reason': 'Saved export completeness, CSV/Parquet row equivalence, estimator/filename versions and '
            'code/results licenses remain unresolved; no history acquisition or model execution.',
  'status': 'held_for_separate_work'},
 {'candidate_id': 'TD004',
  'reason': 'Statistics CSV rights, exact release-denominator bridge, per-subset processing differences and '
            'cross-corpus overlap remain unresolved; no corpus acquisition.',
  'status': 'held_for_separate_work'},
 {'candidate_id': 'TD005',
  'reason': 'Replication-code/input rights, indexed-page/pivot-count discrepancy and exact GL001 input join '
            'remain unresolved; no model execution.',
  'status': 'held_for_separate_work'}]

CORRECTIONS = [{'correction': 'Repository baseline advanced from research-time 6c2a4aa to d196d9c; frozen64 and all nine '
                'earlier catalogs compared anew.',
  'correction_id': 'TD-C01'},
 {'correction': 'FineWeb2 paper 1320/1868 domain-composition claim is version-specific; later CSV has 1870 '
                'filtered-train language-script rows. Do not mix denominators.',
  'correction_id': 'TD-C02'},
 {'correction': 'Common Crawl share sums may deviate from 100 through rounding; exact page sums and per-row '
                'tolerance are separate tests.',
  'correction_id': 'TD-C03'},
 {'correction': 'Current pinned Collapse producer code confirms bias=True; manuscript covariance formula '
                'remains a separately recorded discrepancy.',
  'correction_id': 'TD-C04'},
 {'correction': 'HelpSteer2 real-data experimental role is distinct from model-generated responses and human '
                'ratings.',
  'correction_id': 'TD-C05'},
 {'correction': 'Unknown CSV/metadata/results/code rights remain scoped unknowns; no source license '
                'propagates to content or other artifacts.',
  'correction_id': 'TD-C06'},
 {'correction': 'DPI template is illustrative, not JSON Schema; 109 non-template JSON collection files are '
                'not a current dataset-record count.',
  'correction_id': 'TD-C07'},
 {'correction': 'Consent denominator, domain exclusion and absence-of-consent caveats are verified in v2 '
                'PDF; parsed HTML omitted those details.',
  'correction_id': 'TD-C08'},
 {'correction': 'Collapse export-era filenames and sampling differ from current helper; configured run/row '
                'totals cannot become observed export coverage.',
  'correction_id': 'TD-C09'},
 {'correction': 'Epoch paper indexed-page assumptions and pivot-word counts differ from pinned code/input; '
                'keep estimates, inputs and versions separate without reproduction claims.',
  'correction_id': 'TD-C10'},
 {'correction': 'Common Crawl unknown.urls is a residual-page scalar, not a measured unknown-language URL '
                'cardinality; preserve native value without enforcing URL-sum equality.',
  'correction_id': 'TD-C11'}]
