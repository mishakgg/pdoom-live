"""Metadata catalog of public OpenAI research index pages.

Each stored URL was confirmed with one bounded GET that returned the page
HTML. A blocked response is omitted. A row keeps the title, publisher,
canonical URL, date, and rights label. Page text, abstracts, and PDFs are
not stored. Rights is ``creative_commons`` only when the page states CC0,
CC BY, or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown. A public page, a copyright notice, an all-rights-reserved line, or
a terms link is not a licence. Updated, modified, and copyright years are
not publication dates. A missing date stays unknown. The live URL is stored
as confirmed; a different rel=canonical does not replace it. This module
does not fetch and it is not a belief collector. ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "openai_research_pages"
CATALOG_FILENAME = "openai_research_pages.json"
RUNNER_WIRED = False
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "openai.com"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
_QUALIFYING_LICENCES = frozenset({"cc0", "cc-by", "cc-by-sa"})

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_INDEX_PATH = re.compile(
    r"^/(?:research/index(?:/[a-z0-9]+(?:-[a-z0-9]+)*)?|news/research)/?$"
)
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_BLOCK_MARKERS = ("cdn-cgi/challenge-platform", "cf-browser-verification")
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_PUBLISHER_KEYS = (
    "citation_publisher",
    "dc.publisher",
    "dcterms.publisher",
    "og:site_name",
)
_SITE_SUFFIXES = (" | OpenAI", " - OpenAI", " – OpenAI", " — OpenAI")
_DOWNLOAD_SUFFIXES = (".pdf", ".zip", ".csv", ".json", ".xml", ".jpg", ".jpeg", ".png", ".gif", ".webp")
_CC_URL = re.compile(
    r"(?i)(?:^|[^a-z0-9])creativecommons\.org/"
    r"(?P<kind>publicdomain/zero|publicdomain/mark|licenses/(?:by-nc-nd|by-nc-sa|by-nd|by-nc|by-sa|by))"
    r"(?=/|[^\w-]|$)"
)
_CC_TEXT = re.compile(
    r"(?i)(?:"
    r"\bcc\s*0\b|\bcc0\b|creative commons zero\b"
    r"|creative commons attribution[-\s]*non[-\s]*commercial[-\s]*no[-\s]*derivatives"
    r"|creative commons attribution[-\s]*non[-\s]*commercial[-\s]*share[-\s]*alike"
    r"|creative commons attribution[-\s]*non[-\s]*commercial"
    r"|creative commons attribution[-\s]*no[-\s]*derivatives"
    r"|creative commons attribution[-\s]*share[-\s]*alike"
    r"|creative commons attribution\b"
    r"|\bcc[-\s]by[-\s]nc[-\s]nd\b"
    r"|\bcc[-\s]by[-\s]nc[-\s]sa\b"
    r"|\bcc[-\s]by[-\s]nc\b"
    r"|\bcc[-\s]by[-\s]nd\b"
    r"|\bcc[-\s]by[-\s]sa\b"
    r"|\bcc[-\s]by\b"
    r"|\bccby(?:ncnd|ncsa|nc|nd|sa)?\b"
    r")"
)
_URL_LICENCE = {
    "publicdomain/zero": "cc0",
    "publicdomain/mark": "pdm",
    "licenses/by-nc-nd": "cc-by-nc-nd",
    "licenses/by-nc-sa": "cc-by-nc-sa",
    "licenses/by-nd": "cc-by-nd",
    "licenses/by-nc": "cc-by-nc",
    "licenses/by-sa": "cc-by-sa",
    "licenses/by": "cc-by",
}


class CatalogError(ValueError):
    """A catalog row or page failed the OpenAI research index rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    _require_text(document.get("description"), "description", MAX_DESCRIPTION_CHARS)
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS} or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}") from exc
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public OpenAI research index page")
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
        or not host
        or not is_official_host(host)
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public OpenAI research index page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons only for a stated CC0, CC BY, or CC BY-SA licence.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. Script,
    style, noscript, and comments do not count. A copyright notice, an
    all-rights-reserved line, a terms link, or the fact that the page is
    public is not a reuse licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _normalize_marks(_visible_html(page_text))
    if _QUALIFYING_LICENCES.intersection(_licence_codes(visible)):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, dcterms.modified, and a copyright
    year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible_html(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = _DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(heading.group(1))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible_html(page_html))
    for key in _PUBLISHER_KEYS:
        raw = metas.get(key, "").strip()
        if not raw:
            continue
        name = _clean_text(raw)
        if not name or name.casefold().startswith(("http://", "https://")):
            continue
        return name
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed research index page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def row_from_response(body: object, *, status: int, content_type: str, page_url: str) -> dict | None:
    """Return a row only when the response is the page HTML.

    A blocked status, a non-HTML type, or an interstitial is omitted. A page
    that does not state a title is omitted rather than given an invented title.
    """

    if status != 200:
        return None
    media = (content_type or "").split(";", 1)[0].strip().lower()
    if media not in _HTML_TYPES:
        return None
    if isinstance(body, bytes):
        text = body.decode("utf-8", "replace")
    elif isinstance(body, str):
        text = body
    else:
        return None
    if not text.strip():
        return None
    folded = text.casefold()
    if any(marker in folded for marker in _BLOCK_MARKERS):
        return None
    try:
        return page_record(text, page_url=page_url)
    except CatalogError:
        return None


def _official_path(path: str) -> bool:
    if path != path.lower() or path.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _INDEX_PATH.fullmatch(path) is not None


def _licence_codes(visible: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(visible):
        kind = match.group("kind").lower()
        code = _URL_LICENCE.get(kind)
        if code:
            codes.add(code)
    for match in _CC_TEXT.finditer(visible):
        code = _code_from_text(match.group(0))
        if code:
            codes.add(code)
    return codes


def _code_from_text(token: str) -> str | None:
    compact = re.sub(r"[^a-z0-9]+", "", token.casefold())
    if compact in {"cc0", "cczero"} or "creativecommonszero" in compact:
        return "cc0"
    if "noncommercial" in compact and "noderivative" in compact:
        return "cc-by-nc-nd"
    if "noncommercial" in compact and "sharealike" in compact:
        return "cc-by-nc-sa"
    if "noncommercial" in compact:
        return "cc-by-nc"
    if "noderivative" in compact:
        return "cc-by-nd"
    if "sharealike" in compact:
        return "cc-by-sa"
    if "attribution" in compact:
        return "cc-by"
    if "ccbyncnd" in compact:
        return "cc-by-nc-nd"
    if "ccbyncsa" in compact:
        return "cc-by-nc-sa"
    if "ccbync" in compact:
        return "cc-by-nc"
    if "ccbynd" in compact:
        return "cc-by-nd"
    if "ccbysa" in compact:
        return "cc-by-sa"
    if "ccby" in compact:
        return "cc-by"
    return None


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _visible_html(page_html: str) -> str:
    return _HIDDEN.sub(" ", page_html)


def _normalize_marks(value: str) -> str:
    text = unescape(value)
    return (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
