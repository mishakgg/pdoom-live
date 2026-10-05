"""Metadata catalog of public pages on the official host ought.org.

Each stored URL was confirmed with one bounded GET that returned HTML. A row
keeps the title, publisher, canonical URL, date, and rights label. Page bodies,
abstracts, PDFs, and quotes are not stored. A date the page does not state
stays unknown. Updated, modified, and copyright years are not publication
dates. Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA.
Those three are labeled creative_commons. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A restricted deed wins when it appears beside a
permissive one. A hyphen is a word boundary, so CC BY does not match CC BY-NC,
and a creativecommons.org/licenses/ URL does not match every deed. Longer
restricted deeds are checked first. A public page, a copyright notice, All
rights reserved, and a terms link are not licences. The Public Domain Mark is
not CC0. A Cloudflare challenge, a SiteGround captcha, an HTTP 202, an Akamai
interstitial, a robot check, a non-HTML response, or a redirect off ought.org
stores no row. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "ought_pages"
CATALOG_FILENAME = "ought_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "ought.org"
PUBLISHER = "Ought"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 20


def fetch_bounds() -> tuple[int, int, int]:
    """Return the confirming GET limits: timeout seconds, redirects, and bytes."""

    return (TIMEOUT_SECONDS, MAX_REDIRECTS, MAX_RESPONSE_BYTES)


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
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PATH = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$|^/$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>")
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_BLOG_DATE = re.compile(
    r"(?is)<span\b[^>]*class\s*=\s*['\"][^'\"]*\bBlogPostPage-Date\b[^'\"]*['\"][^>]*>(.*?)</span>"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s+(?:\||–|—|-)\s+Ought\s*$")
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
_MONTH = r"January|February|March|April|May|June|July|August|September|October|November|December"
_EXCLUDED_DATE = re.compile(r"(?i)\b(?:updated|modified|modification|copyright)\b|©")
_MDY = re.compile(rf"(?i)^({_MONTH})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})$")
_DMY = re.compile(rf"(?i)^(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH}),?\s+(\d{{4}})$")
_LABELED_PUBLISHED = re.compile(
    rf"(?i)\b(?:date published|published on|published)\b\s*[:\-]?\s*"
    rf"(?:(\d{{4}}-\d{{2}}-\d{{2}})|(({_MONTH})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}}))|((\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH}),?\s+(\d{{4}})))"
)
# Longer restricted deeds are listed before shorter ones. A hyphen is a word
# boundary, so these must be recognized before CC BY or a licenses/by URL.
_RESTRICTED_DEED = re.compile(
    r"(?i)"
    r"creativecommons\.org/licenses/by-(?:nc-sa|nc-nd|nc|nd)(?:/|$)"
    r"|\bcc[\s-]*by[\s-]*(?:nc[\s-]*sa|nc[\s-]*nd|nc|nd)\b"
    r"|\bcreative\s+commons\s+attribution[\s-]*(?:non[\s-]*commercial|no[\s-]*deriv)"
)
# Permissive URLs require the deed slash. licenses/by must not match by-nc.
_PERMITTED_DEED = re.compile(
    r"(?i)"
    r"creativecommons\.org/publicdomain/zero(?:/|$)"
    r"|creativecommons\.org/licenses/by-sa(?:/|$)"
    r"|creativecommons\.org/licenses/by/(?:\d|$)"
    r"|\bcc[\s-]*0\b"
    r"|\bcreative\s+commons(?:\s+public\s+domain)?[\s-]+(?:cc[\s-]*)?zero\b"
    r"|\bcc[\s-]*by(?![\s-]*(?:nc|nd)\b)(?:[\s-]*sa\b)?"
    r"|\bcreative\s+commons\s+attribution(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv))(?:[\s-]*share[\s-]*alike\b)?"
)
_BLOCK_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "pardon our interruption",
    "errors.edgesuite.net",
    "akamaighost",
    "are you a robot",
    "robot check",
    "verify you are human",
    "verify you are a human",
)
_BLOCK_TITLES = frozenset(
    {
        "just a moment...",
        "attention required! | cloudflare",
        "access denied",
        "robot check",
        "please wait while your request is being verified...",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})


class CatalogError(ValueError):
    """A catalog row or page failed the Ought page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_ought_host(hostname: str) -> bool:
    """True only for the official ought.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label.

    ``creative_commons`` means the page states CC0, CC BY, or CC BY-SA.
    Restricted deeds are checked first and stay unknown. The Public Domain
    Mark is not CC0. A public page, a copyright notice, All rights reserved,
    and a terms link stay unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    blob = _licence_blob(page_text)
    if _RESTRICTED_DEED.search(blob):
        return RIGHTS_UNKNOWN
    if _PERMITTED_DEED.search(blob):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated, modified, and copyright years are not publication dates.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    for raw in _BLOG_DATE.findall(visible):
        found = _full_date(_plain(raw))
        if found:
            return found
    labeled = _labeled_published(_plain(visible))
    if labeled:
        return labeled
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
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
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
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
    """Return Ought when the page states that name."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    if _clean_text(metas.get("og:site_name", "")) == PUBLISHER:
        return PUBLISHER
    pieces = [metas.get("og:title", ""), metas.get("citation_publisher", "")]
    title_tag = _TITLE.search(visible)
    if title_tag:
        pieces.append(title_tag.group(1))
    pieces.append(_plain(visible))
    for piece in pieces:
        if re.search(rf"\b{re.escape(PUBLISHER)}\b", _clean_text(piece)):
            return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    A challenge page is refused.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if _challenge_html(page_html):
        raise CatalogError("blocked page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def confirmed_record(
    body: str,
    *,
    status: int,
    content_type: str,
    final_url: str,
    redirects: int = 0,
) -> dict | None:
    """Return a catalog row, or None when the GET must not be stored.

    None covers a Cloudflare challenge, a SiteGround captcha, HTTP 202, an
    Akamai interstitial, a robot check, a non-HTML body, an oversized body,
    too many redirects, and a final URL that is not on ought.org.
    """

    if response_is_blocked(
        body,
        status=status,
        content_type=content_type,
        final_url=final_url,
        redirects=redirects,
    ):
        return None
    try:
        return metadata_from_page(body, page_url=final_url)
    except CatalogError:
        return None


