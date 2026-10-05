"""Offline checks for the New Zealand government AI page catalog. No network."""

from __future__ import annotations

import copy
import inspect
import socket

import pytest

from pdoom_pipeline.catalogs.nz_ai import (
    CATALOG_ID,
    RIGHTS_CC_BY,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    date_from_page,
    load_catalog,
    official_nz_government_host,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

GDDA = "Government Digital Delivery Agency"
MOE = "Ministry of Education"
DOC = "https://standards.digital.govt.nz/docref/public-service-gen-ai-guidance-"

EXPECTED = [
    (
        "2024 Cross-agency AI Survey: Highlights",
        GDDA,
        DOC + "2024-cross-agency-ai-survey-highlights/2024/en/",
        "2024-09-19",
        RIGHTS_CC_BY,
    ),
    (
        "Public Service AI Framework",
        GDDA,
        DOC + "ai-framework/2025/en/",
        "2025-01-29",
        RIGHTS_CC_BY,
    ),
    (
        "Accessibility and GenAI",
        GDDA,
        DOC + "accessibility/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Accountability, Responsibility and GenAI",
        GDDA,
        DOC + "accountability-and-responsibility/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Bias, Discrimination, Fairness, Equity and GenAI",
        GDDA,
        DOC + "bias-discrimination-fairness-and-equity/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Glossary of AI Terms",
        GDDA,
        DOC + "glossary/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Governance and GenAI in the Public Service",
        GDDA,
        DOC + "governance/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Māori, Pacific Peoples, Ethnic Communities and GenAI",
        GDDA,
        DOC + "maori-pacific-peoples-and-ethnic-communities/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Misinformation, Hallucinations and GenAI",
        GDDA,
        DOC + "misinformation-and-hallucinations/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Next Steps for Safe, Responsible AI in Government",
        GDDA,
        DOC + "next-steps-for-safe-responsible-ai/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Overview",
        GDDA,
        DOC + "overview/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Privacy and GenAI",
        GDDA,
        DOC + "privacy/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Procurement and GenAI",
        GDDA,
        DOC + "procurement/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Security and GenAI",
        GDDA,
        DOC + "security/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Skills, Capabilities and GenAI",
        GDDA,
        DOC + "skills-and-capabilities/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Transparency and GenAI",
        GDDA,
        DOC + "transparency/2025/en/",
        "2025-02-03",
        RIGHTS_CC_BY,
    ),
    (
        "Government Chief Digital Officer’s Role in Artificial Intelligence (AI)",
        GDDA,
        DOC + "government-chief-digital-officers-role/2025/en/",
        "2025-02-05",
        RIGHTS_CC_BY,
    ),
    (
        "Generative AI",
        MOE,
        "https://www.education.govt.nz/education-professionals/schools-year-0-13/digital-technology/generative-ai",
        "2026-05-22",
        RIGHTS_UNKNOWN,
    ),
    (
        "Public Service Generative AI Guidance",
        GDDA,
        "https://standards.digital.govt.nz/collections/generative-ai-guidance-gcdo/",
        UNKNOWN_DATE,
        RIGHTS_UNKNOWN,
    ),
    (
        "Artificial Intelligence (AI)",
        GDDA,
        DOC + "artificial-intelligence/2025/en/",
        UNKNOWN_DATE,
        RIGHTS_CC_BY,
    ),
    (
        "GenAI and Customer Experience with Government",
        GDDA,
        DOC + "customer-experience/2025/en/",
        UNKNOWN_DATE,
        RIGHTS_CC_BY,
    ),
    (
        "Responsible AI Guidance for the Public Service: GENAI",
        GDDA,
        DOC + "responsible-ai/2025/en/",
        UNKNOWN_DATE,
        RIGHTS_CC_BY,
    ),
]

REJECTED_URLS = [
    "https://example.com/artificial-intelligence",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://govt.nz.example/ai",
    "https://notgovt.nz/ai",
    "https://education.govt.nz.example/ai",
    "http://www.education.govt.nz/generative-ai",
    "https://user:pass@www.education.govt.nz/generative-ai",
    "https://www.education.govt.nz/generative-ai?utm_source=x",
    "https://www.education.govt.nz/generative-ai#section",
    "https://www.govt.nz/",
    "https://127.0.0.1/ai",
    "https://standards.digital.govt.nz/(S(abc))/docref/ai",
]


def test_catalog_rows_are_confirmed_nz_government_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 22
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
        assert official_nz_government_host(host)
        assert host == "govt.nz" or host.endswith(".govt.nz")
    assert publishers == {GDDA, MOE}
    assert labels.count(RIGHTS_UNKNOWN) == 2
    assert labels.count(RIGHTS_CC_BY) == 20
    assert [entry["date"] for entry in entries].count(UNKNOWN_DATE) == 4


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    blob = inspect.getsource(__import__("pdoom_pipeline.catalogs.nz_ai", fromlist=["nz_ai"]))
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
    terms = "<footer><a href='/copyright'>Copyright</a> © 2026 Ministry of Education</footer>"
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    crown = "<p>© Copyright Te Kāwanatanga o Aotearoa</p>"
    assert rights_from_page(crown) == RIGHTS_UNKNOWN
    social = "<p>Social licence — to ensure New Zealanders have trust in public service AI use.</p>"
    assert rights_from_page(social) == RIGHTS_UNKNOWN
    nzgoal = "<p>The NZGOAL framework recommends open licensing of government copyright works.</p>"
    assert rights_from_page(nzgoal) == RIGHTS_UNKNOWN
    vague = "<p>This material is licensed under a Creative Commons licence.</p>"
    assert rights_from_page(vague) == RIGHTS_UNKNOWN
    noncommercial = "<p>Creative Commons Attribution-NonCommercial 4.0 International</p>"
    assert rights_from_page(noncommercial) == RIGHTS_UNKNOWN
    hidden = "<script>Document © Creative Commons Attribution 4.0 International</script><p>No public licence.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN
    commented = "<!-- Creative Commons Attribution 4.0 International --><p>No public licence.</p>"
    assert rights_from_page(commented) == RIGHTS_UNKNOWN


def test_stated_creative_commons_attribution_is_labeled_and_page_text_is_not_returned():
    notice = "<p>Document © Creative Commons Attribution 4.0 International</p><article>" + ("page body " * 40) + "</article>"
    assert rights_from_page(notice) == RIGHTS_CC_BY
    assert "page body" not in rights_from_page(notice)
    spelled = "<p>Licensed under the Creative Commons Attribution 4.0 International licence.</p>"
    assert rights_from_page(spelled) == RIGHTS_CC_BY
    deed = "<p>https://creativecommons.org/licenses/by/4.0/</p>"
    assert rights_from_page(deed) == RIGHTS_CC_BY
    restricted = "<p>https://creativecommons.org/licenses/by-nc/4.0/</p>"
    assert rights_from_page(restricted) == RIGHTS_UNKNOWN


def test_missing_dates_stay_unknown_and_issued_dates_win():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>Version: 2025</p>") == UNKNOWN_DATE
    assert date_from_page("<p>In June 2024, Cabinet set a direction.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>© 2026 Ministry of Education</p>") == UNKNOWN_DATE
    assert date_from_page("<time>2024-09-19</time>") == UNKNOWN_DATE
    assert date_from_page("<p>May 22, 2026</p>") == UNKNOWN_DATE
    assert date_from_page("<p>Updated 22 May 2026</p>") == UNKNOWN_DATE
    assert date_from_page("<p>Last updated 19 September 2024</p>") == "2024-09-19"
    assert date_from_page("<p>Last updated 29 January 2025</p>") == "2025-01-29"
    assert date_from_page("<p>Last updated 03 February 2025</p>") == "2025-02-03"
    assert date_from_page("<p>Last updated 05 February 2025</p>") == "2025-02-05"
    assert date_from_page("<p>Last updated : 22 May 2026</p>") == "2026-05-22"
    issued = (
        '<meta name="dcterms.issued" content="2025-01-29">'
        "<p>Last updated 03 February 2025</p>"
    )
    assert date_from_page(issued) == "2025-01-29"
    empty_issued = (
        '<meta name="dcterms.issued" content="">'
        '<meta name="dcterms.modified" content="2026-05-22">'
    )
    assert date_from_page(empty_issued) == "2026-05-22"
    published = "<p>Date published: 2024-09-19</p><p>Last updated 03 February 2025</p>"
    assert date_from_page(published) == "2024-09-19"
    hidden = "<script>Last updated 03 February 2025</script><p>No visible date.</p>"
    assert date_from_page(hidden) == UNKNOWN_DATE
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("22 May 2026")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_non_government_urls_are_rejected_and_official_hosts_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [
        "https://www.education.govt.nz/education-professionals/schools-year-0-13/digital-technology/generative-ai",
        "https://standards.digital.govt.nz/docref/public-service-gen-ai-guidance-ai-framework/2025/en/",
        "https://www.digital.govt.nz/standards-and-guidance/technology-and-architecture/artificial-intelligence",
        "https://www.mbie.govt.nz/business-and-employment/economic-growth/digital-policy/new-zealands-ai-strategy-investing-with-confidence",
        "https://govt.nz/en/artificial-intelligence",
    ]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_nz_government_host("govt.nz")
    assert official_nz_government_host("www.education.govt.nz")
    assert not official_nz_government_host("govt.nz.example")
    assert not official_nz_government_host("notgovt.nz")
    assert not official_nz_government_host("education.govt.nz.example")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = UNKNOWN_DATE
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
