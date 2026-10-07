"""Offline source fairness and fail-closed admitted-adapter response validation."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from pdoom_pipeline.collectors.arxiv import ArxivCollector
from pdoom_pipeline.collectors.github import GitHubCollector
from pdoom_pipeline.collectors.openalex_works import OpenAlexWorksCollector
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.ingest.collection_state import CollectionState
from pdoom_pipeline.ingest.writes import atomic_bytes
from pdoom_pipeline.refresh.runner import run_refresh
from test_refresh import _people, _source, _write_seed, NOW

EMPTY_FEED = b'<rss><channel/></rss>'
EMPTY_ATOM = b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
LATER = "2026-10-02T00:00:00Z"


def sources():
    return [_source(f"src:person:refresh-ada:rss:{name}", f"https://fair.example/{name}", "rss_feed", "rss", True) for name in ("a", "b", "c")]


def refresh(tmp_path, registry, transport, **kwargs):
    seed = tmp_path / "seed"
    _write_seed(seed)
    return run_refresh(seed_dir=seed, collection_dir=tmp_path / "collection", people=_people(), leads=[], registry_sources=registry,
                       fetcher=SafeFetcher(transport=transport, sleep=lambda _: None, max_attempts=1), now=kwargs.pop("now", NOW),
                       completed_at=NOW, max_sources=kwargs.pop("max_sources", 1), **kwargs)


def load_state(tmp_path):
    return CollectionState.load(tmp_path / "collection/state/collection_state.json")


@pytest.mark.parametrize("problem", ["http_failure", "policy_failure", "cooldown"])
def test_bad_first_source_does_not_starve_later_sources(tmp_path, problem):
    rows = sources()
    calls = []
    if problem == "policy_failure":
        rows[0]["rights_notes"] = ""
    if problem == "cooldown":
        state = load_state(tmp_path)
        state.source(rows[0]["canonical_url"])["retry_not_before"] = LATER
        state.save()
    def transport(url, _headers):
        calls.append(url)
        return FetchResult(url, 503 if url.endswith('/a') else 200, {"content-type": "application/rss+xml", "retry-after": "10"}, EMPTY_FEED)
    first = refresh(tmp_path, rows, transport)
    assert first["status"] == "failed"
    assert first["cursor"] is None
    assert load_state(tmp_path).scan_cursor == rows[0]["id"]
    second = refresh(tmp_path, rows, transport)
    third = refresh(tmp_path, rows, transport)
    assert second["status"] == third["status"] == "succeeded"
    assert second["cursor"] == rows[1]["id"]
    assert third["cursor"] == rows[2]["id"]
    assert calls[-2:] == [rows[1]["canonical_url"], rows[2]["canonical_url"]]
    # Wraparound considers A without manufacturing a success or a new attempt in cooldown.
    before = deepcopy(load_state(tmp_path).sources.get(rows[0]["canonical_url"]))
    again = refresh(tmp_path, rows, transport)
    assert again["status"] == "failed"
    assert again["cursor"] == rows[2]["id"]
    assert load_state(tmp_path).scan_cursor == rows[0]["id"]
    if problem in {"http_failure", "cooldown"}:
        assert load_state(tmp_path).sources[rows[0]["canonical_url"]] == before
    assert refresh(tmp_path, rows, transport)["status"] == "succeeded"


def test_cancelled_before_item_does_not_advance_scan_or_success(tmp_path):
    rows = sources()
    result = refresh(tmp_path, rows, lambda *_: pytest.fail("cancelled source must not fetch"), cancelled=lambda: True)
    assert result["status"] == "failed"
    state = load_state(tmp_path)
    assert state.scan_cursor is None and state.cursor is None


def test_cancellation_keeps_only_considered_source_position(tmp_path):
    rows = sources()
    calls = []
    def transport(url, _headers):
        calls.append(url)
        return FetchResult(url, 200, {"content-type": "application/rss+xml"}, EMPTY_FEED)
    result = refresh(tmp_path, rows, transport, max_sources=3, cancelled=lambda: bool(calls))
    assert result["status"] == "partial"
    state = load_state(tmp_path)
    assert state.scan_cursor == state.cursor == rows[0]["id"]
    assert calls == [rows[0]["canonical_url"]]


def test_failed_checkpoint_write_does_not_durably_advance_scan(tmp_path):
    rows = sources()
    def transport(url, _headers):
        return FetchResult(url, 200, {"content-type": "application/rss+xml"}, EMPTY_FEED)
    def fail_checkpoint(path, body):
        if path.name == "collection_state.json":
            raise OSError("synthetic refused state write")
        atomic_bytes(path, body)
    with pytest.raises(OSError, match="refused state write"):
        refresh(tmp_path, rows, transport, write_bytes=fail_checkpoint)
    state = load_state(tmp_path)
    assert state.scan_cursor is None and state.cursor is None
    assert refresh(tmp_path, rows, transport)["cursor"] == rows[0]["id"]


def test_legacy_success_cursor_initializes_scan_without_repeating_first_source(tmp_path):
    rows = sources()
    state = load_state(tmp_path)
    state.cursor = rows[0]["id"]
    state.save()
    payload = json.loads(state.path.read_text())
    payload.pop("scan_cursor", None)
    state.path.write_text(json.dumps(payload))
    result = refresh(tmp_path, rows, lambda url, _: FetchResult(url, 200, {"content-type": "application/rss+xml"}, EMPTY_FEED))
    assert result["cursor"] == rows[1]["id"]
    assert load_state(tmp_path).scan_cursor == rows[1]["id"]


@pytest.mark.parametrize("payload", [b'<html><body>Maintenance</body></html>', b'<feed/>', b'<feed xmlns="https://wrong.example/atom"/>'])
def test_arxiv_wrong_root_is_not_an_empty_success(payload):
    with pytest.raises(CollectorFailure):
        ArxivCollector().parse(payload, source_identity="src:a", observed_at=NOW)


@pytest.mark.parametrize("payload", [b'[{}]', b'[42]', b'[{"full_name":"alice/repo"}]', b'[{"full_name":42,"html_url":"https://github.com/alice/repo"}]'])
def test_github_malformed_rows_are_not_an_empty_success(payload):
    with pytest.raises(CollectorFailure):
        GitHubCollector().parse_repos(payload, source_identity="src:a", username="alice", observed_at=NOW)


@pytest.mark.parametrize("payload", [b'{"results":[42]}', b'{"results":[{}]}', b'{"results":[null]}', b'{"results":[{"id":"https://openalex.org/Wwrong"}]}'])
def test_openalex_malformed_rows_are_not_an_empty_success(payload):
    with pytest.raises(CollectorFailure):
        OpenAlexWorksCollector().parse(payload, source_identity="src:a", observed_at=NOW)


def test_valid_empty_adapter_payloads_remain_valid():
    assert ArxivCollector().parse(EMPTY_ATOM, source_identity="src:a", observed_at=NOW) == []
    assert GitHubCollector().parse_repos(b'[]', source_identity="src:a", username="alice", observed_at=NOW) == []
    assert OpenAlexWorksCollector().parse(b'{"results":[]}', source_identity="src:a", observed_at=NOW) == []


@pytest.mark.parametrize("adapter,method,url,valid,invalid,ctype", [
    ("arxiv", "arxiv_api", "https://export.arxiv.org/api/query", EMPTY_ATOM, b'<html/>', "application/xml"),
    ("github", "github_api", "https://github.com/alice", b'[]', b'[{}]', "application/json"),
    ("openalex", "openalex_api", "https://api.openalex.org/works?filter=authorships.author.id:A123", b'{"results":[]}', b'{"results":[42]}', "application/json"),
])
def test_malformed_response_preserves_last_good_validators_and_success(tmp_path, adapter, method, url, valid, invalid, ctype):
    source = _source(f"src:person:refresh-ada:{adapter}", url, method, "rss", True)
    if adapter == "arxiv":
        source["search_query"] = "au:Alice"
    body = {"value": valid, "etag": '"good"'}
    def transport(request_url, _headers):
        return FetchResult(request_url, 200, {"content-type": ctype, "etag": body["etag"]}, body["value"])
    assert refresh(tmp_path, [source], transport)["status"] == "succeeded"
    before = load_state(tmp_path)
    success = {key: (row["last_success_at"], row["etag"]) for key, row in before.sources.items()}
    body.update(value=invalid, etag='"bad"')
    result = refresh(tmp_path, [source], transport, now=LATER)
    after = load_state(tmp_path)
    assert result["status"] == "failed" and result["counts"]["failed"] == 1
    assert result["cursor"] == before.cursor
    assert {key: (row["last_success_at"], row["etag"]) for key, row in after.sources.items()} == success
    assert all(row["last_outcome"] == "failed" for row in after.sources.values())


def test_mixed_good_and_malformed_rows_fail_as_one_source():
    valid_repo = {"full_name": "alice/example", "html_url": "https://github.com/alice/example", "name": "example"}
    with pytest.raises(CollectorFailure):
        GitHubCollector().parse_repos(json.dumps([valid_repo, {}]).encode(), source_identity="src:a", username="alice", observed_at=NOW)
    valid_work = {"id": "https://openalex.org/W1", "display_name": "Example"}
    with pytest.raises(CollectorFailure):
        OpenAlexWorksCollector().parse(json.dumps({"results": [valid_work, None]}).encode(), source_identity="src:a", observed_at=NOW)
    with pytest.raises(CollectorFailure):
        ArxivCollector().parse(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry xmlns=""/></feed>', source_identity="src:a", observed_at=NOW)


def test_runner_reports_its_imported_extractor_version(tmp_path, monkeypatch):
    from pdoom_pipeline.refresh import runner
    from pdoom_pipeline.extract.statements import EXTRACTOR_VERSION
    assert runner.EXTRACTOR_VERSION == EXTRACTOR_VERSION
    monkeypatch.setattr(runner, "EXTRACTOR_VERSION", "synthetic-extractor-version")
    result = refresh(tmp_path, sources(), lambda url, _: FetchResult(url, 200, {"content-type": "application/rss+xml"}, EMPTY_FEED))
    assert result["result"]["extractor_version"] == "synthetic-extractor-version"
