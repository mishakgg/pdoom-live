"""Metadata catalog of public Schwartz Reisman Institute pages.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, and quotes are not stored. A date the page does not
state stays unknown. Updated, modified, and copyright years are not
publication dates. Rights stay unknown unless the page states CC0, CC BY, or
CC BY-SA. Those three are labeled creative_commons. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted deed wins when it
appears beside a permissive one. A hyphen is a word boundary, so CC BY does
not match CC BY-NC. A creativecommons.org/licenses/ URL does not match every
deed. The Public Domain Mark is not CC0. uk_ogl is used only when the page
states the Open Government Licence. us_government_work is used only when a
rights field says the item is a US government work. A public page, a copyright
notice, All rights reserved, a terms link, and the university host are not
licences. Vector Institute and Mila pages are outside this catalog. A
challenge page or a non-HTML response is not stored. This catalog is not a
collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "sri_pages"
CATALOG_FILENAME = "sri_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_LABELS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL, RIGHTS_US_GOVERNMENT_WORK}
)
OFFICIAL_HOST = "srinstitute.utoronto.ca"
PUBLISHER = "Schwartz Reisman Institute"
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
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HTTP_URL = re.compile(
    r"(?P<scheme>https?)://"
    r"(?:(?P<userinfo>[^/?#@]+)@)?"
    r"(?P<host>\[[0-9A-Fa-f:.]+\]|[^:/?#]+)"
    r"(?::(?P<port>[0-9]+))?"
    r"(?P<path>/[^?#]*)?"
    r"(?P<query>\?[^#]*)?"
    r"(?P<fragment>#.*)?"
    r"\Z"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_RIGHTS = re.compile(r'"(?:license|rights)"\s*:\s*"((?:\\.|[^"\\])*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_HREF_TAG = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_LD_PUBLISHER_NAME = re.compile(
    r'(?is)"publisher"\s*:\s*\{[^{}]*?"name"\s*:\s*"((?:\\.|[^"\\])*)"'
)
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# Longer restricted codes are listed first. Matching is the whole path segment,
# so licenses/by does not match licenses/by-nc.
_CC_URL = re.compile(
    r"(?i)(?:https?://|//)?(?:www\.)?creativecommons\.org/"
    r"(?P<area>publicdomain|licenses)/(?P<code>[a-z0-9-]+)"
)
_RESTRICTED_DEEDS = ("by-nc-nd", "by-nc-sa", "by-nc", "by-nd")
_PERMISSIVE_DEEDS = ("by-sa", "by")
_RESTRICTED_PROSE = re.compile(
    r"(?i)(?:"
    r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
    r"|\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
    r"|\bcc[\s-]*by[\s-]*nd\b"
    r"|\bcc[\s-]*by[\s-]*nc\b"
    r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*derivatives\b"
    r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike\b"
    r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial\b"
    r"|creative\s+commons\s+attribution[\s-]*no[\s-]*derivatives\b"
    r")"
)
_PDM_PROSE = re.compile(r"(?i)\bpublic\s+domain\s+mark\b")
_PERMISSIVE_PROSE = re.compile(
    r"(?i)(?:"
    r"\bcc[\s-]*0\b"
    r"|\bcreative\s+commons\s+(?:cc[\s-]*)?zero\b"
    r"|\bcc[\s-]*by[\s-]*share[\s-]*alike\b"
    r"|\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)"
    r"|creative\s+commons\s+attribution[\s-]*share[\s-]*alike\b"
    r"|\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
    r"|creative\s+commons\s+attribution\b"
    r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*derivatives|share[\s-]*alike)\b)"
    r")"
)
_US_GOV_WORK = re.compile(
    r"(?i)(?:"
    r"\bus\s+government\s+works?\b"
    r"|\bu\.s\.\s+government\s+works?\b"
    r"|\bunited\s+states\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+united\s+states\s+government\b"
    r"|\bworks?\s+of\s+the\s+u\.s\.\s+government\b"
    r"|\bworks?\s+of\s+the\s+us\s+government\b"
    r")"
)
_US_GOV_NEGATED = re.compile(
    r"(?i)(?:"
    r"\bnot\s+(?:a\s+)?(?:us|u\.s\.|united\s+states)\s+government\s+works?\b"
    r"|\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r")"
)
_SITE_SUFFIXES = (
    " — Schwartz Reisman Institute for Technology and Society",
    " – Schwartz Reisman Institute for Technology and Society",
    " - Schwartz Reisman Institute for Technology and Society",
    " | Schwartz Reisman Institute for Technology and Society",
    " — Schwartz Reisman Institute",
    " – Schwartz Reisman Institute",
    " - Schwartz Reisman Institute",
    " | Schwartz Reisman Institute",
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
)
_BLOCKED_PREFIXES = ("/config", "/search", "/account", "/api", "/static", "/commerce")
_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "cf-mitigated",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "siteground-captcha",
    "errors.edgesuite.net",
    "akamai-ghost",
    "akamai-error",
    "akamai_error",
    "robot interstitial",
    "are you a robot",
    "please verify you are human",
    "checking your browser before accessing",
)
_CHALLENGE_TITLES = frozenset(
    {
        "just a moment...",
        "just a moment",
        "attention required! | cloudflare",
        "access denied",
        "robot check",
        "are you a human?",
    }
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
_EXCLUDED_PUBLISHERS = frozenset({"vector institute", "mila"})


class CatalogError(ValueError):
    """A catalog row or page failed the Schwartz Reisman Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_sri_host(hostname: str) -> bool:
    """True only for the official srinstitute.utoronto.ca host."""
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
    """True when the response is an interstitial rather than the institute page."""
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:12000].casefold()
    if any(marker in head for marker in _CHALLENGE_MARKERS):
        return True
    title = _TITLE.search(page_html[:12000])
    if title is None:
        return False
    text = _plain(title.group(1)).casefold()
    return text in _CHALLENGE_TITLES or text.startswith("just a moment")


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
) -> bool:
    """A row is stored only from HTML on the official host that is not a challenge.

    HTTP 202, a non-HTML body, a Cloudflare, SiteGround, or Akamai interstitial,
    a robot check, and a redirect off srinstitute.utoronto.ca are not stored.
    """
    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html) or _challenge_headers(headers):
        return False
    if hops and any(not _on_official_host(hop) for hop in hops):
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
    hops: tuple[str, ...] | list[str] | None = None,
) -> dict | None:
    """Return metadata when the response is the page HTML. Otherwise return None."""
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        hops=hops,
    ):
        return None
    assert isinstance(page_html, str)
    return page_record(page_html, page_url=page_url)


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a licence the page itself states.

    creative_commons is only CC0, CC BY, or CC BY-SA. Restricted deeds are
    checked before permissive ones and win when both appear. Anchor text does
    not override a by-nc or by-nd URL. The Public Domain Mark is not CC0.
    uk_ogl requires the phrase open government licence. us_government_work
    requires a rights field. A university host is not a licence.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    kinds: set[str] = set()
    for blob in _hrefs(visible):
        kinds.update(_deed_kinds(blob))
    rights_fields = [*_meta_rights(visible), *_ld_rights(page_text)]
    for blob in rights_fields:
        kinds.update(_deed_kinds(blob))
    plain = _plain(_without_cc_anchor_text(visible))
    kinds.update(_deed_kinds(plain))
    if "restricted" in kinds:
        return RIGHTS_UNKNOWN
    if _states_us_government_work(" ".join(rights_fields)):
        return RIGHTS_US_GOVERNMENT_WORK
    if "permissive" in kinds:
        return RIGHTS_CREATIVE_COMMONS
    if OGL_PHRASE in plain.casefold():
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
    for raw in _meta_values(_visible(page_text), _PUBLISHED_META):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if title and '"+' not in title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _clean_text(_metas(_visible(page_html)).get("og:site_name", ""))
    if _is_excluded_publisher(site):
        raise CatalogError("publisher must be the Schwartz Reisman Institute")
    if site == PUBLISHER:
        return PUBLISHER
    for match in _LD_PUBLISHER_NAME.finditer(page_html):
        name = _clean_text(match.group(1).replace("\\/", "/"))
        if _is_excluded_publisher(name):
            raise CatalogError("publisher must be the Schwartz Reisman Institute")
        if name == PUBLISHER:
            return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the URL that
    returned HTML. A different rel=canonical does not replace it.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    return {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page, or refuse a challenge page."""
    record = metadata_from_page(page_html, page_url=page_url)
    return validate_entry(record)


def confirmed_url(page_html: str, page_url: str) -> str:
    """Return the fetched URL. A rel=canonical on another path is not substituted."""
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return validate_canonical_url(page_url)


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
        raise CatalogError("canonical URL must be an https srinstitute.utoronto.ca page")
    parsed = _split_url(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https srinstitute.utoronto.ca page: {url}")
    host = parsed["host"]
    path = parsed["path"]
    if (
        parsed["scheme"] != "https"
        or parsed["userinfo"]
        or parsed["query"]
        or parsed["fragment"]
        or parsed["port"] is not None
        or host != OFFICIAL_HOST
        or not official_sri_host(host)
        or ".." in path
        or "\\" in url
        or "//" in path
        or "%" in path
        or _blocked_path(path)
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be an https srinstitute.utoronto.ca page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _split_url(url: str) -> dict[str, str | None] | None:
    match = _HTTP_URL.fullmatch(url)
    if match is None:
        return None
    host = match.group("host") or ""
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return {
        "scheme": (match.group("scheme") or "").lower(),
        "userinfo": match.group("userinfo"),
        "host": host,
        "port": match.group("port"),
        "path": match.group("path") or "",
        "query": match.group("query"),
        "fragment": match.group("fragment"),
    }


def _on_official_host(url: str) -> bool:
    parsed = _split_url(url.strip()) if isinstance(url, str) else None
    if parsed is None:
        return False
    return official_sri_host(str(parsed["host"]))


def _blocked_path(path: str) -> bool:
    lowered = path.lower()
    if lowered in {"", "/"}:
        return False
    return any(lowered == prefix or lowered.startswith(prefix + "/") for prefix in _BLOCKED_PREFIXES)


def _is_download(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
    return False


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


def _visible(page_text: str) -> str:
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


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _is_excluded_publisher(name: str) -> bool:
    return name.casefold() in _EXCLUDED_PUBLISHERS


def _without_cc_anchor_text(html: str) -> str:
    """Drop anchor text when the href is a Creative Commons deed.

    The deed is the URL. Anchor text that says CC BY on a by-nc URL does not
    reclassify that deed, and anchor text that says CC0 on a public-domain
    mark URL does not make the mark CC0.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _CC_URL.search(_normalize_licence_text(href)):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, html)


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _HREF_TAG.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _meta_rights(html: str) -> list[str]:
    return _meta_values(html, _LICENSE_META)


