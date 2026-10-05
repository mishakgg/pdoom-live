"""Wikidata entity metadata for one item.

Reads one QID from the public EntityData endpoint:

https://www.wikidata.org/wiki/Special:EntityData/QID.json

The stored record is the QID, the English label, and the English
description when that description is shorter than 300 characters.
Wikipedia article text, sitelink pages, and claim biographies are not
stored. Aliases and a second entity are not returned as another person.
The record is not an instruction to attach this entity to a tracked
person.

This module is not registered with the collectors package or the belief
runner. Payload text is data, not instructions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher

COLLECTOR_VERSION = "wikidata-metadata-0.1.0"
ENTITY_DATA_ORIGIN = "https://www.wikidata.org"
# One EntityData document. Large enough for a person item, small enough
# that an unbounded biography dump is refused.
MAX_RESPONSE_BYTES = 1_000_000
MAX_LABEL_CHARS = 250
MAX_DESCRIPTION_CHARS = 300
_QID = re.compile(r"^Q[1-9][0-9]{0,15}$")
_ARTICLE_KEYS = ("extract", "extract_html", "wikitext")


@dataclass(frozen=True)
class WikidataEntity:
    """English label metadata for one Wikidata item."""

    qid: str
    label: str
    description: str | None = None

    def as_record(self) -> dict[str, str]:
        if self.description is not None and len(self.description) >= MAX_DESCRIPTION_CHARS:
            raise CollectorFailure("collector_bug", "description is not short enough to store")
        record = {"qid": self.qid, "label": self.label}
        if self.description is not None:
            record["description"] = self.description
        record["source_url"] = entity_data_url(self.qid)
        return record


class WikidataCollector:
    """Retrieve one item's label metadata. The default fetcher makes one attempt."""

    collector = "wikidata"
    platform = "wikidata"
    collector_version = COLLECTOR_VERSION

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher(
            allowed_content_types=("application/json",),
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=10.0,
            max_redirects=0,
            max_attempts=1,
        )

    def retrieve(self, qid: str) -> WikidataEntity:
        url = entity_data_url(qid)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        if requested != [url]:
            raise CollectorFailure("blocked_by_policy", "wikidata lookup does not follow another page")
        for hop in requested:
            if not _is_entity_data_url(hop):
                raise CollectorFailure("blocked_by_policy", "refusing a non-entitydata url")
        entity = parse_entity(result.body)
        if entity.qid != _validated_qid(qid):
            raise CollectorFailure("invalid_content", "wikidata qid mismatch")
        return entity


def entity_data_url(qid: str) -> str:
    checked = _validated_qid(qid)
    return f"{ENTITY_DATA_ORIGIN}/wiki/Special:EntityData/{checked}.json"


def parse_entity(payload: bytes | str) -> WikidataEntity:
    """Read QID, English label, and a short English description. Performs no I/O."""
    body = _payload_bytes(payload)
    if body.lstrip().startswith((b"<", b"%PDF", b"\xef\xbb\xbf<")):
        raise CollectorFailure("blocked_by_policy", "wikipedia article text is not stored")
    try:
        data = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed wikidata payload: {exc}") from exc
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "wikidata payload is not an object")
    if any(key in data for key in _ARTICLE_KEYS):
        raise CollectorFailure("blocked_by_policy", "wikipedia article text is not stored")
    entities = data.get("entities")
    if not isinstance(entities, dict) or not entities:
        if "sitelinks" in data:
            raise CollectorFailure("blocked_by_policy", "sitelink pages are not stored")
        raise CollectorFailure("invalid_content", "wikidata payload has no entities")
    if len(entities) != 1:
        raise CollectorFailure("invalid_content", "wikidata payload must contain one entity")
    key, entity = next(iter(entities.items()))
    qid = _validated_qid(key) if isinstance(key, str) else ""
    if not qid:
        raise CollectorFailure("invalid_content", "wikidata id must be a single QID")
    if not isinstance(entity, dict):
        raise CollectorFailure("invalid_content", "wikidata entity is not an object")
    if entity.get("missing") is not None:
        raise CollectorFailure("not_found", "wikidata entity is missing")
    if "redirects" in entity or entity.get("id") != qid:
        raise CollectorFailure("blocked_by_policy", "refusing a redirected wikidata entity")
    if entity.get("type") != "item":
        raise CollectorFailure("invalid_content", "wikidata entity is not an item")
    if any(key in entity for key in _ARTICLE_KEYS):
        raise CollectorFailure("blocked_by_policy", "wikipedia article text is not stored")
    # claims, sitelinks, and aliases are intentionally unread.
    return WikidataEntity(
        qid=qid,
        label=_label(entity.get("labels")),
        description=_description(entity.get("descriptions")),
    )


def _payload_bytes(payload: bytes | str) -> bytes:
    if isinstance(payload, str):
        body = payload.encode("utf-8")
    elif isinstance(payload, (bytes, bytearray)):
        body = bytes(payload)
    else:
        raise CollectorFailure("invalid_content", "wikidata payload must be json text")
    if len(body) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "wikidata entity payload exceeds limit")
    return body


def _validated_qid(value: str) -> str:
    text = (value or "").strip()
    lowered = text.lower()
    if "wikipedia.org" in lowered or "wikimedia.org" in lowered:
        raise CollectorFailure("blocked_by_policy", "wikipedia pages are not wikidata entity metadata")
    if not _QID.fullmatch(text):
        raise CollectorFailure("invalid_content", "wikidata id must be a single QID")
    return text


def _is_entity_data_url(url: str) -> bool:
    if not url.startswith(f"{ENTITY_DATA_ORIGIN}/wiki/Special:EntityData/"):
        return False
    if "wikipedia.org" in url.lower() or "sitelinks" in url.lower():
        return False
    qid = url.removeprefix(f"{ENTITY_DATA_ORIGIN}/wiki/Special:EntityData/").removesuffix(".json")
    return bool(_QID.fullmatch(qid)) and url.endswith(".json") and url.count("/") == 5


def _label(block: object) -> str:
    text = _english_text(block)
    if text is None:
        raise CollectorFailure("invalid_content", "wikidata english label is missing")
    if len(text) > MAX_LABEL_CHARS:
        raise CollectorFailure("content_too_large", "wikidata label exceeds limit")
    if _page_pointer(text):
        raise CollectorFailure("blocked_by_policy", "wikipedia pages are not entity labels")
    return text


def _description(block: object) -> str | None:
    text = _english_text(block)
    if text is None or len(text) >= MAX_DESCRIPTION_CHARS or _page_pointer(text):
        return None
    return text


def _english_text(block: object) -> str | None:
    if not isinstance(block, dict):
        return None
    entry = block.get("en")
    if not isinstance(entry, dict):
        return None
    if "language" in entry and entry.get("language") != "en":
        return None
    value = entry.get("value")
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized or any(ord(char) < 32 for char in normalized):
        return None
    return normalized


def _page_pointer(text: str) -> bool:
    lowered = text.lower()
    return "://" in text or "wikipedia.org" in lowered or "wikimedia.org" in lowered
