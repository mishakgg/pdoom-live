#!/usr/bin/env python3
"""Read two pinned, supplied Common Crawl statistics CSVs, without networking.

Only three crawl aggregates are emitted. This is an experimental review format,
not a production import, corpus manifest, license determination or token estimate.
Synthetic mode validates the same CSV contract but cannot claim source byte/date
verification. No full source CSV is bundled with this reader.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
from decimal import Decimal, localcontext
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA_VERSION = 'common-crawl-statistics-review-v1'
SOURCE_REPOSITORY = 'https://github.com/commoncrawl/cc-crawl-statistics'
SOURCE_COMMIT = '1053c982a91ba0bb4323c5f00ec3230d9cd54e4b'
ALLOWED_CRAWLS = ('CC-MAIN-2026-30', 'CC-MAIN-2026-34', 'CC-MAIN-2026-39')
LANGUAGES_PATH = 'plots/languages.csv'
MONTHLY_PATH = 'plots/crawlsize/monthly.csv'
LANGUAGES_HEADER = ('crawl', 'primary_language', 'pages', 'urls', '%pages/crawl')
MONTHLY_HEADER = ('crawl', 'digest estim.', 'page', 'url')
SOURCE_SHA256 = {
    LANGUAGES_PATH: '4f3b987a60d72a356c480d788a930388ebe05225307aec7fc280513f6f9b0cff',
    MONTHLY_PATH: 'b49fb0e4acd9cd3a4676cc4bad17eca9645e38dcecfea1dfc3f2436a1c7b98a7',
}
MAX_BYTES = {LANGUAGES_PATH: 1024 * 1024, MONTHLY_PATH: 64 * 1024}
MAX_ROWS = {LANGUAGES_PATH: 20000, MONTHLY_PATH: 256}
MAX_FIELD_BYTES = 128
MAX_PHYSICAL_LINE_BYTES = 1024
MAX_LANGUAGES_PER_CRAWL = 512
MAX_COUNT = 10 ** 12
PERCENTAGE_TOLERANCE = Decimal('0.00005')  # Percentage points, inclusive.
UNKNOWN_LANGUAGE = '<unknown>'
# Verified release announcements, not times inferred from crawl IDs or commits.
# Day precision; the source does not establish a timezone for these dates.
CRAWL_DATES = {
    'CC-MAIN-2026-30': ('2026-07-07', '2026-07-25', '2026-07-28'),
    'CC-MAIN-2026-34': ('2026-08-07', '2026-08-20', '2026-08-24'),
    'CC-MAIN-2026-39': ('2026-09-04', '2026-09-17', '2026-09-19'),
}
ANNOUNCEMENT_URLS = {
    'CC-MAIN-2026-30': 'https://commoncrawl.org/blog/july-2026-crawl-archive-now-available',
    'CC-MAIN-2026-34': 'https://commoncrawl.org/blog/august-2026-crawl-archive-now-available',
    'CC-MAIN-2026-39': 'https://commoncrawl.org/blog/september-2026-crawl-archive-now-available',
}


class StatisticsInputError(ValueError):
    """The supplied input violates the bounded, pinned review contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StatisticsInputError(message)


def _cell(value: str) -> None:
    _require(0 < len(value.encode('utf-8')) <= MAX_FIELD_BYTES,
             'CSV field must be nonempty and within the byte limit')
    _require(not any(ord(char) < 32 or ord(char) == 127 for char in value),
             'CSV fields must not contain control characters or multiline values')


def _count(value: str, label: str, *, positive: bool = False) -> int:
    _require(re.fullmatch(r'(?:0|[1-9][0-9]{0,12})', value, re.ASCII) is not None,
             f'{label} must be a nonnegative finite decimal integer')
    result = int(value)
    _require((1 if positive else 0) <= result <= MAX_COUNT,
             f'{label} exceeds the allowed count magnitude')
    return result


def _percentage(value: str) -> Decimal:
    _require(re.fullmatch(r'(?:0|[1-9][0-9]{0,2})\.[0-9]{4}', value, re.ASCII) is not None,
             'percentage must be a finite decimal with exactly four decimal places')
    result = Decimal(value)
    _require(result.is_finite() and Decimal(0) <= result <= Decimal(100),
             'percentage must be between zero and one hundred')
    return result


