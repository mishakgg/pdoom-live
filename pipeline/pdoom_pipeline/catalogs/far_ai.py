"""Metadata catalog of public FAR.AI pages.

Rows keep a title, publisher, canonical URL, date, and rights label for official
HTML pages on www.far.ai. Page bodies, abstracts, and PDFs are not stored. A
date the page does not state stays unknown. Updated times, modification times,
and copyright years are not publication dates. The CMS ``datePublished`` clock
on this site is not a publication date: article pages display a research hero
date, and listing pages repeat other works' dates.

Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA and does not
also state a restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND
stay unknown. A hyphen is a word boundary, so the text CC BY does not match
CC BY-NC. A Creative Commons licences index URL is not itself a licence.
Public Domain Mark is not CC0. MIT and Apache-2.0 keep their own tokens.
A public page, a copyright notice, or a terms link is not a licence.

Author profiles are not catalog entries. This module does not fetch and it is
not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "far_ai_pages"
CATALOG_FILENAME = "far_ai_pages.json"
PUBLISHER = "FAR.AI"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_LABELS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_MIT, RIGHTS_APACHE}
)
OFFICIAL_HOST = "www.far.ai"
OFFICIAL_ORIGIN = "https://www.far.ai"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
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
_TOP_LEVEL = frozenset(
    {
        "about",
        "alignment-series-and-specialized-workshops",
        "blog",
        "careers",
        "contact",
        "donate",
        "events",
        "frontier-summit",
        "newsletter",
        "newsletters",
        "privacy-policy",
        "programs",
        "publications",
        "recordings",
        "research",
        "team",
        "terms-of-service",
        "transparency",
    }
)
_NESTED_ROOTS = frozenset({"blog", "events", "newsletters", "research"})
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "citation_date",
    "dcterms.issued",
    "dc.date.issued",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"[a-z0-9]+(?:-+[a-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_HERO_DATE = re.compile(
    r"(?is)<p\b[^>]*\bclass\s*=\s*(?:\"[^\"]*\bresearch_hero_date\b[^\"]*\"|'[^']*\bresearch_hero_date\b[^']*')[^>]*>(.*?)</p>"
)
_PUBLISHED_LABEL = re.compile(
    r"(?i)(?<!last )(?<!updated )(?<!modified )\b(?:date published|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b"
)
_LONG_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s+(\d{4})\b",
    re.IGNORECASE,
)
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " | frontier alignment research",
    " | far.ai",
    " | far ai",
    " - far.ai",
)
# Longer deeds are listed first. A hyphen ends the short code, so "by" does not match "by-nc".
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?=/|$|[?#])"
)
_TEXT_CODES = (
    ("by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("by-nc-sa", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    ("by-sa", re.compile(r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*nc\b)")),
    (
        "zero",
        re.compile(
            r"\bcc[\s-]*0\b|\bcc[\s-]*zero\b|\bcreative commons(?:\s+public\s+domain)?\s+zero\b"
        ),
    ),
    ("by", re.compile(r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)")),
    ("mark", re.compile(r"\bpublic domain mark\b")),
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?=/|$|[?#])")
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?=/|$|[?#])"
)
_MIT_PHRASE = re.compile(r"\bmit licen[cs]e\b|licen[cs]ed under (?:the )?mit licen[cs]e\b")
_APACHE_PHRASE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*2\.0)?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the FAR.AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_far_ai_host(hostname: str) -> bool:
    """True only for the official www.far.ai host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the
    page does not also state a restricted deed. A by-nc URL stays unknown
    even when the anchor text says CC BY. MIT and Apache-2.0 are their own
    tokens.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    blobs = [_plain(visible), *_hrefs(visible), *_license_meta_values(visible)]
    codes: set[str] = set()
    mit = False
    apache = False
    for blob in blobs:
        codes.update(_cc_codes(blob))
        mit = mit or _states_mit(blob)
        apache = apache or _states_apache(blob)
    if codes & _RESTRICTED:
        return RIGHTS_UNKNOWN
    permissive = bool(codes & _PERMISSIVE)
    if permissive and (mit or apache):
        return RIGHTS_UNKNOWN
    if mit and apache:
        return RIGHTS_UNKNOWN
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Modification times stay unknown.

    The displayed research hero date is the article date. A CMS
    ``datePublished`` value, an event date, a copyright year, and an updated
    or modified time are not publication dates.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    hero = _hero_publication_date(visible)
    if hero:
        return hero
    for raw in _meta_values(visible, _PUBLISHED_META):
        found = _iso_prefix(raw)
        if found:
            return found
    match = _PUBLISHED_LABEL.search(_plain(visible))
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(heading.group(1))
        if title:
            return title
    raise CatalogError("title is required")


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
            "publisher": PUBLISHER,
            "canonical_url": confirmed_url(page_html, page_url),
            "date": date_from_page(page_html),
            "rights": rights_from_page(page_html),
        }
    )


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(_without_trailing_slash(page_url))
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_without_trailing_slash(_absolute(live, href)))
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
        raise CatalogError("catalog fields must be catalog_id, description, and entries")
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
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
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an https www.far.ai page")
    if any(mark in url for mark in ("?", "#", "\\", "@", "%")):
        raise CatalogError(f"canonical URL must be an https www.far.ai page: {url}")
    if not url.startswith(OFFICIAL_ORIGIN):
        raise CatalogError(f"canonical URL must be an https www.far.ai page: {url}")
    path = url[len(OFFICIAL_ORIGIN) :]
    if path.startswith("//") or (path and not path.startswith("/")) or not _official_path(path):
        raise CatalogError(f"canonical URL must be an https www.far.ai page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _official_path(path: str) -> bool:
    if path == "":
        return True
    if not path.startswith("/") or path.endswith("/") or "//" in path or ".." in path:
        return False
    parts = path.split("/")[1:]
    if any(_SEGMENT.fullmatch(part) is None for part in parts):
        return False
    if len(parts) == 1:
        return parts[0] in _TOP_LEVEL
    if len(parts) == 2:
        return parts[0] in _NESTED_ROOTS
    return False


def _without_trailing_slash(url: str) -> str:
    if url == OFFICIAL_ORIGIN + "/":
        return OFFICIAL_ORIGIN
    if url.startswith(OFFICIAL_ORIGIN + "/") and url.endswith("/") and url.count("/") > 3:
        return url.rstrip("/")
    return url


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


def _same_page(left: str, right: str) -> bool:
    left_path = left[len(OFFICIAL_ORIGIN) :].rstrip("/")
    right_path = right[len(OFFICIAL_ORIGIN) :].rstrip("/")
    return left.startswith(OFFICIAL_ORIGIN) and right.startswith(OFFICIAL_ORIGIN) and left_path == right_path


def _absolute(base: str, href: str) -> str:
    raw = unescape(href).strip()
    if raw.startswith("https://") or raw.startswith("http://"):
        return raw
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("/"):
        return OFFICIAL_ORIGIN + raw
    return raw or base


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain(value).replace("\u200b", "").replace("\ufeff", "")
    folded = text.casefold()
    changed = True
    while changed:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix):
                text = text[: -len(suffix)].strip()
                folded = text.casefold()
                changed = True
                break
    return text.strip()


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


