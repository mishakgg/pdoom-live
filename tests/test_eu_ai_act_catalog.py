"""Offline checks for the official EU AI Act metadata catalog."""

from __future__ import annotations

import copy
import json
import socket

import pytest

from pdoom_pipeline.catalogs.eu_ai_act import (
    CATALOG_ID,
    MAX_TEXT_CHARS,
    RIGHTS_CC_BY_4_0,
    RIGHTS_UNKNOWN,
    CatalogError,
    catalog_path,
    is_official_host,
    load_catalog,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
)

EXPECTED = [
    (
        "Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU, (EU) 2016/797 and (EU) 2020/1828 (Artificial Intelligence Act) (Text with EEA relevance)",
        "European Parliament and the Council",
        "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
        "2024-07-12",
    ),
    (
        "AI Act",
        "European Commission",
        "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
        "unknown",
    ),
    (
        "European Artificial Intelligence Act comes into force",
        "European Commission",
        "https://digital-strategy.ec.europa.eu/en/news/european-artificial-intelligence-act-comes-force",
        "2024-08-01",
    ),
    (
        "European AI Office",
        "European Commission",
        "https://digital-strategy.ec.europa.eu/en/policies/ai-office",
        "unknown",
    ),
    (
        "Governance and enforcement of the AI Act",
        "European Commission",
        "https://digital-strategy.ec.europa.eu/en/policies/ai-act-governance-and-enforcement",
        "unknown",
    ),
    (
        "The enforcement framework of the AI Act",
        "European Commission",
        "https://digital-strategy.ec.europa.eu/en/policies/enforcement-ai-act",
        "unknown",
    ),
    (
        "Navigating the AI Act",
        "European Commission",
        "https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act",
        "unknown",
    ),
]

OFFICIAL_URLS = [
    "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
    "https://digital-strategy.ec.europa.eu/en/policies/ai-office",
    "https://ec.europa.eu/example/ai-act",
    "https://commission.europa.eu/example/ai-act",
]

REJECTED_URLS = [
    "https://artificialintelligenceact.eu/the-act",
    "https://en.wikipedia.org/wiki/Artificial_Intelligence_Act",
    "https://example.com/ai-act",
    "https://data.europa.eu/eli/reg/2024/1689/oj",
    "https://europa.eu/ai-act",
    "https://op.europa.eu/en/publication-detail",
    "https://eur-lex.europa.eu.example/eli/reg/2024/1689/oj",
    "https://not-eur-lex.europa.eu/eli/reg/2024/1689/oj",
    "https://ec.europa.eu.evil.test/ai-act",
    "http://eur-lex.europa.eu/eli/reg/2024/1689/oj",
    "https://user:pass@eur-lex.europa.eu/eli/reg/2024/1689/oj",
    "https://digital-strategy.ec.europa.eu/en/policies/ai-act?utm_source=x",
    "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng#text",
    "https://127.0.0.1/eli/reg/2024/1689/oj",
]


def test_catalog_load_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("catalog load must not use the network")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    document = load_catalog()
    assert document["catalog_id"] == CATALOG_ID
    assert len(document["entries"]) == len(EXPECTED)


def test_catalog_rows_are_confirmed_official_pages():
    document = load_catalog()
    assert catalog_path().name == "eu_ai_act.json"
    blob = catalog_path().read_text(encoding="utf-8")
    assert len(blob) < 8000
    assert "Having regard to the Treaty" not in blob
    assert "free and open-source licence" not in blob
    entries = document["entries"]
    assert [entry["canonical_url"] for entry in entries] == [row[2] for row in EXPECTED]
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, publisher, url, published = expected
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["title"] == title
        assert entry["publisher"] == publisher
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == RIGHTS_UNKNOWN
        assert len(entry["title"]) <= MAX_TEXT_CHARS
        assert is_official_host(url.split("/")[2])
        host = url.split("/")[2]
        assert host == "eur-lex.europa.eu" or host.endswith(".ec.europa.eu")


def test_pages_that_do_not_state_a_reuse_licence_stay_unknown():
    reserved = "<footer>© European Union, 2024. All rights reserved.</footer>"
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    act_mention = (
        "<p>Providers shall put in place a policy to comply with Union copyright law.</p>"
        "<p>The model is released under a free and open-source licence.</p>"
        "<p>the licence for the model.</p>"
    )
    assert rights_from_page(act_mention) == RIGHTS_UNKNOWN
    hidden = "<script>Creative Commons Attribution 4.0 International (CC BY 4.0)</script><p>No reuse licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_a_stated_cc_by_4_licence_is_labeled():
    page = (
        "<p>Introductory notice.</p>"
        "<p>Unless otherwise indicated, reuse is authorised under the "
        "Creative Commons Attribution 4.0 International (CC BY 4.0) licence.</p>"
    )
    assert rights_from_page(page) == RIGHTS_CC_BY_4_0
    document = copy.deepcopy(load_catalog())
    document["entries"][1]["rights"] = RIGHTS_CC_BY_4_0
    validate_catalog(document)


def test_non_official_hosts_are_rejected():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["canonical_url"] = "https://artificialintelligenceact.eu/the-act"
    with pytest.raises(CatalogError, match="not an official"):
        validate_catalog(document)


@pytest.mark.parametrize("url", OFFICIAL_URLS)
def test_official_eur_lex_and_commission_hosts_are_accepted(url: str):
    assert validate_canonical_url(url) == url


def test_validator_rejects_long_text_bad_dates_and_unknown_rights_labels(tmp_path):
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = "unknown"
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = "12 July 2024"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document["entries"][0]["date"] = "2024-07-32"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = "all_rights_reserved"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["title"] = "x" * (MAX_TEXT_CHARS + 1)
    with pytest.raises(CatalogError, match="too long"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["regulation_text"] = "Article 1 " + ("harmonised rules " * 40)
    with pytest.raises(CatalogError, match="entry fields"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        load_catalog(duplicate)
