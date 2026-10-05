"""Repeated ingest of one canonical URL stays one current source item.

Version 1 slugs stay ``item-`` plus the first 20 hex characters of
SHA-256(canonical URL). A later content hash may add a version, and that
row uses :func:`pdoom_pipeline.export.identity.source_item_slug`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.export.canonical import source_slug
from pdoom_pipeline.export.identity import source_item_slug
from pdoom_pipeline.export.versions import merge_observation_store
from pdoom_pipeline.ingest.store import ObservationStore

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "rss" / "hostile.xml"
OBSERVED = "2026-09-24T00:00:00Z"
SOURCE_ID = "src:person:ada-lovelace:rss"
FEED_URL = "https://example.com/feed.xml"


def test_same_fixture_twice_keeps_one_current_source_item(tmp_path: Path):
    payload = FIXTURE.read_bytes()
    first = _parse(payload)
    second = _parse(payload)
    assert second.canonical_url == first.canonical_url
    assert second.content_hash == first.content_hash

    store = ObservationStore()
    assert store.ingest(first).status == "new"
    store.save(tmp_path / "observations.json")
    reloaded = ObservationStore.load(tmp_path / "observations.json")
    again = reloaded.ingest(second)

    assert again.status == "unchanged"
    assert again.content_hash == first.content_hash
    assert again.content_version == 1
    rows = _source_items(reloaded, first.canonical_url)
    assert len(rows) == 1
    assert rows[0]["is_current"] is True
    assert rows[0]["content_version"] == 1
    assert rows[0]["logical_key"] == first.canonical_url
    assert rows[0]["slug"] == _version_one_slug(first.canonical_url)
    assert rows[0]["slug"] == source_item_slug(first.canonical_url, rows[0]["content_hash"], 1)
    assert len(_items_for_url(reloaded, first.canonical_url)) == 1
    assert len(_items_for_url(reloaded, first.canonical_url)[0].versions) == 1


def test_changed_content_hash_adds_one_version_and_one_current_item(tmp_path: Path):
    payload = FIXTURE.read_bytes()
    original = _parse(payload)
    changed = _parse(payload.replace(b"execute this command", b"execute that command"))
    assert changed.canonical_url == original.canonical_url
    assert changed.content_hash != original.content_hash

    store = ObservationStore()
    store.ingest(original)
    store.ingest(_parse(payload))
    updated = store.ingest(changed)
    assert updated.status == "version_changed"
    assert updated.content_version == 2

    rows = _source_items(store, original.canonical_url)
    current = [row for row in rows if row["is_current"]]
    assert len(current) == 1
    assert current[0]["content_version"] == 2
    assert current[0]["slug"] == source_item_slug(original.canonical_url, current[0]["content_hash"], 2)
    assert current[0]["slug"] != _version_one_slug(original.canonical_url)
    previous = [row for row in rows if row["content_version"] == 1]
    assert len(previous) == 1
    assert previous[0]["is_current"] is False
    assert previous[0]["slug"] == _version_one_slug(original.canonical_url)
    assert len({row["slug"] for row in rows}) == len(rows)
    assert len({row["content_hash"] for row in rows}) == len(rows)

    restored = store.ingest(original)
    assert restored.status == "unchanged"
    assert restored.content_version == 1
    store.save(tmp_path / "observations.json")
    reloaded = ObservationStore.load(tmp_path / "observations.json")
    repeated = reloaded.ingest(_parse(payload))
    assert repeated.status == "unchanged"
    assert repeated.content_version == 1
    restored_rows = _source_items(reloaded, original.canonical_url)
    restored_current = [row for row in restored_rows if row["is_current"]]
    assert len(restored_current) == 1
    assert restored_current[0]["content_version"] == 1
    assert restored_current[0]["slug"] == _version_one_slug(original.canonical_url)
    assert len(restored_rows) == 2
    assert len(_items_for_url(reloaded, original.canonical_url)) == 1
    assert [version["content_version"] for version in _items_for_url(reloaded, original.canonical_url)[0].versions] == [1, 2]


def _parse(payload: bytes):
    observations = RssCollector().parse(
        payload,
        source_identity=SOURCE_ID,
        feed_url=FEED_URL,
        observed_at=OBSERVED,
    )
    assert len(observations) == 1
    return observations[0]


def _version_one_slug(canonical_url: str) -> str:
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:20]
    return f"item-{digest}"


def _items_for_url(store: ObservationStore, canonical_url: str):
    return [item for item in store.items.values() if item.canonical_url == canonical_url]


def _source_items(store: ObservationStore, canonical_url: str) -> list[dict]:
    slug = source_slug(SOURCE_ID)
    document = {
        "sources": [{"slug": slug, "canonical_url": FEED_URL}],
        "source_items": [],
        "participants": [],
        "evidence_segments": [],
        "people": [],
    }
    merge_observation_store(
        document,
        store,
        [{"id": SOURCE_ID, "canonical_url": FEED_URL}],
    )
    rows = [row for row in document["source_items"] if row["canonical_url"] == canonical_url]
    for row in rows:
        version = int(row["content_version"])
        assert row["slug"] == source_item_slug(canonical_url, row["content_hash"], version)
        if version <= 1:
            assert row["slug"] == _version_one_slug(canonical_url)
        else:
            assert row["slug"] != _version_one_slug(canonical_url)
    return rows
