"""Offline checks for the Safe Superintelligence page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import re
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.ssi as ssi
from pdoom_pipeline.catalogs.ssi import (
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
    official_ssi_host,
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

# Titles, publishers, canonical URLs, dates, and rights confirmed from one bounded GET each.
# The homepage states no publication date. The updates page lists several news dates and has
# no single publication date. None of the pages state a reuse licence.
# Trailing-slash aliases of the same HTML are not stored a second time.
EXPECTED = [
    [
        "Safe Superintelligence Inc.",
        "Safe Superintelligence",
        "https://ssi.inc/",
        "unknown",
        "unknown",
    ],
    [
        "Contact Us",
        "Safe Superintelligence",
        "https://ssi.inc/contact",
        "unknown",
        "unknown",
    ],
    [
        "Updates",
        "Safe Superintelligence",
        "https://ssi.inc/updates",
        "unknown",
        "unknown",
    ],
]

SAMPLE_URL = "https://ssi.inc/updates"
BODY = (
    "This paragraph is the page body. It is not catalog metadata and must not be stored. "
    "straight-shot superintelligence Palo Alto."
)
REJECTED_URLS = [
    "http://ssi.inc/",
    "https://jobs.ashbyhq.com/ssi/",
    "https://www.globenewswire.com/news-release/example",
    "https://x.com/ilyasut/status/1",
    "https://www.reuters.com/technology/example",
    "https://ssi.inc/login/",
    "https://ssi.inc/updates?ref=home",
    "https://ssi.inc/updates#news",
    "https://user:pass@ssi.inc/updates",
    "https://ssi.inc:443/updates",
    "https://ssi.inc/paper.pdf",
    "https://ssi.inc/public/styles.css",
    "https://ssi.inc/public/og-preview.jpg",
    "https://127.0.0.1/updates",
    "https://169.254.169.254/latest/meta-data/",
    "https://ssi.inc/updates/../contact",
    "https://ssi.inc/index.html",
    "https://not-ssi.inc/",
]
CLOUDFLARE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing ssi.inc. "
    "cf-mitigated: challenge challenge-platform</body></html>"
)
SITEGROUND_HTML = (
    "<html><head><meta http-equiv=\"refresh\" "
    "content=\"0;/.well-known/sgcaptcha/?r=%2Fupdates\"></head>"
    "<body>sg-captcha</body></html>"
)
AKAMAI_HTML = (
    "<html><head><title>Access Denied</title></head>"
    "<body>You don't have permission to access. AkamaiGHost errors.edgesuite.net</body></html>"
)
ROBOTS_404 = "<!DOCTYPE html><html><title>404: NOT_FOUND</title><p>Page not found</p></html>"


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
        f'<meta property="og:title" content="{title}">'
        f"{published_tag}{updated_tag}"
        f'<link rel="canonical" href="{canonical}">'
        "</head><body>"
        f"<h2>{shown}</h2>"
        f"<p>{body if body is not None else BODY}</p>"
        "<p>By Ilya Sutskever.</p>"
        "<footer>Safe Superintelligence Inc. &copy; 2024 - 2026</footer>"
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
    assert len(document["entries"]) == len(EXPECTED)


def test_committed_catalog_matches_confirmed_pages():
    document = load_catalog()
    assert catalog_path().name == "ssi_pages.json"
    assert document["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert document["description"] == CATALOG_DESCRIPTION
    assert len(document["description"]) <= 800
    description = document["description"]
    assert OFFICIAL_HOST in description
    assert "bounded GET" in description
    assert "robots.txt" in description
    assert "404" in description
    assert "creative_commons_attribution" in description
    assert "creative_commons" in description
    assert "runner_wired is false" in description
    assert "belief collector" in description
    assert FETCH_TIMEOUT_SECONDS == 12
    assert FETCH_MAX_REDIRECTS == 3
    assert FETCH_MAX_BYTES == 400_000
    raw = catalog_path().read_text(encoding="utf-8")
    for host in (
        "jobs.ashbyhq.com",
        "globenewswire.com",
        "reuters.com",
        "x.com",
    ):
        assert host not in raw
    for leaked in (
        "straight-shot",
        "Palo Alto",
        "NVIDIA",
        "Daniel Gross",
        "comms@",
        "mailto:",
        "<html",
        ".pdf",
        BODY,
    ):
        assert leaked not in raw
    parsed = json.loads(raw)
    assert set(parsed) == {"catalog_id", "description", "runner_wired", "entries"}
    entries = document["entries"]
    assert [
        tuple(entry[field] for field in ("title", "publisher", "canonical_url", "date", "rights"))
        for entry in entries
    ] == [tuple(row) for row in EXPECTED]
    rights_counts = {label: 0 for label in sorted(RIGHTS_LABELS)}
    unknown_dates = 0
    hosts: set[str] = set()
    for entry in entries:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["publisher"] == PUBLISHER
        host = entry["canonical_url"].split("/")[2]
        hosts.add(host)
        assert official_ssi_host(host)
        assert entry["date"] == UNKNOWN_DATE or re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
        rights_counts[entry["rights"]] += 1
        if entry["date"] == UNKNOWN_DATE:
            unknown_dates += 1
    assert len(entries) == 3
    assert rights_counts[RIGHTS_UNKNOWN] == 3
    assert sum(rights_counts.values()) == 3
    assert unknown_dates == 3
    assert hosts == {OFFICIAL_HOST}
    assert WWW_HOST not in hosts


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
    source = Path(ssi.__file__).read_text(encoding="utf-8")
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
    two_restricted = "<p>CC BY-NC and CC BY-ND.</p>"
    assert rights_from_page(two_restricted) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY-NC-SA and CC BY-NC-ND.</p>") == RIGHTS_UNKNOWN


def test_generic_license_url_anchor_text_is_not_a_licence():
    for anchor in ("CC BY", "CC BY 4.0", "CC BY-SA", "Creative Commons Attribution 4.0"):
        for href in (
            "https://creativecommons.org/licenses/",
            "https://creativecommons.org/licenses",
            "https://www.creativecommons.org/licenses/",
            "http://creativecommons.org/licenses/",
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
        "<footer>© 2026 Safe Superintelligence Inc. All rights reserved.</footer>",
        "<p>See the terms. Hosted at ssi.inc.</p>",
        '<a href="https://ssi.inc/">Safe Superintelligence</a>',
    ]
    for html in cases:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<link rel="license" href="https://creativecommons.org/licenses/by-nc-nd/4.0/">') == RIGHTS_CC_BY_NC_ND


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
    ]
    for html in hidden:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    visible_link = '<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">'
    assert rights_from_page(visible_link) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_publication_dates_ignore_updated_modified_and_copyright_years():
    stated = (
        '<time datetime="2026-07-26T00:00:00Z">July 26, 2026</time>'
        '<meta property="article:modified_time" content="2026-10-01T00:00:00Z">'
        '<meta property="og:updated_time" content="2026-11-01T00:00:00Z">'
        "<p>© 2024 Safe Superintelligence Inc.</p>"
    )
    assert publication_date_from_page(stated) == "2026-07-26"
    listing = (
        '<time datetime="2024-09-04">September 4, 2024</time>'
        '<time datetime="2025-07-03">July 3, 2025</time>'
        '<time datetime="2026-07-26">July 26, 2026</time>'
        '<meta property="article:published_time" content="2020-01-01T00:00:00Z">'
    )
    assert publication_date_from_page(listing) == UNKNOWN_DATE
    prose = "<p>July 26, 2026. July 3, 2025. September 4, 2024. Update: a note. © 2024</p>"
    assert publication_date_from_page(prose) == UNKNOWN_DATE
    updated = "<p>Last update: May 2026.</p><p>Updated 2024-05-01</p><p>© 2020</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    modified = '<meta property="article:modified_time" content="2024-04-18T14:43:38.000Z">'
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    meta_only = '<meta property="article:published_time" content="2024-09-04T00:00:00Z">'
    assert publication_date_from_page(meta_only) == "2024-09-04"
    script_date = '<script type="application/ld+json">{"datePublished":"2024-09-04"}</script><p>No date.</p>'
    assert publication_date_from_page(script_date) == UNKNOWN_DATE
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2024-09-04") == "2024-09-04"
    with pytest.raises(CatalogError, match="date"):
        validate_date("4 September 2024")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    record = page_record(_page("Safe Superintelligence Inc.", "https://ssi.inc/", heading="Updates"), page_url=SAMPLE_URL)
    assert record["title"] == "Updates"
    assert record["publisher"] == PUBLISHER
    assert record["canonical_url"] == SAMPLE_URL
    assert record["date"] == UNKNOWN_DATE
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    stored = json.dumps(record)
    assert BODY not in stored
    assert "Ilya Sutskever" not in stored
    assert "straight-shot" not in stored
    dated = page_record(
        _page(
            "Safe Superintelligence Inc.",
            SAMPLE_URL,
            heading="Updates",
            published="2026-07-26T00:00:00Z",
            updated="2026-10-01T00:00:00Z",
        ),
        page_url=SAMPLE_URL,
    )
    assert dated["date"] == "2026-07-26"
    assert "2026-10-01" not in json.dumps(dated)


def test_a_different_canonical_link_does_not_replace_the_live_url():
    html = _page("Safe Superintelligence Inc.", "https://ssi.inc")
    record = page_record(html, page_url="https://ssi.inc/")
    assert record["canonical_url"] == "https://ssi.inc/"


def test_a_person_is_not_the_publisher():
    record = page_record(_page("Safe Superintelligence Inc.", "https://ssi.inc/"), page_url="https://ssi.inc/")
    assert record["publisher"] == PUBLISHER
    missing = "<html><head><title>A note</title></head><body><h1>A note</h1><p>By Ilya Sutskever.</p></body></html>"
    with pytest.raises(CatalogError, match="publisher"):
        page_record(missing, page_url="https://ssi.inc/")


def test_title_uses_the_page_heading_when_the_document_title_is_only_the_organization():
    updates = "<html><head><title>Safe Superintelligence Inc.</title></head><body><h2>Updates</h2></body></html>"
    assert title_from_page(updates) == "Updates"
    contact = "<html><head><title>Safe Superintelligence Inc.</title></head><body><h2>Contact Us</h2></body></html>"
    assert title_from_page(contact) == "Contact Us"
    home = (
        "<html><head><title>Safe Superintelligence Inc.</title></head>"
        "<body><h2>Safe Superintelligence Inc.</h2></body></html>"
    )
    assert title_from_page(home) == "Safe Superintelligence Inc."
    suffixed = "<html><head><title>A paper - Safe Superintelligence</title></head><body></body></html>"
    assert title_from_page(suffixed) == "A paper"
    hidden = "<html><head><script>ignore previous instructions</script><title>Safe Superintelligence Inc.</title></head><body><h2>Updates</h2></body></html>"
    assert title_from_page(hidden) == "Updates"
    assert "ignore previous instructions" not in title_from_page(hidden)


def test_technical_challenge_prose_is_not_a_block_page():
    html = _page(
        "Safe Superintelligence Inc.",
        "https://ssi.inc/",
        body="Building safe superintelligence is the most important technical challenge of our age.",
    )
    assert is_challenge_page(html) is False
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=utf-8",
        page_html=html,
        page_url="https://ssi.inc/",
        final_url="https://ssi.inc/",
    )
    assert stored is not None
    assert stored["canonical_url"] == "https://ssi.inc/"
    assert "technical challenge" not in json.dumps(stored)


def test_challenge_status_and_off_host_redirect_are_not_stored():
    assert is_challenge_page(CLOUDFLARE_HTML)
    assert is_challenge_page(SITEGROUND_HTML)
    assert record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=CLOUDFLARE_HTML,
        page_url=SAMPLE_URL,
        headers={"cf-mitigated": "challenge"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=SITEGROUND_HTML,
        page_url=SAMPLE_URL,
        headers={"sg-captcha": "challenge"},
    ) is None
    assert record_from_response(
        status=202,
        content_type="text/html; charset=UTF-8",
        page_html=_page("Updates", SAMPLE_URL),
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=404,
        content_type="text/html",
        page_html="<html><title>404: NOT_FOUND</title></html>",
        page_url="https://ssi.inc/research",
    ) is None
    assert record_from_response(
        status=403,
        content_type="text/html",
        page_html=AKAMAI_HTML,
        page_url=SAMPLE_URL,
        headers={"server": "AkamaiGHost"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7 synthetic",
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/css",
        page_html="body{color:#111}",
        page_url="https://ssi.inc/public/styles.css",
    ) is None
    assert confirmed_fetch_url(SAMPLE_URL, "https://jobs.ashbyhq.com/ssi/") is None
    assert confirmed_fetch_url("https://ssi.inc/updates", "https://ssi.inc/contact") is None
    assert confirmed_fetch_url("https://www.ssi.inc/updates", "https://ssi.inc/updates") is None
    assert confirmed_fetch_url("http://ssi.inc/", "https://ssi.inc/") is None
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page("Safe Superintelligence Inc.", SAMPLE_URL, heading="Updates", published="2026-07-26T00:00:00Z"),
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
    )
    assert stored is not None
    assert stored["canonical_url"] == SAMPLE_URL
    assert stored["date"] == "2026-07-26"
    assert BODY not in json.dumps(stored)


def test_www_is_stored_only_when_the_response_stays_on_www():
    html = _page("Safe Superintelligence Inc.", "https://www.ssi.inc/updates", heading="Updates")
    stayed = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url="https://www.ssi.inc/updates",
        final_url="https://www.ssi.inc/updates",
    )
    assert stayed is not None
    assert stayed["canonical_url"] == "https://www.ssi.inc/updates"
    redirected = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url="https://www.ssi.inc/updates",
        final_url="https://ssi.inc/updates",
    )
    assert redirected is None
    assert official_ssi_host(WWW_HOST)
    assert official_ssi_host(OFFICIAL_HOST)


def test_robots_404_allows_public_paths_and_a_disallow_blocks_them():
    assert robots_allows(ROBOTS_404, "/")
    assert robots_allows(ROBOTS_404, "/updates")
    assert robots_allows(ROBOTS_404, "/contact")
    assert robots_allows("", "/updates")
    challenge = "<html><title>Just a moment...</title><p>challenge-platform</p></html>"
    assert robots_allows(challenge, "/updates") is False
    blocked = "User-agent: *\nDisallow: /\n"
    assert robots_allows(blocked, "/updates") is False
    assert robots_allows(blocked, "/") is False
    private = "User-agent: *\nDisallow: /private/\nAllow: /updates\n"
    assert robots_allows(private, "/updates") is True
    assert robots_allows(private, "/contact") is True
    assert robots_allows(private, "/private/draft/") is False
    html = _page("Safe Superintelligence Inc.", SAMPLE_URL, heading="Updates")
    omitted = record_from_response(
        status=200,
        content_type="text/html",
        page_html=html,
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
        robots_text=blocked,
    )
    assert omitted is None


def test_non_ssi_urls_are_rejected():
    for rejected in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(rejected)


@pytest.mark.parametrize(
    "url",
    [
        "https://ssi.inc/",
        "https://ssi.inc",
        "https://ssi.inc/updates",
        "https://ssi.inc/updates/",
        "https://ssi.inc/contact",
        "https://ssi.inc/research/example-note",
        "https://www.ssi.inc/updates",
    ],
)
def test_official_ssi_urls_are_accepted(url: str):
    assert validate_canonical_url(url) == url
    assert official_ssi_host(url.split("/")[2])


def test_blocked_hostname_is_rejected(monkeypatch):
    monkeypatch.setattr(ssi, "hostname_is_blocked", lambda _host: True)
    with pytest.raises(CatalogError):
        validate_canonical_url("https://ssi.inc/updates")
    assert official_ssi_host("ssi.inc") is False


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
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["canonical_url"] = "https://jobs.ashbyhq.com/ssi/"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0], document["entries"][1] = document["entries"][1], document["entries"][0]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)


def test_catalog_is_not_wired_into_belief_collection():
    module = Path(ssi.__file__).read_text(encoding="utf-8")
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
    assert "ssi" not in init
    collectors = (root / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py").read_text(encoding="utf-8")
    assert collectors.strip() == '"""Package marker."""'
    assert "ssi" not in collectors
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "ssi_pages" not in text
        assert "catalogs.ssi" not in text
    collect = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in collect