def _crawl(value: str) -> None:
    legacy = {'CC-MAIN-2008-2009', 'CC-MAIN-2009-2010', 'CC-MAIN-2012'}
    _require(value in legacy or re.fullmatch(r'CC-MAIN-20[0-9]{2}-(?:0[1-9]|[1-4][0-9]|5[0-3])',
                                           value, re.ASCII) is not None,
             'invalid native crawl identifier')


def _rows(raw: bytes, artifact_path: str, header: tuple[str, ...]) -> list[dict]:
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES[artifact_path],
             'CSV input must be nonempty bytes within the artifact byte limit')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise StatisticsInputError('CSV input must be UTF-8') from exc
    _require(not text.startswith('\ufeff'), 'CSV byte-order marks are unsupported')
    # No native field can contain a newline. Bound physical records before CSV
    # parsing as well as fields/rows after parsing; never change global CSV limits.
    _require(all(len(line.encode('utf-8')) <= MAX_PHYSICAL_LINE_BYTES
                 for line in text.splitlines()), 'CSV physical line byte limit exceeded')
    result = []
    try:
        reader = csv.reader(StringIO(text, newline=''), strict=True)
        _require(tuple(next(reader)) == header, 'CSV header or field order differs from the exact native schema')
        for values in reader:
            _require(len(result) < MAX_ROWS[artifact_path], 'CSV row count limit exceeded')
            _require(len(values) == len(header), 'CSV row has missing or extra fields')
            for value in values:
                _cell(value)
            result.append(dict(zip(header, values)))
    except (csv.Error, StopIteration) as exc:
        raise StatisticsInputError('invalid CSV syntax') from exc
    _require(bool(result), 'CSV must contain data rows')
    return result


def _observed_at(value: str | None) -> None:
    if value is None:
        return
    _require(type(value) is str and re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', value) is not None,
        'observed_at_utc must be null or an explicit second-precision UTC timestamp')
    try:
        datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError as exc:
        raise StatisticsInputError('invalid observed_at_utc date/time') from exc


def _dates(crawl: str, synthetic: bool) -> dict:
    start, end, release = CRAWL_DATES[crawl]
    try:
        _require(all(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) for value in (start, end, release))
                 and date.fromisoformat(start) <= date.fromisoformat(end) <= date.fromisoformat(release),
                 'invalid pinned crawl date ordering')
    except ValueError as exc:
        raise StatisticsInputError('invalid pinned crawl date') from exc
    return {
        'capture_started_on': None if synthetic else start,
        'capture_ended_on': None if synthetic else end,
        'released_on': None if synthetic else release,
        'date_precision': None if synthetic else 'day',
        'source_timezone': None,
        'date_evidence_url': None if synthetic else ANNOUNCEMENT_URLS[crawl],
        'date_basis': 'synthetic_dates_unknown' if synthetic else 'verified_release_announcement',
        'underlying_content_published_at': None,
        'statistics_published_at': None,
    }


