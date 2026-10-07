"""GitHub public repository metadata collector.

Descriptions only. Full READMEs, repository file contents, and release
archives are not copied into the dataset.
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation, excerpt
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "github-0.1.1"
GITHUB_ACCEPT = {"Accept": "application/vnd.github+json"}
# One repository object. Not /contents, /releases, /zipball, or /tarball.
REPOSITORY_METADATA_URL = "https://api.github.com/repos/{owner}/{name}"
_PATH_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class GitHubCollector:
    collector = "github"
    platform = "github"

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=1_000_000,
        )

    def collect_repository(self, *, source_identity: str, owner: str, name: str, observed_at: str) -> SourceObservation:
        """Read public metadata for one repository. No token and no archive download."""
        owner_name = _github_path_component(owner, "owner")
        repo_name = _github_path_component(name, "repository")
        url = REPOSITORY_METADATA_URL.format(owner=quote(owner_name, safe=""), name=quote(repo_name, safe=""))
        result = self.fetcher.get(url, headers=dict(GITHUB_ACCEPT))
        return self.parse_repository(result.body, source_identity=source_identity, observed_at=observed_at)

    def parse_repository(self, payload: bytes, *, source_identity: str, observed_at: str) -> SourceObservation:
        data = _decode_json(payload)
        if not isinstance(data, dict):
            raise CollectorFailure("invalid_content", "github repository response was not an object")
        _raise_if_github_error(data)
        owner = data.get("owner") if isinstance(data.get("owner"), dict) else {}
        username = str(owner.get("login") or "")
        observation = _repository_observation(
            data,
            source_identity=source_identity,
            username=username,
            observed_at=observed_at,
        )
        if observation is None:
            raise CollectorFailure("invalid_content", "github repository missing full_name or html_url")
        return observation

    def collect_repos(self, *, source_identity: str, username: str, observed_at: str, per_page: int = 10) -> list[SourceObservation]:
        if not username or "/" in username or username.startswith("."):
            raise CollectorFailure("invalid_content", "invalid github username")
        if per_page < 1 or per_page > 30:
            raise CollectorFailure("invalid_content", "per_page must be between 1 and 30")
        url = f"https://api.github.com/users/{quote(username)}/repos?per_page={per_page}&sort=updated&type=owner"
        result = self.fetcher.get(url, headers=dict(GITHUB_ACCEPT))
        return self.parse_repos(result.body, source_identity=source_identity, username=username, observed_at=observed_at)

    def parse_repos(self, payload: bytes, *, source_identity: str, username: str, observed_at: str) -> list[SourceObservation]:
        data = _decode_json(payload)
        if isinstance(data, dict) and data.get("message"):
            _raise_if_github_error(data)
        if not isinstance(data, list):
            raise CollectorFailure("invalid_content", "github repo response was not a list")
        observations = []
        for repo in data[:30]:
            if not isinstance(repo, dict):
                raise CollectorFailure("invalid_content", "github repository row was not an object")
            if any(not isinstance(repo.get(key), str) or not repo[key].strip() for key in ("full_name", "html_url")):
                raise CollectorFailure("invalid_content", "github repository row has invalid identity fields")
            observation = _repository_observation(
                repo,
                source_identity=source_identity,
                username=username,
                observed_at=observed_at,
            )
            if observation is None:
                raise CollectorFailure("invalid_content", "github repository row missing full_name or html_url")
            observations.append(observation)
        return observations


def _repository_observation(repo: dict, *, source_identity: str, username: str, observed_at: str) -> SourceObservation | None:
    full_name = str(repo.get("full_name") or "")
    html_url = str(repo.get("html_url") or "")
    if not full_name or not html_url:
        return None
    description, truncated = excerpt(str(repo.get("description") or ""), 500)
    owner = repo.get("owner") if isinstance(repo.get("owner"), dict) else {}
    owner_login = str(owner.get("login") or username)
    updated_at = _as_utc(repo.get("updated_at"))
    pushed_at = _as_utc(repo.get("pushed_at"))
    # Prefer the API's updated time, then the push time. Do not invent one from
    # created_at or observed_at when both are missing.
    activity_at = updated_at or pushed_at
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
            "upstream_version": activity_at or "",
            "updated_at": updated_at,
            "pushed_at": pushed_at,
            "truncated": truncated,
            "fork": bool(repo.get("fork")),
            "visibility": repo.get("visibility") or ("private" if repo.get("private") else "public"),
        },
        collection_method="github_api",
        collector="github",
        collector_version=COLLECTOR_VERSION,
    )
    return observation.finalize_hash()


def _github_path_component(value: object, kind: str) -> str:
    if not isinstance(value, str) or not _PATH_COMPONENT.fullmatch(value):
        raise CollectorFailure("invalid_content", f"invalid github {kind}")
    return value


def _decode_json(payload: bytes):
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed github payload: {exc}") from exc


def _raise_if_github_error(data: dict) -> None:
    if not data.get("message"):
        return
    if data.get("full_name") and data.get("html_url"):
        return
    message = str(data.get("message"))
    if "rate limit" in message.lower():
        raise CollectorFailure("rate_limited", message)
    raise CollectorFailure("invalid_content", message)


def _as_utc(value: object) -> str | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        return text
    return text
