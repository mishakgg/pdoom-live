"""Podcast RSS keeps episode metadata and stores the enclosure as a URL."""

from __future__ import annotations

import socket
import urllib.request
from pathlib import Path

import pytest

from pdoom_pipeline.collectors.rss import podcast_episode_metadata

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "podcasts" / "ai_risk_feed.xml"
FIELDS = ("title", "published_at", "canonical_url", "enclosure_url")


def _refuse_network(*_args, **_kwargs):
    raise AssertionError("podcast audio must not be downloaded")


def _episodes(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    monkeypatch.setattr(urllib.request, "urlopen", _refuse_network)
    monkeypatch.setattr(socket, "create_connection", _refuse_network)
    payload = FIXTURE.read_bytes()
    assert b"<enclosure " in payload
    assert b".mp3" in payload
    return podcast_episode_metadata(payload)


def test_episode_metadata_is_kept_and_enclosure_is_url_only(monkeypatch):
    episodes = _episodes(monkeypatch)
    assert [row["canonical_url"] for row in episodes] == [
        "https://example.com/ai-risk-notes/catastrophic-risk",
        "https://example.com/ai-risk-notes/untitled",
        "https://example.com/ai-risk-notes/undated",
    ]
    episode = episodes[0]
    assert set(episode) == set(FIELDS)
    assert episode["title"] == "What counts as catastrophic risk"
    assert episode["published_at"] == "2026-03-03T15:00:00Z"
    assert episode["enclosure_url"] == "https://cdn.example.com/ai-risk-notes/catastrophic-risk.mp3"
    assert isinstance(episode["enclosure_url"], str)
    assert all(isinstance(value, str) for value in episode.values())
    assert "2048" not in episode.values()
    assert podcast_episode_metadata(FIXTURE.read_bytes()) == episodes


def test_omitted_title_or_date_is_unknown_and_not_invented(monkeypatch):
    episodes = _episodes(monkeypatch)
    untitled = episodes[1]
    undated = episodes[2]
    assert untitled["title"] == "unknown"
    assert untitled["title"] != "Show notes that are not a title"
    assert untitled["title"] != "untitled"
    assert untitled["published_at"] == "2026-03-04T15:00:00Z"
    assert untitled["enclosure_url"] == "https://cdn.example.com/ai-risk-notes/untitled.mp3"
    assert undated["title"] == "Horizon left open"
    assert undated["published_at"] == "unknown"
    assert undated["published_at"] != "2026-01-01T00:00:00Z"
    assert undated["enclosure_url"] == "https://cdn.example.com/ai-risk-notes/undated.mp3"
