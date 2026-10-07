"""Offline identity, provenance-revision and legacy store round-trip regressions."""
from copy import deepcopy
from pathlib import Path

import pytest

from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.contracts import Segment
from pdoom_pipeline.export.canonical import source_slug
from pdoom_pipeline.export.versions import merge_observation_store
from pdoom_pipeline.ingest.collection_state import CollectionState
from pdoom_pipeline.ingest.store import ObservationStore
from pdoom_pipeline.refresh.runner import _enforce_retained_policy, _work_items

NOW = "2026-10-07T00:00:00Z"


def observation(identity="src:show:a", *, url="https://example.org/article", guid="1", author="Original Author", text="A short excerpt"):
    payload = f'<rss><channel><item><guid isPermaLink="false">{guid}</guid><link>{url}</link><title>Example</title><author>{author}</author><description>{text}</description></item></channel></rss>'.encode()
    return RssCollector().parse(payload, source_identity=identity, feed_url=f"https://example.org/{identity.split(':')[-1]}/feed", observed_at=NOW)[0]


def registry(identity):
    return {"id": identity, "canonical_url": f"https://example.org/{identity.split(':')[-1]}/feed", "collection_method": "rss_feed", "enabled": True, "rights_notes": "Synthetic fixture rights."}


def exported(store, identities=("src:show:a", "src:show:b")):
    rows = [registry(identity) for identity in identities]
    document = {"sources": [{"slug": source_slug(row["id"])} for row in rows], "source_items": [], "participants": [], "evidence_segments": [], "people": []}
    merge_observation_store(document, store, rows)
    return document


def test_rss_feed_local_guid_cannot_merge_unrelated_sources(tmp_path):
    store = ObservationStore()
    first = observation(url="https://a.example/article", text="A")
    other = observation("src:show:b", url="https://b.example/article", text="B")
    assert store.ingest(first).status == "new"
    assert store.ingest(other).status == "new"
    store.save(tmp_path / "store.json")
    reloaded = ObservationStore.load(tmp_path / "store.json")
    assert reloaded.ingest(first).status == "unchanged"
    assert reloaded.ingest(other).status == "unchanged"
    current = [row for row in exported(reloaded)["source_items"] if row["is_current"]]
    assert {row["canonical_url"] for row in current} == {first.canonical_url, other.canonical_url}


def test_authorship_only_correction_is_separately_versioned_without_rehashing_content(tmp_path):
    original = observation()
    correction = observation(author="Corrected Author")
    assert original.content_hash == correction.content_hash
    store = ObservationStore()
    first = store.ingest(original)
    correction_result = store.ingest(correction)
    assert correction_result.status == "version_changed"
    item = store.items[first.logical_key]
    assert len(item.versions) == 1
    assert item.latest["content_hash"] == original.content_hash
    assert item.latest["content_version"] == 1
    assert item.latest["author_candidates"][0]["name"] == "Corrected Author"
    revisions = item.latest["provenance_observations"]
    assert [row["author_candidates"][0]["name"] for row in revisions] == ["Original Author", "Corrected Author"]
    assert [row["provenance_revision"] for row in revisions] == [1, 2]
    store.save(tmp_path / "store.json")
    reloaded = ObservationStore.load(tmp_path / "store.json")
    assert reloaded.ingest(correction).status == "unchanged"
    assert reloaded.items[first.logical_key].latest["author_candidates"][0]["name"] == "Corrected Author"
    assert exported(reloaded)["source_items"][0]["content_hash"] == original.content_hash.removeprefix("sha256:")


@pytest.mark.parametrize("remaining", ["src:show:a", "src:show:b"])
def test_revocation_keeps_other_admitted_source_provenance(tmp_path, remaining):
    store = ObservationStore()
    first = observation()
    same = observation("src:show:b")
    assert first.content_hash == same.content_hash
    store.ingest(first)
    store.ingest(same)
    store.save(tmp_path / "store.json")
    store = ObservationStore.load(tmp_path / "store.json")
    sources = [registry(remaining)]
    state = CollectionState(tmp_path / "state.json")
    _enforce_retained_policy(state, store, sources, [], _work_items(sources, [], NOW), NOW)
    assert len(store.items) == 1
    version = next(iter(store.items.values())).latest
    assert version["source_identity"] == remaining
    assert {row["source_identity"] for row in version["provenance_observations"]} == {remaining}
    current = [row for row in exported(store, (remaining,))["source_items"] if row["is_current"]]
    assert len(current) == 1 and current[0]["source_slug"] == source_slug(remaining)
    _enforce_retained_policy(state, store, [], [], [], NOW)
    assert not store.items