def validate_statistics_bytes(languages_raw: bytes, monthly_raw: bytes, *,
                              synthetic_fixture: bool = False,
                              observed_at_utc: str | None = None) -> dict:
    """Validate complete supplied bytes and emit only the three allowed crawls.

    Default mode requires both exact full-artifact hashes at SOURCE_COMMIT.
    Explicit synthetic mode tests the contract with invented counts; source hashes
    and dates stay unknown, and observation IDs have a separate synthetic scope.
    observed_at_utc is optional caller-reported observation time, never publication
    or source acquisition time. Repeating the same import does not create new IDs.
    """
    _require(type(synthetic_fixture) is bool, 'synthetic_fixture must be a boolean')
    _observed_at(observed_at_utc)
    inputs = {LANGUAGES_PATH: languages_raw, MONTHLY_PATH: monthly_raw}
    language_rows = _rows(languages_raw, LANGUAGES_PATH, LANGUAGES_HEADER)
    monthly_rows = _rows(monthly_raw, MONTHLY_PATH, MONTHLY_HEADER)
    hashes = {path: hashlib.sha256(raw).hexdigest() for path, raw in inputs.items()}
    if not synthetic_fixture:
        _require(hashes == SOURCE_SHA256, 'supplied CSV bytes do not match the two pinned source SHA-256 hashes')

    monthly = {}
    for row in monthly_rows:
        crawl = row['crawl']
        _crawl(crawl)
        _require(crawl not in monthly, 'duplicate monthly crawl identity')
        page = _count(row['page'], 'page', positive=True)
        url = _count(row['url'], 'url')
        digest = _count(row['digest estim.'], 'digest estim.')
        _require(url <= page, 'URL cardinality cannot exceed page captures in a monthly row')
        # Digest cardinality is estimated; do not require digest <= URL/page.
        monthly[crawl] = (row, page, url, digest)

    languages = {}
    by_crawl = {}
    for row in language_rows:
        crawl, language = row['crawl'], row['primary_language']
        _crawl(crawl)
        _require(language == UNKNOWN_LANGUAGE or re.fullmatch(r'[a-z]{3}', language, re.ASCII) is not None,
                 'invalid native primary-language label')
        key = (crawl, language)
        _require(key not in languages, 'duplicate crawl/language identity')
        pages = _count(row['pages'], 'pages')
        urls = _count(row['urls'], 'urls')
        percentage = _percentage(row['%pages/crawl'])
        _require(urls <= pages, 'URL cardinality cannot exceed page captures in a language row')
        languages[key] = (row, pages, urls, percentage)
        by_crawl.setdefault(crawl, []).append(key)
        _require(len(by_crawl[crawl]) <= MAX_LANGUAGES_PER_CRAWL, 'languages per crawl limit exceeded')

    # Historical rows are syntax/type/duplicate checked but are not admitted to
    # the output or interpreted as additional reviewed crawl observations.
    for crawl in ALLOWED_CRAWLS:
        _require(crawl in monthly and crawl in by_crawl, 'all three allowed crawls must occur in both inputs')
        _require((crawl, UNKNOWN_LANGUAGE) in languages, 'selected crawl must retain its explicit unknown-language bucket')
        unknown = languages[(crawl, UNKNOWN_LANGUAGE)]
        _require(unknown[2] == unknown[1],
                 'selected unknown native urls must equal its page-residual scalar, not a URL cardinality sum')
        total = monthly[crawl][1]
        _require(sum(languages[key][1] for key in by_crawl[crawl]) == total,
                 'selected-crawl language page sum, including unknown, must equal monthly page captures')
        with localcontext() as context:
            context.prec = 40
            for key in by_crawl[crawl]:
                _, pages, _, percentage = languages[key]
                # Multiplication comparison avoids division/rounding artifacts.
                _require(abs(percentage * total - Decimal(pages) * 100) <= PERCENTAGE_TOLERANCE * total,
                         'reported percentage exceeds the four-decimal rounding tolerance')

    scope = 'synthetic-commoncrawl' if synthetic_fixture else 'commoncrawl'
    pair_hash = hashlib.sha256((hashes[LANGUAGES_PATH] + ':' + hashes[MONTHLY_PATH]).encode('ascii')).hexdigest()
    revision = f'{scope}:statistics:{SOURCE_COMMIT}:{pair_hash}'
    summaries, observations = [], []
    for crawl in ALLOWED_CRAWLS:
        native, pages, urls, digest = monthly[crawl]
        entity_id = f'{scope}:{crawl}'
        summaries.append({
            'crawl_id': crawl,
            'crawl_entity_id': entity_id,
            'observation_id': f'{revision}:{crawl}:monthly',
            'source_artifact_path': MONTHLY_PATH,
            'evidence_locator': f'crawl={crawl}',
            'native_fields': native,
            'page_captures': pages,
            'url_cardinality': urls,
            'digest_estimated_cardinality': digest,
            'page_is_estimate': False,
            'url_is_estimate': False,
            'digest_is_estimate': True,
            'language_page_sum_including_unknown': sum(languages[key][1] for key in by_crawl[crawl]),
            'language_row_count': len(by_crawl[crawl]),
            **_dates(crawl, synthetic_fixture),
        })
        for key in sorted(by_crawl[crawl]):
            native, pages, urls, _ = languages[key]
            language = key[1]
            observations.append({
                'crawl_id': crawl,
                'crawl_entity_id': entity_id,
                'observation_id': f'{revision}:{crawl}:language:{language}',
                'source_artifact_path': LANGUAGES_PATH,
                'evidence_locator': f'crawl={crawl};primary_language={language}',
                'native_fields': native,
                'primary_language': language,
                'language_detector': None if synthetic_fixture else 'CLD2',
                'language_detector_version': None,
                'language_detection_scope': None if synthetic_fixture else 'HTML_only',
                'language_assignment_basis': ('residual_bucket_classification_unavailable'
                                              if language == UNKNOWN_LANGUAGE else
                                              ('synthetic_fixture_label' if synthetic_fixture else 'first_CLD2_language')),
                'denominator_metric': 'page_captures',
                'denominator_value': monthly[crawl][1],
                'page_is_estimate': False,
                'url_is_estimate': None if language == UNKNOWN_LANGUAGE else False,
                'language_status': 'unknown' if language == UNKNOWN_LANGUAGE else 'source_reported_classifier_label',
                'page_captures': pages,
                'page_count_basis': ('residual_monthly_pages_after_labeled_buckets'
                                     if language == UNKNOWN_LANGUAGE else 'source_reported_capture_count'),
                'url_cardinality': None if language == UNKNOWN_LANGUAGE else urls,
                'url_count_basis': ('page_residual_placeholder_not_measured_URL_cardinality'
                                    if language == UNKNOWN_LANGUAGE else 'source_reported_URL_cardinality'),
                'pages_percent_of_crawl_decimal': native['%pages/crawl'],
            })
    artifacts = []
    for path in (LANGUAGES_PATH, MONTHLY_PATH):
        artifacts.append({
            'expected_source_repository': SOURCE_REPOSITORY,
            'expected_source_commit': SOURCE_COMMIT,
            'expected_source_path': path,
            'expected_source_url': f'{SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/{path}',
            'pinned_source_sha256': SOURCE_SHA256[path],
            'supplied_bytes_sha256': hashes[path],
            'supplied_byte_count': len(inputs[path]),
            'source_sha256': None if synthetic_fixture else hashes[path],
            'source_commit': None if synthetic_fixture else SOURCE_COMMIT,
            'source_path': None if synthetic_fixture else path,
            'source_byte_pin_verified': not synthetic_fixture,
            'source_acquired_at_utc': None,
            'source_publication_at': None,
            'csv_specific_license': None,
            'csv_redistribution_rights': 'unknown',
        })
    return {
        'schema_version': SCHEMA_VERSION,
        'status': 'experimental_review_records_not_admitted',
        'synthetic': synthetic_fixture,
        'canonical_import_enabled': False,
        'network_access_performed': False,
        'source_execution_performed': False,
        'source_bytes_acquired_by_reader': False,
        'supplied_bytes_read': True,
        'observed_at_utc': observed_at_utc,
        'observed_at_basis': None if observed_at_utc is None else 'caller_reported_not_source_publication',
        'statistics_revision_id': revision,
        'crawl_count': len(summaries),
        'source_artifacts': artifacts,
        'crawl_summaries': summaries,
        'language_observations': observations,
        'measurement_definitions': {
            'page_captures': {'unit': 'captures', 'count_method': 'source_reported_capture_count',
                              'is_estimate': False},
            'url_cardinality': {'unit': 'distinct_URLs_within_source_row_scope',
                                'count_method': 'source_reported_URL_cardinality', 'is_estimate': False,
                                'unknown_language_exception': 'null_cardinality_native_field_is_page_residual'},
            'digest_estimated_cardinality': {'unit': 'distinct_content_digests',
                                            'count_method': 'source_reported_estimated_cardinality',
                                            'is_estimate': True},
            'pages_percent_of_crawl_decimal': {'unit': 'percentage_points',
                                              'denominator_metric': 'monthly_page_captures',
                                              'count_method': 'source_reported_rounded_capture_share',
                                              'decimal_places': 4},
        },
        'interpretation_evidence': {
            'primary_language_and_HTML_detection_scope': f'{SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/plots/languages.md',
            'unknown_page_residual_and_export': f'{SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/plot/table.py#L111-L128',
            'scalar_reused_for_native_page_and_url_fields': f'{SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/crawlstats.py#L404-L410',
        },
        'rights': {
            'repository_code_license': 'Apache-2.0',
            'code_license_applies_to_csv_or_underlying_pages': False,
            'csv_specific_license': None,
            'csv_redistribution_rights': 'unknown',
            'underlying_pages_rights': 'unknown',
        },
        'interpretation': {
            'page': 'captures_not_unique_content_or_tokens',
            'url': 'source_reported_URL_cardinality_not_unique_usable_training_supply',
            'digest_estim': 'estimated_digest_cardinality_not_exact_unique_content',
            'language': 'primary_language_classifier_bucket_including_explicit_unknown',
            'percentage': 'page_capture_share_four_decimal_percentage_points_not_token_share',
            'percentage_rounding_tolerance_points': str(PERCENTAGE_TOLERANCE),
            'published_percentages_need_not_sum_exactly_100': True,
            'url_cardinalities_not_summed_across_language_buckets': True,
            'unknown_urls': 'native_scalar_is_page_residual_placeholder_normalized_URL_cardinality_is_null',
            'historical_rows': 'bounded_syntax_and_types_checked_but_not_emitted_or_cross_validated',
            'identity': 'native_crawl_identity_separate_from_revision_and_supplied_byte_scoped_observation',
            'revision_policy': 'only_fixed_source_revision_accepted_new_versions_require_explicit_review',
            'filesystem_locality': 'regular_POSIX_path_does_not_prove_local_mount',
            'validation_scope': 'byte_pin_and_structural_consistency_not_source_truth_or_rights_approval',
        },
    }


