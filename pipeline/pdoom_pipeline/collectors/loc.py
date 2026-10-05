"""Library of Congress public item metadata.

Reads one item from the public JSON API:

    https://www.loc.gov/item/{id}/?fo=json&at=item

``robots.txt`` disallows ``/search``, so this collector never calls that path.
``at=item`` asks for the bibliographic item. Images, PDFs, IIIF tiles, and
manifests are not requested. Related-item text is ignored.

A description longer than 400 characters is not stored in full. Rights is
``us_government_work`` only when a rights field says the item is a US
government work. Any other rights wording, including public domain or CC0,
stays ``unknown``. Contributor search links are not names and are not fetched.

This module is not wired into belief collection. ``runner_wired`` stays false.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse

from pdoom_pipeline.errors import CollectorFailure
from pdoom_pipeline.fetch import SafeFetcher
from pdoom_pipeline.urls import canonicalize_url

COLLECTOR_VERSION = "loc-metadata-0.1.0"
API_ORIGIN = "https://www.loc.gov"
ITEM_PATH = "/item"
UNKNOWN = "unknown"
US_GOVERNMENT_WORK = "us_government_work"
MAX_RESPONSE_BYTES = 200_000
MAX_DESCRIPTION_CHARS = 400
MAX_TITLE_CHARS = 2_000
MAX_CONTRIBUTORS = 200
MAX_NAME_CHARS = 300
RUNNER_WIRED = False

_ITEM_HOSTS = frozenset({"www.loc.gov"})
_ITEM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
_TAG = re.compile(r"(?is)<[^>]+>")
_MEDIA_SUFFIX = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp", ".jp2")
_RIGHTS_FIELDS = ("rights", "rights_advisory", "rights_information", "rights_and_access")
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


@dataclass(frozen=True)
class LocItem:
    """Metadata fields taken from one public loc.gov item."""

    id: str
    title: str
    date: str
    contributors: tuple[str, ...]
    canonical_url: str
    rights: str
    description: str | None = None
    description_truncated: bool = False

    def __post_init__(self) -> None:
        if self.rights not in {US_GOVERNMENT_WORK, UNKNOWN}:
            raise ValueError(f"rights must be {US_GOVERNMENT_WORK} or {UNKNOWN}")
        if self.description is not None and len(self.description) > MAX_DESCRIPTION_CHARS:
            raise ValueError("description exceeds 400 characters")

    def as_dict(self) -> dict[str, object]:
        record: dict[str, object] = {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "contributors": list(self.contributors),
            "canonical_url": self.canonical_url,
            "rights": self.rights,
        }
        if self.description is not None:
            record["description"] = self.description
        if self.description_truncated:
            record["description_truncated"] = True
        return record


class LocCollector:
    """Retrieve one public item. The default fetcher makes a single attempt."""

    collector = "loc"
    platform = "loc"
    collector_version = COLLECTOR_VERSION
    runner_wired = RUNNER_WIRED

    def __init__(self, fetcher: SafeFetcher | None = None):
        if fetcher is None:
            fetcher = SafeFetcher(
                allowed_content_types=("application/json",),
                max_bytes=MAX_RESPONSE_BYTES,
                timeout=10.0,
                max_redirects=0,
                max_attempts=1,
            )
            # loc.gov robots.txt asks for a five-second crawl delay.
            fetcher.host_interval = 5.0
        self.fetcher = fetcher

    def retrieve(self, item_id: str) -> LocItem:
        """Fetch one item's JSON metadata. Does not follow image or PDF links."""
        url = item_request_url(item_id)
        result = self.fetcher.get(url, headers={"Accept": "application/json"})
        requested = result.requested_urls or [result.url]
        for hop in requested:
            if not _is_metadata_url(hop):
                raise CollectorFailure("blocked_by_policy", "loc image and pdf downloads are not requested")
        if _looks_like_media(result.body):
            raise CollectorFailure("blocked_by_policy", "loc image and pdf bytes are not metadata")
        record = self.parse(result.body)
        if record.id != item_id.strip():
            raise CollectorFailure("invalid_content", "loc item id mismatch")
        return record

    def parse(self, payload: bytes) -> LocItem:
        """Parse one item JSON body. Performs no I/O."""
        return parse_loc_item(payload)


def item_request_url(item_id: str) -> str:
    """JSON URL for one item. The path is ``/item/{id}/``, never a file or search."""
    cleaned = _require_request_id(item_id)
    url = f"{API_ORIGIN}{ITEM_PATH}/{cleaned}/?fo=json&at=item"
    if not _is_metadata_url(url):
        raise CollectorFailure("blocked_by_policy", "loc image and pdf downloads are not requested")
    return url