def _meta_values(html: str, names: tuple[str, ...] | frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _license_meta_values(html: str) -> list[str]:
    return _meta_values(html, _LICENSE_META)


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _normalize_licence_text(value: str) -> str:
    text = unescape(value).casefold().replace("\xa0", " ")
    for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text)


def _cc_codes(value: str) -> set[str]:
    text = _normalize_licence_text(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(text):
        code = match.group("code") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _TEXT_CODES:
        if pattern.search(text):
            codes.add(code)
    if "creative commons" in text:
        if re.search(r"attribution[-\s]*non[-\s]*commercial[-\s]*no[-\s]*deriv", text):
            codes.add("by-nc-nd")
        elif re.search(r"attribution[-\s]*non[-\s]*commercial[-\s]*share", text):
            codes.add("by-nc-sa")
        elif re.search(r"attribution[-\s]*non[-\s]*commercial", text):
            codes.add("by-nc")
        elif re.search(r"attribution[-\s]*no[-\s]*deriv", text):
            codes.add("by-nd")
        elif re.search(r"attribution[-\s]*share[-\s]*alike", text):
            codes.add("by-sa")
        elif re.search(r"\battribution\b", text):
            codes.add("by")
    return codes


def _states_mit(value: str) -> bool:
    text = _normalize_licence_text(value).strip()
    if text in {"mit", "mit-license", "mit-licence"}:
        return True
    return _MIT_URL.search(text) is not None or _MIT_PHRASE.search(text) is not None


def _states_apache(value: str) -> bool:
    text = _normalize_licence_text(value).strip()
    if text in {"apache-2.0", "apache-2", "apache2.0"}:
        return True
    return _APACHE_URL.search(text) is not None or _APACHE_PHRASE.search(text) is not None


def _hero_publication_date(visible_html: str) -> str | None:
    """Return the displayed article date.

    FAR.AI reuses the research hero class for the abstract label, so only
    values that are a month, day, and year count. Several different dates on
    one page are not one publication date.
    """
    found: list[str] = []
    for inner in _HERO_DATE.findall(visible_html):
        parsed = _long_date(_plain(inner))
        if parsed:
            found.append(parsed)
    if len(set(found)) == 1:
        return found[0]
    return None


def _long_date(value: str) -> str | None:
    match = _LONG_DATE.search(value)
    if match is None:
        return None
    month = _MONTHS[match.group(1).casefold()]
    try:
        return date(int(match.group(3)), month, int(match.group(2))).isoformat()
    except ValueError:
        return None


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
