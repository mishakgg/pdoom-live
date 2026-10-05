"""Offline checks for the UNESCO AI ethics recommendation page catalog. No network."""

from __future__ import annotations

import copy
import inspect
import socket

import pytest

from pdoom_pipeline.catalogs.unesco_ai import (
    CATALOG_ID,
    PUBLISHER,
    RIGHTS_CC_BY_4_0,
    RIGHTS_CC_BY_NC_SA_3_0_IGO,
    RIGHTS_CC_BY_SA_3_0_IGO,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    date_from_page,
    load_catalog,
    official_unesco_host,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

EXPECTED = [
    (
        "Recommendation on the Ethics of Artificial Intelligence",
        "https://www.unesco.org/en/legal-affairs/recommendation-ethics-artificial-intelligence",
        "2021-11-23",
    ),
    (
        "UNESCO member states adopt the first ever global agreement on the Ethics of Artificial Intelligence",
        "https://www.unesco.org/en/articles/unesco-member-states-adopt-first-ever-global-agreement-ethics-artificial-intelligence",
        "2021-11-25",
    ),
    (
        "UNESCO adopts first global standard on the ethics of artificial intelligence",
        "https://www.unesco.org/en/articles/unesco-adopts-first-global-standard-ethics-artificial-intelligence",
        "2022-04-08",
    ),
    (
        "Certified copy of the Recommendation on the Ethics of Artificial Intelligence adopted by acclamation by the 41st session of the General Conference in November 2021",
        "https://www.unesco.org/en/articles/certified-copy-recommendation-ethics-artificial-intelligence-adopted-acclamation-41st-session",
        "2022-06-29",
    ),
    (
        "Recommendation on the Ethics of Artificial Intelligence",
        "https://www.unesco.org/en/articles/recommendation-ethics-artificial-intelligence",
        "2023-05-16",
    ),
    (
        "Ethical Impact Assessment: A Tool of the Recommendation on the Ethics of Artificial Intelligence",
        "https://www.unesco.org/en/articles/ethical-impact-assessment-tool-recommendation-ethics-artificial-intelligence",
        "2023-08-28",
    ),
    (
        "Readiness assessment methodology: a tool of the Recommendation on the Ethics of Artificial Intelligence",
        "https://www.unesco.org/en/articles/readiness-assessment-methodology-tool-recommendation-ethics-artificial-intelligence",
        "2023-08-28",
    ),
    (
        "Recommendation on the Ethics of Artificial Intelligence",
        "https://www.unesco.org/en/artificial-intelligence/recommendation-ethics",
        "2026-06-22",
    ),
    (
        "Ethical Impact Assessment",
        "https://www.unesco.org/ethics-ai/en/eia",
        "2026-09-09",
    ),
    (
        "AI Readiness Assessment Methodology",
        "https://www.unesco.org/ethics-ai/en/ram",
        "2026-09-13",
    ),
    (
        "Global AI Ethics and Governance Observatory",
        "https://www.unesco.org/ethics-ai/en",
        UNKNOWN_DATE,
    ),
]

REJECTED_URLS = [
    "https://example.com/recommendation-ethics",
    "https://en.wikipedia.org/wiki/UNESCO",
    "https://unesco.org.example/recommendation",
    "https://notunesco.org/en/artificial-intelligence",
    "https://unesco.org.evil/recommendation",
    "http://www.unesco.org/en/artificial-intelligence/recommendation-ethics",
    "https://user:pass@www.unesco.org/en/artificial-intelligence/recommendation-ethics",
    "https://www.unesco.org/en/artificial-intelligence/recommendation-ethics?hub=1",
    "https://www.unesco.org/en/artificial-intelligence/recommendation-ethics?utm_source=x",
    "https://www.unesco.org/en/artificial-intelligence/recommendation-ethics#core-values",
    "https://www.unesco.org/ethics-ai/en/",
    "https://www.unesco.org/",
    "https://127.0.0.1/recommendation",
]


def test_catalog_rows_are_confirmed_unesco_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 11
    labels = []
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, url, published = expected
        assert entry["title"] == title
        assert entry["publisher"] == PUBLISHER
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == RIGHTS_UNKNOWN
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        labels.append(entry["rights"])
        host = url.split("/")[2]
        assert official_unesco_host(host)
        assert host == "www.unesco.org"
    assert labels.count(RIGHTS_UNKNOWN) == 11
    assert RIGHTS_CC_BY_NC_SA_3_0_IGO not in labels
    assert RIGHTS_CC_BY_SA_3_0_IGO not in labels
    assert RIGHTS_CC_BY_4_0 not in labels
    assert RIGHTS_CREATIVE_COMMONS not in labels


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    blob = inspect.getsource(__import__("pdoom_pipeline.catalogs.unesco_ai", fromlist=["unesco_ai"]))
    assert "pdoom_pipeline.fetch" not in blob
    assert "pdoom_pipeline.belief" not in blob
    assert "p(doom)" not in blob.casefold()


def test_catalog_file_stores_no_page_body_or_recommendation_articles():
    catalog = load_catalog()
    blob = str(catalog).casefold()
    assert "p(doom)" not in blob
    assert "<p>" not in blob
    assert "<html" not in blob
    assert "preamble" not in blob
    assert "adopts the present recommendation" not in blob
    assert "member states should" not in blob
    for entry in catalog["entries"]:
        for value in entry.values():
            assert len(value) < 400


def test_public_page_without_a_reuse_licence_stays_unknown():
    public = "<h1>Recommendation on the Ethics of Artificial Intelligence</h1><p>This page is public.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    terms = "<footer><a href='/en/terms-use'>Terms of use</a> © UNESCO 2026</footer>"
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    reserved = "<p>© UNESCO. All rights reserved.</p>"
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    open_access = "<p>Open access. This publication is publicly available.</p>"
    assert rights_from_page(open_access) == RIGHTS_UNKNOWN
    incidental = "<p>Member States should consider the appropriate licence for an AI system.</p>"
    assert rights_from_page(incidental) == RIGHTS_UNKNOWN
    hidden = "<script>Licensed under CC BY-SA 3.0 IGO</script><p>No public licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_stated_reuse_licence_is_labeled_and_page_text_is_not_returned():
    nc_sa = (
        "<p>This publication is available in Open Access under the "
        "Attribution-NonCommercial-ShareAlike 3.0 IGO (CC-BY-NC-SA 3.0 IGO) license "
        "(https://creativecommons.org/licenses/by-nc-sa/3.0/igo/).</p>"
        "<article>" + ("recommendation article " * 40) + "</article>"
    )
    assert rights_from_page(nc_sa) == RIGHTS_CC_BY_NC_SA_3_0_IGO
    assert "recommendation article" not in rights_from_page(nc_sa)
    share_alike = "<p>Licence type: CC BY-SA 3.0 IGO</p>"
    assert rights_from_page(share_alike) == RIGHTS_CC_BY_SA_3_0_IGO
    attribution = "<p>This work is licensed under the Creative Commons Attribution 4.0 International licence.</p>"
    assert rights_from_page(attribution) == RIGHTS_CC_BY_4_0
    other = "<p>Licensed under a Creative Commons Attribution-NonCommercial 4.0 licence.</p>"
    assert rights_from_page(other) == RIGHTS_CREATIVE_COMMONS
    linked = '<a href="https://creativecommons.org/licenses/by-nc/4.0/">reuse</a>'
    assert rights_from_page(linked) == RIGHTS_CREATIVE_COMMONS
    structured = (
        '<script type="application/ld+json">'
        '{"@type":"Article","license":"https://creativecommons.org/licenses/by-sa/3.0/igo/"}'
        "</script><p>No visible licence sentence.</p>"
    )
    assert rights_from_page(structured) == RIGHTS_CC_BY_SA_3_0_IGO


def test_missing_dates_stay_unknown_and_publication_dates_win():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>In November 2021, Member States adopted a recommendation.</p>") == UNKNOWN_DATE
    assert date_from_page("<time>25 September 2026</time>") == UNKNOWN_DATE
    assert date_from_page('<div class="updated-time"><span>Last update:</span><span>20 April 2023</span></div>') == UNKNOWN_DATE
    modified_only = (
        '<script type="application/ld+json">'
        '{"@type":"Article","dateModified":"2024-09-26T11:20:03+0200"}'
        "</script>"
    )
    assert date_from_page(modified_only) == UNKNOWN_DATE
    created = (
        '<div class="created-time"><span>25 November 2021</span></div>'
        '<div class="updated-time"><span>Last update:</span><span>20 April 2023</span></div>'
        '<script type="application/ld+json">'
        '{"@graph":[{"@type":"NewsArticle","datePublished":"2021-11-25T17:05:26+0100",'
        '"dateModified":"2023-04-20T16:18:00+0200"}]}'
        "</script>"
    )
    assert date_from_page(created) == "2021-11-25"
    adopted = (
        "<p>Date and place of adoption</p><p>23 November 2021</p>"
        '<script type="application/ld+json">'
        '{"@type":"Article","datePublished":"2026-04-29T09:15:08+0200"}'
        "</script>"
    )
    assert date_from_page(adopted) == "2021-11-23"
    schema = (
        '<script type="application/ld+json">'
        '{"@graph":[{"@type":"Article","headline":"Recommendation on the Ethics of Artificial Intelligence",'
        '"datePublished":"2026-06-22T13:05:42+0200"},'
        '{"@type":"Event","startDate":"2026-10-05"}]}'
        "</script>"
    )
    assert date_from_page(schema) == "2026-06-22"
    issued = '<meta name="dcterms.issued" content="2023-08-28">'
    assert date_from_page(issued) == "2023-08-28"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("23 November 2021")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_non_unesco_urls_are_rejected_and_official_hosts_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [row[1] for row in EXPECTED]
    accepted.append("https://unesdoc.unesco.org/ark:/48223/pf0000381137")
    accepted.append("https://unesco.org/en/artificial-intelligence/recommendation-ethics")
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_unesco_host("www.unesco.org")
    assert official_unesco_host("unesdoc.unesco.org")
    assert not official_unesco_host("unesco.org.example")
    assert not official_unesco_host("evilunesco.org")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    document["entries"][1]["date"] = UNKNOWN_DATE
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][-1]["date"] = UNKNOWN_DATE
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = "public"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = "full page"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["articles"] = "article 1"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)
