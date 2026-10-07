"""Run the actual refresh write seam against synthetic admitted feeds and Drive."""
import inspect
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from test_collection_storage import FakeDrive, PIN, root, scratch
from pdoom_pipeline.collection_storage.bootstrap import synthetic_smoke
from pdoom_pipeline.collection_storage.pilot import admitted_sources, run_metadata_pilot
from pdoom_pipeline.collection_storage.scratch import METADATA_RESERVE, StorageStop
from pdoom_pipeline.collection_storage.supervisor import CHECKPOINT, PENDING
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.refresh.runner import run_refresh

SEED = Path(__file__).resolve().parents[1] / "data/seed/cohort/v2026-09"
REGISTRY = [json.loads(line) for line in (SEED / "sources.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
NOW = "2026-10-07T05:00:00Z"
MARKER = "UNPERMITTED_RAW_BODY_SENTINEL"


@pytest.fixture
def fetcher():
    called = []
    selected = admitted_sources(REGISTRY)
    urls = {source["canonical_url"] for source in selected}
    def transport(url, headers):
        assert url in urls, "pilot fetched a destination outside the exact admitted feeds"
        called.append(url)
        p = urlsplit(url)
        body = f"""<rss version="2.0"><channel><title>Fixture</title><item>
<title>Fixture metadata</title><guid>{url}/fixture-guid</guid>
<link>{p.scheme}://{p.netloc}/fixture-post</link><author>Fixture author</author>
<description>{MARKER}</description><pubDate>Wed, 07 Oct 2026 04:00:00 GMT</pubDate>
</item></channel></rss>""".encode()
        return FetchResult(url=url, status=200, headers={"content-type":"application/rss+xml"}, body=body)
    return SafeFetcher(transport=transport, sleep=lambda n: None, max_bytes=6_000_000), called


def require_hook():
    assert "write_bytes" in inspect.signature(run_refresh).parameters, \
        "collection readiness write-hook dependency must be present in CI and before live release"


def test_real_runner_outputs_are_guarded_metadata_and_verified_before_cleanup(root, fetcher):
    require_hook()
    client, called = fetcher
    d = FakeDrive()
    with scratch() as s:
        synthetic_smoke(s, d, PIN)
        result = run_metadata_pilot(scratch=s, drive=d, pin=PIN, seed_dir=SEED, people=[],
                    registry_sources=REGISTRY, refresh=run_refresh, fetcher=client, released=True, now=NOW)
        assert result["cursor_after"]["status"] == "succeeded"
        assert result["cursor_after"]["counts"]["new"] == 8
        assert result["cursor_after"]["public_import"] is False
        assert result["cursor_after"]["publication"] == {"imported": False, "public_revocations_applied": False}
        decisions = result["cursor_after"]["policy_decisions"]
        assert len(decisions) == 8
        assert all(d["admitted"] and not d["evidence"] and not d["extraction"] and d["raw_until"] is None for d in decisions)
        assert len(called) == 8 and len(set(called)) == 8
        assert not list(s.path("runner").rglob("*.json"))
        assert not list(s.path("runner").rglob("*.jsonl"))
        assert not list(s.path("runner").rglob("*.bin"))
        assert not s.path(PENDING).exists()
        payloads = [row["data"] for row in d.sessions.values()]
        assert all(MARKER.encode() not in payload for payload in payloads)
        canonical = next(json.loads(row["data"]) for row in d.sessions.values()
                         if row["meta"]["name"].endswith("-canonical-live.json"))
        assert canonical["statements"] == [] and canonical["forecasts"] == []
        assert canonical["evidence_segments"] == []
        assert s.usage() < METADATA_RESERVE


def test_real_runner_cap_stop_leaves_smoke_checkpoint_and_never_uploads_partial_run(root, fetcher, monkeypatch):
    require_hook()
    client, called = fetcher
    d = FakeDrive()
    with scratch() as s:
        smoke = synthetic_smoke(s, d, PIN)
        before = len(d.begun)
        original = s.atomic_bytes
        def bounded(relative, chunks, *, max_bytes, metadata=False):
            if relative == "runner/state/observations.json":
                raise StorageStop("fixture quota stop during actual runner state write")
            return original(relative, chunks, max_bytes=max_bytes, metadata=metadata)
        monkeypatch.setattr(s, "atomic_bytes", bounded)
        with pytest.raises(StorageStop, match="quota stop"):
            run_metadata_pilot(scratch=s, drive=d, pin=PIN, seed_dir=SEED, people=[],
                    registry_sources=REGISTRY, refresh=run_refresh, fetcher=client, released=True, now=NOW)
        assert s.read_json(CHECKPOINT) == smoke
        assert not s.path(PENDING).exists()
        assert len(d.begun) == before
        assert len(called) == 1
        assert not s.path("runner/state/observations.json").exists()


def test_real_runner_failed_feed_remains_partial_in_remote_checkpoint(root, fetcher):
    require_hook()
    client, called = fetcher
    first = admitted_sources(REGISTRY)[0]["canonical_url"]
    transport = client.transport
    def one_failure(url, headers):
        if url == first:
            called.append(url)
            return FetchResult(url=url,status=403,headers={},body=b"blocked fixture")
        return transport(url, headers)
    client.transport = one_failure
    d = FakeDrive()
    with scratch() as s:
        synthetic_smoke(s, d, PIN)
        result = run_metadata_pilot(scratch=s, drive=d, pin=PIN, seed_dir=SEED, people=[],
                    registry_sources=REGISTRY, refresh=run_refresh, fetcher=client, released=True, now=NOW)
        assert result["cursor_after"]["status"] == "partial"
        assert result["cursor_after"]["counts"]["failed"] == 1
        assert result["cursor_after"]["counts"]["new"] == 7
        assert len(called) == 8
