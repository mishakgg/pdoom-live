"""Missing canonical URL, publication time, and rights counts for one fixture document."""

from __future__ import annotations

import copy
import json

import pytest

from pdoom_pipeline.quality.report import render_source_missingness, source_missingness


def test_fixture_document_counts_missing_fields_and_leaves_unknown_unknown():
    document = {
        "sources": [
            {
                "id": "complete",
                "canonical_url": "https://example.test/complete",
                "published_at": "2024-01-15T00:00:00Z",
                "rights_notes": "Short excerpts only.",
            },
            {
                "id": "gaps",
                "canonical_url": None,
                "published_at": "",
                "license": None,
                "rights_notes": "  ",
                "observed_at": "2024-02-01T00:00:00Z",
                "url": "https://example.test/decoy",
                "feed_url": "https://example.test/feed-decoy",
            },
            {
                "id": "unknowns",
                "canonical_url": " unknown ",
                "published_at": "UNKNOWN",
                "license": "unknown",
                "rights_notes": "Unknown",
            },
            {
                "id": "license-only",
                "canonical_url": "https://example.test/licensed",
                "published_at": "2020-05-01T00:00:00Z",
                "license": "CC BY 4.0",
            },
            {
                "id": "rights-note",
                "canonical_url": "https://example.test/noted",
                "publication_time": "2022-03-04T00:00:00Z",
                "rights_note": "Store the link only.",
            },
            {
                "id": "license-with-unknown-rights",
                "canonical_url": "https://example.test/both",
                "published_at": "2021-01-01T00:00:00Z",
                "license": "CC0-1.0",
                "rights_notes": "unknown",
            },
            {
                "id": "registry-only",
                "canonical_url": "https://example.test/registry",
                "rights_notes": "Metadata only.",
            },
        ],
        "source_items": [
            {
                "slug": "item-gap",
                "canonical_url": None,
                "published_at": None,
                "observed_at": "2024-03-01T00:00:00Z",
            },
            {
                "slug": "item-unknown-time",
                "canonical_url": "https://example.test/item-unknown",
                "published_at": "unknown",
            },
            {
                "slug": "item-ok",
                "canonical_url": "https://example.test/item-ok",
                "published_at": "2021-01-01T00:00:00Z",
            },
        ],
    }
    original = copy.deepcopy(document)
    report = source_missingness(document)

    assert document == original
    assert report["sources_missing_canonical_url"] == 2
    assert report["sources_unknown_canonical_url"] == 1
    assert report["sources_missing_publication_time"] == 2
    assert report["sources_unknown_publication_time"] == 2
    assert report["sources_missing_license_or_rights_note"] == 1
    assert report["sources_unknown_license_or_rights_note"] == 1
    assert report["not_a_census"] is True
    rendered = json.dumps(report)
    assert "https://example.test/decoy" not in rendered
    assert "2024-02-01T00:00:00Z" not in rendered
    assert "2024-03-01T00:00:00Z" not in rendered
    text = rendered + render_source_missingness(report)
    assert "not all AI researchers" in text
    assert text.lower().count("all ai researchers") == text.lower().count("not all ai researchers")
    assert "Sources missing a canonical URL: 2" in text
    assert "Sources missing a publication time: 2" in text
    assert "Sources missing a license or rights note: 1" in text
    assert "left unknown: 1" in text


def test_items_carry_publication_time_and_sources_carry_rights():
    document = {
        "sources": [
            {
                "canonical_url": None,
                "rights_notes": None,
            },
            {
                "canonical_url": "https://example.test/feed",
                "rights_notes": "Excerpts only.",
            },
        ],
        "source_items": [
            {
                "canonical_url": "https://example.test/item",
                "published_at": None,
            },
            {
                "canonical_url": "unknown",
                "published_at": "2024-01-01T00:00:00Z",
            },
        ],
        "observations": [
            {
                "canonical_url": "https://example.test/observed",
                "published_at": None,
                "observed_at": "2024-04-01T00:00:00Z",
            }
        ],
    }
    report = source_missingness(document)
    assert report["sources_missing_canonical_url"] == 1
    assert report["sources_unknown_canonical_url"] == 1
    assert report["sources_missing_publication_time"] == 2
    assert report["sources_unknown_publication_time"] == 0
    assert report["sources_missing_license_or_rights_note"] == 1
    assert report["sources_unknown_license_or_rights_note"] == 0


def test_explicit_unknown_status_is_not_replaced():
    document = {
        "sources": [
            {
                "canonical_url": None,
                "canonical_url_status": "unknown",
                "published_at": None,
                "publication_time_status": "unknown",
                "license": None,
                "rights_notes": None,
                "license_status": "unknown",
            }
        ]
    }
    report = source_missingness(document)
    assert report["sources_missing_canonical_url"] == 0
    assert report["sources_unknown_canonical_url"] == 1
    assert report["sources_missing_publication_time"] == 0
    assert report["sources_unknown_publication_time"] == 1
    assert report["sources_missing_license_or_rights_note"] == 0
    assert report["sources_unknown_license_or_rights_note"] == 1
    assert document["sources"][0]["canonical_url"] is None
    assert document["sources"][0]["published_at"] is None
    assert document["sources"][0]["license"] is None


def test_sources_without_items_count_a_missing_publication_time():
    report = source_missingness(
        {
            "sources": [
                {
                    "canonical_url": "https://example.test/a",
                    "rights_notes": "Excerpts only.",
                }
            ]
        }
    )
    assert report["sources_missing_canonical_url"] == 0
    assert report["sources_missing_publication_time"] == 1
    assert report["sources_missing_license_or_rights_note"] == 0
    assert report["sources_unknown_publication_time"] == 0


def test_empty_fixture_document_reports_zero_gaps_and_is_not_a_census():
    report = source_missingness({})
    assert report["sources_missing_canonical_url"] == 0
    assert report["sources_missing_publication_time"] == 0
    assert report["sources_missing_license_or_rights_note"] == 0
    assert report["sources_unknown_canonical_url"] == 0
    assert report["sources_unknown_publication_time"] == 0
    assert report["sources_unknown_license_or_rights_note"] == 0
    assert report["not_a_census"] is True
    assert "not all AI researchers" in report["wording"]


def test_fixture_document_must_be_a_dict():
    with pytest.raises(TypeError):
        source_missingness([])  # type: ignore[arg-type]
