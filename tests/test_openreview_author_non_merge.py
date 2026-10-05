"""OpenReview profile identifiers keep a shared display name from collapsing.

Fixture records only. This module does not call the OpenReview API.
"""

from __future__ import annotations

import socket

import pytest

from pdoom_pipeline.identity.resolve import choose_openalex_author


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("openreview identity tests must not use the network")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def _person(display_name: str, institutions: list[str]) -> dict:
    return {
        "display_name": display_name,
        "name_distinctiveness": "high",
        "institution_keywords": institutions,
        "name_variants": [],
    }


def _author(openalex_id: str, display_name: str, openreview_id: str | None, works: int, institution: str) -> dict:
    return {
        "id": f"https://openalex.org/{openalex_id}",
        "display_name": display_name,
        "works_count": works,
        "ids": {"openreview": f"https://openreview.net/profile?id={openreview_id}"} if openreview_id else {},
        "affiliations": [{"institution": {"display_name": institution}}],
    }


def test_same_display_name_with_different_openreview_profiles_stay_two_people():
    records = [
        _author("A1", "James Zhang", "~James_Zhang1", 100, "Tsinghua University"),
        _author("A2", "James Zhang", "~James_Zhang2", 12, "Tsinghua University"),
    ]
    decision = choose_openalex_author(_person("James Zhang", ["Tsinghua"]), records)
    assert decision["status"] == "ambiguous"
    assert decision.get("openalex_id") is None
    assert decision.get("openreview_id") is None
    assert {row.get("openalex_id") for row in decision.get("candidates") or []} == {"A1", "A2"}
    assert {row.get("openreview_id") for row in decision.get("candidates") or []} == {"~James_Zhang1", "~James_Zhang2"}


def test_exact_unique_name_without_second_identifier_still_matches():
    person = _person("Dario Amodei", ["Not A Real Lab"])
    records = [
        {
            "id": "https://openalex.org/A5066197394",
            "display_name": "Dario Amodei",
            "works_count": 50,
            "ids": {},
            "affiliations": [{"institution": {"display_name": "OpenAI (United States)"}}],
        }
    ]
    decision = choose_openalex_author(person, records)
    assert decision["status"] == "accepted"
    assert decision["verification_method"] == "openalex_unique_exact_name"
    assert decision["openalex_id"] == "A5066197394"
    assert decision.get("openreview_id") is None


def test_missing_openreview_profile_does_not_attach_to_nearest_similar_name():
    nearest = [
        _author("A2", "James Y. Zhang", None, 80, "Tsinghua University"),
        _author("A3", "Jameson Zhang", "~Jameson_Zhang1", 90, "Tsinghua University"),
    ]
    decision = choose_openalex_author(_person("James Zhang", ["Tsinghua"]), nearest)
    assert decision["status"] == "not_found"
    assert decision.get("openalex_id") is None
    assert decision.get("openreview_id") is None
    candidate_ids = {row.get("openalex_id") for row in decision.get("candidates") or []}
    assert candidate_ids.isdisjoint({"A2", "A3"})
