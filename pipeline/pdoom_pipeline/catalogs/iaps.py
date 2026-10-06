"""Metadata catalog of public Institute for AI Policy and Strategy pages.

The canonical host is www.iaps.ai. The apex iaps.ai answers robots.txt and then
redirects HTML pages to www.iaps.ai, which is the host named by rel=canonical,
og:url, and the sitemap. A row is stored only when one bounded GET stays on
www.iaps.ai and returns HTML. A Cloudflare challenge, a SiteGround captcha, an
HTTP 202 challenge, an Akamai interstitial, a robot check, a non-HTML response,
or a redirect off www.iaps.ai is not stored. A confirming GET is limited to
1000000 bytes, 15 seconds, and 3 redirects. An empty entry list is valid.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, chart data, and quotes are not stored. A date the
page does not state stays unknown. Updated, modified, and copyright years are
not publication dates. ``creative_commons`` means only CC0, CC BY, or CC BY-SA.
CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted
deed wins when it appears beside a permissive one. A hyphen is a word
boundary, so CC BY does not match CC BY-NC, and a creativecommons.org/licenses/
URL does not match every deed. Longer restricted deeds are checked first. The
Public Domain Mark is not CC0. ``uk_ogl`` is used only when the page states
the Open Government Licence. ``us_government_work`` is used only when a rights
field says the item is a US government work. A public page, a copyright
notice, All rights reserved, or a terms link is not a licence. This catalog
is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "iaps_pages"
CATALOG_FILENAME = "iaps_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_LABELS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL, RIGHTS_US_GOVERNMENT_WORK}
)
OFFICIAL_HOST = "www.iaps.ai"
PUBLISHER = "Institute for AI Policy and Strategy"
MAX_RESPONSE_BYTES = 1_000_000
FETCH_TIMEOUT_SECONDS = 15
MAX_REDIRECTS = 3
OGL_PHRASE = "open government licence"
CATALOG_DESCRIPTION = (
    "Metadata for public Institute for AI Policy and Strategy pages on www.iaps.ai. "
    "The apex iaps.ai redirects there; a redirect off www.iaps.ai is not stored. "
    "Each row was confirmed with one bounded GET that returned HTML. "
    "Rows store the title, publisher, canonical URL, date, and rights. "
    "Page bodies, abstracts, PDFs, chart data, and quotes are not stored. "
    "A missing date is unknown. Updated, modified, and copyright years are not publication dates. "
    "creative_commons means only CC0, CC BY, or CC BY-SA. Restricted deeds stay unknown. "
    "uk_ogl is used only when the page states the Open Government Licence. "
    "us_government_work is used only when a rights field says the item is a US government work. "
    "A public page is not a licence. Tag and category indexes are not listed. runner_wired is false."
)
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
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_HREF_TAG = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RIGHTS_CELL = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_LICENSE_META = frozenset(
    {"license", "dc.license", "dcterms.license", "rights", "dc.rights", "dcterms.rights"}
)
_PUBLISHED_META = frozenset(
    {"article:published_time", "citation_publication_date", "datepublished", "dcterms.issued"}
)
_SITE_SUFFIX = re.compile(
    r"(?i)\s*(?:\||[-–—])\s*Institute for AI Policy and Strategy\s*$"
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
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
    ".epub",
)
_BLOCKED_PREFIXES = ("/config", "/search", "/account", "/api", "/static", "/commerce", "/404")
_PATH = re.compile(r"/[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*/?")
_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "cf-mitigated",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "errors.edgesuite.net",
    "akamai-ghost",
    "akamaighost",
    "please verify you are a human",
    "are you a robot",
    "robot interstitial",
    "performing security verification",
)
_CHALLENGE_TITLES = (
    "just a moment...",
    "just a moment",
    "attention required! | cloudflare",
    "attention required!",
    "bot verification",
    "please wait while your request is being verified",
)
_DASHES = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# Longer restricted deeds are listed before shorter ones. A hyphen is a word
# boundary, so these patterns require the NC or ND token itself and do not
# treat every creativecommons.org/licenses/ URL as CC BY.
_RESTRICTED_DEED = re.compile(
    r"(?:"
    r"creativecommons\.org/licenses/by-nc-nd(?:/|\b)"
    r"|creativecommons\.org/licenses/by-nc-sa(?:/|\b)"
    r"|creativecommons\.org/licenses/by-nc(?:/|\b)"
    r"|creativecommons\.org/licenses/by-nd(?:/|\b)"
    r"|\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
    r"|\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
    r"|\bcc[\s-]*by[\s-]*nc\b"
    r"|\bcc[\s-]*by[\s-]*nd\b"
    r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike\b"
    r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv(?:ative)?s?\b"
    r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial\b"
    r"|creative\s+commons\s+attribution[\s-]*no[\s-]*deriv(?:ative)?s?\b"
    r"|attribution[\s-]*non[\s-]*commercial\b"
    r"|attribution[\s-]*no[\s-]*deriv(?:ative)?s?\b"
    r")"
)
# CC BY uses a negative lookahead so the token inside CC BY-NC does not match.
# licenses/by/ requires the slash that separates the deed from its version.
_PERMITTED_DEED = re.compile(
    r"(?:"
    r"creativecommons\.org/publicdomain/zero(?:/|\b)"
    r"|creativecommons\.org/licenses/by-sa(?:/|\b)"
    r"|creativecommons\.org/licenses/by/(?:\d|\b)"
    r"|\bcc[\s-]*0\b"
    r"|creative\s+commons\s+(?:cc[\s-]*)?(?:0|zero)\b"
    r"|\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)"
    r"|\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
    r"|creative\s+commons\s+attribution[\s-]*share[\s-]*alike\b"
    r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv))"
    r"|creative\s+commons\s+attribution\b"
    r"(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv))"
    r")"
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
    """A catalog row or page failed the Institute for AI Policy and Strategy page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_iaps_host(hostname: str) -> bool:
    """True only for the canonical www.iaps.ai host."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str, headers: Mapping[str, str] | None = None) -> bool:
    """True for an interstitial challenge rather than the institute page."""

    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            text = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in text:
                return True
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:12000].casefold()
    if any(marker in head for marker in _CHALLENGE_MARKERS):
        return True
    match = _TITLE.search(page_html[:8000])
    if match is None:
        return False
    title = _plain(match.group(1)).casefold()
    return title in _CHALLENGE_TITLES


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that stayed on www.iaps.ai."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html, headers):
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
    """Return metadata when the response is institute HTML.

    A challenge page, an HTTP 202 response, a non-HTML body, or a URL that is
    not on www.iaps.ai is not stored.
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
    """Return a rights label stated by the page, or unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA. Restricted deeds
    stay unknown and win when a permissive deed is also present. The Public
    Domain Mark is not CC0. ``uk_ogl`` requires the phrase "open government
    licence". ``us_government_work`` requires a rights field that says the
    item is a US government work.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    evidence = _licence_evidence(page_text)
    if _RESTRICTED_DEED.search(evidence):
        return RIGHTS_UNKNOWN
    if _PERMITTED_DEED.search(evidence):
        return RIGHTS_CREATIVE_COMMONS
    rights_fields = _rights_field_text(page_text)
    if rights_fields and not _NEGATED_GOV_WORK.search(rights_fields) and _GOV_WORK.search(rights_fields):
        return RIGHTS_US_GOVERNMENT_WORK
    visible = _normalize(_plain(_without_hidden(page_text)))
    if OGL_PHRASE in visible or OGL_PHRASE in rights_fields:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    for raw in _meta_values(page_text, _PUBLISHED_META):
        found = _iso_prefix(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for headline in _jsonld_strings(page_html, "headline"):
        title = _clean_title(headline)
        if _usable_title(title):
            return title
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(heading.group(1))
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
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:site_name", "citation_publisher"):
        publisher = _clean_text(metas.get(key, ""))
        if publisher == PUBLISHER:
            return PUBLISHER
    for name in _jsonld_strings(page_html, "name"):
        if _clean_text(name) == PUBLISHER:
            return PUBLISHER
    title_bits = " ".join(
        (
            metas.get("og:title", ""),
            _TITLE.search(visible).group(1) if _TITLE.search(visible) else "",
        )
    )
    if PUBLISHER in _clean_text(title_bits):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": date_from_page(page_html),
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
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(ch.isspace() for ch in url):
        raise CatalogError("canonical URL must be an https www.iaps.ai page")
    parsed = _parse_https(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https www.iaps.ai page: {url}")
    host, port, path = parsed
    lowered = path.casefold()
    if (
        port is not None
        or not official_iaps_host(host)
        or host != OFFICIAL_HOST
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or "+" in path
        or not _html_path(path)
        or lowered.endswith(_DOWNLOAD_SUFFIXES)
        or _blocked_prefix(lowered)
        or "/tag/" in lowered
        or "/category/" in lowered
    ):
        raise CatalogError(f"canonical URL must be an https www.iaps.ai page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _parse_https(url: str) -> tuple[str, str | None, str] | None:
    if not url.startswith("https://"):
        return None
    rest = url[len("https://") :]
    if not rest or any(mark in rest for mark in "?#@"):
        return None
    if "/" in rest:
        authority, path_rest = rest.split("/", 1)
        path = "/" + path_rest
    else:
        authority = rest
        path = "/"
    if not authority or ":" in authority[1:] and authority.count(":") != 1:
        return None
    port: str | None = None
    if ":" in authority:
        host, port = authority.rsplit(":", 1)
        if not port.isdigit():
            return None
    else:
        host = authority
    if not host or host.endswith(".") or host.startswith("."):
        return None
    return host.casefold(), port, path


def _html_path(path: str) -> bool:
    if path == "/":
        return True
    return _PATH.fullmatch(path) is not None


def _blocked_prefix(path: str) -> bool:
    for prefix in _BLOCKED_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value or "://" in value:
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


def _licence_evidence(page_text: str) -> str:
    parts = list(_jsonld_strings(page_text, "license"))
    visible = _without_hidden(page_text)
    parts.append(_plain(visible))
    for tag in _HREF_TAG.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            parts.append(href)
    parts.extend(_meta_values(visible, _LICENSE_META))
    return _normalize("\n".join(parts))


def _rights_field_text(page_text: str) -> str:
    parts: list[str] = []
    visible = _without_hidden(page_text)
    parts.extend(_meta_values(visible, _LICENSE_META))
    for tag in _HREF_TAG.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel and attrs.get("href"):
            parts.append(attrs["href"])
    for cell in _RIGHTS_CELL.findall(visible):
        parts.append(_plain(cell))
    parts.extend(_jsonld_strings(page_text, "license"))
    parts.extend(_jsonld_strings(page_text, "rights"))
    return _normalize("\n".join(parts))


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize(value: str) -> str:
    return _plain(value).translate(_DASHES).casefold()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        match = _SITE_SUFFIX.search(text)
        if match:
            text = text[: match.start()].strip()
            changed = True
    return text


def _usable_title(title: str) -> bool:
    if not title or len(title) > MAX_FIELD_CHARS or "<" in title or ">" in title or "://" in title:
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
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _jsonld_strings(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    wanted = key.casefold()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for name, value in node.items():
                if str(name).casefold() == wanted:
                    found.extend(_text_values(value))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for blob in _LDJSON.findall(page_html):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        walk(data)
    return found


def _text_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        for key in ("name", "url", "@id"):
            item = value.get(key)
            if isinstance(item, str):
                return [item]
        return []
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(_text_values(item))
        return found
    return []


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
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
