"""Offline checks for the Brookings artificial-intelligence page catalog. No network."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.brookings_ai as brookings_ai
from pdoom_pipeline.catalogs.brookings_ai import (
    OFFICIAL_HOST,
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
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    is_challenge_page,
    is_official_host,
    is_section_path,
    load_catalog,
    page_record,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    robots_allows_path,
    title_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
    validate_entry,
)

TOPIC_URL = "https://www.brookings.edu/topics/artificial-intelligence/"
ARTICLE_URL = "https://www.brookings.edu/articles/in-ai-evaluation-access-is-not-evidence/"
ENTRY_FIELDS = {"title", "publisher", "canonical_url", "date", "rights"}
BODY = "Full page body that must not be stored. " * 30
ROBOTS = """
User-agent: *
Disallow: /?*qry
Disallow: /?*topics
Disallow: /*?s=
Disallow: /search/
Disallow: /wp-content/uploads/2026/09/GS_20260921_TechTankPodcast_AI.pdf

User-agent: *
Disallow:
"""
REJECTED_URLS = [
    "https://brookings.edu/topics/artificial-intelligence/",
    "https://foreignpolicy.com/articles/ai-risk/",
    "https://www.nytimes.com/2026/09/17/opinion/ai-china-america-risk.html",
    "https://www.hamiltonproject.org/event/understanding-ais-impact-on-the-labor-market/",
    "https://www.brookings.edu.example/articles/ai-risk/",
    "https://example.com/topics/artificial-intelligence/",
    "http://www.brookings.edu/topics/artificial-intelligence/",
    "https://user:pass@www.brookings.edu/topics/artificial-intelligence/",
    "https://www.brookings.edu/topics/artificial-intelligence/?utm_source=x",
    "https://www.brookings.edu/articles/ai-risk/?s=ai",
    "https://www.brookings.edu/topics/artificial-intelligence/#section",
    "https://www.brookings.edu:443/topics/artificial-intelligence/",
    "https://www.brookings.edu/",
    "https://www.brookings.edu/topics/health-care-2/",
    "https://www.brookings.edu/about-us/",
    "https://www.brookings.edu/people/nicol-turner-lee/",
    "https://www.brookings.edu/search/",
    "https://www.brookings.edu/wp-login.php",
    "https://www.brookings.edu/wp-admin/",
    "https://www.brookings.edu/articles/ai-risk.pdf",
    "https://127.0.0.1/topics/artificial-intelligence/",
    "https://169.254.169.254/topics/artificial-intelligence/",
]
OMITTED_HOSTS = (
    "foreignpolicy.com",
    "www.foreignaffairs.com",
    "www.nytimes.com",
    "www.hamiltonproject.org",
    "www.cfr.org",
    "www.theatlantic.com",
    "hbr.org",
    "www.wired.com",
    "techcrunch.com",
    "doi.org",
    "home.treasury.gov",
)


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def rejected(*_args, **_kwargs):
        raise AssertionError("catalog test tried to use the network")

    monkeypatch.setattr(socket, "create_connection", rejected)
    monkeypatch.setattr(socket, "socket", rejected)
    monkeypatch.setattr(socket, "getaddrinfo", rejected)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    _block_network(monkeypatch)


def _entry(url: str = ARTICLE_URL, published: str = "2026-09-24", title: str = "In AI evaluation, access is not evidence") -> dict:
    return {
        "title": title,
        "publisher": PUBLISHER,
        "canonical_url": url,
        "date": published,
        "rights": RIGHTS_UNKNOWN,
    }


def _page(title: str, url: str = ARTICLE_URL, *, published: str = "", body: str = "This page is public.") -> str:
    published_meta = (
        f'<meta property="article:published_time" content="{published}" />' if published else ""
    )
    return f"""
    <html><head>
    <title>{title} | Brookings</title>
    <meta property="og:title" content="{title} | Brookings" />
    <meta property="og:site_name" content="Brookings" />
    <link rel="canonical" href="{url}" />
    {published_meta}
    </head><body>
    <h1>{title}</h1>
    <p>{body}</p>
    <footer>Copyright 2026 The Brookings Institution. All rights reserved.
    <a href="https://www.brookings.edu/terms-of-use/">Terms of Use</a></footer>
    </body></html>
    """


def test_catalog_rows_are_brookings_section_metadata():
    catalog = load_catalog()
    assert catalog["catalog_id"] == "brookings_ai_pages"
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert "www.brookings.edu" in catalog["description"]
    assert "artificial-intelligence" in catalog["description"]
    assert "runner_wired is false" in catalog["description"]
    assert "creative_commons_attribution" in catalog["description"]
    rights_counts: dict[str, int] = {}
    for entry in catalog["entries"]:
        validate_entry(entry)
        assert set(entry) == ENTRY_FIELDS
        assert entry["publisher"] == PUBLISHER
        assert entry["canonical_url"].startswith(f"https://{OFFICIAL_HOST}/")
        assert is_section_path(entry["canonical_url"].split(OFFICIAL_HOST, 1)[1])
        rights_counts[entry["rights"]] = rights_counts.get(entry["rights"], 0) + 1
    ordered = sorted(
        catalog["entries"],
        key=lambda entry: (
            "9999-99-99" if entry["date"] == UNKNOWN_DATE else entry["date"],
            entry["canonical_url"],
        ),
    )
    assert [entry["canonical_url"] for entry in catalog["entries"]] == [entry["canonical_url"] for entry in ordered]
    assert sum(rights_counts.values()) == len(catalog["entries"])
    assert set(rights_counts) <= {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_ATTRIBUTION,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_UK_OGL,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
    by_url = {entry["canonical_url"]: entry for entry in catalog["entries"]}
    assert by_url[TOPIC_URL]["title"] == "Artificial Intelligence"
    assert by_url[TOPIC_URL]["date"] == "2023-05-29"
    assert by_url[TOPIC_URL]["rights"] == RIGHTS_UNKNOWN
    assert by_url[ARTICLE_URL]["title"] == "In AI evaluation, access is not evidence"
    assert by_url[ARTICLE_URL]["date"] == "2026-09-24"
    assert by_url[ARTICLE_URL]["rights"] == RIGHTS_UNKNOWN


def test_load_catalog_does_not_use_the_network():
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    source = inspect.getsource(brookings_ai)
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
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "pdoom_pipeline.belief.collect" not in imported
    assert "import requests" not in source
    assert "runner_wired = True" not in source
    root = Path(__file__).resolve().parents[1]
    init = (root / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py").read_text(encoding="utf-8")
    assert init.strip() == '"""Package marker."""'
    assert "brookings" not in init
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "brookings_ai" not in text
        assert "brookings_ai_pages" not in text


def test_catalog_file_stores_no_page_body_or_off_host_page():
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<p>" not in raw
    assert "<html" not in raw.casefold()
    assert "doctype" not in raw.casefold()
    assert "p(doom)" not in raw.casefold()
    for host in OMITTED_HOSTS:
        assert f"https://{host}" not in raw
    document = json.loads(raw)
    assert set(document) == {"catalog_id", "description", "runner_wired", "entries"}
    assert document["entries"]
    assert len(document["description"]) <= 800


def test_sole_restricted_deeds_keep_their_tokens():
    assert rights_from_page("<p>Licensed under CC BY-NC 4.0.</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Licensed under CC BY-ND 4.0.</p>") == RIGHTS_CC_BY_ND
    assert rights_from_page("<p>Licensed under CC BY-NC-SA 4.0.</p>") == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>Licensed under CC BY-NC-ND 4.0.</p>") == RIGHTS_CC_BY_NC_ND
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial 4.0.</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Creative Commons Attribution-NoDerivatives 4.0.</p>") == RIGHTS_CC_BY_ND
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial-ShareAlike 4.0.</p>") == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial-NoDerivatives 4.0.</p>") == RIGHTS_CC_BY_NC_ND
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY&#45;NC</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY–ND</p>") == RIGHTS_CC_BY_ND


def test_cc_by_alone_is_attribution_and_permissive_mix_is_creative_commons():
    assert rights_from_page("<p>Licensed under CC BY 4.0.</p>") == RIGHTS_CC_ATTRIBUTION
    assert rights_from_page("<p>Creative Commons Attribution 4.0 International License.</p>") == RIGHTS_CC_ATTRIBUTION
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>') == RIGHTS_CC_ATTRIBUTION
    assert rights_from_page("<p>Licensed under CC0 1.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>Licensed under CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>Creative Commons Attribution-ShareAlike 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    mixed_permissive = "<p>Licensed under CC0 and CC BY-SA 4.0.</p>"
    assert rights_from_page(mixed_permissive) == RIGHTS_CREATIVE_COMMONS
    by_and_zero = "<p>Licensed under CC BY 4.0 and CC0.</p>"
    assert rights_from_page(by_and_zero) == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY-NC</p>") != RIGHTS_CC_ATTRIBUTION
    assert rights_from_page("<p>CC BY 4.0</p>") == RIGHTS_CC_ATTRIBUTION


def test_deceptive_anchors_and_generic_licence_urls_stay_unknown():
    for href in (
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "https://creativecommons.org/licenses/by-nd/4.0/",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "https://creativecommons.org/publicdomain/mark/1.0/",
    ):
        assert rights_from_page(f'<a href="{href}">CC BY</a>') == RIGHTS_UNKNOWN
        assert rights_from_page(f'<a href="{href}">CC BY-SA</a>') == RIGHTS_UNKNOWN
    mark = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC0</a>'
    assert rights_from_page(mark) == RIGHTS_UNKNOWN
    generic = '<a href="https://creativecommons.org/licenses/">Creative Commons</a>'
    assert rights_from_page(generic) == RIGHTS_UNKNOWN
    hidden = "<script>Licensed under CC BY 4.0.</script><p>All rights reserved.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_mixed_restricted_permissive_and_software_stay_unknown():
    assert rights_from_page("<p>Licensed under CC BY 4.0 and CC BY-NC 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC0 and CC BY-NC-ND.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Licensed under CC BY 4.0 and the MIT License.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and apache-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache License 2.0 and Mozilla Public License 2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY-NC and CC BY-ND.</p>") == RIGHTS_UNKNOWN


def test_public_domain_mark_terms_and_host_name_stay_unknown():
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>') == RIGHTS_UNKNOWN
    assert rights_from_page("<p>This work is identified with the Public Domain Mark.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<footer>© 2026 The Brookings Institution. All rights reserved.</footer>") == RIGHTS_UNKNOWN
    assert rights_from_page('<p>See the <a href="https://www.brookings.edu/terms-of-use/">terms</a>.</p>') == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Published on www.brookings.edu by the Brookings Institution.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Researchers from Harvard, MIT, and other universities.</p>") == RIGHTS_UNKNOWN


def test_software_tokens_and_uk_ogl_need_their_own_phrases():
    assert rights_from_page("<p>Licensed under the MIT License.</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Licensed under the Apache License 2.0.</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Licensed under the Mozilla Public License 2.0.</p>") == RIGHTS_MPL
    assert rights_from_page("<p>Open Government Licence v3.0.</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>Licensed under the Open Government License v3.0.</p>") == RIGHTS_UNKNOWN
    archives = '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">National Archives</a>'
    assert rights_from_page(archives) == RIGHTS_UNKNOWN
    hidden = "<script>Open Government Licence v3.0</script><p>All rights reserved.</p>"
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_updated_modified_and_copyright_years_are_not_publication_dates():
    assert publication_date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    modified = (
        '<meta property="article:modified_time" content="2026-09-24T17:57:53+00:00" />'
        '<meta property="og:updated_time" content="2026-10-01" />'
        '<script type="application/ld+json">{"dateModified":"2026-09-24","copyrightYear":2026}</script>'
        "<footer>Copyright 2026 The Brookings Institution. Updated August 2024. Last modified 13 June 2024.</footer>"
    )
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    published = modified + '<meta property="article:published_time" content="2026-09-24T16:08:43+00:00" />'
    assert publication_date_from_page(published) == "2026-09-24"
    structured = (
        '<script type="application/ld+json">'
        '{"dateModified":"2026-09-24T17:57:53+00:00","datePublished":"2026-09-24T16:08:43+00:00"}'
        "</script>"
    )
    assert publication_date_from_page(structured) == "2026-09-24"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("24 September 2026")
    with pytest.raises(CatalogError):
        validate_date("2026-02-31")


def test_page_record_keeps_metadata_and_drops_the_body():
    page = _page("In AI evaluation, access is not evidence", published="2026-09-24T16:08:43+00:00", body=BODY)
    page = page.replace(ARTICLE_URL, "https://example.com/not-brookings/", 1)
    record = page_record(page, page_url=ARTICLE_URL)
    assert record == {
        "title": "In AI evaluation, access is not evidence",
        "publisher": PUBLISHER,
        "canonical_url": ARTICLE_URL,
        "date": "2026-09-24",
        "rights": RIGHTS_UNKNOWN,
    }
    assert BODY not in json.dumps(record)
    assert "example.com" not in json.dumps(record)
    assert title_from_page('<meta property="og:title" content="Artificial Intelligence | Brookings" />') == "Artificial Intelligence"


def test_challenge_off_host_and_robots_disallows_are_not_stored():
    cloudflare = (
        "<html><head><title>Just a moment...</title></head>"
        "<body>Checking your browser. cf-mitigated challenge-platform</body></html>"
    )
    assert is_challenge_page(cloudflare)
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=cloudflare,
        page_url=ARTICLE_URL,
        headers={"cf-mitigated": "challenge"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=_page("In AI evaluation, access is not evidence"),
        page_url="https://foreignpolicy.com/articles/ai-risk/",
        final_url="https://foreignpolicy.com/articles/ai-risk/",
    ) is None
    assert record_from_response(
        status=301,
        content_type="text/html",
        page_html="",
        page_url="https://brookings.edu/topics/artificial-intelligence/",
        final_url="https://example.com/away/",
        requested_urls=["https://brookings.edu/topics/artificial-intelligence/", "https://example.com/away/"],
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=_page("In AI evaluation, access is not evidence"),
        page_url="https://www.brookings.edu/search/",
        robots_text=ROBOTS,
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7",
        page_url=ARTICLE_URL,
    ) is None
    assert robots_allows_path(ROBOTS, "/topics/artificial-intelligence/") is True
    assert robots_allows_path(ROBOTS, "/articles/in-ai-evaluation-access-is-not-evidence/") is True
    assert robots_allows_path(ROBOTS, "/search/") is False
    assert robots_allows_path(ROBOTS, "/?topics=artificial-intelligence") is False
    assert robots_allows_path(ROBOTS, "/articles/foo/?s=ai") is False
    assert robots_allows_path(ROBOTS, "/wp-content/uploads/2026/09/GS_20260921_TechTankPodcast_AI.pdf") is False
    assert robots_allows_path("<html><title>Just a moment</title></html>", "/topics/artificial-intelligence/") is False
    with pytest.raises(CatalogError, match="challenge page is not stored"):
        page_record(cloudflare, page_url=ARTICLE_URL)


def test_non_section_urls_are_rejected_and_official_pages_are_accepted():
    for url in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    assert validate_canonical_url(TOPIC_URL) == TOPIC_URL
    assert validate_canonical_url(ARTICLE_URL) == ARTICLE_URL
    assert validate_canonical_url("https://www.brookings.edu/events/how-china-and-the-us-will-regulate-ai-models-for-safety/")
    assert is_official_host(OFFICIAL_HOST)
    assert not is_official_host("brookings.edu")
    assert not is_official_host("foreignpolicy.com")
    assert not is_official_host("127.0.0.1")
    assert is_section_path("/topics/artificial-intelligence/")
    assert not is_section_path("/topics/health-care-2/")
    assert not is_section_path("/wp-login.php")
    assert not is_section_path("/search/")


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"] = [_entry(ARTICLE_URL, "2026-09-24"), _entry(TOPIC_URL, "2023-05-29", "Artificial Intelligence")]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)
    document = {
        "catalog_id": "brookings_ai_pages",
        "description": "Metadata for public Brookings Institution pages in the artificial-intelligence section on www.brookings.edu.",
        "runner_wired": False,
        "entries": [
            _entry(TOPIC_URL, "2023-05-29", "Artificial Intelligence"),
            _entry(ARTICLE_URL, "2026-09-24"),
        ],
    }
    validate_catalog(document)
    document["entries"][1]["rights"] = "all_rights_reserved"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)
    document["entries"][1]["rights"] = RIGHTS_UNKNOWN
    document["entries"][1]["body"] = BODY
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["abstract"] = "a stored abstract"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["quote"] = "a stored quote"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate"):
        validate_catalog(document)
