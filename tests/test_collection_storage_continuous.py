"""Continuous queue tests use only small local files and synthetic transports."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import os

import pytest

from test_collection_storage import FakeDrive, PIN, registry
from pdoom_pipeline.collection_storage.bootstrap import synthetic_smoke
from pdoom_pipeline.collection_storage.continuous import (
    ContinuousQueue, ReviewedProfile, QueueLimits, SourceSlice, RecoveryPin,
    JOURNAL, INDEX, PAYLOAD, SNAPSHOT,
)
from pdoom_pipeline.collection_storage.continuous_feed import MetadataFeedProducer
from pdoom_pipeline.collection_storage.pilot import admitted_sources
from pdoom_pipeline.collection_storage.scratch import BoundedScratch, ScratchPaths, StorageStop, CHUNK_BYTES
from pdoom_pipeline.collection_storage.supervisor import CHECKPOINT, PENDING
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher, FetchResult

pytestmark = pytest.mark.skipif(os.name != "posix", reason="real POSIX scratch fixture")


class Drive(FakeDrive):
    def __init__(self):
        super().__init__()
        self.download_sizes = []
        self.corrupt_download = False

    def download_chunks(self, file_id, *, chunk_bytes, max_bytes):
        row = next(r for r in self.sessions.values() if r["id"] == file_id and len(r["data"]) == r["size"])
        raw = row["data"]
        if self.corrupt_download:
            raw = raw[:-1] + bytes([raw[-1] ^ 1])
        assert len(raw) <= max_bytes
        for offset in range(0, len(raw), chunk_bytes):
            block = raw[offset:offset + chunk_bytes]
            self.download_sizes.append(len(block))
            yield block


class Clock:
    value = 10000.0
    def __call__(self): return self.value
    def advance(self, seconds=120): self.value += seconds


@pytest.fixture
def rig(tmp_path):
    seed = tmp_path / "seed"
    seed.mkdir()
    paths = ScratchPaths(mode="posix", workspace_base=tmp_path,
                         collection_root=tmp_path / "collection", seed_root=seed)
    drive, clock = Drive(), Clock()
    rows = registry()
    pin_file = Path(__file__).parents[1] / "pipeline/pdoom_pipeline/collection_storage/pilot_sources.json"
    profile = ReviewedProfile("fixture-one", "1", (json.loads(pin_file.read_text())[0],), 3)
    limits = QueueLimits(shard_bytes=16384, record_bytes=4096, state_bytes=65536,
                         index_entries=20, records_per_shard=8)
    with BoundedScratch(paths=paths, free_bytes=lambda _: 10**12) as scratch:
        synthetic_smoke(scratch=scratch, drive=drive, pin=PIN)
        def queue(**kwargs):
            return ContinuousQueue(scratch=scratch, drive=drive, pin=PIN, profile=profile,
                                   stream_id="fixture-stream", limits=limits, clock=clock, **kwargs)
        yield scratch, drive, clock, profile, rows, queue


def item(key="a", title="Title"):
    return {"upstream_id": key, "canonical_url": f"https://example.org/{key}", "title": title,
            "published_at": "2026-10-01T00:00:00Z", "observed_at": "2026-10-08T00:00:00Z", "author": "Holden Karnofsky"}


def producer(*items, cursor="next", etag='"etag"', call_log=None):
    def call(source, state, max_items, stop):
        if call_log is not None: call_log.append((source, state, max_items))
        return SourceSlice(iter(items), cursor_after=cursor, etag=etag)
    return call


def run(rig, collect=None, **kwargs):
    s, d, c, p, rows, queue = rig
    return queue().run_cycle(registry=rows, producer=collect or producer(item()), released=True, **kwargs)


def state_rows(s):
    return [json.loads(line) for line in s.path(INDEX).read_text().splitlines()]


def remote_payloads(d):
    return [r["data"] for r in d.sessions.values() if r["meta"]["name"].endswith("-metadata.jsonl")]


def test_repeated_cycles_dedup_versions_and_bounded_local_history(rig):
    s, d, c, p, rows, q = rig
    a = run(rig)
    log = []
    b = run(rig, producer(item(), call_log=log))
    c = run(rig, producer(item(title="Updated")))
    d3 = run(rig, producer(item()))  # old version repeated is also deduplicated
    assert [r["generation"] for r in (a,b,c,d3)] == [1,2,3,4]
    assert [json.loads(raw)["content_version"] for raw in remote_payloads(d)] == [1,2]
    assert log[0][1]["etag"] == '"etag"'
    assert len(state_rows(s)) == 3
    assert not s.path(PAYLOAD).exists() and not s.path(SNAPSHOT).exists()
    assert not s.path(PENDING).exists()
    assert s.usage() < 10000
    assert max(d.download_sizes) <= CHUNK_BYTES


def test_profile_is_explicit_and_legacy_exact_eight_unchanged(rig):
    s,d,c,p,rows,q = rig
    assert len(admitted_sources(rows)) == 8
    assert len(p.validate(rows)) == 1
    with pytest.raises(StorageStop):
        ReviewedProfile("subset", "1", (), 1)
    with pytest.raises(StorageStop):
        ReviewedProfile("subset", "1", (dict(p.source_pins[0], rights_notes="different"),), 1)
    with pytest.raises(StorageStop):
        ReviewedProfile("subset", "1", (p.source_pins[0],p.source_pins[0]), 1)
    with pytest.raises(StorageStop, match="release"):
        q().run_cycle(registry=rows, producer=producer(item()))


@pytest.mark.parametrize("change", ["rights_notes", "canonical_url", "enabled", "collection_policy", "allowed_fetch_origins"])
def test_rights_and_origin_changes_fail_before_fetch_or_upload(rig, change):
    s,d,c,p,rows,q = rig
    target = next(row for row in rows if row["id"] == p.source_pins[0]["id"])
    target[change] = {"admitted": False} if change == "collection_policy" else ["https://example.org"] if change == "allowed_fetch_origins" else False if change == "enabled" else "changed"
    before = len(d.begun)
    with pytest.raises(StorageStop, match="rights or origin"):
        run(rig, lambda *args: pytest.fail("fetch occurred"))
    assert len(d.begun) == before


@pytest.mark.parametrize("field", ["body", "evidence", "segments", "summary", "statements", "forecasts", "article_text"])
def test_record_whitelist_rejects_raw_and_public_content(rig, field):
    s,d,c,p,rows,q = rig
    checkpoint = s.read_json(CHECKPOINT)
    with pytest.raises(StorageStop, match="disallowed"):
        run(rig, producer(dict(item(), **{field: "RAW_BODY_SENTINEL"})))
    assert s.read_json(CHECKPOINT) == checkpoint
    assert not remote_payloads(d)


def test_dedup_limit_fails_closed_without_eviction_or_cursor_reset(rig):
    s,d,c,p,rows,q = rig
    limited = ContinuousQueue(scratch=s, drive=d, pin=PIN, profile=p, stream_id="limited",
                             limits=replace(q().limits, index_entries=1), clock=c)
    limited.run_cycle(registry=rows, producer=producer(item()), released=True)
    checkpoint = s.read_json(CHECKPOINT)
    with pytest.raises(StorageStop, match="no silent eviction"):
        limited.run_cycle(registry=rows, producer=producer(item("b")), released=True)
    assert s.read_json(CHECKPOINT) == checkpoint and len(state_rows(s)) == 2
    assert limited.run_cycle(registry=rows, producer=producer(item()), released=True)["generation"] == 2


class Crash(BaseException): pass


@pytest.mark.parametrize("phase", ["payload_written", "snapshot_written", "sealed", "uploading", "supervisor_committed", "manifest_verified", "index_installed", "checkpoint_installed", "cleanup"])
def test_crash_at_every_transition_recovers_without_duplicate_upload(rig, phase):
    s,d,c,p,rows,q = rig
    def crash(point):
        if point == phase: raise Crash()
    with pytest.raises(Crash):
        q(fault=crash).run_cycle(registry=rows, producer=producer(item()), released=True)
    before = len(remote_payloads(d))
    result = run(rig)
    assert result["status"] == "committed" and result["generation"] == 1
    assert len(remote_payloads(d)) == 1 and before <= 1
    assert len(state_rows(s)) == 2 and not s.path(PENDING).exists()


@pytest.mark.parametrize("failure", ["fail_chunk", "lose_final", "fail_manifest"])
def test_upload_failure_and_lost_reply_keep_ids_with_bounded_backoff(rig, failure):
    s,d,c,p,rows,q = rig
    setattr(d, failure, True)
    with pytest.raises(StorageStop): run(rig)
    first = list(d.begun)
    assert run(rig)["reason"] == "backoff"
    assert d.begun == first
    setattr(d, failure, False)
    c.advance()
    assert run(rig)["status"] == "committed"
    assert len(remote_payloads(d)) == 1
    assert len(set(d.begun)) == len(d.begun)


def test_expired_session_reuses_durable_file_id(rig):
    s,d,c,p,rows,q = rig
    d.fail_chunk = True
    with pytest.raises(StorageStop): run(rig)
    pending = s.read_json(PENDING)
    first_id = pending["entries"][0]["remote_id"]
    d.sessions.clear()
    c.advance()
    assert run(rig)["status"] == "committed"
    assert d.begun.count(first_id) == 2
    assert len(remote_payloads(d)) == 1


@pytest.mark.parametrize("fault", ["account", "root", "checksum", "download"])
def test_remote_receipt_mismatch_prevents_queue_commit(rig, fault):
    s,d,c,p,rows,q = rig
    checkpoint = s.read_json(CHECKPOINT)
    if fault == "account": d.user["emailAddress"] = "other@example.org"
    if fault == "root": d.remote[PIN.folder_id]["permissions"].append({"type": "anyone"})
    if fault == "checksum": d.corrupt = True
    if fault == "download": d.corrupt_download = True
    with pytest.raises(StorageStop): run(rig)
    journal = s.read_json(JOURNAL)
    assert not journal or journal["phase"] != "cleaning"
    assert not s.path(INDEX).exists()
    if fault != "download": assert s.read_json(CHECKPOINT) == checkpoint


def test_full_quota_blocks_before_fetch_and_committed_cleanup_needs_zero(rig):
    s,d,c,p,rows,q = rig
    d.quota["usage"] = d.quota["limit"]
    with pytest.raises(StorageStop, match="quota"):
        run(rig, lambda *args: pytest.fail("fetch admitted at full quota"))
    d.quota["usage"] = "0"
    def crash(phase):
        if phase == "checkpoint_installed": raise Crash()
    with pytest.raises(Crash):
        q(fault=crash).run_cycle(registry=rows, producer=producer(item()), released=True)
    d.quota["usage"] = d.quota["limit"]
    uploads = len(d.begun)
    assert run(rig)["status"] == "committed"
    assert len(d.begun) == uploads


def test_partial_source_failure_is_truthful_and_has_durable_backoff(rig):
    s,d,c,p,rows,q = rig
    pins = json.loads((Path(__file__).parents[1] / "pipeline/pdoom_pipeline/collection_storage/pilot_sources.json").read_text())[:2]
    profile = ReviewedProfile("two", "1", tuple(pins), 1)
    queue = ContinuousQueue(scratch=s, drive=d, pin=PIN, profile=profile, stream_id="two", limits=q().limits, clock=c)
    calls = []
    def collect(source, *args):
        calls.append(source["id"])
        if source["id"] == pins[1]["id"]:
            raise CollectorFailure("rate_limited", "upstream secret must not be logged", retry_after=60)
        return SourceSlice([item()])
    result = queue.run_cycle(registry=rows, producer=collect, released=True)
    assert result["outcome"] == "partial"
    queue.run_cycle(registry=rows, producer=collect, released=True)
    assert calls.count(pins[1]["id"]) == 1
    assert b"upstream secret" not in s.path(INDEX).read_bytes()


def test_cancellation_and_deadline_stop_before_producer(rig):
    s,d,c,p,rows,q = rig
    never = lambda *args: pytest.fail("producer should not run")
    assert run(rig, never, cancelled=lambda: True)["reason"] == "cancelled_or_deadline"
    assert run(rig, never, deadline=c())["reason"] == "cancelled_or_deadline"
    assert not remote_payloads(d)


def test_timer_and_record_seals_do_not_advance_incomplete_source_cursor(rig):
    s,d,c,p,rows,q = rig
    def collect(*args):
        def rows():
            yield item("a")
            c.advance(301)
            yield item("b")
        return SourceSlice(rows(), cursor_after="must-not-advance", etag="must-not-advance")
    result = run(rig, collect)
    assert result["outcome"] == "interrupted"
    assert state_rows(s)[0]["sources"] == {}
    assert len(remote_payloads(d)) == 1
    assert run(rig, producer(item("a"),item("b")))["generation"] == 2
    assert len(state_rows(s)) == 3


def test_capacity_hysteresis_counts_outstanding_reservation_and_foreign_bytes(rig, monkeypatch):
    s,d,c,p,rows,q = rig
    queue = q()
    limits = queue.limits
    usage = [limits.pause_bytes - limits.reservation]
    real = s.usage
    monkeypatch.setattr(s, "usage", lambda: usage[0])
    assert run(rig)["reason"] == "capacity"
    usage[0] = limits.resume_bytes - limits.reservation + 1
    assert run(rig)["reason"] == "capacity"
    monkeypatch.setattr(s, "usage", real)
    assert run(rig)["status"] == "committed"


def test_low_disk_guard_applies_before_fetch(rig):
    s,d,c,p,rows,q = rig
    s.free_bytes = lambda _: 5_000_000_000
    with pytest.raises(StorageStop, match="reserve"):
        run(rig, lambda *args: pytest.fail("source fetched at reserve"))


def test_missing_index_does_not_reset_dedup(rig):
    s,d,c,p,rows,q = rig
    run(rig)
    s.path(INDEX).unlink()
    with pytest.raises((StorageStop, FileNotFoundError)):
        run(rig, lambda *args: pytest.fail("silent reset"))


def test_restore_exact_head_replays_duplicates_and_retains_versions(rig, tmp_path):
    s,d,c,p,rows,q = rig
    first = run(rig)
    run(rig, producer(item(title="Updated")))
    head = q()._head()
    # New scratch has no old local cursor/index; remote head selection is explicit.
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    seed = fresh / "seed"
    seed.mkdir()
    paths = ScratchPaths(mode="posix", workspace_base=fresh, collection_root=fresh/"collection", seed_root=seed)
    with BoundedScratch(paths=paths, free_bytes=lambda _: 10**12) as s2:
        queue = ContinuousQueue(scratch=s2, drive=d, pin=PIN, profile=p, stream_id="fixture-stream", limits=q().limits, clock=c)
        pin = RecoveryPin(head["manifest_id"], head["manifest_sha256"], 2)
        with pytest.raises(StorageStop, match="sole coordinator"):
            queue.restore(pin)
        assert queue.restore(pin, sole_coordinator_confirmed=True)["generation"] == 2
        before = len(remote_payloads(d))
        assert queue.run_cycle(registry=rows, producer=producer(item()), released=True)["generation"] == 3
        assert len(remote_payloads(d)) == before
        queue.run_cycle(registry=rows, producer=producer(item(title="Third")), released=True)
        assert json.loads(remote_payloads(d)[-1])["content_version"] == 3


@pytest.mark.parametrize("fault", ["hash", "generation", "profile", "missing_snapshot", "root"])
def test_restore_wrong_head_or_missing_state_fails_closed(rig, tmp_path, fault):
    s,d,c,p,rows,q = rig
    result = run(rig)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    seed = fresh / "seed"
    seed.mkdir()
    if fault == "profile": p = replace(p, version="2")
    if fault == "root": d.remote[PIN.folder_id]["permissions"].append({"type":"anyone"})
    if fault == "missing_snapshot":
        entry = next(r for r in d.sessions.values() if r["meta"]["name"].endswith("-state.jsonl"))
        del d.remote[entry["id"]]
    paths = ScratchPaths(mode="posix", workspace_base=fresh, collection_root=fresh/"collection", seed_root=seed)
    with BoundedScratch(paths=paths, free_bytes=lambda _: 10**12) as s2:
        queue = ContinuousQueue(scratch=s2, drive=d, pin=PIN, profile=p, stream_id="fixture-stream", limits=q().limits, clock=c)
        pin = RecoveryPin(result["manifest_id"], "0"*64 if fault=="hash" else result["manifest_sha256"], 2 if fault=="generation" else 1)
        with pytest.raises(StorageStop): queue.restore(pin, sole_coordinator_confirmed=True)
        assert not s2.path(INDEX).exists() and not s2.read_json(CHECKPOINT)


def test_limits_cannot_expand_cap_or_erase_minimum_disk_reserve(rig):
    s,d,c,p,rows,q = rig
    for kwargs in ({"shard_bytes": 65*1024*1024}, {"pause_bytes":25_000_000_000}, {"index_entries":65537}, {"seal_seconds":301}):
        with pytest.raises(StorageStop): QueueLimits(**kwargs)
    s.min_free_bytes = 0
    with pytest.raises(StorageStop, match="five GB"): q()


def test_ordinary_connector_cannot_be_substituted_for_full_backend(rig):
    s,d,c,p,rows,q = rig
    with pytest.raises(StorageStop, match="connector is insufficient"):
        ContinuousQueue(scratch=s, drive=object(), pin=PIN, profile=p, stream_id="no-forged-quota")


def test_feed_adapter_checks_robots_and_strips_all_body_content(rig):
    s,d,c,p,rows,q = rig
    feed = b'<rss><channel><item><guid>a</guid><link>https://example.org/a</link><title>Safe title</title><author>Holden Karnofsky</author><description>RAW_BODY_SENTINEL</description></item></channel></rss>'
    calls = []
    def transport(url, headers):
        calls.append((url,headers))
        return FetchResult(url,200,{"content-type":"application/rss+xml", "etag":'"one"'},feed)
    factory = lambda: SafeFetcher(transport=transport, max_bytes=1_000_000)
    denied = MetadataFeedProducer(robots_allowed=lambda *_: False,fetcher_factory=factory)
    with pytest.raises(StorageStop, match="policy"):
        run(rig, denied)
    assert calls == []
    allowed = MetadataFeedProducer(robots_allowed=lambda *_: True,fetcher_factory=factory)
    assert run(rig, allowed)["status"] == "committed"
    assert len(calls) == 1
    assert all(b"RAW_BODY_SENTINEL" not in r["data"] for r in d.sessions.values())


def test_feed_adapter_accepts_conditional_304_without_body_cache(rig):
    s,d,c,p,rows,q = rig
    run(rig, producer(item(), cursor=None))
    calls=[]
    def transport(url, headers):
        calls.append(headers)
        return FetchResult(url,304,{},b"")
    adapter = MetadataFeedProducer(robots_allowed=lambda *_:True,
        fetcher_factory=lambda: SafeFetcher(transport=transport))
    before=len(remote_payloads(d))
    assert run(rig,adapter)["status"] == "committed"
    assert calls[0]["if-none-match"] == '"etag"'
    assert len(remote_payloads(d)) == before


@pytest.mark.parametrize("phase", ["restore_journal", "restore_checkpoint", "manifest_verified", "index_installed", "checkpoint_installed", "cleanup"])
def test_restore_interrupted_installation_never_uploads_again(rig, tmp_path, phase):
    s,d,c,p,rows,q = rig
    result = run(rig)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    seed = fresh / "seed"
    seed.mkdir()
    paths = ScratchPaths(mode="posix", workspace_base=fresh, collection_root=fresh/"collection", seed_root=seed)
    def crash(point):
        if point == phase: raise Crash()
    with BoundedScratch(paths=paths, free_bytes=lambda _: 10**12) as s2:
        kwargs = dict(scratch=s2,drive=d,pin=PIN,profile=p,stream_id="fixture-stream",limits=q().limits,clock=c)
        queue = ContinuousQueue(**kwargs, fault=crash)
        before = len(d.begun)
        with pytest.raises(Crash):
            queue.restore(RecoveryPin(result["manifest_id"],result["manifest_sha256"],1), sole_coordinator_confirmed=True)
        restored = ContinuousQueue(**kwargs).run_cycle(registry=rows,producer=lambda *args: pytest.fail("restore refetched"),released=True)
        assert restored["generation"] == 1 and len(d.begun) == before
        assert len(state_rows(s2)) == 2


def test_mutated_local_snapshot_cannot_become_committed_index(rig):
    s,d,c,p,rows,q = rig
    def crash(phase):
        if phase == "supervisor_committed": raise Crash()
    with pytest.raises(Crash):
        q(fault=crash).run_cycle(registry=rows,producer=producer(item()),released=True)
    raw = s.path(SNAPSHOT).read_bytes()
    s.atomic_bytes(SNAPSHOT,[raw.replace(b'"version":1',b'"version":2')],max_bytes=len(raw))
    with pytest.raises(StorageStop,match="checksum"):
        run(rig)
    assert not s.path(INDEX).exists() and s.path(PAYLOAD).exists()


def test_mutated_index_cannot_silently_accept_duplicate_as_new(rig):
    s,d,c,p,rows,q = rig
    run(rig)
    raw = s.path(INDEX).read_bytes()
    s.atomic_bytes(INDEX,[raw.replace(b'"version":1',b'"version":2')],max_bytes=len(raw))
    with pytest.raises(StorageStop,match="checksum"):
        run(rig)


@pytest.mark.parametrize("limit", ["bytes", "records"])
def test_shard_limit_seals_at_record_boundary_without_advancing_source(rig, limit):
    s,d,c,p,rows,q = rig
    limits = replace(q().limits,shard_bytes=1024,record_bytes=1024) if limit=="bytes" else replace(q().limits,records_per_shard=1)
    queue=ContinuousQueue(scratch=s,drive=d,pin=PIN,profile=p,stream_id="bounded",limits=limits,clock=c)
    result=queue.run_cycle(registry=rows,producer=producer(item("a"),item("b")),released=True)
    assert result["outcome"] == "interrupted"
    assert len(remote_payloads(d)[-1].splitlines()) == 1
    assert state_rows(s)[0]["sources"] == {}


def test_upload_retry_limit_is_explicit_and_durable(rig):
    s,d,c,p,rows,q=rig
    for _ in range(q().limits.retry_attempts):
        d.fail_chunk=True
        with pytest.raises(StorageStop): run(rig)
        c.advance()
    before=len(d.begun)
    with pytest.raises(StorageStop,match="attempt bound"):
        run(rig)
    assert len(d.begun)==before and s.path(PENDING).exists() and s.path(PAYLOAD).exists()


def test_writer_lock_and_root_namespace_remain_protected(rig):
    s,d,c,p,rows,q=rig
    with pytest.raises(StorageStop,match="another collection writer"):
        with BoundedScratch(paths=s.paths,free_bytes=lambda _:10**12): pass
    for stream in ("../writer.lock","writer.lock/writing","/absolute"):
        with pytest.raises(StorageStop):
            ContinuousQueue(scratch=s,drive=d,pin=PIN,profile=p,stream_id=stream)
    before=s.path("writer.lock").stat().st_ino
    run(rig)
    assert s.path("writer.lock").stat().st_ino==before


def test_actual_write_guard_accounts_for_logs_temp_and_cache(rig,monkeypatch):
    s,d,c,p,rows,q=rig
    for name in ("logs/log", "temp/partial", "cache/cache"):
        s.atomic_bytes(name,[b"x"*100],max_bytes=100)
    assert s.usage()>=300
    checks=[]
    original=s.check_write
    def check(size,**kwargs):
        checks.append(size)
        return original(size,**kwargs)
    monkeypatch.setattr(s,"check_write",check)
    run(rig,producer(item("a"),item("b")))
    assert 0 in checks and q().limits.reservation in checks
    assert len([n for n in checks if 0<n<=CHUNK_BYTES])>10
    assert all(s.path(name).read_bytes()==b"x"*100 for name in ("logs/log","temp/partial","cache/cache"))


def test_many_duplicate_cycles_plateau_without_growing_local_corpus(rig):
    s,d,c,p,rows,q=rig
    import tracemalloc
    tracemalloc.start()
    sizes=[]
    try:
        for _ in range(20):
            run(rig)
            sizes.append(s.usage())
        _,peak=tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert len(remote_payloads(d))==1 and len(state_rows(s))==2
    # Generation one has no preceding collection hash; subsequent heads do.
    assert max(sizes[1:])-min(sizes[1:])<100
    assert max(sizes)<4096
    assert peak<16*1024*1024  # bounded fixture plateau, not a full-capacity benchmark


def test_rights_change_blocks_already_sealed_upload(rig):
    s,d,c,p,rows,q=rig
    def crash(phase):
        if phase=="sealed": raise Crash()
    with pytest.raises(Crash):
        q(fault=crash).run_cycle(registry=rows,producer=producer(item()),released=True)
    next(row for row in rows if row["id"]==p.source_pins[0]["id"])["enabled"]=False
    before=len(d.begun)
    with pytest.raises(StorageStop,match="rights or origin"):
        run(rig)
    assert len(d.begun)==before and s.path(PAYLOAD).exists()


def test_unknown_lost_completion_is_redacted_and_reconciles_same_id(rig):
    s,d,c,p,rows,q=rig
    chunk=d.chunk
    failed=[False]
    def unknown(*args):
        result=chunk(*args)
        if not failed[0]:
            failed[0]=True
            raise RuntimeError("SECRET_TOKEN_MUST_NOT_ESCAPE")
        return result
    d.chunk=unknown
    with pytest.raises(StorageStop,match="outcome unknown") as error:
        run(rig)
    assert "SECRET_TOKEN" not in str(error.value)
    c.advance()
    assert run(rig)["status"]=="committed"
    assert len(remote_payloads(d))==1 and len(d.begun)==len(set(d.begun))


def test_low_disk_midstream_preserves_previous_checkpoint(rig):
    s,d,c,p,rows,q=rig
    checkpoint=s.read_json(CHECKPOINT)
    def collect(*args):
        def records():
            yield item("a")
            s.free_bytes=lambda _:5_000_000_000
            yield item("b")
        return SourceSlice(records())
    with pytest.raises(StorageStop,match="reserve"):
        run(rig,collect)
    assert s.read_json(CHECKPOINT)==checkpoint and not s.path(INDEX).exists()
    assert not s.path(PAYLOAD+".writing").exists()


def test_cancellation_keeps_sealed_partial_for_later_reconciliation(rig):
    s,d,c,p,rows,q=rig
    cancelled=[False]
    def collect(*args):
        def records():
            yield item("a")
            cancelled[0]=True
            yield item("b")
        return SourceSlice(records(),cursor_after="incomplete")
    with pytest.raises(StorageStop,match="cancelled"):
        run(rig,collect,cancelled=lambda:cancelled[0])
    assert s.path(PAYLOAD).exists() and s.read_json(JOURNAL)["phase"]=="sealed"
    cancelled[0]=False
    c.advance()
    result=run(rig,lambda *args:pytest.fail("sealed data refetched"))
    assert result["outcome"]=="interrupted" and state_rows(s)[0]["sources"]=={}


@pytest.mark.parametrize("phase", ["checkpoint_installed", "cleanup"])
def test_post_commit_storage_stop_preserves_cleaning_journal(rig, phase):
    s,d,c,p,rows,q=rig
    def stop(point):
        if point==phase: raise StorageStop("post-commit local metadata fault")
    with pytest.raises(StorageStop):
        q(fault=stop).run_cycle(registry=rows,producer=producer(item()),released=True)
    assert s.read_json(JOURNAL)["phase"]=="cleaning"
    before=len(d.begun)
    assert run(rig)["status"]=="committed" and len(d.begun)==before


def feed_adapter(feed, calls=None, author="Holden Karnofsky"):
    def transport(url,headers):
        if calls is not None: calls.append(headers)
        content=feed() if callable(feed) else feed
        return FetchResult(url,304 if 'if-none-match' in headers else 200,
            {"content-type":"application/rss+xml","etag":'"whole-feed"'},
            b"" if 'if-none-match' in headers else content)
    return MetadataFeedProducer(robots_allowed=lambda *_:True,
        fetcher_factory=lambda:SafeFetcher(transport=transport))


def xml_feed(keys, *, author="Holden Karnofsky", stable=True):
    return ('<rss><channel>'+''.join(
        f'<item><title>{key}</title><author>{author}</author>'+
        (f'<guid>{key}</guid><link>https://example.org/{key}</link>' if stable else '')+'</item>'
        for key in keys)+'</channel></rss>').encode()


def test_feed_continuation_consumes_tail_before_saving_whole_feed_validators(rig):
    s,d,c,p,rows,q=rig
    calls=[]
    adapter=feed_adapter(xml_feed(["a","b","c","d"]),calls)
    first=run(rig,adapter)
    assert first["outcome"]=="partial" and len(state_rows(s))==4
    source=state_rows(s)[0]["sources"][p.source_pins[0]["id"]]
    assert source["etag"] is None and json.loads(source["cursor"])["offset"]==3
    second=run(rig,adapter)
    assert second["outcome"]=="succeeded" and len(state_rows(s))==5
    assert 'if-none-match' not in calls[1]
    assert state_rows(s)[0]["sources"][p.source_pins[0]["id"]]["cursor"] is None
    run(rig,adapter)
    assert calls[2]['if-none-match']=='"whole-feed"'
    assert [json.loads(line)["upstream_id"] for raw in remote_payloads(d) for line in raw.splitlines()]==["a","b","c","d"]


def test_changed_feed_resets_bound_offset_without_forgetting_dedup(rig):
    s,d,c,p,rows,q=rig
    feed=[xml_feed(["a","b","c","d"])]
    adapter=feed_adapter(lambda:feed[0])
    run(rig,adapter)
    feed[0]=xml_feed(["new","a","b","c","d"])
    assert run(rig,adapter)["outcome"]=="partial"
    assert run(rig,adapter)["outcome"]=="succeeded"
    ids=[json.loads(line)["upstream_id"] for raw in remote_payloads(d) for line in raw.splitlines()]
    assert ids==["a","b","c","new","d"]


def test_interrupted_feed_page_does_not_advance_continuation(rig):
    s,d,c,p,rows,q=rig
    queue=ContinuousQueue(scratch=s,drive=d,pin=PIN,profile=p,stream_id="small",
        limits=replace(q().limits,records_per_shard=1),clock=c)
    result=queue.run_cycle(registry=rows,producer=feed_adapter(xml_feed(["a","b","c","d"])),released=True)
    assert result["outcome"]=="interrupted" and state_rows(s)[0]["sources"]=={}


@pytest.mark.parametrize("existing", [False,True])
def test_not_modified_with_records_fails_closed(rig,existing):
    s,d,c,p,rows,q=rig
    if existing: run(rig,producer(item(),cursor=None))
    checkpoint=s.read_json(CHECKPOINT)
    with pytest.raises(StorageStop,match="304"):
        run(rig,lambda *args:SourceSlice([item("new")],not_modified=True))
    assert s.read_json(CHECKPOINT)==checkpoint


@pytest.mark.parametrize("author", ["Different Author", "", "Holden Karnofsky and Guest"])
def test_author_rule_filters_guests_before_metadata_retention(rig,author):
    s,d,c,p,rows,q=rig
    assert run(rig,feed_adapter(xml_feed(["guest"],author=author)))["status"]=="committed"
    assert len(state_rows(s))==1 and not remote_payloads(d)
    with pytest.raises(StorageStop,match="author rule"):
        run(rig,producer(dict(item("b"),author=author)))


def test_statement_candidate_pin_is_not_silently_admitted_to_metadata_only(rig):
    s,d,c,p,rows,q=rig
    pins=json.loads((Path(__file__).parents[1]/"pipeline/pdoom_pipeline/collection_storage/pilot_sources.json").read_text())
    p2=ReviewedProfile("conditional","1",(pins[-1],),1)
    queue=ContinuousQueue(scratch=s,drive=d,pin=PIN,profile=p2,stream_id="conditional",limits=q().limits,clock=c)
    with pytest.raises(StorageStop,match="statement candidate"):
        queue.run_cycle(registry=rows,producer=lambda *args:pytest.fail("must not fetch"),released=True)
    assert len(admitted_sources(rows))==8


def test_ambiguous_positional_identity_is_never_retained(rig):
    s,d,c,p,rows,q=rig
    result=run(rig,feed_adapter(xml_feed(["First","Second"],stable=False)))
    assert result["outcome"]=="failed" and not remote_payloads(d)
    assert len(state_rows(s))==1
    c.advance()
    result=run(rig,feed_adapter(xml_feed(["Second","First"],stable=False)))
    assert result["outcome"]=="failed" and not remote_payloads(d)


def test_default_user_agent_has_no_unverified_email_address():
    producer=MetadataFeedProducer(robots_allowed=lambda *_:True)
    assert producer.fetcher_factory().user_agent=="pdoom.live-collector/0.1 (+https://github.com/mishakgg/pdoom-live)"


def test_cleanup_rejects_changed_checkpoint_before_deleting_inputs(rig):
    s,d,c,p,rows,q=rig
    def stop(phase):
        if phase=="checkpoint_installed": raise Crash()
    with pytest.raises(Crash):
        q(fault=stop).run_cycle(registry=rows,producer=producer(item()),released=True)
    checkpoint=s.read_json(CHECKPOINT)
    changed={**checkpoint,"manifest_id":"another-head"}
    s.atomic_json(CHECKPOINT,changed)
    with pytest.raises(StorageStop,match="cleanup head"):
        run(rig)
    assert s.path(PAYLOAD).exists() and s.path(SNAPSHOT).exists()
    s.atomic_json(CHECKPOINT,checkpoint)
    assert run(rig)["status"]=="committed"


@pytest.mark.parametrize("extra", [
    '<author>Guest</author>',
    '<dc:creator>Guest</dc:creator>',
    '<author></author>',
    '<author><name>Holden Karnofsky</name><name>Guest</name></author>',
])
def test_all_rss_author_declarations_are_checked(rig,extra):
    s,d,c,p,rows,q=rig
    feed=('<rss xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><item><guid>x</guid>'
          '<link>https://example.org/x</link><title>X</title><author>Holden Karnofsky</author>'+
          extra+'</item></channel></rss>').encode()
    run(rig,feed_adapter(feed))
    assert not remote_payloads(d) and len(state_rows(s))==1


def test_namespaced_atom_identity_and_exact_author_are_supported(rig):
    s,d,c,p,rows,q=rig
    feed=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>atom-x</id><title>X</title>
      <link rel="self" href="https://example.org/api/x"/>
      <link rel="alternate" href="https://example.org/x"/>
      <author><name>Holden Karnofsky</name></author><published>2026-10-08T00:00:00Z</published>
      <summary>RAW_BODY_SENTINEL</summary></entry></feed>'''
    assert run(rig,feed_adapter(feed))["outcome"]=="succeeded"
    row=json.loads(remote_payloads(d)[0])
    assert row["upstream_id"]=="atom-x" and row["canonical_url"]=="https://example.org/x"
    assert row["author"]=="Holden Karnofsky" and b"RAW_BODY_SENTINEL" not in remote_payloads(d)[0]


def test_atom_multiple_authors_do_not_pass_first_author_match(rig):
    s,d,c,p,rows,q=rig
    feed=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>x</id><title>X</title>
      <link href="https://example.org/x"/><author><name>Holden Karnofsky</name></author>
      <author><name>Guest</name></author></entry></feed>'''
    run(rig,feed_adapter(feed))
    assert not remote_payloads(d)


def test_missing_guid_uses_stable_canonical_item_link(rig):
    s,d,c,p,rows,q=rig
    feed=b'''<rss><channel><item><link>https://example.org/x</link><author>Holden Karnofsky</author>
      </item></channel></rss>'''
    assert run(rig,feed_adapter(feed))["outcome"]=="succeeded"
    assert json.loads(remote_payloads(d)[0])["upstream_id"]=="https://example.org/x"


@pytest.mark.parametrize("content", [
    '<guid>one</guid><guid>two</guid><link>https://example.org/x</link>',
    '<guid>one</guid><link>https://example.org/x</link><link>https://example.org/y</link>',
    '<link>https://www.cold-takes.com/rss/</link>',
])
def test_ambiguous_identity_and_feed_link_fail_closed(rig,content):
    s,d,c,p,rows,q=rig
    feed=('<rss><channel><item><title>X</title><author>Holden Karnofsky</author>'+content+'</item></channel></rss>').encode()
    assert run(rig,feed_adapter(feed))["outcome"]=="failed"
    assert not remote_payloads(d)


@pytest.mark.parametrize("author", [
    '<author><name>Holden Karnofsky</name> and Different Author</author>',
    '<author><name>Holden Karnofsky</name><x:name xmlns:x="https://invalid.example/ns">Different Author</x:name></author>',
    '<author>Different Author<name>Holden Karnofsky</name></author>',
    '<author><name>Holden Karnofsky</name><email><name>Guest</name></email></author>',
    '<author><x:name xmlns:x="https://invalid.example/ns">Holden Karnofsky</x:name></author>',
])
def test_mixed_or_foreign_author_person_construct_fails_closed(rig,author):
    s,d,c,p,rows,q=rig
    feed=('<rss><channel><item><guid>x</guid><link>https://example.org/x</link><title>X</title>'+
          author+'</item></channel></rss>').encode()
    assert run(rig,feed_adapter(feed))["outcome"]=="failed"
    assert not remote_payloads(d)


def test_standard_atom_author_email_uri_fields_are_ancillary(rig):
    s,d,c,p,rows,q=rig
    feed=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>x</id><title>X</title>
      <link href="https://example.org/x"/><author><name>Holden Karnofsky</name>
      <email>fixture@example.org</email><uri>https://example.org/author</uri></author></entry></feed>'''
    assert run(rig,feed_adapter(feed))["outcome"]=="succeeded"
    assert json.loads(remote_payloads(d)[0])["author"]=="Holden Karnofsky"
    assert b"fixture@example.org" not in remote_payloads(d)[0]
