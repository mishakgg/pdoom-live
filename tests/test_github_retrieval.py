"""Offline checks for one public GitHub repository metadata response.

The fixture was saved from a single unauthenticated GET of
https://api.github.com/repos/octocat/Hello-World. These tests do not
call the network and do not download repository contents or archives.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from pdoom_pipeline.collectors.github import GitHubCollector
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult, SafeFetcher

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "github"
PUBLIC_REPO = FIXTURES / "octocat-hello-world.json"
OBSERVED = "2026-10-05T00:00:00Z"
KNOWN_REPOSITORY = "octocat/Hello-World"
KNOWN_URL = "https://github.com/octocat/Hello-World"
METADATA_URL = "https://api.github.com/repos/octocat/Hello-World"
MAX_FIXTURE_BYTES = 200 * 1024


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("github retrieval tests must not use the network")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def test_public_repository_fixture_keeps_url_description_and_time():
    payload = PUBLIC_REPO.read_bytes()
    assert len(payload) < MAX_FIXTURE_BYTES
    repo = json.loads(payload)
    assert repo["full_name"] == KNOWN_REPOSITORY
    assert repo["html_url"] == KNOWN_URL
    observation = GitHubCollector().parse_repository(
        payload,
        source_identity="src:github:octocat:hello-world",
        observed_at=OBSERVED,
    )
    assert observation.canonical_url == KNOWN_URL
    assert observation.upstream_id == KNOWN_REPOSITORY
    assert observation.segments[0].text == " ".join(str(repo.get("description") or "").split())[:500]
    assert observation.metadata["updated_at"] == repo.get("updated_at")
    assert observation.metadata["pushed_at"] == repo.get("pushed_at")
    assert observation.metadata["updated_at"] or observation.metadata["pushed_at"]
    assert observation.metadata["upstream_version"] == (
        observation.metadata["updated_at"] or observation.metadata["pushed_at"]
    )


def test_missing_pushed_and_updated_time_stays_unknown():
    payload = _repository(created_at="2011-01-26T19:01:12Z")
    observation = GitHubCollector().parse_repository(
        payload,
        source_identity="src:github:octocat:hello-world",
        observed_at=OBSERVED,
    )
    assert observation.canonical_url == KNOWN_URL
    assert observation.segments[0].text == "My first repository on GitHub!"
    assert observation.metadata["updated_at"] is None
    assert observation.metadata["pushed_at"] is None
    assert observation.metadata["upstream_version"] == ""
    assert observation.metadata["updated_at"] != observation.published_at
    assert observation.metadata["pushed_at"] != OBSERVED


def test_pushed_time_is_kept_when_updated_time_is_missing():
    payload = _repository(pushed_at="2024-05-01T12:00:00Z")
    observation = GitHubCollector().parse_repository(
        payload,
        source_identity="src:github:octocat:hello-world",
        observed_at=OBSERVED,
    )
    assert observation.metadata["updated_at"] is None
    assert observation.metadata["pushed_at"] == "2024-05-01T12:00:00Z"
    assert observation.metadata["upstream_version"] == "2024-05-01T12:00:00Z"


def test_collect_repository_requests_metadata_only_without_a_token():
    payload = PUBLIC_REPO.read_bytes()
    seen: list[tuple[str, dict[str, str]]] = []

    def transport(url: str, headers: dict[str, str]) -> FetchResult:
        seen.append((url, headers))
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=payload)

    observation = GitHubCollector(fetcher=SafeFetcher(transport=transport, max_attempts=1)).collect_repository(
        source_identity="src:github:octocat:hello-world",
        owner="octocat",
        name="Hello-World",
        observed_at=OBSERVED,
    )
    assert seen == [(METADATA_URL, seen[0][1])]
    headers = {key.lower(): value for key, value in seen[0][1].items()}
    assert "authorization" not in headers
    assert not any("token" in key for key in headers)
    assert not any(part in seen[0][0] for part in ("/contents", "/zipball", "/tarball", "/releases", "/archive"))
    assert observation.canonical_url == KNOWN_URL


def test_collect_repository_rejects_extra_path_segments():
    def transport(url: str, headers: dict[str, str]) -> FetchResult:
        raise AssertionError(f"should not fetch {url}")

    collector = GitHubCollector(fetcher=SafeFetcher(transport=transport, max_attempts=1))
    with pytest.raises(CollectorFailure) as caught:
        collector.collect_repository(
            source_identity="src:github",
            owner="octocat",
            name="Hello-World/contents/README",
            observed_at=OBSERVED,
        )
    assert caught.value.error_class == "invalid_content"


def _repository(**overrides: object) -> bytes:
    body = {
        "full_name": KNOWN_REPOSITORY,
        "html_url": KNOWN_URL,
        "name": "Hello-World",
        "description": "My first repository on GitHub!",
        "owner": {"login": "octocat"},
        "fork": False,
        "private": False,
    }
    body.update(overrides)
    return json.dumps(body).encode("utf-8")
