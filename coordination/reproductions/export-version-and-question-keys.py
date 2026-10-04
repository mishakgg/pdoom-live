"""Reproduce two main-branch contract gaps without a database.

Scenario inputs are local fixtures and the current export code.
The script prints one JSON object and exits 0 after measuring.
Callers record failures; this file does not change product behavior.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pdoom_pipeline.belief.taxonomy import QUESTION_KEYS
from pdoom_pipeline.export.corpus import export_corpus

ROOT = Path(__file__).resolve().parents[2]
URL = "https://example.com/coordination/same-source"
GENERATED = "2026-10-04T20:40:00Z"


def person_slug() -> str:
    line = (ROOT / "data/seed/cohort/v2026-09/people.jsonl").read_text(encoding="utf-8").splitlines()[0]
    return json.loads(line)["slug"]


def observation(content_hash: str, observed_at: str) -> dict:
    slug = person_slug()
    return {
        "canonical_url": URL,
        "content_hash": content_hash,
        "upstream_id": URL,
        "title": "Coordination fixture",
        "published_at": "2024-01-01T00:00:00Z",
        "observed_at": observed_at,
        "person_slug": slug,
        "display_name": "Coordination Fixture",
        "ownership": "owned",
        "feed_url": "https://example.com/coordination/feed",
        "role": "author",
        "source_type": "blog",
        "platform": "blog",
        "attribution_method": "byline",
    }


def statement(local_id: str, evidence: str) -> dict:
    return {
        "local_id": local_id,
        "source_url": URL,
        "person_slug": person_slug(),
        "role": "author",
        "evidence_text": evidence,
        "normalized_text": evidence,
        "statement_type": "explicit_numeric",
        "published_at": "2024-01-01T00:00:00Z",
        "extractor_version": "rule-extract-0.2.0",
        "confidence": "high",
        "review_state": "unreviewed",
        "topic_slug": "ai-extinction",
        "forecast_kind": "probability",
        "question_key": "extinction_unconditional",
        "question_text": "Probability of AI-caused human extinction.",
        "definition_text": None,
        "condition_text": None,
        "horizon_text": "by 2040",
        "value_type": "point",
        "value_text": "10%",
        "value_numeric": 0.1,
        "value_min": None,
        "value_max": None,
        "unit": "probability",
        "start_char": 0,
        "end_char": len(evidence),
        "start_ms": None,
        "context_text": evidence,
    }


def export_one(content_hash: str, observed_at: str, local_id: str, evidence: str) -> dict:
    return export_corpus(
        {
            "observations": [observation(content_hash, observed_at)],
            "statements": [statement(local_id, evidence)],
            "relationships": [],
            "extractor_version": "rule-extract-0.2.0",
        },
        generated_at=GENERATED,
    )


def curation_keys() -> list[str]:
    text = (ROOT / "packages/contracts/src/curation.ts").read_text(encoding="utf-8")
    block = text.split("export const QUESTION_TAXONOMY", 1)[1].split("] as const", 1)[0]
    return re.findall(r'key: "([^"]+)"', block)


def main() -> None:
    first_hash = hashlib.sha256(b"version-one").hexdigest()
    second_hash = hashlib.sha256(b"version-two").hexdigest()
    first = export_one(first_hash, "2026-09-01T00:00:00Z", "v1", "I think there is a 10% chance of extinction by 2040.")
    second = export_one(second_hash, "2026-10-01T00:00:00Z", "v2", "I now think there is a 20% chance of extinction by 2040.")
    both = export_corpus(
        {
            "observations": [
                observation(first_hash, "2026-09-01T00:00:00Z"),
                observation(second_hash, "2026-10-01T00:00:00Z"),
            ],
            "statements": [
                statement("v1", "I think there is a 10% chance of extinction by 2040."),
            ],
            "relationships": [],
        },
        generated_at=GENERATED,
    )
    first_item = first["source_items"][0]
    second_item = second["source_items"][0]
    product_keys = curation_keys()
    pipeline_keys = sorted(QUESTION_KEYS)
    report = {
        "base_sha": "d13c8ab9bc2d643e28b7f52daf1a4c15724e77d7",
        "same_url_separate_exports": {
            "slug_v1": first_item["slug"],
            "slug_v2": second_item["slug"],
            "same_slug": first_item["slug"] == second_item["slug"],
            "content_version_v1": first_item["content_version"],
            "content_version_v2": second_item["content_version"],
            "hash_v1": first_item["content_hash"],
            "hash_v2": second_item["content_hash"],
            "hashes_differ": first_item["content_hash"] != second_item["content_hash"],
            "is_current_v2": second_item["is_current"],
            "changed_count": second["ingestion_runs"][-1]["changed_count"],
        },
        "same_export_two_observations": {
            "item_count": len(both["source_items"]),
            "slugs": [item["slug"] for item in both["source_items"]],
            "duplicate_slugs": len({item["slug"] for item in both["source_items"]}) != len(both["source_items"]),
        },
        "question_keys": {
            "exported_question_key": first["forecasts"][0]["question_key"],
            "pipeline_key_count": len(pipeline_keys),
            "product_key_count": len(product_keys),
            "overlap": sorted(set(pipeline_keys) & set(product_keys)),
            "exported_key_in_product_taxonomy": first["forecasts"][0]["question_key"] in product_keys,
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
