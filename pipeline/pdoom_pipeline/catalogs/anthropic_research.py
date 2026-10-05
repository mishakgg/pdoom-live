"""Metadata catalog of public Anthropic research pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, abstracts, and
PDFs are not stored. Rights is ``creative_commons`` only when the page states
CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown. A public page, a copyright notice, an all-rights-reserved line, or a
terms link is not a licence. A page that does not state a publication date
keeps the date unknown. Updated, modified, and copyright years are not
publication dates. The live URL is stored as confirmed; a different
rel=canonical does not replace it. This module does not fetch and it is not a
belief collector. ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "anthropic_research_pages"
CATALOG_FILENAME = "anthropic_research_pages.json"
RUNNER_WIRED = False
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
HOST = "www.anthropic.com"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_COPYING_CODES = frozenset({"cc0", "cc-by", "cc-by-sa"})
_RESTRICTED_CODES = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_PUBLISHER_KEYS = ("citation_publisher", "publisher", "dcterms.publisher", "og:site_name")
_LICENSE_META_KEYS = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dc.rights.license",
        "dcterms.rights",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title", "twitter:title")
_SITE_SUFFIXES = (
    " \\ Anthropic PBC",
    " \\ Anthropic",
    " | Anthropic PBC",
    " | Anthropic",
    " - Anthropic PBC",
    " - Anthropic",
    " – Anthropic PBC",
    " – Anthropic",
    " — Anthropic PBC",
    " — Anthropic",
)
_DOWNLOAD_SUFFIXES = (".pdf", ".zip", ".csv", ".json", ".xml", ".jpg", ".jpeg", ".png", ".gif", ".webp")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SLUG = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,158}[A-Za-z0-9])?")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_JSONLD = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*(?:\"application/ld\+json\"|'application/ld\+json')[^>]*>(.*?)</script>"
)
_TIME_DT = re.compile(
    r"""(?is)<time\b[^>]*\bdatetime\s*=\s*(?:"([^"]*)"|'([^']*)')[^>]*>"""
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_TITLE_PUBLISHER = re.compile(r"^(?P<body>.+?)\s+(?:\\|\||[-–—])\s+(?P<publisher>Anthropic(?: PBC)?)$")
_STATED_LICENCE = re.compile(
    r"(?:this\s+(?:work|page|article|post|paper|publication|research|content|document|report|note)"
    r"|all\s+content|page\s+content|site\s+content)"
    r".{0,80}?"
    r"(?<!not )(?<!n't )"
    r"(?:is\s+|are\s+)?(?:made\s+available|available|licen[cs]ed|released)\s+under"
    r"(?:\s+the\s+terms\s+of)?"
    r"\s+(.{0,180})",
    re.I,
)
_GRANT_SENTENCE = re.compile(
    r"(?:^|[.!?]\s+)"
    r"(?:licen[cs]ed|released|made\s+available|available)\s+under"
    r"(?:\s+the\s+terms\s+of)?"
    r"\s+(.{0,180})",
    re.I,
)
_CC_URL = re.compile(
    r"creativecommons\.org/(?:licenses/(by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)|publicdomain/zero)(?:/|\b)",
    re.I,
)
_CODE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "cc-by-nc-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
            r"|attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv",
            re.I,
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
            r"|attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike",
            re.I,
        ),
    ),
    (
        "cc-by-nd",
        re.compile(r"\bcc[\s-]*by[\s-]*nd\b|attribution[\s-]*no[\s-]*deriv", re.I),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)"
            r"|attribution[\s-]*non[\s-]*commercial\b(?![\s-]*(?:share|no))",
            re.I,
        ),
    ),
    (
        "cc-by-sa",
        re.compile(r"\bcc[\s-]*by[\s-]*sa\b|attribution[\s-]*share[\s-]*alike", re.I),
    ),
    (
        "cc-by",
        re.compile(
            r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
            r"|creative\s+commons\s+attribution\b(?![\s-]*(?:non|no|share))",
            re.I,
        ),
    ),
    (
        "cc0",
        re.compile(r"\bcc[\s-]*0\b|\bcc0\b|creative\s+commons\s+zero\b|publicdomain/zero", re.I),
    ),
)
_URL_SLUGS = {
    "by": "cc-by",
    "by-sa": "cc-by-sa",
    "by-nd": "cc-by-nd",
    "by-nc": "cc-by-nc",
    "by-nc-sa": "cc-by-nc-sa",
    "by-nc-nd": "cc-by-nc-nd",
    "zero": "cc0",
}


