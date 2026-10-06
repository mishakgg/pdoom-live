"""Offline tests for the Idiap Research Institute page catalog."""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from pdoom_pipeline.catalogs import idiap
from pdoom_pipeline.catalogs.idiap import (
    CATALOG_DESCRIPTION,
    CATALOG_ID,
    PUBLISHER,
    RIGHTS_APACHE,
    RIGHTS_CC_BY_NC,
    RIGHTS_CC_BY_NC_ND,
    RIGHTS_CC_BY_NC_SA,
    RIGHTS_CC_BY_ND,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
    RIGHTS_MIT,
    RIGHTS_MPL,
    RIGHTS_UK_OGL,
    RIGHTS_UNKNOWN,
    RIGHTS_US_GOVERNMENT_WORK,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    confirmed_fetch_url,
    is_challenge_page,
    load_catalog,
    official_idiap_host,
    page_record,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    robots_allows,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

BODY = "The model assigns a precise probability of 0.42 to extinction by 2030."
SAMPLE_URL = "https://www.idiap.ch/en/news/annual-report-2025"
APEX_URL = "https://idiap.ch/en/research/groups/machine-learning"
ROBOTS = """User-Agent: *
Allow: /
Disallow: /api/

Host: https://www.idiap.ch
Sitemap: https://www.idiap.ch/sitemap.xml
"""
RESTRICTED_URLS = (
    "https://creativecommons.org/licenses/by-nc/4.0/",
    "https://creativecommons.org/licenses/by-nd/4.0/",
    "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "https://creativecommons.org/licenses/by-nc-nd/4.0/",
)


def _page(title: str, *, body: str = "", published: str | None = None, extra: str = "") -> str:
    published_meta = ""
    if published:
        published_meta = f'<meta property="article:published_time" content="{published}">'
    return f"""<!doctype html><html><head>
<title>{title} | Idiap</title>
<meta property="og:title" content="{title}">
<meta property="og:site_name" content="Idiap Research Institute">
{published_meta}
<link rel="canonical" href="https://example.com/not-idiap">
</head><body>
<h1>{title}</h1>
<p>{body}</p>
<p>{BODY}</p>
<p>Author: Jane Doe.</p>
{extra}
</body></html>"""


def test_runner_wired_is_false():
    assert RUNNER_WIRED is False
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    assert catalog["description"] == CATALOG_DESCRIPTION
    assert "runner_wired is false" in catalog["description"]
    document = dict(catalog)
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)


def test_catalog_is_metadata_only():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert set(catalog) == {"catalog_id", "description", "runner_wired", "entries"}
    raw = catalog_path().read_text(encoding="utf-8")
    assert "probability" not in raw.casefold()
    assert "p(doom)" not in raw.casefold()
    assert "<p>" not in raw
    assert ".pdf" not in raw.casefold()
    for entry in catalog["entries"]:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert entry["publisher"] == PUBLISHER
        for value in entry.values():
            assert isinstance(value, str)
            assert len(value) <= 500
        assert BODY not in json.dumps(entry)


def test_catalog_rows_stay_on_idiap_hosts_and_scope():
    catalog = load_catalog()
    hosts = set()
    rights_counts: Counter[str] = Counter()
    for entry in catalog["entries"]:
        host = entry["canonical_url"].split("/")[2]
        hosts.add(host)
        assert official_idiap_host(host)
        path = "/" + entry["canonical_url"].split("/", 3)[3]
        assert path.startswith(("/en/research", "/en/projects", "/en/news"))
        assert "/people" not in path
        assert "/publications" not in path
        rights_counts[entry["rights"]] += 1
        validate_date(entry["date"])
    assert hosts == {"www.idiap.ch"}
    assert len(catalog["entries"]) == 457
    assert rights_counts["unknown"] == 456
    assert rights_counts["mit"] == 1
    assert sum(rights_counts.values()) == 457
    sections = Counter(entry["canonical_url"].split("/")[4] for entry in catalog["entries"])
    assert sections == {"projects": 358, "news": 59, "research": 40}
    assert "HTTP 404" in catalog["description"]


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("catalog load must not use the network")

    monkeypatch.setattr("urllib.request.urlopen", explode)
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID


