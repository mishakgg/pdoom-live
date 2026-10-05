"""Shape checks for the US federal AI publication catalog. No network."""

from __future__ import annotations

import copy
import socket

import pytest

from pdoom_pipeline.catalogs.us_federal import (
    MAX_HASHED_BYTES,
    CatalogError,
    content_hash_for_small_payload,
    load_catalog,
    validate_entry,
)

REQUIRED_FIELDS = (
    "title",
    "publisher",
    "canonical_url",
    "publication_date",
    "rights",
    "final_url",
    "retrieved_at",
)


def _sample() -> dict:
    return copy.deepcopy(load_catalog()["entries"][0])


def test_catalog_shape_required_fields_and_government_works():
    catalog = load_catalog()
    assert catalog["catalog_id"] == "us_federal_ai_publications"
    assert isinstance(catalog["description"], str) and catalog["description"].strip()
    entries = catalog["entries"]
    assert isinstance(entries, list) and entries
    kinds = set()
    for entry in entries:
        for field in REQUIRED_FIELDS:
            assert entry[field]
        assert entry["rights"] == "us_government_work"
        assert entry["publication_date"] == "unknown" or len(entry["publication_date"]) == 10
        assert entry["retrieval_method"] in {"HEAD", "GET"}
        assert entry["canonical_url"].startswith("https://")
        assert entry["final_url"].startswith("https://")
        assert entry["hashed_bytes"] <= MAX_HASHED_BYTES
        assert entry["content_hash"].startswith("sha256:")
        kinds.add(entry["kind"])
    assert kinds == {"nist_publication", "gao_report", "congressional_hearing"}


def test_non_government_url_is_rejected():
    entry = _sample()
    entry["canonical_url"] = "https://example.com/ai-risk-framework"
    entry["final_url"] = entry["canonical_url"]
    with pytest.raises(CatalogError, match="non-government"):
        validate_entry(entry)

    doi = _sample()
    doi["canonical_url"] = "https://doi.org/10.6028/NIST.AI.100-1"
    doi["final_url"] = doi["canonical_url"]
    with pytest.raises(CatalogError, match="non-government"):
        validate_entry(doi)

    lookalike = _sample()
    lookalike["canonical_url"] = "https://nist.gov.example/NIST.AI.100-1.pdf"
    lookalike["final_url"] = lookalike["canonical_url"]
    with pytest.raises(CatalogError, match="non-government"):
        validate_entry(lookalike)


def test_unknown_publication_date_is_accepted_and_other_rights_are_rejected():
    unknown = _sample()
    unknown["publication_date"] = "unknown"
    validate_entry(unknown)

    missing = _sample()
    del missing["publisher"]
    with pytest.raises(CatalogError, match="publisher"):
        validate_entry(missing)

    wrong_rights = _sample()
    wrong_rights["rights"] = "cc-by"
    with pytest.raises(CatalogError, match="us_government_work"):
        validate_entry(wrong_rights)


def test_content_hash_is_only_kept_for_a_small_header_or_snippet():
    assert content_hash_for_small_payload(b"a" * MAX_HASHED_BYTES).startswith("sha256:")
    assert content_hash_for_small_payload(b"a" * (MAX_HASHED_BYTES + 1)) is None
    assert content_hash_for_small_payload(b"") is None

    oversized = _sample()
    oversized["hashed_bytes"] = MAX_HASHED_BYTES + 1
    with pytest.raises(CatalogError, match="2048"):
        validate_entry(oversized)


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    catalog = load_catalog()
    assert len(catalog["entries"]) == 10