def _ld_rights(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_RIGHTS.findall(blob):
            found.append(raw.replace("\\/", "/").replace("\\u002f", "/"))
    return found


def _deed_kinds(blob: str) -> set[str]:
    kinds: set[str] = set()
    text = _normalize_licence_text(blob)

    def replace(match: re.Match[str]) -> str:
        kind = _url_kind(match.group("area"), match.group("code"))
        if kind:
            kinds.add(kind)
        return " "

    stripped = _CC_URL.sub(replace, text)
    if _RESTRICTED_PROSE.search(stripped):
        kinds.add("restricted")
    if _PDM_PROSE.search(stripped):
        kinds.add("pdm")
    if _PERMISSIVE_PROSE.search(stripped):
        kinds.add("permissive")
    return kinds


def _url_kind(area: str, code: str) -> str | None:
    area_name = area.casefold()
    deed = code.casefold()
    if area_name == "licenses":
        for restricted in _RESTRICTED_DEEDS:
            if deed == restricted:
                return "restricted"
        for permissive in _PERMISSIVE_DEEDS:
            if deed == permissive:
                return "permissive"
        return None
    if area_name == "publicdomain" and deed == "zero":
        return "permissive"
    if area_name == "publicdomain" and deed == "mark":
        return "pdm"
    return None


def _states_us_government_work(value: str) -> bool:
    text = _normalize_licence_text(value)
    if not text or _US_GOV_NEGATED.search(text):
        return False
    return _US_GOV_WORK.search(text) is not None


def _normalize_licence_text(value: str) -> str:
    return unescape(value).replace("\\/", "/").translate(_DASHES)


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
