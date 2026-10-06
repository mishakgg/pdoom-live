"""Metadata catalog of public Data & Society pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, quotes, and chart data are not stored. A missing date
stays unknown. Updated, modified, and copyright years are not publication
dates. Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA,
which are labeled creative_commons. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A restricted deed wins when it appears beside a
permissive one. uk_ogl is used only when the page states the Open Government
Licence. us_government_work is used only when a rights field says the item is
a US government work. A public page, a copyright notice, or a terms link is
not a licence. This module does not fetch. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "datasociety_pages"
CATALOG_FILENAME = "datasociety_pages.json"
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
OFFICIAL_HOST = "datasociety.net"
PUBLISHER = "Data & Society"
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4})[-/](\d{2})[-/](\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_RIGHTS = re.compile(
    r'"(?:license|rights)"\s*:\s*"((?:\\.|[^"\\])*)"',
    re.IGNORECASE,
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_RIGHTS_META = frozenset(
    {
        "rights",
        "dc.rights",
        "dcterms.rights",
        "license",
        "dc.license",
        "dcterms.license",
    }
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "citation_date",
    "dcterms.issued",
    "dcterms.created",
    "dc.date",
    "dc.date.issued",
)
_RIGHTS_DD = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_SITE_SUFFIXES = (
    " | Data & Society",
    " - Data & Society",
    " – Data & Society",
    " — Data & Society",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_TITLE_CHALLENGES = (
    "just a moment",
    "attention required",
    "access denied",
    "are you a robot",
    "verify you are human",
    "please wait while your request is being verified",
    "robot check",
    "checking your browser",
)
_RAW_CHALLENGES = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "sg-captcha",
    "sgcaptcha",
    "errors.edgesuite.net",
    "akamai-ghost",
)
_BLOCKED_PREFIXES = (
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
    "/xmlrpc.php",
    "/cgi-bin",
    "/cdn-cgi",
    "/feed",
    "/es",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".epub",
    ".mp3",
    ".mp4",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".gz",
    ".tgz",
    ".tar",
)
# Longer restricted deeds are listed first. A hyphen is a word boundary, so
# "CC BY" must not match "CC BY-NC", and a licenses/ URL must name one deed.
_RESTRICTED_DEEDS = (
    re.compile(r"creativecommons\.org/licenses/by-nc-sa(?:/|\b)"),
    re.compile(r"creativecommons\.org/licenses/by-nc-nd(?:/|\b)"),
    re.compile(r"creativecommons\.org/licenses/by-nc(?:/|\b)"),
    re.compile(r"creativecommons\.org/licenses/by-nd(?:/|\b)"),
    re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"),
    re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"),
    re.compile(r"\bcc[\s-]*by[\s-]*nc\b"),
    re.compile(r"\bcc[\s-]*by[\s-]*nd\b"),
    re.compile(r"attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    re.compile(r"attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    re.compile(r"attribution[\s-]+non[\s-]*commercial\b"),
    re.compile(r"attribution[\s-]+no[\s-]*deriv"),
)
_PERMISSIVE_DEEDS = (
    re.compile(r"creativecommons\.org/publicdomain/zero(?:/|\b)"),
    re.compile(r"creativecommons\.org/licenses/by-sa(?:/|\b)"),
    re.compile(r"creativecommons\.org/licenses/by/(?:\d|\b)"),
    re.compile(r"\bcc[\s-]*0\b"),
    re.compile(r"\bcc[\s-]*zero\b"),
    re.compile(r"creative commons(?:\s+public\s+domain)?[\s-]+zero\b"),
    re.compile(r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)"),
    re.compile(r"attribution[\s-]+share[\s-]*alike\b"),
    re.compile(r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"),
    re.compile(r"creative commons[\s-]+attribution\b(?![\s-]*(?:non|no[\s-]*deriv|share))"),
)
_PUBLIC_DOMAIN_MARK = (
    re.compile(r"creativecommons\.org/publicdomain/mark(?:/|\b)"),
    re.compile(r"public[\s-]+domain[\s-]+mark\b"),
)
_OGL = re.compile(
    r"open government licence\b|nationalarchives\.gov\.uk/doc/open-government-licence(?:/|$)"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Data & Society page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_datasociety_host(hostname: str) -> bool:
    """True only for the official datasociety.net host."""
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
    head = page_html[:15000].casefold()
    title = ""
    match = _TITLE.search(head)
    if match:
        title = _clean_text(match.group(1)).casefold()
    if any(marker in title for marker in _TITLE_CHALLENGES):
        return True
    return any(marker in head for marker in _RAW_CHALLENGES)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML on datasociety.net that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html) or _challenge_headers(headers):
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
    headers: Mapping[str, str] | None = None,
) -> dict | None:
    """Return metadata when one response is the page HTML.

    HTTP 202, a non-HTML body, a challenge interstitial, and a URL that is not
    on datasociety.net are not stored.
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
    """Return a rights label stated by the page.

    creative_commons means CC0, CC BY, or CC BY-SA. Longer restricted deeds
    are checked first, so CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND
    stay unknown, including when a permissive deed appears beside them. A
    public-domain mark is not CC0. uk_ogl requires the Open Government
    Licence. us_government_work requires a rights field. A public page, a
    copyright notice, and a terms link are not licences.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    fields = _normalize_licence_text(_rights_field_text(page_text))
    corpus = _normalize_licence_text(_rights_corpus(page_text))
    if _states_us_government_work(fields) and not _has_restricted(fields):
        return RIGHTS_US_GOVERNMENT_WORK
    if _has_restricted(corpus):
        return RIGHTS_UNKNOWN
    if _has_permissive(corpus):
        return RIGHTS_CREATIVE_COMMONS
    if _OGL.search(corpus):
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years do not count."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    metas = _metas(page_text)
    for key in _PUBLICATION_DATE_KEYS:
        found = _normalize_date(metas.get(key, ""))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    for match in _H1.finditer(visible):
        title = _clean_title(match.group(1))
        if _usable_title(title):
            return title
    metas = _metas(visible)
    for key in ("citation_title", "og:title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
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
    metas = _metas(_without_hidden(page_html))
    for key in ("og:site_name", "citation_publisher"):
        if _clean_text(metas.get(key, "")) == PUBLISHER:
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the URL
    that returned HTML. A rel=canonical on another path is not substituted.
    A challenge page is not stored.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    return page_record(page_html, page_url=page_url)


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_absolute_https(live, href))
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
    if description != description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if "p(doom)" in description.casefold():
        raise CatalogError("description must not store a p(doom) figure")
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
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    if "p(doom)" in entry["title"].casefold():
        raise CatalogError("title must not store a p(doom) figure")
    return entry


def validate_canonical_url(url: object) -> str:
    parsed = _parse_https_url(url)
    if parsed is None:
        raise CatalogError("canonical URL must be an https datasociety.net page")
    host, path = parsed
    if not official_datasociety_host(host) or not _html_path(path):
        raise CatalogError(f"canonical URL must be an https datasociety.net page: {url}")
    return str(url)


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _parse_https_url(url: object) -> tuple[str, str] | None:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        return None
    if not url.startswith("https://"):
        return None
    rest = url[len("https://") :]
    if not rest or any(char in rest for char in ("@", "?", "#")):
        return None
    slash = rest.find("/")
    if slash == -1:
        host, path = rest, "/"
    else:
        host, path = rest[:slash], rest[slash:]
    if not host or ":" in host:
        return None
    hostname = host.lower().rstrip(".")
    if not hostname or ".." in hostname:
        return None
    return hostname, path


def _html_path(path: str) -> bool:
    if not path.startswith("/") or ".." in path or "\\" in path or "//" in path or "%" in path:
        return False
    bare = path[:-1] if path != "/" and path.endswith("/") else path
    lowered = bare.casefold()
    if lowered in {"", "/"}:
        return False
    if lowered.endswith(_DOWNLOAD_SUFFIXES) or lowered.endswith("/feed"):
        return False
    for prefix in _BLOCKED_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "/"):
            return False
    return True


def _absolute_https(base: str, href: str) -> str:
    value = unescape(href).strip()
    if value.startswith("https://") or value.startswith("http://"):
        return value
    parsed = _parse_https_url(base)
    if parsed is None:
        return value
    host, path = parsed
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("/"):
        return f"https://{host}{value}"
    parent = path.rsplit("/", 1)[0]
    return f"https://{host}{parent}/{value}"


def _same_page(left: str, right: str) -> bool:
    a = _parse_https_url(left)
    b = _parse_https_url(right)
    if a is None or b is None:
        return False
    return a[0] == b[0] and a[1].rstrip("/") == b[1].rstrip("/")


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value:
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


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
            return True
    return False


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() != PUBLISHER.casefold()


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found[key.casefold()] = unescape(double or single or bare).strip()
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _rights_corpus(page_html: str) -> str:
    parts = [_rights_field_text(page_html), _plain(_without_hidden(page_html))]
    visible = _without_hidden(page_html)
    for tag in _ANCHOR.findall(visible) + _LINK.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            parts.append(href)
    return "\n".join(parts)


def _rights_field_text(page_html: str) -> str:
    parts: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_RIGHTS.findall(blob):
            parts.append(raw.replace("\\/", "/"))
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for name in _RIGHTS_META:
        if metas.get(name):
            parts.append(metas[name])
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel and attrs.get("href"):
            parts.append(attrs["href"])
    for block in _RIGHTS_DD.findall(visible):
        parts.append(_plain(block))
    return "\n".join(parts)


def _normalize_licence_text(value: str) -> str:
    text = unescape(value).casefold().replace("\xa0", " ").replace("\\/", "/")
    for src in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        text = text.replace(src, "-")
    return re.sub(r"\s+", " ", text)


def _has_restricted(text: str) -> bool:
    return any(pattern.search(text) for pattern in _RESTRICTED_DEEDS)


def _has_permissive(text: str) -> bool:
    remaining = text
    for pattern in _PUBLIC_DOMAIN_MARK:
        remaining = pattern.sub(" ", remaining)
    return any(pattern.search(remaining) for pattern in _PERMISSIVE_DEEDS)


def _states_us_government_work(text: str) -> bool:
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


def _normalize_date(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    found = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    if _iso_date(found):
        return found
    return None


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
