"""Collect owned writing and verified show appearances for people already in the cohort."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

from urllib.parse import urlparse

from pdoom_pipeline.belief.appearances import guest_from_title, speaker_turns, turns_for_person
from pdoom_pipeline.belief.changes import view_change_candidates
from pdoom_pipeline.belief.pages import article_text, host_of, page_title, published_time, robots_allows
from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.enrich.html_page import strip_markup
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.extract.statements import EXTRACTOR_VERSION, extract_statements
from pdoom_pipeline.hashing import content_hash
from pdoom_pipeline.identity.names import name_key, same_person_name
from pdoom_pipeline.ingest.participants import mentioned
from pdoom_pipeline.urls import canonicalize_url

MAX_STATEMENTS = 12
MAX_TRANSCRIPT_BYTES = 800_000
ESSAY_TEXT_CHARS = 80_000


def collect_beliefs(*, people: list[dict], leads: list[dict], fetch_bytes, observed_at: str, priority_slugs: set[str]) -> dict:
    by_slug = {person["slug"]: person for person in people}
    observations = []
    statements = []
    runs = []
    seen_items = set()
    robots_cache: dict[str, str | None] = {}
    ordered = sorted(leads, key=lambda row: {"essay": 0, "owned_feed": 1, "author_feed": 2, "show_feed": 3}.get(row["kind"], 9))
    for lead in ordered:
        kind = lead["kind"]
        if kind == "essay":
            _collect_essay(lead, by_slug, fetch_bytes, observed_at, observations, statements, runs, seen_items, robots_cache)
            continue
        if kind == "owned_feed" and lead["person_slug"] not in priority_slugs:
            continue
        pages = int(lead.get("pages") or 1)
        for page in range(1, pages + 1):
            url = lead["url"] if page == 1 else _paged(lead["url"], page)
            try:
                payload = fetch_bytes(url)
            except CollectorFailure as exc:
                runs.append({"status": "failure", "kind": kind, "url": url, "error_class": exc.error_class})
                break
            try:
                parsed = RssCollector().parse(
                    payload,
                    source_identity=lead.get("show_slug") or lead.get("person_slug") or "feed",
                    feed_url=url,
                    observed_at=observed_at,
                    max_bytes=6_000_000,
                    max_items=400,
                )
            except CollectorFailure as exc:
                runs.append({"status": "failure", "kind": kind, "url": url, "error_class": exc.error_class})
                break
            if not parsed:
                break
            runs.append({"status": "success", "kind": kind, "url": url, "items": len(parsed)})
            new_on_page = 0
            for observation in parsed:
                item = _item_from_feed(lead, observation, by_slug, people)
                if item is None:
                    continue
                key = item["canonical_url"]
                if key in seen_items:
                    continue
                seen_items.add(key)
                new_on_page += 1
                text, start_ms = _evidence_text(item, fetch_bytes, runs, use_body=bool(lead.get("use_body")))
                item["evidence_body"] = text
                observations.append(item)
                statements.extend(_statements_for_item(item, text, start_ms))
            if page > 1 and new_on_page == 0:
                break
    _assign_local_ids(statements)
    relationships = view_change_candidates(statements)
    return {
        "observations": observations,
        "statements": statements,
        "relationships": relationships,
        "runs": runs,
        "extractor_version": EXTRACTOR_VERSION,
    }


def _collect_essay(lead, by_slug, fetch_bytes, observed_at, observations, statements, runs, seen_items, robots_cache) -> None:
    person = by_slug.get(lead.get("person_slug"))
    if person is None:
        runs.append({"status": "failure", "kind": "essay", "url": lead.get("url"), "error_class": "attribution_unresolved"})
        return
    fetch_url = lead.get("fetch_url") or lead["url"]
    robots = _robots_text(fetch_bytes, fetch_url, robots_cache, runs)
    if robots is None:
        return
    path = urlparse(fetch_url).path or "/"
    if not robots_allows(robots, path):
        runs.append({"status": "failure", "kind": "essay", "url": fetch_url, "error_class": "blocked_by_policy"})
        return
    try:
        payload = fetch_bytes(fetch_url)
    except CollectorFailure as exc:
        runs.append({"status": "failure", "kind": "essay", "url": fetch_url, "error_class": exc.error_class})
        return
    raw = payload.decode("utf-8", errors="replace")
    text = article_text(raw, max_chars=ESSAY_TEXT_CHARS)
    marker = lead.get("cut_before")
    if marker and marker in text:
        text = text[: text.index(marker)]
    title_for_byline = page_title(raw) or ""
    if not _essay_attributed(lead, person, text + "\n" + title_for_byline):
        runs.append({"status": "failure", "kind": "essay", "url": lead["url"], "error_class": "attribution_unresolved"})
        return
    try:
        canonical = canonicalize_url(lead["url"])
    except ValueError:
        runs.append({"status": "failure", "kind": "essay", "url": lead["url"], "error_class": "invalid_content"})
        return
    if canonical in seen_items:
        return
    seen_items.add(canonical)
    title = page_title(raw) if "<html" in raw[:2000].lower() else None
    item = {
        "person_id": f"person:{person['slug']}",
        "person_slug": person["slug"],
        "display_name": person["display_name"],
        "role": "author",
        "ownership": "owned",
        "show_slug": None,
        "show_name": lead.get("name"),
        "source_type": lead.get("source_type") or "blog",
        "feed_url": canonical,
        "canonical_url": canonical,
        "title": (title or lead.get("name") or "")[:300] or None,
        "published_at": published_time(raw),
        "observed_at": observed_at,
        "upstream_id": canonical[:300],
        "platform": "blog",
        "collector": "html-page",
        "collector_version": "html-page-0.1.0",
        "collection_method": "html_page",
        "content_hash": content_hash({"url": canonical, "text": text}),
        "summary": text[:500],
        "transcript_url": None,
        "attribution_method": "byline",
    }
    item["evidence_body"] = text
    observations.append(item)
    statements.extend(_statements_for_item(item, text, None))
    runs.append({"status": "success", "kind": "essay", "url": canonical, "person_id": item["person_id"]})


def _robots_text(fetch_bytes, url: str, cache: dict, runs: list[dict]) -> str | None:
    host = host_of(url)
    if not host:
        return None
    if host in cache:
        return cache[host]
    robots_url = f"https://{host}/robots.txt"
    try:
        payload = fetch_bytes(robots_url)
    except CollectorFailure as exc:
        if exc.error_class == "not_found":
            cache[host] = ""
            return ""
        runs.append({"status": "failure", "kind": "robots", "url": robots_url, "error_class": exc.error_class})
        cache[host] = None
        return None
    text = payload.decode("utf-8", errors="replace")
    cache[host] = text
    return text


def _essay_attributed(lead: dict, person: dict, text: str) -> bool:
    if mentioned(text, person["display_name"]):
        return True
    handle = lead.get("byline_handle") or ""
    if handle and person.get("name_distinctiveness") == "high" and handle.lower() in text.lower():
        compact = "".join(char for char in handle.lower() if char.isalnum())
        tokens = [token for token in name_key(person["display_name"]) if len(token) > 2]
        if tokens and all(token in compact for token in tokens):
            return True
    return _host_names_person(lead, person)


def _host_names_person(lead: dict, person: dict) -> bool:
    owner_host = (lead.get("owner_host") or "").lower()
    if not owner_host or person.get("name_distinctiveness") != "high":
        return False
    host = host_of(lead["url"])
    if host != owner_host and not host.endswith("." + owner_host):
        return False
    tokens = name_key(person["display_name"])
    if len(tokens) < 2:
        return False
    family = tokens[-1]
    given = tokens[0]
    return len(family) > 3 and family in host and given in host


def _item_from_feed(lead: dict, observation, by_slug: dict, people: list[dict]) -> dict | None:
    title = observation.title or ""
    author = observation.author_candidates[0].name if observation.author_candidates else ""
    if lead["kind"] == "owned_feed":
        person = by_slug.get(lead["person_slug"])
        if person is None:
            return None
        if author and not same_person_name(author, person["display_name"]):
            return None
        if not author and not _feed_names_person(observation, person["display_name"]):
            return None
        role = "author"
        ownership = "owned"
    elif lead["kind"] == "author_feed":
        person = _person_by_author(author, people)
        if person is None:
            return None
        role = "author"
        ownership = "owned"
    elif lead["kind"] == "show_feed":
        person = guest_from_title(title, people)
        if person is None:
            return None
        role = "guest"
        ownership = "appearance"
    else:
        return None
    return {
        "person_id": f"person:{person['slug']}",
        "person_slug": person["slug"],
        "display_name": person["display_name"],
        "role": role,
        "ownership": ownership,
        "show_slug": lead.get("show_slug"),
        "show_name": lead.get("name"),
        "source_type": lead["source_type"],
        "feed_url": lead["url"],
        "canonical_url": observation.canonical_url,
        "title": title[:300] or None,
        "published_at": observation.published_at,
        "observed_at": observation.observed_at,
        "upstream_id": (observation.upstream_id or observation.canonical_url)[:300],
        "platform": "podcast" if lead["kind"] == "show_feed" else observation.platform,
        "collector": observation.collector,
        "collector_version": observation.collector_version,
        "collection_method": observation.collection_method,
        "content_hash": observation.content_hash,
        "summary": " ".join(segment.text for segment in observation.segments)[:2000],
        "article_text": ((observation.metadata or {}).get("upstream_version") or "")[:50_000],
        "transcript_url": (observation.metadata or {}).get("transcript_url"),
    }


def _feed_names_person(observation, display_name: str) -> bool:
    blob = " ".join([observation.title or "", *[segment.text for segment in observation.segments]])
    return mentioned(strip_markup(blob), display_name)


def _person_by_author(author: str, people: list[dict]) -> dict | None:
    if not author:
        return None
    hits = [
        person
        for person in people
        if person.get("name_distinctiveness") == "high" and same_person_name(author, person["display_name"])
    ]
    if len(hits) != 1:
        return None
    return hits[0]


def _evidence_text(item: dict, fetch_bytes, runs: list[dict], use_body: bool = False) -> tuple[str, int | None]:
    if item["ownership"] == "owned":
        if use_body and item.get("article_text"):
            return article_text(item["article_text"], max_chars=ESSAY_TEXT_CHARS), None
        return strip_markup(item.get("summary") or ""), None
    url = item.get("transcript_url")
    if not url:
        return "", None
    try:
        payload = fetch_bytes(url)
    except CollectorFailure as exc:
        runs.append({"status": "failure", "kind": "transcript", "url": url, "error_class": exc.error_class, "person_id": item["person_id"]})
        return "", None
    if len(payload) > MAX_TRANSCRIPT_BYTES:
        runs.append({"status": "failure", "kind": "transcript", "url": url, "error_class": "content_too_large", "person_id": item["person_id"]})
        return "", None
    text = payload.decode("utf-8", errors="replace")
    turns = turns_for_person(speaker_turns(text), item["display_name"])
    if not turns:
        return "", None
    runs.append({"status": "success", "kind": "transcript", "url": url, "person_id": item["person_id"], "turns": len(turns)})
    body = "\n".join(turn["text"] for turn in turns)
    start_ms = next((turn["start_ms"] for turn in turns if turn.get("start_ms") is not None), None)
    return body[:200_000], start_ms


def _statements_for_item(item: dict, text: str, start_ms: int | None) -> list[dict]:
    if not text:
        return []
    found = extract_statements(text, person_id=item["person_id"])
    kept = []
    seen = set()
    for statement in _prefer(found):
        if not _passes_gate(statement):
            continue
        signature = (
            statement.get("question_key"),
            statement.get("value_numeric"),
            statement.get("value_min"),
            statement.get("value_max"),
            statement.get("horizon_text"),
            statement.get("statement_type"),
        )
        digest = hashlib.sha256(
            f"{item['person_id']}|{signature}|{statement['evidence_text'][:180]}".encode("utf-8")
        ).hexdigest()
        if digest in seen or (statement.get("statement_type") == "explicit_numeric" and signature in seen):
            continue
        seen.add(digest)
        if statement.get("statement_type") == "explicit_numeric":
            seen.add(signature)
        statement.update(
            {
                "person_slug": item["person_slug"],
                "source_url": item["canonical_url"],
                "published_at": item["published_at"],
                "observed_at": item["observed_at"],
                "role": item["role"],
                "ownership": item["ownership"],
                "start_ms": start_ms if statement.get("start_ms") is None else statement.get("start_ms"),
                "attribution_method": "transcript_label" if item["role"] == "guest" else item.get("attribution_method") or "metadata",
                "attribution_detail": "speaker_label" if item["role"] == "guest" else ("page_byline" if item.get("attribution_method") == "byline" else "feed_author_field"),
                "verified": False,
            }
        )
        kept.append(statement)
        if len(kept) >= MAX_STATEMENTS:
            break
    return kept


def _prefer(statements: list[dict]) -> list[dict]:
    rank = {"probability": 0, "timeline": 1, "quantity": 2, "qualitative": 3}
    return sorted(statements, key=lambda row: rank.get(row.get("forecast_kind"), 9))


def _passes_gate(statement: dict) -> bool:
    evidence = statement.get("evidence_text") or ""
    if statement.get("review_state") == "human_verified":
        return False
    if statement.get("statement_type") == "explicit_numeric":
        if statement.get("unit") == "probability":
            if statement.get("value_text") and statement["value_text"] not in evidence:
                return False
            if statement.get("value_numeric") is None and (statement.get("value_min") is None or statement.get("value_max") is None):
                return False
        if statement.get("unit") == "year":
            year = str(int(statement["value_numeric"]))
            if year not in evidence:
                return False
        if statement.get("value_text") and statement["value_text"] not in evidence and statement.get("unit") != "year":
            return False
    if statement.get("statement_type") == "explicit_qualitative" and statement.get("value_numeric") is not None:
        return False
    return True


def _assign_local_ids(statements: list[dict]) -> None:
    for index, statement in enumerate(statements):
        statement["local_id"] = f"st{index:05d}"


def _paged(url: str, page: int) -> str:
    joiner = "&" if "?" in url else "?"
    return f"{url}{joiner}paged={page}"


def summarize(result: dict) -> dict:
    statements = result["statements"]
    observations = result["observations"]
    return {
        "source_items": len(observations),
        "statements": len(statements),
        "by_type": dict(Counter(row["statement_type"] for row in statements)),
        "by_kind": dict(Counter(row.get("forecast_kind") for row in statements)),
        "by_question": dict(Counter(row.get("question_key") for row in statements if row.get("question_key"))),
        "by_topic": dict(Counter(row.get("topic_slug") for row in statements)),
        "people_with_items": len({row["person_slug"] for row in observations}),
        "people_with_statements": len({row["person_slug"] for row in statements}),
        "explicit_numeric": sum(1 for row in statements if row["statement_type"] == "explicit_numeric"),
        "explicit_qualitative": sum(1 for row in statements if row["statement_type"] == "explicit_qualitative"),
        "model_inferred": sum(1 for row in statements if row["statement_type"] == "model_inferred_signal"),
        "missing_horizon": sum(1 for row in statements if row["statement_type"] == "explicit_numeric" and not row.get("horizon_text")),
        "missing_definition": sum(1 for row in statements if row["statement_type"] == "explicit_numeric" and not row.get("definition_text")),
        "podcast_people": len({row["person_slug"] for row in observations if row.get("platform") == "podcast" or row.get("role") == "guest"}),
        "owned_people": len({row["person_slug"] for row in observations if row.get("ownership") == "owned"}),
        "relationships": len(result["relationships"]),
        "runs": len(result["runs"]),
        "failures": dict(Counter(row.get("error_class") for row in result["runs"] if row.get("status") != "success")),
        "failure_urls": [
            {"error_class": row.get("error_class"), "kind": row.get("kind"), "url": row.get("url")}
            for row in result["runs"]
            if row.get("status") != "success"
        ],
    }


def dumps_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
