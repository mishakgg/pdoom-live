"""One bounded refresh. It does not enable a schedule and it does not import."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pdoom_pipeline.belief.changes import view_change_candidates
from pdoom_pipeline.belief.collect import collect_beliefs
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.export.corpus import export_corpus
from pdoom_pipeline.export.versions import merge_observation_store
from pdoom_pipeline.urls import canonicalize_url
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.ingest.collection_state import CollectionState
from pdoom_pipeline.ingest.staging import belief_dir, enrichment_dir, read_enrichment_sources, state_dir, write_belief_staging
from pdoom_pipeline.ingest.store import ObservationStore
from pdoom_pipeline.refresh.runtime import adapter_source, call_adapter, ingest_observations

WORK_SCHEMA = "refresh-work/1.0.0"


def run_refresh(
    *,
    seed_dir: Path,
    collection_dir: Path,
    people: list[dict],
    leads: list[dict],
    registry_sources: list[dict],
    fetcher: SafeFetcher | None = None,
    now: str | None = None,
    completed_at: str | None = None,
    max_sources: int = 40,
    max_seconds: float = 900,
    include_adapters: bool = True,
    include_belief: bool = True,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
    transport=None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Refresh a bounded slice, then assemble canonical output from staging."""
    started = now or _iso()
    state = CollectionState.load(state_dir(collection_dir) / "collection_state.json")
    store = ObservationStore.load(state_dir(collection_dir) / "observations.json")
    client = fetcher or SafeFetcher(
        transport=transport,
        sleep=sleep,
        timeout=20,
        max_bytes=6_000_000,
        allowed_content_types=(
            "application/rss+xml",
            "application/atom+xml",
            "application/xml",
            "text/xml",
            "text/plain",
            "text/html",
            "application/xhtml+xml",
            "application/json",
            "application/octet-stream",
        ),
    )
    if sleep is not None:
        client.sleep = sleep
    if clock is not None:
        client.clock = clock
    if fetcher is None and client.host_interval <= 0:
        client.host_interval = 0.25
    client.deadline_at = client.clock() + max_seconds
    client.cancelled = cancelled
    client.header_provider = lambda url: state.conditional_headers(url)
    client.cache_get = state.read_body
    client.cache_put = lambda url, body, _headers: state.write_body(url, body)

    work = _work_items(registry_sources if include_adapters else [], leads if include_belief else [])
    selected, cursor_before, _planned = _select(work, state.cursor, max_sources)
    cursor_after = state.cursor
    counts = {"new": 0, "changed": 0, "unchanged": 0, "skipped": 0, "failed": 0}
    errors: list[str] = []
    belief_observations: list[dict] = []
    belief_statements: list[dict] = []
    runs: list[dict] = []
    checked: dict[str, dict[str, str | None]] = {}
    visited_urls: set[str] = set()

    for item in selected:
        if cancelled and cancelled():
            break
        if item["kind"] == "adapter":
            _run_adapter_item(
                item,
                client=client,
                state=state,
                store=store,
                observed_at=started,
                counts=counts,
                errors=errors,
                checked=checked,
                visited_urls=visited_urls,
            )
        else:
            _run_belief_item(
                item,
                people=people,
                client=client,
                state=state,
                observed_at=started,
                counts=counts,
                errors=errors,
                checked=checked,
                visited_urls=visited_urls,
                belief_observations=belief_observations,
                belief_statements=belief_statements,
                runs=runs,
            )
        cursor_after = item["key"]
        state.cursor = cursor_after
        state.save()
        store.save(state_dir(collection_dir) / "observations.json")

    retained_observations, retained_statements = state.retained_for(visited_urls)
    for observation in retained_observations:
        observation["ingest_status"] = "unchanged"
        counts["unchanged"] += 1
    belief_observations.extend(retained_observations)
    belief_statements.extend(retained_statements)
    _reindex(belief_statements)
    completed = completed_at or _iso()
    failed = counts["failed"]
    progressed = counts["new"] + counts["changed"] + counts["unchanged"]
    if failed and progressed:
        status = "partial"
    elif failed:
        status = "failed"
    else:
        status = "succeeded"
    refresh = {
        "started_at": started,
        "completed_at": completed,
        "extracted_at": completed,
        "status": status,
        "cursor_before": cursor_before,
        "cursor_after": cursor_after,
        "new_count": counts["new"],
        "changed_count": counts["changed"],
        "unchanged_count": counts["unchanged"],
        "skipped_count": counts["skipped"],
        "failed_count": failed,
        "error_summary": "; ".join(errors)[:400] or None,
        "checks": checked,
    }
    result = {
        "observations": belief_observations,
        "statements": belief_statements,
        "relationships": view_change_candidates(belief_statements),
        "runs": runs,
        "source_leads": [],
        "extractor_version": "rule-extract-0.4.0",
        "refresh": refresh,
    }
    write_belief_staging(
        collection_dir,
        observations=belief_observations,
        statements=belief_statements,
        runs=runs,
        summary={"status": status, **{key: counts[key] for key in counts}},
    )
    document = export_corpus(result, seed_dir=seed_dir, generated_at=completed)
    merge_observation_store(document, store, registry_sources)
    _merge_enrichment(document, read_enrichment_sources(collection_dir))
    canonical = collection_dir / "canonical-live.json"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    temporary = canonical.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document), encoding="utf-8")
    temporary.replace(canonical)
    if enrichment_dir(collection_dir).exists():
        belief_names = {path.name for path in belief_dir(collection_dir).glob("*")}
        overlap = belief_names.intersection(path.name for path in enrichment_dir(collection_dir).glob("*") if path.name != "README.md")
        if overlap:
            raise RuntimeError(f"belief staging collided with enrichment files: {sorted(overlap)}")
    return {"status": status, "counts": counts, "cursor": cursor_after, "document": document, "result": result}


