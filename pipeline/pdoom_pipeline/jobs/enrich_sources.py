"""Attach verified pages, rel=me identities, and public feeds for cohort 2026.09.0.

Does not add people. Does not search social networks by name.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.collectors.github import GitHubCollector
from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.enrich.discover import discover_from_orcid_urls, discover_from_page
from pdoom_pipeline.enrich.html_page import feed_is_acceptable, host_is_blocked, parse_html, strip_markup
from pdoom_pipeline.enrich.merge import merge_records
from pdoom_pipeline.enrich.orcid import researcher_urls
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.extract.statements import EXTRACTOR_VERSION, extract_statements, infer_topic_signal
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.ingest.store import ObservationStore
from pdoom_pipeline.quality.report import write_report
from pdoom_pipeline.seed.build import SEED_DIR, load_jsonl, _write_jsonl

HTML_TYPES = ("text/html", "application/xhtml+xml", "text/plain", "application/xml", "application/octet-stream")
ORCID_TYPES = ("application/json", "application/vnd.orcid+json", "application/octet-stream")
MAX_FEED_ITEMS = 12


def org_hosts(orgs: list[dict]) -> set[str]:
    hosts = set()
    for org in orgs:
        host = (urlparse(org.get("canonical_url") or "").hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            hosts.add(host)
    return hosts


def enrich(
    *,
    people: list[dict],
    identities: list[dict],
    sources: list[dict],
    ambiguities: list[dict],
    orgs: list[dict],
    fetch_text,
    fetch_json,
    observed_at: str,
    collect_feed=None,
    collect_github=None,
) -> dict:
    """fetch_text(url) -> (final_url, html) or raises CollectorFailure. fetch_json likewise returns dict."""
    hosts = org_hosts(orgs)
    orcid_by_person = {
        row["person_id"]: row["external_id"]
        for row in identities
        if row.get("namespace") == "orcid" and row.get("external_id")
    }
    decisions = []
    runs = []
    identity_additions = []
    source_additions = []
    feeds = []
    person_count = len(people)
    for person in people:
        person_id = person["id"]
        variants = list(person.get("name_variants") or [])
        pending = []
        for claimed in person.get("claimed_urls") or []:
            url = claimed.get("url") if isinstance(claimed, dict) else claimed
            if url:
                pending.append({"url": url, "verification_method": "claimed_url_page_name", "label": "claimed"})
        orcid = orcid_by_person.get(person_id)
        if orcid:
            orcid_url = f"https://pub.orcid.org/v3.0/{orcid}"
            try:
                record = fetch_json(orcid_url)
                found = researcher_urls(record if isinstance(record, dict) else {})
                orcid_found = discover_from_orcid_urls(person_id=person_id, urls=found, verified_at=observed_at)
                source_additions.extend(orcid_found["sources"])
                pending.extend(
                    {**item, "verification_method": "orcid_researcher_url"} for item in orcid_found["pending_pages"]
                )
                runs.append({"status": "success", "kind": "orcid", "url": orcid_url, "person_id": person_id})
            except CollectorFailure as exc:
                runs.append(
                    {
                        "status": "failure",
                        "kind": "orcid",
                        "url": orcid_url,
                        "person_id": person_id,
                        "error_class": exc.error_class,
                    }
                )
                decisions.append({"person_id": person_id, "orcid": orcid, "reason": exc.error_class})
        seen_urls = set()
        for item in pending[:8]:
            url = item["url"]
            if url in seen_urls or host_is_blocked(url):
                continue
            seen_urls.add(url)
            try:
                final_url, html = fetch_text(url)
            except CollectorFailure as exc:
                runs.append(
                    {"status": "failure", "kind": "page", "url": url, "person_id": person_id, "error_class": exc.error_class}
                )
                decisions.append({"person_id": person_id, "page_url": url, "name_confirmed": False, "reason": exc.error_class})
                continue
            parsed = parse_html(html, page_url=final_url)
            found = discover_from_page(
                person_id=person_id,
                display_name=person["display_name"],
                variants=variants,
                page_url=final_url,
                parsed=parsed,
                verification_method=item["verification_method"],
                verified_at=observed_at,
                org_hosts=hosts,
            )
            identity_additions.extend(found["identities"])
            source_additions.extend(found["sources"])
            feeds.extend(found["feeds"])
            decisions.append(found["decision"])
            runs.append({"status": "success", "kind": "page", "url": final_url, "person_id": person_id})
    identities = [row for row in identities if _row_allowed(row)]
    sources = [row for row in sources if _row_allowed(row)]
    identity_additions = [row for row in identity_additions if _row_allowed(row)]
    source_additions = [row for row in source_additions if _row_allowed(row)]
    feeds = [row for row in feeds if feed_is_acceptable(row["feed_url"])]
    identities, identity_ambiguities = merge_records(
        identities, identity_additions, key_fields=("namespace", "external_id")
    )
    sources, source_ambiguities = merge_records(sources, source_additions, key_fields=("canonical_url",))
    ambiguities = list(ambiguities) + identity_ambiguities + source_ambiguities
    observations, dead_feeds = _collect_feeds(feeds, collect_feed, runs, observed_at)
    for source in sources:
        if source.get("canonical_url") in dead_feeds:
            source["enabled"] = False
            source["continuously_collectible"] = False
    observations.extend(_collect_github_sources(sources, collect_github, runs, observed_at))
    statements = _statements_from_observations(observations)
    if len(people) != person_count:
        raise RuntimeError("enrichment changed the cohort size")
    return {
        "people": people,
        "identities": identities,
        "sources": sources,
        "ambiguities": ambiguities,
        "decisions": decisions,
        "runs": runs,
        "observations": observations,
        "statements": statements,
        "people_count": len(people),
    }


def _row_allowed(row: dict) -> bool:
    url = row.get("canonical_url") or ""
    if host_is_blocked(url):
        return False
    if row.get("source_type") == "rss" and not feed_is_acceptable(url):
        return False
    path = (urlparse(url).path or "").lower()
    directory = any(part in path.split("/") for part in {"team", "people", "faculty", "staff", "equipo", "about"})
    if directory and row.get("namespace") == "personal_website":
        return False
    if directory and row.get("source_type") == "personal_website":
        return False
    return True


def _collect_feeds(feeds: list[dict], collect_feed, runs: list[dict], observed_at: str) -> tuple[list[dict], set[str]]:
    if collect_feed is None:
        return [], set()
    observations = []
    dead = set()
    seen = set()
    for feed in feeds:
        url = feed["feed_url"]
        if url in seen:
            continue
        seen.add(url)
        try:
            batch = collect_feed(url, feed["person_id"])[:MAX_FEED_ITEMS]
        except CollectorFailure as exc:
            runs.append({"status": "failure", "kind": "feed", "url": url, "person_id": feed["person_id"], "error_class": exc.error_class})
            if exc.error_class == "not_found":
                dead.add(url)
            continue
        runs.append({"status": "success", "kind": "feed", "url": url, "person_id": feed["person_id"], "items": len(batch)})
        observations.extend(batch)
    return observations, dead


def _collect_github_sources(sources: list[dict], collect_github, runs: list[dict], observed_at: str) -> list[dict]:
    if collect_github is None:
        return []
    observations = []
    for source in sources:
        if source.get("source_type") != "github" or not source.get("enabled"):
            continue
        username = (urlparse(source["canonical_url"]).path or "").strip("/")
        if not username or "/" in username:
            continue
        try:
            batch = collect_github(username, source["owner_person_id"], source["id"])
        except CollectorFailure as exc:
            runs.append(
                {
                    "status": "failure",
                    "kind": "github",
                    "url": source["canonical_url"],
                    "person_id": source["owner_person_id"],
                    "error_class": exc.error_class,
                }
            )
            if exc.error_class == "rate_limited":
                break
            continue
        runs.append({"status": "success", "kind": "github", "url": source["canonical_url"], "person_id": source["owner_person_id"], "items": len(batch)})
        observations.extend(batch)
    return observations


def _statements_from_observations(observations: list[dict]) -> list[dict]:
    rows = []
    for observation in observations:
        text = strip_markup(" ".join(segment.get("text") or "" for segment in observation.get("segments") or []))
        person_id = observation.get("person_id")
        for statement in extract_statements(text, person_id=person_id):
            statement.update(
                {
                    "source_url": observation.get("canonical_url"),
                    "observed_at": observation.get("observed_at"),
                    "published_at": observation.get("published_at"),
                    "content_hash": observation.get("content_hash"),
                    "review_state": "unreviewed" if statement.get("review_state") == "unreviewed" else statement.get("review_state"),
                    "verified": False,
                }
            )
            rows.append(statement)
        signal = infer_topic_signal(text, person_id=person_id)
        if signal:
            signal.update(
                {
                    "source_url": observation.get("canonical_url"),
                    "observed_at": observation.get("observed_at"),
                    "published_at": observation.get("published_at"),
                    "content_hash": observation.get("content_hash"),
                    "verified": False,
                    "extractor_version": EXTRACTOR_VERSION,
                }
            )
            rows.append(signal)
    return rows


def _observation_dict(observation, person_id: str) -> dict:
    if isinstance(observation, dict):
        observation = dict(observation)
        observation["person_id"] = person_id
        return observation
    payload = observation.to_dict()
    payload["person_id"] = person_id
    return payload


def run_enrichment(seed_dir: Path | None = None, *, live: bool = False, pause_seconds: float = 0.2) -> dict:
    directory = seed_dir or SEED_DIR
    people = load_jsonl(directory / "people.jsonl")
    before = len(people)
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html_fetcher = SafeFetcher(allowed_content_types=HTML_TYPES, max_bytes=1_000_000, timeout=12)
    orcid_fetcher = SafeFetcher(allowed_content_types=ORCID_TYPES, max_bytes=2_000_000, timeout=12)
    rss = RssCollector()
    github = GitHubCollector()

    def fetch_text(url: str):
        if live:
            time.sleep(pause_seconds)
        result = html_fetcher.get(url, headers={"Accept": "text/html,application/xhtml+xml"})
        return result.url, result.body.decode("utf-8", errors="replace")

    def fetch_json(url: str):
        if live:
            time.sleep(pause_seconds)
        result = orcid_fetcher.get(url, headers={"Accept": "application/vnd.orcid+json"})
        return json.loads(result.body.decode("utf-8"))

    def collect_feed(url: str, person_id: str):
        if live:
            time.sleep(pause_seconds)
        observations = rss.collect(source_identity=f"feed:{person_id}", feed_url=url, observed_at=observed_at)
        return [_observation_dict(item, person_id) for item in observations]

    def collect_github(username: str, person_id: str, source_id: str):
        if not live:
            return []
        time.sleep(pause_seconds)
        observations = github.collect_repos(source_identity=source_id, username=username, observed_at=observed_at, per_page=5)
        return [_observation_dict(item, person_id) for item in observations]

    result = enrich(
        people=people,
        identities=load_jsonl(directory / "external_identities.jsonl"),
        sources=load_jsonl(directory / "sources.jsonl"),
        ambiguities=load_jsonl(directory / "ambiguities.jsonl"),
        orgs=load_jsonl(directory / "organizations.jsonl"),
        fetch_text=fetch_text,
        fetch_json=fetch_json,
        observed_at=observed_at,
        collect_feed=collect_feed if live else None,
        collect_github=collect_github if live else None,
    )
    if result["people_count"] != before:
        raise RuntimeError("cohort size changed")
    _write_jsonl(directory / "external_identities.jsonl", result["identities"])
    _write_jsonl(directory / "sources.jsonl", result["sources"])
    _write_jsonl(directory / "ambiguities.jsonl", result["ambiguities"])
    (directory / "enrichment.json").write_text(
        json.dumps(
            {
                "enriched_at": observed_at,
                "people": result["people_count"],
                "decisions": result["decisions"],
                "runs": result["runs"],
                "note": "Social accounts come only from rel=me on a name-confirmed page or from an ORCID researcher URL whose page contains the full name. Name search was not used. LinkedIn, Wikipedia, and sitewide feeds are not registered.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    collection_dir = directory.parents[2] / "collections" / "cohort-v2026-09"
    collection_dir.mkdir(parents=True, exist_ok=True)
    stored, observation_rows = _dedupe_observations(result["observations"])
    _write_jsonl(collection_dir / "source_observations.jsonl", observation_rows)
    _write_jsonl(collection_dir / "candidate_statements.jsonl", result["statements"])
    report = write_report(directory, result["runs"])
    return {"people": result["people_count"], "report": report, "runs": len(result["runs"]), "stored": stored}


def _dedupe_observations(observations: list[dict]) -> tuple[dict, list[dict]]:
    store = ObservationStore()
    rows = []
    for observation in observations:
        from pdoom_pipeline.contracts import AuthorCandidate, Segment, SourceObservation

        item = SourceObservation(
            source_identity=observation["source_identity"],
            platform=observation["platform"],
            upstream_id=observation.get("upstream_id"),
            canonical_url=observation["canonical_url"],
            observed_at=observation["observed_at"],
            published_at=observation.get("published_at"),
            author_candidates=[AuthorCandidate(**candidate) for candidate in observation.get("author_candidates") or []],
            title=observation.get("title"),
            segments=[
                Segment(
                    segment_kind=segment["segment_kind"],
                    sequence=segment["sequence"],
                    text=segment["text"],
                    start_char=segment.get("start_char"),
                    end_char=segment.get("end_char"),
                )
                for segment in observation.get("segments") or []
            ],
            metadata=observation.get("metadata") or {},
            content_hash=observation.get("content_hash") or "",
            collection_method=observation.get("collection_method") or "",
            collector=observation.get("collector") or "",
            collector_version=observation.get("collector_version") or "",
        )
        result = store.ingest(item)
        if result.status != "unchanged":
            row = item.to_dict()
            row["person_id"] = observation.get("person_id")
            row["ingest_status"] = result.status
            rows.append(row)
    return {"items": len(store.items), "written": len(rows)}, rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich verified sources for the existing cohort.")
    parser.add_argument("--live", action="store_true", help="Fetch ORCID and confirmed pages. Uses the network.")
    args = parser.parse_args()
    if not args.live:
        raise SystemExit("Refusing to rewrite the seed without --live. Tests call enrich() directly.")
    summary = run_enrichment(live=True)
    print(json.dumps({k: summary[k] for k in ("people", "runs")}, indent=2))


if __name__ == "__main__":
    main()
