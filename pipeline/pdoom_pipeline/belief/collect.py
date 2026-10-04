"""Collect owned writing and verified show appearances for people already in the cohort."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

from urllib.parse import urlparse

from pdoom_pipeline.belief.appearances import evidence_for_person, guest_from_title, speaker_turns
from pdoom_pipeline.belief.changes import view_change_candidates
from pdoom_pipeline.belief.pages import (
    article_text,
    host_of,
    opening_byline,
    page_authors,
    page_language,
    page_title,
    parse_published,
    robots_allows,
    title_byline,
)
from pdoom_pipeline.collectors.rss import RssCollector
from pdoom_pipeline.enrich.html_page import strip_markup
from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.extract.statements import EXTRACTOR_VERSION, SPEAKER_GAP, extract_statements
from pdoom_pipeline.fetch import USER_AGENT
from pdoom_pipeline.hashing import content_hash
from pdoom_pipeline.identity.names import name_key, same_person_name
from pdoom_pipeline.ingest.participants import mentioned
from pdoom_pipeline.urls import canonicalize_url, hostname_is_blocked

MAX_STATEMENTS = 12
MAX_TRANSCRIPT_BYTES = 800_000
ESSAY_TEXT_CHARS = 80_000


def collect_beliefs(*, people: list[dict], leads: list[dict], fetch_bytes, observed_at: str, priority_slugs: set[str]) -> dict:
    by_slug = {person["slug"]: person for person in people}
    observations = []
    statements = []
    runs = []
    source_leads = []
    seen_items = set()
    robots_cache: dict[str, str | None] = {}
    ordered = sorted(leads, key=lambda row: {"essay": 0, "talk": 1, "owned_feed": 2, "author_feed": 3, "show_feed": 4, "lead": 5}.get(row["kind"], 9))
    for lead in ordered:
        kind = lead["kind"]
        if kind == "lead":
            source_leads.append(_lead_row(lead, lead.get("reason_not_admitted") or "not_yet_collected", bool(lead.get("retryable", True))))
            continue
        if kind in {"essay", "talk"}:
            _collect_page(lead, by_slug, fetch_bytes, observed_at, observations, statements, runs, seen_items, robots_cache, source_leads)
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
                failed = dict(lead)
                failed["url"] = url
                source_leads.append(_lead_row(failed, exc.error_class, exc.retryable))
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
                failed = dict(lead)
                failed["url"] = url
                source_leads.append(_lead_row(failed, exc.error_class, exc.retryable))
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
                evidence = _evidence_text(
                    item,
                    fetch_bytes,
                    runs,
                    use_body=bool(lead.get("use_body")),
                    robots_cache=robots_cache,
                )
                text = evidence["text"]
                item["locators"] = evidence["locators"]
                item["participants"] = _with_primary(_feed_participants(item), evidence["participants"])
                found = _statements_for_item(item, text)
                if lead.get("require_statement") and not found:
                    continue
                seen_items.add(key)
                new_on_page += 1
                item["evidence_body"] = text
                observations.append(item)
                statements.extend(found)
            if page > 1 and new_on_page == 0:
                break
    _assign_local_ids(statements)
    relationships = view_change_candidates(statements)
    _mark_duplicates(statements)
    return {
        "observations": observations,
        "statements": statements,
        "relationships": relationships,
        "runs": runs,
        "source_leads": source_leads,
        "extractor_version": EXTRACTOR_VERSION,
    }


def _collect_page(lead, by_slug, fetch_bytes, observed_at, observations, statements, runs, seen_items, robots_cache, source_leads) -> None:
    kind = lead.get("kind") or "essay"
    person = by_slug.get(lead.get("person_slug"))
    if person is None:
        runs.append({"status": "failure", "kind": kind, "url": lead.get("url"), "error_class": "attribution_unresolved"})
        source_leads.append(_lead_row(lead, "attribution_unresolved", False))
        return
    fetch_url = lead.get("fetch_url") or lead["url"]
    payload = _fetch_if_allowed(fetch_bytes, fetch_url, robots_cache, runs, kind)
    if payload is None:
        if not any(row.get("url") == fetch_url and row.get("status") == "failure" for row in runs):
            source_leads.append(_lead_row(lead, "robots_unavailable", True))
        else:
            failure = next(row for row in reversed(runs) if row.get("url") == fetch_url and row.get("status") == "failure")
            source_leads.append(_lead_row(lead, failure.get("error_class") or "blocked_by_policy", failure.get("error_class") == "robots_unavailable"))
        return
    raw = payload.decode("utf-8", errors="replace")
    text = article_text(raw, max_chars=200_000 if kind == "talk" else ESSAY_TEXT_CHARS)
    marker = lead.get("cut_before")
    if marker and marker in text:
        text = text[: text.index(marker)]
    if not _page_attributed(lead, person, raw):
        runs.append({"status": "failure", "kind": kind, "url": lead["url"], "error_class": "attribution_unresolved"})
        source_leads.append(_lead_row(lead, "attribution_unresolved", False))
        return
    try:
        canonical = canonicalize_url(lead["url"])
    except ValueError:
        runs.append({"status": "failure", "kind": kind, "url": lead["url"], "error_class": "invalid_content"})
        source_leads.append(_lead_row(lead, "invalid_content", False))
        return
    if canonical in seen_items:
        return
    seen_items.add(canonical)
    title = page_title(raw) if "<html" in raw[:2000].lower() else None
    talk = kind == "talk"
    evidence = _page_evidence(lead, person, text)
    published = parse_published(raw)
    item = {
        "person_id": f"person:{person['slug']}",
        "person_slug": person["slug"],
        "display_name": person["display_name"],
        "role": "speaker" if talk else "author",
        "ownership": "appearance" if talk else "owned",
        "show_slug": lead.get("show_slug"),
        "show_name": lead.get("name"),
        "source_type": lead.get("source_type") or ("video" if talk else "blog"),
        "feed_url": canonical,
        "canonical_url": canonical,
        "title": (title or lead.get("name") or "")[:300] or None,
        "published_at": published["utc"],
        "published_timezone": published["timezone"],
        "published_unzoned": published["unzoned"],
        "language": page_language(raw),
        "observed_at": observed_at,
        "upstream_id": canonical[:300],
        "platform": lead.get("platform") or ("video" if talk else "blog"),
        "collector": "html-page",
        "collector_version": "html-page-0.1.0",
        "collection_method": "html_page",
        "content_hash": content_hash({"url": canonical, "text": text}),
        "summary": text[:500],
        "transcript_url": lead.get("transcript_url"),
        "attribution_method": evidence["attribution"],
        "locators": evidence["locators"],
        "participants": evidence["participants"],
    }
    item["evidence_body"] = evidence["text"]
    observations.append(item)
    statements.extend(_statements_for_item(item, evidence["text"]))
    runs.append({"status": "success", "kind": kind, "url": canonical, "person_id": item["person_id"]})


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


def _page_attributed(lead: dict, person: dict, raw: str) -> bool:
    """Essays need authorship. A curated single-speaker talk is that person's appearance."""
    if lead.get("kind") == "talk" and lead.get("single_speaker"):
        return True
    return _essay_attributed(lead, person, raw)


