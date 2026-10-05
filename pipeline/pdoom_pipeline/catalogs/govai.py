"""Metadata catalog of public Centre for the Governance of AI pages.

Rows keep a title, publisher, canonical URL, date, and rights label for official
HTML pages on www.governance.ai. Page text is not stored. A date the page does
not state stays unknown. Rights stay unknown unless the page states CC0, CC BY,
or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A
public page, a copyright notice, a terms link, or a bare Creative Commons
mention is not a licence.

Research papers, analysis posts, update posts, and staff profiles are not
listed. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "govai_pages"
CATALOG_FILENAME = "govai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Centre for the Governance of AI"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "www.governance.ai"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "content",
        "excerpt",
        "full_text",
        "html",
        "page",
        "page_text",
        "pdf",
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dcterms.created",
    "dc.date.issued",
)
_MODIFIED_DATE_KEYS = (
    "article:modified_time",
    "og:updated_time",
    "dcterms.modified",
    "dc.date.modified",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_DATE_PUBLISHED = re.compile(r"\b(?:date published|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b", re.I)
# creative_commons is only a licence that allows copying: CC0, CC BY, or CC BY-SA.
# NonCommercial and NoDerivatives are not labeled, so they cannot be read as permission to copy.
_CC0_PHRASE = re.compile(r"\bcc[\s-]*0\b|creative commons(?:\s+public\s+domain)?[\s-]+zero\b")
_CC_BY_SA_PHRASE = re.compile(
    r"\bcc[\s-]*by[\s-]*sa\b"
    r"|creative commons\s+attribution[\s-]*(?:share[\s-]*alike|sa)\b"
)
_CC_BY_PHRASE = re.compile(
    r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
    r"|creative commons\s+attribution\b"
    r"(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?|sa|nc|nd)\b)"
)
_CC_COPYING_URL = re.compile(
    r"creativecommons\.org/(?:licenses/by(?:-sa)?/|publicdomain/zero/)"
)
_SITE_SUFFIXES = (" | GovAI", " - GovAI")
_SITE_PREFIX = "GovAI | "


class CatalogError(ValueError):
    """A catalog row or page failed the GovAI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_govai_host(hostname: str) -> bool:
    """True only for the canonical www.governance.ai host."""
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a rights label.

    ``creative_commons`` means the page states CC0, CC BY, or CC BY-SA.
    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. Public
    availability, a copyright notice, a terms link, and a bare Creative Commons
    mention stay unknown.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    plain = _plain(html).casefold()
    if _states_creative_commons(plain) or any(_states_creative_commons(item.casefold()) for item in _meta_contents(html)):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Modified and updated times are not publication dates. A month and year, a
    copyright year, and a date inside script or style text do not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_html)
    metas = _meta_map(html)
    for key in _MODIFIED_DATE_KEYS:
        metas.pop(key, None)
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    match = _DATE_PUBLISHED.search(_plain(html))
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_html)
    metas = _meta_map(html)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(html)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(html)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": PUBLISHER,
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document["runner_wired"] is not False:
        raise CatalogError("runner_wired must be false")
    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for index, entry in enumerate(entries):
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if index and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict):
        raise CatalogError("entry must be an object")
    _reject_stored_body(entry, path="entry")
    if set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry, "title")
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an official www.governance.ai HTML page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OFFICIAL_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not official_govai_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _html_path(path)
    ):
        raise CatalogError(f"canonical URL must be an official www.governance.ai HTML page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _html_path(path: str) -> bool:
    if path == "/":
        return True
    if not path.startswith("/") or path.endswith("/"):
        return False
    lowered = path.casefold()
    return not lowered.endswith(_DOWNLOAD_SUFFIXES)


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS:
        raise CatalogError(f"{field} is too long")
    if "<" in value or ">" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _reject_stored_body(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        found = _FORBIDDEN_KEYS.intersection(value)
        if found:
            names = ", ".join(sorted(found))
            raise CatalogError(f"{path} must not store page text ({names})")
        for key, item in value.items():
            _reject_stored_body(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_stored_body(item, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if len(value) > MAX_DESCRIPTION_CHARS:
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _states_creative_commons(plain: str) -> bool:
    text = plain.casefold().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    return any(pattern.search(text) for pattern in (_CC0_PHRASE, _CC_BY_SA_PHRASE, _CC_BY_PHRASE, _CC_COPYING_URL))


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = _TAG.sub(" ", _without_hidden(page_text))
    text = unescape(text)
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = unescape(_TAG.sub(" ", value))
    text = re.sub(r"\s+", " ", text).strip()
    folded = text.casefold()
    for suffix in _SITE_SUFFIXES:
        if folded.endswith(suffix.casefold()):
            text = text[: -len(suffix)].strip()
            folded = text.casefold()
            break
    if folded.startswith(_SITE_PREFIX.casefold()):
        text = text[len(_SITE_PREFIX) :].strip()
    text = re.sub(r"^[^A-Za-z0-9]+", "", text).strip()
    return text


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _meta_map(html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_contents(html: str) -> list[str]:
    contents: list[str] = []
    for tag in _META.findall(html):
        content = _attrs(tag).get("content", "")
        if content:
            contents.append(content)
    return contents


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return None


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