def test_sole_restricted_deeds_keep_underscore_tokens():
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
        assert rights_from_page(page) not in {RIGHTS_CREATIVE_COMMONS, RIGHTS_CREATIVE_COMMONS_ATTRIBUTION}
    assert rights_from_page("<p>CC BY-NC</p>") != RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert "cc-by-nc" not in idiap.RIGHTS_LABELS
    source = Path(idiap.__file__).read_text(encoding="utf-8")
    assert "(?!-)" in source


def test_cc_by_alone_is_attribution_and_permissive_mixes_are_creative_commons():
    assert rights_from_page("<p>No reuse licence is stated.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>CC BY 4.0</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>CC-BY 4.0</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>Creative Commons Attribution 4.0.</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>') == (
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    )
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">read the deed</a>') == (
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    )
    assert rights_from_page("<p>CC0</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY-SA 4.0</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC0 and CC BY-SA.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY and CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY and CC BY-SA.</p>") == RIGHTS_CREATIVE_COMMONS
    zero = '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
    assert rights_from_page(zero) == RIGHTS_CREATIVE_COMMONS


def test_generic_license_url_anchor_text_is_not_a_deed():
    for anchor in ("CC BY", "CC BY 4.0", "CC BY-SA"):
        for href in (
            "https://creativecommons.org/licenses/",
            "https://creativecommons.org/licenses",
            "https://www.creativecommons.org/licenses/",
            "http://creativecommons.org/licenses/",
            "https://creativecommons.org/licenses/?lang=en",
            "http://www.creativecommons.org/licenses?ref=chooser",
        ):
            assert rights_from_page(f'<a href="{href}">{anchor}</a>') == RIGHTS_UNKNOWN
    elsewhere = (
        '<a href="https://creativecommons.org/licenses/">CC BY</a>'
        "<p>Licensed under CC BY-SA 4.0.</p>"
    )
    assert rights_from_page(elsewhere) == RIGHTS_CREATIVE_COMMONS
    specific = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
    assert rights_from_page(specific) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    generic_plus_restricted = (
        '<a href="https://creativecommons.org/licenses/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>'
    )
    assert rights_from_page(generic_plus_restricted) == RIGHTS_CC_BY_NC


def test_deceptive_anchors_and_public_domain_mark_stay_unknown():
    for url in RESTRICTED_URLS:
        assert rights_from_page(f'<a href="{url}">CC BY</a>') == RIGHTS_UNKNOWN
        assert rights_from_page(f'<a href="{url}">CC BY-SA</a>') == RIGHTS_UNKNOWN
    mark = "https://creativecommons.org/publicdomain/mark/1.0/"
    assert rights_from_page(f'<a href="{mark}">CC BY</a>') == RIGHTS_UNKNOWN
    assert rights_from_page(f'<a href="{mark}">CC BY-SA</a>') == RIGHTS_UNKNOWN
    assert rights_from_page(f'<a href="{mark}">CC0</a>') == RIGHTS_UNKNOWN
    assert rights_from_page(f'<a href="{mark}">Public Domain Mark</a>') == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Public Domain Mark 1.0</p>") == RIGHTS_UNKNOWN
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    swapped = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY-NC</a>'
    assert rights_from_page(swapped) == RIGHTS_UNKNOWN
    elsewhere = (
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>'
        "<p>Licensed under CC BY 4.0.</p>"
    )
    assert rights_from_page(elsewhere) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_mixed_deeds_and_software_licences_stay_distinct():
    assert rights_from_page("<p>CC BY-NC and CC BY-ND.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY-NC-SA and CC BY-NC-ND.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY 4.0 and also CC BY-NC.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC0 and CC BY-ND 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>This work is licensed under the MIT License.</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Apache License, Version 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache License 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache License</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MPL-2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>Mozilla Public License 2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MIT License and Apache-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and MPL-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and CC BY-SA 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and CC BY-NC.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MPL-2.0 and CC0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>A collaboration with MIT and NYU.</p>") == RIGHTS_UNKNOWN