def _essay_attributed(lead: dict, person: dict, raw: str) -> bool:
    """Author metadata, a title byline, or an exact title. A name only in the body is not authorship."""
    authors = page_authors(raw)
    title = page_title(raw) if "<html" in (raw or "")[:2000].lower() else None
    if authors:
        return any(_author_matches(lead, person, author) for author in authors)
    if title and same_person_name(title, person["display_name"]):
        return True
    byline = title_byline(title)
    if byline and _author_matches(lead, person, byline):
        return True
    chrome = " ".join(part for part in [title or "", lead.get("name") or ""] if part)
    if _alias_or_handle(lead, person, chrome):
        return True
    body_byline = opening_byline(raw)
    if body_byline and _alias_or_handle(lead, person, body_byline):
        return True
    return _host_names_person(lead, person)


def _author_matches(lead: dict, person: dict, name: str) -> bool:
    if same_person_name(name, person["display_name"]):
        return True
    return _alias_or_handle(lead, person, name)


def _alias_or_handle(lead: dict, person: dict, text: str) -> bool:
    if person.get("name_distinctiveness") != "high" or not text:
        return False
    alias = lead.get("byline_alias") or ""
    if alias and mentioned(text, alias):
        family = name_key(person["display_name"])[-1] if name_key(person["display_name"]) else ""
        alias_tokens = name_key(alias)
        if len(alias_tokens) >= 2 and len(family) > 3 and family in alias_tokens:
            return True
    handle = lead.get("byline_handle") or ""
    if handle and handle.lower() in text.lower():
        compact = "".join(char for char in handle.lower() if char.isalnum())
        tokens = [token for token in name_key(person["display_name"]) if len(token) > 2]
        if tokens and all(token in compact for token in tokens):
            return True
    return False


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
    """An owned feed item with no author field must name the person in the title, not the body."""
    return mentioned(strip_markup(observation.title or ""), display_name)


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


