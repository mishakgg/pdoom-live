"""Collect ForumMagnum and Bluesky sources, plus a small RSS backfill.

This command is not the recurring belief runner. It does not write
canonical-live.json and it does not mark records human_verified.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from pdoom_pipeline.collectors.bluesky import BlueskyCollector
from pdoom_pipeline.collectors.forum_magnum import ForumMagnumCollector
from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.extract.statements import extract_statements
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.identity.names import same_person_name
from pdoom_pipeline.seed.additions_2026_10 import PRESS_EXCERPTS, VERIFIED_AT
from pdoom_pipeline.seed.build import SEED_DIR, load_jsonl
from pdoom_pipeline.seed.cohort_2026_10 import TARGET_DIR

ROOT = Path(__file__).resolve().parents[3]
COLLECTION = ROOT / "data" / "collections" / "cohort-v2026-10"
LEGACY_OBSERVATIONS = ROOT / "data" / "collections" / "cohort-v2026-09" / "source_observations.jsonl"
TAG_RE = re.compile(r"<[^>]+>")


def press_observations(observed_at: str = VERIFIED_AT) -> list[dict]:
    rows = []
    for excerpt in PRESS_EXCERPTS:
        rows.append(
            {
                "source_identity": f"src:person:{excerpt['person_slug']}:press:hyperclova-think",
                "platform": "press",
                "upstream_id": excerpt["canonical_url"],
                "canonical_url": excerpt["canonical_url"],
                "observed_at": observed_at,
                "published_at": excerpt["published_at"],
                "title": "NAVER HyperCLOVA X THINK announcement",
                "text": excerpt["text"],
                "role": excerpt["role"],
                "person_id": f"person:{excerpt['person_slug']}",
                "person_slug": excerpt["person_slug"],
                "language": excerpt["language"],
                "translation": excerpt["translation"],
                "translation_note": excerpt["translation_note"],
                "claim_level": excerpt["claim_level"],
                "sole_author": True,
                "collection_method": "reference_only",
                "collector": "reviewed_excerpt",
                "collector_version": "reviewed-excerpt-0.1.0",
                "review_state": "needs_review",
            }
        )
    return rows


def collect_configured(
    *,
    seed_dir: Path,
    legacy_observations: Path | None,
    live: bool,
    observed_at: str,
    forum_pages: int,
    bluesky_pages: int,
    rss_items: int,
    sleep_seconds: float = 0.0,
) -> dict:
    if COLLECTION.name == "canonical-live.json":
        raise RuntimeError("refusing to treat the canonical file as a collection directory")
    people = {row["id"]: row for row in load_jsonl(seed_dir / "people.jsonl")}
    sources = load_jsonl(seed_dir / "sources.jsonl")
    already = _legacy_people(legacy_observations)
    forum_fetcher = _fetcher()
    bluesky_fetcher = _fetcher()
    rss_fetcher = _fetcher(rss=True)
    requests = {"count": 0}
    _count_gets(forum_fetcher, requests)
    _count_gets(bluesky_fetcher, requests)
    _count_gets(rss_fetcher, requests)
    forum = ForumMagnumCollector(fetcher=forum_fetcher)
    bluesky = BlueskyCollector(fetcher=bluesky_fetcher)
    rss = RssCollector(fetcher=rss_fetcher)
    observations: list[dict] = []
    runs: list[dict] = []
    failures: list[dict] = []
    started = time.perf_counter()
    observations.extend(press_observations(observed_at))

    if live:
        for source in sources:
            if not source.get("enabled") or source.get("runner_wired"):
                continue
            owner = source.get("owner_person_id")
            person = people.get(owner or "")
            if source.get("collection_method") == "forum_magnum_api" and person:
                _pause(sleep_seconds)
                try:
                    batch = forum.collect_user_posts(
                        source_identity=source["id"],
                        site=source["site"],
                        user_id=source["user_id"],
                        expected_slug=source["expected_slug"],
                        observed_at=observed_at,
                        page_size=5,
                        max_pages=forum_pages,
                    )
                    observations.extend(_from_collector(batch, person=person, source=source))
                    runs.append(_success(source, len(batch)))
                except CollectorFailure as exc:
                    runs.append(_failure(source, exc))
                    failures.append(_failure_example(source, exc))
            elif source.get("collection_method") == "bluesky_api" and person:
                _pause(sleep_seconds)
                try:
                    batch = bluesky.collect_author_feed(
                        source_identity=source["id"],
                        actor=source["actor"],
                        observed_at=observed_at,
                        limit=15,
                        max_pages=bluesky_pages,
                    )
                    observations.extend(_from_collector(batch, person=person, source=source))
                    runs.append(_success(source, len(batch)))
                except CollectorFailure as exc:
                    runs.append(_failure(source, exc))
                    failures.append(_failure_example(source, exc))

        for source in sources:
            if source.get("collection_method") != "rss_feed" or not source.get("enabled"):
                continue
            owner = source.get("owner_person_id")
            if not owner or owner in already:
                continue
            person = people.get(owner)
            if not person:
                continue
            _pause(sleep_seconds)
            try:
                batch = rss.collect(source_identity=source["id"], feed_url=source["canonical_url"], observed_at=observed_at)
            except CollectorFailure as exc:
                runs.append(_failure(source, exc))
                failures.append(_failure_example(source, exc))
                continue
            kept = []
            for observation in batch[:rss_items]:
                if observation.segments:
                    observation.segments[0].text = _plain(observation.segments[0].text)
                    observation.metadata["html_stripped"] = True
                    observation.finalize_hash()
                assigned = _assign_rss(observation, person)
                if assigned is None:
                    failures.append(
                        {
                            "person_slug": person["slug"],
                            "url": observation.canonical_url,
                            "error_class": "attribution_unresolved",
                            "detail": "RSS author field did not match the registered owner.",
                        }
                    )
                    continue
                kept.append(assigned)
            observations.extend(kept)
            runs.append(_success(source, len(kept)))

    candidates = _candidates(observations)
    elapsed = round(time.perf_counter() - started, 3)
    return {
        "observations": observations,
        "candidates": candidates,
        "runs": runs,
        "failures": failures,
        "runtime_seconds": elapsed,
        "request_estimate": requests["count"],
        "live": live,
        "cost_note": "No paid API was called. Cost is request count and runtime only.",
    }


def write_collection(result: dict, directory: Path | None = None) -> Path:
    target = directory or COLLECTION
    if target.name == "canonical-live.json" or (target / "canonical-live.json").name == "canonical-live.json" and False:
        raise RuntimeError("refusing canonical output")
    target.mkdir(parents=True, exist_ok=True)
    forbidden = target / "canonical-live.json"
    if forbidden.exists():
        raise RuntimeError("refusing to write into a directory that already holds canonical-live.json")
    _write_jsonl(target / "source_observations.jsonl", result["observations"])
    _write_jsonl(target / "candidate_statements.jsonl", result["candidates"])
    _write_jsonl(target / "collector_runs.jsonl", result["runs"])
    _write_jsonl(target / "attribution_failures.jsonl", result["failures"])
    (target / "live_checks.json").write_text(
        json.dumps(
            {
                "live": result["live"],
                "runtime_seconds": result["runtime_seconds"],
                "request_estimate": result["request_estimate"],
                "cost_note": result["cost_note"],
                "observations": len(result["observations"]),
                "candidates": len(result["candidates"]),
                "failures": len(result["failures"]),
                "separate_from_fixture_tests": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def _from_collector(batch, *, person: dict, source: dict) -> list[dict]:
    rows = []
    for observation in batch:
        sole = observation.metadata.get("sole_author", True)
        data = observation.to_dict()
        data["person_id"] = person["id"] if sole else None
        data["person_slug"] = person["slug"] if sole else None
        data["role"] = "author" if sole else None
        data["text"] = observation.segments[0].text if observation.segments else ""
        data["language"] = observation.metadata.get("language")
        data["translation"] = observation.metadata.get("translation")
        data["sole_author"] = sole
        data["shared_authorship"] = not sole
        data["review_state"] = "needs_review"
        data["source_owner_person_id"] = person["id"]
        if not sole:
            data["attribution_note"] = "Coauthored post. Not stored as one person's statement."
        rows.append(data)
    return rows


def _assign_rss(observation, person: dict) -> dict | None:
    names = [candidate.name for candidate in observation.author_candidates if candidate.name]
    accepted = [person["display_name"], *(person.get("name_variants") or [])]
    if names and not any(any(same_person_name(name, candidate) for candidate in accepted) for name in names):
        return None
    if not names:
        observation.author_candidates = []
        observation.metadata["attribution_method"] = "owned_feed_empty_author"
    data = observation.to_dict()
    data["person_id"] = person["id"]
    data["person_slug"] = person["slug"]
    data["role"] = "author"
    data["text"] = observation.segments[0].text if observation.segments else ""
    data["language"] = None
    data["sole_author"] = True
    data["review_state"] = "needs_review"
    return data


def _candidates(observations: list[dict]) -> list[dict]:
    rows = []
    for observation in observations:
        if not observation.get("sole_author") or not observation.get("person_id"):
            continue
        if observation.get("claim_level") == "institution":
            continue
        text = observation.get("text") or ""
        for statement in extract_statements(text, person_id=observation["person_id"]):
            if statement.get("review_state") == "human_verified":
                statement["review_state"] = "needs_review"
            statement["source_url"] = observation.get("canonical_url")
            statement["evidence_text"] = statement.get("evidence_text") or statement.get("normalized_text") or text
            statement["language"] = observation.get("language")
            statement["translation"] = observation.get("translation")
            statement["person_slug"] = observation.get("person_slug")
            statement["claim_level"] = observation.get("claim_level") or "personal"
            statement["automated"] = True
            rows.append(statement)
    return rows


def _legacy_people(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    return {json.loads(line).get("person_id") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _count_gets(fetcher, requests: dict) -> None:
    original = fetcher.get

    def counted(url, headers=None, **kwargs):
        requests["count"] += 1
        return original(url, headers=headers, **kwargs)

    fetcher.get = counted


def _fetcher(rss: bool = False):
    types = ("application/json", "text/plain", "application/octet-stream")
    if rss:
        types = ("application/rss+xml", "application/atom+xml", "application/xml", "text/xml", "text/plain", "application/octet-stream")
    return SafeFetcher(allowed_content_types=types, max_bytes=1_000_000, timeout=20, max_attempts=2)


def _plain(text: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", text or "")).split())


def _pause(seconds: float) -> None:
    if seconds:
        time.sleep(seconds)


def _success(source: dict, count: int) -> dict:
    return {"status": "success", "source_id": source["id"], "url": source["canonical_url"], "person_id": source.get("owner_person_id"), "items": count}


def _failure(source: dict, exc: CollectorFailure) -> dict:
    return {
        "status": "failure",
        "source_id": source["id"],
        "url": source["canonical_url"],
        "person_id": source.get("owner_person_id"),
        "error_class": exc.error_class,
    }


def _failure_example(source: dict, exc: CollectorFailure) -> dict:
    return {
        "person_slug": (source.get("owner_person_id") or "").split(":")[-1],
        "url": source.get("canonical_url"),
        "error_class": exc.error_class,
        "detail": str(exc),
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect unwired ForumMagnum and Bluesky adapters into a staging directory.")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--seed", default=str(TARGET_DIR))
    parser.add_argument("--out", default=str(COLLECTION))
    parser.add_argument("--forum-pages", type=int, default=2)
    parser.add_argument("--bluesky-pages", type=int, default=2)
    parser.add_argument("--rss-items", type=int, default=8)
    args = parser.parse_args()
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = collect_configured(
        seed_dir=Path(args.seed),
        legacy_observations=LEGACY_OBSERVATIONS,
        live=args.live,
        observed_at=observed_at,
        forum_pages=args.forum_pages,
        bluesky_pages=args.bluesky_pages,
        rss_items=args.rss_items,
        sleep_seconds=0.25 if args.live else 0,
    )
    directory = write_collection(result, Path(args.out))
    print(
        json.dumps(
            {
                "directory": str(directory),
                "live": result["live"],
                "observations": len(result["observations"]),
                "candidates": len(result["candidates"]),
                "runtime_seconds": result["runtime_seconds"],
                "request_estimate": result["request_estimate"],
                "canonical_live_written": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
