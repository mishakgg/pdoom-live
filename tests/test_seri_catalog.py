"""Offline checks for the Stanford Existential Risks Initiative page catalog. No network."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.seri as seri
from pdoom_pipeline.catalogs.seri import (
    ALLOWED_RIGHTS,
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    PUBLISHER,
    RIGHTS_APACHE,
    RIGHTS_CC_BY,
    RIGHTS_CC_BY_NC,
    RIGHTS_CC_BY_NC_ND,
    RIGHTS_CC_BY_NC_SA,
    RIGHTS_CC_BY_ND,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_MIT,
    RIGHTS_MPL,
    RIGHTS_UK_OGL,
    RIGHTS_UNKNOWN,
    RIGHTS_US_GOVERNMENT_WORK,
    RUNNER_WIRED,
    TIMEOUT_SECONDS,
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    load_catalog,
    metadata_from_page,
    official_seri_host,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_URL = "https://seri.stanford.edu/research"
CHALLENGE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body><h1>Performing security verification</h1>"
    "<p>Enable JavaScript and cookies to continue.</p>"
    "<p>cf-mitigated: challenge</p></body></html>"
)
PAGE = """
<html><head>
<meta property="og:title" content="Research | Existential Risks Initiative" />
<meta property="og:site_name" content="Existential Risks Initiative" />
<link rel="canonical" href="https://hai.stanford.edu/research" />
</head>
<body>
<h1>Stanford Existential Risks Initiative</h1>
<h1>Research</h1>
<p>FULL PAGE TEXT that must not be stored.</p>
</body></html>
"""


def _entry(url: str, *, day: str = UNKNOWN_DATE, rights: str = RIGHTS_UNKNOWN) -> dict:
    return {
        "title": "Research",
        "publisher": PUBLISHER,
        "canonical_url": url,
        "date": day,
        "rights": rights,
    }


def test_sole_restricted_deeds_keep_their_own_tokens():
    assert rights_from_page("<p>Licensed under CC BY-NC 4.0.</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Licensed under CC BY-ND 4.0.</p>") == RIGHTS_CC_BY_ND
    assert rights_from_page("<p>Licensed under CC BY-NC-SA 4.0.</p>") == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>Licensed under CC BY-NC-ND 4.0.</p>") == RIGHTS_CC_BY_NC_ND
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-ND</a>') == RIGHTS_CC_BY_ND
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY-NC-ND</a>') == RIGHTS_CC_BY_NC_ND
    assert (
        rights_from_page('<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-SA</a>')
        == RIGHTS_UNKNOWN
    )
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial 4.0.</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Creative Commons Attribution-NoDerivatives 4.0.</p>") == RIGHTS_CC_BY_ND
    assert (
        rights_from_page("<p>Creative Commons Attribution-NonCommercial-ShareAlike 4.0.</p>")
        == RIGHTS_CC_BY_NC_SA
    )
    assert (
        rights_from_page("<p>Creative Commons Attribution-NonCommercial-NoDerivatives 4.0.</p>")
        == RIGHTS_CC_BY_NC_ND
    )
    assert rights_from_page("<p>https://creativecommons.org/licenses/</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Licensed under CC BY 4.0.</p>") == RIGHTS_CC_BY
    assert rights_from_page("<p>Creative Commons Attribution 4.0 International License.</p>") == RIGHTS_CC_BY
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">licence</a>') == RIGHTS_CC_BY
    assert rights_from_page("<p>Licensed under CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>Dedicated under CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY 4.0 and CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY-SA 4.0 and CC0.</p>") == RIGHTS_CREATIVE_COMMONS


def test_anchor_text_cc_by_on_a_by_nc_url_stays_unknown():
    restricted = (
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "https://creativecommons.org/licenses/by-nd/4.0/",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "https://creativecommons.org/publicdomain/mark/1.0/",
    )
    for href in restricted:
        assert rights_from_page(f'<a href="{href}">CC BY</a>') == RIGHTS_UNKNOWN
        assert rights_from_page(f'<a href="{href}">CC BY-SA</a>') == RIGHTS_UNKNOWN
    quoted = "<a href='https://creativecommons.org/licenses/by-nd'>CC BY</a>"
    assert rights_from_page(quoted) == RIGHTS_UNKNOWN
    bare = '<a href="https://creativecommons.org/licenses/">CC BY</a>'
    assert rights_from_page(bare) == RIGHTS_UNKNOWN
    mark_zero = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC0</a>'
    assert rights_from_page(mark_zero) == RIGHTS_UNKNOWN


def test_mixed_permissive_and_restricted_stays_unknown():
    mixed = "<p>Text is CC BY 4.0 and the figure is CC BY-NC 4.0.</p>"
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN
    beside = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY-NC-ND</a>'
    )
    assert rights_from_page(beside) == RIGHTS_UNKNOWN
    share = "<p>CC BY-SA 4.0 for the summary and CC BY-ND 4.0 for the chart.</p>"
    assert rights_from_page(share) == RIGHTS_UNKNOWN
    zero_nc = "<p>CC0 and CC BY-NC 4.0.</p>"
    assert rights_from_page(zero_nc) == RIGHTS_UNKNOWN
    hidden = "<script>Licensed under CC BY 4.0.</script><p>All rights reserved.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_a_public_domain_mark_is_not_cc0():
    mark = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>'
    assert rights_from_page(mark) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Public Domain Mark 1.0</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>This work is in the public domain.</p>") == RIGHTS_UNKNOWN
    zero = '<a href="https://creativecommons.org/publicdomain/zero/1.0/">public domain</a>'
    assert rights_from_page(zero) == RIGHTS_CREATIVE_COMMONS


def test_public_pages_copyright_terms_and_edu_hosts_are_not_licences():
    public = "<p>This page is public.</p>"
    reserved = "<p>Copyright 2024 Stanford University. All rights reserved.</p>"
    terms = '<p>See the <a href="https://www.stanford.edu/site/terms/">Terms of Use</a>.</p>'
    edu = "<p>Published at https://seri.stanford.edu/ on a .edu host.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    assert rights_from_page(edu) == RIGHTS_UNKNOWN
    body_gov = "<p>This essay says the item is a US government work.</p>"
    assert rights_from_page(body_gov) == RIGHTS_UNKNOWN
    rights = '<meta name="dc.rights" content="This item is a work of the United States government.">'
    assert rights_from_page(rights) == RIGHTS_US_GOVERNMENT_WORK
    negated = '<meta name="dc.rights" content="Not a work of the US government.">'
    assert rights_from_page(negated) == RIGHTS_UNKNOWN
    ogl = "<p>Available under the Open Government Licence.</p>"
    assert rights_from_page(ogl) == RIGHTS_UK_OGL
    american = "<p>Available under the Open Government License.</p>"
    assert rights_from_page(american) == RIGHTS_UNKNOWN
    script_ogl = "<script>Open Government Licence</script><p>All rights reserved.</p>"
    assert rights_from_page(script_ogl) == RIGHTS_UNKNOWN
    hyphenated = '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">licence</a>'
    assert rights_from_page(hyphenated) == RIGHTS_UNKNOWN


def test_software_licences_keep_their_own_tokens():
    assert rights_from_page("<p>Licensed under the MIT License.</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Licensed under the Apache License 2.0.</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Licensed under MPL-2.0.</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MIT License and Apache License 2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and CC BY 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and CC BY-NC 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MPL-2.0 and CC0.</p>") == RIGHTS_UNKNOWN


def test_a_challenge_or_non_html_response_is_not_stored():
    assert record_from_response(
        status=202,
        content_type="text/html; charset=UTF-8",
        page_html=PAGE,
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=CHALLENGE_HTML,
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=PAGE,
        page_url=SAMPLE_URL,
        headers={"cf-mitigated": "challenge"},
    ) is None
    siteground = "<html><title>Please wait</title><body>sgcaptcha siteground captcha</body></html>"
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=siteground,
        page_url=SAMPLE_URL,
    ) is None
    akamai = "<html><body>errors.edgesuite.net akamai bot manager</body></html>"
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=akamai,
        page_url=SAMPLE_URL,
    ) is None
    robot = "<html><title>Are you a robot?</title><p>robot interstitial</p></html>"
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=robot,
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7",
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/xml",
        page_html="<urlset></urlset>",
        page_url=SAMPLE_URL,
    ) is None
    for url in (
        "https://hai.stanford.edu/",
        "https://crfm.stanford.edu/about",
        "https://www.stanford.edu/",
        "https://example.com/seri",
    ):
        assert record_from_response(
            status=200,
            content_type="text/html",
            page_html=PAGE,
            page_url=url,
        ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=PAGE,
        page_url=SAMPLE_URL,
        redirect_count=MAX_REDIRECTS + 1,
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=PAGE,
        page_url=SAMPLE_URL,
        elapsed_seconds=TIMEOUT_SECONDS + 1,
    ) is None
    huge = PAGE + ("x" * (MAX_RESPONSE_BYTES + 1))
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=huge,
        page_url=SAMPLE_URL,
    ) is None
    with pytest.raises(CatalogError, match="challenge page is not stored"):
        metadata_from_page(CHALLENGE_HTML, page_url=SAMPLE_URL)


def test_a_successful_html_response_stores_metadata_only():
    record = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=PAGE,
        page_url=SAMPLE_URL,
    )
    assert record == {
        "title": "Research",
        "publisher": PUBLISHER,
        "canonical_url": SAMPLE_URL,
        "date": UNKNOWN_DATE,
        "rights": RIGHTS_UNKNOWN,
    }
    assert "FULL PAGE TEXT" not in json.dumps(record)
    assert "hai.stanford.edu" not in json.dumps(record)


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["catalog_id"] == "seri_pages"
    assert catalog["runner_wired"] is False
    assert isinstance(catalog["entries"], list)
    source = inspect.getsource(seri)
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    joined = " ".join(sorted(imported))
    assert "requests" not in joined
    assert "httpx" not in joined
    assert "urllib" not in joined
    assert "pdoom_pipeline.fetch" not in joined
    assert "pdoom_pipeline.belief" not in joined
    assert "pdoom_pipeline.urls" in joined
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/catalogs/__init__.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "catalogs.seri" not in text
        assert "seri_pages" not in text
    init = (ROOT / "pipeline/pdoom_pipeline/catalogs/__init__.py").read_text(encoding="utf-8")
    assert ast.get_docstring(ast.parse(init)) == "Package marker."


def test_runner_wired_is_false():
    assert RUNNER_WIRED is False
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    source = Path(seri.__file__).read_text(encoding="utf-8")
    assert "RUNNER_WIRED = True" not in source
    document = copy.deepcopy(catalog)
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)


def test_catalog_file_stores_no_body_or_probability():
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<p>" not in raw
    assert "<html" not in raw.casefold()
    assert "doctype" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert "probability" not in raw.casefold()
    assert "p(doom)" not in raw.casefold()
    document = json.loads(raw)
    assert document["runner_wired"] is False
    assert len(document["entries"]) == 71
    assert "seri.stanford.edu" in document["description"]
    assert "creative_commons" in document["description"]
    assert "hai" in document["description"].casefold()
    assert "crfm" in document["description"].casefold()
    for entry in document["entries"]:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["publisher"] == PUBLISHER
        assert entry["rights"] == RIGHTS_UNKNOWN
        assert entry["rights"] in ALLOWED_RIGHTS
        assert entry["canonical_url"].startswith("https://seri.stanford.edu")
        assert "hai.stanford.edu" not in entry["canonical_url"]
        assert "crfm.stanford.edu" not in entry["canonical_url"]
        assert official_seri_host(entry["canonical_url"].split("/")[2])
        for value in entry.values():
            assert isinstance(value, str)
            assert len(value) <= 400


def test_dates_ignore_updated_modified_and_copyright_years():
    assert publication_date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert publication_date_from_page("<footer>Copyright 2024. Updated 2025. Modified 2026.</footer>") == UNKNOWN_DATE
    assert publication_date_from_page('<meta property="article:modified_time" content="2024-06-13T00:00:00Z" />') == UNKNOWN_DATE
    assert publication_date_from_page('<meta property="og:updated_time" content="2024-06-13" />') == UNKNOWN_DATE
    listed = """
    <div class="su-news-publishing-date"><time datetime="2024-01-02T00:00:00Z">January 2, 2024</time></div>
    <div class="su-news-publishing-date"><time datetime="2025-08-03T12:00:00Z">August 3, 2025</time></div>
    """
    assert publication_date_from_page(listed) == UNKNOWN_DATE
    single = '<div class="node su-news-publishing-date"><time datetime="2025-08-03T12:00:00Z">August 3, 2025</time></div>'
    assert publication_date_from_page(single) == "2025-08-03"
    published = (
        '<meta property="article:modified_time" content="2026-01-01T00:00:00Z" />'
        '<meta property="article:published_time" content="2024-04-04T00:00:00Z" />'
        "<footer>© 2020</footer>"
    )
    assert publication_date_from_page(published) == "2024-04-04"
    structured = (
        '<script type="application/ld+json">'
        '{"dateModified":"2026-01-01","datePublished":"2023-11-06"}'
        "</script>"
    )
    assert publication_date_from_page(structured) == "2023-11-06"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("2024")
    with pytest.raises(CatalogError):
        validate_date("2024-02-31")


def test_other_stanford_hosts_are_rejected():
    rejected = [
        "https://hai.stanford.edu/",
        "https://www.hai.stanford.edu/news",
        "https://crfm.stanford.edu/",
        "https://www.crfm.stanford.edu/about",
        "https://www.seri.stanford.edu/",
        "https://seri.stanford.edu.example/",
        "http://seri.stanford.edu/research",
        "https://user:pass@seri.stanford.edu/research",
        "https://seri.stanford.edu/research?utm_source=x",
        "https://seri.stanford.edu/research#section",
        "https://seri.stanford.edu/report.pdf",
        "https://seri.stanford.edu/admin/",
        "https://127.0.0.1/",
        "https://seri.stanford.edu/research/../news",
    ]
    for url in rejected:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    assert validate_canonical_url("https://seri.stanford.edu/") == "https://seri.stanford.edu/"
    assert validate_canonical_url("https://seri.stanford.edu/research") == "https://seri.stanford.edu/research"
    assert official_seri_host("seri.stanford.edu")
    assert not official_seri_host("hai.stanford.edu")
    assert not official_seri_host("crfm.stanford.edu")
    assert not official_seri_host("www.seri.stanford.edu")
    assert not official_seri_host("127.0.0.1")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    document["entries"] = [
        _entry("https://seri.stanford.edu/news", day="2024-01-01"),
        _entry("https://seri.stanford.edu/research", day="2024-02-02"),
    ]
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [
        _entry("https://seri.stanford.edu/research", day="2024-02-02"),
        _entry("https://seri.stanford.edu/news", day="2024-01-01"),
    ]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [
        _entry("https://seri.stanford.edu/research"),
        _entry("https://seri.stanford.edu/research"),
    ]
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry("https://seri.stanford.edu/research", rights="cc-by-nc")]
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry("https://seri.stanford.edu/research")]
    document["entries"][0]["body"] = "full page"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry("https://seri.stanford.edu/research")]
    document["entries"][0]["probability"] = 0.2
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry("https://hai.stanford.edu/")]
    with pytest.raises(CatalogError):
        validate_catalog(document)

    validate_catalog(load_catalog())