def _empty_evidence() -> dict:
    return {"text": "", "locators": [], "participants": [], "attribution": None}


def _fetch_if_allowed(fetch_bytes, url: str, robots_cache: dict, runs: list[dict], kind: str) -> bytes | None:
    """Same robots and blocked-host checks for a page and for an explicit transcript URL."""
    host = host_of(url)
    if host and hostname_is_blocked(host):
        runs.append({"status": "failure", "kind": kind, "url": url, "error_class": "blocked_by_policy"})
        return None
    robots = _robots_text(fetch_bytes, url, robots_cache, runs)
    if robots is None:
        return None
    path = urlparse(url).path or "/"
    if not robots_allows(robots, path, user_agent=USER_AGENT):
        runs.append({"status": "failure", "kind": kind, "url": url, "error_class": "blocked_by_policy"})
        return None
    try:
        return fetch_bytes(url)
    except CollectorFailure as exc:
        runs.append({"status": "failure", "kind": kind, "url": url, "error_class": exc.error_class})
        return None


def _evidence_text(item: dict, fetch_bytes, runs: list[dict], use_body: bool = False, robots_cache: dict | None = None) -> dict:
    if item["ownership"] == "owned":
        if use_body and item.get("article_text"):
            return {"text": article_text(item["article_text"], max_chars=ESSAY_TEXT_CHARS), "locators": [], "participants": [], "attribution": "metadata"}
        return {"text": strip_markup(item.get("summary") or ""), "locators": [], "participants": [], "attribution": "metadata"}
    url = item.get("transcript_url")
    if not url and item.get("canonical_url") and item.get("role") == "guest":
        url = item["canonical_url"]
    if not url:
        return _empty_evidence()
    cache = robots_cache if robots_cache is not None else {}
    payload = _fetch_if_allowed(fetch_bytes, url, cache, runs, "transcript")
    if payload is None:
        for row in reversed(runs):
            if row.get("url") == url and row.get("status") == "failure":
                row["person_id"] = item["person_id"]
                break
        return _empty_evidence()
    if len(payload) > MAX_TRANSCRIPT_BYTES:
        runs.append({"status": "failure", "kind": "transcript", "url": url, "error_class": "content_too_large", "person_id": item["person_id"]})
        return _empty_evidence()
    text = article_text(payload.decode("utf-8", errors="replace"), max_chars=200_000)
    evidence = evidence_for_person(text, item["display_name"], SPEAKER_GAP)
    if not evidence["text"]:
        runs.append({"status": "failure", "kind": "transcript", "url": url, "error_class": "speaker_labels_absent", "person_id": item["person_id"]})
        return _empty_evidence()
    runs.append({"status": "success", "kind": "transcript", "url": url, "person_id": item["person_id"]})
    evidence["text"] = evidence["text"][:200_000]
    evidence["attribution"] = "transcript_label"
    return evidence


