"""Fetch the belief corpus for cohort 2026.09.0. Does not add people."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pdoom_pipeline.belief.collect import dumps_jsonl
from pdoom_pipeline.enrich.merge import source_record
from pdoom_pipeline.seed.build import SEED_DIR, _write_jsonl, load_jsonl
from pdoom_pipeline.urls import canonicalize_url

ROOT = Path(__file__).resolve().parents[3]
LEADS = SEED_DIR / "belief_sources.jsonl"
COLLECTION = ROOT / "data" / "collections" / "cohort-v2026-09"


def run(
    seed_dir: Path | None = None,
    *,
    max_sources: int = 40,
    max_seconds: float = 900,
    cancelled=None,
) -> dict:
    """Refresh a bounded slice of the cohort and assemble canonical output.

    Source rows already in the seed registry stay there. Belief output is
    written under the collection staging directory, not the enrichment directory.
    """
    from pdoom_pipeline.refresh.runner import run_refresh

    directory = seed_dir or SEED_DIR
    people = load_jsonl(directory / "people.jsonl")
    if seed_dir is None and len(people) != 323:
        raise RuntimeError(f"cohort size changed: {len(people)}")
    leads = load_jsonl(directory / "belief_sources.jsonl") if seed_dir else load_jsonl(LEADS)
    if not leads and (directory / "belief_sources.jsonl").exists():
        leads = load_jsonl(directory / "belief_sources.jsonl")
    sources = load_jsonl(directory / "sources.jsonl")
    collection = COLLECTION if seed_dir is None else seed_dir.parent / "collection"
    if seed_dir is not None:
        collection = Path(seed_dir).parent / "refresh-collection"
    refreshed = run_refresh(
        seed_dir=directory,
        collection_dir=collection if seed_dir is None else collection,
        people=people,
        leads=leads,
        registry_sources=sources,
        max_sources=max_sources,
        max_seconds=max_seconds,
        cancelled=cancelled,
    )
    if seed_dir is None:
        COLLECTION.mkdir(parents=True, exist_ok=True)
        document = refreshed["document"]
        (COLLECTION / "canonical-live.json").write_text(json.dumps(document), encoding="utf-8")
    summary = {
        "status": refreshed["status"],
        "counts": refreshed["counts"],
        "cursor": refreshed["cursor"],
        "people": len(people),
    }
    return summary


def _register_sources(directory: Path, leads: list[dict], result: dict) -> None:
    existing = _unique_sources(load_jsonl(directory / "sources.jsonl"))
    urls = {canonicalize_url(row["canonical_url"]) for row in existing}
    ids = {row["id"] for row in existing}
    additions = []

    def add(row: dict) -> None:
        url = canonicalize_url(row["canonical_url"])
        if row["id"] in ids or url in urls:
            return
        ids.add(row["id"])
        urls.add(url)
        additions.append(row)

    for lead in leads:
        if canonicalize_url(lead["url"]) in urls:
            continue
        if lead["kind"] == "lead":
            continue
        if lead["kind"] == "talk" and not lead.get("owned"):
            show = lead.get("show_slug")
            if not show:
                continue
            add(
                {
                    "id": f"src:show:{show}",
                    "source_type": lead["source_type"] if lead["source_type"] in {"video", "conference_talk", "testimony", "interview", "podcast"} else "video",
                    "name": lead["name"],
                    "canonical_url": canonicalize_url(lead["url"]),
                    "platform": lead.get("platform") or "video",
                    "owner_person_id": None,
                    "owner_organization_id": None,
                    "collection_method": "html_page",
                    "rights_notes": lead["basis"],
                    "enabled": True,
                    "continuously_collectible": False,
                    "review_state": "machine_validated",
                    "verification_method": "official_event_page",
                }
            )
            continue
        if lead["kind"] in {"essay", "talk"}:
            allowed = {"blog", "newsletter", "personal_website", "video", "youtube", "conference_talk", "testimony", "interview", "lab_page"}
            add(
                source_record(
                    person_id=f"person:{lead['person_slug']}",
                    source_type=lead["source_type"] if lead["source_type"] in allowed else "blog",
                    name=lead["name"],
                    canonical_url=canonicalize_url(lead["url"]),
                    platform=lead.get("platform") or lead.get("source_type") or "blog",
                    collection_method="html_page",
                    enabled=True,
                    verification_method="owned_page_byline",
                    rights_notes=lead["basis"],
                )
            )
            continue
        if lead["kind"] == "show_feed":
            add(
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
                add(
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
        add(
            source_record(
                person_id=f"person:{owner}",
                source_type=lead["source_type"],
                name=lead["name"],
                canonical_url=canonicalize_url(lead["url"]),
                platform=lead["source_type"],
                collection_method="rss_feed",
                enabled=True,
                verification_method="owned_feed_author",
                rights_notes=lead["basis"],
            )
        )
    if additions or len(existing) != len(load_jsonl(directory / "sources.jsonl")):
        _write_jsonl(directory / "sources.jsonl", existing + additions)


def _unique_sources(rows: list[dict]) -> list[dict]:
    kept = []
    ids: set[str] = set()
    urls: set[str] = set()
    for row in rows:
        url = canonicalize_url(row["canonical_url"])
        if row["id"] in ids or url in urls:
            continue
        ids.add(row["id"])
        urls.add(url)
        kept.append(row)
    return kept


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
