"""Offline refresh: fetch, versions, stable ids, partial failure, and publication."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.export.identity import candidate_key_for, evidence_slug, statement_slug
from pdoom_pipeline.export.publish import publication_decision
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.ingest.collection_state import CollectionState
from pdoom_pipeline.ingest.store import ObservationStore
from pdoom_pipeline.observability.metrics import observe_collection_run, render, reset_metrics
from pdoom_pipeline.refresh.lock import RefreshLock, RefreshOverlap
from pdoom_pipeline.refresh.runner import run_refresh

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "refresh"
NOW = "2026-10-01T12:00:00Z"
DONE = "2026-10-01T12:05:00Z"
TYPES = (
    "application/rss+xml",
    "application/xml",
    "text/xml",
    "text/plain",
    "text/html",
    "application/json",
)

ESSAY = """<!DOCTYPE html><html><head><title>Refresh Ada notes</title>
<meta name="author" content="Refresh Ada">
<time datetime="2024-06-01T00:00:00Z">June 2024</time></head><body>
<p>Refresh Ada writes that the chance of human extinction from AI is 15% by 2070.</p>
<p>A serious risk of disempowerment is plausible.</p>
</body></html>
"""
ESSAY_CHANGED = ESSAY.replace("from AI", "from ML")
OLDER = """<!DOCTYPE html><html><head><title>Refresh Ada earlier note</title>
<meta name="author" content="Refresh Ada">
<time datetime="2020-01-01T00:00:00Z">January 2020</time></head><body>
<p>Refresh Ada writes that serious risk of extinction is unlikely before 2030.</p>
</body></html>
"""
FEED = """<?xml version="1.0"?><rss version="2.0"><channel><title>Refresh Ada</title>
<item><title>Feed note</title><link>https://refresh.example/feed/note</link>
<pubDate>Mon, 02 Jun 2025 00:00:00 GMT</pubDate><author>Refresh Ada</author>
<description>Refresh Ada published a short excerpt on this feed.</description>
</item></channel></rss>
"""
FEED_INSERTED = FEED.replace(
    "</channel>",
    """<item><title>Earlier feed note</title><link>https://refresh.example/feed/earlier</link>
