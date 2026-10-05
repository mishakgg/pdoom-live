"""Offline checks for the US congressional AI-risk hearing catalog."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from pdoom_pipeline.catalogs.congress_hearings import (
    RIGHTS,
    UNKNOWN_DATE,
    default_catalog_path,
    hearing_from_record,
    load_hearings,
    validate_canonical_url,
    validate_date,
)

OFFICIAL_URLS = [
    "https://house.gov/hearing",
    "https://www.senate.gov/hearing",
    "https://www.congress.gov/event/118th-congress/senate-event/LC71543",
    "https://docs.house.gov/meetings/IF/IF02/20251118/118669",
    "https://judiciary.senate.gov/committee-activity/hearings/example",
]

REJECTED_URLS = [
    "https://example.com/ai-hearing",
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://whitehouse.gov/ostp/ai",
    "https://senate.gov.example.net/hearing",
    "https://notcongress.gov/event",
    "https://myhouse.gov/hearing",
    "http://www.congress.gov/hearing",
    "https://user:pass@www.senate.gov/hearing",
    "https://www.house.gov/hearing?utm_source=x",
    "https://www.congress.gov/hearing#transcript",
    "https://127.0.0.1/hearing",
]


def test_catalog_rows_are_official_public_domain_hearings():
    hearings = load_hearings()
    assert len(hearings) == 9
    assert [hearing.date for hearing in hearings] == sorted(hearing.date for hearing in hearings)
    for hearing in hearings:
        assert hearing.rights == RIGHTS
        assert hearing.date != UNKNOWN_DATE
        assert hearing.title
        assert hearing.committee
        lowered = hearing.title.lower()
        assert "artificial intelligence" in lowered or " ai" in f" {lowered}"
        host = hearing.canonical_url.split("/")[2]
        assert host.endswith("house.gov") or host.endswith("senate.gov") or host.endswith("congress.gov")


def test_known_risk_hearings_keep_their_confirmed_urls():
    by_id = {hearing.id: hearing for hearing in load_hearings()}
    assert by_id["s-hsgac-2023-03-08-ai-risks-opportunities"].canonical_url == (
        "https://www.hsgac.senate.gov/hearings/artificial-intelligence-risks-and-opportunities/"
    )
    assert by_id["s-judiciary-2023-07-25-oversight-ai-principles"].date == "2023-07-25"
    assert by_id["h-science-2023-10-18-ai-risk-management"].committee.startswith(
        "House Committee on Science, Space, and Technology"
    )
    assert by_id["h-energy-commerce-2025-11-18-ai-chatbot-risks"].date == "2025-11-18"


def test_non_congress_urls_are_rejected():
    for url in REJECTED_URLS:
        with pytest.raises(ValueError):
            validate_canonical_url(url)


@pytest.mark.parametrize("url", OFFICIAL_URLS)
def test_official_congress_hosts_are_accepted(url: str):
    assert validate_canonical_url(url) == url


def test_date_accepts_unknown_and_rejects_invalid_calendar_dates():
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2023-05-16") == "2023-05-16"
    with pytest.raises(ValueError):
        validate_date("May 16, 2023")
    with pytest.raises(ValueError):
        validate_date("2023-02-31")
    with pytest.raises(ValueError):
        validate_date(None)


def test_row_rejects_transcript_fields_and_foreign_urls():
    base = {
        "id": "s-example-2023-01-01-ai-risk",
        "title": "Artificial Intelligence Risk",
        "committee": "Senate Committee on the Judiciary",
        "date": UNKNOWN_DATE,
        "canonical_url": "https://www.judiciary.senate.gov/hearings/example",
        "rights": RIGHTS,
    }
    hearing = hearing_from_record(base)
    assert hearing.date == UNKNOWN_DATE
    with pytest.raises(ValueError):
        hearing_from_record({**base, "transcript": "full spoken record"})
    with pytest.raises(ValueError):
        hearing_from_record({**base, "canonical_url": "https://example.com/hearing"})
    with pytest.raises(ValueError):
        hearing_from_record({**base, "rights": "all_rights_reserved"})


def test_catalog_file_stores_no_transcript(tmp_path: Path):
    payload = json.loads(default_catalog_path().read_text(encoding="utf-8"))
    assert payload["rights"] == RIGHTS
    blob = json.dumps(payload).lower()
    assert "transcript" not in blob
    assert len(blob) < 8000

    payload["hearings"].append(dict(payload["hearings"][0]))
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_hearings(duplicate)

    payload["hearings"].pop()
    payload["hearings"][0] = {**payload["hearings"][0], "body": "x" * 800}
    oversized = tmp_path / "oversized.json"
    oversized.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        load_hearings(oversized)


def test_load_catalog_does_not_open_sockets(monkeypatch: pytest.MonkeyPatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("catalog load must not use the network")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    assert load_hearings()
