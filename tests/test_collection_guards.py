"""Offline regressions for admission, retention, identity and truthful checkpoints."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.ingest.collection_state import CollectionState
from pdoom_pipeline.refresh.runner import _work_items, run_refresh
from pdoom_pipeline.refresh.runtime import adapter_source, call_adapter
from pdoom_pipeline.rights import collection_policy
from pdoom_pipeline.urls import canonicalize_url
from test_refresh import ESSAY, FEED, NOW, _Script, _leads, _people, _refresh, _source, _sources, _write_seed

LATER = "2026-10-01T13:00:00Z"
EXPIRY = "2026-10-02T00:00:00Z"
FEED_URL = "https://refresh.example/feed.xml"


def _policy(**changes):
    return {"admitted": True, "rights_basis": "Fixture source permission, reviewed by curator.", **changes}


def _run(tmp_path, *, sources=None, leads=None, pages=None, now=NOW, **options):
    seed = tmp_path / "seed"
    _write_seed(seed)
    client = SafeFetcher(transport=_Script(pages or {FEED_URL: (FEED.encode(), "application/rss+xml", '"good"')}), sleep=lambda _: None)
    return run_refresh(seed_dir=seed, collection_dir=tmp_path / "collection", people=_people(),
                       registry_sources=_sources() if sources is None else sources,
                       leads=[] if leads is None else leads, fetcher=client, now=now,
                       completed_at=now, max_sources=40, **options)


def _state(tmp_path):
    return json.loads((tmp_path / "collection/state/collection_state.json").read_text())


@pytest.mark.parametrize("row,lead", [({}, False), ({"enabled": True}, False), ({"basis": ""}, True), ({"enabled": False, "basis": "curated"}, True)])
def test_admission_is_explicit(row, lead):
    assert not collection_policy(row, now=NOW, lead=lead).admitted


def test_public_availability_and_prose_do_not_grant_raw_retention():
    row = {"enabled": True, "rights_notes": "Public page, open access, copyable CC-BY."}
    assert collection_policy(row, now=NOW).admitted
    assert collection_policy(row, now=NOW).raw_until is None
    row["collection_policy"] = _policy(raw_retention={"license": "CC-BY-ND-4.0", "expires_at": EXPIRY})
    assert collection_policy(row, now=NOW).raw_until == EXPIRY
    assert collection_policy(row, now=EXPIRY).raw_until is None


@pytest.mark.parametrize("raw", [{}, {"license": "unknown", "expires_at": EXPIRY}, {"license": "CC0", "expires_at": "2026-10-02"}])
def test_raw_retention_requires_license_and_zoned_expiry(raw):
    with pytest.raises(CollectorFailure, match="raw retention"):
        collection_policy({"collection_policy": _policy(raw_retention=raw)}, now=NOW)


@pytest.mark.parametrize("url", ["https://evil.example/alice", "https://github.com/alice/repos", "https://github.com/alice?next=bob", "https://github.com/alice#bob", "https://github.com@evil.example/alice", "https://github.com/alice%2Fbob", "https://github.com/alice--bob"])
def test_github_url_cannot_redirect_identity(url):
    with pytest.raises(CollectorFailure):
        adapter_source({"id": "src:alice", "canonical_url": url, "collection_method": "github_api"})


def test_platform_external_id_must_agree():
    with pytest.raises(CollectorFailure):
        adapter_source({"id": "src:a", "canonical_url": "https://github.com/alice", "external_id": "bob", "collection_method": "github_api"})
    with pytest.raises(CollectorFailure):
        adapter_source({"id": "src:a", "canonical_url": "https://api.openalex.org/works?filter=authorships.author.id:A123", "external_id": "A456", "collection_method": "openalex_api"})
    valid = adapter_source({"id": "src:a", "canonical_url": "https://api.openalex.org/works?filter=authorships.author.id:A123", "external_id": "A123", "collection_method": "openalex_api"})
    assert valid["openalex_author_id"] == "A123"
    assert "per-page=25" in valid["url"]


@pytest.mark.parametrize("url", ["https://evil.example/works?filter=authorships.author.id:A123", "https://api.openalex.org/works?filter=authorships.author.id:A123,A456", "https://api.openalex.org/works?filter=authorships.author.id:A123&filter=authorships.author.id:A456", "https://api.openalex.org/works?filter=authorships.author.id:A123&search=other"])
def test_openalex_filter_is_one_exact_identity(url):
    with pytest.raises(CollectorFailure):
        adapter_source({"id": "src:a", "canonical_url": url, "collection_method": "openalex_api"})


@pytest.mark.parametrize("url", ["https://evil.example/youtube.com/watch?v=abcdefghi", "https://evil.example/arxiv.org/abs/2401.12345", "https://evil.example/openalex.org/A123", "https://notdoi.org/10.1234/hello"])
def test_canonicalization_cannot_change_a_foreign_host(url):
    assert canonicalize_url(url) == url


@pytest.mark.parametrize("body", [b"<evilfeed/>", b"<html><channel/></html>", b"<rss><channel>", b"<feed xmlns='https://evil.example/atom'/>"])
def test_invalid_feed_is_not_an_empty_success(body):
    with pytest.raises(CollectorFailure):
        RssCollector().parse(body, source_identity="src:a", feed_url=FEED_URL, observed_at=NOW)


def test_304_cannot_mask_a_parser_failure():
    fetcher = SafeFetcher(transport=lambda url, _: FetchResult(url, 304, {}, b""))
    fetcher.cache_get = lambda _: b"<not-a-feed/>"
    with pytest.raises(CollectorFailure):
        call_adapter("rss", fetcher=fetcher, source={"source_identity": "src:a", "url": FEED_URL}, observed_at=NOW)


def test_repeated_304_without_a_body_fails():
    fetcher = SafeFetcher(transport=lambda url, _: FetchResult(url, 304, {}, b""))
    with pytest.raises(CollectorFailure, match="validated retained body"):
        fetcher.get(FEED_URL)


def test_adapter_parse_failure_does_not_commit_or_advance(tmp_path):
    first = _run(tmp_path)
    assert first["status"] == "succeeded"
    before = _state(tmp_path)
    second = _run(tmp_path, now=LATER, pages={FEED_URL: (b"<html/>", "application/rss+xml", '"bad"')})
    after = _state(tmp_path)
    assert second["status"] == "failed"
    assert after["cursor"] == before["cursor"]
    assert after["sources"][FEED_URL]["last_success_at"] == NOW
    assert after["sources"][FEED_URL]["etag"] == '"good"'
    assert after["sources"][FEED_URL]["content_versions"] == before["sources"][FEED_URL]["content_versions"]
    assert second["document"]["source_items"] == first["document"]["source_items"]


def test_belief_parser_failure_and_robots_denial_are_truthful(tmp_path):
    lead = {"kind": "owned_feed", "url": FEED_URL, "person_slug": "refresh-ada", "source_type": "blog", "basis": "Fixture feed authored by Refresh Ada."}
    first = _run(tmp_path, leads=[lead])
    assert first["status"] == "succeeded"
    before = _state(tmp_path)
    bad = _run(tmp_path, leads=[lead], now=LATER, pages={FEED_URL: (b"<rss>", "application/rss+xml", '"bad"')})
    after = _state(tmp_path)
    assert bad["status"] == "failed"
    assert after["cursor"] == before["cursor"]
    assert after["sources"][FEED_URL]["etag"] == '"good"'
    assert after["sources"][FEED_URL]["last_success_at"] == NOW
    assert after["items"] == before["items"]
    essay = _leads(include_older=False)
    denied = _run(tmp_path / "denied", leads=essay, pages={"https://refresh.example/notes": (ESSAY.encode(), "text/html", '"e"')}, cancelled=lambda: True)
    assert denied["status"] == "failed"
    assert all(not row.get("last_success_at") for row in _state(tmp_path / "denied")["sources"].values())


def test_default_retention_never_persists_full_feed_body(tmp_path):
    result = _run(tmp_path)
    assert result["status"] == "succeeded"
    assert not list((tmp_path / "collection/state/bodies").glob("*"))
    saved = json.loads((tmp_path / "collection/state/observations.json").read_text())
    assert all("upstream_version" not in version["metadata"] for item in saved["items"] for version in item["versions"])


def test_permitted_raw_cache_expires_and_legacy_cache_is_purged(tmp_path):
    sources = _sources()
    sources[1]["collection_policy"] = _policy(raw_retention={"license": "CC0", "expires_at": EXPIRY})
    _run(tmp_path, sources=sources)
    state = CollectionState.load(tmp_path / "collection/state/collection_state.json")
    assert state.read_body(FEED_URL, now=NOW) == FEED.encode()
    legacy = state.body_path("https://refresh.example/unlicensed")
    legacy.write_bytes(b"unlicensed body")
    _run(tmp_path, sources=sources, now="2026-10-03T00:00:00Z")
    assert not legacy.exists()
    assert not state.body_path(FEED_URL).exists()
    assert _state(tmp_path)["raw_bodies"] == {}


def test_revoked_policy_removes_cached_evidence_and_statements(tmp_path):
    lead = _leads(include_older=False)
    pages = {"https://refresh.example/notes": (ESSAY.encode(), "text/html", '"e"')}
    first = _run(tmp_path, leads=lead, sources=[], pages=pages)
    assert first["document"]["statements"]
    lead[0]["collection_policy"] = _policy(evidence=False)
    second = _run(tmp_path, leads=lead, sources=[], pages=pages, now=LATER)
    assert not second["document"]["statements"]
    assert not second["document"]["evidence_segments"]
    assert not _state(tmp_path)["items"]["https://refresh.example/notes"]["statements"]
    assert "locators" not in _state(tmp_path)["items"]["https://refresh.example/notes"]["item"]


def test_disabled_registry_cannot_be_bypassed_by_lead(tmp_path):
    sources = _sources()
    sources[0]["enabled"] = False
    result = _run(tmp_path, sources=sources, leads=_leads(include_older=False))
    assert result["counts"]["failed"] == 1
    assert not result["document"]["statements"]
    assert "https://refresh.example/notes" not in _state(tmp_path)["sources"]


def test_identity_retarget_is_rejected_before_fetch_and_export(tmp_path):
    sources = _sources()
    _run(tmp_path, sources=sources)
    sources[1]["canonical_url"] = "https://evil.example/redirected-feed.xml"
    result = _run(tmp_path, sources=sources, now=LATER)
    assert result["status"] == "failed"
    assert not result["document"]["source_items"]
    assert "https://evil.example/redirected-feed.xml" not in _state(tmp_path)["sources"]


def test_duplicate_identity_or_lead_is_not_silently_attributed():
    sources = _sources()
    duplicate = deepcopy(sources[1])
    duplicate["canonical_url"] = "https://evil.example/feed"
    work = _work_items(sources + [duplicate], [], NOW)
    assert all(item.get("error") for item in work)
    leads = _leads(include_older=False)
    work = _work_items([], leads + [{**leads[0], "person_slug": "another-person"}], NOW)
    assert all(item.get("error") for item in work)


def test_untrusted_fetch_alias_and_transcript_never_reach_transport(tmp_path):
    lead = _leads(include_older=False)
    lead[0]["fetch_url"] = "https://evil.example/stolen"
    result = _run(tmp_path, sources=[], leads=lead)
    assert result["status"] == "failed"
    assert not _state(tmp_path)["sources"]


def test_all_outputs_use_the_injected_atomic_sink(tmp_path):
    calls = []
    def sink(path, payload):
        assert path.is_absolute()
        assert path.is_relative_to(tmp_path)
        assert isinstance(payload, bytes)
        calls.append(path.relative_to(tmp_path).as_posix())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    sources = _sources()
    sources[1]["collection_policy"] = _policy(raw_retention={"license": "CC0", "expires_at": EXPIRY})
    result = _run(tmp_path, sources=sources, write_bytes=sink)
    assert result["status"] == "succeeded"
    expected = {"collection/state/collection_state.json", "collection/state/observations.json", "collection/staging/belief/observations.jsonl", "collection/staging/belief/statements.jsonl", "collection/staging/belief/runs.jsonl", "collection/staging/belief/summary.json", "collection/canonical-live.json"}
    assert expected.issubset(calls)
    assert any(path.startswith("collection/state/bodies/") for path in calls)
    assert not list((tmp_path / "collection").rglob("*.tmp"))


def test_sink_refusal_keeps_last_successful_checkpoint(tmp_path):
    _run(tmp_path)
    before = (tmp_path / "collection/state/collection_state.json").read_bytes()
    def refuse(path, payload):
        raise OSError("quota reservation refused")
    with pytest.raises(OSError, match="quota"):
        _run(tmp_path, now=LATER, write_bytes=refuse)
    assert (tmp_path / "collection/state/collection_state.json").read_bytes() == before


def test_failed_source_cursor_is_not_a_success_checkpoint(tmp_path):
    state = CollectionState(tmp_path / "state.json")
    state.record_outcome("url", outcome="fetched", now=NOW, success=True, cursor="accepted")
    state.record_outcome("url", outcome="failed", now=LATER, success=False, cursor="failed")
    assert state.sources["url"]["cursor"] == "accepted"


def test_valid_empty_feed_is_a_successful_check(tmp_path):
    result = _run(tmp_path, pages={FEED_URL: (b"<rss><channel/></rss>", "application/rss+xml", '"empty"')})
    assert result["status"] == "succeeded"
    assert _state(tmp_path)["sources"][FEED_URL]["last_success_at"] == NOW


def test_previous_registry_shape_remains_admitted():
    directory = Path(__file__).resolve().parents[1] / "data/seed/cohort/v2026-09"
    sources = [json.loads(line) for line in (directory / "sources.jsonl").read_text().splitlines() if line]
    leads = [json.loads(line) for line in (directory / "belief_sources.jsonl").read_text().splitlines() if line]
    assert len(sources) == 312
    assert sum(row.get("enabled") and row.get("continuously_collectible") for row in sources) == 263
    work = _work_items(sources, leads, NOW)
    assert not [item for item in work if item.get("error")]
    assert not any(item["policy"].raw_until for item in work)


def test_lock_probe_never_signals_its_own_process(monkeypatch):
    import os
    from pdoom_pipeline.refresh.lock import _alive
    def forbidden(*args):
        raise AssertionError("liveness must not signal this process")
    monkeypatch.setattr(os, "kill", forbidden)
    assert _alive(os.getpid())


def test_windows_lock_probe_uses_handle_api_without_signals(monkeypatch):
    import os
    import pdoom_pipeline.refresh.lock as lock
    calls = []
    monkeypatch.setattr(lock, "_windows_alive", lambda pid: calls.append(pid) or True)
    monkeypatch.setattr(os, "kill", lambda *args: pytest.fail("Windows must never call os.kill"))
    original = os.name
    try:
        os.name = "nt"
        assert lock._alive(12345678)
    finally:
        os.name = original
    assert calls == [12345678]


def test_live_old_lock_is_never_stolen(tmp_path):
    import os
    from pdoom_pipeline.refresh.lock import RefreshLock, RefreshOverlap
    path = tmp_path / "old.lock"
    path.write_text(json.dumps({"pid": os.getpid(), "started_at": "2000-01-01T00:00:00Z"}))
    with pytest.raises(RefreshOverlap):
        RefreshLock(path).acquire()
    assert path.exists()


def test_unreadable_lock_is_not_deleted(tmp_path):
    from pdoom_pipeline.refresh.lock import RefreshLock, RefreshOverlap
    path = tmp_path / "unfinished.lock"
    path.write_text("")
    with pytest.raises(RefreshOverlap):
        RefreshLock(path).acquire()
    assert path.exists()


def test_robots_denial_cannot_advance_success(tmp_path, monkeypatch):
    original = _Script.__call__
    calls = []
    def transport(self, url, headers):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FetchResult(url, 200, {"content-type": "text/plain"}, b"User-agent: *\nDisallow: /\n")
        return original(self, url, headers)
    monkeypatch.setattr(_Script, "__call__", transport)
    result = _run(tmp_path, sources=[], leads=_leads(include_older=False))
    assert result["status"] == "failed"
    assert "https://refresh.example/notes" not in calls
    assert not _state(tmp_path)["sources"]["https://refresh.example/notes"]["last_success_at"]


def test_foreign_transport_response_is_rejected(tmp_path, monkeypatch):
    original = _Script.__call__
    def transport(self, url, headers):
        result = original(self, url, headers)
        result.url = "https://evil.example/feed"
        return result
    monkeypatch.setattr(_Script, "__call__", transport)
    result = _run(tmp_path)
    assert result["status"] == "failed"
    assert not result["document"]["source_items"]


def test_collector_bug_is_truthful_not_a_crash(tmp_path, monkeypatch):
    import pdoom_pipeline.refresh.runtime as runtime
    def broken(*args, **kwargs):
        raise ValueError("bad parser")
    monkeypatch.setattr(runtime, "_collect", broken)
    result = _run(tmp_path)
    assert result["status"] == "failed"
    assert _state(tmp_path)["sources"][FEED_URL]["errors"][-1]["error_class"] == "collector_bug"


def test_legacy_lead_checkpoint_adopts_only_matching_owner(tmp_path):
    lead = _leads(include_older=False)
    pages = {"https://refresh.example/notes": (ESSAY.encode(), "text/html", '"e"')}
    _run(tmp_path, leads=lead, sources=[], pages=pages)
    state_path = tmp_path / "collection/state/collection_state.json"
    state = _state(tmp_path)
    state["bindings"] = {}
    state["sources"][lead[0]["url"]]["source_identity"] = "refresh-ada"
    state_path.write_text(json.dumps(state))
    good = _run(tmp_path, leads=lead, sources=[], pages=pages, now=LATER)
    assert good["status"] == "succeeded"
    assert _state(tmp_path)["sources"][lead[0]["url"]]["source_identity"] == "lead:" + lead[0]["url"]
    state = _state(tmp_path)
    state["bindings"] = {}
    state["sources"][lead[0]["url"]]["source_identity"] = "someone-else"
    state_path.write_text(json.dumps(state))
    refused = _run(tmp_path, leads=lead, sources=[], pages=pages, now="2026-10-01T14:00:00Z")
    assert refused["status"] == "failed"
    assert not refused["document"]["statements"]


def test_legacy_openalex_failure_preserves_registry_success(tmp_path):
    source = _source("src:person:refresh-ada:openalex", "https://api.openalex.org/works?filter=authorships.author.id:A123", "openalex_api", "openalex_works", True)
    source["external_id"] = "A123"
    state = CollectionState(tmp_path / "collection/state/collection_state.json")
    state.record_attempt(source["canonical_url"], identity=source["id"], url=source["canonical_url"], now=NOW)
    state.record_outcome(source["canonical_url"], outcome="fetched", now=NOW, success=True, etag='"old"')
    state.save()
    result = _run(tmp_path, sources=[source], now=LATER)
    assert result["status"] == "failed"
    key = adapter_source(source)["url"]
    saved = _state(tmp_path)["sources"][key]
    assert saved["last_success_at"] == NOW
    assert saved["etag"] == '"old"'
    assert result["result"]["refresh"]["checks"][source["canonical_url"]]["last_success_at"] == NOW
