"""Metadata catalog of public pages on the official Forethought host.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, long descriptions, chart data, and quotes are not
stored. A missing date is the string unknown. Updated, modified, and copyright
years are not publication dates. Rights stay unknown unless the page states
CC0, CC BY, or CC BY-SA. Those three are labeled creative_commons. CC BY-NC,
CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted deed wins
when it appears beside a permissive one. Longer restricted deeds are checked
first, and a hyphen is a word boundary, so CC BY does not match CC BY-NC and
a creativecommons.org/licenses/ URL does not match every deed. A public page,
a copyright notice, all rights reserved, or a terms link is not a licence.
uk_ogl is used only when the page states the Open Government Licence.
us_government_work is used only when a rights field says the item is a US
government work. The Public Domain Mark is not CC0.

The official hosts are forethought.org and www.forethought.org. A redirect
off those hosts is not stored. This module does not fetch. It is not a belief
collector, and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime, timezone
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "forethought_pages"
CATALOG_FILENAME = "forethought_pages.json"
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
OFFICIAL_HOSTS = frozenset({"forethought.org", "www.forethought.org"})
PUBLISHER = "Forethought"
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
_NEXT_DATA = re.compile(
    r"(?is)<script\b[^>]*\bid\s*=\s*['\"]__NEXT_DATA__['\"][^>]*>(.*?)</script>"
)
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_RIGHTS_DD = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_URL = re.compile(
    r"^(?P<scheme>https)://(?P<authority>[^/?#\s]+)(?P<path>/[^?#\s]*)?(?P<query>\?[^#\s]*)?(?P<fragment>#\S*)?$"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_SITE_SUFFIXES = (
    " | Forethought Research",
    " - Forethought Research",
    " – Forethought Research",
    " — Forethought Research",
    " | Forethought",
    " - Forethought",
    " – Forethought",
    " — Forethought",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".mp3",
    ".mp4",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".css",
    ".js",
    ".gz",
    ".tgz",
    ".epub",
    ".rss",
    ".atom",
)
_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "cf-mitigated",
    "sgcaptcha",
    "sg-captcha",
    "siteground captcha",
    "pardon our interruption",
    "errors.edgesuite.net",
    "akamai-ghost",
    "are you a robot",
    "verify you are human",
    "checking your browser",
    "just a moment",
    "enable javascript and cookies",
    "bot verification",
)
_CHALLENGE_TITLES = frozenset(
    {
        "just a moment...",
        "just a moment",
        "attention required! | cloudflare",
        "access denied",
        "pardon our interruption",
        "robot check",
        "are you a robot?",
        "bot verification",
        "please verify you are human",
        "one moment, please",
    }
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
# Longer restricted deeds are listed before shorter ones. A hyphen is not a
# licence boundary: CC BY must not match CC BY-NC, and licenses/by must not
# match licenses/by-nc. publicdomain/mark is not publicdomain/zero.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(zero|mark)|licenses/(by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_RESTRICTED_DEEDS = (
    re.compile(r"creative\s+commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike\b"),
    re.compile(
        r"creative\s+commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv(?:ative)?s?\b"
    ),
    re.compile(
        r"creative\s+commons\s+attribution[\s-]+non[\s-]*commercial\b(?![\s-]*(?:share|no)\b)"
    ),
    re.compile(r"creative\s+commons\s+attribution[\s-]+no[\s-]*deriv(?:ative)?s?\b"),
    re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"),
    re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"),
    re.compile(r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)"),
    re.compile(r"\bcc[\s-]*by[\s-]*nd\b"),
)
_PERMISSIVE_DEEDS = (
    re.compile(r"\bcc[\s-]*0\b"),
    re.compile(r"\bcc[\s-]*zero\b"),
    re.compile(r"creative\s+commons(?:\s+public\s+domain)?[\s-]+(?:cc[\s-]*0|zero)\b"),
    re.compile(r"creative\s+commons\s+zero\b"),
    re.compile(
        r"creative\s+commons\s+attribution[\s-]+share[\s-]*alike\b(?![\s-]*(?:non|no)\b)"
    ),
    re.compile(r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)"),
    re.compile(r"creative\s+commons\s+attribution\b(?![\s-]*(?:share|non|no)\b)"),
    re.compile(r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"),
)
_OGL = re.compile(r"\bopen government licence\b")


class CatalogError(ValueError):
    """A catalog row or page failed the Forethought page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_forethought_host(hostname: str) -> bool:
    """True for forethought.org and www.forethought.org."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
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
    title = _plain(match.group(1)).casefold()
    return title in _CHALLENGE_TITLES


def rights_from_page(page_text: str) -> str:
    """Return a rights label the page itself states.

    creative_commons means CC0, CC BY, or CC BY-SA. Restricted Creative Commons
    deeds stay unknown, including when a permissive deed appears beside them.
    Longer restricted deeds are checked first. A hyphen keeps CC BY from
    matching CC BY-NC, and a creativecommons.org/licenses/ URL does not match
    every deed. The Public Domain Mark is not CC0. uk_ogl requires the phrase
    "open government licence". us_government_work requires a rights field that
    says the item is a US government work. A public page, a copyright notice,
    all rights reserved, and a terms link are not licences. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    stated = _licence_haystack(visible)
    if _restricted_deed(stated):
        return RIGHTS_UNKNOWN
    if _rights_field_says_us_government_work(page_text):
        return RIGHTS_US_GOVERNMENT_WORK
    if _OGL.search(_plain(visible).casefold()):
        return RIGHTS_UK_OGL
    if _permissive_deed(stated):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown.

    The article publishedAt field, JSON-LD datePublished, and publication
    meta tags count. A timestamp is the UTC calendar day, so an offset just
    after local midnight does not move the date forward. updatedAt,
    createdAt, article:modified_time, og:updated_time, a last-update line,
    and a copyright year do not count. A date on a listed item is not the
    page's publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    published = _article_published_at(page_html)
    if published:
        return published
    for blob in _LDJSON.findall(page_html):
        for match in _DATE_PUBLISHED.finditer(blob):
            found = _utc_day(match.group(1))
            if found:
                return found
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        found = _utc_day(metas.get(key, ""))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    raw_title = _article_fields(page_html).get("title")
    article_title = _clean_title(raw_title) if isinstance(raw_title, str) else ""
    if article_title and article_title.casefold() != PUBLISHER.casefold():
        return article_title
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title and not _looks_like_blurb(title):
                return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title and title.casefold() != PUBLISHER.casefold():
            return title
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Forethought when the page states that name.

    A person's name is not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    site = _plain(_metas(visible).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    title_tag = _TITLE.search(visible)
    if title_tag and PUBLISHER in _plain(title_tag.group(1)):
        return PUBLISHER
    if re.search(rf"\b{re.escape(PUBLISHER)}\b", _plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed HTML page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical does not replace it. A
    challenge page is refused.
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


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: object,
    headers: Mapping[str, object] | None = None,
) -> dict | None:
    """Return metadata when a bounded GET returned on-host HTML.

    An HTTP 202 challenge, a non-HTML body, a Cloudflare, SiteGround, Akamai,
    or robot interstitial, and a URL off the official host are not stored.
    """

    if status != 200 or not isinstance(page_html, str):
        return None
    if not is_html_content_type(content_type):
        return None
    if _challenge_header(headers) or is_challenge_page(page_html):
        return None
    try:
        url = validate_canonical_url(page_url)
    except CatalogError:
        return None
    try:
        return metadata_from_page(page_html, page_url=url)
    except CatalogError:
        return None


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
        raise CatalogError("canonical URL must be an https forethought.org page")
    match = _URL.fullmatch(url)
    if match is None:
        raise CatalogError(f"canonical URL must be an https forethought.org page: {url}")
    authority = match.group("authority")
    path = match.group("path") or ""
    query = match.group("query")
    fragment = match.group("fragment")
    userinfo, host, port = _split_authority(authority)
    if (
        userinfo
        or port
        or query
        or fragment
        or not path.startswith("/")
        or not official_forethought_host(host)
        or host != host.lower()
        or host.endswith(".")
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be an https forethought.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _split_authority(authority: str) -> tuple[str, str, str]:
    if not authority or "@" in authority[:1]:
        return "invalid", "", ""
    userinfo = ""
    hostport = authority
    if "@" in authority:
        userinfo, hostport = authority.rsplit("@", 1)
    if not hostport:
        return userinfo or "invalid", "", ""
    if hostport.startswith("["):
        end = hostport.find("]")
        if end <= 1:
            return userinfo, "", ""
        host = hostport[1:end]
        rest = hostport[end + 1 :]
        if rest and not rest.startswith(":"):
            return userinfo, "", ""
        port = rest[1:] if rest.startswith(":") else ""
        return userinfo, host, port
    if hostport.count(":") > 1:
        return userinfo, "", ""
    if ":" in hostport:
        host, port = hostport.rsplit(":", 1)
        return userinfo, host, port
    return userinfo, hostport, ""


def _is_download(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


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


def _article_fields(page_html: str) -> dict:
    match = _NEXT_DATA.search(page_html)
    if match is None:
        return {}
    blob = match.group(1).strip()
    if len(blob) > 2_000_000:
        return {}
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    props = payload.get("props")
    if not isinstance(props, dict):
        return {}
    page_props = props.get("pageProps")
    if not isinstance(page_props, dict):
        return {}
    article = page_props.get("article")
    if not isinstance(article, dict):
        return {}
    fields = article.get("fields")
    if not isinstance(fields, dict):
        return {}
    return fields


def _article_published_at(page_html: str) -> str | None:
    raw = _article_fields(page_html).get("publishedAt")
    if not isinstance(raw, str):
        return None
    return _utc_day(raw)


def _looks_like_blurb(title: str) -> bool:
    """An SEO summary is not the page title."""
    if len(title) > 140 and title.count(" ") > 16:
        return True
    return title.casefold().startswith("today, ") and len(title) > 80


def _rights_field_says_us_government_work(page_html: str) -> bool:
    text = _plain(" ".join(_rights_fields(page_html))).casefold()
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


def _rights_fields(page_html: str) -> list[str]:
    fields: list[str] = []
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _RIGHTS_META:
        if metas.get(key):
            fields.append(metas[key])
    for block in _RIGHTS_DD.findall(visible):
        fields.append(_plain(block))
    for node in _jsonld_dicts(page_html):
        rights = node.get("rights")
        if isinstance(rights, str) and rights.strip():
            fields.append(rights)
    return fields


def _jsonld_dicts(page_html: str) -> list[dict]:
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for block in _LDJSON.findall(page_html):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        walk(payload)
    return found


def _licence_haystack(visible: str) -> str:
    parts = [_plain(visible).casefold()]
    for tag in _LINK.findall(visible) + _ANCHOR.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            parts.append(href.casefold())
    metas = _metas(visible)
    for key in ("dc.rights", "dcterms.rights", "rights", "license", "dc.license", "dcterms.license"):
        if metas.get(key):
            parts.append(metas[key].casefold())
    return "\n".join(parts)


def _restricted_deed(stated: str) -> bool:
    lowered = stated.casefold()
    for match in _CC_URL.finditer(lowered):
        if _url_kind(match) == "restricted":
            return True
    return any(pattern.search(lowered) for pattern in _RESTRICTED_DEEDS)


def _permissive_deed(stated: str) -> bool:
    lowered = stated.casefold()
    for match in _CC_URL.finditer(lowered):
        if _url_kind(match) == "permissive":
            return True
    return any(pattern.search(lowered) for pattern in _PERMISSIVE_DEEDS)


def _url_kind(match: re.Match[str]) -> str:
    public_domain = match.group(1)
    deed = match.group(2)
    if public_domain == "zero":
        return "permissive"
    if public_domain == "mark":
        return "mark"
    if deed in {"by-nc-nd", "by-nc-sa", "by-nc", "by-nd"}:
        return "restricted"
    if deed in {"by", "by-sa"}:
        return "permissive"
    return ""


def _challenge_header(headers: Mapping[str, object] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
            return True
    return False


def _utc_day(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if _DATE.fullmatch(text):
        return text if _iso_date(text) else None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return _iso_prefix(value)
    if parsed.tzinfo is None:
        return _iso_prefix(parsed.date().isoformat())
    try:
        utc_day = parsed.astimezone(timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None
    return utc_day if _iso_date(utc_day) else None


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _clean_title(value: str) -> str:
    text = _plain(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


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
