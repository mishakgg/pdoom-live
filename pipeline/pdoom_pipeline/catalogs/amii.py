"""Metadata catalog of public Alberta Machine Intelligence Institute pages.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, and quotes are not stored. A date the page does not
state stays unknown. Updated, modified, and copyright years are not
publication dates. Rights stay unknown unless the page states CC0, CC BY, or
CC BY-SA. Those three are ``creative_commons``. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted deed wins when it
appears beside a permissive one. A hyphen is a word boundary, so CC BY does
not match CC BY-NC. ``uk_ogl`` is used only when the page states the Open
Government Licence. ``us_government_work`` is used only when a rights field
says the item is a US government work. Mila and the Vector Institute are not
catalogued. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "amii_pages"
CATALOG_FILENAME = "amii_pages.json"
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
OFFICIAL_HOSTS = frozenset({"amii.ca", "www.amii.ca"})
PUBLISHER = "Alberta Machine Intelligence Institute"
OGL_PHRASE = "open government licence"
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_RIGHTS = re.compile(r'"(?:license|rights)"\s*:\s*"((?:\\.|[^"\\])*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RIGHTS_DD = re.compile(r"(?is)<dt\b[^>]*>\s*Rights\s*</dt>\s*<dd\b[^>]*>(.*?)</dd>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_URL = re.compile(
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*)://"
    r"(?:(?P<userinfo>[^/@\s]+)@)?"
    r"(?P<host>\[[^\]]+\]|[^/:@\s]+)"
    r"(?::(?P<port>\d+))?"
    r"(?P<path>/[^?#\s]*)?"
    r"(?P<query>\?[^#\s]*)?"
    r"(?P<fragment>#[^\s]*)?"
    r"$"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "citation_date",
    "dcterms.issued",
    "dc.date.issued",
    "dcterms.created",
)
_RIGHTS_META = frozenset(
    {
        "dc.rights",
        "dcterms.license",
        "dcterms.rights",
        "license",
        "licence",
        "rights",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_SITE_SUFFIXES = (
    " — Alberta Machine Intelligence Institute",
    " – Alberta Machine Intelligence Institute",
    " - Alberta Machine Intelligence Institute",
    " | Alberta Machine Intelligence Institute",
    " — Amii",
    " – Amii",
    " | Amii",
    " - Amii",
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
    ".svg",
    ".mp3",
    ".mp4",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".gz",
    ".tgz",
    ".tar",
    ".epub",
    ".css",
    ".js",
    ".ico",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "cf-mitigated",
    "just a moment",
    "checking your browser",
    "enable javascript and cookies",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "siteground captcha",
    "akamaighost",
    "akamai bot",
    "errors.edgesuite.net",
    "pardon our interruption",
    "are you a robot",
    "verify you are human",
    "robot check",
    "robot interstitial",
)
_CHALLENGE_TITLES = frozenset(
    {
        "just a moment...",
        "attention required! | cloudflare",
        "access denied",
        "robot check",
    }
)
# Longer restricted deeds are listed first. A hyphen is a word boundary, so
# "by" must not match "by-nc". A creativecommons.org/licenses/ URL matches one
# deed, not every deed. publicdomain/mark is not CC0.
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<deed>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?![\w-]))"
)
_TEXT_DEEDS = (
    (
        "by-nc-nd",
        re.compile(
            r"(?i)\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
            r"|creative\s+commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?i)\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
            r"|creative\s+commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"(?i)\bcc[\s-]*by[\s-]*nc\b"
            r"|creative\s+commons\s+attribution[\s-]+non[\s-]*commercial\b"
        ),
    ),
    (
        "by-nd",
        re.compile(
            r"(?i)\bcc[\s-]*by[\s-]*nd\b"
            r"|creative\s+commons\s+attribution[\s-]+no[\s-]*deriv"
        ),
    ),
    ("mark", re.compile(r"(?i)\bpublic[\s-]+domain[\s-]+mark\b")),
    (
        "by-sa",
        re.compile(
            r"(?i)\bcc[\s-]*by[\s-]*sa\b"
            r"|creative\s+commons\s+attribution[\s-]+share[\s-]*alike\b"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?i)\bcc[\s-]*0\b"
            r"|\bcreative\s+commons\s+(?:cc[\s-]*)?zero\b"
            r"|\bcreative\s+commons\s+cc0\b"
        ),
    ),
    (
        "by",
        re.compile(
            r"(?i)\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
            r"|creative\s+commons\s+attribution\b"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike)\b)"
        ),
    ),
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Alberta Machine Intelligence Institute rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_amii_host(hostname: str) -> bool:
    """True only for amii.ca and www.amii.ca.

    Mila, the Vector Institute, and other hosts are not the official host.
    """

    host = (hostname or "").strip().lower()
    if not host or host.endswith(".") or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True for a Cloudflare, SiteGround, Akamai, or robot interstitial."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:12000].casefold()
    if any(marker in head for marker in _CHALLENGE_MARKERS):
        return True
    match = _TITLE.search(_visible(page_html[:12000]))
    if match is None:
        return False
    return _clean_text(match.group(1)).casefold() in _CHALLENGE_TITLES


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A row requires one HTML response from the official host.

    HTTP 202, a non-HTML body, a challenge page, and a URL on another host
    are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if _challenge_headers(headers):
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
    """Return metadata when the response is official-host HTML.

    A challenge, an HTTP 202, a non-HTML body, or an off-host URL stores no row.
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
    """Return a rights label from a licence the page itself states.

    ``creative_commons`` means only CC0, CC BY, or CC BY-SA. Longer restricted
    deeds are checked first, and any one of them keeps the label unknown even
    when a permissive deed is also present. The Public Domain Mark is not CC0.
    A public page, a copyright notice, All rights reserved, and a terms link
    are not licences. ``uk_ogl`` requires the phrase "open government licence".
    ``us_government_work`` requires a rights field that says the item is a US
    government work. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    plain = _plain(visible)
    blobs = [plain]
    blobs.extend(_hrefs(visible))
    rights_fields = _rights_fields(page_text, visible)
    blobs.extend(rights_fields)
    deeds = _cc_deeds("\n".join(blobs))
    if deeds & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if deeds & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    if OGL_PHRASE in plain.casefold() or any(OGL_PHRASE in item.casefold() for item in rights_fields):
        return RIGHTS_UK_OGL
    if _states_us_government_work("\n".join(rights_fields)):
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            found = _iso_prefix(match.group(1))
            if found:
                return found
    visible = _visible(page_text)
    for raw in _meta_values(visible, _PUBLICATION_DATE_KEYS):
        found = _iso_prefix(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
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
    """Return the institute when the page names it. A person is not the publisher."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    site = _clean_text(metas.get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    for key in ("og:title", "citation_publisher"):
        if PUBLISHER in _clean_text(metas.get(key, "")):
            return PUBLISHER
    title_tag = _TITLE.search(visible)
    if title_tag and PUBLISHER in _clean_text(title_tag.group(1)):
        return PUBLISHER
    if re.search(rf"\b{re.escape(PUBLISHER)}\b", _plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the URL
    that returned HTML. A different rel=canonical does not replace it. A
    challenge page is not stored.
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


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(_visible(page_html))
    if not href:
        return live
    try:
        declared = validate_canonical_url(_urljoin(live, href))
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
    if not isinstance(description, str) or not description.strip() or description != description.strip():
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
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be an https amii.ca page")
    if "%" in url:
        raise CatalogError(f"canonical URL must be an https amii.ca page: {url}")
    parsed = _parse_https_url(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https amii.ca page: {url}")
    host = parsed["host"]
    path = parsed["path"]
    if (
        parsed["scheme"] != "https"
        or parsed["userinfo"]
        or parsed["query"]
        or parsed["fragment"]
        or parsed["port"] is not None
        or host != host.lower()
        or not official_amii_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be an https amii.ca page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_prefix(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


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


def _parse_https_url(url: str) -> dict | None:
    match = _URL.fullmatch(url)
    if match is None:
        return None
    host = match.group("host") or ""
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return {
        "scheme": (match.group("scheme") or "").lower(),
        "userinfo": match.group("userinfo") or "",
        "host": host,
        "port": match.group("port"),
        "path": match.group("path") or "",
        "query": match.group("query") or "",
        "fragment": match.group("fragment") or "",
    }


def _same_page(left: str, right: str) -> bool:
    a = _parse_https_url(left)
    b = _parse_https_url(right)
    if a is None or b is None:
        return False
    return a["host"].lower() == b["host"].lower() and a["path"].rstrip("/") == b["path"].rstrip("/")


def _urljoin(base: str, href: str) -> str:
    href = unescape(href).strip()
    if re.match(r"(?i)[a-z][a-z0-9+.-]*://", href) or href.startswith("//"):
        if href.startswith("//"):
            return "https:" + href
        return href
    parsed = _parse_https_url(base)
    if parsed is None:
        return href
    if href.startswith("/") or href.startswith("?") or href.startswith("#"):
        return f"https://{parsed['host']}{href}"
    parent = parsed["path"] or "/"
    if not parent.endswith("/"):
        parent = parent.rsplit("/", 1)[0] + "/"
    return f"https://{parsed['host']}{_collapse_path(parent + href)}"


def _collapse_path(path: str) -> str:
    query = ""
    fragment = ""
    if "#" in path:
        path, fragment = path.split("#", 1)
        fragment = "#" + fragment
    if "?" in path:
        path, query = path.split("?", 1)
        query = "?" + query
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    collapsed = "/" + "/".join(parts)
    return collapsed + query + fragment


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


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
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() != PUBLISHER.casefold()


def _is_download(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


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


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINK.findall(page_html) + _ANCHOR.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _rights_fields(page_html: str, visible: str) -> list[str]:
    fields: list[str] = []
    for name, content in _metas(visible).items():
        if name in _RIGHTS_META and content:
            fields.append(content)
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel or "licence" in rel:
            if attrs.get("href"):
                fields.append(attrs["href"])
    for block in _RIGHTS_DD.findall(visible):
        text = _plain(block)
        if text:
            fields.append(text)
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_RIGHTS.findall(blob):
            fields.append(raw.replace("\\/", "/"))
    return fields


def _cc_deeds(text: str) -> set[str]:
    found: set[str] = set()

    def take_url(match: re.Match[str]) -> str:
        public_domain = match.group("pd")
        deed = match.group("deed")
        if public_domain:
            found.add("zero" if public_domain.casefold() == "zero" else "mark")
        elif deed:
            found.add(deed.casefold())
        return " "

    scrubbed = _CC_URL.sub(take_url, text)
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(scrubbed):
            found.add(code)
            scrubbed = pattern.sub(" ", scrubbed)
    return found


def _states_us_government_work(text: str) -> bool:
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
            return True
    return False


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
        date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return match.group(1)