def test_uk_ogl_and_us_government_work():
    assert rights_from_page("<p>Open Government Licence v3.0</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>open government licence</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>Licensed under the Open Government License v3.0.</p>") == RIGHTS_UNKNOWN
    archives = '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">terms</a>'
    assert rights_from_page(archives) == RIGHTS_UNKNOWN
    rights_field = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(rights_field) == RIGHTS_US_GOVERNMENT_WORK
    named = '<meta name="rights" content="United States Government work">'
    assert rights_from_page(named) == RIGHTS_US_GOVERNMENT_WORK
    dcterms = '<meta name="dcterms.rights" content="Work of the United States Government.">'
    assert rights_from_page(dcterms) == RIGHTS_US_GOVERNMENT_WORK
    assert rights_from_page("<p>This is a work of the United States Government.</p>") == RIGHTS_UNKNOWN
    licence_field = '<meta name="license" content="This is a work of the United States Government.">'
    assert rights_from_page(licence_field) == RIGHTS_UNKNOWN
    negated = '<meta name="rights" content="This is not a work of the United States Government.">'
    assert rights_from_page(negated) == RIGHTS_UNKNOWN
    mixed = rights_field + "<p>CC BY 4.0</p>"
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN
    assert rights_from_page("<p>All rights reserved.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>This page is public. See the terms.</p>") == RIGHTS_UNKNOWN


def test_photo_caption_and_image_credits_stay_unknown():
    photo = "<p>Photo credit: UNDRR, CC BY-NC-ND 2.0.</p>"
    assert rights_from_page(photo) == RIGHTS_UNKNOWN
    linked = (
        "<p>Photo credit: UNDRR ("
        '<a href="https://creativecommons.org/licenses/by-nc-nd/2.0/">CC BY-NC-ND 2.0</a>).</p>'
    )
    assert rights_from_page(linked) == RIGHTS_UNKNOWN
    assert rights_from_page("<figcaption>Caption credit: CC BY-SA 4.0.</figcaption>") == RIGHTS_UNKNOWN
    assert rights_from_page(
        '<p>Image credit: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a></p>'
    ) == RIGHTS_UNKNOWN
    separate = photo + "<p>Licensed under CC BY 4.0.</p>"
    assert rights_from_page(separate) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


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
        "<noscript>Licensed under CC BY 4.0.</noscript><p>All rights reserved.</p>",
    ]
    for html in hidden:
        assert rights_from_page(html) == RIGHTS_UNKNOWN
    visible_link = '<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">'
    assert rights_from_page(visible_link) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_publication_dates_ignore_updated_modified_and_copyright_years():
    stated = (
        '<time datetime="2026-05-20T00:00:00Z">May 20, 2026</time>'
        '<meta property="article:modified_time" content="2026-10-01T00:00:00Z">'
        '<meta property="og:updated_time" content="2026-11-01T00:00:00Z">'
        "<p>© 2024 Idiap Research Institute</p>"
    )
    assert publication_date_from_page(stated) == "2026-05-20"
    listing = (
        '<time datetime="2024-09-04">September 4, 2024</time>'
        '<time datetime="2025-07-03">July 3, 2025</time>'
    )
    assert publication_date_from_page(listing) == UNKNOWN_DATE
    updated = "<p>Last update: May 2026.</p><p>Updated 2024-05-01</p><p>© 2020</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    modified = '<meta property="article:modified_time" content="2024-04-18T14:43:38.000Z">'
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    meta_only = '<meta property="article:published_time" content="2026-05-20T00:00:00.000Z">'
    assert publication_date_from_page(meta_only) == "2026-05-20"
    script_date = '<script type="application/ld+json">{"datePublished":"2024-09-04"}</script><p>No date.</p>'
    assert publication_date_from_page(script_date) == UNKNOWN_DATE
    updated_time = '<time class="updated" datetime="2024-05-01">Updated May 1, 2024</time>'
    assert publication_date_from_page(updated_time) == UNKNOWN_DATE
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2026-05-20") == "2026-05-20"
    with pytest.raises(CatalogError, match="date"):
        validate_date("20 May 2026")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    record = page_record(
        _page("Annual Report 2025", published="2026-05-20T00:00:00.000Z"),
        page_url=SAMPLE_URL,
    )
    assert record["title"] == "Annual Report 2025"
    assert record["publisher"] == PUBLISHER
    assert record["canonical_url"] == SAMPLE_URL
    assert record["date"] == "2026-05-20"
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    stored = json.dumps(record)
    assert BODY not in stored
    assert "Jane Doe" not in stored
    assert "example.com" not in stored
    assert "0.42" not in stored


