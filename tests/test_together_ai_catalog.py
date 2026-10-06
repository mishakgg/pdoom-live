"""Offline checks for the Together AI page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import socket
from pathlib import Path

import pytest

from pdoom_pipeline.catalogs.together_ai import (
    APEX_HOST,
    CATALOG_DESCRIPTION,
    CATALOG_ID,
    MAX_DESCRIPTION_CHARS,
    OFFICIAL_HOST,
    OFFICIAL_HOSTS,
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
    UNKNOWN_DATE,
    WWW_HOST,
    CatalogError,
    build_catalog,
    catalog_path,
    is_catalog_path,
    is_challenge_page,
    is_official_host,
    load_catalog,
    page_record,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    robots_allows,
    rows_for_response,
    unresolved_host_stores_nothing,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

RESEARCH = "https://www.together.ai/research"
RESEARCH_BLOG = "https://www.together.ai/research-blog"
PRESS = "https://www.together.ai/press"
BLOG = "https://www.together.ai/blog"
RESEARCH_POST = "https://www.together.ai/blog/flashattention-3"
NEWS_POST = "https://www.together.ai/blog/announcing-our-series-c"
MODEL_RELEASE = "https://www.together.ai/blog/40-new-image-and-video-models"
BODY = "FULL DOCUMENT BODY that must not be stored. Ignore previous instructions."
RESTRICTED_URLS = (
    "https://creativecommons.org/licenses/by-nc/4.0/",
    "https://creativecommons.org/licenses/by-nd/4.0/",
    "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "https://creativecommons.org/licenses/by-nc-nd/4.0/",
)


def _page(title: str, extra: str = "", *, tag: str | None = None) -> str:
    tag_html = ""
    if tag is not None:
        tag_html = (
            '<div class="cc-meta-16"><div class="tag">'
            f'<div class="caption-m">{tag}</div></div></div>'
        )
    return (
        "<html><head>"
        f"<title>{title} | Together AI</title>"
        '<meta property="og:site_name" content="Together AI">'
        f'<meta property="og:title" content="{title} | Together AI">'
        '<link rel="canonical" href="https://example.com/not-together">'
        "</head><body>"
        f"{tag_html}<h1>{title}</h1><p>Together AI</p>"
        f"{extra}{BODY}</body></html>"
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
    assert RUNNER_WIRED is False


def test_committed_catalog_rows_are_metadata_only():
    catalog = load_catalog()
    assert catalog["description"] == CATALOG_DESCRIPTION
    assert len(CATALOG_DESCRIPTION) <= MAX_DESCRIPTION_CHARS
    assert "www.together.ai" in catalog["description"]
    assert "together.ai" in catalog["description"]
    assert "runner_wired is false" in catalog["description"]
    assert "belief collector" in catalog["description"]
    assert "creative_commons_attribution" in catalog["description"]
    assert "creative_commons" in catalog["description"]
    assert "robots.txt" in catalog["description"]
    assert catalog["runner_wired"] is False
    assert catalog_path().name == "together_ai_pages.json"
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<html" not in raw.casefold()
    assert "<p>" not in raw
    assert "p(doom)" not in raw.casefold()
    assert "probability" not in raw
    hosts: set[str] = set()
    rights_counts: dict[str, int] = {}
    unknown_dates = 0
    urls: list[str] = []
    for entry in catalog["entries"]:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["publisher"] == PUBLISHER
        assert entry["rights"] in RIGHTS_LABELS
        validate_canonical_url(entry["canonical_url"])
        validate_date(entry["date"])
        host = entry["canonical_url"].split("/", 3)[2]
        hosts.add(host)
        assert is_official_host(host)
        assert "/models" not in entry["canonical_url"]
        assert "/sandbox" not in entry["canonical_url"]
        rights_counts[entry["rights"]] = rights_counts.get(entry["rights"], 0) + 1
        if entry["date"] == UNKNOWN_DATE:
            unknown_dates += 1
        urls.append(entry["canonical_url"])
        blob = json.dumps(entry)
        assert BODY not in blob
        assert ".pdf" not in entry["canonical_url"]
        assert "abstract" not in entry
        assert "quote" not in entry
        assert "transcript" not in entry
    assert urls == sorted(urls, key=lambda url: (catalog["entries"][urls.index(url)]["date"] == UNKNOWN_DATE, catalog["entries"][urls.index(url)]["date"] if catalog["entries"][urls.index(url)]["date"] != UNKNOWN_DATE else "", url))
    assert hosts <= OFFICIAL_HOSTS
    assert unknown_dates <= len(catalog["entries"])
    assert sum(rights_counts.values()) == len(catalog["entries"])
    by_url = {entry["canonical_url"]: entry for entry in catalog["entries"]}
    assert RESEARCH in by_url
    assert RESEARCH_BLOG in by_url
    assert PRESS in by_url
    assert BLOG in by_url
    assert RESEARCH_POST in by_url
    assert NEWS_POST in by_url
    assert MODEL_RELEASE in by_url
    assert by_url[RESEARCH]["publisher"] == PUBLISHER
    assert by_url[RESEARCH_POST]["rights"] in RIGHTS_LABELS
    assert hosts == {OFFICIAL_HOST}
    assert APEX_HOST not in hosts
    assert len(catalog["entries"]) == 165
    assert unknown_dates == 4
    assert rights_counts == {RIGHTS_UNKNOWN: 163, RIGHTS_MIT: 2}
    assert by_url[RESEARCH]["title"] == "Research"
    assert by_url[RESEARCH]["date"] == UNKNOWN_DATE
    assert by_url[RESEARCH_BLOG]["title"] == "Research Blog"
    assert by_url[PRESS]["title"] == "News & Press"
    assert by_url[BLOG]["title"] == "Blog"
    assert by_url[RESEARCH_POST]["date"] == "2024-07-11"
    assert by_url[RESEARCH_POST]["title"].startswith("FlashAttention-3:")
    assert by_url[NEWS_POST]["date"] == "2026-07-01"
    assert by_url[MODEL_RELEASE]["date"] == "2025-10-21"
    assert by_url[MODEL_RELEASE]["rights"] == RIGHTS_UNKNOWN
    guide = "https://www.together.ai/blog/how-to-choose-the-right-open-model-for-production"
    assert by_url[guide]["rights"] == RIGHTS_UNKNOWN
    assert by_url[guide]["date"] == "2026-01-08"


def test_official_hosts_and_public_paths_only():
    assert is_official_host(OFFICIAL_HOST)
    assert is_official_host(WWW_HOST)
    assert is_official_host(APEX_HOST)
    assert not is_official_host("docs.together.ai")
    assert not is_official_host("api.together.ai")
    assert not is_official_host("api.together.xyz")
    assert not is_official_host("example.com")
    assert not is_official_host("localhost")
    assert not is_official_host("127.0.0.1")
    assert OFFICIAL_HOSTS == frozenset({OFFICIAL_HOST, APEX_HOST})
    assert validate_canonical_url(RESEARCH) == RESEARCH
    assert validate_canonical_url(f"https://{APEX_HOST}/research") == f"https://{APEX_HOST}/research"
    assert validate_canonical_url(RESEARCH_BLOG) == RESEARCH_BLOG
    assert validate_canonical_url(PRESS) == PRESS
    assert validate_canonical_url(BLOG) == BLOG
    assert validate_canonical_url(RESEARCH_POST) == RESEARCH_POST
    assert validate_canonical_url(MODEL_RELEASE) == MODEL_RELEASE
    assert is_catalog_path("/research")
    assert is_catalog_path("/research-blog")
    assert is_catalog_path("/press")
    assert is_catalog_path("/blog")
    assert is_catalog_path("/blog/flashattention-3")
    assert not is_catalog_path("/models")
    assert not is_catalog_path("/models/afm-4-5b-preview")
    assert not is_catalog_path("/sandbox")
    assert not is_catalog_path("/login")
    assert not is_catalog_path("/pricing")
    assert not is_catalog_path("/blog/rss.xml")
    assert not is_catalog_path("/blog/paper.pdf")
    rejected = [
        "http://www.together.ai/research",
        "https://example.com/research",
        "https://docs.together.ai/docs",
        "https://api.together.ai/playground",
        "https://api.together.xyz/models",
        "https://www.together.ai/models",
        "https://www.together.ai/models/afm-4-5b-preview",
        "https://www.together.ai/sandbox",
        "https://www.together.ai/login",
        "https://www.together.ai/pricing",
        "https://www.together.ai/fine-tuning",
        "https://www.together.ai/blog/rss.xml",
        "https://user:pass@www.together.ai/research",
        "https://www.together.ai/research?utm_source=x",
        "https://www.together.ai/research#section",
        "https://www.together.ai:443/research",
        "https://www.together.ai/research/paper.pdf",
        "https://127.0.0.1/research",
        "https://www.together.ai/research/../secret",
        "https://WWW.TOGETHER.AI/research",
    ]
    for url in rejected:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)


def test_sole_restricted_deeds_keep_their_tokens():
    notices = {
        "<p>Licensed under CC BY-NC 4.0.</p>": RIGHTS_CC_BY_NC,
        "<p>cc-by-nc</p>": RIGHTS_CC_BY_NC,
        "<p>CC BY-ND</p>": RIGHTS_CC_BY_ND,
        "<p>CC BY-NC-SA</p>": RIGHTS_CC_BY_NC_SA,
        "<p>CC BY-NC-ND</p>": RIGHTS_CC_BY_NC_ND,
        "<p>Creative Commons Attribution-NonCommercial 4.0.</p>": RIGHTS_CC_BY_NC,
        "<p>Creative Commons Attribution-NoDerivatives 4.0.</p>": RIGHTS_CC_BY_ND,
        "<p>Creative Commons Attribution-NonCommercial-ShareAlike 4.0.</p>": RIGHTS_CC_BY_NC_SA,
        "<p>Creative Commons Attribution-NonCommercial-NoDerivatives 4.0.</p>": RIGHTS_CC_BY_NC_ND,
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>': RIGHTS_CC_BY_NC,
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">licence</a>': RIGHTS_CC_BY_ND,
        '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">licence</a>': RIGHTS_CC_BY_NC_SA,
        '<a href="https://creativecommons.org/licenses/by-nc-nd/2.0/">CC BY-NC-ND 2.0</a>': RIGHTS_CC_BY_NC_ND,
    }
    for page, expected in notices.items():
        assert rights_from_page(page) == expected
        assert rights_from_page(page) not in {
            RIGHTS_CREATIVE_COMMONS,
            RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
        }
        assert "-" not in rights_from_page(page)


def test_cc_by_alone_is_attribution_and_permissive_mixes_are_creative_commons():
    assert rights_from_page("<p>CC BY</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>CC-BY 4.0</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>Creative Commons Attribution 4.0.</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>') == (
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    )
    assert rights_from_page("<p>CC0</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY-SA 4.0</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC0 and CC BY-SA.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY and CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY and CC BY-SA.</p>") == RIGHTS_CREATIVE_COMMONS
    zero = '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
    assert rights_from_page(zero) == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY-NC</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY-NC</p><p>CC BY-NC 4.0</p>") == RIGHTS_CC_BY_NC


def test_deceptive_anchors_and_mixed_deeds_stay_unknown():
    for url in RESTRICTED_URLS:
        assert rights_from_page(f'<a href="{url}">CC BY</a>') == RIGHTS_UNKNOWN
        assert rights_from_page(f'<a href="{url}">CC BY-SA</a>') == RIGHTS_UNKNOWN
    mark = "https://creativecommons.org/publicdomain/mark/1.0/"
    assert rights_from_page(f'<a href="{mark}">CC0</a>') == RIGHTS_UNKNOWN
    assert rights_from_page(f'<a href="{mark}">CC BY</a>') == RIGHTS_UNKNOWN
    assert rights_from_page(f'<a href="{mark}">Public Domain Mark</a>') == RIGHTS_UNKNOWN
    swapped = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY-NC</a>'
    assert rights_from_page(swapped) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY</p><p>CC BY-NC</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC0</p><p>CC BY-NC-ND</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY-NC</p><p>CC BY-ND</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License</p><p>Licensed under CC BY 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0</p><p>CC BY-NC</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MPL-2.0 and CC0</p>") == RIGHTS_UNKNOWN


def test_generic_licence_url_anchor_text_and_photo_credits_stay_unknown():
    generic = (
        "https://creativecommons.org/licenses/",
        "https://creativecommons.org/licenses",
        "http://creativecommons.org/licenses/",
        "https://www.creativecommons.org/licenses/",
        "http://www.creativecommons.org/licenses",
        "https://creativecommons.org/licenses/?lang=en",
        "https://creativecommons.org/licenses?ref=footer",
        "http://www.creativecommons.org/licenses?lang=en",
    )
    for href in generic:
        assert rights_from_page(f'<a href="{href}">CC BY</a>') == RIGHTS_UNKNOWN
        assert rights_from_page(f'<a href="{href}">CC BY 4.0</a>') == RIGHTS_UNKNOWN
        assert rights_from_page(f'<a href="{href}">CC BY-SA</a>') == RIGHTS_UNKNOWN
    elsewhere = (
        '<a href="https://creativecommons.org/licenses/">CC BY</a>'
        "<p>Licensed under CC BY-SA 4.0.</p>"
    )
    assert rights_from_page(elsewhere) == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>') == (
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    )
    photo = "<p>Photo credit: UNDRR, CC BY-NC-ND 2.0.</p>"
    assert rights_from_page(photo) == RIGHTS_UNKNOWN
    short_photo = "<p>Photo: UNDRR, CC BY-NC-ND 2.0.</p>"
    assert rights_from_page(short_photo) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Photo: UNDRR, CC BY-NC-ND 2.0</p>") == RIGHTS_UNKNOWN
    linked = (
        "<p>Photo credit: UNDRR ("
        '<a href="https://creativecommons.org/licenses/by-nc-nd/2.0/">CC BY-NC-ND 2.0</a>).</p>'
    )
    assert rights_from_page(linked) == RIGHTS_UNKNOWN
    assert rights_from_page("<figcaption>Caption credit: CC BY-SA 4.0.</figcaption>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Image credit: Wikimedia Commons, CC BY-SA.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Caption credit: Alice, CC BY-NC.</p>") == RIGHTS_UNKNOWN
    separate = photo + "<p>Licensed under CC BY 4.0.</p>"
    assert rights_from_page(separate) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    short_separate = short_photo + "<p>CC BY</p>"
    assert rights_from_page(short_separate) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    same_paragraph = "<p>Licensed under CC BY 4.0. Photo credit: UNDRR, CC BY-NC-ND 2.0.</p>"
    assert rights_from_page(same_paragraph) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    same_short = "<p>Licensed under CC BY. Photo: UNDRR, CC BY-NC-ND 2.0.</p>"
    assert rights_from_page(same_short) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<style>CC BY 4.0</style><p>All rights reserved.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<script>Licensed under CC BY 4.0.</script><p>All rights reserved.</p>") == (
        RIGHTS_UNKNOWN
    )
    assert rights_from_page("<!-- Licensed under CC BY 4.0 --><p>No public licence.</p>") == RIGHTS_UNKNOWN
    hidden_credit = (
        "<script>Photo credit: UNDRR, CC BY-NC-ND 2.0.</script><p>Licensed under CC BY 4.0.</p>"
    )
    assert rights_from_page(hidden_credit) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    caption = (
        "<figure><figcaption>"
        '<a href="https://creativecommons.org/licenses/by-nc-nd/2.0/">CC BY-NC-ND 2.0</a>'
        "</figcaption></figure>"
    )
    assert rights_from_page(caption) == RIGHTS_UNKNOWN
    caption_and_page = caption + "<p>Licensed under CC BY 4.0.</p>"
    assert rights_from_page(caption_and_page) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_software_licences_ogl_and_us_government_work_stay_distinct():
    assert rights_from_page("<p>This work is licensed under the MIT License.</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Licensed under the MIT License.</p>") == RIGHTS_MIT
    assert rights_from_page("<p>MIT Licence</p>") == RIGHTS_MIT
    assert rights_from_page("<p>MIT</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Massachusetts Institute of Technology.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Released under a modified MIT license.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache License 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache License, Version 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>MPL-2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>Mozilla Public License 2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MIT License and Apache-2.0</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and MPL-2.0</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache License, Version 2.0 and CC BY 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>models with Apache-2.0 or MIT licenses.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT licenses</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Open Government Licence v3.0</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>Open Government License v3.0</p>") == RIGHTS_UNKNOWN
    archives = "<p>https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/</p>"
    assert rights_from_page(archives) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Open Government Licence</p><p>CC BY 4.0</p>") == RIGHTS_UNKNOWN
    hidden = "<script>open government licence</script><p>All rights reserved.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN
    prose = "<p>This is a work of the United States Government.</p>"
    assert rights_from_page(prose) == RIGHTS_UNKNOWN
    rights_field = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(rights_field) == RIGHTS_US_GOVERNMENT_WORK
    negated = '<meta name="rights" content="Not a work of the United States Government.">'
    assert rights_from_page(negated) == RIGHTS_UNKNOWN
    script_field = (
        '<script type="application/ld+json">'
        '{"rights":"This is a work of the United States Government."}'
        "</script>"
    )
    assert rights_from_page(script_field) == RIGHTS_US_GOVERNMENT_WORK
    script_prose = "<script>This is a work of the United States Government.</script>"
    assert rights_from_page(script_prose) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>All rights reserved.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>This page is public. See the terms.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Published on www.together.ai.</p>") == RIGHTS_UNKNOWN


def test_updated_modified_and_copyright_years_are_not_publication_dates():
    updated = "<!-- Last Published: Fri Oct 02 2026 00:27:10 GMT+0000 -->"
    updated += '<meta property="article:modified_time" content="2026-10-02T00:00:00+00:00">'
    updated += '<meta property="og:updated_time" content="2026-08-25T00:00:00+00:00">'
    updated += '<meta itemprop="dateModified" content="2026-07-01T00:00:00+00:00">'
    updated += "<p>Last updated: 2026-10-02</p><p>© 2026 Together AI</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    dated = updated + '<meta property="article:published_time" content="2024-06-13T00:00:00+00:00">'
    assert publication_date_from_page(dated) == "2024-06-13"
    itemprop = '<meta itemprop="datePublished" content="2026-04-30T08:41:08+0300">'
    assert publication_date_from_page(itemprop) == "2026-04-30"
    website = (
        '<script type="application/ld+json">'
        '{"@type":"WebSite","name":"Together AI","datePublished":"2020-01-01"}'
        "</script>"
    )
    assert publication_date_from_page(website) == UNKNOWN_DATE
    article = (
        '<script type="application/ld+json">'
        '{"@type":"BlogPosting","dateModified":"2026-01-01","datePublished":"2024-07-11"}'
        "</script>"
    )
    assert publication_date_from_page(article) == "2024-07-11"
    image = (
        '<script type="application/ld+json">'
        '{"@type":"ImageObject","datePublished":"2019-01-01"}'
        "</script>"
    )
    assert publication_date_from_page(image) == UNKNOWN_DATE
    modified_only = '<script type="application/ld+json">{"dateModified":"2024-06-13"}</script>'
    assert publication_date_from_page(modified_only) == UNKNOWN_DATE
    assert publication_date_from_page("<p>Published July 11, 2024</p><p>© 2020</p>") == "2024-07-11"
    assert publication_date_from_page("<p>Published 8/21/2026</p><p>© 2026</p>") == "2026-08-21"
    assert publication_date_from_page("<p>Last updated: 8/21/2026</p><p>© 2026</p>") == UNKNOWN_DATE
    assert publication_date_from_page("<p>Published 2/31/2026</p>") == UNKNOWN_DATE
    assert publication_date_from_page("<p>Published February 31, 2024</p>") == UNKNOWN_DATE
    broken_jsonld = (
        '<script type="application/ld+json">'
        '{"@type":"BlogPosting","description":"costs \\$3.99","datePublished":"2026-08-21"}'
        "</script>"
    )
    assert publication_date_from_page(broken_jsonld) == "2026-08-21"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2024-07-11") == "2024-07-11"
    with pytest.raises(CatalogError, match="date"):
        validate_date("July 11, 2024")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    record = page_record(
        _page(
            "Research",
            extra='<meta itemprop="datePublished" content="2022-06-02T14:31:06+0300">',
        ),
        page_url=RESEARCH,
    )
    assert record == {
        "title": "Research",
        "publisher": PUBLISHER,
        "canonical_url": RESEARCH,
        "date": "2022-06-02",
        "rights": RIGHTS_UNKNOWN,
    }
    stored = json.dumps(record)
    assert BODY not in stored
    assert "example.com" not in stored
    assert "abstract" not in record
    post = page_record(
        _page("FlashAttention-3", tag="Research"),
        page_url=RESEARCH_POST,
    )
    assert post["title"] == "FlashAttention-3"
    assert post["canonical_url"] == RESEARCH_POST
    assert post["publisher"] == PUBLISHER
    model = page_record(_page("Forty models", tag="Model Library"), page_url=MODEL_RELEASE)
    assert model["canonical_url"] == MODEL_RELEASE
    news = page_record(_page("Series C", tag="Company"), page_url=NEWS_POST)
    assert news["publisher"] == PUBLISHER
    with pytest.raises(CatalogError, match="model release"):
        page_record(_page("Inference update", tag="Inference"), page_url=RESEARCH_POST)
    with pytest.raises(CatalogError, match="model release"):
        page_record(_page("Kernels", tag="Kernels"), page_url=RESEARCH_POST)
    missing = (
        "<html><head><title>Ada Example</title>"
        '<meta property="og:site_name" content="Ada Example"></head>'
        f"<p>{BODY}</p></html>"
    )
    with pytest.raises(CatalogError, match="publisher"):
        page_record(missing, page_url=RESEARCH)


def test_a_blocked_fetch_stores_an_empty_catalog():
    cloudflare = (
        "<html><head><title>Just a moment...</title></head>"
        "<body>Performing security verification challenge-platform</body></html>"
    )
    captcha = "<html><head><title>News</title></head><body><div id='sg-captcha'>captcha</div></body></html>"
    login = (
        "<html><head><title>Login</title></head><body>"
        "<form><input type='password' name='pass'></form><p>Together AI</p></body></html>"
    )
    assert is_challenge_page(cloudflare)
    assert is_challenge_page(captcha)
    assert rows_for_response(
        status=200,
        content_type="text/html",
        page_html=cloudflare,
        page_url=RESEARCH,
        headers={"cf-mitigated": "challenge"},
    ) == []
    assert record_from_response(
        status=403,
        content_type="text/html",
        page_html=_page("Research"),
        page_url=RESEARCH,
    ) is None
    assert record_from_response(
        status=401,
        content_type="text/html",
        page_html=_page("Research"),
        page_url=RESEARCH,
        headers={"www-authenticate": "Bearer"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=login,
        page_url=RESEARCH,
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html=_page("Research"),
        page_url="https://www.together.ai/research/paper.pdf",
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=_page("Research"),
        page_url=RESEARCH,
        final_url="https://example.com/research",
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=_page("Models", tag="Model Library"),
        page_url="https://www.together.ai/models",
    ) is None
    robots = "User-agent: *\nAllow: /\n\nUser-agent: Google-Extended\nDisallow: /\n"
    assert robots_allows(robots, "/research") is True
    assert robots_allows(robots, "/blog/flashattention-3") is True
    assert robots_allows("User-agent: *\nDisallow: /blog\nAllow: /research\n", "/blog") is False
    html_robots = "<!DOCTYPE html><html><title>Robots</title><body>Not a robots file</body></html>"
    assert robots_allows(html_robots, "/research") is False
    assert robots_allows("<html><body>User-agent: *\nDisallow:</body></html>", "/research") is False
    challenge_robots = "<html><title>Just a moment...</title><p>challenge-platform</p></html>"
    assert robots_allows(challenge_robots, "/research") is False
    assert rows_for_response(
        status=200,
        content_type="text/html",
        page_html=_page("Research"),
        page_url=RESEARCH,
        robots_txt=html_robots,
    ) == []
    assert unresolved_host_stores_nothing([]) is True
    assert unresolved_host_stores_nothing(None) is True
    assert unresolved_host_stores_nothing(OSError("name does not resolve")) is True
    assert unresolved_host_stores_nothing(["203.0.113.10"]) is False
    stayed = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page("Research"),
        page_url=f"https://{APEX_HOST}/research",
        final_url=RESEARCH,
        robots_txt=robots,
    )
    assert stayed is not None
    assert stayed["canonical_url"] == RESEARCH
    assert "example.com" not in stayed["canonical_url"]
    empty = build_catalog([])
    assert empty["entries"] == []
    assert empty["runner_wired"] is False
    assert empty["catalog_id"] == CATALOG_ID


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = {
        "catalog_id": CATALOG_ID,
        "description": CATALOG_DESCRIPTION,
        "runner_wired": False,
        "entries": [],
    }
    assert validate_catalog(document)["entries"] == []
    wired = copy.deepcopy(document)
    wired["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(wired)
    entry = {
        "title": "Research",
        "publisher": PUBLISHER,
        "canonical_url": RESEARCH,
        "date": UNKNOWN_DATE,
        "rights": RIGHTS_UNKNOWN,
    }
    document["entries"] = [entry]
    validate_catalog(document)
    bad_rights = copy.deepcopy(document)
    bad_rights["entries"][0]["rights"] = "cc-by-nc"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(bad_rights)
    with_body = copy.deepcopy(document)
    with_body["entries"][0]["body"] = BODY
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(with_body)
    with_quote = copy.deepcopy(document)
    with_quote["entries"][0]["quote"] = BODY
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(with_quote)
    with_pdf = copy.deepcopy(document)
    with_pdf["entries"][0]["pdf"] = "not stored"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(with_pdf)
    other_publisher = copy.deepcopy(document)
    other_publisher["entries"][0]["publisher"] = "Ada Example"
    with pytest.raises(CatalogError, match="publisher"):
        validate_catalog(other_publisher)
    duplicate = copy.deepcopy(document)
    duplicate["entries"].append(dict(entry))
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        validate_catalog(duplicate)
    unordered = copy.deepcopy(document)
    unordered["entries"] = [
        {**entry, "canonical_url": "https://www.together.ai/blog/b", "date": "2024-02-01"},
        {**entry, "canonical_url": "https://www.together.ai/blog/a", "date": "2024-01-01"},
    ]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(unordered)


def test_catalog_module_is_not_wired_into_belief_collection():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "pipeline" / "pdoom_pipeline" / "catalogs" / "together_ai.py"
    module = module_path.read_text(encoding="utf-8")
    tree = ast.parse(module)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
    assert "httpx" not in imported
    assert "urllib.request" not in imported
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "pdoom_pipeline.belief.collect" not in imported
    assert "import requests" not in module
    assert "from requests" not in module
    assert "runner_wired = True" not in module
    assert "RUNNER_WIRED = False" in module
    assert RUNNER_WIRED is False
    beliefs = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in beliefs
    assert "from pdoom_pipeline.collectors.rss import RssCollector" in beliefs
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
        "pipeline/pdoom_pipeline/collectors/rss.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "together_ai_pages" not in text
        assert "catalogs.together_ai" not in text
    init = (root / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py").read_text(encoding="utf-8")
    assert init.strip() == '"""Package marker."""'
    assert "together_ai" not in init
