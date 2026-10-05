"""Offline checks for the Australian Government AI page catalog. No network."""

from __future__ import annotations

import copy
import inspect
import socket

import pytest

from pdoom_pipeline.catalogs.australia_ai import (
    CATALOG_ID,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    date_from_page,
    load_catalog,
    official_australia_host,
    publisher_from_page,
    rights_from_page,
    title_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

EXPECTED = [
    (
        'Australia’s AI Ethics Principles',
        'Department of Industry, Science and Resources',
        'https://www.industry.gov.au/publications/australias-ai-ethics-principles',
        '2019-11-07',
        'unknown',
    ),
    (
        'The Australian Government’s interim response to safe and responsible AI consultation',
        'Department of Industry Science and Resources',
        'https://www.industry.gov.au/news/australian-governments-interim-response-safe-and-responsible-ai-consultation',
        '2024-01-17',
        'unknown',
    ),
    (
        'Mandatory guardrails for safe and responsible AI: have your say',
        'Department of Industry Science and Resources',
        'https://www.industry.gov.au/news/mandatory-guardrails-safe-and-responsible-ai-have-your-say',
        '2024-09-05',
        'unknown',
    ),
    (
        'Voluntary AI Safety Standard',
        'National Artificial Intelligence Centre',
        'https://www.industry.gov.au/publications/voluntary-ai-safety-standard',
        '2024-09-05',
        'unknown',
    ),
    (
        'Guidance on privacy and developing and training generative AI models',
        'Office of the Australian Information Commissioner',
        'https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models',
        '2024-10-21',
        'unknown',
    ),
    (
        'Guidance on privacy and the use of commercially available AI products',
        'Office of the Australian Information Commissioner',
        'https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products',
        '2024-10-21',
        'unknown',
    ),
    (
        'National AI Plan',
        'Department of Industry, Science and Resources',
        'https://www.industry.gov.au/publications/national-ai-plan',
        '2025-12-02',
        'unknown',
    ),
    (
        'AI screening questions',
        'National AI Centre',
        'https://www.ai.gov.au/practical-guides-and-learning/planning-tools-and-templates/ai-screening-questions',
        '2026-04-22',
        'unknown',
    ),
    (
        'Be clear about AI-generated content',
        'National AI Centre',
        'https://www.ai.gov.au/staying-safe-and-responsible/essential-ai-practices/be-clear-about-ai-use',
        '2026-04-22',
        'unknown',
    ),
    (
        'Create an AI policy',
        'National AI Centre',
        'https://www.ai.gov.au/staying-safe-and-responsible/essential-ai-practices/create-ai-policy',
        '2026-04-22',
        'unknown',
    ),
    (
        'Guidance for AI adoption: foundations',
        'National AI Centre',
        'https://www.ai.gov.au/staying-safe-and-responsible/essential-ai-practices/guidance-ai-adoption-foundations',
        '2026-05-05',
        'unknown',
    ),
    (
        'Guidance for AI adoption: implementation guidance',
        'National AI Centre',
        'https://www.ai.gov.au/staying-safe-and-responsible/essential-ai-practices/guidance-ai-adoption-implementation-guidance',
        '2026-05-05',
        'unknown',
    ),
    (
        'About the National AI Centre',
        'National AI Centre',
        'https://www.ai.gov.au/about/about-national-ai-centre',
        'unknown',
        'unknown',
    ),
    (
        'Essential AI practices',
        'National AI Centre',
        'https://www.ai.gov.au/staying-safe-and-responsible/essential-ai-practices',
        'unknown',
        'unknown',
    ),
    (
        'Generative AI – position statement',
        'eSafety Commissioner',
        'https://www.esafety.gov.au/industry/tech-trends-and-challenges/generative-ai',
        'unknown',
        'unknown',
    ),
    (
        'National framework for the assurance of artificial intelligence in government',
        'Department of Finance',
        'https://www.finance.gov.au/government/public-data/data-and-digital-ministers-meeting/national-framework-assurance-artificial-intelligence-government',
        'unknown',
        'unknown',
    ),
    (
        'The National AI Plan on a page',
        'Department of Industry, Science and Resources',
        'https://www.industry.gov.au/publications/national-ai-plan/national-ai-plan-page',
        'unknown',
        'unknown',
    ),
    (
        'The 10 guardrails',
        'Department of Industry, Science and Resources',
        'https://www.industry.gov.au/publications/voluntary-ai-safety-standard/10-guardrails',
        'unknown',
        'unknown',
    ),
    (
        'Introduction to the standard',
        'Department of Industry, Science and Resources',
        'https://www.industry.gov.au/publications/voluntary-ai-safety-standard/introduction-standard',
        'unknown',
        'unknown',
    ),
    (
        'Why we wrote the standard',
        'Department of Industry, Science and Resources',
        'https://www.industry.gov.au/publications/voluntary-ai-safety-standard/why-we-wrote-standard',
        'unknown',
        'unknown',
    ),
]


REJECTED_URLS = [
    "https://example.com/artificial-intelligence",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://www.industry.gov.au.example/ai",
    "https://notgov.au/ai",
    "https://gov.au.example/ai",
    "http://www.industry.gov.au/publications/australias-ai-ethics-principles",
    "https://user:pass@www.industry.gov.au/publications/australias-ai-ethics-principles",
    "https://www.industry.gov.au/publications/australias-ai-ethics-principles?utm_source=x",
    "https://www.industry.gov.au/publications/australias-ai-ethics-principles#section",
    "https://www.industry.gov.au/publications/national-ai-plan.pdf",
    "https://www.industry.gov.au/",
    "https://127.0.0.1/ai",
    "https://www.industry.gov.au/pol/(S(abc))/doc",
]


def test_catalog_rows_are_confirmed_australia_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 20
    publishers = set()
    labels = []
    for entry, expected_row in zip(entries, EXPECTED, strict=True):
        title, publisher, url, published, rights = expected_row
        assert entry["title"] == title
        assert entry["publisher"] == publisher
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == rights
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        publishers.add(publisher)
        labels.append(rights)
        host = url.split("/")[2]
        assert official_australia_host(host)
    assert publishers == {
        "Department of Industry, Science and Resources",
        "Department of Industry Science and Resources",
        "National Artificial Intelligence Centre",
        "National AI Centre",
        "Department of Finance",
        "Office of the Australian Information Commissioner",
        "eSafety Commissioner",
    }
    assert labels.count(RIGHTS_UNKNOWN) == 20
    assert labels.count(RIGHTS_CREATIVE_COMMONS) == 0
    assert RIGHTS_UNKNOWN == "unknown"
    assert RIGHTS_CREATIVE_COMMONS == "creative_commons"


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    blob = inspect.getsource(__import__("pdoom_pipeline.catalogs.australia_ai", fromlist=["australia_ai"]))
    assert "pdoom_pipeline.fetch" not in blob
    assert "pdoom_pipeline.belief" not in blob
    assert "curl_cffi" not in blob
    assert "requests" not in blob
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
    copyright_notice = "<p>© Commonwealth of Australia</p><a href='/copyright'>Copyright</a>"
    assert rights_from_page(copyright_notice) == RIGHTS_UNKNOWN
    reserved = "<p>© Department of Finance. All rights reserved.</p>"
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    mention = "<p>This page discusses the Creative Commons movement.</p>"
    assert rights_from_page(mention) == RIGHTS_UNKNOWN
    hidden = "<script>licensed under the CC BY 4.0 license</script><p>No public licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN
    comment = "<!-- licensed under the CC BY 4.0 license --><p>No public licence.</p>"
    assert rights_from_page(comment) == RIGHTS_UNKNOWN


def test_stated_creative_commons_licence_is_labeled_and_page_text_is_not_returned():
    footer = (
        "<p>Except for the Commonwealth Coat of Arms and where otherwise noted, "
        "this work is licensed under the CC BY 4.0 license.</p><article>"
        + ("page body " * 40)
        + "</article>"
    )
    assert rights_from_page(footer) == RIGHTS_CREATIVE_COMMONS
    assert "page body" not in rights_from_page(footer)
    attribution = "<p>This work is licensed under the Creative Commons Attribution 4.0 International licence.</p>"
    assert rights_from_page(attribution) == RIGHTS_CREATIVE_COMMONS
    link = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
    assert rights_from_page(link) == RIGHTS_CREATIVE_COMMONS
    share_alike = "<p>licensed under the CC BY-SA 4.0 license.</p>"
    assert rights_from_page(share_alike) == RIGHTS_CREATIVE_COMMONS
    share_alike_name = "<p>Creative Commons Attribution-ShareAlike 4.0 International.</p>"
    assert rights_from_page(share_alike_name) == RIGHTS_CREATIVE_COMMONS
    share_alike_url = '<a href="https://creativecommons.org/licenses/by-sa/4.0/">Licence</a>'
    assert rights_from_page(share_alike_url) == RIGHTS_CREATIVE_COMMONS
    cc0 = "<p>This work is licensed under CC0.</p>"
    assert rights_from_page(cc0) == RIGHTS_CREATIVE_COMMONS
    cc0_url = '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
    assert rights_from_page(cc0_url) == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>Excerpts may be reproduced with attribution.</p>") == RIGHTS_UNKNOWN


def test_restricted_creative_commons_deeds_stay_unknown():
    phrases = [
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "https://creativecommons.org/licenses/by-nd/4.0/",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "Creative Commons Attribution-NonCommercial",
        "Creative Commons Attribution-NoDerivatives",
        "licensed under the CC BY-NC 4.0",
        "licensed under the CC BY-ND 4.0",
        "licensed under the CC BY-NC-SA 4.0",
        "licensed under the CC BY-NC-ND 4.0",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        "Public Domain Mark 1.0",
        "© Crown copyright",
        "Crown copyright 2024. All rights reserved.",
    ]
    for phrase in phrases:
        assert rights_from_page(f"<p>{phrase}</p>") == RIGHTS_UNKNOWN
    for deed in ("by-nc/4.0", "by-nd/4.0", "by-nc-sa/4.0", "by-nc-nd/4.0"):
        page = f'<a href="https://creativecommons.org/licenses/{deed}/">Licence</a>'
        assert rights_from_page(page) == RIGHTS_UNKNOWN
    mixed = (
        "<p>Except where otherwise noted, this work is licensed under the CC BY 4.0 license. "
        "Third-party material is Creative Commons Attribution-NonCommercial.</p>"
    )
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN


def test_missing_dates_stay_unknown_and_published_dates_win():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>The framework was released on 21 June 2024.</p>") == UNKNOWN_DATE
    updated = '<strong>Updated: </strong><time datetime="2026-02-24T14:28:34+11:00">24 February 2026</time>'
    assert date_from_page(updated) == UNKNOWN_DATE
    last_updated = "<p class='c-audit-box__lu'><span>Last updated:</span> 21/09/2026</p>"
    assert date_from_page(last_updated) == UNKNOWN_DATE
    file_updated = "<div>LAST UPDATED: 1 Dec 2025</div>"
    assert date_from_page(file_updated) == UNKNOWN_DATE
    cms_clock = '<meta name="dcterms.date" content="2026-07-01T14:32:01+1000">'
    assert date_from_page(cms_clock) == UNKNOWN_DATE
    hidden_created = '<meta name="dcterms.created" content="2024-09-05T09:30:00+1000"><p>No visible day.</p>'
    assert date_from_page(hidden_created) == UNKNOWN_DATE
    published = (
        '<meta name="dcterms.created" content="2020-01-01T00:00:00+1100">'
        '<meta name="dcterms.modified" content="2025-12-02T23:00:00+1100">'
        '<meta name="dcterms.date" content="2026-07-01T14:32:01+1000">'
        "<div>Date published: 7 November 2019</div><div>Date updated: 2 December 2025</div>"
    )
    assert date_from_page(published) == "2019-11-07"
    colon = "<span>Published: </span><time datetime='21 October 2024'>21 October 2024</time><span>Updated: 17 January 2025</span>"
    assert date_from_page(colon) == "2024-10-21"
    time_published = '<time datetime="2026-05-05T11:30:53+10:00">Published 05 May 2026</time>'
    assert date_from_page(time_published) == "2026-05-05"
    created = (
        '<meta name="dcterms.created" content="2024-09-05T09:30:00+1000">'
        "<p>5 September 2024</p>"
    )
    assert date_from_page(created) == "2024-09-05"
    issued = '<meta name="dcterms.issued" content="2024-10-21T08:00:33+11:00">'
    assert date_from_page(issued) == "2024-10-21"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("2 November 2023")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_title_and_publisher_come_from_the_page():
    page = """
    <title>Policy for the responsible use of AI in government - Version 2.0 | digital.gov.au</title>
    <h1>Policy for the responsible use of AI in government</h1>
    <a title="An initiative of the Digital Transformation Agency" href="/">Home</a>
    """
    assert title_from_page(page) == "Policy for the responsible use of AI in government - Version 2.0"
    assert publisher_from_page(page) == "Digital Transformation Agency"
    industry = """
    <title>Voluntary AI Safety Standard | Department of Industry Science and Resources</title>
    <h1>Voluntary AI Safety Standard</h1>
    <meta name="dcterms.creator" content="Department of Industry Science and Resources">
    <h3 class="row-label">Publisher</h3>
    <a href="/publications?publisher=1">National Artificial Intelligence Centre</a>
    """
    assert title_from_page(industry) == "Voluntary AI Safety Standard"
    assert publisher_from_page(industry) == "National Artificial Intelligence Centre"
    oaic = """
    <title>Guidance | OAIC</title>
    <h1>Guidance</h1>
    <meta name="dcterms.creator" content="OAIC">
    <img alt="Office of the Australian Information Commissioner (OAIC)">
    """
    assert publisher_from_page(oaic) == "Office of the Australian Information Commissioner"


def test_non_government_urls_are_rejected_and_official_hosts_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [
        "https://www.industry.gov.au/publications/australias-ai-ethics-principles",
        "https://www.ai.gov.au/staying-safe-and-responsible/essential-ai-practices",
        "https://www.digital.gov.au/ai/ai-in-government-policy",
        "https://www.finance.gov.au/government/public-data/data-and-digital-ministers-meeting/national-framework-assurance-artificial-intelligence-government",
        "https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products",
        "https://www.esafety.gov.au/industry/tech-trends-and-challenges/generative-ai",
        "https://www.dta.gov.au/articles/ai-policy-update-strengthening-responsible-use-across-government",
    ]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_australia_host("gov.au")
    assert official_australia_host("www.industry.gov.au")
    assert not official_australia_host("industry.gov.au.example")
    assert not official_australia_host("notgov.au")
    assert not official_australia_host("evilgov.au")


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
