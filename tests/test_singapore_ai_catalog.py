"""Offline checks for the Singapore government AI page catalog. No network."""

from __future__ import annotations

import copy
import inspect
import socket

import pytest

from pdoom_pipeline.catalogs.singapore_ai import (
    CATALOG_ID,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_SINGAPORE_OPEN_DATA,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    date_from_page,
    load_catalog,
    official_singapore_host,
    page_record,
    rights_from_page,
    title_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

EXPECTED = [
    (
        "Developing the MVP for AI Governance Testing Framework",
        "Personal Data Protection Commission",
        "https://www.pdpc.gov.sg/media-events/developing-the-mvp-for-ai-governance-testing-framework",
        "2021-07-14",
        RIGHTS_UNKNOWN,
    ),
    (
        "Singapore Launches A.I. Verify",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/sg-launches-worlds-first-ai-testing-framework-and-toolkit-to-promote-transparency",
        "2022-05-25",
        RIGHTS_UNKNOWN,
    ),
    (
        "Launch of AI Verify - An AI Governance Testing Framework and Toolkit",
        "Personal Data Protection Commission",
        "https://www.pdpc.gov.sg/media-events/launch-of-ai-verify-an-ai-governance-testing-framework-and-toolkit",
        "2023-06-06",
        RIGHTS_UNKNOWN,
    ),
    (
        "Launch of AI Verify Foundation to Shape the Future of AI Standards Through Collaboration",
        "Personal Data Protection Commission",
        "https://www.pdpc.gov.sg/media-events/launch-of-ai-verify-foundation-to-shape-the-future-of-ai-standards-through-collaboration",
        "2023-06-06",
        RIGHTS_UNKNOWN,
    ),
    (
        "Singapore Launches AI Verify Foundation 2023",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/singapore-launches-ai-verify-foundation",
        "2023-06-07",
        RIGHTS_UNKNOWN,
    ),
    (
        "Singapore\u2019s Approach to AI Governance",
        "Personal Data Protection Commission",
        "https://www.pdpc.gov.sg/organisations/resources/guidance-by-topic/singapores-approach-to-ai-governance",
        "2023-11-03",
        RIGHTS_UNKNOWN,
    ),
    (
        "Model AI Governance Framework 2024 - Press Release",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/public-consult-model-ai-governance-framework-genai",
        "2024-01-16",
        RIGHTS_UNKNOWN,
    ),
    (
        "Digital Trust Centre designated as Singapore's AISI",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/digital-trust-centre",
        "2024-05-22",
        RIGHTS_UNKNOWN,
    ),
    (
        "Project Moonshot, powered by AI Verify, and AI Collaborations",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/project-moonshot",
        "2024-05-31",
        RIGHTS_UNKNOWN,
    ),
    (
        "Singapore launches Project Moonshot",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/sg-launches-project-moonshot",
        "2024-05-31",
        RIGHTS_UNKNOWN,
    ),
    (
        "New Singapore UK Agreement to Strengthen Global AI Safety and Governance",
        "Ministry of Digital Development and Information",
        "https://www.mddi.gov.sg/newsroom/new-singapore-uk-agreement-to-strengthen-global-ai-safety-governance/",
        "2024-11-06",
        RIGHTS_UNKNOWN,
    ),
    (
        "Singapore and the European Union Agree to Strengthen Collaboration on AI Safety",
        "Ministry of Digital Development and Information",
        "https://www.mddi.gov.sg/newsroom/singapore-european-union-agree-to-strengthen-collaboration-ai-safety/",
        "2024-11-20",
        RIGHTS_UNKNOWN,
    ),
    (
        "Singapore Launches New Model AI Governance Framework for Agentic AI",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/new-model-ai-governance-framework-for-agentic-ai",
        "2026-01-22",
        RIGHTS_UNKNOWN,
    ),
    (
        "Singapore Launches New Model AI Governance Framework for Agentic AI",
        "Ministry of Digital Development and Information",
        "https://www.mddi.gov.sg/newsroom/singapore-launches-new-model-ai-governance-framework-for-agentic-ai--/",
        "2026-01-22",
        RIGHTS_UNKNOWN,
    ),
    (
        "Updated Model AI Governance Framework for Agentic AI",
        "Infocomm Media Development Authority",
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/updated-model-ai-governance-framework-for-agentic-ai",
        "2026-05-20",
        RIGHTS_UNKNOWN,
    ),
    (
        "MDDI's Response to PQ on Extending Model AI Governance Framework and AI Verify to Cover Agentic AI Systems",
        "Ministry of Digital Development and Information",
        "https://www.mddi.gov.sg/newsroom/mddi-s-response-to-pq-on-extending-model-ai-governance-framework-and-ai-verify-to-cover-agentic-ai-systems/",
        "2026-08-05",
        RIGHTS_UNKNOWN,
    ),
]

REJECTED_URLS = [
    "https://example.com/ai-verify",
    "https://en.wikipedia.org/wiki/AI_Verify",
    "https://gov.sg.example/ai-verify",
    "https://notgov.sg/ai-verify",
    "https://imda.gov.sg.example/ai-verify",
    "http://www.imda.gov.sg/ai-verify",
    "https://user:pass@www.imda.gov.sg/ai-verify",
    "https://www.imda.gov.sg/ai-verify?utm_source=x",
    "https://www.imda.gov.sg/ai-verify#section",
    "https://www.imda.gov.sg/framework.pdf",
    "https://www.imda.gov.sg/",
    "https://127.0.0.1/ai-verify",
    "https://aiverifyfoundation.sg/what-is-ai-verify/",
]


def test_catalog_rows_are_confirmed_singapore_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 16
    publishers = set()
    labels = []
    titles = []
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, publisher, url, published, rights = expected
        assert entry["title"] == title
        assert entry["publisher"] == publisher
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == rights
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        publishers.add(publisher)
        labels.append(rights)
        titles.append(title)
        host = url.split("/")[2]
        assert official_singapore_host(host)
        assert host == "gov.sg" or host.endswith(".gov.sg")
    assert publishers == {
        "Infocomm Media Development Authority",
        "Personal Data Protection Commission",
        "Ministry of Digital Development and Information",
    }
    assert any("AI Verify" in title or "A.I. Verify" in title for title in titles)
    assert any("Model AI Governance Framework" in title for title in titles)
    assert any("AISI" in title for title in titles)
    assert labels.count(RIGHTS_UNKNOWN) == 16
    assert RIGHTS_SINGAPORE_OPEN_DATA not in labels
    assert RIGHTS_CREATIVE_COMMONS not in labels


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    blob = inspect.getsource(__import__("pdoom_pipeline.catalogs.singapore_ai", fromlist=["singapore_ai"]))
    assert "pdoom_pipeline.fetch" not in blob
    assert "pdoom_pipeline.belief" not in blob
    assert "p(doom)" not in blob.casefold()


def test_catalog_file_stores_no_page_body():
    catalog = load_catalog()
    blob = str(catalog).casefold()
    assert "p(doom)" not in blob
    assert "<p>" not in blob
    assert "<html" not in blob
    assert "doctype" not in blob
    for entry in catalog["entries"]:
        for value in entry.values():
            assert len(value) < 400


def test_public_page_without_a_reuse_licence_stays_unknown():
    public = "<h1>AI Verify</h1><p>This page is public and publicly available.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    terms = "<footer><a href='/terms-of-use'>Terms of Use</a></footer>"
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    copyright_notice = "<p>© 2026 Personal Data Protection Commission</p><p>© 2026 Government of Singapore</p>"
    assert rights_from_page(copyright_notice) == RIGHTS_UNKNOWN
    reserved = "<p>All rights reserved.</p>"
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    regulatory = "<p>Regulations &amp; Licences. IMDA administers various licences.</p>"
    assert rights_from_page(regulatory) == RIGHTS_UNKNOWN
    products = "<p>Built by Open Government Products.</p>"
    assert rights_from_page(products) == RIGHTS_UNKNOWN
    unnamed = "<p>You may copy this page for personal use.</p>"
    assert rights_from_page(unnamed) == RIGHTS_UNKNOWN
    hidden = "<script>Licensed under the Singapore Open Data Licence.</script><p>No public licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_stated_reuse_licence_is_labeled_and_page_text_is_not_returned():
    dataset = (
        "<p>This dataset is licensed under the Singapore Open Data Licence version 1.0.</p><article>"
        + ("page body " * 40)
        + "</article>"
    )
    assert rights_from_page(dataset) == RIGHTS_SINGAPORE_OPEN_DATA
    assert "page body" not in rights_from_page(dataset)
    labelled = "<p>Licence: Singapore Open Data Licence</p>"
    assert rights_from_page(labelled) == RIGHTS_SINGAPORE_OPEN_DATA
    creative_commons = "<p>This work is licensed under the Creative Commons Attribution 4.0 International licence.</p>"
    assert rights_from_page(creative_commons) == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>See creativecommons.org/licenses/by/4.0/.</p>") == RIGHTS_CREATIVE_COMMONS


def test_creative_commons_label_is_only_cc0_cc_by_and_cc_by_sa():
    copying = [
        "<p>This work is licensed under CC0 1.0.</p>",
        "<p>Dedicated to the public domain under Creative Commons Zero.</p>",
        "<a href='https://creativecommons.org/publicdomain/zero/1.0/'>CC0</a>",
        "<p>Licensed under CC BY 4.0.</p>",
        "<p>Creative Commons Attribution-ShareAlike 4.0 International.</p>",
        "<p>Licensed under CC BY-SA 4.0.</p>",
        "<a href='https://creativecommons.org/licenses/by-sa/4.0/'>CC BY-SA</a>",
    ]
    for page in copying:
        assert rights_from_page(page) == RIGHTS_CREATIVE_COMMONS
    restricted = [
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "<a href='https://creativecommons.org/licenses/by-nc/4.0/'>CC BY-NC</a>",
        "<p>Licensed under CC BY-NC 4.0.</p>",
        "<p>Creative Commons Attribution-NonCommercial 4.0.</p>",
        "https://creativecommons.org/licenses/by-nd/4.0/",
        "<a href='https://creativecommons.org/licenses/by-nd/4.0/'>CC BY-ND</a>",
        "<p>Licensed under CC BY-ND 4.0.</p>",
        "<p>Creative Commons Attribution-NoDerivatives 4.0.</p>",
        "<p>Licensed under CC BY-NC-SA 4.0.</p>",
        "<a href='https://creativecommons.org/licenses/by-nc-sa/4.0/'>CC BY-NC-SA</a>",
        "<p>Licensed under CC BY-NC-ND 4.0.</p>",
        "<a href='https://creativecommons.org/licenses/by-nc-nd/4.0/'>CC BY-NC-ND</a>",
        "<p>Licensed under a Creative Commons licence.</p>",
        "<a href='https://creativecommons.org/publicdomain/mark/1.0/'>Public Domain Mark</a>",
    ]
    for page in restricted:
        assert rights_from_page(page) == RIGHTS_UNKNOWN


def test_missing_dates_stay_unknown_and_published_dates_win():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>© 2026 Government of Singapore, last updated on 5 October 2026</p>") == UNKNOWN_DATE
    assert date_from_page("<p>LAST UPDATED: 10 Oct 2024</p>") == UNKNOWN_DATE
    assert date_from_page("<script>Published on 01 Jan 2020</script><p>No visible date.</p>") == UNKNOWN_DATE
    published = "<p>Published on 14 Jul 2021</p><p>Last updated 14 Jul 2021</p>"
    assert date_from_page(published) == "2021-07-14"
    dateline = "<p>SINGAPORE – 22 MAY 2024</p><p>LAST UPDATED: 10 Oct 2024</p>"
    assert date_from_page(dateline) == "2024-05-22"
    later_reference = (
        "<h1>Agreement</h1><p>6 November 2024</p><p>signed on 27 June 2023</p>"
        "<p>last updated on 5 October 2026</p>"
    )
    assert date_from_page(later_reference) == "2024-11-06"
    agentic = "<p>20 MAY 2026</p><p>LAST UPDATED: 21 May 2026</p>"
    assert date_from_page(agentic) == "2026-05-20"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("22 May 2024")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_page_record_keeps_the_fetched_url_and_drops_the_body():
    html = (
        "<html><head><title>Singapore Launches A.I. Verify | IMDA</title>"
        '<link rel="canonical" href="https://example.com/elsewhere"></head><body>'
        "<p>Infocomm Media Development Authority</p>"
        "<p>SINGAPORE – 25 MAY 2022</p><p>LAST UPDATED: 02 Oct 2026</p>"
        "<a href='/terms-of-use'>Terms of Use</a><article>"
        + ("page body " * 30)
        + "</article></body></html>"
    )
    url = (
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/"
        "sg-launches-worlds-first-ai-testing-framework-and-toolkit-to-promote-transparency"
    )
    record = page_record(html, page_url=url)
    assert record == {
        "title": "Singapore Launches A.I. Verify",
        "publisher": "Infocomm Media Development Authority",
        "canonical_url": url,
        "date": "2022-05-25",
        "rights": RIGHTS_UNKNOWN,
    }
    assert "page body" not in str(record)
    prefixed = '<meta property="og:title" content="PDPC | Singapore’s Approach to AI Governance">'
    assert title_from_page(prefixed) == "Singapore\u2019s Approach to AI Governance"
    pdpc = (
        "<h1>Developing the MVP for AI Governance Testing Framework</h1>"
        "<p>Personal Data Protection Commission</p><p>Published on 14 Jul 2021</p>"
    )
    pdpc_url = "https://www.pdpc.gov.sg/media-events/developing-the-mvp-for-ai-governance-testing-framework"
    assert page_record(pdpc, page_url=pdpc_url)["publisher"] == "Personal Data Protection Commission"
    with pytest.raises(CatalogError, match="publisher"):
        page_record("<h1>AI Verify</h1><p>Published on 14 Jul 2021</p>", page_url=pdpc_url)


def test_non_government_urls_are_rejected_and_official_hosts_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [
        "https://www.imda.gov.sg/resources/press-releases-factsheets-and-speeches/digital-trust-centre",
        "https://www.pdpc.gov.sg/organisations/resources/guidance-by-topic/singapores-approach-to-ai-governance",
        "https://www.mddi.gov.sg/newsroom/singapore-european-union-agree-to-strengthen-collaboration-ai-safety/",
        "https://imda.gov.sg/ai-verify",
        "https://www.gov.sg/ai-verify",
    ]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_singapore_host("www.imda.gov.sg")
    assert official_singapore_host("gov.sg")
    assert not official_singapore_host("gov.sg.example")
    assert not official_singapore_host("notgov.sg")
    assert not official_singapore_host("imda.gov.sg.example")


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
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)
