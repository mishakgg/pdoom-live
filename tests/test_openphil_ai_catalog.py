"""Offline checks for the Open Philanthropy AI risk, safety, and forecasting catalog. No network."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.openphil_ai as openphil_ai
from pdoom_pipeline.catalogs.openphil_ai import (
    PUBLISHER,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    date_from_page,
    html_response_is_confirmable,
    load_catalog,
    metadata_from_page,
    official_openphil_host,
    rights_from_page,
    title_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
    validate_entry,
)

SAMPLE_URL = "https://www.openphilanthropy.org/research/ai-forecasts/"
EARLIER_URL = "https://openphilanthropy.org/research/ai-safety/"
LATER_URL = "https://www.openphilanthropy.org/focus/ai-risk/"
REJECTED_URLS = [
    "https://coefficientgiving.org/research/ai-risk/",
    "https://example.com/research/ai-risk/",
    "https://openphilanthropy.org.example/research/ai-risk/",
    "https://www.openphilanthropy.org.example/research/ai-risk/",
    "https://blog.openphilanthropy.org/research/ai-risk/",
    "http://openphilanthropy.org/research/ai-risk/",
    "https://user:pass@openphilanthropy.org/research/ai-risk/",
    "https://www.openphilanthropy.org/research/ai-risk/?utm_source=x",
    "https://www.openphilanthropy.org/research/ai-risk/#section",
    "https://www.openphilanthropy.org/research/ai-risk.pdf",
    "https://www.openphilanthropy.org/research/ai-risk",
    "https://127.0.0.1/research/ai-risk/",
    "https://www.openphilanthropy.org/",
    "https://www.openphilanthropy.org/research/",
]


def _entry(url: str, published: str, title: str = "AI risk note") -> dict:
    return {
        "title": title,
        "publisher": PUBLISHER,
        "canonical_url": url,
        "date": published,
        "rights": RIGHTS_UNKNOWN,
    }


def _page(title: str, url: str, *, published: str = "", body: str = "This page is public.") -> str:
    published_meta = (
        f'<meta property="article:published_time" content="{published}" />' if published else ""
    )
    return f"""
    <html><head>
    <title>{title} | Open Philanthropy</title>
    <meta property="og:title" content="{title} | Open Philanthropy" />
    <meta property="og:site_name" content="Open Philanthropy" />
    <link rel="canonical" href="{url}" />
    {published_meta}
    </head><body>
    <h1>Open Philanthropy</h1>
    <h1>{title}</h1>
    <p>{body}</p>
    <footer>Copyright 2024 Open Philanthropy. All rights reserved.
    <a href="https://www.openphilanthropy.org/terms/">Terms</a></footer>
    </body></html>
    """


def test_catalog_has_no_confirmed_rows():
    catalog = load_catalog()
    assert catalog["catalog_id"] == "openphil_ai_pages"
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert catalog["entries"] == []
    assert "openphilanthropy.org" in catalog["description"]
    assert "No HTML page was confirmed" in catalog["description"]
    rights_counts: dict[str, int] = {}
    unknown_dates = 0
    for entry in catalog["entries"]:
        rights_counts[entry["rights"]] = rights_counts.get(entry["rights"], 0) + 1
        if entry["date"] == UNKNOWN_DATE:
            unknown_dates += 1
    assert rights_counts == {}
    assert unknown_dates == 0
    assert RIGHTS_CREATIVE_COMMONS not in rights_counts


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    source = inspect.getsource(openphil_ai)
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
    assert "httpx" not in imported
    assert "urllib" not in imported
    assert not any(name.startswith("urllib.") for name in imported)
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "pdoom_pipeline.belief.collect" not in imported
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "import urllib" not in source
    assert "from urllib" not in source
    assert "collect_beliefs" not in source
    root = Path(__file__).resolve().parents[1]
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/catalogs/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "openphil" not in text
        assert "runner_wired = True" not in text


def test_catalog_file_stores_no_page_body_or_probability():
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<p>" not in raw
    assert "<html" not in raw.casefold()
    assert "doctype" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert "p(doom)" not in raw.casefold()
    document = json.loads(raw)
    assert document["entries"] == []
    assert set(document) == {"catalog_id", "description", "runner_wired", "entries"}


def test_nc_and_nd_notices_stay_unknown():
    notices = [
        "<p>Licensed under CC BY-NC 4.0.</p>",
        "<p>Licensed under CC BY-ND 4.0.</p>",
        "<p>Licensed under CC BY-NC-SA 4.0.</p>",
        "<p>Licensed under CC BY-NC-ND 4.0.</p>",
        "<p>Creative Commons Attribution-NonCommercial 4.0.</p>",
        "<p>Creative Commons Attribution-NoDerivatives 4.0.</p>",
        "<p>Creative Commons Attribution-NonCommercial-ShareAlike 4.0.</p>",
        "<p>Creative Commons Attribution-NonCommercial-NoDerivatives 4.0.</p>",
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>',
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-ND</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY-NC-ND</a>',
        "<p>CC BY&#45;NC</p>",
        "<p>CC BY–ND</p>",
        '<a href="https://creativecommons.org/licenses/">Creative Commons</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>',
        "<p>Public Domain Mark 1.0</p>",
        "<p>This page is public.</p>",
        "<p>Copyright 2024 Open Philanthropy. All rights reserved.</p>",
        '<p>See the <a href="https://www.openphilanthropy.org/terms/">terms</a>.</p>',
        "<script>Licensed under CC BY 4.0. https://creativecommons.org/licenses/by/4.0/</script><p>All rights reserved.</p>",
    ]
    for page in notices:
        assert rights_from_page(page) == RIGHTS_UNKNOWN


def test_by_nc_url_stays_unknown_when_anchor_text_says_cc_by():
    deceptive = '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>'
    assert rights_from_page(deceptive) == RIGHTS_UNKNOWN
    legalcode = '<a href="https://creativecommons.org/licenses/by-nc/4.0/legalcode">CC BY</a>'
    assert rights_from_page(legalcode) == RIGHTS_UNKNOWN
    by_nd = '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY</a>'
    assert rights_from_page(by_nd) == RIGHTS_UNKNOWN
    by_nc_sa = '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY</a>'
    assert rights_from_page(by_nc_sa) == RIGHTS_UNKNOWN
    by_nc_nd = '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY</a>'
    assert rights_from_page(by_nc_nd) == RIGHTS_UNKNOWN


def test_cc0_cc_by_and_cc_by_sa_become_creative_commons():
    pages = [
        "<p>Licensed under CC0 1.0.</p>",
        "<p>Dedicated to the public domain under Creative Commons Zero.</p>",
        "<p>Licensed under CC BY 4.0.</p>",
        "<p>Creative Commons Attribution 4.0 International License.</p>",
        "<p>Licensed under CC BY-SA 4.0.</p>",
        "<p>Creative Commons Attribution-ShareAlike 4.0.</p>",
        '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>',
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA</a>',
        (
            '<script type="application/ld+json">'
            '{"license":"https:\\/\\/creativecommons.org\\/licenses\\/by\\/4.0\\/"}'
            "</script>"
        ),
    ]
    for page in pages:
        assert rights_from_page(page) == RIGHTS_CREATIVE_COMMONS
    assert "Full report text" not in rights_from_page(
        "<p>Licensed under CC BY 4.0.</p><p>" + ("Full report text. " * 40) + "</p>"
    )


def test_mixed_permissive_and_restricted_notice_stays_unknown():
    mixed_text = "<p>Licensed under CC BY 4.0. Also available under CC BY-NC 4.0.</p>"
    assert rights_from_page(mixed_text) == RIGHTS_UNKNOWN
    mixed_links = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>'
    )
    assert rights_from_page(mixed_links) == RIGHTS_UNKNOWN
    mixed_sa = "<p>CC BY-SA 4.0 and CC BY-ND 4.0.</p>"
    assert rights_from_page(mixed_sa) == RIGHTS_UNKNOWN
    mixed_zero = (
        '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>'
    )
    assert rights_from_page(mixed_zero) == RIGHTS_UNKNOWN
    structured = (
        '<script type="application/ld+json">'
        '{"license":"https://creativecommons.org/licenses/by/4.0/"}'
        "</script><p>Licensed under CC BY-NC-ND 4.0.</p>"
    )
    assert rights_from_page(structured) == RIGHTS_UNKNOWN


def test_modified_or_copyright_years_stay_unknown():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>Copyright 2024. © 2024. Updated 2024. Last modified 13 June 2024.</p>") == UNKNOWN_DATE
    modified = (
        '<meta property="article:modified_time" content="2024-06-13T04:28:32+00:00" />'
        '<meta property="og:updated_time" content="2025-01-02T00:00:00+00:00" />'
        '<script type="application/ld+json">{"dateModified":"2024-06-13","copyrightYear":2024}</script>'
        "<footer>Copyright 2024 Open Philanthropy. All rights reserved.</footer>"
    )
    assert date_from_page(modified) == UNKNOWN_DATE
    assert date_from_page('<meta name="citation_publication_date" content="2024" />') == UNKNOWN_DATE
    assert date_from_page('<meta name="citation_publication_date" content="Copyright 2024" />') == UNKNOWN_DATE
    published = (
        modified
        + '<meta property="article:published_time" content="2017-03-15T12:00:00+00:00" />'
    )
    assert date_from_page(published) == "2017-03-15"
    structured = (
        '<script type="application/ld+json">'
        '{"dateModified":"2024-06-13T00:00:00+00:00","datePublished":"2018-05-01T00:00:00+00:00"}'
        "</script>"
        '<meta property="article:published_time" content="1999-01-01T00:00:00+00:00" />'
        "<p>© 2024</p>"
    )
    assert date_from_page(structured) == "2018-05-01"
    invalid = (
        '<script type="application/ld+json">{"datePublished":"2024-13-40T00:00:00Z"}</script>'
        '<script type="application/ld+json">{"datePublished":"2016-11-02T00:00:00Z"}</script>'
    )
    assert date_from_page(invalid) == "2016-11-02"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("15 March 2017")
    with pytest.raises(CatalogError):
        validate_date("2020-02-31")


def test_title_uses_the_heading_not_the_branding_suffix():
    branded = """
    <h1>Open Philanthropy</h1>
    <h1>Research</h1>
    <h1>What should we learn from past AI forecasts?</h1>
    <meta property="og:title" content="What should we learn from past AI forecasts? | Open Philanthropy" />
    <meta property="og:site_name" content="Open Philanthropy" />
    """
    assert title_from_page(branded) == "What should we learn from past AI forecasts?"
    suffix_only = (
        '<meta property="og:title" content="Potential risks from advanced artificial intelligence - Open Philanthropy" />'
    )
    assert title_from_page(suffix_only) == "Potential risks from advanced artificial intelligence"


def test_metadata_record_keeps_the_confirmed_url_and_drops_the_body():
    page = _page(
        "What should we learn from past AI forecasts?",
        SAMPLE_URL,
        published="2019-08-14T00:00:00+00:00",
        body="Full report text that must not be stored. " * 30,
    )
    page = page.replace(SAMPLE_URL, "https://example.com/not-openphil/", 1)
    record = metadata_from_page(page, page_url=SAMPLE_URL)
    assert record == {
        "title": "What should we learn from past AI forecasts?",
        "publisher": PUBLISHER,
        "canonical_url": SAMPLE_URL,
        "date": "2019-08-14",
        "rights": RIGHTS_UNKNOWN,
    }
    assert "Full report text" not in json.dumps(record)
    assert "Copyright 2024" not in json.dumps(record)
    same = _page("What should we learn from past AI forecasts?", SAMPLE_URL, published="2019-08-14T00:00:00+00:00")
    assert metadata_from_page(same, page_url=SAMPLE_URL)["canonical_url"] == SAMPLE_URL


def test_non_html_and_challenge_responses_are_not_rows():
    article = _page("AI safety", SAMPLE_URL)
    assert html_response_is_confirmable(status=200, content_type="text/html; charset=utf-8", body=article)
    assert not html_response_is_confirmable(status=301, content_type="", body="")
    assert not html_response_is_confirmable(
        status=403,
        content_type="text/html",
        body="<html><head><title>403 Forbidden</title></head><body><h1>403 Forbidden</h1></body></html>",
    )
    challenge = (
        "<html><head><title>Just a moment...</title></head>"
        "<body>Checking your browser before accessing the site. cf-mitigated challenge-platform</body></html>"
    )
    assert not html_response_is_confirmable(status=200, content_type="text/html", body=challenge)
    assert not html_response_is_confirmable(status=200, content_type="application/pdf", body=article)
    assert not html_response_is_confirmable(status=200, content_type="text/plain", body="not html")


def test_non_openphil_urls_are_rejected_and_official_pages_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    accepted = [SAMPLE_URL, EARLIER_URL, LATER_URL]
    for url in accepted:
        assert validate_canonical_url(url) == url
    assert official_openphil_host("openphilanthropy.org")
    assert official_openphil_host("www.openphilanthropy.org")
    assert not official_openphil_host("coefficientgiving.org")
    assert not official_openphil_host("blog.openphilanthropy.org")
    assert not official_openphil_host("openphilanthropy.org.example")
    assert not official_openphil_host("127.0.0.1")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [
        _entry(EARLIER_URL, "2018-05-01", "AI safety"),
        _entry(LATER_URL, UNKNOWN_DATE, "AI risk"),
    ]
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [
        _entry(LATER_URL, "2020-01-02", "Later"),
        _entry(EARLIER_URL, "2020-01-01", "Earlier"),
    ]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "15 March 2017")]
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "2019-08-14")]
    document["entries"][0]["rights"] = "all_rights_reserved"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "2019-08-14")]
    document["entries"][0]["rights"] = RIGHTS_CREATIVE_COMMONS
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "2019-08-14")]
    document["entries"][0]["body"] = "full page"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "2019-08-14")]
    document["entries"][0]["pdf"] = "https://www.openphilanthropy.org/files/report.pdf"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "2019-08-14")]
    document["entries"][0]["amount"] = 1000
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "2019-08-14")]
    document["entries"][0]["probability"] = 0.5
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(SAMPLE_URL, "2019-08-14"), _entry(SAMPLE_URL, "2019-08-14")]
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)

    missing = _entry(SAMPLE_URL, "2019-08-14")
    del missing["publisher"]
    with pytest.raises(CatalogError, match="publisher"):
        validate_entry(missing)

    other_publisher = _entry(SAMPLE_URL, "2019-08-14")
    other_publisher["publisher"] = "Coefficient Giving"
    with pytest.raises(CatalogError, match="publisher"):
        validate_entry(other_publisher)
