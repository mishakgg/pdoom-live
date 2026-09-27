"""Fetch the belief corpus for cohort 2026.09.0. Does not add people."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from pdoom_pipeline.belief.collect import collect_beliefs, dumps_jsonl, summarize
from pdoom_pipeline.belief.priority import priority_rows
from pdoom_pipeline.enrich.merge import source_record
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.export.corpus import export_corpus
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.quality.report import write_report
from pdoom_pipeline.seed.build import SEED_DIR, _write_jsonl, load_jsonl
from pdoom_pipeline.urls import canonicalize_url

ROOT = Path(__file__).resolve().parents[3]
LEADS = SEED_DIR / "belief_sources.jsonl"
COLLECTION = ROOT / "data" / "collections" / "cohort-v2026-09"


def run(seed_dir: Path | None = None) -> dict:
    directory = seed_dir or SEED_DIR
    people = load_jsonl(directory / "people.jsonl")
    if len(people) != 323:
        raise RuntimeError(f"cohort size changed: {len(people)}")
    leads = load_jsonl(directory / "belief_sources.jsonl") if seed_dir else load_jsonl(LEADS)
    lead_slugs = {row["person_slug"] for row in leads if row.get("person_slug")}
    sources = load_jsonl(directory / "sources.jsonl")
    covered = set()
    for source in sources:
        if source.get("source_type") != "openalex_works" and source.get("owner_person_id"):
            covered.add(source["owner_person_id"].split(":", 1)[1])
    priority = priority_rows(people, lead_slugs=lead_slugs, covered_slugs=covered)
    priority_slugs = {row["person_slug"] for row in priority}
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fetcher = SafeFetcher(
        allowed_content_types=("application/rss+xml", "application/atom+xml", "application/xml", "text/xml", "text/plain", "text/html", "application/xhtml+xml", "application/octet-stream"),
        max_bytes=6_000_000,
        timeout=20,
    )

    def fetch_bytes(url: str) -> bytes:
        time.sleep(0.12)
        return fetcher.get(url).body

    result = collect_beliefs(
        people=people,
        leads=leads,
        fetch_bytes=fetch_bytes,
        observed_at=observed_at,
        priority_slugs=priority_slugs,
    )
    _register_sources(directory, leads, result)
    COLLECTION.mkdir(parents=True, exist_ok=True)
    (COLLECTION / "source_observations.jsonl").write_text(_observations(result), encoding="utf-8")
    (COLLECTION / "candidate_statements.jsonl").write_text(dumps_jsonl(result["statements"]), encoding="utf-8")
    (COLLECTION / "view_changes.jsonl").write_text(dumps_jsonl(result["relationships"]), encoding="utf-8")
    (directory / "collection_priority.jsonl").write_text(dumps_jsonl(priority), encoding="utf-8")
    document = export_corpus(result, seed_dir=directory, generated_at=observed_at)
    (COLLECTION / "canonical-live.json").write_text(json.dumps(document), encoding="utf-8")
    summary = summarize(result)
    summary["priority_people"] = len(priority)
    summary["people"] = len(people)
    (COLLECTION / "belief-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_report(directory, result["runs"], corpus=summary)
    return summary


def _register_sources(directory: Path, leads: list[dict], result: dict) -> None:
    existing = load_jsonl(directory / "sources.jsonl")
    urls = {row["canonical_url"] for row in existing}
    additions = []
    for lead in leads:
        if lead["url"] in urls:
            continue
        if lead["kind"] == "essay":
            additions.append(
                source_record(
                    person_id=f"person:{lead['person_slug']}",
                    source_type=lead["source_type"] if lead["source_type"] in {"blog", "newsletter", "personal_website"} else "blog",
                    name=lead["name"],
                    canonical_url=canonicalize_url(lead["url"]),
                    platform=lead.get("source_type") or "blog",
                    collection_method="html_page",
                    enabled=True,
                    verification_method="owned_page_byline",
                    rights_notes=lead["basis"],
                )
            )
            continue
        if lead["kind"] == "show_feed":
            additions.append(
                {
                    "id": f"src:show:{lead['show_slug']}",
                    "source_type": "podcast",
                    "name": lead["name"],
                    "canonical_url": lead["url"],
                    "platform": "podcast",
                    "owner_person_id": None,
                    "owner_organization_id": None,
                    "collection_method": "rss_feed",
                    "rights_notes": lead["basis"],
                    "enabled": True,
                    "continuously_collectible": True,
                    "review_state": "machine_validated",
                    "verification_method": "official_show_feed",
                }
            )
            continue
        owner = lead.get("person_slug")
        if not owner:
            owners = sorted({row["person_slug"] for row in result["observations"] if row["feed_url"] == lead["url"]})
            if len(owners) != 1:
                slug = lead.get("show_slug") or "feed-" + lead["name"].lower().replace(" ", "-")
                additions.append(
                    {
                        "id": f"src:show:{slug}",
                        "source_type": lead["source_type"] if lead["source_type"] in {"blog", "newsletter", "podcast"} else "blog",
                        "name": lead["name"],
                        "canonical_url": lead["url"],
                        "platform": lead["source_type"],
                        "owner_person_id": None,
                        "owner_organization_id": None,
                        "collection_method": "rss_feed",
                        "rights_notes": lead["basis"],
                        "enabled": True,
                        "continuously_collectible": True,
                        "review_state": "machine_validated",
                        "verification_method": "author_matched_feed",
                    }
                )
                continue
            owner = owners[0]
        additions.append(
            source_record(
                person_id=f"person:{owner}",
                source_type=lead["source_type"],
                name=lead["name"],
                canonical_url=lead["url"],
                platform=lead["source_type"],
                collection_method="rss_feed",
                enabled=True,
                verification_method="owned_feed_author",
                rights_notes=lead["basis"],
            )
        )
    if additions:
        _write_jsonl(directory / "sources.jsonl", existing + additions)


def _observations(result: dict) -> str:
    rows = []
    for item in result["observations"]:
        row = dict(item)
        row.pop("evidence_body", None)
        row.pop("summary", None)
        row.pop("article_text", None)
        rows.append(row)
    return dumps_jsonl(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect belief and forecast evidence for the existing cohort.")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        raise SystemExit("Refusing to fetch without --live.")
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
