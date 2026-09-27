"""Turn belief-corpus observations into the canonical live import document."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pdoom_pipeline.belief.taxonomy import QUESTION_KEYS, TOPICS
from pdoom_pipeline.export.canonical import export_seed

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
    for observation in result["observations"]:
        source_slug = _ensure_source(document, source_slugs, observation)
        item_slug = _slug("item", observation["canonical_url"])
        item_slugs[observation["canonical_url"]] = item_slug
        content_hash = _hex_hash(observation.get("content_hash"), observation["canonical_url"])
        items.append(
            {
                "slug": item_slug,
                "source_slug": source_slug,
                "upstream_id": (observation.get("upstream_id") or observation["canonical_url"])[:300],
                "logical_key": observation["canonical_url"][:300],
                "canonical_url": observation["canonical_url"],
                "title": observation.get("title"),
                "published_at": observation.get("published_at"),
                "published_timezone": None,
                "observed_at": observation["observed_at"],
                "updated_at_source": None,
                "language": "en",
                "content_hash": content_hash,
                "content_hash_input": None,
                "content_version": 1,
                "content_reference": observation["canonical_url"][:300],
                "metadata": {
                    "ownership": observation["ownership"],
                    "feed_url": observation["feed_url"],
                    "role": observation["role"],
                },
                "collection_status": "collected",
                "availability": "available",
                "is_current": True,
                "ingestion_run_slug": "belief-corpus-2026-09",
            }
        )
        participants.append(
            {
                "source_item_slug": item_slug,
                "person_slug": observation["person_slug"],
                "organization_slug": None,
                "role": observation["role"],
                "attribution_method": "transcript_label" if observation["role"] == "guest" else observation.get("attribution_method") or "metadata",
                "attribution_detail": "episode_title_and_speaker_label" if observation["role"] == "guest" else ("page_byline" if observation.get("attribution_method") == "byline" else "feed_author_or_owned_feed"),
                "confidence_level": "high" if observation["ownership"] == "owned" else "medium",
            }
        )
    by_item_evidence: dict[str, list[str]] = {}
    for statement in result["statements"]:
        if statement.get("review_state") == "human_verified":
            raise ValueError("machine export cannot mark human_verified")
        item_slug = item_slugs.get(statement["source_url"])
        if not item_slug:
            continue
        evidence_slug = _slug("ev", statement["local_id"] + statement["evidence_text"])
        statement_slug = _slug("st", statement["local_id"] + statement["source_url"])
        statement_slugs[statement["local_id"]] = statement_slug
        evidence.append(
            {
                "slug": evidence_slug,
                "source_item_slug": item_slug,
                "segment_kind": "transcript" if statement.get("role") == "guest" else "text",
                "sequence": len(by_item_evidence.get(item_slug, [])) + 1,
                "start_char": statement.get("start_char"),
                "end_char": statement.get("end_char"),
                "start_ms": statement.get("start_ms"),
                "end_ms": None,
                "text": statement["evidence_text"][:2000],
                "context_text": (statement.get("context_text") or "")[:800] or None,
            }
        )
        by_item_evidence.setdefault(item_slug, []).append(evidence_slug)
        topic = statement.get("topic_slug") or "ai-risk-qualitative"
        statements.append(
            {
                "slug": statement_slug,
                "person_slug": statement["person_slug"],
                "source_item_slug": item_slug,
                "statement_type": statement["statement_type"],
                "normalized_text": statement["normalized_text"][:600],
                "event_time": statement.get("published_at"),
                "evidence_slug": evidence_slug,
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
            forecasts.append(_forecast(statement, statement_slug))
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
                "started_at": generated_at,
                "completed_at": generated_at,
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
    document["ingestion_runs"].append(
        {
            "slug": "belief-corpus-2026-09",
            "collector": "belief-corpus",
            "source_slug": None,
            "started_at": generated_at,
            "completed_at": generated_at,
            "status": "succeeded",
            "cursor_before": None,
            "cursor_after": None,
            "observed_count": len(items),
            "new_count": len(items),
            "changed_count": 0,
            "error_summary": None,
        }
    )
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
