"""Offline checks for the UK Open Government Licence AI safety catalog."""

from __future__ import annotations

import copy
import socket

import pytest

from pdoom_pipeline.catalogs.uk_ogl import (
    LICENSE,
    MAX_ATTRIBUTION_CHARS,
    CatalogError,
    attribution_from_page,
    load_catalog,
    states_open_government_licence,
    validate_catalog,
)

FOOTER = "All content is available under the Open Government Licence v3.0, except where otherwise stated"
PUBLICATION_NOTICE = (
    "This publication is licensed under the terms of the Open Government Licence v3.0 except where otherwise stated. "
    "To view this licence, visit nationalarchives.gov.uk/doc/open-government-licence/version/3 "
    "or write to the Information Policy Team, The National Archives, Kew, London TW9 4DU, "
    "or email: psi@nationalarchives.gov.uk. "
    "Where we have identified any third party copyright information you will need to obtain permission from the copyright holders concerned."
)

EXPECTED = [
    (
        "Emerging processes for frontier AI safety",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/emerging-processes-for-frontier-ai-safety/emerging-processes-for-frontier-ai-safety",
        "2023-10-27",
        "2023",
    ),
    (
        "Frontier AI Taskforce: second progress report",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/frontier-ai-taskforce-second-progress-report/frontier-ai-taskforce-second-progress-report",
        "2023-10-30",
        "2023",
    ),
    (
        "AI Safety Institute: overview",
        "Department for Science, Innovation and Technology; AI Safety Institute",
        "https://www.gov.uk/government/publications/ai-safety-institute-overview",
        "2023-11-02",
        None,
    ),
    (
        "Introducing the AI Safety Institute",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/ai-safety-institute-overview/introducing-the-ai-safety-institute",
        "2023-11-02",
        "2024",
    ),
    (
        "Frontier AI: capabilities and risks – discussion paper",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/frontier-ai-capabilities-and-risks-discussion-paper/frontier-ai-capabilities-and-risks-discussion-paper",
        "2023-11-03",
        "2025",
    ),
    (
        "AI Safety Institute: third progress report",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/uk-ai-safety-institute-third-progress-report/ai-safety-institute-third-progress-report",
        "2024-02-05",
        "2024",
    ),
    (
        "AI Safety Institute approach to evaluations",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/ai-safety-institute-approach-to-evaluations/ai-safety-institute-approach-to-evaluations",
        "2024-02-09",
        "2024",
    ),
    (
        "Introduction to AI assurance",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/introduction-to-ai-assurance/introduction-to-ai-assurance",
        "2024-02-12",
        "2024",
    ),
    (
        "Frontier AI Safety Commitments, AI Seoul Summit 2024",
        "Department for Science, Innovation and Technology",
        "https://www.gov.uk/government/publications/frontier-ai-safety-commitments-ai-seoul-summit-2024/frontier-ai-safety-commitments-ai-seoul-summit-2024",
        "2024-05-21",
        "2025",
    ),
]


def test_catalog_load_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    document = load_catalog()
    assert document["catalog"] == "uk_ogl_ai_safety"
    assert len(document["entries"]) == len(EXPECTED)


def test_catalog_rows_match_confirmed_aisi_and_dsit_pages():
    entries = load_catalog()["entries"]
    publishers = {entry["publisher"] for entry in entries}
    assert "Department for Science, Innovation and Technology" in publishers
    assert any("AI Safety Institute" in publisher for publisher in publishers)
    assert [entry["canonical_url"] for entry in entries] == [row[2] for row in EXPECTED]
    for entry, expected in zip(entries, EXPECTED, strict=True):
        title, publisher, url, published, year = expected
        assert entry["title"] == title
        assert entry["publisher"] == publisher
        assert entry["canonical_url"] == url
        assert entry["date"] == published
        assert entry["license"] == LICENSE
        assert len(entry["attribution"]) <= MAX_ATTRIBUTION_CHARS
        assert "open government licence" in entry["attribution"].casefold()
        page = f"<article><p>Full document text that must not be stored.</p><p>{entry['attribution']}</p></article>"
        assert attribution_from_page(page) == entry["attribution"]
        assert "Full document text" not in attribution_from_page(page)
        if year is None:
            assert entry["attribution"] == FOOTER
        else:
            assert entry["attribution"].startswith(f"© Crown copyright {year} ")
            assert PUBLICATION_NOTICE in entry["attribution"]


def test_page_that_does_not_state_the_open_government_licence_is_rejected():
    reserved = "<p>© Crown copyright 2024. All rights reserved.</p>" + ("<p>AI safety findings.</p>" * 20)
    assert not states_open_government_licence(reserved)
    with pytest.raises(CatalogError, match="does not state the Open Government Licence"):
        attribution_from_page(reserved)
    incidental = "The minister mentioned the Open Government Licence " + ("without the publication notice. " * 40)
    with pytest.raises(CatalogError, match="bounded Open Government Licence attribution"):
        attribution_from_page(incidental)


def test_short_licence_sentence_is_kept_and_html_notices_are_plain_text():
    page = "<p>Intro.</p><p>This dataset is licensed under the Open Government Licence v3.0.</p><p>End.</p>"
    assert attribution_from_page(page) == "This dataset is licensed under the Open Government Licence v3.0."
    hidden = "<script>Open Government Licence</script><p>No public licence notice.</p>"
    assert not states_open_government_licence(hidden)


def test_validator_rejects_bad_dates_licences_and_document_fields():
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["date"] = "unknown"
    validate_catalog(document)
    document["entries"][0]["date"] = "2 November 2023"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["license"] = "cc-by"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["attribution"] = "© Crown copyright 2023"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = "full document"
    with pytest.raises(CatalogError):
        validate_catalog(document)
