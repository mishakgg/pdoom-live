"""Metadata catalog of public pages on the official host bair.berkeley.edu.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
text, abstracts, and PDFs are not stored. A date the page does not state stays
unknown. Updated, modified, and copyright years are not publication dates.
Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA.
``creative_commons`` means only those three. CC BY-NC, CC BY-ND, CC BY-NC-SA,
and CC BY-NC-ND stay unknown, and a restricted deed wins when it appears
beside a permissive one. A hyphen is part of the deed, so CC BY does not match
CC BY-NC. ``uk_ogl`` is used only when the page states the Open Government
Licence. ``us_government_work`` is used only when a rights field says the item
is a US government work. A public page, a copyright notice, or a .edu host is
not a licence. A challenge page or a non-HTML response is not stored. This
catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "bair_pages"
CATALOG_FILENAME = "bair_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
    }
)
OFFICIAL_HOST = "bair.berkeley.edu"
PUBLISHER = "Berkeley AI Research Lab"
MAX_FIELD_CHARS = 500
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
_SECTION_PATHS = frozenset(
    {
        "/",
        "/blog/",
        "/blog/about/",
        "/blog/archive/",
        "/blog/subscribe/",
    }
)
_HTML_PATHS = frozenset(
    {
        "/initiatives/bair-reu.html",
        "/initiatives/hic.html",
        "/initiatives/responsible-ai.html",
        "/resources/admissions.html",
        "/resources/courses.html",
        "/resources/seminar.html",
        "/resources/software.html",
        "/resources/textbooks.html",
    }
)
_RIGHTS_META = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dc.rights",
        "dcterms.rights",
        "rights",
    }
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "cf-browser-verification",
    "challenge-platform",
    "checking your browser",
    "enable javascript and cookies",
    "sgcaptcha",
    "sg-captcha",
    "/.well-known/sgcaptcha",
    "akamaighost",
    "edgesuite.net",
    "are you a robot",
    "verify you are human",
    "robot interstitial",
)
_SITE_SUFFIXES = (
    " | The Berkeley Artificial Intelligence Research Blog",
    " – The Berkeley Artificial Intelligence Research Blog",
    " — The Berkeley Artificial Intelligence Research Blog",
    " - The Berkeley Artificial Intelligence Research Blog",
    " | The BAIR Blog",
    " | BAIR",
    " – BAIR",
    " — BAIR",
    " - BAIR",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_POST_PATH = re.compile(r"^/blog/(\d{4})/(\d{2})/(\d{2})/([a-z0-9]+(?:-[a-z0-9]+)*)/$")
_HTTP_URL = re.compile(
    r"^(?P<scheme>https?)://"
    r"(?:(?P<userinfo>[^/?#@]*)@)?"
    r"(?P<host>\[[0-9A-Fa-f:.]+\]|[^:/?#]+)"
    r"(?::(?P<port>[0-9]+))?"
    r"(?P<path>/[^?#]*)?"
    r"(?P<query>\?[^#]*)?"
    r"(?P<fragment>#.*)?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_RIGHTS = re.compile(r'"(?:license|rights)"\s*:\s*"((?:\\.|[^"\\])*)"')
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_HREF_TAG = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# Longer restricted deeds are listed first. A hyphen is not a word boundary:
# the deed must end before another letter or hyphen, so CC BY does not match
# CC BY-NC and licenses/by does not match licenses/by-nc.
_DEED_END = r"(?![a-z0-9-])"
_CC_URL = re.compile(
    r"(?i)(?:https?:)?//(?:www\.)?creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    + _DEED_END
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd{_DEED_END}")),
    ("by-nc-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa{_DEED_END}")),
    ("by-nc", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc{_DEED_END}")),
    ("by-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nd{_DEED_END}")),
    ("by-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*sa{_DEED_END}")),
    (
        "zero",
        re.compile(
            rf"(?i)(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero){_DEED_END}"
            rf"|creative commons(?:\s+public\s+domain)?[\s-]+zero{_DEED_END}"
        ),
    ),
    ("by", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*by{_DEED_END}")),
    (
        "by-nc-nd",
        re.compile(
            r"(?i)creative commons[\s-]+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?i)creative commons[\s-]+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"(?i)creative commons[\s-]+attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
        ),
    ),
    (
        "by-nd",
        re.compile(r"(?i)creative commons[\s-]+attribution[\s-]+no[\s-]*deriv"),
    ),
    (
        "by-sa",
        re.compile(r"(?i)creative commons[\s-]+attribution[\s-]+share[\s-]*alike"),
    ),
    (
        "by",
        re.compile(
            r"(?i)creative commons[\s-]+attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_NONPERMISSIVE_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_OGL = re.compile(r"(?i)\bopen[\s-]+government[\s-]+licence\b")
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_UNUSABLE_TITLES = frozenset(
    {
        "404",
        "404: this page could not be found.",
        "this page could not be found.",
        "just a moment...",
        "access denied",
    }
)


class CatalogError(ValueError):
    """A catalog row or page failed the BAIR page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for the official bair.berkeley.edu host."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML on bair.berkeley.edu that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
                return False
    try:
        validate_canonical_url(page_url)
    except CatalogError:
        return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict[str, str] | None = None,
) -> dict | None:
    """Return metadata when the response is the page HTML.

    A challenge page, an HTTP 202 response, a non-HTML response, or a final
    URL off bair.berkeley.edu is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA. Noncommercial and
    no-derivatives deeds stay unknown, including when the anchor text says
    CC BY and the URL is a restricted deed. A public-domain mark is not CC0.
    ``uk_ogl`` requires the words "open government licence".
    ``us_government_work`` requires a rights field that says the item is a US
    government work. A .edu host is not a licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    licence_blobs = _jsonld_rights(page_text)
    visible = _without_hidden(page_text)
    licence_blobs.extend(_rights_fields(visible))
    licence_blobs.extend(_hrefs(visible))
    plain = _plain(visible)
    codes: set[str] = set()
    for blob in licence_blobs:
        codes.update(_cc_codes(blob))
    codes.update(_cc_codes(plain))
    if codes & _NONPERMISSIVE_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    rights_text = _plain(" ".join(licence_blobs))
    if rights_text and not _NEGATED_GOV_WORK.search(rights_text) and _GOV_WORK.search(rights_text):
        return RIGHTS_US_GOVERNMENT_WORK
    if _OGL.search(plain):
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Modification times stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    visible = _without_hidden(page_text)
    for raw in _meta_values(visible, _PUBLICATION_DATE_KEYS):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if _usable_title(title):
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """The lab is the publisher. A person named on the page is not."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return PUBLISHER


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical does not replace it.
    """

    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    return page_record(page_html, page_url=page_url)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or not description.strip() or description != description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if "p(doom)" in description.casefold():
        raise CatalogError("description must not store a p(doom) figure")
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
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
    _require_text(entry.get("title"), "title")
    _require_text(entry.get("publisher"), "publisher")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    if "p(doom)" in entry["title"].casefold():
        raise CatalogError("title must not store a p(doom) figure")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char in url for char in " \t\r\n"):
        raise CatalogError("canonical URL must be an https bair.berkeley.edu page")
    parsed = _split_url(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https bair.berkeley.edu page: {url}")
    host = parsed["host"]
    path = parsed["path"]
    if (
        parsed["scheme"] != "https"
        or parsed["userinfo"]
        or parsed["query"]
        or parsed["fragment"]
        or parsed["port"] is not None
        or not is_official_host(host)
        or not _official_path(path)
    ):
        raise CatalogError(f"canonical URL must be an https bair.berkeley.edu page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _official_path(path: str) -> bool:
    if ".." in path or "\\" in path or "//" in path or "%" in path:
        return False
    if path in _SECTION_PATHS or path in _HTML_PATHS:
        return True
    match = _POST_PATH.fullmatch(path)
    if match is None:
        return False
    try:
        date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    return True


def _split_url(url: str) -> dict[str, str | None] | None:
    match = _HTTP_URL.fullmatch(url)
    if match is None:
        return None
    host = match.group("host") or ""
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    port = match.group("port")
    return {
        "scheme": (match.group("scheme") or "").lower(),
        "userinfo": match.group("userinfo"),
        "host": host.lower().rstrip("."),
        "port": port,
        "path": match.group("path") or "",
        "query": match.group("query"),
        "fragment": match.group("fragment"),
    }


def _require_text(value: object, field: str) -> None:
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
        if len(value) > MAX_DESCRIPTION_CHARS and path.endswith("description"):
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    text = (
        text.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    folded = title.casefold()
    if folded in _UNUSABLE_TITLES or folded.startswith("index of "):
        return False
    return True


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


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _HREF_TAG.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _rights_fields(page_html: str) -> list[str]:
    fields: list[str] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key in _RIGHTS_META and attrs.get("content"):
            fields.append(attrs["content"])
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if ("license" in rel or "licence" in rel) and attrs.get("href"):
            fields.append(attrs["href"])
    for attrs_text, inner in _ANCHOR.findall(page_html):
        attrs = _attrs(f"<a {attrs_text}>")
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel or "licence" in rel:
            text = _plain(inner)
            if text:
                fields.append(text)
    return fields


def _jsonld_rights(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_RIGHTS.findall(blob):
            found.append(raw.replace("\\/", "/"))
    return found


def _cc_codes(value: str) -> set[str]:
    """Return CC deed codes. Restricted codes are checked before CC BY."""

    folded = _normalize_deed(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _normalize_deed(value: str) -> str:
    text = unescape(value).casefold()
    return (
        text.replace("\\/", "/")
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
