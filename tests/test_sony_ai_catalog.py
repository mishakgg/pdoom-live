"""Offline checks for the Sony AI page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import re
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.sony_ai as sony_ai
from pdoom_pipeline.catalogs.sony_ai import (
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
    UNKNOWN_DATE,
    WWW_HOST,
    CatalogError,
    catalog_path,
    confirmed_fetch_url,
    is_challenge_page,
    load_catalog,
    official_sony_ai_host,
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

SAMPLE_URL = "https://ai.sony/publications/ccstereo-audio-visual-contextual-and-contrastive-learning-for-binaural-audio-generation"
NEWS_URL = "https://ai.sony/news/pr0001"
BLOG_URL = "https://ai.sony/blog/sony-ai-at-icml-sharing-new-approaches-to-reinforcement-learning-generative-modeling-and-defensible-ai"
RESEARCH_URL = "https://ai.sony/research-areas/gaming-ai"
BODY = (
    "This paragraph is the page body. It is not catalog metadata and must not be stored. "
    "binaural audio generation abstract."
)
REJECTED_URLS = [
    "http://ai.sony/news",
    "https://www.sony.com/",
    "https://store.sony.com/",
    "https://electronics.sony.com/ai",
    "https://sony.com/research",
    "https://www.example.com/publications/paper",
    "https://ai.sony/people/semin-kwak",
    "https://ai.sony/join-us",
    "https://ai.sony/about/leadership",
    "https://ai.sony/terms-of-use",
    "https://ai.sony/privacy-policy",
    "https://ai.sony/contact-us",
    "https://ai.sony/login/",
    "https://ai.sony/store/camera",
    "https://ai.sony/news?ref=home",
    "https://ai.sony/news#top",
    "https://user:pass@ai.sony/news",
    "https://ai.sony:443/news",
    "https://ai.sony/publications/paper.pdf",
    "https://ai.sony/hubfs/logo.png",
    "https://127.0.0.1/news",
    "https://169.254.169.254/latest/meta-data/",
    "https://ai.sony/news/../publications",
    "https://not-ai.sony/news",
    "https://ai.sony.example/news",
]
CLOUDFLARE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing ai.sony. "
    "cf-mitigated: challenge challenge-platform</body></html>"
)
SITEGROUND_HTML = (
    "<html><head><meta http-equiv=\"refresh\" "
    "content=\"0;/.well-known/sgcaptcha/?r=%2Fnews\"></head>"
    "<body>sg-captcha</body></html>"
)
AKAMAI_HTML = (
    "<html><head><title>Access Denied</title></head>"
    "<body>You don't have permission to access. AkamaiGHost errors.edgesuite.net</body></html>"
)
ROBOTS = """User-agent: *
Disallow: /_hcms/preview/
Disallow: /hs/manage-preferences/
Disallow: /hs/preferences-center/
Disallow: /*?*hs_preview=*
Disallow: /*?*hsCacheBuster=*
"""
ROBOTS_404 = "<!DOCTYPE html><html><title>404: NOT_FOUND</title><p>Page not found</p></html>"


def _page(
    title: str,
    canonical: str,
    *,
    heading: str | None = None,
    published: str | None = None,
    updated: str | None = None,
    body: str | None = None,
    hero_date: str | None = None,
) -> str:
    published_tag = (
        f'<meta property="article:published_time" content="{published}">' if published else ""
    )
    updated_tag = f'<meta property="article:modified_time" content="{updated}">' if updated else ""
    shown = heading if heading is not None else title
    hero = (
        f'<div class="blog-post-hero__details"><span>{hero_date}</span></div>' if hero_date else ""
    )
    return (
        "<html><head>"
        f"<title>{title} - Sony AI</title>"
        f'<meta property="og:title" content="{title}">'
        f"{published_tag}{updated_tag}"
        f'<link rel="canonical" href="{canonical}">'
        "</head><body>"
        f"<h1>{shown}</h1>"
        f"{hero}"
        f"<p>{body if body is not None else BODY}</p>"
        "<p>By a Sony AI researcher.</p>"
        "<footer>Sony AI &copy; 2026</footer>"
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
    assert document["entries"]


def test_committed_catalog_is_metadata_only_and_runner_wired_is_false():
    document = load_catalog()
    assert catalog_path().name == "sony_ai_pages.json"
    assert document["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert document["description"] == CATALOG_DESCRIPTION
    assert len(document["description"]) <= 800
    description = document["description"]
    assert OFFICIAL_HOST in description
    assert WWW_HOST in description
    assert "bounded GET" in description
    assert "robots.txt" in description
    assert "sitemap" in description
    assert "creative_commons_attribution" in description
    assert "creative_commons" in description
    assert "runner_wired is false" in description
    assert "belief collector" in description
    assert FETCH_TIMEOUT_SECONDS == 12
    assert FETCH_MAX_REDIRECTS == 3
    assert FETCH_MAX_BYTES == 2_000_000
    raw = catalog_path().read_text(encoding="utf-8")
    for host in (
        "store.sony.com",
        "www.sony.com",
        "electronics.sony.com",
        "sony.com/store",
    ):
        assert host not in raw
    for leaked in ("<html", ".pdf", "p(doom)", BODY):
        assert leaked not in raw
    parsed = json.loads(raw)
    assert set(parsed) == {"catalog_id", "description", "runner_wired", "entries"}
    entries = document["entries"]
    rights_counts = {label: 0 for label in sorted(RIGHTS_LABELS)}
    hosts: set[str] = set()
    sections: set[str] = set()
    for entry in entries:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["publisher"] == PUBLISHER
        assert entry["rights"] in RIGHTS_LABELS
        host = entry["canonical_url"].split("/")[2]
        hosts.add(host)
        assert official_sony_ai_host(host)
        assert entry["date"] == UNKNOWN_DATE or re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
        rights_counts[entry["rights"]] += 1
        path = "/" + entry["canonical_url"].split("/", 3)[-1]
        if entry["canonical_url"].rstrip("/") == f"https://{OFFICIAL_HOST}":
            sections.add("/")
        else:
            sections.add(path.strip("/").split("/", 1)[0])
    assert hosts == {OFFICIAL_HOST}
    assert WWW_HOST not in hosts
    assert sections <= {"/", "publications", "news", "blog", "research-areas", "stories", "ja"}
    assert "publications" in sections
    assert "news" in sections
    assert "blog" in sections
    assert "research-areas" in sections
    urls = {entry["canonical_url"] for entry in entries}
    assert "https://ai.sony" in urls or "https://ai.sony/" in urls
    assert SAMPLE_URL in urls
    assert NEWS_URL in urls
    assert BLOG_URL in urls
    assert RESEARCH_URL in urls
    assert "https://ai.sony/people/semin-kwak" not in urls
    assert "https://ai.sony/join-us" not in urls
    assert len(entries) == 572
    assert sum(rights_counts.values()) == 572
    assert rights_counts[RIGHTS_UNKNOWN] == 570
    assert rights_counts[RIGHTS_CC_BY_NC_SA] == 1
    assert rights_counts[RIGHTS_MIT] == 1
    by_url = {entry["canonical_url"]: entry for entry in entries}
    assert by_url[
        "https://ai.sony/blog/new-dataset-labeling-breakthrough-strips-social-constructs-in-image-recognition"
    ]["rights"] == RIGHTS_CC_BY_NC_SA
    assert by_url[
        "https://ai.sony/blog/unlocking-the-future-of-video-to-audio-synthesis-inside-the-mmaudio-model"
    ]["rights"] == RIGHTS_MIT
    assert by_url[NEWS_URL]["date"] == "2020-05-11"
    assert by_url[BLOG_URL]["title"] == (
        "Sony AI at ICML: Sharing New Approaches to Reinforcement Learning, Generative Modeling, and Defensible AI"
    )
    assert by_url[BLOG_URL]["date"] == "2025-07-14"
    for entry in entries:
        path = entry["canonical_url"].split("ai.sony", 1)[1]
        if path.startswith("/blog/") or path.startswith("/news/"):
            assert entry["date"] != UNKNOWN_DATE
        if path.startswith("/publications"):
            assert entry["date"] == UNKNOWN_DATE


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
    source = Path(sony_ai.__file__).read_text(encoding="utf-8")
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
            "http://www.creativecommons.org/licenses?ref=home",
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
    elsewhere = (
        '<a href="https://creativecommons.org/licenses/?lang=en">CC BY</a>'
        "<p>Licensed under CC BY-SA 4.0.</p>"
    )
    assert rights_from_page(elsewhere) == RIGHTS_CREATIVE_COMMONS


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
        "<footer>© 2026 Sony AI. All rights reserved.</footer>",
        "<p>See the terms. Hosted at ai.sony.</p>",
        '<a href="https://ai.sony/">Sony AI</a>',
        "<p>No reuse licence is stated.</p>",
    ]
    for html in cases:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<link rel="license" href="https://creativecommons.org/licenses/by-nc-nd/4.0/">') == RIGHTS_CC_BY_NC_ND


def test_photo_caption_and_image_credits_stay_unknown():
    photo = (
        "<p>Photo credit: UNDRR ("
        '<a href="https://creativecommons.org/licenses/by-nc-nd/2.0/">CC BY-NC-ND 2.0</a>).</p>'
    )
    assert rights_from_page(photo) == RIGHTS_UNKNOWN
    prose = "<p>Photo credit: UNDRR, CC BY-NC-ND 2.0.</p>"
    assert rights_from_page(prose) == RIGHTS_UNKNOWN
    assert rights_from_page("<figcaption>Caption credit: CC BY-SA 4.0.</figcaption>") == RIGHTS_UNKNOWN
    assert rights_from_page(
        '<p>Image credit: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a></p>'
    ) == RIGHTS_UNKNOWN
    separate = photo + "<p>Licensed under CC BY 4.0.</p>"
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
        "<script>Photo credit: UNDRR, CC BY-NC-ND 2.0.</script><p>Licensed under CC BY 4.0.</p>",
    ]
    for html in hidden[:-1]:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    assert rights_from_page(hidden[-1]) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    visible_link = '<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">'
    assert rights_from_page(visible_link) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_publication_dates_ignore_updated_modified_and_copyright_years():
    hero = (
        '<div class="blog-post-hero__details"><span>July 14, 2025</span></div>'
        "<p>Sony AI was founded on April 1, 2020.</p>"
        '<meta property="article:modified_time" content="2026-03-04T12:13:07Z">'
        '<meta property="og:updated_time" content="2026-11-01T00:00:00Z">'
        "<p>© 2026 Sony AI</p>"
        "<p>Date 2025</p>"
    )
    assert publication_date_from_page(hero) == "2025-07-14"
    listing = (
        "<span>December 11, 2025</span>"
        "<span>August 20, 2025</span>"
        "<span>March 26, 2025</span>"
        "<p>© 2026</p>"
    )
    assert publication_date_from_page(listing) == UNKNOWN_DATE
    updated = "<p>Last update: May 2026.</p><p>Updated 2024-05-01</p><p>© 2020</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    modified = '<meta property="article:modified_time" content="2024-04-18T14:43:38.000Z">'
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    meta_only = '<meta property="article:published_time" content="2020-05-11T04:00:00.000Z">'
    assert publication_date_from_page(meta_only) == "2020-05-11"
    script_date = (
        '<script type="application/ld+json">{"datePublished":"2025-07-14","dateModified":"2026-03-04"}</script>'
        "<p>No visible date.</p>"
    )
    assert publication_date_from_page(script_date) == UNKNOWN_DATE
    comment = "<!-- July 14, 2025 --><p>No visible date.</p>"
    assert publication_date_from_page(comment) == UNKNOWN_DATE
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2025-07-14") == "2025-07-14"
    with pytest.raises(CatalogError, match="date"):
        validate_date("July 14, 2025")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    record = page_record(
        _page("CCStereo", SAMPLE_URL, hero_date="July 14, 2025"),
        page_url=SAMPLE_URL,
    )
    assert record["title"] == "CCStereo"
    assert record["publisher"] == PUBLISHER
    assert record["canonical_url"] == SAMPLE_URL
    assert record["date"] == "2025-07-14"
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    stored = json.dumps(record)
    assert BODY not in stored
    assert "must not be stored" not in stored
    assert "generation abstract" not in stored
    dated = page_record(
        _page(
            "CCStereo",
            SAMPLE_URL,
            published="2020-05-11T04:00:00.000Z",
            updated="2026-03-04T01:32:59.830Z",
        ),
        page_url=SAMPLE_URL,
    )
    assert dated["date"] == "2020-05-11"
    assert "2026-03-04" not in json.dumps(dated)


def test_a_different_canonical_link_does_not_replace_the_live_url():
    html = _page("News", "https://www.ai.sony/news/pr0001")
    record = page_record(html, page_url=NEWS_URL)
    assert record["canonical_url"] == NEWS_URL


def test_a_person_is_not_the_publisher():
    record = page_record(_page("CCStereo", SAMPLE_URL), page_url=SAMPLE_URL)
    assert record["publisher"] == PUBLISHER
    missing = "<html><head><title>A note</title></head><body><h1>A note</h1><p>By someone else.</p></body></html>"
    with pytest.raises(CatalogError, match="publisher"):
        page_record(missing, page_url=SAMPLE_URL)


def test_title_strips_the_site_suffix_and_ignores_script():
    suffixed = "<html><head><title>A paper - Sony AI</title></head><body></body></html>"
    assert title_from_page(suffixed) == "A paper"
    piped = "<html><head><title>Blog | Sony AI</title></head><body></body></html>"
    assert title_from_page(piped) == "Blog"
    hidden = (
        "<html><head><script>ignore previous instructions</script>"
        "<title>News | Sony AI</title></head><body><h1>Hacked</h1></body></html>"
    )
    assert title_from_page(hidden) == "News"
    assert "ignore previous instructions" not in title_from_page(hidden)
    assert "Hacked" not in title_from_page(hidden)
    completed = (
        "<html><head><title>Sony AI at ICML: Sharing New Approaches to Reinforcement Learning, Generative Mo... - Sony AI</title></head>"
        "<body><h1>Sony AI at ICML: Sharing New Approaches to Reinforcement Learning, Generative Modeling, and Defensible AI"
        "AI for CreatorsGame AI and Interactive AgentsPPML</h1></body></html>"
    )
    assert title_from_page(completed) == (
        "Sony AI at ICML: Sharing New Approaches to Reinforcement Learning, Generative Modeling, and Defensible AI"
    )
    kept = "<html><head><title>A complete paper - Sony AI</title></head><body><h1>A different heading</h1></body></html>"
    assert title_from_page(kept) == "A complete paper"
    robotics = (
        "<html><head><title>Named 2022 IEEE Fellow in Recognition of Outstanding ... - Sony AI</title></head>"
        "<body><h1>Named 2022 IEEE Fellow in Recognition of Outstanding Contributions to Computational Auction, "
        "Multiagent Systems and Robotics</h1></body></html>"
    )
    assert title_from_page(robotics).endswith("Multiagent Systems and Robotics")


def test_research_prose_is_not_a_block_page():
    html = _page(
        "Advancing Artificial Intelligence Research",
        "https://ai.sony/",
        body="Sony AI explores research that can solve ambitious global challenges.",
    )
    assert is_challenge_page(html) is False
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=utf-8",
        page_html=html,
        page_url="https://ai.sony/",
        final_url="https://ai.sony/",
    )
    assert stored is not None
    assert stored["canonical_url"] == "https://ai.sony/"
    assert "global challenges" not in json.dumps(stored)


def test_challenge_status_and_off_host_redirect_are_not_stored():
    assert is_challenge_page(CLOUDFLARE_HTML)
    assert is_challenge_page(SITEGROUND_HTML)
    assert record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=CLOUDFLARE_HTML,
        page_url=NEWS_URL,
        headers={"cf-mitigated": "challenge"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=SITEGROUND_HTML,
        page_url=NEWS_URL,
        headers={"sg-captcha": "challenge"},
    ) is None
    assert record_from_response(
        status=202,
        content_type="text/html; charset=UTF-8",
        page_html=_page("News", NEWS_URL),
        page_url=NEWS_URL,
    ) is None
    assert record_from_response(
        status=404,
        content_type="text/html",
        page_html="<html><title>404: NOT_FOUND</title></html>",
        page_url="https://ai.sony/research-areas",
    ) is None
    assert record_from_response(
        status=403,
        content_type="text/html",
        page_html=AKAMAI_HTML,
        page_url=NEWS_URL,
        headers={"server": "AkamaiGHost"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7 synthetic",
        page_url=NEWS_URL,
    ) is None
    assert confirmed_fetch_url(NEWS_URL, "https://www.sony.com/news") is None
    assert confirmed_fetch_url(NEWS_URL, "https://ai.sony/blog") is None
    assert confirmed_fetch_url("https://www.ai.sony/news/pr0001", NEWS_URL) is None
    assert confirmed_fetch_url("http://ai.sony/news/pr0001", NEWS_URL) is None
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page("A press note", NEWS_URL, hero_date="May 11, 2020"),
        page_url=NEWS_URL,
        final_url=NEWS_URL,
    )
    assert stored is not None
    assert stored["canonical_url"] == NEWS_URL
    assert stored["date"] == "2020-05-11"
    assert BODY not in json.dumps(stored)


def test_www_is_stored_only_when_the_response_stays_on_www():
    html = _page("News", "https://www.ai.sony/news")
    stayed = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url="https://www.ai.sony/news",
        final_url="https://www.ai.sony/news",
    )
    assert stayed is not None
    assert stayed["canonical_url"] == "https://www.ai.sony/news"
    redirected = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url="https://www.ai.sony/news",
        final_url="https://ai.sony/news",
    )
    assert redirected is None
    assert official_sony_ai_host(WWW_HOST)
    assert official_sony_ai_host(OFFICIAL_HOST)
    assert official_sony_ai_host("www.sony.com") is False
    assert official_sony_ai_host("store.sony.com") is False


def test_robots_allows_public_paths_and_blocks_preview_and_challenges():
    assert robots_allows(ROBOTS, "/")
    assert robots_allows(ROBOTS, "/publications")
    assert robots_allows(ROBOTS, "/news/pr0001")
    assert robots_allows(ROBOTS, "/blog")
    assert robots_allows(ROBOTS, "/research-areas/gaming-ai")
    assert robots_allows(ROBOTS, "/_hcms/preview/page") is False
    assert robots_allows(ROBOTS, "/hs/manage-preferences/email") is False
    assert robots_allows(ROBOTS, "/news?hs_preview=1") is False
    assert robots_allows(ROBOTS, "/blog?hsCacheBuster=1") is False
    assert robots_allows(ROBOTS_404, "/publications")
    assert robots_allows("", "/news")
    challenge = "<html><title>Just a moment...</title><p>challenge-platform</p></html>"
    assert robots_allows(challenge, "/news") is False
    blocked = "User-agent: *\nDisallow: /\n"
    html = _page("News", NEWS_URL)
    omitted = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url=NEWS_URL,
        final_url=NEWS_URL,
        robots_text=blocked,
    )
    assert omitted is None


def test_non_sony_ai_urls_are_rejected():
    for rejected in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(rejected)


@pytest.mark.parametrize(
    "url",
    [
        "https://ai.sony/",
        "https://ai.sony",
        "https://ai.sony/publications",
        "https://ai.sony/publications/",
        SAMPLE_URL,
        "https://ai.sony/news",
        NEWS_URL,
        "https://ai.sony/blog",
        BLOG_URL,
        RESEARCH_URL,
        "https://ai.sony/stories",
        "https://ai.sony/ja/news",
        "https://www.ai.sony/news",
        "https://ai.sony/publications/ligand-based-and-structure-based-studies-to-develop-predictive-models-for-sars-cov-2-main-protease-inhibitors-through-the-3d-qsar.com-portal",
        "https://ai.sony/news/groundbreaking-fairness-evaluation-dataset-from-sony-ai-",
        "https://ai.sony/blog/what-happened-after-the-nature-paper-ace-vs.-professional-players",
    ],
)
def test_official_sony_ai_urls_are_accepted(url: str):
    assert validate_canonical_url(url) == url
    assert official_sony_ai_host(url.split("/")[2])


def test_blocked_hostname_is_rejected(monkeypatch):
    monkeypatch.setattr(sony_ai, "hostname_is_blocked", lambda _host: True)
    with pytest.raises(CatalogError):
        validate_canonical_url("https://ai.sony/news")
    assert official_sony_ai_host("ai.sony") is False


def test_validator_rejects_bad_rights_and_accepts_an_empty_list():
    document = copy.deepcopy(load_catalog())
    document["entries"] = []
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = "cc-by-nc"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = BODY
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["abstract"] = "a stored abstract"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["quote"] = "a stored quote"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["transcript"] = "a stored transcript"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["probability"] = 0.2
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["canonical_url"] = "https://store.sony.com/"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["publisher"] = "Sony"
    with pytest.raises(CatalogError, match="publisher"):
        validate_catalog(document)


def test_catalog_is_not_wired_into_belief_collection():
    module = Path(sony_ai.__file__).read_text(encoding="utf-8")
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
    assert "sony_ai" not in init
    collectors = (root / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py").read_text(encoding="utf-8")
    assert collectors.strip() == '"""Package marker."""'
    assert "sony_ai" not in collectors
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "sony_ai_pages" not in text
        assert "catalogs.sony_ai" not in text
    collect = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in collect
    assert "RssCollector" in collect
    wired = re.findall(r"(\w+Collector)\(", collect)
    assert wired == ["RssCollector"]
