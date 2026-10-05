"""Hugging Face public model and dataset card metadata.

Uses the Hub JSON API for one repo. The response is card metadata only.
This module does not download model weights, dataset files, or card images,
and it is not wired into the belief runner.

A card license is copied only from ``cardData.license`` when that value is a
single non-empty string. Tag names such as ``license:mit`` are not a license.
A missing license stays ``unknown``. ``lastModified`` is kept when it is a
timezone-aware timestamp; otherwise the time stays ``unknown``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "huggingface-0.1.0"
UNKNOWN = "unknown"
# Fixture and response must stay under 200KB. One attempt, no redirects.
MAX_CARD_BYTES = 200 * 1024
API_HOST = "huggingface.co"
_KINDS = {
    "model": ("models", "https://huggingface.co/"),
    "dataset": ("datasets", "https://huggingface.co/datasets/"),
}
_SEGMENT = r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,94}[A-Za-z0-9])?"
_REPO_ID = re.compile(rf"^{_SEGMENT}(?:/{_SEGMENT})?$")
_MAX_LICENSE_CHARS = 128


@dataclass(frozen=True)
class HuggingFaceCard:
    """Metadata taken from one public model or dataset card."""

    repo_id: str
    canonical_url: str
    last_modified: str
    license: str


class HuggingFaceCollector:
    """Retrieve one public card from the Hugging Face Hub API."""

    collector = "huggingface"
    platform = "huggingface"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_CARD_BYTES - 1,
            max_attempts=1,
            max_redirects=0,
            timeout=10.0,
        )

    def retrieve(self, repo_id: str, *, kind: str = "model") -> HuggingFaceCard:
        """Fetch one card. Does not follow redirects or file links."""
        repo_id = _require_repo_id(repo_id)
        api_name, _prefix = _require_kind(kind)
        url = _api_url(api_name, repo_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        if result.requested_urls != [url]:
            raise CollectorFailure("blocked_by_policy", "refusing a redirected huggingface fetch")
        card = self.parse(result.body, kind=kind)
        if card.repo_id != repo_id:
            raise CollectorFailure("invalid_content", "huggingface repo id mismatch")
        return card

    def parse(self, payload: bytes, *, kind: str = "model") -> HuggingFaceCard:
        """Parse a Hub model or dataset JSON body. Performs no I/O."""
        _require_kind(kind)
        if len(payload) >= MAX_CARD_BYTES:
            raise CollectorFailure("content_too_large", "huggingface card metadata exceeds 200KB")
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CollectorFailure("invalid_content", f"malformed huggingface payload: {exc}") from exc
        if not isinstance(data, dict):
            raise CollectorFailure("invalid_content", "huggingface payload was not an object")
        if "id" not in data and data.get("error"):
            _raise_api_error(data)
        repo_id = _require_repo_id(data.get("id"))
        return HuggingFaceCard(
            repo_id=repo_id,
            canonical_url=_canonical_url(kind, repo_id),
            last_modified=_last_modified(data.get("lastModified")),
            license=_card_license(data.get("cardData")),
        )


def _require_kind(kind: str) -> tuple[str, str]:
    if kind not in _KINDS:
        raise CollectorFailure("invalid_content", "huggingface kind must be model or dataset")
    return _KINDS[kind]


def _require_repo_id(value: object) -> str:
    if not isinstance(value, str) or not _REPO_ID.fullmatch(value):
        raise CollectorFailure("invalid_content", "invalid huggingface repo id")
    return value


def _api_url(api_name: str, repo_id: str) -> str:
    encoded = "/".join(quote(part, safe="") for part in repo_id.split("/"))
    url = f"https://{API_HOST}/api/{api_name}/{encoded}"
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.query or parsed.fragment:
        raise CollectorFailure("unsafe_url", "refusing huggingface url")
    if parts[:2] != ["api", api_name] or len(parts) not in {3, 4}:
        raise CollectorFailure("blocked_by_policy", "refusing non-metadata huggingface path")
    if any(part in {"resolve", "media", "blobs", "raw"} for part in parts):
        raise CollectorFailure("blocked_by_policy", "refusing huggingface file path")
    return url


def _canonical_url(kind: str, repo_id: str) -> str:
    _api_name, prefix = _require_kind(kind)
    try:
        return canonicalize_url(f"{prefix}{repo_id}")
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "invalid huggingface canonical url") from exc


def _last_modified(value: object) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    text = value.strip()
    if not text or len(text) > 40 or text != value:
        return UNKNOWN
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return UNKNOWN
    if parsed.tzinfo is None:
        return UNKNOWN
    return text


def _card_license(card_data: object) -> str:
    if not isinstance(card_data, dict) or "license" not in card_data:
        return UNKNOWN
    raw = card_data.get("license")
    if not isinstance(raw, str):
        return UNKNOWN
    text = raw.strip()
    if not text or len(text) > _MAX_LICENSE_CHARS:
        return UNKNOWN
    if any(char in text for char in "\r\n\x00"):
        return UNKNOWN
    return text


def _raise_api_error(data: dict) -> None:
    message = str(data.get("message") or data.get("error") or "huggingface error")
    error = str(data.get("error") or "")
    lowered = f"{error} {message}".lower()
    if "not found" in lowered or error in {"RepoNotFound", "NotFound"}:
        raise CollectorFailure("not_found", message)
    if "rate" in lowered:
        raise CollectorFailure("rate_limited", message)
    raise CollectorFailure("invalid_content", message)
