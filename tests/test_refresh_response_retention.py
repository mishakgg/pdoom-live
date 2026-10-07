"""Many-response fixtures exercise live runner buffers, without live collection."""
from pathlib import Path

import pytest

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.ingest.collection_state import CollectionState
from pdoom_pipeline.refresh.runner import run_refresh
from test_refresh import _people, _write_seed, NOW

PRIMARY = "https://bounded.example/feed"
BODY = b"x" * 65536
EXPIRY = "2026-10-02T00:00:00Z"


def closure_values(callable):
    return dict(zip(callable.__code__.co_freevars, (cell.cell_contents for cell in callable.__closure__ or [])))


def setup(tmp_path, monkeypatch, *, allow_raw, fail=False, request_count=100):
    seed = tmp_path / "seed"
    _write_seed(seed)
    lead = {"kind": "show_feed", "url": PRIMARY, "show_slug": "fixture", "source_type": "podcast",
            "collection_policy": {"admitted": True, "rights_basis": "Synthetic source permission", "evidence": False}}
    if allow_raw:
        lead["collection_policy"]["raw_retention"] = {"license": "CC0", "expires_at": EXPIRY}
    calls, witnessed = [], []
    def transport(url, headers):
        calls.append((url, dict(headers)))
        if url == PRIMARY and headers.get("if-none-match") == '"fixture"':
            return FetchResult(url, 304, {"etag": '"fixture"'}, b"")
        return FetchResult(url, 200, {"content-type": "text/plain", "etag": '"fixture"'}, BODY)
    client = SafeFetcher(transport=transport, sleep=lambda _: None, max_bytes=len(BODY))
    def synthetic_collector(*, fetch_bytes, **_kwargs):
        assert fetch_bytes(PRIMARY) == BODY
        for index in range(request_count):
            assert fetch_bytes(f"https://bounded.example/transcript/{index}") == BODY
        pending = closure_values(client.cache_put)["pending"]
        responses = closure_values(fetch_bytes)["responses"]
        witnessed.append({"pending_urls": set(pending), "raw_bytes": sum(map(len, pending.values())),
                          "response_urls": set(responses), "checkpoint_body_bytes": sum(len(row.body) for row in responses.values())})
        if fail:
            raise CollectorFailure("invalid_content", "synthetic terminal parse failure")
        return {"observations": [], "statements": [], "runs": []}
    monkeypatch.setattr("pdoom_pipeline.refresh.runner.collect_beliefs", synthetic_collector)
    def run(now=NOW):
        return run_refresh(seed_dir=seed, collection_dir=tmp_path / "collection", people=_people(),
                           leads=[lead], registry_sources=[], fetcher=client, now=now, completed_at=now,
                           max_sources=1, max_seconds=30)
    return run, lead, calls, witnessed


@pytest.mark.parametrize("allow_raw", [False, True])
@pytest.mark.parametrize("fail", [False, True])
def test_many_responses_retain_only_permitted_primary_and_body_free_metadata(tmp_path, monkeypatch, allow_raw, fail):
    run, _lead, _calls, witnessed = setup(tmp_path, monkeypatch, allow_raw=allow_raw, fail=fail)
    result = run()
    assert result["status"] == ("failed" if fail else "succeeded")
    captured = witnessed[-1]
    assert captured["pending_urls"] == ({PRIMARY} if allow_raw else set())
    assert captured["raw_bytes"] == (len(BODY) if allow_raw else 0)
    assert captured["response_urls"] == {PRIMARY}
    assert captured["checkpoint_body_bytes"] == 0
    state = CollectionState.load(tmp_path / "collection/state/collection_state.json")
    assert state.read_body(PRIMARY, now=NOW) == (BODY if allow_raw and not fail else None)
    assert state.raw_bodies.keys() == ({PRIMARY} if allow_raw and not fail else set())
    assert not result["document"]["statements"]
    assert not result["document"]["evidence_segments"]


@pytest.mark.parametrize("allow_raw", [False, True])
def test_304_recovery_preserves_policy_and_success(tmp_path, monkeypatch, allow_raw):
    run, _lead, calls, witnessed = setup(tmp_path, monkeypatch, allow_raw=allow_raw, request_count=3)
    assert run()["status"] == "succeeded"
    before = len(calls)
    again = run()
    assert again["status"] == "succeeded"
    primary_calls = [headers for url, headers in calls[before:] if url == PRIMARY]
    assert primary_calls[0].get("if-none-match") == '"fixture"'
    assert len(primary_calls) == (1 if allow_raw else 2)
    assert witnessed[-1]["raw_bytes"] == 0
    assert witnessed[-1]["checkpoint_body_bytes"] == 0
    state = CollectionState.load(tmp_path / "collection/state/collection_state.json")
    assert state.sources[PRIMARY]["last_success_at"] == NOW
    assert state.read_body(PRIMARY, now=NOW) == (BODY if allow_raw else None)


def test_expired_raw_policy_purges_body_and_recovers_without_retention(tmp_path, monkeypatch):
    run, _lead, calls, witnessed = setup(tmp_path, monkeypatch, allow_raw=True, request_count=3)
    assert run()["status"] == "succeeded"
    before = len(calls)
    assert run(now="2026-10-03T00:00:00Z")["status"] == "succeeded"
    assert len([url for url, _ in calls[before:] if url == PRIMARY]) == 2
    assert witnessed[-1]["pending_urls"] == set()
    assert witnessed[-1]["checkpoint_body_bytes"] == 0
    state = CollectionState.load(tmp_path / "collection/state/collection_state.json")
    assert not state.raw_bodies
    assert not state.body_path(PRIMARY).exists()


def test_revoked_raw_permission_does_not_keep_old_primary_body(tmp_path, monkeypatch):
    run, lead, _calls, witnessed = setup(tmp_path, monkeypatch, allow_raw=True, request_count=3)
    assert run()["status"] == "succeeded"
    del lead["collection_policy"]["raw_retention"]
    assert run()["status"] == "succeeded"
    assert witnessed[-1]["pending_urls"] == set()
    state = CollectionState.load(tmp_path / "collection/state/collection_state.json")
    assert not state.raw_bodies and not state.body_path(PRIMARY).exists()
