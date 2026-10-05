"""Offline checks for the White House OSTP AI page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import socket
from pathlib import Path

import pytest

from pdoom_pipeline.catalogs.ostp_ai import (
    CATALOG_ID,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_UNKNOWN,
    RIGHTS_US_GOVERNMENT_WORK,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    is_official_host,
    load_catalog,
    page_record,
    publication_date_from_page,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
    validate_entry,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "catalogs" / "ostp_ai_pages.json"
HTML_FIXTURE = ROOT / "data" / "fixtures" / "ostp" / "ai_policy_page.html"

# Titles, publishers, canonical URLs, dates, and rights confirmed from one bounded GET each.
# Curly apostrophes are the characters the pages used. Modified times are not these dates.
EXPECTED = [
    (
        "Removing Barriers to American Leadership in Artificial Intelligence",
        "The White House",
        "https://www.whitehouse.gov/presidential-actions/2025/01/removing-barriers-to-american-leadership-in-artificial-intelligence/",
        "2025-01-23",
        "unknown",
    ),
    (
        "White House Releases New Policies on Federal Agency AI Use and Procurement",
        "The White House",
        "https://www.whitehouse.gov/releases/2025/04/white-house-releases-new-policies-on-federal-agency-ai-use-and-procurement/",
        "2025-04-07",
        "unknown",
    ),
    (
        "American Public Submits Over 10,000 Comments on White House\u2019s AI Action Plan",
        "The White House",
        "https://www.whitehouse.gov/releases/2025/04/american-public-submits-over-10000-comments-on-white-houses-ai-action-plan/",
        "2025-04-24",
        "unknown",
    ),
    (
        "Pledge to America\u2019s Youth",
        "The White House",
        "https://www.whitehouse.gov/edai/",
        "2025-06-30",
        "unknown",
    ),
    (
        "60+ Organizations Sign White House Pledge to Support America\u2019s Youth and Invest in AI Education",
        "The White House",
        "https://www.whitehouse.gov/releases/2025/06/60-organizations-sign-white-house-pledge-to-support-americas-youth-and-invest-in-ai-education/",
        "2025-06-30",
        "unknown",
    ),
    (
        "White House Unveils America's AI Action Plan",
        "The White House",
        "https://www.whitehouse.gov/releases/2025/07/white-house-unveils-americas-ai-action-plan/",
        "2025-07-23",
        "unknown",
    ),
    (
        "Remarks by Director Kratsios at the APEC Digital and AI Ministerial Meeting",
        "The White House",
        "https://www.whitehouse.gov/releases/2025/08/remarks-by-director-kratsios-at-the-apec-digital-and-ai-ministerial-meeting/",
        "2025-08-05",
        "unknown",
    ),
    (
        "President Trump Launches the Genesis Mission to Accelerate AI for Scientific Discovery",
        "The White House",
        "https://www.whitehouse.gov/releases/2025/11/president-trump-launches-the-genesis-mission-to-accelerate-ai-for-scientific-discovery/",
        "2025-11-24",
        "unknown",
    ),
    (
        "Ensuring a National Policy Framework for Artificial Intelligence",
        "The White House",
        "https://www.whitehouse.gov/presidential-actions/2025/12/eliminating-state-law-obstruction-of-national-artificial-intelligence-policy/",
        "2025-12-11",
        "unknown",
    ),
    (
        "The White House Hosts Third AI Education Task Force Meeting with Educators and Parents",
        "The White House",
        "https://www.whitehouse.gov/releases/2025/12/31600/",
        "2025-12-11",
        "unknown",
    ),
    (
        "Lead the World in AI",
        "The White House",
        "https://www.whitehouse.gov/priorities/tech-innovation/",
        "2026-01-22",
        "unknown",
    ),
    (
        "Remarks by Director Michael Kratsios at the India AI Impact Summit",
        "The White House",
        "https://www.whitehouse.gov/releases/2026/02/remarks-by-director-michael-kratsios-at-the-india-ai-impact-summit/",
        "2026-02-20",
        "unknown",
    ),
    (
        "U.S. Promotes AI Adoption, Sovereignty, and Exports at India AI Impact Summit",
        "The White House",
        "https://www.whitehouse.gov/releases/2026/02/u-s-promotes-ai-adoption-sovereignty-and-exports-at-india-ai-impact-summit/",
        "2026-02-20",
        "unknown",
    ),
    (
        "President Donald J. Trump Unveils National AI Legislative Framework",
        "The White House",
        "https://www.whitehouse.gov/releases/2026/03/president-donald-j-trump-unveils-national-ai-legislative-framework/",
        "2026-03-20",
        "unknown",
    ),
    (
        "Trump Administration Announces More Than $5 Billion for the Genesis Mission, a National Mission on AI for Science",
        "The White House",
        "https://www.whitehouse.gov/releases/2026/07/45502/",
        "2026-07-22",
        "unknown",
    ),
]

REJECTED_URLS = [
    "https://example.com/ostp/ai",
    "https://whitehouse.gov.example/ostp/",
    "https://www.whitehouse.gov.example/releases/ai",
    "https://notwhitehouse.gov/ostp/",
    "https://bidenwhitehouse.archives.gov/ostp/ai-bill-of-rights/",
    "https://www.ai.gov/",
    "http://www.whitehouse.gov/ostp/",
    "https://user:pass@www.whitehouse.gov/ostp/",
    "https://www.whitehouse.gov/ostp/?utm_source=x",
    "https://www.whitehouse.gov/ostp/#ai",
    "https://www.whitehouse.gov:443/ostp/",
    "https://www.whitehouse.gov/wp-content/uploads/2025/07/Americas-AI-Action-Plan.pdf",
    "https://www.whitehouse.gov/releases/2025/07/example.pdf",
    "https://www.whitehouse.gov/about-the-white-house/air-force-one/",
    "https://127.0.0.1/ostp/",
    "https://www.whitehouse.gov/ostp-fake/",
]

BODY = "FULL DOCUMENT BODY that must not be stored."


def _sample() -> dict:
    return copy.deepcopy(load_catalog()["entries"][0])


def test_catalog_rows_match_confirmed_html_pages():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert "HTML" in catalog["description"]
    assert "us_government_work" in catalog["description"]
    assert "creative_commons" in catalog["description"]
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 15
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, publisher, url, published, rights = expected
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["title"] == title
        assert entry["publisher"] == publisher
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == rights
        assert entry["rights"] == RIGHTS_UNKNOWN
        assert url.startswith("https://www.whitehouse.gov/")
        assert not url.lower().endswith(".pdf")
        assert is_official_host(url.split("/")[2])
    dates = [entry["date"] for entry in entries]
    assert dates == sorted(dates)
    assert "2026-02-05" not in dates
    assert "2026-08-10" not in dates


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog(FIXTURE)
    assert len(catalog["entries"]) == 15
    blob = FIXTURE.read_text(encoding="utf-8")
    assert "p(doom)" not in blob.casefold()
    assert "<html" not in blob.casefold()
    assert ".pdf" not in blob.casefold()
    assert "by the authority vested" not in blob.casefold()
    for entry in catalog["entries"]:
        assert all(len(value) <= 400 for value in entry.values())


def test_non_government_and_pdf_urls_are_rejected():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError, match="official White House or OSTP"):
            validate_canonical_url(url)
    assert not is_official_host("whitehouse.gov.example")
    assert not is_official_host("notostp.gov")
    assert is_official_host("www.whitehouse.gov")
    assert is_official_host("ostp.gov")
    assert validate_canonical_url("https://www.whitehouse.gov/ostp/") == "https://www.whitehouse.gov/ostp/"
    assert (
        validate_canonical_url("https://www.ostp.gov/ai-policy")
        == "https://www.ostp.gov/ai-policy"
    )


def test_unknown_date_is_accepted_and_other_rights_are_rejected():
    unknown = _sample()
    unknown["date"] = UNKNOWN_DATE
    validate_entry(unknown)
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2025-07-23") == "2025-07-23"
    with pytest.raises(CatalogError, match="date"):
        validate_date("July 23, 2025")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2025-02-31")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024")

    document = copy.deepcopy(load_catalog())
    document["entries"][-1]["date"] = UNKNOWN_DATE
    validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = UNKNOWN_DATE
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)

    for label in ("cc-by", "cc-by-sa", "cc0", "public-domain", "us-government-work", ""):
        wrong = _sample()
        wrong["rights"] = label
        with pytest.raises(CatalogError, match="rights"):
            validate_entry(wrong)

    missing = _sample()
    del missing["publisher"]
    with pytest.raises(CatalogError, match="publisher"):
        validate_entry(missing)


def test_rights_field_rules():
    body_only = (
        "<p>This is a work of the United States Government.</p>"
        "<p>Licensed under CC BY 4.0 on a public .gov page. Copyright 2024.</p>"
    )
    assert rights_from_page(body_only) == RIGHTS_UNKNOWN
    assert rights_from_page("<footer>Copyright 2025 The White House</footer>") == RIGHTS_UNKNOWN
    assert rights_from_page('<meta name="copyright" content="2024">') == RIGHTS_UNKNOWN
    hidden = (
        "<script>This is a work of the United States Government. CC BY 4.0.</script>"
        "<p>No rights field.</p>"
    )
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN

    government = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(government) == RIGHTS_US_GOVERNMENT_WORK
    labeled = "<dt>Rights</dt><dd>U.S. government work</dd><p>Copyright 2024</p>"
    assert rights_from_page(labeled) == RIGHTS_US_GOVERNMENT_WORK
    negated = '<meta name="rights" content="Not a work of the United States Government.">'
    assert rights_from_page(negated) == RIGHTS_UNKNOWN

    cc_by = '<meta name="rights" content="Licensed under CC BY 4.0.">'
    assert rights_from_page(cc_by) == RIGHTS_CREATIVE_COMMONS
    cc_by_sa = (
        '<link rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">'
    )
    assert rights_from_page(cc_by_sa) == RIGHTS_CREATIVE_COMMONS
    cc0 = (
        '<script type="application/ld+json">'
        '{"license":"https://creativecommons.org/publicdomain/zero/1.0/"}'
        "</script>"
    )
    assert rights_from_page(cc0) == RIGHTS_CREATIVE_COMMONS
    attribution = (
        '<meta name="dcterms.license" content="Creative Commons Attribution-ShareAlike 4.0">'
    )
    assert rights_from_page(attribution) == RIGHTS_CREATIVE_COMMONS

    for deed in (
        "CC BY-NC 4.0",
        "CC BY-ND 4.0",
        "CC BY-NC-SA 4.0",
        "CC BY-NC-ND 4.0",
        "Creative Commons Attribution-NonCommercial 4.0",
        "Creative Commons",
        "public domain",
    ):
        assert rights_from_page(f'<meta name="rights" content="{deed}">') == RIGHTS_UNKNOWN
    by_nd = '<link rel="license" href="https://creativecommons.org/licenses/by-nd/4.0/deed">'
    assert rights_from_page(by_nd) == RIGHTS_UNKNOWN
    mixed = '<meta name="rights" content="CC BY 4.0 and CC BY-NC 4.0">'
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN


def test_updated_modified_and_copyright_years_are_not_publication_dates():
    assert publication_date_from_page("<p>Copyright 2024. Updated 2026.</p>") == UNKNOWN_DATE
    modified = (
        '<meta property="article:modified_time" content="2026-08-13T11:30:00+00:00">'
        '<meta property="og:updated_time" content="2026-09-01T00:00:00+00:00">'
        '<meta name="copyright" content="Copyright 2024">'
        '<script type="application/ld+json">{"dateModified":"2026-02-05T14:50:15+00:00"}</script>'
    )
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    published = modified + '<meta property="article:published_time" content="2026-01-22T14:00:00+00:00">'
    assert publication_date_from_page(published) == "2026-01-22"
    issued = '<meta name="dcterms.issued" content="2025-04-07">' + modified
    assert publication_date_from_page(issued) == "2025-04-07"
    assert publication_date_from_page("<p>No date. The URL says 2025-07-23.</p>") == UNKNOWN_DATE


def test_fixture_page_keeps_metadata_and_not_the_document_body():
    html = HTML_FIXTURE.read_text(encoding="utf-8")
    record = page_record(
        html,
        page_url="https://www.whitehouse.gov/releases/2025/07/example-ai-policy-page/",
    )
    assert record["title"] == "Example AI Policy Page"
    assert record["publisher"] == "The White House"
    assert record["canonical_url"] == "https://www.whitehouse.gov/releases/2025/07/example-ai-policy-page/"
    assert record["date"] == "2025-07-23"
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    dumped = json.dumps(record)
    assert BODY not in dumped
    assert "Hacked" not in dumped
    assert "ignore previous instructions" not in dumped.casefold()
    assert "Executive order text" not in dumped


def test_duplicate_url_stored_body_and_wired_runner_are_rejected(tmp_path: Path):
    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = BODY
    stored = tmp_path / "body.json"
    stored.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(CatalogError, match="entry fields"):
        load_catalog(stored)

    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)


def test_catalog_is_not_wired_into_belief_collection():
    module_path = ROOT / "pipeline" / "pdoom_pipeline" / "catalogs" / "ostp_ai.py"
    source = module_path.read_text(encoding="utf-8")
    assert "p(doom)" not in source.casefold()
    assert "runner_wired = True" not in source
    assert "RUNNER_WIRED = True" not in source
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "requests" not in imported

    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/catalogs/__init__.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "ostp_ai" not in text
        assert "ostp_ai_pages" not in text
    init = (ROOT / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py").read_text(encoding="utf-8")
    assert ast.get_docstring(ast.parse(init)) == "Package marker."