def test_legacy_store_replay_preserves_hash_version_and_slug(tmp_path):
    source = observation()
    store = ObservationStore()
    store.ingest(source)
    legacy = deepcopy(store.to_dict())
    legacy["schema_version"] = "observation-store/1.0.0"
    for item in legacy["items"]:
        for upstream in item["upstream_ids"]:
            upstream.pop("source_identity", None)
        for version in item["versions"]:
            version.pop("provenance_observations", None)
            version.pop("provenance_revision", None)
            version.pop("current_provenance_id", None)
    original_export = exported(store)["source_items"]
    loaded = ObservationStore.from_dict(legacy)
    assert loaded.ingest(source).status == "unchanged"
    assert exported(loaded)["source_items"] == original_export
    assert loaded.ingest(observation("src:show:b", url="https://different.example/item")).status == "new"
    assert len(loaded.items) == 2


def test_segment_timecodes_and_correction_survive_store_export(tmp_path):
    source = observation()
    source.segments = [Segment("transcript", 0, "A short excerpt", 0, 15, 10000, 12000)]
    source.finalize_hash()
    store = ObservationStore()
    store.ingest(source)
    store.save(tmp_path / "store.json")
    reloaded = ObservationStore.load(tmp_path / "store.json")
    segment = exported(reloaded)["evidence_segments"][0]
    assert (segment["start_ms"], segment["end_ms"]) == (10000, 12000)
    corrected = deepcopy(source)
    corrected.segments[0].start_ms = 11000
    assert corrected.finalize_hash().content_hash == source.content_hash
    assert reloaded.ingest(corrected).status == "version_changed"
    assert exported(reloaded)["evidence_segments"][0]["start_ms"] == 11000


def test_narrower_evidence_permission_scrubs_every_provenance_revision(tmp_path):
    store = ObservationStore()
    store.ingest(observation())
    store.ingest(observation(author="Corrected Author"))
    source = registry("src:show:a")
    source["collection_policy"] = {"admitted": True, "rights_basis": "Metadata only", "evidence": False}
    state = CollectionState(tmp_path / "state.json")
    _enforce_retained_policy(state, store, [source], [], _work_items([source], [], NOW), NOW)
    version = next(iter(store.items.values())).latest
    assert not version["segments"]
    assert all(not row["segments"] for row in version["provenance_observations"])


def test_contaminated_legacy_rss_store_requires_review_without_rewriting_file(tmp_path):
    import json
    store = ObservationStore()
    store.ingest(observation(url="https://a.example/article"))
    payload = deepcopy(store.to_dict())
    payload["schema_version"] = "observation-store/1.0.0"
    other = ObservationStore()
    other.ingest(observation("src:show:b", url="https://b.example/article", text="Different content"))
    wrong_version = deepcopy(other.to_dict()["items"][0]["versions"][0])
    wrong_version["content_version"] = 2
    payload["items"][0]["versions"].append(wrong_version)
    payload["items"][0]["current_hash"] = wrong_version["content_hash"]
    for version in payload["items"][0]["versions"]:
        version.pop("provenance_observations", None)
        version.pop("current_provenance_id", None)
        version.pop("provenance_revision", None)
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="RSS identity reconciliation required") as error:
        ObservationStore.load(path)
    assert "src:show:a" in str(error.value) and "src:show:b" in str(error.value)
    assert "https://" not in str(error.value)
    assert path.read_bytes() == before


