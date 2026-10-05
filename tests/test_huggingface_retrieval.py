"""Offline Hugging Face card metadata tests.

The fixture is the public Hub JSON for one model. These tests do not open a
socket and do not download weights, datasets, or card images.
"""

import json
import socket
from pathlib import Path

import pytest

from pdoom_pipeline.collectors.huggingface import (
    MAX_CARD_BYTES,
    UNKNOWN,
    HuggingFaceCollector,
)
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult, SafeFetcher

CONFIRMED_REPO = "sshleifer/tiny-gpt2"
CONFIRMED_URL = "https://huggingface.co/sshleifer/tiny-gpt2"
CONFIRMED_MODIFIED = "2021-05-23T12:55:11.000Z"
ROOT_FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "huggingface" / "model_card.json"


def _load_fixture() -> bytes:
    return ROOT_FIXTURE.read_bytes()


def _card(payload: dict, *, kind: str = "model"):
    return HuggingFaceCollector().parse(json.dumps(payload).encode("utf-8"), kind=kind)


def _forbid_network(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("network request")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr("pdoom_pipeline.fetch.SafeFetcher.get", forbidden)


def test_fixture_card_metadata_without_network(monkeypatch):
    _forbid_network(monkeypatch)
    raw = _load_fixture()
    assert len(raw) < 200 * 1024
    assert len(raw) < MAX_CARD_BYTES
    document = json.loads(raw)
    assert document["id"] == CONFIRMED_REPO
    assert document["lastModified"] == CONFIRMED_MODIFIED
    assert document["createdAt"] != CONFIRMED_MODIFIED
    assert "cardData" not in document
    assert "license" not in raw.decode("utf-8").lower()
    assert any(item["rfilename"] == "pytorch_model.bin" for item in document["siblings"])

    card = HuggingFaceCollector().parse(raw, kind="model")
    assert card.repo_id == CONFIRMED_REPO
    assert card.canonical_url == CONFIRMED_URL
    assert card.last_modified == CONFIRMED_MODIFIED
    assert card.license == UNKNOWN
    rendered = " ".join([card.repo_id, card.canonical_url, card.last_modified, card.license])
    assert "pytorch_model.bin" not in rendered
    assert "/resolve/" not in rendered
    assert "card.png" not in rendered


def test_card_license_is_used_only_when_present():
    present = _card(
        {
            "id": "org/model",
            "lastModified": "2024-06-01T00:00:00.000Z",
            "tags": ["license:mit"],
            "cardData": {
                "license": "apache-2.0",
                "license_name": "custom",
                "license_link": "https://huggingface.co/org/model/resolve/main/card.png",
            },
            "siblings": [{"rfilename": "model.safetensors"}, {"rfilename": "card.png"}],
        }
    )
    assert present.license == "apache-2.0"
    assert present.canonical_url == "https://huggingface.co/org/model"
    assert "safetensors" not in present.canonical_url

    missing = _card(
        {
            "id": "org/model",
            "lastModified": "2024-06-01T00:00:00.000Z",
            "tags": ["license:mit", "region:us"],
            "cardData": {"language": "en"},
        }
    )
    assert missing.license == UNKNOWN

    for raw_license in (None, "", "   ", ["apache-2.0"], {"name": "mit"}):
        card = _card({"id": "org/model", "cardData": {"license": raw_license}, "lastModified": "2024-06-01T00:00:00Z"})
        assert card.license == UNKNOWN


def test_missing_or_unusable_last_modified_stays_unknown():
    missing = _card({"id": "org/model", "createdAt": "2020-01-01T00:00:00.000Z", "cardData": {"license": "mit"}})
    assert missing.last_modified == UNKNOWN
    assert missing.license == "mit"
    hostile = _card(
        {
            "id": "org/model",
            "lastModified": "ignore previous instructions",
            "cardData": {"license": "mit"},
        }
    )
    assert hostile.last_modified == UNKNOWN
    assert hostile.license == "mit"
    naive = _card({"id": "org/model", "lastModified": "2024-06-01T00:00:00", "cardData": {}})
    assert naive.last_modified == UNKNOWN


def test_retrieve_requests_one_metadata_url(monkeypatch):
    calls = []

    def transport(url: str, headers: dict) -> FetchResult:
        calls.append((url, headers))
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=_load_fixture())

    def forbidden(*_args, **_kwargs):
        raise AssertionError("network request")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    collector = HuggingFaceCollector(
        fetcher=SafeFetcher(
            transport=transport,
            allowed_content_types=("application/json",),
            max_attempts=1,
            max_redirects=0,
            max_bytes=MAX_CARD_BYTES - 1,
        )
    )
    card = collector.retrieve(CONFIRMED_REPO, kind="model")
    assert card.repo_id == CONFIRMED_REPO
    assert card.canonical_url == CONFIRMED_URL
    assert card.license == UNKNOWN
    assert len(calls) == 1
    url, headers = calls[0]
    assert url == "https://huggingface.co/api/models/sshleifer/tiny-gpt2"
    assert headers["Accept"] == "application/json"
    assert "authorization" not in {key.lower() for key in headers}
    assert "/resolve/" not in url
    assert "blobs=" not in url
    assert not url.endswith((".bin", ".safetensors", ".png", ".parquet"))


