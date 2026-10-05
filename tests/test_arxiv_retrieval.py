"""Offline checks for one confirmed arXiv AI-risk query.

The fixture is the Atom body from a single export.arxiv.org query:
all:"existential risk" AND all:"artificial intelligence", max_results=5.
That response has descriptive metadata and PDF links, and no item license.
License rules are checked on the same parser with small Atom entries.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from pdoom_pipeline.collectors.arxiv import METADATA_LICENSE_URL, API, ArxivCollector
from pdoom_pipeline.fetch import FetchResult, SafeFetcher

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "arxiv" / "ai-risk-query.xml"
QUERY = 'all:"existential risk" AND all:"artificial intelligence"'
OBSERVED = "2026-10-05T00:00:00Z"
SOURCE = "src:arxiv:ai-risk"
DEFAULT_LICENSE = "http://arxiv.org/licenses/nonexclusive-distrib/1.0/"

EXPECTED = (
    (
        "2209.10604",
        "2209.10604v1",
        "Current and Near-Term AI as a Potential Existential Risk Factor",
        "2022-09-21T18:56:14Z",
        ("Benjamin S. Bucknall", "Shiri Dori-Hacohen"),
    ),
    (
        "2310.18244",
        "2310.18244v1",
        "A Review of the Evidence for Existential Risk from AI via Misaligned Power-Seeking",
        "2023-10-27T16:29:45Z",
        ("Rose Hadshar",),
    ),
    (
        "2011.03044",
        "2011.03044v1",
        "Artificial Intelligence and its impact on the Fourth Industrial Revolution: A Review",
        "2020-11-05T15:57:34Z",
        ("Gissel Velarde",),
    ),
    (
        "2311.08698",
        "2311.08698v1",
        "Artificial General Intelligence, Existential Risk, and Human Risk Perception",
        "2023-11-15T04:57:16Z",
        ("David R. Mandel",),
    ),
    (
        "2511.19115",
        "2511.19115v2",
        "AI Consciousness and Existential Risk",
        "2025-11-24T13:48:02Z",
        ("Rufin VanRullen",),
    ),
)

COPYING_LICENSES = (
    "http://creativecommons.org/licenses/by/4.0/",
    "https://creativecommons.org/licenses/by-sa/4.0/",
    "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "https://creativecommons.org/publicdomain/zero/1.0/",
    "https://creativecommons.org/licenses/by/3.0/",
)


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def rejected(*_args, **_kwargs):
        raise AssertionError("arXiv retrieval test tried to use the network")

    monkeypatch.setattr(socket, "create_connection", rejected)
    monkeypatch.setattr(socket, "socket", rejected)


def _entry_xml(license_xml: str, *, pdf: bool = True) -> bytes:
    pdf_link = ""
    if pdf:
        pdf_link = (
            '<link href="https://arxiv.org/pdf/2209.10604v1" rel="related" '
            'type="application/pdf" title="pdf"/>'
        )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <entry>
    <id>http://arxiv.org/abs/2209.10604v1</id>
    <title>Current and Near-Term AI as a Potential Existential Risk Factor</title>
    <published>2022-09-21T18:56:14Z</published>
    <summary>Abstract text stored as data, not as a PDF.</summary>
    <author><name>Benjamin S. Bucknall</name></author>
    {pdf_link}
    {license_xml}
  </entry>
</feed>
"""
    return xml.encode()


def _parse(payload: bytes):
    return ArxivCollector().parse(payload, source_identity=SOURCE, observed_at=OBSERVED)[0]