def test_legacy_rss_alias_scope_survives_retention_before_replay(tmp_path):
    store = ObservationStore()
    source = observation(guid="original")
    store.ingest(source)
    store.ingest(observation(guid="alternate"))
    payload = deepcopy(store.to_dict())
    for record in payload["items"][0]["upstream_ids"]:
        record.pop("source_identity", None)
    loaded = ObservationStore.from_dict(payload)
    rows = [registry("src:show:a")]
    _enforce_retained_policy(CollectionState(tmp_path / "state.json"), loaded, rows, [], _work_items(rows, [], NOW), NOW)
    assert {record["upstream_id"] for record in next(iter(loaded.items.values())).upstream_ids} == {"original", "alternate"}
    assert loaded.ingest(source).logical_key == source.canonical_url


def test_provenance_revert_reuses_revision_but_reports_projection_change():
    original = observation()
    correction = observation(author="Corrected Author")
    store = ObservationStore()
    store.ingest(original)
    store.ingest(correction)
    assert store.ingest(original).status == "version_changed"
    current = next(iter(store.items.values())).latest
    assert current["provenance_revision"] == 1
    assert len(current["provenance_observations"]) == 2
    assert store.ingest(original).status == "unchanged"


def test_cross_platform_replay_of_previous_content_does_not_duplicate_hash():
    original = observation()
    other = deepcopy(original)
    other.platform = "openalex"
    other.source_identity = "src:show:b"
    store = ObservationStore()
    store.ingest(original)
    store.ingest(other)
    changed = observation(text="Changed body")
    store.ingest(changed)
    assert store.ingest(other).status == "unchanged"
    item = next(iter(store.items.values()))
    assert len(item.versions) == 2
    assert item.current_hash == original.content_hash


def test_legitimate_legacy_same_url_multisource_versions_still_load():
    store = ObservationStore()
    store.ingest(observation())
    store.ingest(observation("src:show:b", text="Updated excerpt"))
    payload = deepcopy(store.to_dict())
    payload["schema_version"] = "observation-store/1.0.0"
    for version in payload["items"][0]["versions"]:
        version.pop("provenance_observations", None)
        version.pop("current_provenance_id", None)
        version.pop("provenance_revision", None)
    loaded = ObservationStore.from_dict(payload)
    assert len(loaded.items) == 1
    assert len(next(iter(loaded.items.values())).versions) == 2
    assert len([row for row in exported(loaded)["source_items"] if row["is_current"]]) == 1


def test_same_source_url_move_can_be_coobserved_and_reloaded():
    store = ObservationStore()
    original = observation(url="https://example.org/old")
    moved = observation(url="https://example.org/new")
    coobserved = observation("src:show:b", url="https://example.org/new")
    store.ingest(original)
    store.ingest(moved)
    store.ingest(coobserved)
    loaded = ObservationStore.from_dict(deepcopy(store.to_dict()))
    assert len(loaded.items) == 1
    assert loaded.by_url[original.canonical_url] == loaded.by_url[moved.canonical_url]
    assert loaded.ingest(coobserved).status == "unchanged"


def test_scoped_url_move_survives_original_source_revocation_and_reload(tmp_path):
    store = ObservationStore()
    original = observation(url="https://example.org/old")
    moved = observation(url="https://example.org/new")
    coobserved = observation("src:show:b", url="https://example.org/new")
    store.ingest(original)
    store.ingest(moved)
    store.ingest(coobserved)
    before = exported(store)["source_items"][0]
    store.retain_sources({"src:show:b"}, {"src:show:b"})
    path = tmp_path / "scoped.json"
    store.save(path)
    loaded = ObservationStore.load(path)
    assert loaded.ingest(coobserved).logical_key == original.canonical_url
    after = exported(loaded)["source_items"][0]
    assert (after["slug"], after["logical_key"], after["content_hash"], after["content_version"]) == (before["slug"], before["logical_key"], before["content_hash"], before["content_version"])
    assert next(iter(loaded.items.values())).latest["source_identity"] == "src:show:b"
    assert loaded.to_dict()["schema_version"] == "observation-store/1.1.0"


def test_unknown_observation_store_schema_is_not_silently_adopted():
    with pytest.raises(ValueError, match="unsupported observation store schema"):
        ObservationStore.from_dict({"schema_version": "observation-store/99.0.0", "items": []})