def parse_loc_item(payload: bytes) -> LocItem:
    """Return one item, or fail when the payload is empty or not an item.

    A search result list is not an item. ``/search`` is disallowed by robots.txt.
    """
    if _looks_like_media(payload):
        raise CollectorFailure("blocked_by_policy", "loc image and pdf bytes are not metadata")
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CollectorFailure("content_too_large", "loc payload exceeds limit")
    if not payload.strip():
        raise CollectorFailure("invalid_content", "empty loc payload")
    try:
        data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollectorFailure("invalid_content", f"malformed loc payload: {exc}") from exc
    item = _item_record(data)
    item_id = _item_id(item)
    title = _title(item)
    if item_id is None or title is None:
        raise CollectorFailure("invalid_content", "empty loc payload")
    description, truncated = _description(item)
    return LocItem(
        id=item_id,
        title=title,
        date=_date(item),
        contributors=_contributors(item),
        canonical_url=_canonical_url(item, item_id),
        rights=_rights(item),
        description=description,
        description_truncated=truncated,
    )


def _item_record(data: object) -> dict:
    if data is None or data == {} or data == []:
        raise CollectorFailure("invalid_content", "empty loc payload")
    if isinstance(data, list):
        raise CollectorFailure("invalid_content", "loc payload is not one item")
    if not isinstance(data, dict):
        raise CollectorFailure("invalid_content", "empty loc payload")
    if "results" in data and not _nested_item_is_record(data):
        raise CollectorFailure("invalid_content", "loc search results are not one item")
    if _nested_item_is_record(data):
        item = data.get("item")
        if isinstance(item, dict):
            return item
    if _is_item_record(data):
        return data
    raise CollectorFailure("invalid_content", "empty loc payload")


def _nested_item_is_record(data: dict) -> bool:
    item = data.get("item")
    return isinstance(item, dict) and _is_item_record(item)


def _is_item_record(data: dict) -> bool:
    title = data.get("title")
    if isinstance(title, list):
        title = next((entry for entry in title if isinstance(entry, str)), "")
    if not isinstance(title, str) or not title.strip():
        return False
    return _item_id(data) is not None


def _item_id(item: dict) -> str | None:
    for candidate in (item.get("url"), item.get("id")):
        found = _path_id(candidate)
        if found:
            return found
    lccn = item.get("library_of_congress_control_number")
    if isinstance(lccn, str) and _acceptable_id(lccn.strip()):
        return lccn.strip()
    numbers = item.get("number_lccn")
    if isinstance(numbers, list):
        for entry in numbers:
            if isinstance(entry, str) and _acceptable_id(entry.strip()):
                return entry.strip()
    return None


def _path_id(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in {"www.loc.gov", "loc.gov"}:
        return None
    if parsed.username or parsed.password:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[0] != "item":
        return None
    item_id = parts[1]
    if not _acceptable_id(item_id):
        return None
    return item_id


def _require_request_id(item_id: str) -> str:
    text = (item_id or "").strip()
    if _media_name(text):
        raise CollectorFailure("blocked_by_policy", "loc image and pdf downloads are not requested")
    if not _acceptable_id(text):
        raise CollectorFailure("invalid_content", "loc item id is not an item identifier")
    return text


def _acceptable_id(text: str) -> bool:
    if _ITEM_ID.fullmatch(text) is None:
        return False
    if _media_name(text) or _forbidden_token(text):
        return False
    return True


def _media_name(text: str) -> bool:
    lowered = text.lower().split("?", 1)[0].split("#", 1)[0]
    return lowered.endswith(_MEDIA_SUFFIX)


def _forbidden_token(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("search", "resource", "iiif", "tile", "..", "manifest"))


def _title(item: dict) -> str | None:
    value = item.get("title")
    if isinstance(value, list):
        value = next((entry for entry in value if isinstance(entry, str) and entry.strip()), None)
    if not isinstance(value, str):
        return None
    title = " ".join(value.split())
    if not title:
        return None
    if len(title) > MAX_TITLE_CHARS:
        raise CollectorFailure("content_too_large", "loc title exceeds limit")
    return title


def _date(item: dict) -> str:
    """Catalog date only. Modification timestamps and notes are not dates."""
    for candidate in (_date_value(item.get("date")), _nested_date(item)):
        if candidate is not None:
            return candidate
    return UNKNOWN


def _nested_date(item: dict) -> str | None:
    nested = item.get("item")
    if isinstance(nested, dict):
        return _date_value(nested.get("date"))
    return None


def _date_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    match = _DATE.fullmatch(text)
    if match is None:
        return None
    year = int(match.group(1))
    if year < 1000 or year > 9999:
        return None
    month = match.group(2)
    day = match.group(3)
    if month is not None and not 1 <= int(month) <= 12:
        return None
    if day is not None and not 1 <= int(day) <= 31:
        return None
    return text


def _contributors(item: dict) -> tuple[str, ...]:
    """One display name per contributor. Names are not joined or split.

    Facet maps whose values are ``/search`` links are not names.
    """
    named = item.get("contributor_names")
    if named is not None:
        return _name_list(named)
    nested = item.get("item")
    if isinstance(nested, dict) and nested.get("contributors") is not None:
        nested_names = nested.get("contributors")
        if _is_search_facet_list(nested_names):
            return ()
        return _name_list(nested_names)
    raw = item.get("contributors")
    if raw is None:
        return ()
    if _is_search_facet_list(raw):
        return ()
    return _name_list(raw)


def _is_search_facet_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(entry, dict) for entry in value)