def response_is_blocked(
    body: str,
    *,
    status: int,
    content_type: str,
    final_url: str,
    redirects: int = 0,
) -> bool:
    """True when this GET must not add a catalog row."""

    if status != 200 or not isinstance(redirects, int) or redirects < 0 or redirects > MAX_REDIRECTS:
        return True
    if not _html_content_type(content_type):
        return True
    if not isinstance(body, str) or not body.strip():
        return True
    if len(body.encode("utf-8", "replace")) > MAX_RESPONSE_BYTES:
        return True
    if _non_html_body(body) or _challenge_html(body):
        return True
    try:
        host, _path = _split_https(final_url)
    except CatalogError:
        return True
    return not official_ought_host(host)


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
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
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
        raise CatalogError("canonical URL must be an https ought.org page")
    host, path = _split_https(url)
    if (
        not official_ought_host(host)
        or host != OFFICIAL_HOST
        or _PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL must be an https ought.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _split_https(url: str) -> tuple[str, str]:
    if not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be an https ought.org page")
    if not url.startswith("https://"):
        raise CatalogError(f"canonical URL must be an https ought.org page: {url}")
    rest = url[len("https://") :]
    if not rest or any(char in rest for char in "#?@\\"):
        raise CatalogError(f"canonical URL must be an https ought.org page: {url}")
    host, separator, tail = rest.partition("/")
    if not host or ":" in host or host.endswith(".") or ".." in host:
        raise CatalogError(f"canonical URL must be an https ought.org page: {url}")
    path = f"/{tail}" if separator else ""
    if ".." in path or "//" in path:
        raise CatalogError(f"canonical URL must be an https ought.org page: {url}")
    return host, path


def _resolve(base: str, href: str) -> str:
    target = href.strip()
    if target.startswith("https://") or target.startswith("http://"):
        return target
    host, path = _split_https(base)
    if target.startswith("/"):
        return f"https://{host}{target}"
    directory = path.rsplit("/", 1)[0]
    return f"https://{host}{directory}/{target}"


def _same_page(left: str, right: str) -> bool:
    try:
        host_left, path_left = _split_https(left)
        host_right, path_right = _split_https(right)
    except CatalogError:
        return False
    return host_left == host_right and path_left.rstrip("/") == path_right.rstrip("/")


def _html_content_type(content_type: str) -> bool:
    if not isinstance(content_type, str):
        return False
    media = content_type.split(";", 1)[0].strip().casefold()
    return media in _HTML_TYPES


def _non_html_body(body: str) -> bool:
    head = body.lstrip()[:80].casefold()
    return head.startswith("<?xml") or head.startswith("%pdf") or head.startswith("{") or head.startswith("[")


def _challenge_html(page_html: str) -> bool:
    if not isinstance(page_html, str) or not page_html:
        return False
    head = page_html[:12000].casefold()
    if any(marker in head for marker in _BLOCK_MARKERS):
        return True
    match = _TITLE.search(_without_hidden(page_html[:12000]))
    if match is None:
        return False
    title = _clean_text(match.group(1)).casefold()
    return title in _BLOCK_TITLES or title.startswith("just a moment")


def _licence_blob(page_html: str) -> str:
    parts: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for raw in _LD_LICENSE.findall(blob):
            parts.append(raw.replace("\\/", "/"))
    visible = _without_hidden(page_html)
    parts.append(_plain(visible))
    for tag in _ANCHOR.findall(visible) + _LINK.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            parts.append(href)
    metas = _metas(visible)
    for key in ("license", "dcterms.license", "dc.rights", "dcterms.rights"):
        if metas.get(key):
            parts.append(metas[key])
    return "\n".join(parts)


def _labeled_published(plain: str) -> str | None:
    for match in _LABELED_PUBLISHED.finditer(plain):
        prefix = plain[max(0, match.start() - 24) : match.start()]
        if _EXCLUDED_DATE.search(prefix):
            continue
        if match.group(1) and _iso_date(match.group(1)):
            return match.group(1)
        if match.group(3) and match.group(4) and match.group(5):
            found = _calendar(match.group(5), match.group(3), match.group(4))
            if found:
                return found
        if match.group(7) and match.group(8) and match.group(9):
            found = _calendar(match.group(9), match.group(8), match.group(7))
            if found:
                return found
    return None


def _full_date(value: str) -> str | None:
    text = value.strip()
    if not text or _EXCLUDED_DATE.search(text):
        return None
    if _DATE.fullmatch(text) and _iso_date(text):
        return text
    month_first = _MDY.fullmatch(text)
    if month_first:
        return _calendar(month_first.group(3), month_first.group(1), month_first.group(2))
    day_first = _DMY.fullmatch(text)
    if day_first:
        return _calendar(day_first.group(3), day_first.group(2), day_first.group(1))
    return None


def _calendar(year_text: str, month_name: str, day_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        return date(int(year_text), month, int(day_text)).isoformat()
    except ValueError:
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


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


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


def _meta_values(html: str, names: tuple[str, ...]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _canonical_href(page_html: str) -> str:
    visible = _without_hidden(page_html)
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""