def _run_adapter_item(item, *, client, state, store, observed_at, counts, errors, checked, visited_urls) -> None:
    source = item["source"]
    key = source["url"]
    identity = source["source_identity"]
    if not state.eligible(key, observed_at):
        counts["skipped"] += 1
        _check(checked, source.get("registry_url") or key, state, success=False, checked_at=None)
        return
    state.record_attempt(key, identity=identity, url=key, now=observed_at)
    try:
        fetched = call_adapter(source["adapter"], fetcher=client, source=source, observed_at=observed_at)
    except CollectorFailure as exc:
        state.record_outcome(
            key,
            outcome="failed",
            now=observed_at,
            success=False,
            error_class=exc.error_class,
            message=str(exc),
            retry_after=exc.retry_after,
        )
        retained = _stored_for_identity(store, identity)
        if retained:
            counts["unchanged"] += len(retained)
        counts["failed"] += 1
        errors.append(f"{identity}: {exc.error_class}")
        _check(checked, source.get("registry_url") or key, state, success=False, checked_at=observed_at)
        return
    ingested = ingest_observations(store, fetched["observations"])
    if fetched["outcome"] == "unchanged":
        outcome = "unchanged"
        for row in ingested:
            row["status"] = "unchanged"
        counts["unchanged"] += len(ingested) or 1
    else:
        outcome = _tally(ingested, counts)
    state.record_outcome(
        key,
        outcome=outcome,
        now=observed_at,
        success=True,
        etag=fetched.get("etag"),
        last_modified=fetched.get("last_modified"),
        content_hash=ingested[-1]["content_hash"] if ingested else None,
    )
    visited_urls.add(key)
    _check(checked, source.get("registry_url") or key, state, success=True, checked_at=observed_at)