def test_ai_risk_fixture_parses_descriptive_metadata_without_network(monkeypatch):
    _block_network(monkeypatch)
    payload = FIXTURE.read_bytes()
    assert len(payload) < 200_000
    assert b"%PDF" not in payload
    assert b"/e-print/" not in payload
    assert QUERY.encode() in payload
    assert b"max_results=5" in payload
    observations = ArxivCollector().parse(payload, source_identity=SOURCE, observed_at=OBSERVED)
    assert len(observations) == len(EXPECTED)
    for observation, (bare, versioned, title, published, authors) in zip(observations, EXPECTED, strict=True):
        assert observation.canonical_url == f"https://arxiv.org/abs/{bare}"
        assert "/pdf/" not in observation.canonical_url
        assert observation.upstream_id == versioned
        assert observation.title == title
        assert observation.published_at == published
        assert observation.published_at != observation.observed_at
        assert tuple(author.name for author in observation.author_candidates) == authors
        assert observation.author_candidates[0].role == "author"
        excerpt = observation.segments[0].text
        assert excerpt
        assert len(excerpt) <= 1500
        assert not excerpt.startswith("%PDF")
        assert observation.collection_method == "arxiv_api"
        assert observation.collector == "arxiv"
        assert observation.metadata["arxiv_id"] == bare
        assert observation.metadata["license_url"] is None
        assert observation.metadata["redistributable"] is False
        assert observation.metadata["metadata_license_url"] == METADATA_LICENSE_URL
        assert observation.content_hash.startswith("sha256:")


def test_default_arxiv_license_is_not_redistributable():
    observation = _parse(_entry_xml(f"<arxiv:license>{DEFAULT_LICENSE}</arxiv:license>"))
    assert observation.metadata["license_url"] == DEFAULT_LICENSE
    assert observation.metadata["redistributable"] is False
    assert observation.metadata["metadata_license_url"] == METADATA_LICENSE_URL
    assert observation.canonical_url == "https://arxiv.org/abs/2209.10604"


@pytest.mark.parametrize("license_url", COPYING_LICENSES)
def test_creative_commons_license_that_allows_copying_is_redistributable(license_url):
    observation = _parse(_entry_xml(f"<arxiv:license>{license_url}</arxiv:license>"))
    assert observation.metadata["redistributable"] is True
    assert observation.metadata["license_url"] == license_url


def test_dc_rights_creative_commons_license_is_kept():
    license_url = "https://creativecommons.org/licenses/by-sa/4.0/"
    observation = _parse(_entry_xml(f"<dc:rights>{license_url}</dc:rights>"))
    assert observation.metadata["redistributable"] is True
    assert observation.metadata["license_url"] == license_url


def test_pdf_link_is_not_a_license_and_is_not_fetched():
    calls: list[str] = []

    def transport(url: str, headers: dict) -> FetchResult:
        calls.append(url)
        body = _entry_xml(f"<arxiv:license>{DEFAULT_LICENSE}</arxiv:license>", pdf=True)
        return FetchResult(url=url, status=200, headers={"content-type": "application/atom+xml"}, body=body)

    fetcher = SafeFetcher(
        transport=transport,
        allowed_content_types=("application/atom+xml",),
        max_attempts=1,
    )
    observations = ArxivCollector(fetcher=fetcher).collect_query(
        source_identity=SOURCE,
        search_query=QUERY,
        observed_at=OBSERVED,
        max_results=5,
    )
    assert calls == [API + "?" + "search_query=all%3A%22existential+risk%22+AND+all%3A%22artificial+intelligence%22&start=0&max_results=5"]
    assert all("/pdf/" not in url and "/e-print/" not in url for url in calls)
    assert observations[0].metadata["license_url"] == DEFAULT_LICENSE
    assert observations[0].metadata["redistributable"] is False
    assert observations[0].canonical_url == "https://arxiv.org/abs/2209.10604"


def test_non_copying_creative_commons_license_is_not_redistributable():
    license_url = "https://creativecommons.org/licenses/sampling/1.0/"
    observation = _parse(_entry_xml(f"<arxiv:license>{license_url}</arxiv:license>"))
    assert observation.metadata["license_url"] == license_url
    assert observation.metadata["redistributable"] is False