class CatalogError(ValueError):
    """A catalog row or page failed the Anthropic research page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    previous: tuple[str, str] | None = None
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        key = _entry_sort_key(entry)
        if previous is not None and key < previous:
            raise CatalogError("entries must be ordered by date, then canonical URL")
        previous = key
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS} or {RIGHTS_UNKNOWN}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_date_prefix(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Anthropic research page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or host != HOST
        or parsed.netloc.lower() != HOST
        or hostname_is_blocked(host)
        or not _research_path(parsed.path or "")
    ):
        raise CatalogError(f"canonical URL is not a public Anthropic research page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == HOST and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons only when the page states CC0, CC BY, or CC BY-SA.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A public
    page, a copyright notice, an all-rights-reserved line, or a terms link is
    not a licence. Script and style text does not count. A mention of someone
    else's dataset licence does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible_html(page_text)
    codes = _stated_licence_codes(visible)
    copying = codes & _COPYING_CODES
    restricted = codes & _RESTRICTED_CODES
    if copying and not restricted:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, dcterms.modified, JSON-LD
    dateModified, and copyright years are not publication dates. A hub that
    lists several item dates does not supply a publication date for the hub.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_date_prefix(metas.get(key))
        if parsed:
            return parsed
    published = _jsonld_published_dates(page_html)
    if len(published) == 1:
        return published[0]
    single = _single_time_date(visible)
    if single:
        return single
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
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
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        name = _clean_text(metas.get(key, ""))
        if name and name.casefold() not in {"www.anthropic.com", "anthropic.com"}:
            return name
    title_tag = _TITLE.search(visible)
    if title_tag:
        match = _TITLE_PUBLISHER.search(_clean_text(title_tag.group(1)))
        if match:
            return match.group("publisher")
    names = _jsonld_publishers(page_html)
    if len(names) == 1:
        return names[0]
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body, abstract, or PDF. ``page_url``
    is the live URL that was fetched. A rel=canonical pointing somewhere else
    is not used.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _entry_sort_key(entry: dict) -> tuple[str, str]:
    published = entry["date"]
    stamp = "9999-99-99" if published == UNKNOWN_DATE else published
    return (stamp, entry["canonical_url"])


def _research_path(path: str) -> bool:
    if not path.startswith("/") or (path != "/" and path.endswith("/")):
        return False
    if "\\" in path or "//" in path or ".." in path or "%" in path:
        return False
    if path.lower().endswith(_DOWNLOAD_SUFFIXES):
        return False
    segments = path.strip("/").split("/")
    if not segments or segments[0] != "research":
        return False
    if len(segments) == 1:
        return True
    if len(segments) == 2:
        return _SLUG.fullmatch(segments[1]) is not None
    if len(segments) == 3 and segments[1] == "team":
        return _SLUG.fullmatch(segments[2]) is not None
    return False


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")
    if "<" in value or ">" in value:
        raise CatalogError(f"{field} must be plain text")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    text = (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(visible_html: str) -> str:
    return _clean_text(visible_html)


def _visible_html(page_html: str) -> str:
    return _HIDDEN.sub(" ", page_html)


def _iso_date_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return match.group(1)


def _single_time_date(visible_html: str) -> str | None:
    found: list[str] = []
    for primary, secondary in _TIME_DT.findall(visible_html):
        parsed = _iso_date_prefix(primary or secondary)
        if parsed:
            found.append(parsed)
    if len(found) == 1:
        return found[0]
    return None


def _jsonld_nodes(page_html: str) -> list[dict]:
    nodes: list[dict] = []
    for raw in _JSONLD.findall(page_html):
        try:
            data = json.loads(unescape(raw).strip())
        except json.JSONDecodeError:
            continue
        nodes.extend(node for node in _walk(data) if isinstance(node, dict))
    return nodes


def _jsonld_published_dates(page_html: str) -> list[str]:
    found: list[str] = []
    for node in _jsonld_nodes(page_html):
        parsed = _iso_date_prefix(node.get("datePublished"))
        if parsed and parsed not in found:
            found.append(parsed)
    return found


def _jsonld_publishers(page_html: str) -> list[str]:
    names: list[str] = []
    for node in _jsonld_nodes(page_html):
        publisher = node.get("publisher")
        for name in _publisher_name(publisher):
            if name not in names:
                names.append(name)
    return names


def _publisher_name(value: object) -> list[str]:
    if isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return [name.strip()]
        return []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_publisher_name(item))
        return names
    return []


def _walk(value: object):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _stated_licence_codes(visible_html: str) -> set[str]:
    codes: set[str] = set()
    for tag in _LINKISH.findall(visible_html):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").lower().replace("licence", "license")
        if "license" in rel.split():
            codes |= _codes_in_text(attrs.get("href", ""))
    metas = _metas(visible_html)
    for key, value in metas.items():
        if key in _LICENSE_META_KEYS:
            codes |= _codes_in_text(value)
    plain = _plain_text(visible_html)
    for pattern in (_STATED_LICENCE, _GRANT_SENTENCE):
        for match in pattern.finditer(plain):
            codes |= _codes_in_text(match.group(1))
    return codes


def _codes_in_text(value: str) -> set[str]:
    text = _plain_text(value)
    folded = text.casefold()
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        slug = (match.group(1) or "zero").lower()
        code = _URL_SLUGS.get(slug)
        if code:
            codes.add(code)
    for code, pattern in _CODE_PATTERNS:
        if pattern.search(text):
            codes.add(code)
    return codes


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
