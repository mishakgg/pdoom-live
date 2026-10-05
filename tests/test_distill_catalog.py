"""Offline checks for the Distill article catalog. No network."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.distill as distill
from pdoom_pipeline.catalogs.distill import (
    PUBLISHER,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_UNKNOWN,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    date_from_page,
    is_challenge_page,
    load_catalog,
    official_distill_host,
    page_record,
    record_from_response,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

SAMPLE_URL = "https://distill.pub/2017/research-debt/"
BODY = "Full article text that must not be stored. " * 30
CHALLENGE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body><h1>Performing security verification</h1>"
    "<p>Checking your browser before the site will load. "
    "Enable JavaScript and cookies to continue.</p>"
    "<p>cf-mitigated: challenge</p></body></html>"
)
CC_BY = (
    "<p>Diagrams and text are licensed under Creative Commons Attribution "
    "CC-BY 4.0, unless noted otherwise.</p>"
)


def _page(title: str, *, published: str | None = None, extra: str = "") -> str:
    published_tag = (
        f'<meta name="citation_publication_date" content="{published}">' if published else ""
    )
    return (
        "<html><head>"
        f'<meta property="og:title" content="{title} | Distill">'
        '<meta property="og:site_name" content="Distill">'
        f"{published_tag}"
        '<link rel="canonical" href="https://example.com/not-distill">'
        "</head><body>"
        f"<h1>{title}</h1><p>{BODY}</p>{extra}</body></html>"
    )


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["catalog_id"] == "distill_pages"
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    source = inspect.getsource(distill)
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
    assert "httpx" not in imported
    assert "urllib" not in imported
    assert "urllib.request" not in imported
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "import urllib" not in source
    assert "import requests" not in source
    assert "import httpx" not in source


def test_runner_wired_is_false_and_catalog_is_not_a_belief_collector():
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    assert "bounded GET" in catalog["description"]
    assert "unknown" in catalog["description"]
    assert "creative_commons" in catalog["description"]
    root = Path(__file__).resolve().parents[1]
    module = (root / "pipeline" / "pdoom_pipeline" / "catalogs" / "distill.py").read_text(encoding="utf-8")
    assert "RUNNER_WIRED = False" in module
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/catalogs/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "distill" not in text
    init = root / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py"
    assert ast.get_docstring(ast.parse(init.read_text(encoding="utf-8"))) == "Package marker."


def test_confirmed_articles_are_metadata_from_bounded_gets():
    catalog = load_catalog()
    entries = catalog["entries"]
    assert len(entries) == 45
    assert [entry["rights"] for entry in entries] == [RIGHTS_CREATIVE_COMMONS] * 45
    by_url = {entry["canonical_url"]: entry for entry in entries}
    debt = by_url["https://distill.pub/2017/research-debt/"]
    assert debt["title"] == "Research Debt"
    assert debt["date"] == "2017-03-22"
    assert debt["publisher"] == PUBLISHER
    safety = by_url["https://distill.pub/2019/safety-needs-social-scientists/"]
    assert safety["title"] == "AI Safety Needs Social Scientists"
    assert safety["date"] == "2019-02-19"
    assert by_url["https://distill.pub/2016/augmented-rnns/"]["date"] == "2016-09-08"
    assert by_url["https://distill.pub/2021/gnn-intro/"]["title"] == (
        "A Gentle Introduction to Graph Neural Networks"
    )
    absent = [
        "https://distill.pub/",
        "https://distill.pub/about/",
        "https://distill.pub/journal/",
        "https://distill.pub/archive/",
        "https://distill.pub/2017/momentum/",
        "https://distill.pub/2020/circuits/zoom-in/",
        "https://distill.pub/2020/circuits/early-vision/",
        "https://distill.pub/2020/circuits/curve-detectors/",
        "https://distill.pub/2020/circuits/frequency-edges/",
    ]
    for url in absent:
        assert url not in by_url


def test_catalog_file_stores_no_body_or_probability():
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<p>" not in raw
    assert "<html" not in raw.casefold()
    assert "doctype" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert '"body"' not in raw
    assert '"probability"' not in raw
    assert '"pdoom"' not in raw
    assert '"p_doom"' not in raw
    assert '"explanation"' not in raw
    assert '"figure"' not in raw
    assert "p(doom)" not in raw.casefold()
    document = json.loads(raw)
    assert document["runner_wired"] is False
    assert isinstance(document["entries"], list)
    for entry in document["entries"]:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["publisher"] == PUBLISHER
        assert entry["rights"] in {RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS}
        assert official_distill_host(entry["canonical_url"].split("/")[2])
        for value in entry.values():
            assert isinstance(value, str)
            assert len(value) < 400
            assert "<" not in value


def test_sole_nc_and_nd_stay_unknown():
    sole = [
        "<p>Licensed under CC BY-NC 4.0.</p>",
        "<p>Licensed under CC BY-ND 4.0.</p>",
        "<p>CC-BY-NC</p>",
        "<p>CC-BY-ND</p>",
        "<p>Licensed under CC BY-NC-SA 4.0.</p>",
        "<p>Licensed under CC BY-NC-ND.</p>",
        "<p>https://creativecommons.org/licenses/by-nc/4.0/</p>",
        "<p>https://creativecommons.org/licenses/by-nd/4.0/</p>",
        "<p>https://creativecommons.org/licenses/by-nc-sa/4.0/</p>",
        "<p>https://creativecommons.org/licenses/by-nc-nd/4.0/</p>",
        "<p>Creative Commons Attribution-NonCommercial 4.0</p>",
        "<p>Creative Commons Attribution-NoDerivatives 4.0</p>",
        '<link rel="license" href="https://creativecommons.org/licenses/by-nc/4.0/">',
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">deed</a>',
    ]
    for page in sole:
        assert rights_from_page(page) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Licensed under CC BY 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>Licensed under CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC0 1.0 Universal</p>") == RIGHTS_CREATIVE_COMMONS


def test_anchor_text_cc_by_on_a_by_nc_url_stays_unknown():
    anchor = '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>'
    assert rights_from_page(anchor) == RIGHTS_UNKNOWN
    longer = '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en">CC BY</a>'
    assert rights_from_page(longer) == RIGHTS_UNKNOWN
    bare = '<a href="https://creativecommons.org/licenses/">CC BY</a>'
    assert rights_from_page(bare) == RIGHTS_UNKNOWN
    by_url = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
    assert rights_from_page(by_url) == RIGHTS_CREATIVE_COMMONS
    by_sa_url = '<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY</a>'
    assert rights_from_page(by_sa_url) == RIGHTS_CREATIVE_COMMONS


def test_mixed_permissive_and_restricted_stays_unknown():
    mixed = "<p>Text is licensed under CC BY 4.0. Figures are licensed under CC BY-NC 4.0.</p>"
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN
    urls = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-ND</a>'
    )
    assert rights_from_page(urls) == RIGHTS_UNKNOWN
    share = "<p>CC BY-SA 4.0 and CC BY-NC-SA 4.0.</p>"
    assert rights_from_page(share) == RIGHTS_UNKNOWN


def test_a_public_domain_mark_is_not_cc0():
    mark = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>'
    assert rights_from_page(mark) == RIGHTS_UNKNOWN
    mark_text = "<p>Public Domain Mark 1.0</p>"
    assert rights_from_page(mark_text) == RIGHTS_UNKNOWN
    mark_labeled_cc0 = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC0</a>'
    assert rights_from_page(mark_labeled_cc0) == RIGHTS_UNKNOWN
    zero = '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
    assert rights_from_page(zero) == RIGHTS_CREATIVE_COMMONS
    public = "<p>This page is public.</p><p>Copyright 2017 Distill. All rights reserved.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    notice = "<p>© 2017 Distill.</p>"
    assert rights_from_page(notice) == RIGHTS_UNKNOWN


def test_a_challenge_or_non_html_response_is_not_stored():
    assert is_challenge_page(CHALLENGE_HTML)
    assert (
        record_from_response(
            status=200,
            content_type="text/html; charset=UTF-8",
            page_html=CHALLENGE_HTML,
            page_url=SAMPLE_URL,
        )
        is None
    )
    assert (
        record_from_response(
            status=403,
            content_type="text/html",
            page_html=CHALLENGE_HTML,
            page_url=SAMPLE_URL,
            headers={"cf-mitigated": "challenge"},
        )
        is None
    )
    good = _page("Research Debt", published="2017/03/22", extra=CC_BY)
    assert (
        record_from_response(
            status=200,
            content_type="text/html",
            page_html=good,
            page_url=SAMPLE_URL,
            headers={"CF-Mitigated": "challenge"},
        )
        is None
    )
    assert (
        record_from_response(
            status=200,
            content_type="application/pdf",
            page_html="%PDF-1.7 synthetic",
            page_url=SAMPLE_URL,
        )
        is None
    )
    assert (
        record_from_response(
            status=200,
            content_type="text/plain",
            page_html="not html",
            page_url=SAMPLE_URL,
        )
        is None
    )
    assert (
        record_from_response(
            status=200,
            content_type="text/html",
            page_html=good,
            page_url="https://example.com/2017/research-debt/",
        )
        is None
    )
    captcha = "<html><head><title>Verify</title></head><body><div class='g-recaptcha'></div></body></html>"
    assert is_challenge_page(captcha)
    assert (
        record_from_response(
            status=200,
            content_type="text/html",
            page_html=captcha,
            page_url=SAMPLE_URL,
        )
        is None
    )
    with pytest.raises(CatalogError, match="challenge page is not stored"):
        page_record(CHALLENGE_HTML, page_url=SAMPLE_URL)
    assert "Just a moment" not in json.dumps(load_catalog())


def test_updated_modified_and_copyright_years_are_not_publication_dates():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    modified = (
        '<meta property="article:modified" content="2018-05-22T18:08:59.000Z">'
        '<meta property="og:updated_time" content="2019-01-01">'
        '<meta property="article:created" content="2016-01-01">'
        "<footer>Copyright 2017 Distill.</footer>"
    )
    assert date_from_page(modified) == UNKNOWN_DATE
    published = (
        '<meta name="citation_publication_date" content="2017/03/22">'
        '<meta property="article:modified" content="2018-05-22T18:08:59.000Z">'
        "<footer>© 2017</footer>"
    )
    assert date_from_page(published) == "2017-03-22"
    article_published = '<meta property="article:published" content="2019-02-19">'
    assert date_from_page(article_published) == "2019-02-19"
    invalid = (
        '<meta name="citation_publication_date" content="NaN-NaN-NaN">'
        '<meta property="article:published" content="2017-02-31">'
        '<script type="application/ld+json">{"datePublished":"2016-10-17"}</script>'
    )
    assert date_from_page(invalid) == "2016-10-17"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("2017")
    with pytest.raises(CatalogError):
        validate_date("22 March 2017")


def test_page_record_keeps_metadata_and_not_the_article_body():
    record = page_record(
        _page("Research Debt", published="2017/03/22", extra=CC_BY),
        page_url=SAMPLE_URL,
    )
    assert record == {
        "title": "Research Debt",
        "publisher": PUBLISHER,
        "canonical_url": SAMPLE_URL,
        "date": "2017-03-22",
        "rights": RIGHTS_CREATIVE_COMMONS,
    }
    stored = json.dumps(record)
    assert "Full article text" not in stored
    assert "creativecommons.org" not in stored
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    off_canonical = page_record(
        _page("Research Debt", published="2017/03/22"),
        page_url=SAMPLE_URL,
    )
    assert off_canonical["canonical_url"] == SAMPLE_URL
    assert off_canonical["rights"] == RIGHTS_UNKNOWN


def test_non_distill_urls_are_rejected():
    rejected = [
        "https://example.com/2017/research-debt/",
        "https://www.distill.pub/2017/research-debt/",
        "https://distill.pub.example/2017/research-debt/",
        "http://distill.pub/2017/research-debt/",
        "https://user:pass@distill.pub/2017/research-debt/",
        "https://distill.pub/2017/research-debt/?utm=1",
        "https://distill.pub/2017/research-debt/#section",
        "https://distill.pub/2017/research-debt",
        "https://distill.pub/about/",
        "https://distill.pub/",
        "https://distill.pub/rss.xml",
        "https://127.0.0.1/2017/research-debt/",
        "https://distill.pub/2017/research-debt.pdf",
    ]
    for url in rejected:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    assert validate_canonical_url("https://distill.pub/2020/circuits/zoom-in/") == (
        "https://distill.pub/2020/circuits/zoom-in/"
    )
    assert official_distill_host("distill.pub")
    assert not official_distill_host("www.distill.pub")
    assert not official_distill_host("127.0.0.1")
    assert not official_distill_host("localhost")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    validate_catalog(document)
    document["entries"] = []
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    if document["entries"]:
        document["entries"][0]["rights"] = "cc-by-nc"
        with pytest.raises(CatalogError):
            validate_catalog(document)
        document = copy.deepcopy(load_catalog())
        document["entries"][0]["body"] = "full page"
        with pytest.raises(CatalogError, match="page text"):
            validate_catalog(document)
        document = copy.deepcopy(load_catalog())
        document["entries"][0]["probability"] = 0.2
        with pytest.raises(CatalogError, match="page text"):
            validate_catalog(document)
        document = copy.deepcopy(load_catalog())
        document["entries"][0]["explanation"] = "model prose"
        with pytest.raises(CatalogError, match="page text"):
            validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)