def _page_evidence(lead: dict, person: dict, text: str) -> dict:
    if lead.get("kind") != "talk":
        return {
            "text": text,
            "attribution": "byline",
            "locators": [],
            "participants": [
                {
                    "name": person["display_name"],
                    "role": "author",
                    "attribution_method": "byline",
                    "attribution_detail": "page_byline",
                }
            ],
        }
    evidence = evidence_for_person(text, person["display_name"], SPEAKER_GAP)
    if evidence["text"]:
        primary = {
            "name": person["display_name"],
            "role": "speaker",
            "attribution_method": "transcript_label",
            "attribution_detail": "speaker_label",
        }
        return {
            "text": evidence["text"],
            "attribution": "transcript_label",
            "locators": evidence["locators"],
            "participants": _with_primary([primary], evidence["participants"]),
        }
    if lead.get("single_speaker") and not speaker_turns(text):
        return {
            "text": text,
            "attribution": "byline",
            "locators": [],
            "participants": [
                {
                    "name": person["display_name"],
                    "role": "speaker",
                    "attribution_method": "byline",
                    "attribution_detail": "single_speaker_page",
                }
            ],
        }
    return {"text": "", "attribution": "byline", "locators": [], "participants": []}


def _feed_participants(item: dict) -> list[dict]:
    role = item.get("role") or "speaker"
    guest = role == "guest"
    return [
        {
            "name": item["display_name"],
            "role": role,
            "attribution_method": "transcript_label" if guest else "metadata",
            "attribution_detail": "episode_title" if guest else "feed_author_field",
        }
    ]