def test_a_different_canonical_link_does_not_replace_the_live_url():
    html = _page("Machine Learning")
    record = page_record(html, page_url=APEX_URL)
    assert record["canonical_url"] == APEX_URL
    assert "example.com" not in record["canonical_url"]


def test_a_person_is_not_the_publisher():
    html = """<!doctype html><html><head>
<meta property="og:title" content="A note">
<meta name="author" content="Jane Doe">
</head><body><p>Jane Doe wrote this note.</p></body></html>"""
    with pytest.raises(CatalogError, match="publisher"):
        page_record(html, page_url=SAMPLE_URL)


def test_host_limits_reject_other_hosts_and_person_or_login_paths():
    accepted = (
        "https://www.idiap.ch/en/news",
        "https://www.idiap.ch/en/research/groups/machine-learning",
        "https://www.idiap.ch/en/projects/2000lakes",
        "https://idiap.ch/en/research",
        "https://idiap.ch/en/news/annual-report-2025",
    )
    for url in accepted:
        assert validate_canonical_url(url) == url
        assert official_idiap_host(url.split("/")[2])
    rejected = (
        "https://publications.idiap.ch/publications/show/1",
        "https://cdn.idiap.ch/en/news",
        "https://blog.idiap.ch/en/news",
        "https://example.com/en/news",
        "http://www.idiap.ch/en/news",
        "https://www.idiap.ch/en/people",
        "https://www.idiap.ch/en/people/8",
        "https://www.idiap.ch/en/news/jane-doe/profile",
        "https://www.idiap.ch/login",
        "https://www.idiap.ch/en/news/paper.pdf",
        "https://www.idiap.ch/api/pages",
        "https://www.idiap.ch/en/about-us",
        "https://user:pass@www.idiap.ch/en/news",
        "https://www.idiap.ch/en/news?ref=1",
        "https://www.idiap.ch/en/news#top",
        "https://127.0.0.1/en/news",
        "https://www.idiap.ch:443/en/news",
        "https://www.idiap.ch/en/publications/",
    )
    for url in rejected:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    assert official_idiap_host("www.idiap.ch")
    assert official_idiap_host("idiap.ch")
    assert not official_idiap_host("publications.idiap.ch")
    assert not official_idiap_host("localhost")


def test_robots_allows_public_paths_and_blocks_challenges():
    assert robots_allows(ROBOTS, "/en/news")
    assert robots_allows(ROBOTS, "/en/research/groups/machine-learning")
    assert robots_allows(ROBOTS, "/en/projects/2000lakes")
    assert not robots_allows(ROBOTS, "/api/")
    assert not robots_allows(ROBOTS, "/api/pages")
    assert robots_allows("", "/en/news")
    assert robots_allows("<!doctype html><html><title>404</title></html>", "/en/news")
    challenge = "<html><title>Just a moment...</title><p>challenge-platform</p></html>"
    assert not robots_allows(challenge, "/en/news")
    assert not robots_allows(challenge, "/en/publications")


