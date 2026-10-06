"""Offline checks for the Data & Society AI page catalog. No network."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.datasociety as datasociety
from pdoom_pipeline.catalogs.datasociety import (
    PUBLISHER,
    RIGHTS_APACHE,
    RIGHTS_CC_ATTRIBUTION,
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
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    date_from_page,
    is_challenge_page,
    load_catalog,
    official_datasociety_host,
    page_record,
    record_from_response,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
    validate_entry,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_URL = "https://datasociety.net/research-library/algorithmic-accountability-a-primer/"
REQUIRED_URLS = (
    "https://datasociety.net/ai-civics/",
    "https://datasociety.net/ai-on-the-ground/",
    "https://datasociety.net/democracy-in-the-age-of-ai/",
    "https://datasociety.net/worker-lens-on-the-ai-economy/",
    "https://datasociety.net/participation-agency-and-algorithmic-accountability/",
    SAMPLE_URL,
)
CHALLENGE_HTML = (
    "<html><head><title>Just a moment...</title></head>"
    "<body>cf-browser-verification challenge-platform</body></html>"
)
SITEGROUND_HTML = (
    "<html><head><title>Please wait while your request is being verified...</title></head>"
    "<body>sg-captcha</body></html>"
)
AKAMAI_HTML = (
    "<html><head><title>Access Denied</title></head>"
    "<body>errors.edgesuite.net akamai-ghost</body></html>"
)


def _page(body: str, *, title: str = "AI accountability primer", url: str = SAMPLE_URL) -> str:
    return f"""
    <html><head>
    <title>{title} - Data &amp; Society</title>
    <meta property="og:title" content="{title} - Data &amp; Society" />
    <meta property="og:site_name" content="Data &amp; Society" />
    <meta name="citation_publisher" content="Data &amp; Society" />
    <link rel="canonical" href="{url}" />
    </head>
    <body>
    <h1>{title}</h1>
    {body}
    </body></html>
    """


def test_sole_restricted_deeds_keep_their_own_tokens():
    notices = (
        ("<p>Licensed under CC BY-NC 4.0.</p>", RIGHTS_CC_BY_NC),
        ("<p>Licensed under CC BY-ND 4.0.</p>", RIGHTS_CC_BY_ND),
        ("<p>Licensed under CC BY-NC-SA 4.0.</p>", RIGHTS_CC_BY_NC_SA),
        ("<p>Licensed under CC BY-NC-ND 4.0.</p>", RIGHTS_CC_BY_NC_ND),
        ('<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>', RIGHTS_CC_BY_NC),
        ('<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-ND</a>', RIGHTS_CC_BY_ND),
        (
            '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA</a>',
            RIGHTS_CC_BY_NC_SA,
        ),
        (
            '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY-NC-ND</a>',
            RIGHTS_CC_BY_NC_ND,
        ),
        (
            "<p>Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license.</p>",
            RIGHTS_CC_BY_NC_SA,
        ),
        ("<p>Creative Commons Attribution-NoDerivatives 4.0.</p>", RIGHTS_CC_BY_ND),
    )
    for notice, expected in notices:
        assert rights_from_page(notice) == expected
        assert rights_from_page(notice) != RIGHTS_CREATIVE_COMMONS
        assert rights_from_page(notice) != RIGHTS_CC_ATTRIBUTION
        assert "-" not in expected


def test_cc_by_alone_is_creative_commons_attribution():
    assert rights_from_page("<p>CC BY</p>") == RIGHTS_CC_ATTRIBUTION
    assert rights_from_page("<p>CC BY 4.0</p>") == RIGHTS_CC_ATTRIBUTION
    page = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
    assert rights_from_page(page) == RIGHTS_CC_ATTRIBUTION
    attribution = "<p>Licensed under a Creative Commons Attribution 4.0 International License.</p>"
    assert rights_from_page(attribution) == RIGHTS_CC_ATTRIBUTION
    assert rights_from_page("<p>Licensed under CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>This work is licensed under CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    mixed = "<p>Licensed under CC0 and CC BY-SA 4.0.</p>"
    assert rights_from_page(mixed) == RIGHTS_CREATIVE_COMMONS
    by_and_zero = "<p>Licensed under CC BY 4.0 and CC0.</p>"
    assert rights_from_page(by_and_zero) == RIGHTS_UNKNOWN


def test_a_generic_licenses_url_is_not_a_deed():
    texts = ("CC BY", "CC BY 4.0", "CC BY-SA")
    hrefs = (
        "https://creativecommons.org/licenses/",
        "https://creativecommons.org/licenses",
        "http://creativecommons.org/licenses/",
        "http://creativecommons.org/licenses",
        "https://www.creativecommons.org/licenses/",
        "http://www.creativecommons.org/licenses/",
        "https://creativecommons.org/licenses/?lang=en",
        "https://creativecommons.org/licenses?lang=en",
    )
    for href in hrefs:
        for text in texts:
            page = f'<a href="{href}">{text}</a>'
            assert rights_from_page(page) == RIGHTS_UNKNOWN
    specific = '<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA</a>'
    assert rights_from_page(specific) == RIGHTS_CREATIVE_COMMONS


def test_anchor_text_on_a_public_domain_mark_stays_unknown():
    by_mark = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC BY</a>'
    zero_mark = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC0</a>'
    assert rights_from_page(by_mark) == RIGHTS_UNKNOWN
    assert rights_from_page(zero_mark) == RIGHTS_UNKNOWN
    words = "<p>This work is identified with the Public Domain Mark.</p>"
    assert rights_from_page(words) == RIGHTS_UNKNOWN
    zero = '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
    assert rights_from_page(zero) == RIGHTS_CREATIVE_COMMONS


def test_anchor_text_cc_by_on_a_by_nc_url_stays_unknown():
    page = '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>'
    assert rights_from_page(page) == RIGHTS_UNKNOWN
    named = '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en">CC BY</a>'
    assert rights_from_page(named) == RIGHTS_UNKNOWN


def test_mixed_permissive_and_restricted_stays_unknown():
    mixed = "<p>Licensed under CC BY 4.0 and also under CC BY-NC 4.0.</p>"
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN
    beside = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-ND</a>'
    )
    assert rights_from_page(beside) == RIGHTS_UNKNOWN
    share = "<p>CC BY-SA together with CC BY-NC-SA.</p>"
    assert rights_from_page(share) == RIGHTS_UNKNOWN
    two_restricted = "<p>Licensed under CC BY-NC 4.0 and CC BY-ND 4.0.</p>"
    assert rights_from_page(two_restricted) == RIGHTS_UNKNOWN


def test_software_licences_and_credits():
    assert rights_from_page("<p>MIT License</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Apache License, Version 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Mozilla Public License 2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MIT</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and CC BY 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache License, Version 2.0 and CC BY-NC-SA 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and Apache License, Version 2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Photo credit: Ada Lovelace / CC BY 4.0</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Image credit: diagram, CC0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<figcaption>Caption credit: CC BY-SA 4.0.</figcaption>") == RIGHTS_UNKNOWN
    page_licence = (
        "<p>Image credit: Jane Doe, CC BY 4.0.</p>"
        "<p>Unless otherwise noted, this site and its contents are licensed under a "
        "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license.</p>"
    )
    assert rights_from_page(page_licence) == RIGHTS_CC_BY_NC_SA
    caption = (
        '<p class="wp-caption-text">Jamillah Knowles / '
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a></p>'
        "<p>Licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license.</p>"
    )
    assert rights_from_page(caption) == RIGHTS_CC_BY_NC_SA
    assert rights_from_page(
        '<p class="wp-caption-text">https://creativecommons.org/licenses/by/4.0/</p>'
    ) == RIGHTS_UNKNOWN
    illustration = (
        "<p><i>Illustration: Jamillah Knowles / https://creativecommons.org/licenses/by/4.0/</i></p>"
        "<p>Licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license.</p>"
    )
    assert rights_from_page(illustration) == RIGHTS_CC_BY_NC_SA
    header_image = (
        '<h6>Header image: <a href="https://creativecommons.org/licenses/by-nc/2.0/">CC BY 2.0</a>-licensed photo</h6>'
        "<p>Licensed under CC BY-NC-SA 4.0.</p>"
    )
    assert rights_from_page(header_image) == RIGHTS_CC_BY_NC_SA
    image_from = (
        '<p><a href="https://creativecommons.org/publicdomain/zero/1.0/deed.en">CC0</a> image from Pixabay.</p>'
        "<p>Licensed under CC BY-NC-SA 4.0.</p>"
    )
    assert rights_from_page(image_from) == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>Illustration: Ada Lovelace / CC BY 4.0</p>") == RIGHTS_UNKNOWN
    image_line = (
        "<p><i>Image: Jamillah Knowles / https://creativecommons.org/licenses/by/4.0/</i></p>"
        "<p>Licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license.</p>"
    )
    assert rights_from_page(image_line) == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>Image: Ada Lovelace / CC BY 4.0</p>") == RIGHTS_UNKNOWN
    illustration_by = (
        "<p><em>Illustration by Jamillah Knowles, edited from the original. "
        "https://creativecommons.org/licenses/by/4.0/</em></p>"
        "<p>Licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license.</p>"
    )
    assert rights_from_page(illustration_by) == RIGHTS_CC_BY_NC_SA


def test_public_pages_copyright_and_terms_are_not_licences():
    public = "<p>This page is public.</p>"
    reserved = "<p>Copyright 2024. All rights reserved.</p>"
    terms = '<p>See the <a href="https://datasociety.net/privacy-policy/">terms</a>.</p>'
    american = "<p>Licensed under the Open Government License v3.0.</p>"
    hidden = (
        "<script>var license = 'https://creativecommons.org/licenses/by/4.0/';</script>"
        "<style>CC BY-SA 4.0</style>"
        "<!-- MIT License -->"
        "<p>All rights reserved.</p>"
    )
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    assert rights_from_page(american) == RIGHTS_UNKNOWN
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN
    ogl = "<p>This publication is licensed under the Open Government Licence v3.0.</p>"
    assert rights_from_page(ogl) == RIGHTS_UK_OGL
    body_gov = "<p>This essay discusses a work of the United States Government.</p>"
    assert rights_from_page(body_gov) == RIGHTS_UNKNOWN
    field = '<meta name="dc.rights" content="This is a work of the United States Government." />'
    assert rights_from_page(field) == RIGHTS_US_GOVERNMENT_WORK
    negated = '<meta name="dc.rights" content="This is not a work of the United States Government." />'
    assert rights_from_page(negated) == RIGHTS_UNKNOWN


def test_a_challenge_or_non_html_response_is_not_stored():
    assert is_challenge_page(CHALLENGE_HTML)
    assert is_challenge_page(SITEGROUND_HTML)
    assert is_challenge_page(AKAMAI_HTML)
    cases = (
        (202, "text/html; charset=UTF-8", _page("<p>AI page</p>"), SAMPLE_URL, None),
        (403, "text/html", CHALLENGE_HTML, SAMPLE_URL, {"cf-mitigated": "challenge"}),
        (200, "text/html", CHALLENGE_HTML, SAMPLE_URL, None),
        (200, "text/html", SITEGROUND_HTML, SAMPLE_URL, None),
        (200, "text/html", AKAMAI_HTML, SAMPLE_URL, None),
        (200, "application/pdf", "%PDF-1.7", SAMPLE_URL, None),
        (200, "text/plain", "not html", SAMPLE_URL, None),
        (200, "application/json", '{"title":"AI"}', SAMPLE_URL, None),
        (200, "text/html", _page("<p>AI page</p>"), "https://example.com/ai", None),
        (
            200,
            "text/html",
            _page("<p>AI page</p>"),
            SAMPLE_URL,
            {"CF-Mitigated": "challenge"},
        ),
    )
    for status, content_type, body, url, headers in cases:
        assert (
            record_from_response(
                status=status,
                content_type=content_type,
                page_html=body,
                page_url=url,
                headers=headers,
            )
            is None
        )
    with pytest.raises(CatalogError, match="challenge page is not stored"):
        page_record(CHALLENGE_HTML, page_url=SAMPLE_URL)


def test_updated_modified_and_copyright_years_are_not_publication_dates():
    assert date_from_page("<p>No date. Copyright 2026. Updated 2024-06-01. Modified 2025-01-02.</p>") == UNKNOWN_DATE
    modified = (
        '<meta property="article:modified_time" content="2026-09-18T14:27:51+00:00" />'
        '<meta property="og:updated_time" content="2026-09-18T14:27:51+00:00" />'
        '<script type="application/ld+json">{"dateModified":"2026-09-18T14:27:51+00:00"}</script>'
    )
    assert date_from_page(modified) == UNKNOWN_DATE
    published = (
        modified
        + '<script type="application/ld+json">{"datePublished":"2018-04-18T04:01:26+00:00"}</script>'
    )
    assert date_from_page(published) == "2018-04-18"
    assert date_from_page('<meta name="citation_date" content="2018/04/18" />') == "2018-04-18"
    assert date_from_page('<meta property="article:published_time" content="2020-06-02T00:00:00+00:00" />') == "2020-06-02"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("18 April 2018")
    with pytest.raises(CatalogError):
        validate_date("2018-02-31")


def test_page_record_keeps_metadata_and_not_the_body_or_a_probability():
    abstract = "Algorithmic accountability examines harm. " * 12
    page = _page(
        "<p>p(doom) = 0.13.</p>"
        f"<meta name=\"citation_abstract\" content=\"{abstract}\" />"
        "<p>chart data 1,2,3,4</p>"
        "<footer>© 2026 Data &amp; Society. All rights reserved. "
        "Unless otherwise noted, this site and its contents are licensed under a "
        "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license.</footer>"
        '<script type="application/ld+json">{"datePublished":"2018-04-18T04:01:26+00:00","dateModified":"2026-09-18"}</script>'
    )
    record = page_record(page, page_url=SAMPLE_URL)
    assert record == {
        "title": "AI accountability primer",
        "publisher": PUBLISHER,
        "canonical_url": SAMPLE_URL,
        "date": "2018-04-18",
        "rights": RIGHTS_CC_BY_NC_SA,
    }
    stored = json.dumps(record)
    assert "p(doom)" not in stored.casefold()
    assert "0.13" not in stored
    assert "chart data" not in stored
    assert abstract not in stored
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}


def test_catalog_load_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    tree = ast.parse(inspect.getsource(datasociety))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in {"requests", "httpx", "urllib"}
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("urllib")
            assert module not in {"requests", "httpx"}
            assert not module.startswith("pdoom_pipeline.fetch")
            assert not module.startswith("pdoom_pipeline.belief")
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/catalogs/__init__.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "datasociety" not in source
    init = (ROOT / "pipeline/pdoom_pipeline/catalogs/__init__.py").read_text(encoding="utf-8")
    assert init.strip() == '"""Package marker."""'


def test_catalog_file_stores_no_body_or_probability_and_runner_wired_is_false():
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<p>" not in raw
    assert "<html" not in raw.casefold()
    assert "doctype" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert "p(doom)" not in raw.casefold()
    assert '"probability"' not in raw
    assert '"pdoom"' not in raw
    assert '"p_doom"' not in raw
    document = json.loads(raw)
    assert document["catalog_id"] == "datasociety_pages"
    assert document["runner_wired"] is False
    assert "datasociety.net" in document["description"]
    urls = []
    for entry in document["entries"]:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["publisher"] == PUBLISHER
        assert entry["rights"] == RIGHTS_CC_BY_NC_SA
        assert entry["date"] == UNKNOWN_DATE or len(entry["date"]) == 10
        assert official_datasociety_host(entry["canonical_url"].split("/")[2])
        assert not entry["canonical_url"].lower().endswith(".pdf")
        urls.append(entry["canonical_url"])
    for url in REQUIRED_URLS:
        assert url in urls
    assert len(urls) == 192
    assert document["description"].count("cc_by_nc_sa") == 1
    assert "creative_commons_attribution" in document["description"]
    assert "Just a moment" not in raw
    validate_catalog(document)


def test_non_datasociety_urls_are_rejected():
    rejected = (
        "http://datasociety.net/ai-civics/",
        "https://www.datasociety.net/ai-civics/",
        "https://datasociety.net.example/ai-civics/",
        "https://example.com/ai-civics/",
        "https://datasociety.net/ai-civics/?subject=ai",
        "https://datasociety.net/ai-civics/#section",
        "https://datasociety.net/wp-content/uploads/report.pdf",
        "https://datasociety.net/es/ai-civics/",
        "https://127.0.0.1/ai-civics/",
        "https://datasociety.net/",
        "https://user:pass@datasociety.net/ai-civics/",
    )
    for url in rejected:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    assert validate_canonical_url(SAMPLE_URL) == SAMPLE_URL
    assert official_datasociety_host("datasociety.net")
    assert not official_datasociety_host("www.datasociety.net")
    assert not official_datasociety_host("127.0.0.1")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner(tmp_path: Path):
    document = copy.deepcopy(load_catalog())
    if not document["entries"]:
        document["entries"] = [
            {
                "title": "AI accountability primer",
                "publisher": PUBLISHER,
                "canonical_url": SAMPLE_URL,
                "date": "2018-04-18",
                "rights": RIGHTS_UNKNOWN,
            }
        ]
    validate_catalog(document)

    wired = copy.deepcopy(document)
    wired["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(wired)

    body = copy.deepcopy(document)
    body["entries"][0]["body"] = "full page"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(body)

    probability = copy.deepcopy(document)
    probability["entries"][0]["probability"] = 0.5
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(probability)

    pdf = copy.deepcopy(document)
    pdf["entries"][0]["pdf"] = "https://datasociety.net/wp-content/uploads/report.pdf"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(pdf)

    quote = copy.deepcopy(document)
    quote["entries"][0]["quote"] = "a sourced sentence"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(quote)

    bad_rights = copy.deepcopy(document)
    bad_rights["entries"][0]["rights"] = "cc-by-nc"
    with pytest.raises(CatalogError):
        validate_catalog(bad_rights)

    creative = copy.deepcopy(document)
    creative["entries"][0]["rights"] = RIGHTS_CREATIVE_COMMONS
    validate_catalog(creative)
    attribution = copy.deepcopy(document)
    attribution["entries"][0]["rights"] = RIGHTS_CC_ATTRIBUTION
    validate_catalog(attribution)
    noncommercial = copy.deepcopy(document)
    noncommercial["entries"][0]["rights"] = RIGHTS_CC_BY_NC_SA
    validate_catalog(noncommercial)
    apache = copy.deepcopy(document)
    apache["entries"][0]["rights"] = RIGHTS_APACHE
    validate_catalog(apache)
    government = copy.deepcopy(document)
    government["entries"][0]["rights"] = RIGHTS_US_GOVERNMENT_WORK
    validate_catalog(government)
    ogl = copy.deepcopy(document)
    ogl["entries"][0]["rights"] = RIGHTS_UK_OGL
    validate_catalog(ogl)

    duplicate = copy.deepcopy(document)
    duplicate["entries"].append(dict(duplicate["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(duplicate)

    missing = dict(document["entries"][0])
    del missing["publisher"]
    with pytest.raises(CatalogError):
        validate_entry(missing)

    target = tmp_path / "datasociety_pages.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    loaded = load_catalog(target)
    assert loaded["runner_wired"] is False