<pubDate>Mon, 02 Jan 2024 00:00:00 GMT</pubDate><author>Refresh Ada</author>
<description>An older excerpt inserted ahead of the existing feed note.</description>
</item></channel>""",
)


def test_fetcher_304_retry_after_deadline_and_cancel():
    calls = []

    def transport(url: str, headers: dict) -> FetchResult:
        calls.append((url, dict(headers)))
        if headers.get("if-none-match") == '"v1"':
            return FetchResult(url=url, status=304, headers={"etag": '"v1"'}, body=b"")
        return FetchResult(url=url, status=200, headers={"content-type": "text/plain", "etag": '"v1"'}, body=b"page")

    cache = {}
    fetcher = SafeFetcher(transport=transport, sleep=lambda _s: None, max_attempts=2, allowed_content_types=("text/plain",))
    fetcher.cache_get = cache.get
    fetcher.cache_put = lambda url, body, _headers: cache.__setitem__(url, body)
    first = fetcher.get("https://example.com/page")
    assert first.status == 200
    assert first.not_modified is False
    second = fetcher.get("https://example.com/page", headers={"If-None-Match": '"v1"'})
    assert second.status == 304
    assert second.not_modified is True
    assert second.body == b"page"

    bare = SafeFetcher(transport=transport, sleep=lambda _s: None, max_attempts=1, allowed_content_types=("text/plain",))
    bare.header_provider = lambda _url: {"If-None-Match": '"v1"'}
    recovered = bare.get("https://example.com/other")
    assert recovered.status == 200
    assert recovered.not_modified is False
    assert any("if-none-match" not in headers for _url, headers in calls if _url.endswith("/other"))

    slept = []

    def limited(url: str, headers: dict) -> FetchResult:
        return FetchResult(url=url, status=429, headers={"content-type": "text/plain", "retry-after": "5"}, body=b"")

    limited_fetcher = SafeFetcher(transport=limited, sleep=slept.append, max_attempts=2, allowed_content_types=("text/plain",))
    with pytest.raises(CollectorFailure) as rate:
        limited_fetcher.get("https://example.com/slow")
    assert rate.value.error_class == "rate_limited"
    assert rate.value.retry_after == 5
    assert slept == [5]

    clock = {"now": 0.0}

    def unavailable(url: str, headers: dict) -> FetchResult:
        return FetchResult(url=url, status=503, headers={"content-type": "text/plain", "retry-after": "30"}, body=b"")

    def advance(seconds: float) -> None:
        clock["now"] += seconds

    deadline = SafeFetcher(transport=unavailable, sleep=advance, max_attempts=3, allowed_content_types=("text/plain",))
    deadline.clock = lambda: clock["now"]
    deadline.deadline_at = 10
    with pytest.raises(CollectorFailure) as late:
        deadline.get("https://example.com/down")
    assert "deadline" in str(late.value)

    cancelled = SafeFetcher(transport=transport, sleep=lambda _s: None, max_attempts=3, allowed_content_types=("text/plain",))
    cancelled.cancelled = lambda: True
    with pytest.raises(CollectorFailure) as stopped:
        cancelled.get("https://example.com/page")
    assert stopped.value.retryable is False

    paced = []
    pace_clock = {"now": 0.0}

    def pace_sleep(seconds: float) -> None:
        paced.append(seconds)
        pace_clock["now"] += seconds

    host = SafeFetcher(transport=transport, sleep=pace_sleep, max_attempts=1, allowed_content_types=("text/plain",))
    host.clock = lambda: pace_clock["now"]
    host.host_interval = 0.25
    host.get("https://example.com/a")
    host.get("https://example.com/b")
    assert paced == [0.25]


def test_store_keeps_versions_across_reorder_and_reload(tmp_path: Path):
    store = ObservationStore()
    first = _observation("https://example.com/a", "one", "hash-one")
    second = _observation("https://example.com/b", "two", "hash-two")
    assert store.ingest(first).status == "new"
    assert store.ingest(second).status == "new"
    changed = _observation("https://example.com/a", "one changed", "hash-one-b")
    again = store.ingest(changed)
    assert again.status == "version_changed"
    assert again.content_version == 2
    restored = store.ingest(first)
    assert restored.status == "unchanged"
    assert restored.content_version == 1
    path = tmp_path / "observations.json"
    store.save(path)
    loaded = ObservationStore.load(path)
    assert loaded.ingest(second).status == "unchanged"
    assert [version["content_version"] for version in loaded.items[loaded.by_url["https://example.com/a"]].versions] == [1, 2]


def test_collection_state_bounds_errors_and_retry_window(tmp_path: Path):
    state = CollectionState(tmp_path / "collection_state.json")
    state.record_attempt("https://example.com/a", identity="src:a", url="https://example.com/a", now=NOW)
    state.record_outcome("https://example.com/a", outcome="failed", now=NOW, success=False, error_class="rate_limited", message="slow", retry_after=30)
    assert state.eligible("https://example.com/a", NOW) is False
    assert state.eligible("https://example.com/a", "2026-10-01T12:00:31Z") is True
    for index in range(12):
        state.record_outcome("https://example.com/a", outcome="failed", now=NOW, success=False, error_class="temporarily_unavailable", message=f"e{index}")
    assert len(state.sources["https://example.com/a"]["errors"]) == 8
    state.record_outcome("https://example.com/a", outcome="unchanged", now=DONE, success=True, etag='"e"', content_hash="abc")
    assert state.conditional_headers("https://example.com/a")["If-None-Match"] == '"e"'
    assert state.sources["https://example.com/a"]["consecutive_failures"] == 0
    state.save()
    loaded = CollectionState.load(state.path)
    assert loaded.cursor is None
    assert loaded.sources["https://example.com/a"]["last_success_at"] == DONE


def test_lock_refuses_overlap_and_reclaims_dead_pid(tmp_path: Path):
    path = tmp_path / "refresh.lock"
    with RefreshLock(path):
        with pytest.raises(RefreshOverlap):
            RefreshLock(path).acquire()
    path.write_text(json.dumps({"pid": -1, "started_at": NOW}), encoding="utf-8")
    with RefreshLock(path):
        assert json.loads(path.read_text(encoding="utf-8"))["pid"]


def test_candidate_key_matches_typescript_contract():
    statement = {
        "person_slug": "refresh-ada",
        "extractor_version": "rule-extract-0.4.0",
        "statement_type": "explicit_numeric",
        "question_key": "extinction_unconditional",
        "horizon_text": "by 2070",
        "unit": "probability",
        "value_type": "point",
        "value_numeric": 0.15,
        "value_min": None,
        "value_max": None,
    }
    evidence = "Refresh Ada writes that the chance of human extinction from AI is 15% by 2070."
    source_hash = "ab" * 32
    python_key = candidate_key_for(statement, source_content_hash=source_hash, evidence_text=evidence)
    payload = {
        "person_slug": "refresh-ada",
        "source_content_hash": source_hash,
        "evidence_hash": __import__("hashlib").sha256(evidence.encode()).hexdigest(),
        "extractor_name": "rule-extract-0.4.0",
        "extractor_version": "rule-extract-0.4.0",
        "statement_type": "explicit_numeric",
        "question_key": "extinction_unconditional",
        "horizon_text": "by 2070",
        "unit": "probability",
        "value_type": "point",
        "value_numeric": 0.15,
        "value_min": None,
        "value_max": None,
    }
    completed = subprocess.run(
        ["npx", "tsx", "-e", "import { candidateKey } from './packages/contracts/src/curation.ts'; process.stdout.write(candidateKey(JSON.parse(process.argv[1])))", json.dumps(payload)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout == python_key


def test_refresh_converges_and_publishes_truthful_outcomes(tmp_path: Path):
    seed = tmp_path / "seed"
    collection = tmp_path / "collection"
    _write_seed(seed)
    pages = {
        "https://refresh.example/notes": (ESSAY.encode(), "text/html", '"essay-1"'),
        "https://refresh.example/older": (OLDER.encode(), "text/html", '"older-1"'),
        "https://refresh.example/feed.xml": (FEED.encode(), "application/rss+xml", '"feed-1"'),
    }
    script = _Script(pages)
    first = _refresh(seed, collection, script, leads=_leads(include_older=False))
    _validate(first["document"])
    assert first["status"] == "succeeded"
    assert first["counts"]["failed"] == 0
    assert first["counts"]["new"] > 0
    assert 'name="author" content="Refresh Ada"' in ESSAY
    assert 'name="author" content="Refresh Ada"' in OLDER
    _assert_author_metadata(first["document"], "https://refresh.example/notes", "page_byline")
    slugs = _statement_slugs(first["document"])
    numeric = _typed(first["document"], "explicit_numeric")
    qualitative = _typed(first["document"], "explicit_qualitative")
    assert len(numeric) == 1
    assert len(qualitative) == 1
    assert numeric[0]["slug"] == statement_slug(_raw_statement(first, numeric[0]["slug"]))
    item_slugs = {row["slug"] for row in first["document"]["source_items"]}
    feed_items = [row for row in first["document"]["source_items"] if row["canonical_url"] == "https://refresh.example/feed/note"]
    assert len(feed_items) == 1
    assert feed_items[0]["content_version"] == 1

    same = _refresh(seed, collection, script, leads=_leads(include_older=False))
    _validate(same["document"])
    assert same["status"] == "succeeded"
    assert same["counts"]["new"] == 0
    assert same["counts"]["changed"] == 0
    assert same["counts"]["unchanged"] > 0
    assert _statement_slugs(same["document"]) == slugs
    belief = _belief_run(same["document"])
    assert belief["status"] == "succeeded"
    assert belief["new_count"] == 0

    _write_seed(tmp_path / "seed-b")
    reordered = _refresh(tmp_path / "seed-b", tmp_path / "collection-b", _Script(pages), leads=list(reversed(_leads(include_older=False))))
    assert _statement_slugs(reordered["document"]) == slugs

    inserted_pages = dict(pages)
    inserted_pages["https://refresh.example/feed.xml"] = (FEED_INSERTED.encode(), "application/rss+xml", '"feed-2"')
    inserted_pages["https://refresh.example/older"] = (OLDER.encode(), "text/html", '"older-1"')
    inserted = _refresh(seed, collection, _Script(inserted_pages), leads=_leads(include_older=True))
    _validate(inserted["document"])
    assert set(slugs).issubset(_statement_slugs(inserted["document"]))
    assert any(row["canonical_url"] == "https://refresh.example/feed/earlier" for row in inserted["document"]["source_items"])
    assert any(row["canonical_url"] == "https://refresh.example/feed/note" and row["content_version"] == 1 for row in inserted["document"]["source_items"])

    changed_pages = dict(inserted_pages)
    changed_pages["https://refresh.example/notes"] = (ESSAY_CHANGED.encode(), "text/html", '"essay-2"')
    changed = _refresh(seed, collection, _Script(changed_pages), leads=_leads(include_older=True))
    _validate(changed["document"])
    assert changed["counts"]["changed"] >= 1
    changed_numeric = _typed(changed["document"], "explicit_numeric")
    assert changed_numeric[0]["slug"] == numeric[0]["slug"]
    versions = [row for row in changed["document"]["source_items"] if "refresh.example/notes" in row["canonical_url"]]
    assert {row["content_version"] for row in versions} >= {1, 2}
    assert sum(1 for row in versions if row["is_current"]) == 1
    assert any(not row["is_current"] and row["content_version"] == 1 for row in versions)

    failed_pages = dict(changed_pages)
    crash_seed = tmp_path / "seed-crash"
    crash_collection = tmp_path / "collection-crash"
    _write_seed(crash_seed, broken=True)
    crash_script = _Script(failed_pages, fail={"https://refresh.example/broken.xml"})
    partial_leads = _leads(include_older=True)
    crash_sources = _sources(include_broken=True)
    one = _refresh(crash_seed, crash_collection, crash_script, leads=partial_leads, max_sources=1, sources=crash_sources)
    assert one["counts"]["new"] >= 1
    cursor = json.loads((crash_collection / "state" / "collection_state.json").read_text(encoding="utf-8"))["cursor"]
    assert cursor
    two = _refresh(crash_seed, crash_collection, crash_script, leads=partial_leads, max_sources=1, sources=crash_sources)
    assert two["cursor"] != cursor
    assert set(_statement_slugs(one["document"])).issubset(_statement_slugs(two["document"]))

    full = _refresh(crash_seed, crash_collection, crash_script, leads=partial_leads, max_sources=10, sources=crash_sources)
    _validate(full["document"])
    assert full["status"] == "partial"
    assert full["counts"]["failed"] >= 1
    assert full["counts"]["new"] + full["counts"]["changed"] + full["counts"]["unchanged"] > 0
    partial_run = _belief_run(full["document"])
    assert partial_run["status"] == "partial"
    assert partial_run["unchanged_count"] == full["counts"]["unchanged"]
    assert partial_run["skipped_count"] == full["counts"]["skipped"]
    assert partial_run["failed_count"] == full["counts"]["failed"]
    assert partial_run["failed_count"] >= 1
    assert partial_run["new_count"] + partial_run["changed_count"] + partial_run["unchanged_count"] > 0
    _assert_author_metadata(full["document"], "https://refresh.example/notes", "page_byline")
    assert publication_decision(full["document"]) == "publish_partial"
    refused = json.loads(json.dumps(full["document"]))
    refused["ingestion_runs"][-1]["status"] = "failed"
    assert publication_decision(refused) == "refuse"

    down_pages = dict(changed_pages)
    down = _Script(down_pages, fail={"https://refresh.example/notes"})
    later = "2026-10-01T13:00:00Z"
    retained = _refresh(
        seed,
        collection,
        down,
        leads=_leads(include_older=True),
        now=later,
        completed_at="2026-10-01T13:05:00Z",
    )
    assert retained["status"] == "partial"
    assert any(row["slug"] == numeric[0]["slug"] for row in retained["document"]["statements"])
    checked = next(row for row in retained["document"]["sources"] if row["canonical_url"] == "https://refresh.example/notes")
    assert checked["last_checked_at"] == later
    assert checked["last_success_at"] == NOW

    FIXTURE.mkdir(parents=True, exist_ok=True)
    _dump(FIXTURE / "dataset.json", first["document"])
    _dump(FIXTURE / "dataset-changed.json", changed["document"])
    _dump(FIXTURE / "dataset-partial.json", full["document"])
    (FIXTURE / "manifest.json").write_text(
        json.dumps(
            {
                "numeric_slug": numeric[0]["slug"],
                "qualitative_slug": qualitative[0]["slug"],
                "numeric_evidence_slug": numeric[0]["evidence_slug"],
                "source_item_slug": numeric[0]["source_item_slug"],
                "changed_evidence_slug": changed_numeric[0]["evidence_slug"],
                "changed_source_item_slug": changed_numeric[0]["source_item_slug"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assert item_slugs
    assert evidence_slug({"source_url": "https://refresh.example/notes", "evidence_text": "x", "start_char": 0, "start_ms": None})


def test_partial_metrics_are_not_a_full_success():
    reset_metrics()
    observe_collection_run(
        {
            "collector": "belief-corpus",
            "status": "partial",
            "new_count": 1,
            "changed_count": 0,
            "unchanged_count": 2,
            "error_class": "not-a-label",
        }
    )
    text = render()
    assert "pdoom_collection_succeeded" not in text
    assert 'outcome="failed"' in text
    assert "pdoom_collection_new 1" in text or "pdoom_collection_new " in text
    assert 'failure_class="unclassified"' in text


def test_refresh_command_requires_once():
    completed = subprocess.run(
        [__import__("sys").executable, "-m", "pdoom_pipeline.jobs.refresh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": "pipeline"},
    )
    assert completed.returncode != 0
    assert "--once" in completed.stderr
    release = (ROOT / "scripts" / "deploy" / "release.sh").read_text(encoding="utf-8")
    assert "pdoom-refresh" not in release


class _Script:
    def __init__(self, pages: dict[str, tuple[bytes, str, str]], fail: set[str] | None = None):
        self.pages = pages
        self.fail = fail or set()

    def __call__(self, url: str, headers: dict[str, str]) -> FetchResult:
        if url.endswith("/robots.txt"):
            return FetchResult(url=url, status=404, headers={"content-type": "text/plain"}, body=b"")
        if url in self.fail:
            return FetchResult(url=url, status=503, headers={"content-type": "text/plain", "retry-after": "0"}, body=b"")
        if url not in self.pages:
            return FetchResult(url=url, status=404, headers={"content-type": "text/plain"}, body=b"")
        body, content_type, etag = self.pages[url]
        if headers.get("if-none-match") == etag:
            return FetchResult(url=url, status=304, headers={"etag": etag}, body=b"")
        return FetchResult(url=url, status=200, headers={"content-type": content_type, "etag": etag}, body=body)


def _refresh(
    seed: Path,
    collection: Path,
    script: _Script,
    *,
    leads: list[dict],
    max_sources: int = 10,
    sources: list[dict] | None = None,
    now: str = NOW,
    completed_at: str = DONE,
) -> dict:
    fetcher = SafeFetcher(transport=script, sleep=lambda _seconds: None, max_attempts=3, allowed_content_types=TYPES, timeout=5)
    fetcher.host_interval = 0
    return run_refresh(
        seed_dir=seed,
        collection_dir=collection,
        people=_people(),
        leads=leads,
        registry_sources=sources if sources is not None else _sources(include_broken=False),
        fetcher=fetcher,
        now=now,
        completed_at=completed_at,
        max_sources=max_sources,
        max_seconds=30,
        include_adapters=True,
        include_belief=True,
    )


def _validate(document: dict) -> None:
    import tempfile

    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    path = Path(handle.name)
    json.dump(document, handle)
    handle.close()
    completed = subprocess.run(
        [
            "npx",
            "tsx",
            "-e",
            "import { readFileSync } from 'node:fs'; import { validateDocument } from './packages/db/src/import.ts'; validateDocument(JSON.parse(readFileSync(process.argv[1], 'utf8')));",
            str(path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout + completed.stderr)
    path.unlink(missing_ok=True)


def _people() -> list[dict]:
    return [
        {
            "id": "person:refresh-ada",
            "slug": "refresh-ada",
            "display_name": "Refresh Ada",
            "given_name": "Refresh",
            "family_name": "Ada",
            "bio_short": "Fixture researcher used only to test refresh continuity.",
            "inclusion_reason": "Fixture person for the offline refresh path.",
            "cohort_tags": ["fixture_refresh"],
            "status": "active",
            "name_distinctiveness": "high",
            "review_state": "machine_validated",
        }
    ]


def _sources(*, include_broken: bool = False) -> list[dict]:
    rows = [
        _source("src:person:refresh-ada:html-page", "https://refresh.example/notes", "html_page", "blog", False),
        _source("src:person:refresh-ada:rss", "https://refresh.example/feed.xml", "rss_feed", "rss", True),
    ]
    if include_broken:
        rows.append(_source("src:person:refresh-ada:rss:broken", "https://refresh.example/broken.xml", "rss_feed", "rss", True))
    return rows


def _source(identity: str, url: str, method: str, source_type: str, collectible: bool) -> dict:
    return {
        "id": identity,
        "name": url,
        "canonical_url": url,
        "source_type": source_type,
        "platform": "blog",
        "owner_person_id": "person:refresh-ada",
        "owner_organization_id": None,
        "collection_method": method,
        "rights_notes": "Fixture page. Store the excerpt and the link.",
        "enabled": True,
        "continuously_collectible": collectible,
        "review_state": "machine_validated",
    }


def _leads(*, include_older: bool) -> list[dict]:
    rows = [
        {
            "kind": "essay",
            "url": "https://refresh.example/notes",
            "person_slug": "refresh-ada",
            "source_type": "blog",
            "name": "Refresh Ada notes",
            "basis": "Fixture page whose author metadata names Refresh Ada.",
        }
    ]
    if include_older:
        rows.append(
            {
                "kind": "essay",
                "url": "https://refresh.example/older",
                "person_slug": "refresh-ada",
                "source_type": "blog",
                "name": "Refresh Ada earlier note",
                "basis": "Fixture page whose author metadata names Refresh Ada.",
            }
        )
    return rows


def _write_seed(directory: Path, *, broken: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _jsonl(directory / "organizations.jsonl", [
        {
            "id": "org:refresh-lab",
            "slug": "refresh-lab",
            "name": "Refresh Lab",
            "organization_type": "research_lab",
            "canonical_url": "https://refresh.example",
        }
    ])
    _jsonl(directory / "people.jsonl", _people())
    _jsonl(directory / "affiliations.jsonl", [
        {
            "person_id": "person:refresh-ada",
            "organization_id": "org:refresh-lab",
            "role": "Researcher",
            "confidence": "high",
            "verification_method": "curator_reviewed",
            "review_state": "machine_validated",
            "basis": "current",
        }
    ])
    _jsonl(directory / "external_identities.jsonl", [
        {
            "person_id": "person:refresh-ada",
            "namespace": "personal_website",
            "external_id": "refresh-ada.example",
            "canonical_url": "https://refresh.example",
            "handle": None,
            "verification_method": "curator_reviewed",
            "confidence": "high",
            "review_state": "machine_validated",
            "verified_at": "2026-09-01T00:00:00Z",
        }
    ])
    sources = _sources(include_broken=broken)
    _jsonl(directory / "sources.jsonl", sources)
    _jsonl(directory / "belief_sources.jsonl", _leads(include_older=True))
    (directory / "cohort.json").write_text(
        json.dumps(
            {
                "cohort_id": "cohort_2026_09",
                "version": "2026.09.0",
                "description": "Offline fixture for refresh continuity. This is one fictional person and it is not a census.",
                "resolver_version": "0.1.0",
            }
        ),
        encoding="utf-8",
    )


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _statement_slugs(document: dict) -> list[str]:
    return sorted(row["slug"] for row in document["statements"])


def _typed(document: dict, statement_type: str) -> list[dict]:
    return [row for row in document["statements"] if row["statement_type"] == statement_type]


def _belief_run(document: dict) -> dict:
    return next(row for row in document["ingestion_runs"] if row["collector"] == "belief-corpus")


def _assert_author_metadata(document: dict, url: str, attribution_detail: str) -> None:
    item = next(row for row in document["source_items"] if row["canonical_url"] == url)
    authors = [row for row in document["participants"] if row["source_item_slug"] == item["slug"] and row["role"] == "author"]
    assert len(authors) == 1
    assert authors[0]["person_slug"] == "refresh-ada"
    assert authors[0]["attribution_detail"] == attribution_detail


def _raw_statement(result: dict, slug: str) -> dict:
    from pdoom_pipeline.export.corpus import _stable_statement_slugs

    mapping = _stable_statement_slugs(result["result"]["statements"])
    for statement in result["result"]["statements"]:
        if mapping[id(statement)] == slug:
            return statement
    raise AssertionError(slug)


def _dump(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _observation(url: str, title: str, digest: str) -> SourceObservation:
    observation = SourceObservation(
        source_identity="src:test",
        platform="blog",
        upstream_id=url,
        canonical_url=url,
        observed_at=NOW,
        published_at=NOW,
        author_candidates=[AuthorCandidate(name="Refresh Ada", role="author", attribution_method="metadata", confidence="medium")],
        title=title,
        segments=[Segment(segment_kind="text", sequence=1, text=title)],
        metadata={},
        collector="test",
        collector_version="test",
        collection_method="manual",
    )
    observation.content_hash = digest
    return observation