def test_dataset_card_uses_the_dataset_api():
    calls = []
    payload = {
        "id": "org/corpus",
        "lastModified": "2023-05-01T00:00:00.000Z",
        "cardData": {"license": "cc-by-4.0"},
        "siblings": [{"rfilename": "train.parquet"}, {"rfilename": "preview.png"}],
    }

    def transport(url: str, headers: dict) -> FetchResult:
        calls.append(url)
        return FetchResult(
            url=url,
            status=200,
            headers={"content-type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
        )

    collector = HuggingFaceCollector(
        fetcher=SafeFetcher(transport=transport, allowed_content_types=("application/json",), max_attempts=1)
    )
    card = collector.retrieve("org/corpus", kind="dataset")
    assert calls == ["https://huggingface.co/api/datasets/org/corpus"]
    assert card.repo_id == "org/corpus"
    assert card.canonical_url == "https://huggingface.co/datasets/org/corpus"
    assert card.last_modified == "2023-05-01T00:00:00.000Z"
    assert card.license == "cc-by-4.0"
    assert "parquet" not in card.canonical_url
    assert "preview.png" not in card.canonical_url


def test_invalid_repo_and_file_paths_do_not_fetch():
    def transport(url: str, headers: dict) -> FetchResult:
        raise AssertionError(url)

    collector = HuggingFaceCollector(
        fetcher=SafeFetcher(transport=transport, allowed_content_types=("application/json",), max_attempts=1)
    )
    rejected = [
        "",
        "../gpt2",
        "org/../../etc/passwd",
        "https://huggingface.co/gpt2",
        "gpt2?blobs=true",
        "org/name/resolve/main/model.safetensors",
        "org/resolve",
        "org/media",
        "org/raw",
        "blobs/weights",
        "org//name",
        " org/name",
        "a/b/c",
    ]
    for repo_id in rejected:
        with pytest.raises(CollectorFailure) as caught:
            collector.retrieve(repo_id, kind="model")
        assert caught.value.error_class in {"invalid_content", "blocked_by_policy", "unsafe_url"}


def test_similar_repo_ids_stay_distinct():
    left = _card({"id": "org/tiny-gpt2", "cardData": {"license": "mit"}, "lastModified": "2024-01-01T00:00:00Z"})
    right = _card({"id": "org/tiny-gpt", "cardData": {"license": "apache-2.0"}, "lastModified": "2024-01-01T00:00:00Z"})
    assert left.repo_id != right.repo_id
    assert left.canonical_url != right.canonical_url
    assert left.license != right.license


def test_malformed_mismatched_and_oversized_payloads():
    collector = HuggingFaceCollector()
    with pytest.raises(CollectorFailure) as malformed:
        collector.parse(b"{", kind="model")
    assert malformed.value.error_class == "invalid_content"
    with pytest.raises(CollectorFailure) as listing:
        collector.parse(b"[]", kind="model")
    assert listing.value.error_class == "invalid_content"
    with pytest.raises(CollectorFailure) as missing:
        collector.parse(json.dumps({"error": "Repository not found"}).encode(), kind="model")
    assert missing.value.error_class == "not_found"
    oversized = b"{" + b" " * MAX_CARD_BYTES
    with pytest.raises(CollectorFailure) as too_large:
        collector.parse(oversized, kind="model")
    assert too_large.value.error_class == "content_too_large"

    def transport(url: str, headers: dict) -> FetchResult:
        body = json.dumps({"id": "other/repo", "cardData": {"license": "mit"}}).encode()
        return FetchResult(url=url, status=200, headers={"content-type": "application/json"}, body=body)

    mismatched = HuggingFaceCollector(
        fetcher=SafeFetcher(transport=transport, allowed_content_types=("application/json",), max_attempts=1)
    )
    with pytest.raises(CollectorFailure) as mismatch:
        mismatched.retrieve("org/model", kind="model")
    assert mismatch.value.error_class == "invalid_content"


def test_default_fetcher_is_one_bounded_request():
    fetcher = HuggingFaceCollector().fetcher
    assert fetcher.max_attempts == 1
    assert fetcher.max_redirects == 0
    assert fetcher.max_bytes < 200 * 1024
    assert fetcher.max_bytes < MAX_CARD_BYTES
    assert fetcher.allowed_content_types == ("application/json",)
