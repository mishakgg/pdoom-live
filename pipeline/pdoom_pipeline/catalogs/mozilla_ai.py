"""Metadata catalog of public Mozilla Foundation pages about artificial intelligence.

The host confirmed to return HTML is www.mozilla.org. foundation.mozilla.org
answers with a redirect to www.mozillafoundation.org. That redirect leaves the
official host, so it stores no row. A row is stored only from one HTML
response on www.mozilla.org. A Cloudflare challenge, a SiteGround captcha, an
HTTP 202, an Akamai interstitial, a robot check, a non-HTML response, or a
redirect off the official host stores nothing. An empty catalog is the
correct outcome when every GET is blocked.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
text, abstracts, and PDFs are not stored. A missing date stays unknown.
Updated, modified, and copyright years are not publication dates. Rights stay
unknown unless the page states CC0, CC BY, or CC BY-SA, which are labeled
creative_commons. Longer restricted deeds are checked first. A hyphen is a
word boundary, so CC BY does not match CC BY-NC, and a
creativecommons.org/licenses/ URL does not match every deed. CC BY-NC,
CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted deed wins
when it appears beside a permissive one. The Public Domain Mark is not CC0.
The Mozilla Public License is not CC BY. When the page states MPL 2.0 the
label is mpl-2.0, which is not creative_commons. A public page, a copyright
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

CATALOG_ID = "mozilla_ai_pages"
CATALOG_FILENAME = "mozilla_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_MPL = "mpl-2.0"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_MPL})
OFFICIAL_HOST = "www.mozilla.org"
PUBLISHER = "Mozilla"
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PATH = re.compile(r"^/en-US/foundation/(?:[a-z0-9-]+/)+$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " - State of Mozilla 2024",
    " — State of Mozilla 2024",
    " – State of Mozilla 2024",
    " - State of Mozilla",
    " — Mozilla",
    " – Mozilla",
    " - Mozilla",
    " | Mozilla",
)
_GENERIC_TITLES = frozenset({"mozilla", "mozilla foundation", "sending"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "cf-mitigated",
    "just a moment",
    "attention required! | cloudflare",
    "checking your browser",
    "enable javascript and cookies",
    "sgcaptcha",
    "siteground captcha",
    "errors.edgesuite.net",
    "akamai bot manager",
    "are you a robot",
    "are you human",
    "robot interstitial",
    "please verify you are a human",
)
_REDIRECT_OFF_HOST = "you should be redirected automatically"
# Longer restricted deeds are first. A hyphen is a word boundary, so these
# must be decided before CC BY. A creativecommons.org/licenses/ URL matches
# only the deed named in the path.
_RESTRICTED_DEED = re.compile(
    r"(?i)(?:"
    r"creativecommons\.org/licenses/by-nc-sa(?:/|\b)|"
    r"creativecommons\.org/licenses/by-nc-nd(?:/|\b)|"
    r"creativecommons\.org/licenses/by-nc(?:/|\b)|"
    r"creativecommons\.org/licenses/by-nd(?:/|\b)|"
    r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b|"
    r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b|"
    r"\bcc[\s-]*by[\s-]*nc\b|"
    r"\bcc[\s-]*by[\s-]*nd\b|"
    r"\bcc[\s-]*by[\s-]*non[\s-]*commercial[\s-]*(?:share[\s-]*alike|no[\s-]*deriv)|"
    r"\bcc[\s-]*by[\s-]*non[\s-]*commercial\b|"
    r"\bcc[\s-]*by[\s-]*no[\s-]*deriv|"
    r"attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike|"
    r"attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv|"
    r"attribution[\s-]*non[\s-]*commercial\b|"
    r"attribution[\s-]*no[\s-]*deriv"
    r")"
)
# CC0, CC BY, and CC BY-SA only. The Public Domain Mark is not CC0.
# `(?![\s-]*(?:nc|nd)\b)` treats a hyphen as a boundary so CC BY does not
# match CC BY-NC or CC BY-ND.
_CC0 = re.compile(
    r"(?i)(?:\bcc[\s-]*0\b|"
    r"creativecommons\.org/publicdomain/zero(?:/|\b)|"
    r"creative\s+commons(?:\s+public\s+domain)?[\s-]+(?:cc[\s-]*0|zero)\b)"
)
_CC_BY_SA = re.compile(
    r"(?i)(?:creativecommons\.org/licenses/by-sa(?:/|\b)|"
    r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)|"
    r"creative\s+commons\s+attribution[\s-]*(?:share[\s-]*alike|sa)\b"
    r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv)))"
)
_CC_BY = re.compile(
    r"(?i)(?:creativecommons\.org/licenses/by/(?:\d|\b)|"
    r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)|"
    r"creative\s+commons\s+attribution\b"
    r"(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|sa|nc|nd)\b))"
)
_MPL_2 = re.compile(
    r"(?i)(?:\bmpl[\s-]*2\.0\b|"
    r"mozilla\s+public\s+licen[cs]e\s+2\.0\b|"
    r"mozilla\.org/(?:[a-z]{2}(?:-[a-z]{2})?/)?mpl/2\.0(?:/|\b))"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Mozilla Foundation page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_mozilla_host(hostname: str) -> bool:
    """True only for www.mozilla.org, the host that returned HTML.

    foundation.mozilla.org redirects to www.mozillafoundation.org. That hop
    leaves the official host, so it is not a stored canonical host.
    """

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. A public page stays unknown.

    creative_commons is only CC0, CC BY, or CC BY-SA. Restricted deeds are
    checked first and win when a permissive deed is also present. The Public
    Domain Mark is not CC0. MPL 2.0 is mpl-2.0, not creative_commons.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    stated = _rights_blob(visible)
    if _RESTRICTED_DEED.search(stated):
        return RIGHTS_UNKNOWN
    if _CC0.search(stated) or _CC_BY_SA.search(stated) or _CC_BY.search(stated):
        return RIGHTS_CREATIVE_COMMONS
    if _MPL_2.search(stated):
        return RIGHTS_MPL
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    visible = _without_hidden(page_text)
    for raw in _meta_values(visible, _PUBLISHED_META):
        match = _DATE_PREFIX.match(raw.strip())
        if match and _iso_date(match.group(1)):
            return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    for inner in _H1.findall(visible):
        title = _clean_title(_clean_text(inner))
        if _usable_title(title):
            return title
    raw = _metas(visible).get("og:title", "")
    title = _clean_title(_clean_text(raw))
    if not _usable_title(title):
        title_tag = _TITLE.search(visible)
        title = _clean_title(_clean_text(title_tag.group(1))) if title_tag else ""
    if not _usable_title(title):
        raise CatalogError("title is required")
    return title


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    publisher = _clean_text(_metas(_without_hidden(page_html)).get("og:site_name", ""))
    if publisher != PUBLISHER:
        raise CatalogError("publisher is required")
    return publisher


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A different rel=canonical is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html) or _redirects_off_host(page_html):
        raise CatalogError("a challenge or redirect page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


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
    if any(marker in lowered for marker in _CHALLENGE_MARKERS):
        return True
    match = _TITLE.search(_without_hidden(page_html[:8000]))
    if match is None:
        return False
    title = _clean_text(match.group(1)).casefold()
    return title in {"just a moment...", "attention required! | cloudflare", "access denied"}


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> dict | None:
    """Return metadata only when the response is HTML from the official host.

    HTTP 202, a challenge, a non-HTML payload, and a redirect off
    www.mozilla.org are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not is_html_content_type(content_type):
        return None
    if not _page_url_is_official(page_url):
        return None
    if is_challenge_page(page_html) or _redirects_off_host(page_html):
        return None
    if _headers_block_storage(headers):
        return None
    return metadata_from_page(page_html, page_url=page_url)


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
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str):
        raise CatalogError("canonical URL must be an https www.mozilla.org Foundation page")
    host, path = _split_https_url(url)
    if not official_mozilla_host(host) or _PATH.fullmatch(path) is None:
        raise CatalogError(f"canonical URL must be an https www.mozilla.org Foundation page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _split_https_url(url: str) -> tuple[str, str]:
    if not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be an https www.mozilla.org Foundation page")
    if not url.startswith("https://"):
        raise CatalogError(f"canonical URL must be an https www.mozilla.org Foundation page: {url}")
    remainder = url[len("https://") :]
    if (
        not remainder
        or "@" in remainder
        or "\\" in remainder
        or "#" in remainder
        or "?" in remainder
        or "%" in remainder
    ):
        raise CatalogError(f"canonical URL must be an https www.mozilla.org Foundation page: {url}")
    if "/" in remainder:
        authority, path_rest = remainder.split("/", 1)
        path = "/" + path_rest
    else:
        authority, path = remainder, "/"
    if not authority or ":" in authority or authority.endswith(".") or ".." in path or "//" in path:
        raise CatalogError(f"canonical URL must be an https www.mozilla.org Foundation page: {url}")
    return authority.lower(), path


def _page_url_is_official(url: str) -> bool:
    try:
        host, _path = _split_https_url(url)
    except CatalogError:
        return False
    return official_mozilla_host(host)


def _redirects_off_host(page_html: str) -> bool:
    return _REDIRECT_OFF_HOST in page_html.casefold()


def _headers_block_storage(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "location" and text.startswith("http") and not _page_url_is_official(str(value).strip()):
            return True
    return False


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


def _rights_blob(visible: str) -> str:
    parts = [_plain(visible)]
    for tag in _ANCHOR.findall(visible) + _LINK.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            parts.append(href)
    for content in _meta_values(visible, _LICENSE_META):
        parts.append(content)
    return "\n".join(parts)


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(title: str) -> str:
    changed = True
    while changed and title:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
                changed = True
    return title


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    return title.casefold() not in _GENERIC_TITLES


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


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