def _run_belief_item(
    item,
    *,
    people,
    client,
    state,
    observed_at,
    counts,
    errors,
    checked,
    visited_urls,
    belief_observations,
    belief_statements,
    runs,
) -> None:
    lead = item["lead"]
    key = lead.get("fetch_url") or lead["url"]
    if not state.eligible(key, observed_at):
        counts["skipped"] += 1
        cached = _replay_cached(state, lead, counts, belief_observations, belief_statements, visited_urls)
        if not cached:
            _check(checked, key, state, success=False, checked_at=None)
        return
    state.record_attempt(key, identity=lead.get("person_slug") or lead.get("show_slug") or key, url=key, now=observed_at)
    failed: list[CollectorFailure] = []

    def fetch_bytes(url: str) -> bytes:
        if url.endswith("/robots.txt"):
            try:
                result = client.get(url)
            except CollectorFailure as exc:
                if exc.error_class == "not_found":
                    return b""
                raise
            return result.body
        try:
            result = client.get(url)
        except CollectorFailure as exc:
            failed.append(exc)
            cached = state.read_body(url)
            if cached is not None:
                return cached
            raise
        if not result.not_modified and result.body:
            state.write_body(url, result.body)
        return result.body

    try:
        partial = collect_beliefs(
            people=people,
            leads=[lead],
            fetch_bytes=fetch_bytes,
            observed_at=observed_at,
            priority_slugs={person["slug"] for person in people},
        )
    except CollectorFailure as exc:
        failed.append(exc)
        partial = {"observations": [], "statements": [], "runs": []}
    if failed and not partial["observations"]:
        exc = failed[-1]
        state.record_outcome(key, outcome="failed", now=observed_at, success=False, error_class=exc.error_class, message=str(exc), retry_after=exc.retry_after)
        counts["failed"] += 1
        errors.append(f"{key}: {exc.error_class}")
        _replay_cached(state, lead, counts, belief_observations, belief_statements, visited_urls)
        _check(checked, key, state, success=False, checked_at=observed_at)
        runs.extend(partial.get("runs") or [])
        return
    outcome = "unchanged" if failed or (client.last and client.last.not_modified) else "fetched"
    if failed:
        counts["failed"] += 1
        errors.append(f"{key}: {failed[-1].error_class}")
        state.record_outcome(key, outcome="failed", now=observed_at, success=False, error_class=failed[-1].error_class, message=str(failed[-1]), retry_after=failed[-1].retry_after)
        success = False
    else:
        state.record_outcome(key, outcome=outcome, now=observed_at, success=True, etag=(client.last.headers.get("etag") if client.last else None))
        success = True
    _absorb_belief(partial, state, counts, belief_observations, belief_statements, visited_urls, forced_unchanged=bool(failed) or outcome == "unchanged")
    _check(checked, key, state, success=success, checked_at=observed_at)
    runs.extend(partial.get("runs") or [])


def _absorb_belief(partial, state, counts, belief_observations, belief_statements, visited_urls, *, forced_unchanged: bool) -> None:
    by_url: dict[str, list[dict]] = {}
    for statement in partial.get("statements") or []:
        by_url.setdefault(statement.get("source_url"), []).append(statement)
    for observation in partial.get("observations") or []:
        statements = by_url.get(observation["canonical_url"], [])
        existed = _hash_known(state, observation["canonical_url"], observation.get("content_hash"))
        state.remember_item(observation, statements)
        stored = dict(state.items[observation["canonical_url"]]["item"])
        if forced_unchanged or existed:
            status = "unchanged"
        elif int(stored.get("content_version") or 1) > 1:
            status = "changed"
        else:
            status = "new"
        stored["ingest_status"] = status
        counts[status] += 1
        belief_observations.append(stored)
        belief_statements.extend(statements)
        visited_urls.add(observation["canonical_url"])
        if observation.get("feed_url"):
            visited_urls.add(observation["feed_url"])


def _hash_known(state: CollectionState, url: str, content_hash: str | None) -> bool:
    payload = state.items.get(url)
    if not payload or not content_hash:
        return False
    return any(version.get("content_hash") == content_hash for version in payload.get("versions") or [])


