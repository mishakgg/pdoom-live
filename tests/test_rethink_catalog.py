"""Offline checks for the Rethink Priorities AI page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import re
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.rethink as rethink
from pdoom_pipeline.catalogs.rethink import (
    CATALOG_ID,
    PUBLISHER,
    RIGHTS_CREATIVE_COMMONS,
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
    official_rethink_host,
    page_record,
    record_from_response,
    rights_from_page,
    validate_canonical_url,
    validate_catalog,
    validate_date,
    validate_entry,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_URL = "https://rethinkpriorities.org/research-area/ai-safety-bounties/"
BODY = "FULL PAGE TEXT that must not be stored. " * 30

EXPECTED = [
    (
        'An examination of Metaculus’ resolved AI predictions and their implications for AI timelines',
        'https://rethinkpriorities.org/research-area/an-examination-of-metaculus-resolved-ai-predictions/',
        '2021-07-20',
    ),
    (
        'Using artificial intelligence (machine vision) to increase the effectiveness of human-wildlife conflict mitigations could benefit WAW',
        'https://rethinkpriorities.org/research-area/ai-for-human-wildlife-conflict-mitigations/',
        '2022-10-29',
    ),
    (
        'Background for “Understanding the diffusion of large language models”',
        'https://rethinkpriorities.org/research-area/background-for-understanding-the-diffusion-of-large-language-models/',
        '2022-12-21',
    ),
    (
        'Conclusion and Bibliography for “Understanding the diffusion of large language models”',
        'https://rethinkpriorities.org/research-area/conclusion-and-bibliography-for-understanding-the-diffusion-of-large-language-models/',
        '2022-12-21',
    ),
    (
        'Drivers of large language model diffusion: incremental research, publicity, and cascades',
        'https://rethinkpriorities.org/research-area/drivers-of-large-language-model-diffusion-incremental-research-publicity-and-cascades/',
        '2022-12-21',
    ),
    (
        'GPT-3-like models are now much easier to access and deploy than to develop',
        'https://rethinkpriorities.org/research-area/gpt-3-like-models-are-now-much-easier-to-access-and-deploy-than-to-develop/',
        '2022-12-21',
    ),
    (
        'Implications of large language model diffusion for AI governance',
        'https://rethinkpriorities.org/research-area/implications-of-large-language-model-diffusion-for-ai-governance/',
        '2022-12-21',
    ),
    (
        'Publication decisions for large language models, and their impacts',
        'https://rethinkpriorities.org/research-area/publication-decisions-for-large-language-models-and-their-impacts/',
        '2022-12-21',
    ),
    (
        'Questions for further investigation of AI diffusion',
        'https://rethinkpriorities.org/research-area/questions-for-further-investigation-of-ai-diffusion/',
        '2022-12-21',
    ),
    (
        'The replication and emulation of GPT-3',
        'https://rethinkpriorities.org/research-area/the-replication-and-emulation-of-gpt-3/',
        '2022-12-21',
    ),
    (
        'Understanding the diffusion of large language models: summary',
        'https://rethinkpriorities.org/research-area/understanding-the-diffusion-of-large-language-models-summary/',
        '2022-12-21',
    ),
    (
        'Survey on intermediate goals in AI governance',
        'https://rethinkpriorities.org/research-area/survey-on-intermediate-goals-in-ai-governance/',
        '2023-03-17',
    ),
    (
        'Prospects for AI safety agreements between countries',
        'https://rethinkpriorities.org/research-area/prospects-for-ai-safety-agreements-between-countries/',
        '2023-04-14',
    ),
    (
        'US public opinion of AI policy and risk',
        'https://rethinkpriorities.org/research-area/us-public-opinion-of-ai-policy-and-risk/',
        '2023-05-12',
    ),
    (
        'US public perception of CAIS statement and the risk of extinction',
        'https://rethinkpriorities.org/research-area/us-public-perception-of-cais-statement-and-the-risk-of-extinction/',
        '2023-06-22',
    ),
    (
        'AI Safety Bounties',
        'https://rethinkpriorities.org/research-area/ai-safety-bounties/',
        '2023-08-10',
    ),
    (
        'Why some people disagree with the CAIS statement on AI',
        'https://rethinkpriorities.org/research-area/why-some-people-disagree-with-the-cais-statement-on-ai/',
        '2023-08-15',
    ),
    (
        'New surveys find that most Americans support AI regulation, believing that AI risk mitigation is a global priority',
        'https://rethinkpriorities.org/new-surveys-find-that-most-americans-support-ai-regulation-believing-that-ai-risk-mitigation-is-a-global-priority/',
        '2023-09-28',
    ),
    (
        'Introducing the Institute for AI Policy and Strategy',
        'https://rethinkpriorities.org/introducing-the-institute-for-ai-policy-and-strategy/',
        '2023-10-18',
    ),
    (
        'Rethink Priorities’ Digital Consciousness Project Announcement',
        'https://rethinkpriorities.org/digital-consciousness/',
        '2024-07-05',
    ),
    (
        'Risk Alignment in Agentic AI Systems',
        'https://rethinkpriorities.org/research-area/risk-alignment-in-agentic-ai-systems/',
        '2024-10-01',
    ),
    (
        'Strategic Directions for a Digital Consciousness Model',
        'https://rethinkpriorities.org/research-area/strategic-directions-for-a-digital-consciousness-model/',
        '2024-12-10',
    ),
    (
        'The usage of LLMs in the US general public',
        'https://rethinkpriorities.org/research-area/estimating-the-usage-and-utility-of-llms-in-the-us-general-public/',
        '2025-07-22',
    ),
    (
        'LLM use in the workplace - interviews with power users',
        'https://rethinkpriorities.org/research-area/llm-use-in-the-workplace/',
        '2025-07-22',
    ),
    (
        'Adoption of LLMs among U.S. tech workers',
        'https://rethinkpriorities.org/research-area/adoption-llms-tech-workers/',
        '2025-07-23',
    ),
    (
        'How AI is affecting farmed aquatic animals. Part 1: Innovation',
        'https://rethinkpriorities.org/research-area/how-ai-is-affecting-farmed-aquatic-animals-1/',
        '2025-12-17',
    ),
    (
        'AI for health: landscape review',
        'https://rethinkpriorities.org/research-area/ai-for-health/',
        '2026-02-13',
    ),
    (
        'Initial results of the Digital Consciousness Model',
        'https://rethinkpriorities.org/research-area/initial-results-of-the-digital-consciousness-model/',
        '2026-04-28',
    ),
    (
        'What Do Increasing AI Capabilities Mean For Global Health and Development?',
        'https://rethinkpriorities.org/research-area/what-do-increasing-ai-capabilities-mean-for-global-health-and-development/',
        '2026-06-02',
    ),
    (
        'AI and Cultivated Meat',
        'https://rethinkpriorities.org/research-area/ai-and-cultivated-meat/',
        '2026-06-09',
    ),
    (
        'How AI is Affecting Farmed Aquatic Animals. Part 2: Deployment',
        'https://rethinkpriorities.org/research-area/how-ai-is-affecting-farmed-aquatic-animals-2/',
        '2026-06-18',
    ),
    (
        'Enabling AI for good: Challenges and Opportunities',
        'https://rethinkpriorities.org/research-area/enabling-ai-for-good-challenges-and-opportunities/',
        '2026-06-30',
    ),
    (
        'How AI Is Affecting Farmed Aquatic Animals. Part 3: Welfare Impacts',
        'https://rethinkpriorities.org/research-area/how-ai-is-affecting-farmed-aquatic-animals-3/',
        '2026-08-31',
    ),
]


def _page(title: str, *, published: str | None = None, footer: str = "All rights reserved.") -> str:
    published_tag = (
        f'<meta property="article:published_time" content="{published}">' if published else ""
    )
    return (
        "<html><head>"
        f'<meta property="og:title" content="{title}">'
        '<meta property="og:site_name" content="Rethink Priorities">'
        f"{published_tag}"
        f'<link rel="canonical" href="https://example.com/not-rethink/">'
        "</head><body><article><p>"
        f"{BODY}"
        f"</p></article><footer>{footer}</footer></body></html>"
    )


def test_runner_wired_is_false():
    catalog = load_catalog()
    assert catalog["catalog_id"] == CATALOG_ID
    assert catalog["runner_wired"] is False
    assert RUNNER_WIRED is False
    assert rethink.RUNNER_WIRED is False
    source = inspect_source()
    assert "RUNNER_WIRED = True" not in source
    assert "runner_wired = True" not in source


def test_catalog_rows_match_confirmed_rethink_pages():
    catalog = load_catalog()
    assert "rethinkpriorities.org" in catalog["description"]
    assert "unknown" in catalog["description"]
    entries = catalog["entries"]
    assert len(entries) == len(EXPECTED) == 33
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, url, published = expected
        assert entry["title"] == title
        assert entry["publisher"] == PUBLISHER
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["rights"] == RIGHTS_UNKNOWN
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert official_rethink_host(url.split("/")[2])
        assert not url.lower().endswith(".pdf")
    dates = [entry["date"] for entry in entries]
    assert dates == sorted(dates)
    urls = [entry["canonical_url"] for entry in entries]
    assert urls == sorted(urls, key=lambda url: (dates[urls.index(url)], url))
    assert RIGHTS_CREATIVE_COMMONS not in {entry["rights"] for entry in entries}
    assert "https://rethinkpriorities.org/research-area/ai-safety-bounties/" in urls


def test_load_catalog_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    catalog = load_catalog()
    assert catalog["runner_wired"] is False
    assert len(catalog["entries"]) == 33
    source = inspect_source()
    assert "pdoom_pipeline.fetch" not in source
    assert "pdoom_pipeline.belief" not in source
    assert "urllib" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "collect_beliefs" not in source


def test_catalog_file_stores_no_body_or_probability():
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<p>" not in raw
    assert "<html" not in raw.casefold()
    assert "doctype" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert "abstract" not in raw.casefold()
    assert "probability" not in raw.casefold()
    assert re.search(r"\bp\(doom\)\s*[:=]\s*\d", raw, re.I) is None
    document = json.loads(raw)
    for entry in document["entries"]:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        for value in entry.values():
            assert isinstance(value, str)
            assert len(value) < 400
        dumped = json.dumps(entry)
        assert BODY not in dumped
        assert "quote" not in entry
        assert "chart" not in entry


def test_sole_nc_and_nd_stay_unknown():
    samples = {
        "nc": "<p>Licensed under CC BY-NC 4.0.</p>",
        "nd": "<p>Licensed under CC BY-ND 4.0.</p>",
        "nc-sa": "<p>Licensed under CC BY-NC-SA 4.0.</p>",
        "nc-nd": "<p>Licensed under CC BY-NC-ND 4.0.</p>",
        "nc-url": '<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>',
        "nd-url": '<a href="https://creativecommons.org/licenses/by-nd/4.0/">licence</a>',
        "nc-sa-url": '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">licence</a>',
        "nc-nd-url": '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">licence</a>',
        "noncommercial": "<p>Creative Commons Attribution-NonCommercial 4.0.</p>",
        "noderivatives": "<p>Creative Commons Attribution-NoDerivatives 4.0.</p>",
    }
    for name, page in samples.items():
        assert rights_from_page(page) == RIGHTS_UNKNOWN, name
        assert rights_from_page(page) != RIGHTS_CREATIVE_COMMONS


def test_anchor_text_cc_by_on_a_by_nc_url_stays_unknown():
    page = '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>'
    assert rights_from_page(page) == RIGHTS_UNKNOWN
    by_nd = '<a href="https://creativecommons.org/licenses/by-nd/4.0/deed">CC BY</a>'
    assert rights_from_page(by_nd) == RIGHTS_UNKNOWN
    by_nc_nd = '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY</a>'
    assert rights_from_page(by_nc_nd) == RIGHTS_UNKNOWN
    bare = '<a href="https://creativecommons.org/licenses/">CC BY</a>'
    assert rights_from_page(bare) == RIGHTS_UNKNOWN
    real_by = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
    assert rights_from_page(real_by) == RIGHTS_CREATIVE_COMMONS
    hyphen = "<p>CC BY-NC</p>"
    assert rights_from_page(hyphen) == RIGHTS_UNKNOWN
    stated = "<p>Licensed under CC BY 4.0.</p>"
    assert rights_from_page(stated) == RIGHTS_CREATIVE_COMMONS


def test_mixed_permissive_and_restricted_stays_unknown():
    text = "<p>Licensed under CC BY 4.0. Also available as CC BY-NC 4.0.</p>"
    assert rights_from_page(text) == RIGHTS_UNKNOWN
    links = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-ND</a>'
    )
    assert rights_from_page(links) == RIGHTS_UNKNOWN
    zero_and_nd = "<p>CC0 and CC BY-ND 4.0.</p>"
    assert rights_from_page(zero_and_nd) == RIGHTS_UNKNOWN
    sa_and_nc = "<p>Licensed under CC BY-SA 4.0 and CC BY-NC-SA 4.0.</p>"
    assert rights_from_page(sa_and_nc) == RIGHTS_UNKNOWN


def test_a_public_domain_mark_is_not_cc0():
    mark_url = '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>'
    assert rights_from_page(mark_url) == RIGHTS_UNKNOWN
    mark_text = "<p>Public Domain Mark 1.0</p>"
    assert rights_from_page(mark_text) == RIGHTS_UNKNOWN
    public_domain = "<p>This work is in the public domain.</p>"
    assert rights_from_page(public_domain) == RIGHTS_UNKNOWN
    beside_cc0 = (
        '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>'
    )
    assert rights_from_page(beside_cc0) == RIGHTS_UNKNOWN
    cc0 = "<p>This work is licensed under CC0.</p>"
    assert rights_from_page(cc0) == RIGHTS_CREATIVE_COMMONS
    zero = '<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>'
    assert rights_from_page(zero) == RIGHTS_CREATIVE_COMMONS


def test_public_page_copyright_and_terms_are_not_a_licence():
    public = "<p>This page is public.</p>"
    reserved = "<p>Copyright 2024. All rights reserved.</p>"
    terms = '<p>See the <a href="https://rethinkpriorities.org/privacy-policy/">terms</a>.</p>'
    citation = "<p>CC-BY Jaime Sevilla and colleagues.</p>"
    hidden = "<script>Licensed under CC BY 4.0.</script><p>All rights reserved.</p>"
    assert rights_from_page(public) == RIGHTS_UNKNOWN
    assert rights_from_page(reserved) == RIGHTS_UNKNOWN
    assert rights_from_page(terms) == RIGHTS_UNKNOWN
    assert rights_from_page(citation) == RIGHTS_UNKNOWN
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN
    assert date_from_page(reserved) == UNKNOWN_DATE
    government = "<p>Available under the Open Government Licence v3.0.</p>"
    assert rights_from_page(government) == RIGHTS_UK_OGL
    american = "<p>Licensed under the Open Government License v3.0.</p>"
    assert rights_from_page(american) == RIGHTS_UNKNOWN
    body_only = "<p>This is a work of the United States Government.</p>"
    assert rights_from_page(body_only) == RIGHTS_UNKNOWN
    rights_field = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(rights_field) == RIGHTS_US_GOVERNMENT_WORK
    negated = '<meta name="rights" content="Not a work of the United States Government.">'
    assert rights_from_page(negated) == RIGHTS_UNKNOWN


def test_a_challenge_or_non_html_response_is_not_stored():
    cloudflare = (
        "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
        "<body><h1>Performing security verification</h1>"
        "<p>Enable JavaScript and cookies to continue.</p>"
        "<p>challenge-platform cf-browser-verification</p></body></html>"
    )
    siteground = (
        "<html><head><title>Please wait</title></head>"
        "<body><p>SiteGround captcha</p><form action='/.well-known/sgcaptcha/'></form></body></html>"
    )
    akamai = (
        "<html><head><title>Access Denied</title></head>"
        "<body>You don't have permission to access. Reference #18. errors.edgesuite.net AkamaiGHost</body></html>"
    )
    robot = (
        "<html><head><title>Verify</title></head>"
        "<body><h1>Are you a robot</h1><p>Verify you are human.</p></body></html>"
    )
    real = _page("AI Safety Bounties", published="2023-08-10T16:09:08+00:00")
    assert is_challenge_page(cloudflare)
    assert is_challenge_page(siteground)
    assert is_challenge_page(akamai)
    assert is_challenge_page(robot)
    for page in (cloudflare, siteground, akamai, robot):
        assert (
            record_from_response(
                status=200,
                content_type="text/html; charset=UTF-8",
                page_html=page,
                page_url=SAMPLE_URL,
            )
            is None
        )
    assert (
        record_from_response(
            status=202,
            content_type="text/html; charset=UTF-8",
            page_html=real,
            page_url=SAMPLE_URL,
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
            page_html=real,
            page_url=SAMPLE_URL,
            headers={"CF-Mitigated": "challenge"},
        )
        is None
    )
    assert (
        record_from_response(
            status=200,
            content_type="text/html",
            page_html=real,
            page_url=SAMPLE_URL,
            final_url="https://example.com/ai-safety-bounties/",
        )
        is None
    )
    with pytest.raises(CatalogError, match="challenge page is not stored"):
        page_record(cloudflare, page_url=SAMPLE_URL)
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=real,
        page_url=SAMPLE_URL,
    )
    assert stored is not None
    assert stored["title"] == "AI Safety Bounties"
    assert stored["canonical_url"] == SAMPLE_URL
    assert BODY not in json.dumps(stored)
    assert "Just a moment" not in json.dumps(load_catalog())


def test_updated_modified_and_copyright_years_are_not_publication_dates():
    assert date_from_page("<p>No date on this page.</p>") == UNKNOWN_DATE
    assert date_from_page("<p>Copyright 2024. Updated 2026. Modified 2024-11-06.</p>") == UNKNOWN_DATE
    modified = (
        '<meta property="article:modified_time" content="2024-11-06T16:11:13+00:00">'
        '<meta property="og:updated_time" content="2026-04-07T12:35:38+00:00">'
        '<script type="application/ld+json">{"dateModified":"2024-11-06T16:11:13+00:00"}</script>'
    )
    assert date_from_page(modified) == UNKNOWN_DATE
    published = modified + (
        '<script type="application/ld+json">'
        '{"dateModified":"2024-11-06T16:11:13+00:00","datePublished":"2023-08-10T16:09:08+00:00"}'
        "</script>"
    )
    assert date_from_page(published) == "2023-08-10"
    assert date_from_page('<meta property="article:published_time" content="2023-05-12T00:00:00+00:00">') == "2023-05-12"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    with pytest.raises(CatalogError):
        validate_date("10 August 2023")
    with pytest.raises(CatalogError):
        validate_date("2023-02-31")


def test_page_record_keeps_metadata_and_not_the_body():
    record = page_record(
        _page("AI Safety Bounties", published="2023-08-10T16:09:08+00:00"),
        page_url=SAMPLE_URL,
    )
    assert record == {
        "title": "AI Safety Bounties",
        "publisher": PUBLISHER,
        "canonical_url": SAMPLE_URL,
        "date": "2023-08-10",
        "rights": RIGHTS_UNKNOWN,
    }
    assert BODY not in json.dumps(record)
    assert "example.com" not in record["canonical_url"]


def test_an_empty_catalog_is_valid_when_no_page_was_stored():
    document = {
        "catalog_id": CATALOG_ID,
        "description": "No confirmed HTML page was stored. runner_wired is false.",
        "runner_wired": False,
        "entries": [],
    }
    assert validate_catalog(document)["entries"] == []


def test_non_rethink_urls_are_rejected():
    rejected = [
        "https://example.com/research-area/ai-safety-bounties/",
        "https://www.rethinkpriorities.org/research-area/ai-safety-bounties/",
        "https://rethinkpriorities.org.example/research-area/ai-safety-bounties/",
        "http://rethinkpriorities.org/research-area/ai-safety-bounties/",
        "https://user:pass@rethinkpriorities.org/research-area/ai-safety-bounties/",
        "https://rethinkpriorities.org/research-area/ai-safety-bounties/?utm_source=x",
        "https://rethinkpriorities.org/research-area/ai-safety-bounties/#section",
        "https://rethinkpriorities.org/research-area/ai-safety-bounties.pdf",
        "https://rethinkpriorities.org/team-member/example/",
        "https://rethinkpriorities.org/wp-json/wp/v2/pages",
        "https://127.0.0.1/research-area/ai-safety-bounties/",
        "https://rethinkpriorities.org/",
    ]
    for url in rejected:
        with pytest.raises(CatalogError):
            validate_canonical_url(url)
    assert official_rethink_host("rethinkpriorities.org")
    assert not official_rethink_host("www.rethinkpriorities.org")
    assert not official_rethink_host("127.0.0.1")
    assert validate_canonical_url(SAMPLE_URL) == SAMPLE_URL


def test_validator_rejects_body_storage_bad_rights_and_a_wired_runner():
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = RIGHTS_CREATIVE_COMMONS
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = "all_rights_reserved"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = "full page"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["pdf"] = "https://rethinkpriorities.org/file.pdf"
    with pytest.raises(CatalogError, match="page text"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["probability"] = 0.5
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

    document = copy.deepcopy(load_catalog())
    document["entries"][0], document["entries"][1] = document["entries"][1], document["entries"][0]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)

    missing = copy.deepcopy(load_catalog()["entries"][0])
    del missing["publisher"]
    with pytest.raises(CatalogError):
        validate_entry(missing)


def test_catalog_is_not_wired_into_belief_collection():
    source = inspect_source()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
                imported.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(node.module.split("."))
    assert "urllib" not in imported
    assert "requests" not in imported
    assert "httpx" not in imported
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "hostname_is_blocked" in source
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/catalogs/__init__.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "rethink" not in text
    init = (ROOT / "pipeline/pdoom_pipeline/catalogs/__init__.py").read_text(encoding="utf-8")
    assert ast.get_docstring(ast.parse(init)) == "Package marker."


def inspect_source() -> str:
    return (ROOT / "pipeline/pdoom_pipeline/catalogs/rethink.py").read_text(encoding="utf-8")
