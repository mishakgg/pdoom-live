"""One bounded refresh. It does not enable a schedule and it does not import."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from pdoom_pipeline.belief.changes import view_change_candidates
from pdoom_pipeline.belief.collect import collect_beliefs
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.export.corpus import export_corpus
from pdoom_pipeline.export.versions import merge_observation_store
from pdoom_pipeline.urls import canonicalize_url
from pdoom_pipeline.fetch import FetchResult, SafeFetcher
from pdoom_pipeline.ingest.collection_state import CollectionState, utc_now
from pdoom_pipeline.ingest.staging import belief_dir, enrichment_dir, read_enrichment_sources, state_dir, write_belief_staging
from pdoom_pipeline.ingest.store import ObservationStore
from pdoom_pipeline.refresh.runtime import adapter_source, call_adapter, ingest_observations
from pdoom_pipeline.refresh.admission import public_url, url_scope
from pdoom_pipeline.rights import CollectionPolicy, collection_policy
from pdoom_pipeline.ingest.writes import WriteBytes, atomic_bytes

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
    write_bytes: WriteBytes | None = None,
) -> dict[str, Any]:
    """Refresh a bounded slice, then assemble canonical output from staging."""
    started = now or _iso()
    state = CollectionState.load(state_dir(collection_dir) / "collection_state.json", write_bytes)
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
    work = _work_items(registry_sources if include_adapters else [], leads if include_belief else [], started)
    for item in work:
        identity = item.get("identity") or (item.get("source") or {}).get("source_identity")
        if identity in state.bindings and state.bindings[identity] != item.get("binding"):
            item["error"] = CollectorFailure("blocked_by_policy", "source identity changed; admission review required")
        elif identity and identity not in state.bindings and not item.get("error"):
            source = item.get("source") or {}
            lead = item.get("lead") or {}
            fetch_url = source.get("url") or lead.get("fetch_url") or item["key"]
            expected_urls = {fetch_url, source.get("registry_url")}
            for old_key, old in state.sources.items():
                if source and old.get("source_identity") == identity and old_key not in expected_urls:
                    item["error"] = CollectorFailure("blocked_by_policy", "legacy source identity changed URL; review required")
            legacy = state.sources.get(fetch_url)
            if source and not legacy:
                old = state.sources.get(source.get("registry_url"))
                if old and old.get("source_identity") == identity:
                    # OpenAlex used the registry URL before validators were keyed
                    # by the actual generated request. Keep its last good success.
                    state.sources[fetch_url] = {**old, "canonical_url": fetch_url}
            if lead and legacy:
                if legacy.get("source_identity") in {lead.get("person_slug"), lead.get("show_slug")}:
                    # URL and admitted owner agree with the old person/show key.
                    legacy["source_identity"] = identity
                elif legacy.get("source_identity") != identity:
                    item["error"] = CollectorFailure("blocked_by_policy", "legacy lead attribution changed; review required")
    _enforce_retained_policy(state, store, registry_sources, leads, work, started)
    selected, cursor_before, _planned = _select(work, state.cursor, max_sources)
    cursor_after = state.cursor
    counts = {"new": 0, "changed": 0, "unchanged": 0, "skipped": 0, "failed": 0}
    errors: list[str] = []
    belief_observations: list[dict] = []
    belief_statements: list[dict] = []
    runs: list[dict] = []
    checked: dict[str, dict[str, str | None]] = {}
    visited_urls: set[str] = set()
    successful = 0
    interrupted = False

    for item in selected:
        if (cancelled and cancelled()) or client.clock() >= client.deadline_at:
            interrupted = True
            errors.append("refresh interrupted before completing selected sources")
            break
        pending: dict[str, bytes] = {}
        policy = item.get("policy") or CollectionPolicy(False)
        client.last = None
        client.url_policy = item.get("scope")
        primary_url = (item.get("source") or {}).get("url") or (item.get("lead") or {}).get("fetch_url") or item["key"]
        client.cache_get = lambda url: state.read_body(url, now=started) if policy.raw_until and url == primary_url else None
        client.cache_put = lambda url, body, _headers: pending.__setitem__(url, body)
        if item.get("error"):
            counts["failed"] += 1
            errors.append(f"{item['key']}: {item['error'].error_class}")
            _check(checked, item.get("url") or item["key"], state, success=False, checked_at=started)
            continue
        if item["kind"] == "adapter":
            success = _run_adapter_item(
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
            success = _run_belief_item(
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
        if success:
            successful += 1
            cursor_after = item["key"]
            state.cursor = cursor_after
            if policy.raw_until:
                for url, body in pending.items():
                    if url == primary_url:
                        state.write_body(url, body, expires_at=policy.raw_until, rights_basis=policy.rights_basis or "")
        state.save()
        store.save(state_dir(collection_dir) / "observations.json", write_bytes)
    client.cache_put = None
    client.cache_get = None
    client.url_policy = None

    retained_observations, retained_statements = state.retained_for(visited_urls)
    for observation in retained_observations:
        observation["ingest_status"] = "unchanged"
        counts["unchanged"] += 1
    belief_observations.extend(retained_observations)
    belief_statements.extend(retained_statements)
    _reindex(belief_statements)
    completed = completed_at or _iso()
    failed = counts["failed"]
    if successful and (failed or interrupted):
        status = "partial"
    elif successful:
        status = "succeeded"
    else:
        status = "failed"
        if not errors:
            errors.append("no source completed a successful check")
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
        write_bytes=write_bytes,
    )
    document = export_corpus(result, seed_dir=seed_dir, generated_at=completed)
    merge_observation_store(document, store, registry_sources)
    _merge_enrichment(document, read_enrichment_sources(collection_dir))
    canonical = collection_dir / "canonical-live.json"
    atomic_bytes(canonical, json.dumps(document).encode(), write_bytes)
    state.save()
    store.save(state_dir(collection_dir) / "observations.json", write_bytes)
    if enrichment_dir(collection_dir).exists():
        belief_names = {path.name for path in belief_dir(collection_dir).glob("*")}
        overlap = belief_names.intersection(path.name for path in enrichment_dir(collection_dir).glob("*") if path.name != "README.md")
        if overlap:
            raise RuntimeError(f"belief staging collided with enrichment files: {sorted(overlap)}")
    return {"status": status, "counts": counts, "cursor": cursor_after, "document": document, "result": result,
            "publication": {"imported": False, "public_revocations_applied": False},
            "policy_decisions": [{"source_key": item["key"], **asdict(item["policy"])}
                                 for item in work if item.get("policy") and not item.get("error")]}


def _run_adapter_item(item, *, client, state, store, observed_at, counts, errors, checked, visited_urls) -> bool:
    source = item["source"]
    key = source["url"]
    identity = source["source_identity"]
    registry_url = source.get("registry_url") or key
    if not state.eligible(key, observed_at):
        counts["skipped"] += 1
        _check(checked, registry_url, state, success=False, checked_at=None, state_key=key)
        return False
    try:
        state.bind(identity, item["binding"])
        state.record_attempt(key, identity=identity, url=key, now=observed_at)
        fetched = call_adapter(source["adapter"], fetcher=client, source=source, observed_at=observed_at)
        for observation in fetched["observations"]:
            _restrict_observation(observation, item["policy"])
        ingested = ingest_observations(store, fetched["observations"])
    except CollectorFailure as exc:
        _failure(state, key, observed_at, exc, counts, errors)
        _check(checked, registry_url, state, success=False, checked_at=observed_at, state_key=key)
        return False
    outcome = _tally(ingested, counts)
    state.source(key)["collection_policy"] = asdict(item["policy"])
    state.record_outcome(key, outcome=outcome, now=observed_at, success=True,
                         etag=fetched.get("etag"), last_modified=fetched.get("last_modified"),
                         content_hash=ingested[-1]["content_hash"] if ingested else None)
    visited_urls.add(key)
    _check(checked, registry_url, state, success=True, checked_at=observed_at, state_key=key)
    return True


def _run_belief_item(
    item, *, people, client, state, observed_at, counts, errors, checked,
    visited_urls, belief_observations, belief_statements, runs,
) -> bool:
    lead = item["lead"]
    key = lead.get("fetch_url") or lead["url"]
    if not state.eligible(key, observed_at):
        counts["skipped"] += 1
        _check(checked, lead["url"], state, success=False, checked_at=None, state_key=key)
        return False
    responses: dict[str, FetchResult] = {}
    failed: list[CollectorFailure] = []

    def fetch_bytes(url: str) -> bytes:
        try:
            result = client.get(url)
        except CollectorFailure as exc:
            if url.endswith("/robots.txt") and exc.error_class == "not_found":
                return b""
            failed.append(exc)
            raise
        responses[url] = result
        return result.body

    try:
        state.bind(item["identity"], item["binding"])
        state.record_attempt(key, identity=item["identity"], url=key, now=observed_at)
        partial = collect_beliefs(people=people, leads=[lead], fetch_bytes=fetch_bytes,
                                 observed_at=observed_at, priority_slugs={person["slug"] for person in people})
    except CollectorFailure as exc:
        failed.append(exc)
        partial = {"observations": [], "statements": [], "runs": []}
    except Exception:
        failed.append(CollectorFailure("collector_bug", "belief collector failed before validation"))
        partial = {"observations": [], "statements": [], "runs": []}
    # Collector run failures include parsers, robots and attribution. HTTP success
    # alone cannot commit validators, bodies, observations or successful freshness.
    for run in partial.get("runs") or []:
        if run.get("status") == "failure":
            failed.append(CollectorFailure(run.get("error_class") or "collector_bug", "belief collector did not complete"))
    for deferred in partial.get("source_leads") or []:
        failed.append(CollectorFailure(deferred.get("reason_not_admitted") or "blocked_by_policy", "belief lead was not collected"))
    runs.extend(partial.get("runs") or [])
    if failed:
        _failure(state, key, observed_at, failed[-1], counts, errors)
        _check(checked, lead["url"], state, success=False, checked_at=observed_at, state_key=key)
        return False
    # Empty, valid feeds are successful checks too. They need an actual response.
    response = responses.get(key)
    if response is None:
        _failure(state, key, observed_at, CollectorFailure("invalid_content", "no source response was validated"), counts, errors)
        _check(checked, lead["url"], state, success=False, checked_at=observed_at, state_key=key)
        return False
    if not item["policy"].extraction:
        partial["statements"] = []
    if not item["policy"].evidence:
        for observation in partial["observations"]:
            for field in ("evidence_body", "summary", "article_text", "locators"):
                observation.pop(field, None)
    _absorb_belief(partial, state, counts, belief_observations, belief_statements, visited_urls,
                   forced_unchanged=response.not_modified)
    if not partial["observations"]:
        counts["unchanged"] += 1
    state.source(key)["collection_policy"] = asdict(item["policy"])
    state.record_outcome(key, outcome="unchanged" if response.not_modified else "fetched",
                         now=observed_at, success=True, etag=response.headers.get("etag"),
                         last_modified=response.headers.get("last-modified"))
    _check(checked, lead["url"], state, success=True, checked_at=observed_at, state_key=key)
    return True


def _failure(state, key, now, exc, counts, errors) -> None:
    state.record_outcome(key, outcome="failed", now=now, success=False,
                         error_class=exc.error_class, message=str(exc), retry_after=exc.retry_after)
    counts["failed"] += 1
    errors.append(f"{key}: {exc.error_class}")


def _restrict_observation(observation, policy: CollectionPolicy) -> None:
    # Feed bodies can be used in-memory to hash/extract; never duplicate them in
    # indefinitely retained normalized metadata, even for a licensed raw cache.
    for field in ("upstream_version", "raw_body", "article_text", "evidence_body"):
        observation.metadata.pop(field, None)
    if not policy.evidence:
        observation.segments = []
    else:
        for segment in observation.segments:
            segment.text = segment.text[:2000]


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


def _check(checked: dict, url: str, state: CollectionState, *, success: bool, checked_at: str | None, state_key: str | None = None) -> None:
    row = state.sources.get(state_key or url) or {}
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


def _work_items(sources: list[dict], leads: list[dict], now: str) -> list[dict]:
    items = []
    belief_urls = _belief_urls(leads)
    ids = [source.get("id") for source in sources]
    registry = {source.get("canonical_url"): source for source in sources}
    source_urls = [source.get("canonical_url") for source in sources]
    lead_urls = [lead.get("url") for lead in leads if lead.get("kind") != "lead"]
    for source in sources:
        if not source.get("enabled", True) or source.get("continuously_collectible") is False:
            continue
        if source.get("collection_method") not in {"rss_feed", "github_api", "openalex_api", "arxiv_api"}:
            continue
        key = source.get("id") or source.get("canonical_url") or "invalid-source"
        try:
            if ids.count(key) > 1 or source_urls.count(source.get("canonical_url")) > 1:
                raise CollectorFailure("blocked_by_policy", "duplicate source identity or URL in registry")
            policy = collection_policy(source, now=now)
            if not policy.admitted:
                raise CollectorFailure("blocked_by_policy", "source has no explicit collection admission")
            adapted = adapter_source(source)
            if adapted is None:
                continue
            if canonicalize_url(source["canonical_url"]) in belief_urls:
                continue
            adapted["registry_url"] = source["canonical_url"]
            items.append({"kind": "adapter", "key": key, "source": adapted, "policy": policy,
                          "binding": _binding(source), "scope": url_scope(source, adapted["url"])})
        except (CollectorFailure, KeyError, ValueError) as exc:
            error = exc if isinstance(exc, CollectorFailure) else CollectorFailure("invalid_content", "invalid source configuration")
            items.append({"kind": "adapter", "key": key, "url": source.get("canonical_url"), "error": error})
    for lead in leads:
        if lead.get("kind") == "lead":
            continue
        key = lead.get("url") or "invalid-lead"
        try:
            if lead_urls.count(key) > 1 or source_urls.count(key) > 1:
                raise CollectorFailure("blocked_by_policy", "duplicate belief URL admission")
            row = registry.get(key)
            policy = collection_policy(lead, now=now, lead=True)
            if row:
                registry_policy = collection_policy(row, now=now)
                if not registry_policy.admitted:
                    raise CollectorFailure("blocked_by_policy", "registry disables this belief lead")
                # Both admissions apply; neither route can widen the other's rights.
                policy = CollectionPolicy(policy.admitted, policy.evidence and registry_policy.evidence,
                                          policy.extraction and registry_policy.extraction,
                                          min(policy.raw_until, registry_policy.raw_until, key=utc_now) if policy.raw_until and registry_policy.raw_until else None,
                                          policy.rights_basis)
            if not policy.admitted:
                raise CollectorFailure("blocked_by_policy", "lead has no explicit collection admission")
            public_url(key)
            fetch_url = lead.get("fetch_url") or key
            scope = url_scope(lead, key)
            scope(fetch_url)
            identity = "lead:" + key
            items.append({"kind": "belief", "key": key, "lead": lead, "policy": policy,
                          "identity": identity, "binding": _binding(lead), "scope": scope})
        except (CollectorFailure, KeyError, ValueError) as exc:
            error = exc if isinstance(exc, CollectorFailure) else CollectorFailure("invalid_content", "invalid lead configuration")
            items.append({"kind": "belief", "key": key, "url": key, "error": error})
    items.sort(key=lambda row: row["key"])
    return items


def _binding(row: dict) -> str:
    return json.dumps({key: row.get(key) for key in ("canonical_url", "url", "fetch_url", "collection_method", "external_id",
                                                   "owner_person_id", "owner_organization_id", "person_slug", "show_slug", "kind")}, sort_keys=True)


def _enforce_retained_policy(state, store, sources, leads, work, now):
    policies = {}
    for row, is_lead in [(row, False) for row in sources] + [(row, True) for row in leads if row.get("kind") != "lead"]:
        try:
            policy = collection_policy(row, now=now, lead=is_lead)
        except CollectorFailure:
            policy = CollectionPolicy(False)
        key = row.get("url") if is_lead else row.get("canonical_url")
        previous = policies.get(key)
        if previous:
            policy = CollectionPolicy(previous.admitted and policy.admitted, previous.evidence and policy.evidence,
                                      previous.extraction and policy.extraction)
        policies[key] = policy
    for item in work:
        if item.get("error"):
            url = item.get("url") or (item.get("source") or {}).get("registry_url") or item["key"]
            policies[url] = CollectionPolicy(False)
    for key, payload in list(state.items.items()):
        item = payload["item"]
        policy = policies.get(item.get("feed_url") or key) or CollectionPolicy(False)
        if not policy.admitted:
            del state.items[key]
        else:
            if not policy.extraction:
                payload["statements"] = []
            if not policy.evidence:
                item.pop("locators", None)
    # Not selecting an adapter in this pass is not revocation. Retention follows
    # the full supplied registry, not the active source slice or collection flags.
    admitted_ids = set()
    for row in sources:
        identity = row.get("id")
        if sum(other.get("id") == identity for other in sources) > 1:
            continue
        if sum(other.get("canonical_url") == row.get("canonical_url") for other in sources) > 1:
            continue
        policy = policies.get(row.get("canonical_url")) or CollectionPolicy(False)
        try:
            if policy.admitted and adapter_source(row) is not None:
                if identity not in state.bindings or state.bindings[identity] == _binding(row):
                    admitted_ids.add(identity)
        except (CollectorFailure, KeyError, ValueError):
            continue
    for key, item in list(store.items.items()):
        item.versions = [version for version in item.versions if version.get("source_identity") in admitted_ids]
        if not item.versions:
            del store.items[key]
            continue
        for version in item.versions:
            policy_row = next((row for row in sources if row.get("id") == version.get("source_identity")), {})
            policy = policies.get(policy_row.get("canonical_url")) or CollectionPolicy(False)
            for field in ("upstream_version", "raw_body", "article_text", "evidence_body"):
                (version.get("metadata") or {}).pop(field, None)
            if not policy.evidence:
                version["segments"] = []
    # Rebuild indexes after admission revocation so old URLs cannot alias new IDs.
    rebuilt = ObservationStore.from_dict(store.to_dict())
    store.by_url, store.by_upstream = rebuilt.by_url, rebuilt.by_upstream
    allowed = {}
    for url, permission in state.raw_bodies.items():
        for item in work:
            policy = item.get("policy")
            if not policy or not policy.raw_until or item.get("error"):
                continue
            try:
                primary_url = (item.get("source") or {}).get("url") or (item.get("lead") or {}).get("fetch_url") or item["key"]
                if url != primary_url:
                    continue
                item["scope"](url)
                # Keep the original expiry; a later policy cannot silently extend it.
                expiry = min(permission["expires_at"], policy.raw_until, key=utc_now)
                if utc_now(expiry) > utc_now(now):
                    allowed[url] = {"expires_at": expiry, "rights_basis": policy.rights_basis}
                break
            except CollectorFailure:
                continue
    state.purge_bodies(allowed)


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