def _replay_cached(state, lead, counts, belief_observations, belief_statements, visited_urls) -> bool:
    key = lead.get("url")
    payload = state.items.get(key)
    if not payload:
        return False
    item = dict(payload["item"])
    item["ingest_status"] = "unchanged"
    counts["unchanged"] += 1
    belief_observations.append(item)
    belief_statements.extend(payload.get("statements") or [])
    visited_urls.add(key)
    return True


def _check(checked: dict, url: str, state: CollectionState, *, success: bool, checked_at: str | None) -> None:
    row = state.sources.get(url) or {}
    checked[url] = {
        "last_checked_at": checked_at,
        "last_success_at": row.get("last_success_at") if success or row.get("last_success_at") else None,
    }
    if success:
        checked[url]["last_success_at"] = row.get("last_success_at")


def _tally(ingested: list[dict], counts: dict) -> str:
    if not ingested:
        counts["unchanged"] += 1
        return "unchanged"
    order = {"new": 0, "unchanged": 1, "version_changed": 2, "duplicate_candidate": 1}
    worst = "unchanged"
    for row in ingested:
        status = row["status"]
        if status == "new":
            counts["new"] += 1
        elif status == "version_changed":
            counts["changed"] += 1
        else:
            counts["unchanged"] += 1
        if order.get(status, 1) >= order.get(worst, 1):
            worst = "changed" if status == "version_changed" else status
    if any(row["status"] == "version_changed" for row in ingested):
        return "changed"
    if any(row["status"] == "new" for row in ingested):
        return "new"
    return "unchanged"


def _stored_for_identity(store: ObservationStore, identity: str) -> list:
    kept = []
    for item in store.items.values():
        if any(version.get("source_identity") == identity for version in item.versions):
            kept.append(item)
    return kept


def _belief_urls(leads: list[dict]) -> set[str]:
    urls = set()
    for lead in leads:
        if lead.get("kind") == "lead" or not lead.get("url"):
            continue
        try:
            urls.add(canonicalize_url(lead["url"]))
        except ValueError:
            continue
    return urls


def _work_items(sources: list[dict], leads: list[dict]) -> list[dict]:
    items = []
    belief_urls = _belief_urls(leads)
    for source in sources:
        adapted = adapter_source(source)
        if adapted is None:
            continue
        if source.get("continuously_collectible") is False:
            continue
        try:
            if canonicalize_url(source["canonical_url"]) in belief_urls:
                continue
        except ValueError:
            pass
        adapted["registry_url"] = source["canonical_url"]
        items.append({"kind": "adapter", "key": source["id"], "source": adapted})
    for lead in leads:
        if lead.get("kind") == "lead":
            continue
        items.append({"kind": "belief", "key": lead.get("url") or "", "lead": lead})
    items.sort(key=lambda row: row["key"])
    return items


def _select(items: list[dict], cursor: str | None, max_sources: int) -> tuple[list[dict], str | None, str | None]:
    if not items or max_sources <= 0:
        return [], cursor, cursor
    keys = [item["key"] for item in items]
    start = 0
    if cursor and cursor in keys:
        start = (keys.index(cursor) + 1) % len(keys)
    ordered = items[start:] + items[:start]
    selected = ordered[: min(max_sources, len(ordered))]
    return selected, cursor, selected[-1]["key"]


def _reindex(statements: list[dict]) -> None:
    for index, statement in enumerate(statements):
        statement["local_id"] = f"st{index:05d}"


def _merge_enrichment(document: dict, rows: list[dict]) -> None:
    if not rows:
        return
    seen = {source["slug"] for source in document["sources"]}
    urls = {source["canonical_url"] for source in document["sources"]}
    for row in rows:
        if row.get("slug") in seen or row.get("canonical_url") in urls:
            continue
        if "slug" not in row or "source_type" not in row:
            continue
        document["sources"].append(row)
        seen.add(row["slug"])
        urls.add(row["canonical_url"])


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_fetch_result(url: str, status: int, body: bytes, headers: dict[str, str] | None = None) -> FetchResult:
    return FetchResult(url=url, status=status, headers={key.lower(): value for key, value in (headers or {}).items()}, body=body)
