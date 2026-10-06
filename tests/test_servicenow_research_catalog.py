"""Offline checks for the ServiceNow Research page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import re
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.servicenow_research as servicenow_research
from pdoom_pipeline.catalogs.servicenow_research import (
    CATALOG_DESCRIPTION,
    CATALOG_ID,
    FETCH_MAX_BYTES,
    FETCH_MAX_REDIRECTS,
    FETCH_TIMEOUT_SECONDS,
    OFFICIAL_HOST,
    PUBLISHER,
    RIGHTS_APACHE,
    RIGHTS_CC_BY_NC,
    RIGHTS_CC_BY_NC_ND,
    RIGHTS_CC_BY_NC_SA,
    RIGHTS_CC_BY_ND,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
    RIGHTS_LABELS,
    RIGHTS_MIT,
    RIGHTS_MPL,
    RIGHTS_UK_OGL,
    RIGHTS_UNKNOWN,
    RIGHTS_US_GOVERNMENT_WORK,
    RUNNER_WIRED,
    SKIPPED_CHALLENGE_PATHS,
    UNKNOWN_DATE,
    WWW_HOST,
    CatalogError,
    catalog_path,
    confirmed_fetch_url,
    is_challenge_page,
    load_catalog,
    official_servicenow_research_host,
    page_record,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    robots_allows,
    title_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

SAMPLE_URL = "https://www.servicenow.com/research/publication/rafael-pardinas-pipe-tmlr2026.html"
RESEARCH_URL = "https://research.servicenow.com/"
BODY = (
    "This paragraph is the page body. It is not catalog metadata and must not be stored. "
    "The abstract discusses a model and must stay out of the row."
)
REJECTED_URLS = [
    "http://research.servicenow.com/",
    "http://www.servicenow.com/research/",
    "https://servicenow.com/research/",
    "https://community.servicenow.com/research/",
    "https://developer.servicenow.com/research/",
    "https://www.servicenow.com/",
    "https://www.servicenow.com/products/artificial-intelligence.html",
    "https://www.servicenow.com/company.html",
    "https://www.servicenow.com/now-platform.html",
    "https://www.servicenow.com/login",
    "https://www.servicenow.com/research/login",
    "https://research.servicenow.com/products/ai.html",
    "https://research.servicenow.com/login",
    "https://www.servicenow.com/research/?utm_source=x",
    "https://www.servicenow.com/research/#publications",
    "https://user:pass@www.servicenow.com/research/",
    "https://www.servicenow.com:443/research/",
    "https://www.servicenow.com/research/publication/paper.pdf",
    "https://127.0.0.1/research/",
    "https://169.254.169.254/latest/meta-data/",
    "https://www.servicenow.com/research/../products/ai.html",
    "https://not-servicenow.com/research/",
]
CLOUDFLARE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing www.servicenow.com. "
    "cf-mitigated: challenge challenge-platform</body></html>"
)
AKAMAI_HTML = (
    "<HTML><HEAD><TITLE>Access Denied</TITLE></HEAD><BODY><H1>Access Denied</H1>"
    "<P>https://errors.edgesuite.net/18.example</P></BODY></HTML>"
)


def _page(
    title: str,
    canonical: str,
    *,
    heading: str | None = None,
    published: str | None = None,
    updated: str | None = None,
    body: str | None = None,
) -> str:
    published_tag = (
        f'<meta property="article:published_time" content="{published}">' if published else ""
    )
    updated_tag = f'<meta property="article:modified_time" content="{updated}">' if updated else ""
    shown = heading if heading is not None else title
    return (
        "<html><head>"
        f"<title>{title}</title>"
        f'<meta property="og:site_name" content="ServiceNow AI Research">'
        f"{published_tag}{updated_tag}"
        f'<link rel="canonical" href="{canonical}">'
        "</head><body>"
        f"<h1>{shown}</h1>"
        f"<p>{body if body is not None else BODY}</p>"
        "<footer>ServiceNow Research</footer>"
        "</body></html>"
    )


def test_catalog_load_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("catalog load must not use the network")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    document = load_catalog()
    assert document["catalog_id"] == CATALOG_ID
    assert document["runner_wired"] is False
    assert document["entries"] == []


def test_committed_catalog_is_empty_because_challenge_paths_were_not_stored():
    document = load_catalog()
    assert catalog_path().name == "servicenow_research_pages.json"
    assert document["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert document["description"] == CATALOG_DESCRIPTION
    assert len(document["description"]) <= 800
    description = document["description"]
    assert OFFICIAL_HOST in description
    assert WWW_HOST in description
    assert "Akamai 403" in description
    assert "creative_commons_attribution" in description
    assert "creative_commons" in description
    assert "runner_wired is false" in description
    assert "belief collector" in description
    assert "empty" in description
    assert FETCH_TIMEOUT_SECONDS == 12
    assert FETCH_MAX_REDIRECTS == 3
    assert FETCH_MAX_BYTES == 400_000
    assert SKIPPED_CHALLENGE_PATHS == (
        "https://www.servicenow.com/robots.txt",
        "https://www.servicenow.com/sitemap.xml",
        "https://www.servicenow.com/research/",
        "https://www.servicenow.com/research/sitemap.xml",
        "https://www.servicenow.com/research/publications/",
        "https://www.servicenow.com/research/publication/rafael-pardinas-pipe-tmlr2026.html",
    )
    raw = catalog_path().read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert set(parsed) == {"catalog_id", "description", "runner_wired", "entries"}
    assert parsed["entries"] == []
    assert BODY not in raw
    assert "<html" not in raw
    assert ".pdf" not in raw
    rights_counts = {label: 0 for label in sorted(RIGHTS_LABELS)}
    assert sum(rights_counts.values()) == 0
    assert rights_counts[RIGHTS_UNKNOWN] == 0


def test_sole_restricted_deeds_keep_underscore_tokens():
    assert rights_from_page("<p>CC BY-NC</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>cc-by-nc</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY-ND</p>") == RIGHTS_CC_BY_ND
    assert rights_from_page("<p>CC BY-NC-ND</p>") == RIGHTS_CC_BY_NC_ND
    assert rights_from_page("<p>CC BY-NC-SA</p>") == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>CC BY</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>CC BY-NC</p>") != RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert "cc-by-nc" not in RIGHTS_LABELS
    source = Path(servicenow_research.__file__).read_text(encoding="utf-8")
    assert "(?!-)" in source


def test_permissive_deeds_and_mixed_text():
    assert rights_from_page("<p>This work is licensed under CC BY 4.0.</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>Creative Commons Attribution 4.0</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>This work is licensed under CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>This work is licensed under CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC0 and CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY 4.0 and CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY and CC BY-SA.</p>") == RIGHTS_CREATIVE_COMMONS
    mixed = "<p>This work is CC BY 4.0 and also CC BY-NC.</p>"
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN
    both_urls = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>'
    )
    assert rights_from_page(both_urls) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY-NC and CC BY-ND.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY-NC-SA and CC BY-NC-ND.</p>") == RIGHTS_UNKNOWN


def test_generic_license_url_anchor_text_is_not_a_licence():
    for anchor in ("CC BY", "CC BY 4.0", "CC BY-SA", "Creative Commons Attribution 4.0"):
        for href in (
            "https://creativecommons.org/licenses/",
            "https://creativecommons.org/licenses",
            "https://www.creativecommons.org/licenses/",
            "http://creativecommons.org/licenses/",
            "https://creativecommons.org/licenses/?lang=en",
            "http://www.creativecommons.org/licenses?lang=en",
        ):
            page = f'<a href="{href}">{anchor}</a>'
            assert rights_from_page(page) == RIGHTS_UNKNOWN
    specific = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
    assert rights_from_page(specific) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    deed_only = '<a href="https://creativecommons.org/licenses/by/4.0/">read the deed</a>'
    assert rights_from_page(deed_only) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    share_alike = '<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA</a>'
    assert rights_from_page(share_alike) == RIGHTS_CREATIVE_COMMONS
    generic_plus_restricted = (
        '<a href="https://creativecommons.org/licenses/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>'
    )
    assert rights_from_page(generic_plus_restricted) == RIGHTS_CC_BY_NC
    outside = (
        '<p>Licensed under CC BY 4.0.</p>'
        '<a href="https://creativecommons.org/licenses/">CC BY-SA</a>'
    )
    assert rights_from_page(outside) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_misleading_anchors_and_non_licences_stay_unknown():
    cases = [
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-SA</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC BY</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC BY-SA</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC0</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>',
        "<footer>© 2026 ServiceNow. All rights reserved.</footer>",
        "<p>See the terms. Hosted at servicenow.com.</p>",
        '<a href="https://www.servicenow.com/">ServiceNow</a>',
    ]
    for html in cases:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<link rel="license" href="https://creativecommons.org/licenses/by-nc-nd/4.0/">') == RIGHTS_CC_BY_NC_ND


def test_photo_caption_and_image_credits_do_not_count():
    sentence = "<p>Photo credit: UNDRR, CC BY-NC-ND 2.0.</p>"
    assert rights_from_page(sentence) == RIGHTS_UNKNOWN
    linked = (
        "<p>Photo credit: UNDRR ("
        '<a href="https://creativecommons.org/licenses/by-nc-nd/2.0/">CC BY-NC-ND 2.0</a>).</p>'
    )
    assert rights_from_page(linked) == RIGHTS_UNKNOWN
    assert rights_from_page("<figcaption>Caption credit: CC BY-SA 4.0.</figcaption>") == RIGHTS_UNKNOWN
    assert rights_from_page(
        '<p>Image credit: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a></p>'
    ) == RIGHTS_UNKNOWN
    separate = sentence + "<p>Licensed under CC BY 4.0.</p>"
    assert rights_from_page(separate) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_software_licences_ogl_and_us_government_work():
    assert rights_from_page("<p>MIT License</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Apache License, Version 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache License 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Mozilla Public License 2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MPL-2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>Apache License</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>A collaboration with MIT and NYU.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and Apache-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and MPL-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and CC BY-SA 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and CC BY-NC.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MPL-2.0 and CC0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Open Government Licence v3.0</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>open government licence</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>Licensed under the Open Government License v3.0.</p>") == RIGHTS_UNKNOWN
    archives = '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">terms</a>'
    assert rights_from_page(archives) == RIGHTS_UNKNOWN
    rights_field = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(rights_field) == RIGHTS_US_GOVERNMENT_WORK
    named = '<meta name="rights" content="United States Government work">'
    assert rights_from_page(named) == RIGHTS_US_GOVERNMENT_WORK
    assert rights_from_page("<p>This is a work of the United States Government.</p>") == RIGHTS_UNKNOWN
    licence_field = '<meta name="license" content="This is a work of the United States Government.">'
    assert rights_from_page(licence_field) == RIGHTS_UNKNOWN
    negated = '<meta name="rights" content="This is not a work of the United States Government.">'
    assert rights_from_page(negated) == RIGHTS_UNKNOWN
    mixed_gov = rights_field + "<p>CC BY 4.0</p>"
    assert rights_from_page(mixed_gov) == RIGHTS_UNKNOWN


def test_script_style_and_comments_do_not_count():
    hidden = [
        "<script>Licensed under CC BY 4.0.</script><p>All rights reserved.</p>",
        "<style>.x{content:'CC BY 4.0'}</style><p>All rights reserved.</p>",
        "<!-- Licensed under CC BY 4.0 --><p>All rights reserved.</p>",
        '<script type="application/ld+json">{"license":"https://creativecommons.org/licenses/by/4.0/"}</script>'
        "<p>All rights reserved.</p>",
        "<script>Open Government Licence v3.0</script><p>All rights reserved.</p>",
        '<script type="application/ld+json">{"rights":"This is a work of the United States Government."}</script>'
        "<p>All rights reserved.</p>",
        "<!-- Photo credit: UNDRR, CC BY-NC-ND 2.0. --><p>Licensed under CC BY 4.0.</p>",
    ]
    for html in hidden[:-1]:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    assert rights_from_page(hidden[-1]) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    visible_link = '<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">'
    assert rights_from_page(visible_link) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_publication_dates_ignore_updated_modified_and_copyright_years():
    stated = (
        '<time datetime="2026-01-15T00:00:00Z">January 15, 2026</time>'
        '<meta property="article:modified_time" content="2026-10-01T00:00:00Z">'
        '<meta property="og:updated_time" content="2026-11-01T00:00:00Z">'
        "<p>© 2026 ServiceNow</p>"
    )
    assert publication_date_from_page(stated) == "2026-01-15"
    listing = (
        '<time datetime="2024-09-04">September 4, 2024</time>'
        '<time datetime="2025-07-03">July 3, 2025</time>'
        '<time datetime="2026-01-15">January 15, 2026</time>'
        '<meta property="article:published_time" content="2020-01-01T00:00:00Z">'
    )
    assert publication_date_from_page(listing) == UNKNOWN_DATE
    prose = "<p>January 2026. Updated 2024-05-01. © 2020</p>"
    assert publication_date_from_page(prose) == UNKNOWN_DATE
    updated = "<p>Last update: May 2026.</p><p>Updated 2024-05-01</p><p>© 2020</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    modified = '<meta property="article:modified_time" content="2024-04-18T14:43:38.000Z">'
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    meta_only = '<meta property="article:published_time" content="2026-01-15T00:00:00Z">'
    assert publication_date_from_page(meta_only) == "2026-01-15"
    script_date = '<script type="application/ld+json">{"datePublished":"2026-01-15"}</script><p>No date.</p>'
    assert publication_date_from_page(script_date) == UNKNOWN_DATE
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2026-01-15") == "2026-01-15"
    with pytest.raises(CatalogError, match="date"):
        validate_date("15 January 2026")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    record = page_record(
        _page("PipelineRL | ServiceNow AI Research", SAMPLE_URL, heading="PipelineRL"),
        page_url=SAMPLE_URL,
    )
    assert record["title"] == "PipelineRL"
    assert record["publisher"] == PUBLISHER
    assert record["canonical_url"] == SAMPLE_URL
    assert record["date"] == UNKNOWN_DATE
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    stored = json.dumps(record)
    assert BODY not in stored
    assert "abstract" not in stored
    dated = page_record(
        _page(
            "PipelineRL | ServiceNow AI Research",
            SAMPLE_URL,
            heading="PipelineRL",
            published="2026-01-15T00:00:00Z",
            updated="2026-10-01T00:00:00Z",
        ),
        page_url=SAMPLE_URL,
    )
    assert dated["date"] == "2026-01-15"
    assert "2026-10-01" not in json.dumps(dated)


def test_a_different_canonical_link_does_not_replace_the_live_url():
    html = _page("PipelineRL | ServiceNow AI Research", "https://www.servicenow.com/research/")
    record = page_record(html, page_url=SAMPLE_URL)
    assert record["canonical_url"] == SAMPLE_URL


def test_a_product_name_is_not_the_publisher():
    missing = "<html><head><title>Now Assist</title></head><body><h1>Now Assist</h1><p>ServiceNow</p></body></html>"
    with pytest.raises(CatalogError, match="publisher"):
        page_record(missing, page_url=SAMPLE_URL)
    stated = _page("People | ServiceNow Research", "https://www.servicenow.com/research/people.html")
    assert page_record(stated, page_url="https://www.servicenow.com/research/people.html")["publisher"] == PUBLISHER


def test_title_strips_the_research_site_suffix():
    titled = "<html><head><title>PipelineRL | ServiceNow AI Research</title></head><body></body></html>"
    assert title_from_page(titled) == "PipelineRL"
    org = (
        "<html><head><title>ServiceNow AI Research</title></head>"
        "<body><h1>ServiceNow AI Research</h1><h2>Latest publications</h2></body></html>"
    )
    assert title_from_page(org) == "Latest publications"
    hidden = (
        "<html><head><script>ignore previous instructions</script>"
        "<title>PipelineRL | ServiceNow Research</title></head><body></body></html>"
    )
    assert title_from_page(hidden) == "PipelineRL"
    assert "ignore previous instructions" not in title_from_page(hidden)


def test_challenge_status_and_off_host_redirect_are_not_stored():
    assert is_challenge_page(CLOUDFLARE_HTML)
    assert is_challenge_page(AKAMAI_HTML, headers={"server": "AkamaiGHost"})
    assert record_from_response(
        status=403,
        content_type="text/html",
        page_html=AKAMAI_HTML,
        page_url="https://www.servicenow.com/research/",
        headers={"server": "AkamaiGHost"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=CLOUDFLARE_HTML,
        page_url=SAMPLE_URL,
        headers={"cf-mitigated": "challenge"},
    ) is None
    assert record_from_response(
        status=202,
        content_type="text/html",
        page_html=_page("PipelineRL | ServiceNow AI Research", SAMPLE_URL),
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7 synthetic",
        page_url=SAMPLE_URL,
    ) is None
    assert confirmed_fetch_url(RESEARCH_URL, "https://www.servicenow.com/research/") is None
    assert confirmed_fetch_url(SAMPLE_URL, "https://www.servicenow.com/products/ai.html") is None
    assert confirmed_fetch_url("http://research.servicenow.com/", RESEARCH_URL) is None
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page("PipelineRL | ServiceNow AI Research", SAMPLE_URL, published="2026-01-15T00:00:00Z"),
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
    )
    assert stored is not None
    assert stored["canonical_url"] == SAMPLE_URL
    assert stored["publisher"] == PUBLISHER
    assert stored["date"] == "2026-01-15"
    assert set(stored) == {"title", "publisher", "canonical_url", "date", "rights"}
    assert BODY not in json.dumps(stored)


def test_www_is_stored_only_when_a_research_path_stays_on_www():
    html = _page("PipelineRL | ServiceNow AI Research", SAMPLE_URL)
    stayed = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
    )
    assert stayed is not None
    assert stayed["canonical_url"] == SAMPLE_URL
    redirected = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url=RESEARCH_URL,
        final_url="https://www.servicenow.com/research/",
    )
    assert redirected is None
    preferred = record_from_response(
        status=200,
        content_type="text/html",
        page_html=_page("ServiceNow AI Research", RESEARCH_URL, heading="Latest publications"),
        page_url=RESEARCH_URL,
        final_url=RESEARCH_URL,
    )
    assert preferred is not None
    assert preferred["canonical_url"] == RESEARCH_URL
    assert official_servicenow_research_host(OFFICIAL_HOST)
    assert official_servicenow_research_host(WWW_HOST)
    assert official_servicenow_research_host("servicenow.com") is False


def test_robots_challenge_does_not_allow_a_path():
    assert robots_allows(AKAMAI_HTML, "/research/") is False
    assert robots_allows(CLOUDFLARE_HTML, "/research/") is False
    assert robots_allows("", "/research/") is True
    blocked = "User-agent: *\nDisallow: /\n"
    html = _page("PipelineRL | ServiceNow AI Research", SAMPLE_URL)
    omitted = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
        robots_text=blocked,
    )
    assert omitted is None
    challenge = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
        robots_text=AKAMAI_HTML,
    )
    assert challenge is None


def test_non_research_urls_are_rejected():
    for rejected in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(rejected)


@pytest.mark.parametrize(
    "url",
    [
        "https://research.servicenow.com/",
        "https://research.servicenow.com/publication/example-note.html",
        "https://www.servicenow.com/research/",
        "https://www.servicenow.com/research/people.html",
        "https://www.servicenow.com/research/author/alexandre-drouin.html",
        "https://www.servicenow.com/research/publication/rafael-pardinas-pipe-tmlr2026.html",
    ],
)
def test_official_research_urls_are_accepted(url: str):
    assert validate_canonical_url(url) == url
    assert official_servicenow_research_host(url.split("/")[2])


def test_blocked_hostname_is_rejected(monkeypatch):
    monkeypatch.setattr(servicenow_research, "hostname_is_blocked", lambda _host: True)
    with pytest.raises(CatalogError):
        validate_canonical_url("https://research.servicenow.com/")
    assert official_servicenow_research_host("research.servicenow.com") is False


def test_validator_rejects_bad_rights_and_accepts_an_empty_list():
    document = copy.deepcopy(load_catalog())
    document["entries"] = []
    validate_catalog(document)

    extra = {
        "title": "PipelineRL",
        "publisher": PUBLISHER,
        "canonical_url": SAMPLE_URL,
        "date": "2026-01-15",
        "rights": RIGHTS_UNKNOWN,
    }
    document = copy.deepcopy(load_catalog())
    document["entries"] = [extra, dict(extra)]
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [dict(extra, rights="cc-by-nc")]
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [dict(extra, body=BODY)]
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"] = [dict(extra, abstract="a stored abstract")]
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"] = [dict(extra, quote="a stored quote")]
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"] = [dict(extra, pdf="a stored pdf")]
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    later = dict(extra, canonical_url="https://www.servicenow.com/research/people.html", date="2026-06-01")
    document["entries"] = [later, extra]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"] = [dict(extra, canonical_url="https://www.servicenow.com/products/ai.html")]
    with pytest.raises(CatalogError):
        validate_catalog(document)


def test_catalog_is_not_wired_into_belief_collection():
    module = Path(servicenow_research.__file__).read_text(encoding="utf-8")
    tree = ast.parse(module)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "pdoom_pipeline.belief.collect" not in imported
    assert not re.search(r"(?m)^\s*(?:import|from)\s+requests\b", module)
    assert "hostname_is_blocked" in module
    assert "runner_wired = True" not in module
    assert "RUNNER_WIRED = False" in module

    root = Path(__file__).resolve().parents[1]
    init = (root / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py").read_text(encoding="utf-8")
    assert init.strip() == '"""Package marker."""'
    assert "servicenow" not in init
    collectors = (root / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py").read_text(encoding="utf-8")
    assert collectors.strip() == '"""Package marker."""'
    assert "servicenow" not in collectors
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
        "pipeline/pdoom_pipeline/collectors/rss.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "servicenow_research" not in text
        assert "servicenow_research_pages" not in text
    collect = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in collect
