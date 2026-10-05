"""Metadata catalog of public Federal Trade Commission pages about AI.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
and PDFs are not stored. A date the page does not state stays unknown.
Updated, modified, and copyright years are not publication dates. Rights stay
unknown unless a rights field says the item is a US government work, or the
page states CC0, CC BY, or CC BY-SA and does not also state a restricted deed.
CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen ends a
deed token, so the text CC BY does not match CC BY-NC. A public page, a
copyright notice, All rights reserved, or a terms link is not a licence. A
.gov host is not a licence. This catalog is not a collector and runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ftc_ai_pages"
CATALOG_FILENAME = "ftc_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_US_GOVERNMENT_WORK, RIGHTS_CREATIVE_COMMONS}
)
PUBLISHER = "Federal Trade Commission"
OFFICIAL_HOST = "ftc.gov"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
        "chart",
        "chart_data",
        "content",
        "excerpt",
        "full_text",
        "html",
        "page",
        "page_text",
        "pdf",
        "pdoom",
        "p_doom",
        "probability",
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_PERMISSIVE = frozenset({"cc0", "cc-by", "cc-by-sa"})
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PUBLISHED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.issued",
    }
)
_PUBLISHER_META = ("og:site_name", "citation_publisher", "dcterms.publisher", "publisher")
_TITLE_META = ("og:title", "citation_title", "dcterms.title")
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_PATH_CHARS = re.compile(r"^/[a-z0-9/_-]*[a-z0-9]/?$")
_AI_RELATED = re.compile(
    r"(?i)\bai\b|artificial intelligence|machine learning|generative ai|\balgorithms?\b|"
    r"\bchatbots?\b|\bdeepfakes?\b|\bllms?\b"
)
_URL = re.compile(
    r"(?i)^(?P<scheme>https)://(?P<host>\[[^\]]+\]|[^/:@?#]+)"
    r"(?::(?P<port>\d+))?(?P<path>/[^?#]*)?(?:\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"')
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RIGHTS_ELEMENT = re.compile(
    r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s*(?:\||[-–—])\s*Federal Trade Commission\s*$")
_GENERIC_TITLES = frozenset({"federal trade commission", "home", "search"})
# A hyphen is a token boundary. `(?!-)` stops CC BY from matching CC BY-NC.
_TEXT_DEEDS = (
    ("cc-by-nc-sa", re.compile(r"\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nc(?:\s+|-\s*)sa\b")),
    ("cc-by-nc-nd", re.compile(r"\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nc(?:\s+|-\s*)nd\b")),
    ("cc-by-nc", re.compile(r"\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nc\b")),
    ("cc-by-nd", re.compile(r"\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nd\b")),
    ("cc-by-sa", re.compile(r"\bcc(?:\s+|-\s*)by(?:\s+|-\s*)sa\b")),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution(?:\s*|-)+non-?commercial(?:\s*|-)+share-?alike"
        ),
    ),
    (
        "cc-by-nc-nd",
        re.compile(r"creative commons attribution(?:\s*|-)+non-?commercial(?:\s*|-)+no-?deriv"),
    ),
    (
        "cc-by-nc",
        re.compile(r"creative commons attribution(?:\s*|-)+non-?commercial"),
    ),
    ("cc-by-nd", re.compile(r"creative commons attribution(?:\s*|-)+no-?deriv")),
    ("cc-by-sa", re.compile(r"creative commons attribution(?:\s*|-)+share-?alike")),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution\b(?!\s*-?\s*(?:non-?commercial|no-?deriv|share-?alike))"
        ),
    ),
    ("cc0", re.compile(r"\bcc0\b|\bcreative commons(?:\s+|-)(?:cc0|zero)\b")),
    ("cc-by", re.compile(r"\bcc(?:\s+|-\s*)by\b(?!-)")),
)
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_NEGATED_GOV = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_PUBLISHED_PROSE = re.compile(
    r"(?i)\b(?:published|publication date|date published|posted)\b(?:\s+on)?\s*:?\s*"
    r"(?:(\d{4}-\d{2}-\d{2})|([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})|(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}))"
)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


class CatalogError(ValueError):
    """A catalog row or page failed the Federal Trade Commission page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_ftc_host(hostname: str) -> bool:
    """True for ftc.gov and its subdomains."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or "@" in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(_HOST_LABEL.fullmatch(label) is None or label.startswith("-") or label.endswith("-") for label in labels):
        return False
    return host == OFFICIAL_HOST or host.endswith("." + OFFICIAL_HOST)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. A .gov host alone stays unknown.

    ``us_government_work`` requires a rights field that says the item is a US
    government work. ``creative_commons`` is only CC0, CC BY, or CC BY-SA.
    A restricted deed, alone or beside a permissive deed, stays unknown.
    Public Domain Mark is not CC0. A generic creativecommons.org/licenses/
    URL is not a permissive deed.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    without_comments = _COMMENT.sub(" ", page_text)
    codes: set[str] = set()
    gov = False
    for license_text, rights_text in _jsonld_rights(without_comments):
        codes |= _cc_codes(license_text)
        if _states_us_government_work(rights_text):
            gov = True
        codes |= _cc_codes(rights_text)
    visible = _HIDDEN.sub(" ", without_comments)
    for value in _rights_field_texts(visible):
        if _states_us_government_work(value):
            gov = True
        codes |= _cc_codes(value)
    for value in _license_meta_texts(visible):
        codes |= _cc_codes(value)
    codes |= _cc_codes(_plain(visible))
    for href, anchor_text in _ANCHOR.findall(visible):
        attrs = _attrs(f"<a {href}>")
        codes |= _cc_codes(attrs.get("href", ""))
        codes |= _cc_codes(_plain(anchor_text))
    for href in _license_hrefs(visible):
        codes |= _cc_codes(href)
    if codes & _RESTRICTED:
        return RIGHTS_UNKNOWN
    if gov and codes & _PERMISSIVE:
        return RIGHTS_UNKNOWN
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    if codes & _PERMISSIVE:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    without_comments = _COMMENT.sub(" ", page_text)
    for raw in _jsonld_dates(without_comments):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    visible = _HIDDEN.sub(" ", without_comments)
    for raw in _meta_values(visible, _PUBLISHED_META):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    return _published_prose(_plain(visible))


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", _COMMENT.sub(" ", page_html))
    metas = _metas(visible)
    for key in _TITLE_META:
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    for heading in _H1.findall(visible):
        title = _clean_title(heading)
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_HIDDEN.sub(" ", _COMMENT.sub(" ", page_html)))
    for key in _PUBLISHER_META:
        if _plain(metas.get(key, "")) == PUBLISHER:
            return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return validate_entry(
        {
            "title": title_from_page(page_html),
            "publisher": publisher_from_page(page_html),
            "canonical_url": confirmed_url(page_html, page_url),
            "date": date_from_page(page_html),
            "rights": rights_from_page(page_html),
        }
    )


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_resolve(live, href))
    except CatalogError:
        return live
    if _same_page(declared, live):
        return declared
    return live


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
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
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
    _require_text(entry, "publisher")
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    if not _ai_related(entry["title"], entry["canonical_url"]):
        raise CatalogError("entry must be an AI-related FTC page")
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "@" in url or "%" in url:
        raise CatalogError("canonical URL must be an https ftc.gov AI page")
    parts = _split_url(url)
    if parts is None:
        raise CatalogError(f"canonical URL must be an https ftc.gov AI page: {url}")
    path = parts["path"]
    if (
        parts["scheme"] != "https"
        or parts["query"] is not None
        or parts["fragment"] is not None
        or parts["port"] not in (None, "443")
        or not official_ftc_host(parts["host"])
        or ".." in path
        or "\\" in path
        or "//" in path
        or _PATH_CHARS.fullmatch(path) is None
        or _is_download(path)
        or "/system/files/" in path
        or not _ai_related(path, path)
    ):
        raise CatalogError(f"canonical URL must be an https ftc.gov AI page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _ai_related(title: str, url: str) -> bool:
    blob = f"{title} {url}".replace("-", " ").replace("/", " ").replace("_", " ")
    return _AI_RELATED.search(blob) is not None


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value or "\n" in value:
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


def _split_url(url: str) -> dict | None:
    match = _URL.fullmatch(url)
    if match is None:
        return None
    host = match.group("host")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if host.endswith(".") or host != host.lower():
        return None
    return {
        "scheme": match.group("scheme").lower(),
        "host": host,
        "port": match.group("port"),
        "path": match.group("path") or "/",
        "query": match.group("query"),
        "fragment": match.group("fragment"),
    }


def _same_page(left: str, right: str) -> bool:
    a = _split_url(left)
    b = _split_url(right)
    if a is None or b is None:
        return False
    return a["host"] == b["host"] and a["path"].rstrip("/") == b["path"].rstrip("/")


def _resolve(base: str, href: str) -> str:
    raw = unescape(href).strip()
    if not raw or raw.startswith(("#", "mailto:", "javascript:")):
        return raw
    if raw.startswith("//"):
        return "https:" + raw
    if raw.lower().startswith("https://") or raw.lower().startswith("http://"):
        return raw
    parts = _split_url(base)
    if parts is None:
        return raw
    if raw.startswith("/"):
        return f"https://{parts['host']}{raw}"
    parent = parts["path"].rsplit("/", 1)[0]
    return f"https://{parts['host']}{parent}/{raw}"


def _is_download(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _plain(value))
    return _GOV_WORK.search(text) is not None


def _cc_codes(value: str) -> set[str]:
    """Licence codes in one string. CC BY does not match CC BY-NC."""
    folded = unescape(value).replace("\\/", "/")
    folded = folded.replace("\xa0", " ").replace("–", "-").replace("—", "-")
    folded = re.sub(r"\s+", " ", folded).casefold()
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            codes.add(f"cc-{license_code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _jsonld_rights(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for block in _LDJSON.findall(page_html):
        licenses = [item.replace("\\/", "/") for item in _LD_LICENSE.findall(block)]
        rights = [item.replace("\\/", "/") for item in _LD_RIGHTS.findall(block)]
        if not licenses and not rights:
            continue
        width = max(len(licenses), len(rights), 1)
        licenses.extend([""] * (width - len(licenses)))
        rights.extend([""] * (width - len(rights)))
        found.extend(zip(licenses, rights, strict=True))
    return found


def _jsonld_dates(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        found.extend(_DATE_PUBLISHED.findall(block))
    return found


def _license_meta_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key in {"license", "licence"} or key.endswith((".license", ".licence", ":license", ":licence")):
            found.append(value)
    return found


def _rights_field_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            found.append(value)
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(page_html):
        if not _is_rights_element(attrs):
            continue
        text = _plain(body)
        if text and len(text) <= MAX_FIELD_CHARS:
            found.append(text)
    return found


def _is_rights_element(attrs: str) -> bool:
    parsed = _attrs(f"<x {attrs}>")
    if parsed.get("itemprop", "").casefold() == "rights":
        return True
    for key in ("id", "class"):
        raw = parsed.get(key, "").replace("-", " ").replace("_", " ")
        if any(token.casefold() == "rights" for token in raw.split()):
            return True
    return False


def _published_prose(plain: str) -> str:
    match = _PUBLISHED_PROSE.search(plain)
    if match is None:
        return UNKNOWN_DATE
    if match.group(1):
        return _iso_day(match.group(1)) or UNKNOWN_DATE
    if match.group(4):
        return _calendar(int(match.group(4)), match.group(2), int(match.group(3)))
    return _calendar(int(match.group(7)), match.group(6), int(match.group(5)))


def _calendar(year: int, month_name: str, day: int) -> str:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return UNKNOWN_DATE
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return UNKNOWN_DATE


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    value = match.group(1)
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _plain(value)).strip()


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() not in _GENERIC_TITLES


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found.setdefault(key.casefold(), unescape(double or single or bare).strip())
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(page_html)
    return [metas[name] for name in names if metas.get(name)]


def _canonical_href(page_html: str) -> str:
    visible = _HIDDEN.sub(" ", _COMMENT.sub(" ", page_html))
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _license_hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel or "licence" in rel:
            if attrs.get("href"):
                hrefs.append(attrs["href"])
    return hrefs
