"""GitHub public repository metadata collector.

Descriptions only. Full READMEs are not copied into the dataset.
"""

from __future__ import annotations

import json
from urllib.parse import quote

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "github-0.1.0"


class GitHubCollector:
    collector = "github"
    platform = "github"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=1_000_000,
        )

    def collect_repos(self, *, source_identity: str, username: str, observed_at: str, per_page: int = 10) -> list[SourceObservation]:
        if not username or "/" in username or username.startswith("."):
            raise CollectorFailure("invalid_content", "invalid github username")
        if per_page < 1 or per_page > 30:
            raise CollectorFailure("invalid_content", "per_page must be between 1 and 30")
        url = f"https://api.github.com/users/{quote(username)}/repos?per_page={per_page}&sort=updated&type=owner"
        result = self.fetcher.get(url, headers={"Accept": "application/vnd.github+json"})
        return self.parse_repos(result.body, source_identity=source_identity, username=username, observed_at=observed_at)

    def parse_repos(self, payload: bytes, *, source_identity: str, username: str, observed_at: str) -> list[SourceObservation]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CollectorFailure("invalid_content", f"malformed github payload: {exc}") from exc
        if isinstance(data, dict) and data.get("message"):
            message = str(data.get("message"))
            if "rate limit" in message.lower():
                raise CollectorFailure("rate_limited", message)
            raise CollectorFailure("invalid_content", message)
        if not isinstance(data, list):
            raise CollectorFailure("invalid_content", "github repo response was not a list")
        observations = []
        for repo in data[:30]:
            if not isinstance(repo, dict):
                continue
            full_name = str(repo.get("full_name") or "")
            html_url = str(repo.get("html_url") or "")
            if not full_name or not html_url:
                continue
            description, truncated = excerpt(str(repo.get("description") or ""), 500)
            owner = repo.get("owner") or {}
            owner_login = str(owner.get("login") or username)
            updated = repo.get("updated_at") or repo.get("pushed_at")
            observation = SourceObservation(
                source_identity=source_identity,
                platform="github",
                upstream_id=full_name,
                canonical_url=canonicalize_url(html_url),
                observed_at=observed_at,
                published_at=_as_utc(repo.get("created_at")),
                author_candidates=[
                    AuthorCandidate(
                        name=owner_login,
                        role="author",
                        attribution_method="github_repo_owner",
                        confidence="medium",
                    )
                ],
                title=str(repo.get("name") or full_name),
                segments=[Segment(segment_kind="metadata", sequence=0, text=description, start_char=0, end_char=len(description))],
                metadata={
                    "upstream_version": str(updated or ""),
                    "truncated": truncated,
                    "fork": bool(repo.get("fork")),
                    "visibility": repo.get("visibility") or ("private" if repo.get("private") else "public"),
                },
                collection_method="github_api",
                collector="github",
                collector_version=COLLECTOR_VERSION,
            )
            observations.append(observation.finalize_hash())
        return observations


def _as_utc(value: object) -> str | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        return text
    return text