def _read_regular_file(path: str | Path, limit: int) -> bytes:
    """Use descriptor-relative no-follow reads; reject devices, FIFOs and traversal."""
    try:
        path = os.fspath(path)
    except TypeError as exc:
        raise StatisticsInputError('expected a bounded local regular-file path') from exc
    _require(type(path) is str and 0 < len(path) <= 4096 and '://' not in path and
             '\\' not in path and not any(ord(char) < 32 or ord(char) == 127 for char in path) and
             not path.startswith('//') and path != '-', 'expected a bounded local regular-file path')
    try:
        _require(len(path.encode('utf-8')) <= 4096, 'local path byte limit exceeded')
    except UnicodeEncodeError as exc:
        raise StatisticsInputError('path must be valid UTF-8') from exc
    parts = [part for part in path.split('/') if part not in ('', '.')]
    _require(parts and len(parts) <= 64 and '..' not in parts, 'invalid local path components')
    _require(os.name == 'posix' and all(hasattr(os, name) for name in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')),
             'safe regular-file opening is unavailable')
    directory = descriptor = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory = os.open('/' if path.startswith('/') else '.', flags)
        for part in parts[:-1]:
            child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                             getattr(os, 'O_NOCTTY', 0), dir_fd=directory)
        info = os.fstat(descriptor)
        _require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit,
                 'expected a nonempty regular file within the artifact byte limit')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            raw = stream.read(limit + 1)
        _require(0 < len(raw) <= limit, 'CSV file grew beyond the artifact byte limit')
        return raw
    except (OSError, UnicodeError) as exc:
        raise StatisticsInputError('cannot read supplied no-symlink local regular file') from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def read_statistics(languages_path: str | Path, monthly_path: str | Path, *,
                    synthetic_fixture: bool = False, observed_at_utc: str | None = None) -> dict:
    """Read supplied local files only; the operating system's mount locality is unknown."""
    return validate_statistics_bytes(_read_regular_file(languages_path, MAX_BYTES[LANGUAGES_PATH]),
                                     _read_regular_file(monthly_path, MAX_BYTES[MONTHLY_PATH]),
                                     synthetic_fixture=synthetic_fixture, observed_at_utc=observed_at_utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('languages', help='supplied local plots/languages.csv')
    parser.add_argument('monthly', help='supplied local plots/crawlsize/monthly.csv')
    parser.add_argument('--synthetic-fixture', action='store_true',
                        help='explicitly mark invented fixture counts; no source hash/date claim')
    parser.add_argument('--observed-at-utc', help='optional caller-reported YYYY-MM-DDTHH:MM:SSZ')
    args = parser.parse_args(argv)
    try:
        result = read_statistics(args.languages, args.monthly, synthetic_fixture=args.synthetic_fixture,
                                 observed_at_utc=args.observed_at_utc)
    except StatisticsInputError as exc:
        parser.exit(2, f'error: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