def _with_primary(primary: list[dict], extra: list[dict] | None) -> list[dict]:
    rows = list(primary)
    seen = {(row.get("role"), row.get("name")) for row in rows}
    for row in extra or []:
        key = (row.get("role"), row.get("name"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _lead_row(lead: dict, reason: str, retryable: bool) -> dict:
    return {
        "person_slug": lead.get("person_slug"),
        "candidate_url": lead.get("url"),
        "candidate_source_type": lead.get("candidate_source_type") or lead.get("source_type") or lead.get("kind"),
        "discovery_provenance": lead.get("discovery_provenance") or lead.get("basis") or "collection_attempt",
        "reason_not_admitted": reason,
        "retryable": bool(retryable),
    }


def _statements_for_item(item: dict, text: str) -> list[dict]:
    if not text:
        return []
    found = extract_statements(text, person_id=item["person_id"])
    kept = []
    digests = set()
    kept_by_signature: dict[tuple, dict] = {}
    locators = item.get("locators") or []
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
        if digest in digests or (statement.get("statement_type") == "explicit_numeric" and signature in kept_by_signature):
            if statement.get("statement_type") == "explicit_numeric" and signature in kept_by_signature:
                flags = set(kept_by_signature[signature].get("review_flags") or [])
                flags.add("possible_duplicate")
                kept_by_signature[signature]["review_flags"] = sorted(flags)
            continue
        digests.add(digest)
        if statement.get("statement_type") == "explicit_numeric":
            kept_by_signature[signature] = statement
        flags = list(statement.get("review_flags") or [])
        if item.get("role") == "guest" and item.get("attribution_method") not in {None, "transcript_label"}:
            flags.append("speaker_attribution_weak")
        if item.get("ownership") == "appearance" and item.get("source_type") == "press":
            flags.append("secondary_source_only")
        statement["review_flags"] = sorted(set(flags))
        _apply_locator(statement, locators)
        recommended = statement.get("review_state")
        if recommended == "human_verified":
            continue
        attribution = "transcript_label" if item.get("role") == "guest" else item.get("attribution_method") or "metadata"
        detail = (
            "speaker_label"
            if item.get("role") == "guest" or item.get("attribution_method") == "transcript_label"
            else ("page_byline" if item.get("attribution_method") == "byline" else "feed_author_field")
        )
        update = {
            "person_slug": item["person_slug"],
            "source_url": item["canonical_url"],
            "published_at": item.get("published_at"),
            "published_timezone": item.get("published_timezone"),
            "observed_at": item.get("observed_at"),
            "role": item.get("role"),
            "ownership": item.get("ownership"),
            "attribution_method": attribution,
            "attribution_detail": detail,
            "verified": False,
            "source_type": item.get("source_type"),
            "platform": item.get("platform"),
            "language": item.get("language"),
            "participants": item.get("participants") or [],
            "recommended_review_state": recommended if recommended in {"unreviewed", "needs_review", "machine_validated"} else "unreviewed",
        }
        if item.get("content_hash"):
            update["content_hash"] = item["content_hash"]
            update["content_version"] = item.get("content_version") or 1
        statement.update(update)
        kept.append(statement)
        if len(kept) >= MAX_STATEMENTS:
            break
    return kept


def _apply_locator(statement: dict, locators: list[dict]) -> None:
    """Use the turn that contains the span. A missing alignment stays unknown."""
    start = statement.get("start_char")
    locator = None
    if isinstance(start, int):
        for item in locators:
            begin = item.get("start_char")
            end = item.get("end_char")
            if isinstance(begin, int) and isinstance(end, int) and begin <= start < end:
                locator = item
                break
    if locator is None:
        statement["start_ms"] = None
        statement["evidence_locator"] = None
        return
    statement["start_ms"] = locator.get("start_ms")
    statement["evidence_locator"] = {
        "start_char": locator.get("start_char"),
        "end_char": locator.get("end_char"),
        "start_ms": locator.get("start_ms"),
        "speaker": locator.get("speaker"),
        "turn_index": locator.get("turn_index"),
    }
    preceding = locator.get("preceding") or {}
    prefix = (preceding.get("text") or "").strip()
    if prefix and preceding.get("role") in {"host", "interviewer"}:
        context = statement.get("context_text") or ""
        statement["context_text"] = f"{prefix} {context}".strip()[:800]
        flags = set(statement.get("review_flags") or [])
        flags.add("host_question_in_context")
        statement["review_flags"] = sorted(flags)


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
        if statement.get("unit") == "year" and statement.get("value_numeric") is not None:
            year = str(int(statement["value_numeric"]))
            if year not in evidence:
                return False
        if statement.get("unit") == "year" and statement.get("value_type") == "range":
            if str(int(statement["value_min"])) not in evidence or str(int(statement["value_max"])) not in evidence:
                return False
        if statement.get("unit") in {"years_ahead", "decade"} and statement.get("horizon_text") and statement["horizon_text"] not in evidence:
            return False
        if statement.get("value_text") and statement["value_text"] not in evidence and statement.get("unit") != "year":
            return False
    if statement.get("statement_type") == "explicit_qualitative" and statement.get("value_numeric") is not None:
        return False
    return True


def _repeated_people(statements: list[dict]) -> int:
    counts: Counter = Counter()
    for row in statements:
        if row.get("statement_type") != "explicit_numeric" or not row.get("question_key"):
            continue
        counts[(row.get("person_slug"), row.get("question_key"))] += 1
    return len({person for (person, _key), count in counts.items() if count >= 2})


def _mark_duplicates(statements: list[dict]) -> None:
    seen: dict[tuple, dict] = {}
    for statement in statements:
        signature = (
            statement.get("person_id"),
            statement.get("question_key"),
            statement.get("value_numeric"),
            statement.get("value_min"),
            statement.get("value_max"),
            statement.get("horizon_text"),
            statement.get("evidence_text"),
        )
        earlier = seen.get(signature)
        if earlier is not None:
            flags = set(earlier.get("review_flags") or [])
            flags.add("possible_duplicate")
            earlier["review_flags"] = sorted(flags)
            continue
        seen[signature] = statement


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
        "multi_sentence": sum(1 for row in statements if "multi_sentence_evidence" in (row.get("review_flags") or [])),
        "video_items": sum(1 for row in observations if row.get("platform") == "video" or row.get("source_type") in {"video", "conference_talk", "testimony"}),
        "source_leads": len(result.get("source_leads") or []),
        "people_with_repeated_forecasts": _repeated_people(statements),
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