def _name_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CollectorFailure("invalid_content", "loc contributors are not a list")
    if len(value) > MAX_CONTRIBUTORS:
        raise CollectorFailure("content_too_large", "loc contributor list exceeds limit")
    names: list[str] = []
    for entry in value:
        if isinstance(entry, dict):
            raise CollectorFailure("invalid_content", "loc contributor search links are not names")
        if not isinstance(entry, str):
            raise CollectorFailure("invalid_content", "loc contributor was not a name")
        name = " ".join(entry.split())
        if not name:
            continue
        if len(name) > MAX_NAME_CHARS:
            raise CollectorFailure("content_too_large", "loc contributor name exceeds limit")
        names.append(name)
    return tuple(names)


def _description(item: dict) -> tuple[str | None, bool]:
    """Keep the item description only up to 400 characters.

    Notes, related items, and rights HTML are not copied in its place.
    """
    raw = item.get("description")
    if raw is None:
        return None, False
    if isinstance(raw, str):
        parts = [raw]
    elif isinstance(raw, list):
        parts = []
        for entry in raw:
            if entry is None:
                continue
            if not isinstance(entry, str):
                raise CollectorFailure("invalid_content", "loc description was not text")
            parts.append(entry)
    else:
        raise CollectorFailure("invalid_content", "loc description was not text")
    text = " ".join(" ".join(part.split()) for part in parts if part.strip())
    text = " ".join(text.split())
    if not text:
        return None, False
    if len(text) > MAX_DESCRIPTION_CHARS:
        return text[:MAX_DESCRIPTION_CHARS], True
    return text, False


def _rights(item: dict) -> str:
    """US government work only when a rights field says so. Otherwise unknown."""
    chunks: list[str] = []
    for field in _RIGHTS_FIELDS:
        chunks.extend(_text_chunks(item.get(field)))
    text = _plain(" ".join(chunks))
    if not text or _NEGATED_GOV_WORK.search(text):
        return UNKNOWN
    if _GOV_WORK.search(text):
        return US_GOVERNMENT_WORK
    return UNKNOWN


def _text_chunks(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, str)]
    return []


def _plain(value: str) -> str:
    text = html.unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return " ".join(text.split())


def _canonical_url(item: dict, item_id: str) -> str:
    candidate = item.get("url")
    if isinstance(candidate, str) and _is_item_page(candidate, item_id):
        try:
            return canonicalize_url(candidate.strip())
        except ValueError:
            pass
    try:
        return canonicalize_url(f"https://www.loc.gov/item/{item_id}")
    except ValueError as exc:
        raise CollectorFailure("invalid_content", "loc item url is not canonical") from exc


def _is_item_page(url: str, item_id: str) -> bool:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https" or host not in _ITEM_HOSTS:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return parts == ["item", item_id]


def _is_metadata_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https" or host not in _ITEM_HOSTS:
        return False
    if parsed.username or parsed.password or parsed.fragment:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[0] != "item" or not _acceptable_id(parts[1]):
        return False
    if parse_qsl(parsed.query, keep_blank_values=True) != [("fo", "json"), ("at", "item")]:
        return False
    lowered = parsed.path.lower()
    if any(token in lowered for token in ("/resource", "/search", ".pdf", ".jpg", ".jpeg", ".png")):
        return False
    return True


def _looks_like_media(payload: bytes) -> bool:
    head = payload.lstrip().removeprefix(b"\xef\xbb\xbf")
    return head.startswith((b"%PDF", b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"II*\x00", b"MM\x00*"))
