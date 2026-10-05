"""Offline checks for the Government of Canada AI page catalog. No network."""

from __future__ import annotations

import copy
import inspect
import socket

import pytest

from pdoom_pipeline.catalogs.canada_ai import (
    CATALOG_ID,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_NONCOMMERCIAL,
    RIGHTS_OGL_CANADA,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    date_from_page,
    load_catalog,
    official_canada_host,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

EXPECTED = [
    (
        "Algorithmic Impact Assessment",
        "Treasury Board of Canada Secretariat",
        "https://open.canada.ca/data/en/dataset/5423054a-093c-4239-85be-fa0b36ae0b2e",
        "2019-03-08",
        RIGHTS_OGL_CANADA,
    ),
    (
        "Responsible use of artificial intelligence in government",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai.html",
        "2024-05-30",
        RIGHTS_UNKNOWN,
    ),
    (
        "List of interested Artificial Intelligence (AI) suppliers",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/advancing-ai/list-interested-artificial-intelligence-ai-suppliers.html",
        "2024-05-30",
        RIGHTS_UNKNOWN,
    ),
    (
        "Progress on AI in government",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/advancing-ai/progress.html",
        "2024-05-30",
        RIGHTS_UNKNOWN,
    ),
    (
        "Algorithmic Impact Assessment",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/automated-decision-making/algorithmic-impact-assessment.html",
        "2024-05-30",
        RIGHTS_UNKNOWN,
    ),
    (
        "Guide on the use of generative artificial intelligence",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/generative-ai/guide-use-generative-ai.html",
        "2024-05-30",
        RIGHTS_UNKNOWN,
    ),
    (
        "Directive on Automated Decision-Making",
        "Treasury Board of Canada Secretariat",
        "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592",
        "2024-07-02",
        RIGHTS_UNKNOWN,
    ),
    (
        "Amendments to the Directive on Automated Decision-Making",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/policies-standards/policy-service-digital-announcements/amendments-directive-automated-decision-making.html",
        "2024-10-08",
        RIGHTS_UNKNOWN,
    ),
    (
        "Generative AI in your daily work",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/generative-ai/generative-ai-your-daily-work.html",
        "2024-10-15",
        RIGHTS_UNKNOWN,
    ),
    (
        "Guide to Peer Review of Automated Decision Systems",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/automated-decision-making/guide-peer-review-automated-decision-systems.html",
        "2025-01-07",
        RIGHTS_UNKNOWN,
    ),
    (
        "Consultations on the AI Strategy for the Federal Public Service: What We Heard",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/consultations-ai-strategy-federal-public-service-what-we-heard.html",
        "2025-01-31",
        RIGHTS_UNKNOWN,
    ),
    (
        "AI Strategy for the Federal Public Service 2025-2027: Overview",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/gc-ai-strategy-overview.html",
        "2025-03-04",
        RIGHTS_UNKNOWN,
    ),
    (
        "Guide on the Scope of the Directive on Automated Decision-Making",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/automated-decision-making/guide-scope-directive-automated-decision-making.html",
        "2025-06-12",
        RIGHTS_UNKNOWN,
    ),
    (
        "Artificial Intelligence and Data Act",
        "Innovation, Science and Economic Development Canada",
        "https://ised-isde.canada.ca/site/innovation-better-canada/en/artificial-intelligence-and-data-act",
        "2025-12-09",
        RIGHTS_UNKNOWN,
    ),
    (
        "G7 AI Challenge",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/advancing-ai/g7-ai-challenge.html",
        "2026-03-31",
        RIGHTS_UNKNOWN,
    ),
    (
        "Guide on the Use of Agentic Artificial Intelligence",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/generative-ai/guide-use-agentic-artificial-antelligence.html",
        "2026-05-22",
        RIGHTS_UNKNOWN,
    ),
    (
        "Advisory Council on Artificial Intelligence",
        "Innovation, Science and Economic Development Canada",
        "https://ised-isde.canada.ca/site/ised/en/advisory-council-artificial-intelligence",
        "2026-06-04",
        RIGHTS_UNKNOWN,
    ),
    (
        "Voluntary Code of Conduct on the Responsible Development and Management of Advanced Generative AI Systems",
        "Innovation, Science and Economic Development Canada",
        "https://ised-isde.canada.ca/site/ised/en/voluntary-code-conduct-responsible-development-and-management-advanced-generative-ai-systems",
        "2026-06-04",
        RIGHTS_UNKNOWN,
    ),
    (
        "Canadian Artificial Intelligence Safety Institute",
        "Innovation, Science and Economic Development Canada",
        "https://ised-isde.canada.ca/site/ised/en/canadian-artificial-intelligence-safety-institute",
        "2026-07-08",
        RIGHTS_UNKNOWN,
    ),
    (
        "Pan-Canadian Artificial Intelligence Strategy",
        "Innovation, Science and Economic Development Canada",
        "https://ised-isde.canada.ca/site/ised/en/pan-canadian-artificial-intelligence-strategy",
        "2026-07-30",
        RIGHTS_UNKNOWN,
    ),
    (
        "Advancing AI",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/advancing-ai.html",
        "2026-09-15",
        RIGHTS_UNKNOWN,
    ),
    (
        "AI ethics and responsibilities",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/ai-ethics-responsibilities.html",
        "2026-09-15",
        RIGHTS_UNKNOWN,
    ),
    (
        "Automated decision-making",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/automated-decision-making.html",
        "2026-09-15",
        RIGHTS_UNKNOWN,
    ),
    (
        "Generative AI",
        "Treasury Board of Canada Secretariat",
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/generative-ai.html",
        "2026-09-15",
        RIGHTS_UNKNOWN,
    ),
    (
        "Artificial intelligence ecosystem",
        "Innovation, Science and Economic Development Canada",
        "https://ised-isde.canada.ca/site/ised/en/artificial-intelligence-ecosystem",
        "2026-09-23",
        RIGHTS_UNKNOWN,
    ),
]

REJECTED_URLS = [
    "https://example.com/artificial-intelligence",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://canada.ca.example/ai",
    "https://notcanada.ca/ai",
    "https://ise.gc.ca.example/ai",
    "http://www.canada.ca/en/ai",
    "https://user:pass@www.canada.ca/en/ai",
    "https://www.canada.ca/en/ai?utm_source=x",
    "https://www.canada.ca/en/ai#section",
    "https://www.tbs-sct.canada.ca/pol/(S(abc))/doc-eng.aspx?id=32592",
    "https://www.canada.ca/pol/doc-eng.aspx?id=32592",
    "https://127.0.0.1/ai",
]


def test_catalog_rows_are_confirmed_canada_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 25
    publishers = set()
    labels = []
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
        host = url.split("/")[2]
        assert official_canada_host(host)
        assert host == "canada.ca" or host.endswith(".canada.ca")
    assert publishers == {
        "Treasury Board of Canada Secretariat",
        "Innovation, Science and Economic Development Canada",
    }
    assert labels.count(RIGHTS_UNKNOWN) == 24
    assert labels.count(RIGHTS_OGL_CANADA) == 1
    assert RIGHTS_NONCOMMERCIAL not in labels
    assert RIGHTS_CREATIVE_COMMONS not in labels


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    blob = inspect.getsource(__import__("pdoom_pipeline.catalogs.canada_ai", fromlist=["canada_ai"]))
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
    public = "<h1>Artificial intelligence</h1><p>This page is public and publicly available.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    terms = "<footer><a href='/terms'>Terms and conditions</a></footer>"
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    copyright_notice = "<p>© His Majesty the King in Right of Canada, represented by the President of the Treasury Board, 2021.</p>"
    assert rights_from_page(copyright_notice) == RIGHTS_UNKNOWN
    software = "<p>6.2.4 Determining the appropriate licence for software components, including consideration of open source software.</p>"
    assert rights_from_page(software) == RIGHTS_UNKNOWN
    unnamed = "<p>It is available to the public for sharing and re-use under an open license.</p>"
    assert rights_from_page(unnamed) == RIGHTS_UNKNOWN
    portal = "<p>Published on the Open Government Portal.</p>"
    assert rights_from_page(portal) == RIGHTS_UNKNOWN
    hidden = "<script>Licence: Open Government Licence - Canada</script><p>No public licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_stated_reuse_licence_is_labeled_and_page_text_is_not_returned():
    dataset = "<p>Licence: Open Government Licence - Canada</p><article>" + ("page body " * 40) + "</article>"
    assert rights_from_page(dataset) == RIGHTS_OGL_CANADA
    assert "page body" not in rights_from_page(dataset)
    dash = "<p>Licence: Open Government Licence – Canada</p>"
    assert rights_from_page(dash) == RIGHTS_OGL_CANADA
    grant = (
        "<h1>Open Government Licence - Canada</h1>"
        "<p>You are free to: Copy, modify, publish, translate, adapt, distribute or otherwise use the Information.</p>"
    )
    assert rights_from_page(grant) == RIGHTS_OGL_CANADA
    creative_commons = "<p>This work is licensed under the Creative Commons Attribution 4.0 International licence.</p>"
    assert rights_from_page(creative_commons) == RIGHTS_CREATIVE_COMMONS
    reproduction = (
        "<p>Information on this site may be reproduced, in part or in whole and by any means, "
        "without charge or further permission from the Government of Canada.</p>"
    )
    assert rights_from_page(reproduction) == RIGHTS_NONCOMMERCIAL
    assert rights_from_page("<p>Excerpts may be reproduced with attribution.</p>") == RIGHTS_UNKNOWN


def test_missing_dates_stay_unknown_and_issued_dates_win():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<time>2017-08-24</time>") == UNKNOWN_DATE
    assert date_from_page('<meta name="dcterms.created" content="2017-03-30">') == UNKNOWN_DATE
    assert date_from_page("<p>Record Modified: 2024-11-21</p>") == UNKNOWN_DATE
    issued = (
        '<meta name="dcterms.issued" content="2024-07-02">'
        '<meta name="dcterms.modified" content="2025-06-24">'
        "<time>2017-08-24</time>"
    )
    assert date_from_page(issued) == "2024-07-02"
    empty_issued = (
        '<meta name="dcterms.issued" content="">'
        '<meta name="dcterms.modified" content="2026-07-30">'
    )
    assert date_from_page(empty_issued) == "2026-07-30"
    published = "<p>Date Published: 2019-03-08</p><p>Record Modified: 2024-11-21</p>"
    assert date_from_page(published) == "2019-03-08"
    modified = "<dl><dt>Date modified:</dt><dd>2026-07-08</dd></dl>"
    assert date_from_page(modified) == "2026-07-08"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("2 November 2023")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_non_government_urls_are_rejected_and_official_hosts_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [
        "https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai.html",
        "https://ised-isde.canada.ca/site/ised/en/canadian-artificial-intelligence-safety-institute",
        "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592",
        "https://ise.gc.ca/en/artificial-intelligence",
        "https://www.ise.gc.ca/en/artificial-intelligence",
    ]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_canada_host("canada.ca")
    assert not official_canada_host("canada.ca.example")
    assert not official_canada_host("evilcanada.ca")


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
