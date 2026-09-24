"""Live OpenAlex lookup. Network failures stay failures; they never become guessed IDs."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.identity.resolve import choose_openalex_author, dedupe_openalex_ids
from pdoom_pipeline.seed.build import all_people

API = "https://api.openalex.org/authors"
SELECT = "id,display_name,orcid,works_count,cited_by_count,last_known_institutions,affiliations,ids"


def resolve_live(fetcher: SafeFetcher | None = None, people: list[dict] | None = None) -> dict:
    client = fetcher or SafeFetcher(
        allowed_content_types=("application/json",),
        max_bytes=2_000_000,
        max_attempts=3,
        sleep=time.sleep,
    )
    decisions = {}
    errors = []
    for person in people or all_people():
        person_id = f"person:{person['slug']}"
        query = urlencode({"search": person["display_name"], "per-page": 25, "select": SELECT, "mailto": "collector@pdoom.live"})
        try:
            result = client.get(f"{API}?{query}")
            payload = json.loads(result.body.decode("utf-8"))
            results = payload.get("results") or []
            decisions[person_id] = choose_openalex_author(person, results)
        except Exception as exc:
            error_class = getattr(exc, "error_class", "collector_bug")
            decisions[person_id] = {"status": "not_found", "error_class": error_class, "message": str(exc)}
            errors.append({"person_id": person_id, "error_class": error_class, "message": str(exc)})
        time.sleep(0.12)
    cleaned, conflicts = dedupe_openalex_ids(decisions)
    return {
        "resolved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "people": cleaned,
        "conflicts": conflicts,
        "errors": errors,
    }
