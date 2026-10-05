"""ORCID identifiers keep similar names from collapsing.

Fixture records only. This module does not call the ORCID API.
"""

from __future__ import annotations

from pdoom_pipeline.identity.names import same_person_name
from pdoom_pipeline.identity.resolve import choose_openalex_author, dedupe_openalex_ids


def _person(display_name: str, institutions: list[str]) -> dict:
    return {
        "display_name": display_name,
        "name_distinctiveness": "high",
        "institution_keywords": institutions,
        "name_variants": [],
    }


def _author(openalex_id: str, display_name: str, orcid: str | None, works: int, institution: str) -> dict:
    return {
        "id": f"https://openalex.org/{openalex_id}",
        "display_name": display_name,
        "works_count": works,
        "orcid": orcid,
        "ids": {"orcid": f"https://orcid.org/{orcid}"} if orcid else {},
        "affiliations": [{"institution": {"display_name": institution}}],
    }


def test_similar_names_with_different_orcids_stay_two_people():
    assert not same_person_name("Samir Okonkwo", "Samira Okonkwo")
    assert same_person_name("Wei Zhang", "Wei Y. Zhang")

    wei_records = [
        _author("A1", "Wei Zhang", "0000-0001-0000-0001", 100, "Tsinghua University"),
        _author("A2", "Wei Y. Zhang", "0000-0001-0000-0002", 12, "Tsinghua University"),
    ]
    wei = choose_openalex_author(_person("Wei Zhang", ["Tsinghua"]), wei_records)
    wei_middle = choose_openalex_author(_person("Wei Y. Zhang", ["Tsinghua"]), wei_records)
    assert wei["status"] == "accepted"
    assert wei_middle["status"] == "accepted"
    assert wei["openalex_id"] == "A1"
    assert wei_middle["openalex_id"] == "A2"
    assert wei["orcid"] == "0000-0001-0000-0001"
    assert wei_middle["orcid"] == "0000-0001-0000-0002"

    samir_records = [
        _author("S1", "Samir Okonkwo", "0000-0002-0002-0002", 20, "Northwind Alignment Lab"),
        _author("S2", "Samira Okonkwo", "0000-0002-0003-0003", 80, "Northwind Alignment Lab"),
    ]
    samir = choose_openalex_author(_person("Samir Okonkwo", ["Northwind"]), samir_records)
    samira = choose_openalex_author(_person("Samira Okonkwo", ["Northwind"]), samir_records)
    assert samir["openalex_id"] == "S1"
    assert samira["openalex_id"] == "S2"
    assert samir["orcid"] != samira["orcid"]

    cleaned, conflicts = dedupe_openalex_ids(
        {
            "person:wei-zhang": wei,
            "person:wei-y-zhang": wei_middle,
            "person:samir-okonkwo": samir,
            "person:samira-okonkwo": samira,
        }
    )
    assert conflicts == []
    assert cleaned["person:wei-zhang"]["openalex_id"] != cleaned["person:wei-y-zhang"]["openalex_id"]
    assert cleaned["person:samir-okonkwo"]["orcid"] == "0000-0002-0002-0002"
    assert cleaned["person:samira-okonkwo"]["orcid"] == "0000-0002-0003-0003"


def test_missing_orcid_stays_unresolved_instead_of_nearest_name():
    nearest = [
        _author("A2", "Wei Y. Zhang", None, 80, "Tsinghua University"),
        _author("A3", "Weiyu Zhang", "0000-0001-0000-0003", 90, "Tsinghua University"),
    ]
    decision = choose_openalex_author(_person("Wei Zhang", ["Tsinghua"]), nearest)
    assert decision["status"] == "not_found"
    assert decision.get("openalex_id") is None
    assert decision.get("orcid") is None
    candidate_ids = {row.get("openalex_id") for row in decision.get("candidates") or []}
    assert candidate_ids.isdisjoint({"A2", "A3"})