def test_challenge_login_and_off_host_responses_are_not_stored():
    cloudflare = (
        "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
        "<body><p>Enable JavaScript and cookies to continue.</p>"
        "<p>challenge-platform</p></body></html>"
    )
    assert is_challenge_page(cloudflare)
    assert (
        record_from_response(
            status=200,
            content_type="text/html",
            page_html=cloudflare,
            page_url=SAMPLE_URL,
        )
        is None
    )
    assert (
        record_from_response(
            status=403,
            content_type="text/html",
            page_html=_page("Blocked"),
            page_url=SAMPLE_URL,
            headers={"Server": "AkamaiGHost"},
        )
        is None
    )
    assert (
        record_from_response(
            status=202,
            content_type="text/html",
            page_html=_page("Waiting"),
            page_url=SAMPLE_URL,
        )
        is None
    )
    login = "<html><head><title>Log in</title></head><body><input type='password'></body></html>"
    assert (
        record_from_response(
            status=200,
            content_type="text/html",
            page_html=login,
            page_url="https://www.idiap.ch/en/news",
        )
        is None
    )
    assert (
        record_from_response(
            status=200,
            content_type="application/pdf",
            page_html=_page("Report"),
            page_url=SAMPLE_URL,
        )
        is None
    )
    assert confirmed_fetch_url(SAMPLE_URL, "https://publications.idiap.ch/en/news") is None
    assert confirmed_fetch_url(SAMPLE_URL, "https://www.idiap.ch/en/research") is None
    assert confirmed_fetch_url(SAMPLE_URL, SAMPLE_URL) == SAMPLE_URL
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=utf-8",
        page_html=_page("Annual Report 2025", published="2026-05-20T00:00:00Z"),
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
    )
    assert stored is not None
    assert stored["canonical_url"] == SAMPLE_URL
    assert set(stored) == {"title", "publisher", "canonical_url", "date", "rights"}


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = load_catalog()
    broken = json.loads(json.dumps(document))
    broken["entries"][0]["abstract"] = "stored body"
    with pytest.raises(CatalogError, match="abstract"):
        validate_catalog(broken)
    broken = json.loads(json.dumps(document))
    broken["entries"][0]["rights"] = "cc-by-nc"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(broken)
    broken = json.loads(json.dumps(document))
    broken["entries"][0]["probability"] = 0.2
    with pytest.raises(CatalogError, match="probability"):
        validate_catalog(broken)
    broken = json.loads(json.dumps(document))
    broken["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(broken)
    empty = {
        "catalog_id": CATALOG_ID,
        "description": CATALOG_DESCRIPTION,
        "runner_wired": False,
        "entries": [],
    }
    assert validate_catalog(empty)["entries"] == []


def test_catalog_is_not_wired_into_belief_collection():
    module = Path(idiap.__file__).read_text(encoding="utf-8")
    tree = ast.parse(module)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
    assert "urllib" not in imported
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "pdoom_pipeline.belief.collect" not in imported
    assert not re.search(r"(?m)^\s*(?:import|from)\s+requests\b", module)
    assert "hostname_is_blocked" in module
    assert "runner_wired = True" not in module
    assert RUNNER_WIRED is False

    root = Path(__file__).resolve().parents[1]
    init = (root / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py").read_text(encoding="utf-8")
    assert init.strip() == '"""Package marker."""'
    assert "idiap" not in init
    collectors = (root / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py").read_text(encoding="utf-8")
    assert collectors.strip() == '"""Package marker."""'
    assert "idiap" not in collectors
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "idiap_pages" not in text
        assert "catalogs.idiap" not in text
    collect = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in collect
