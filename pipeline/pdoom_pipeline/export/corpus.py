"""Turn belief-corpus observations into the canonical live import document."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pdoom_pipeline.belief.taxonomy import QUESTION_KEYS, TOPICS
from pdoom_pipeline.export.canonical import export_seed
from pdoom_pipeline.export.identity import evidence_material, evidence_slug, source_item_slug, statement_material, statement_slug

CONFIDENCE = {"high": 0.8, "medium": 0.62, "low": 0.35}


def export_corpus(result: dict, *, seed_dir: Path | None = None, generated_at: str) -> dict:
    document = export_seed(seed_dir)
    document["generated_at"] = generated_at
    source_slugs = {row["slug"] for row in document["sources"]}
    item_slugs: dict[str, str] = {}
    statement_slugs: dict[str, str] = {}
    items = []
    participants = []
    evidence = []
    statements = []
    forecasts = []
    extraction_runs = []
    seen_items: set[str] = set()
    for observation in result["observations"]:
        source_slug = _ensure_source(document, source_slugs, observation)
        current_hash = _hex_hash(observation.get("content_hash"), observation["canonical_url"])
        versions = observation.get("retained_versions") or [
            {
                "content_hash": current_hash,
                "content_version": observation.get("content_version") or 1,
                "observed_at": observation.get("observed_at"),
                "published_at": observation.get("published_at"),
                "title": observation.get("title"),
            }
        ]
        current_slug = None
        for version in versions:
            version_hash = _hex_hash(version.get("content_hash"), observation["canonical_url"])
            version_number = int(version.get("content_version") or 1)
            item_slug = source_item_slug(observation["canonical_url"], version_hash, version_number)
            if item_slug in seen_items:
                if version_hash == current_hash:
                    current_slug = item_slug
                continue
            seen_items.add(item_slug)
            is_current = version_hash == current_hash
            if is_current:
                current_slug = item_slug
            items.append(
                {
                    "slug": item_slug,
                    "source_slug": source_slug,
                    "upstream_id": (observation.get("upstream_id") or observation["canonical_url"])[:300],
                    "logical_key": observation["canonical_url"][:300],
                    "canonical_url": observation["canonical_url"],
                    "title": version.get("title") if version.get("title") is not None else observation.get("title"),
                    "published_at": version.get("published_at") if "published_at" in version else observation.get("published_at"),
                    "published_timezone": None,
                    "observed_at": version.get("observed_at") or observation["observed_at"],
                    "updated_at_source": None,
                    "language": "en",
                    "content_hash": version_hash,
                    "content_hash_input": None,
                    "content_version": version_number,
                    "content_reference": observation["canonical_url"][:300],
                    "metadata": {
                        "ownership": observation["ownership"],
                        "feed_url": observation["feed_url"],
                        "role": observation["role"],
                    },
                    "collection_status": "collected",
                    "availability": "available",
                    "is_current": is_current,
                    "ingestion_run_slug": "belief-corpus-2026-09",
                }
            )
        if current_slug is None:
            current_slug = source_item_slug(observation["canonical_url"], current_hash, int(observation.get("content_version") or 1))
        item_slugs[observation["canonical_url"]] = current_slug
        participants.append(
            {
                "source_item_slug": current_slug,
                "person_slug": observation["person_slug"],
                "organization_slug": None,
                "role": observation["role"],
                "attribution_method": "transcript_label" if observation["role"] == "guest" else observation.get("attribution_method") or "metadata",
                "attribution_detail": "episode_title_and_speaker_label" if observation["role"] == "guest" else ("page_byline" if observation.get("attribution_method") == "byline" else "feed_author_or_owned_feed"),
                "confidence_level": "high" if observation["ownership"] == "owned" else "medium",
            }
        )
    by_item_evidence: dict[str, list[str]] = {}
    sequence_for = _stable_sequences(result["statements"])
    slug_for = _stable_statement_slugs(result["statements"])
    seen_evidence: set[str] = set()
    for statement in result["statements"]:
        if statement.get("review_state") == "human_verified":
            raise ValueError("machine export cannot mark human_verified")
        item_slug = item_slugs.get(statement["source_url"])
        if not item_slug:
            continue
        evidence_id = evidence_slug(statement)
        statement_id = slug_for[id(statement)]
        statement_slugs[statement["local_id"]] = statement_id
        if evidence_id not in seen_evidence:
            seen_evidence.add(evidence_id)
            evidence.append(
                {
                    "slug": evidence_id,
                    "source_item_slug": item_slug,
                    "segment_kind": "transcript" if statement.get("role") == "guest" else "text",
                    "sequence": sequence_for[id(statement)],
                    "start_char": statement.get("start_char"),
                    "end_char": statement.get("end_char"),
                    "start_ms": statement.get("start_ms"),
                    "end_ms": None,
                    "text": statement["evidence_text"][:2000],
                    "context_text": (statement.get("context_text") or "")[:800] or None,
                }
            )
        if evidence_id not in by_item_evidence.get(item_slug, []):
            by_item_evidence.setdefault(item_slug, []).append(evidence_id)
        topic = statement.get("topic_slug") or "ai-risk-qualitative"
        statements.append(
            {
                "slug": statement_id,
                "person_slug": statement["person_slug"],
                "source_item_slug": item_slug,
                "statement_type": statement["statement_type"],
                "normalized_text": statement["normalized_text"][:600],
                "event_time": statement.get("published_at"),
                "evidence_slug": evidence_id,
                "extractor_version": statement["extractor_version"],
                "confidence": CONFIDENCE.get(statement.get("confidence"), 0.35),
                "review_state": statement["review_state"],
                "extraction_run_slug": _slug("run", item_slug),
                "topic_slugs": [topic],
                "topic_method": "question-key-map-2026-09",
                "topic_confidence": 0.55 if statement["statement_type"] == "explicit_numeric" else 0.35,
            }
        )
        if statement.get("forecast_kind") and statement.get("question_key"):
            forecasts.append(_forecast(statement, statement_id))
    for item_slug, evidence_slugs in by_item_evidence.items():
        blob = "|".join(evidence_slugs).encode("utf-8")
        extraction_runs.append(
            {
                "slug": _slug("run", item_slug),
                "source_item_slug": item_slug,
                "extractor_name": "rule-extract",
                "extractor_version": result.get("extractor_version") or "rule-extract-0.2.0",
                "model_provider": None,
                "model_name": None,
                "prompt_contract_version": "none",
                "started_at": (result.get("refresh") or {}).get("extracted_at") or generated_at,
                "completed_at": (result.get("refresh") or {}).get("extracted_at") or generated_at,
                "status": "succeeded",
                "input_hash": hashlib.sha256(blob).hexdigest(),
                "output_hash": hashlib.sha256(("out|" + blob.decode()).encode("utf-8")).hexdigest(),
            }
        )
    relationships = []
    for row in result.get("relationships") or []:
        if row.get("review_state") == "human_verified":
            raise ValueError("machine export cannot mark human_verified")
        later = statement_slugs.get(row.get("later_local_id"))
        earlier = statement_slugs.get(row.get("earlier_local_id"))
        if not later or not earlier or later == earlier:
            continue
        relationships.append(
            {
                "from_statement_slug": later,
                "to_statement_slug": earlier,
                "relationship_type": row["relationship_type"],
                "method": row["method"],
                "confidence": row["confidence"],
                "review_state": row["review_state"],
            }
        )
    used_topics = {slug for statement in statements for slug in statement["topic_slugs"]}
    document["source_items"] = items
    document["participants"] = participants
    document["evidence_segments"] = evidence
    document["topics"] = [
        {"slug": slug, "name": slug, "definition": definition, "parent_slug": None, "version": "2026.09.0"}
        for slug, definition in sorted(TOPICS.items())
        if slug in used_topics
    ]
    document["statements"] = statements
    document["forecasts"] = forecasts
    document["relationships"] = relationships
    document["extraction_runs"] = extraction_runs
    refresh = result.get("refresh") or {}
    counts = _run_counts(result["observations"], refresh)
    document["ingestion_runs"].append(
        {
            "slug": "belief-corpus-2026-09",
            "collector": "belief-corpus",
            "source_slug": None,
            "started_at": refresh.get("started_at") or generated_at,
            "completed_at": refresh.get("completed_at") or generated_at,
            "status": counts["status"],
            "cursor_before": refresh.get("cursor_before"),
            "cursor_after": refresh.get("cursor_after"),
            "observed_count": counts["observed_count"],
            "new_count": counts["new_count"],
            "changed_count": counts["changed_count"],
            "unchanged_count": counts["unchanged_count"],
            "skipped_count": counts["skipped_count"],
            "failed_count": counts["failed_count"],
            "error_summary": counts["error_summary"],
        }
    )
    _apply_source_checks(document, refresh.get("checks") or {})
    extra = " Belief excerpts are unreviewed candidates, not a census or a consensus."
    document["notice"] = (document["notice"] + extra)[:1200]
    _ = QUESTION_KEYS
    return document


def _ensure_source(document: dict, seen: set[str], observation: dict) -> str:
    by_url = {row["canonical_url"]: row["slug"] for row in document["sources"]}
    if observation["feed_url"] in by_url:
        return by_url[observation["feed_url"]]
    if observation["ownership"] == "appearance" and observation.get("platform") == "podcast":
        slug = observation["show_slug"]
        if slug not in seen:
            document["sources"].append(
                {
                    "slug": slug,
                    "source_type": "podcast",
                    "name": (observation.get("show_name") or slug)[:200],
                    "canonical_url": observation["feed_url"],
                    "platform": "podcast",
                    "owner_person_slug": None,
                    "owner_organization_slug": None,
                    "collection_method": "rss",
                    "collection_adapter": "rss_feed",
                    "rights_notes": "Official public show RSS. The tracked person is a guest, not the owner.",
                    "enabled": True,
                    "review_state": "machine_validated",
                    "last_checked_at": observation["observed_at"],
                    "last_success_at": observation["observed_at"],
                }
            )
            seen.add(slug)
        return slug
    slug = _slug("src", observation["person_slug"] + observation["feed_url"])
    if slug not in seen:
        source_type = observation["source_type"]
        if source_type not in {"blog", "newsletter", "podcast", "personal_site", "lab_post", "video", "conference_talk", "testimony", "interview"}:
            source_type = "blog"
        document["sources"].append(
            {
                "slug": slug,
                "source_type": source_type,
                "name": f"{observation['display_name']} {source_type}"[:200],
                "canonical_url": observation["feed_url"],
                "platform": observation.get("platform") or source_type,
                "owner_person_slug": observation["person_slug"],
                "owner_organization_slug": None,
                "collection_method": "rss",
                "collection_adapter": "rss_feed",
                "rights_notes": "Owned public feed. Excerpts only.",
                "enabled": True,
                "review_state": "machine_validated",
                "last_checked_at": observation["observed_at"],
                "last_success_at": observation["observed_at"],
            }
        )
        seen.add(slug)
    return slug


def _forecast(statement: dict, statement_slug: str) -> dict:
    year = None
    if statement.get("unit") == "year" and statement.get("value_numeric") is not None:
        year = int(statement["value_numeric"])
    return {
        "statement_slug": statement_slug,
        "forecast_kind": statement["forecast_kind"],
        "question_key": statement["question_key"],
        "question_text": (statement.get("question_text") or statement["normalized_text"])[:600],
        "definition_text": statement.get("definition_text"),
        "condition_text": statement.get("condition_text"),
        "target_date_start": None,
        "target_date_end": f"{year}-12-31" if year else None,
        "horizon_text": statement.get("horizon_text"),
        "value_type": statement.get("value_type") or "none",
        "value_text": statement.get("value_text"),
        "value_numeric": statement.get("value_numeric"),
        "value_min": statement.get("value_min"),
        "value_max": statement.get("value_max"),
        "unit": statement.get("unit"),
        "distribution": None,
        "resolution_criteria": None,
        "review_state": statement["review_state"],
    }


def _stable_statement_slugs(statements: list[dict]) -> dict[int, str]:
    bases = [(statement, statement_slug(statement)) for statement in statements]
    counts: dict[str, int] = {}
    for _, base in bases:
        counts[base] = counts.get(base, 0) + 1
    slugs: dict[int, str] = {}
    for statement, base in bases:
        if counts[base] == 1:
            slugs[id(statement)] = base
        else:
            slugs[id(statement)] = _slug("st", statement_material(statement) + "\n" + evidence_material(statement))
    return slugs


def _stable_sequences(statements: list[dict]) -> dict[int, int]:
    grouped: dict[str, list[dict]] = {}
    for statement in statements:
        grouped.setdefault(statement.get("source_url") or "", []).append(statement)
    sequences: dict[int, int] = {}
    for group in grouped.values():
        ordered = sorted(group, key=lambda row: (_sort_offset(row), evidence_slug(row), statement_slug(row)))
        seen: dict[str, int] = {}
        next_sequence = 1
        for statement in ordered:
            slug = evidence_slug(statement)
            if slug not in seen:
                seen[slug] = next_sequence
                next_sequence += 1
            sequences[id(statement)] = seen[slug]
    return sequences


def _sort_offset(statement: dict) -> int:
    if statement.get("start_char") is not None:
        return int(statement["start_char"])
    if statement.get("start_ms") is not None:
        return int(statement["start_ms"])
    return 0


def _run_counts(observations: list[dict], refresh: dict) -> dict:
    statuses = [row.get("ingest_status") for row in observations]
    if refresh.get("new_count") is not None:
        new_count = int(refresh["new_count"])
        changed_count = int(refresh.get("changed_count") or 0)
        unchanged_count = int(refresh.get("unchanged_count") or 0)
    elif any(statuses):
        new_count = sum(1 for status in statuses if status == "new")
        changed_count = sum(1 for status in statuses if status in {"changed", "version_changed"})
        unchanged_count = sum(1 for status in statuses if status == "unchanged")
    else:
        new_count = len(observations)
        changed_count = 0
        unchanged_count = 0
    failed_count = int(refresh.get("failed_count") or 0)
    skipped_count = int(refresh.get("skipped_count") or 0)
    status = refresh.get("status")
    if status not in {"succeeded", "partial", "failed"}:
        if failed_count and (new_count or changed_count or unchanged_count):
            status = "partial"
        elif failed_count:
            status = "failed"
        else:
            status = "succeeded"
    error_summary = refresh.get("error_summary")
    if error_summary is not None:
        error_summary = str(error_summary)[:400] or None
    return {
        "status": status,
        "observed_count": new_count + changed_count + unchanged_count,
        "new_count": new_count,
        "changed_count": changed_count,
        "unchanged_count": unchanged_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "error_summary": error_summary,
    }


def _apply_source_checks(document: dict, checks: dict) -> None:
    for source in document["sources"]:
        row = checks.get(source["canonical_url"])
        if not row:
            continue
        if row.get("last_checked_at"):
            source["last_checked_at"] = row["last_checked_at"]
        if row.get("last_success_at"):
            source["last_success_at"] = row["last_success_at"]


def _slug(prefix: str, raw: str) -> str:
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _hex_hash(value: str | None, fallback: str) -> str:
    text = value or ""
    if text.startswith("sha256:"):
        text = text.split(":", 1)[1]
    if len(text) == 64 and all(char in "0123456789abcdef" for char in text):
        return text
    return hashlib.sha256(fallback.encode("utf-8")).hexdigest()
