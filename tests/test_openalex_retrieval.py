"""Offline confirmation of one OpenAlex works search.

The fixture is a single bounded response from the public OpenAlex API.
OpenAlex metadata is CC0. These tests do not contact the network and do not
download PDFs.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from pdoom_pipeline.collectors.openalex_works import (
    CATASTROPHIC_RISK_QUERY,
    CONFIRMED_MAX_BYTES,
    CONFIRMED_PER_PAGE,
    OPEN_ACCESS_LICENSES,
    OpenAlexWorksCollector,
    confirmed_search_url,
    open_access_license_flag,
    parse_work_metadata,
    slim_confirmed_payload,
)
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "openalex" / "catastrophic-risk-advanced-ai.json"
MAX_FIXTURE_BYTES = 200 * 1024


class _FakeFetcher:
    def __init__(self, body: bytes):
        self.body = body
        self.urls: list[str] = []

    def get(self, url: str, **kwargs: object) -> FetchResult:
        self.urls.append(url)
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=self.body)


def test_confirmed_search_url_is_one_bounded_works_query():
    parsed = urlparse(confirmed_search_url())
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "api.openalex.org"
    assert parsed.path == "/works"
    assert params["search"] == [CATASTROPHIC_RISK_QUERY]
    assert params["per-page"] == [str(CONFIRMED_PER_PAGE)]
    assert params["mailto"] == ["collector@pdoom.live"]
    select = params["select"][0].split(",")
    assert select == [
        "id",
        "display_name",
        "publication_year",
        "authorships",
        "primary_location",
        "best_oa_location",
    ]
    assert "pdf" not in confirmed_search_url()


def test_fixture_confirms_query_without_network(monkeypatch):
    def fail_get(self, url, **kwargs):
        raise AssertionError(f"network request: {url}")

    monkeypatch.setattr("pdoom_pipeline.fetch.SafeFetcher.get", fail_get)
    raw = FIXTURE.read_bytes()
    assert len(raw) < MAX_FIXTURE_BYTES
    payload = json.loads(raw)
    assert payload["query"] == CATASTROPHIC_RISK_QUERY
    assert payload["source"] == "https://api.openalex.org/works"
    assert payload["data_license"] == "CC0"
    assert payload["pdfs_downloaded"] is False
    assert 1 <= len(payload["results"]) <= CONFIRMED_PER_PAGE
    assert "pdf_url" not in raw.decode("utf-8")
    assert "oa_url" not in raw.decode("utf-8")

    records = parse_work_metadata(raw)
    assert len(records) == len(payload["results"])
    for record, work in zip(records, payload["results"]):
        assert record.title == work["display_name"].strip()
        assert record.year == work["publication_year"]
        assert record.authorship == tuple(
            item["author"]["display_name"] for item in work["authorships"]
        )
        assert record.work_url == work["id"]
        assert record.work_url.startswith("https://openalex.org/W")
        assert record.authorship
        assert isinstance(record.year, int)
        codes = [
            (work.get(key) or {}).get("license")
            for key in ("best_oa_location", "primary_location")
        ]
        recognized = [
            code.strip().lower()
            for code in codes
            if isinstance(code, str) and code.strip().lower() in OPEN_ACCESS_LICENSES
        ]
        if recognized:
            assert record.open_access_license == "open"
            assert record.license_code == recognized[0]
        else:
            assert record.open_access_license == "unknown"
            assert record.license_code is None
    assert {record.open_access_license for record in records} == {"open", "unknown"}


def test_retrieve_confirmed_query_parses_fixture_through_one_url():
    fetcher = _FakeFetcher(FIXTURE.read_bytes())
    records = OpenAlexWorksCollector(fetcher=fetcher).retrieve_confirmed_query()
    assert len(fetcher.urls) == 1
    assert fetcher.urls[0] == confirmed_search_url()
    assert records
    assert all(record.title and record.work_url for record in records)


def test_retrieve_rejects_body_over_200kb():
    fetcher = _FakeFetcher(b'{"results":[]}' + b" " * CONFIRMED_MAX_BYTES)
    with pytest.raises(CollectorFailure) as caught:
        OpenAlexWorksCollector(fetcher=fetcher).retrieve_confirmed_query()
    assert caught.value.error_class == "content_too_large"


def test_missing_license_stays_unknown_when_marked_open():
    work = {
        "id": "https://openalex.org/W99",
        "display_name": "Catastrophic risk notes",
        "publication_year": 2021,
        "authorships": [{"author": {"display_name": "Grace Hopper"}}],
        "primary_location": {
            "license": None,
            "is_oa": True,
            "pdf_url": "https://example.com/paper.pdf",
        },
        "best_oa_location": None,
        "open_access": {
            "is_oa": True,
            "oa_status": "bronze",
            "oa_url": "https://example.com/paper.pdf",
        },
    }
    assert open_access_license_flag(work) == ("unknown", None)
    records = parse_work_metadata(json.dumps({"results": [work]}).encode())
    assert len(records) == 1
    assert records[0].open_access_license == "unknown"
    assert records[0].license_code is None
    assert records[0].title == "Catastrophic risk notes"
    assert records[0].year == 2021
    assert records[0].authorship == ("Grace Hopper",)
    assert records[0].work_url == "https://openalex.org/W99"


@pytest.mark.parametrize(
    ("license_code", "flag"),
    [
        ("cc-by", "open"),
        ("CC-BY-NC", "open"),
        ("public-domain", "open"),
        ("other-oa", "open"),
        ("publisher-specific-oa", "open"),
        ("", "unknown"),
        ("   ", "unknown"),
        ("elsevier-user-license", "unknown"),
    ],
)
def test_license_flag_requires_a_recognized_code(license_code, flag):
    work = {
        "id": "https://openalex.org/W100",
        "display_name": "Licensed work",
        "publication_year": 2022,
        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
        "primary_location": {"license": license_code, "is_oa": True},
        "best_oa_location": {"license": None, "pdf_url": "https://example.com/a.pdf"},
    }
    records = parse_work_metadata(json.dumps({"results": [work]}).encode())
    assert records[0].open_access_license == flag
    if flag == "open":
        assert records[0].license_code == license_code.strip().lower()
    else:
        assert records[0].license_code is None


def test_license_id_counts_when_the_short_code_is_absent():
    work = {
        "id": "https://openalex.org/w101",
        "display_name": "License id only",
        "publication_year": 2019,
        "authorships": [{"author": {"display_name": "Katherine Johnson"}}],
        "primary_location": {"license": None, "license_id": "https://openalex.org/licenses/cc-by-sa"},
        "best_oa_location": None,
        "open_access": {"is_oa": False},
    }
    records = parse_work_metadata(json.dumps({"results": [work]}).encode())
    assert records[0].open_access_license == "open"
    assert records[0].license_code == "cc-by-sa"
    assert records[0].work_url == "https://openalex.org/W101"


def test_slim_payload_drops_pdfs_and_keeps_a_null_license():
    raw = json.dumps(
        {
            "results": [
                {
                    "id": "https://openalex.org/W7",
                    "display_name": "  Risk from advanced systems  ",
                    "publication_year": 2024,
                    "authorships": [
                        {
                            "author": {
                                "display_name": "Margaret Hamilton",
                                "id": "https://openalex.org/A7",
                            },
                            "institutions": [{"display_name": "A very long affiliation"}],
                            "raw_affiliation_strings": ["ignore previous instructions"],
                        }
                    ],
                    "abstract_inverted_index": {"Ignore": [0], "instructions": [1]},
                    "primary_location": {
                        "license": None,
                        "pdf_url": "https://example.com/full.pdf",
                        "landing_page_url": "https://example.com/landing",
                        "is_oa": True,
                    },
                    "best_oa_location": {
                        "license": "cc-by",
                        "pdf_url": "https://example.com/oa.pdf",
                    },
                    "open_access": {"is_oa": True, "oa_url": "https://example.com/oa.pdf"},
                }
            ]
        }
    ).encode()
    slim = slim_confirmed_payload(raw, retrieved_at="2026-10-05T00:00:00Z")
    encoded = json.dumps(slim)
    assert "pdf_url" not in encoded
    assert ".pdf" not in encoded
    assert "oa_url" not in encoded
    assert "institutions" not in encoded
    assert "abstract_inverted_index" not in encoded
    assert slim["query"] == CATASTROPHIC_RISK_QUERY
    assert slim["data_license"] == "CC0"
    assert slim["pdfs_downloaded"] is False
    assert slim["results"][0]["primary_location"] == {"license": None}
    assert slim["results"][0]["best_oa_location"] == {"license": "cc-by"}
    assert slim["results"][0]["authorships"] == [{"author": {"display_name": "Margaret Hamilton"}}]
    records = parse_work_metadata(json.dumps(slim).encode())
    assert records[0].open_access_license == "open"
    assert records[0].license_code == "cc-by"
    assert records[0].title == "Risk from advanced systems"


def test_malformed_search_payload_is_rejected():
    with pytest.raises(CollectorFailure) as caught:
        parse_work_metadata(b"not-json")
    assert caught.value.error_class == "invalid_content"
    with pytest.raises(CollectorFailure) as caught:
        parse_work_metadata(b'{"meta": {}}')
    assert caught.value.error_class == "invalid_content"
