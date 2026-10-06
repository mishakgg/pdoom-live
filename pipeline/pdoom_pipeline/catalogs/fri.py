"""Metadata catalog of public Forecasting Research Institute pages about AI forecasts.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, report text,
chart data, and PDFs are not stored. Rights is creative_commons only when the
page states CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A public page, a copyright notice, an
all-rights-reserved line, or a terms link is not a licence. A page that does
not state a publication date keeps the date unknown. Updated, modified, and
copyright years are not publication dates. The live URL is stored as
confirmed; a different rel=canonical does not replace it. This module does
not fetch and it is not a belief collector. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "fri_pages"
CATALOG_FILENAME = "fri_pages.json"
RUNNER_WIRED = False
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
INSTITUTE_HOST = "forecastingresearch.org"
LEAP_HOST = "leap.forecastingresearch.org"
OFFICIAL_HOSTS = frozenset({INSTITUTE_HOST, LEAP_HOST})
PUBLISHER_INSTITUTE = "Forecasting Research Institute"
PUBLISHER_LEAP = "Longitudinal Expert AI Panel"
ALLOWED_PUBLISHERS = frozenset({PUBLISHER_INSTITUTE, PUBLISHER_LEAP})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_ARIA_HIDDEN = re.compile(
    r"""(?is)<([a-zA-Z0-9]+)\b[^>]*\baria-hidden\s*=\s*(?:"true"|'true'|true)[^>]*>.*?</\1>"""
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_DECORATIVE_HEADING = re.compile(r"(?is)\baria-hidden\s*=|\bsr-only\b")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
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
_MONTH_NAME = (
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_PUBLISHED_LABEL = re.compile(
    rf"(?i)(?<![A-Za-z])published\s*:\s*{_MONTH_NAME}\s+(\d{{1,2}}),\s+(\d{{4}})"
)
_RELEASED_LABEL = re.compile(
    rf"(?i)(?<![A-Za-z])first\s+released\s+on\s*:\s*(\d{{1,2}})\s+{_MONTH_NAME}\s+(\d{{4}})"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dcterms.created",
    "dc.date.issued",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_SITE_SUFFIXES = (
    " - Forecasting Research Institute",
    " | Forecasting Research Institute",
    " - Longitudinal Expert AI Panel",
    " | Longitudinal Expert AI Panel",
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
    ".ico",
)
# creative_commons is only CC0, CC BY, or CC BY-SA. The substrings "creative
# commons" and "cc-by" are not CC BY when NonCommercial, NoDerivatives, or
# ShareAlike follows. ShareAlike is recognized only as CC BY-SA.
_FOLLOWING_LIMIT = (
    r"(?:nc|nd|sa|share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?)"
)
_CC0_PHRASE = re.compile(r"\bcc[\s-]*0\b|creative commons(?:\s+public\s+domain)?[\s-]+zero\b")
_CC_BY_SA_PHRASE = re.compile(
    r"\bcc[\s-]*by[\s-]*(?:sa|share[\s-]*alike)\b"
    r"|creative commons\s+attribution[\s-]*(?:share[\s-]*alike|sa)\b"
)
_CC_BY_PHRASE = re.compile(
    rf"\bcc[\s-]*by\b(?![\s-]*{_FOLLOWING_LIMIT}\b)"
    rf"|creative commons\s+attribution\b(?![\s-]*{_FOLLOWING_LIMIT}\b)"
)
_CC_COPYING_URL = re.compile(
    r"creativecommons\.org/(?:licenses/by(?:-sa)?/|publicdomain/zero/)"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Forecasting Research Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    order: list[tuple[tuple[str, str], str]] = []
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if len(order) > 1 and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    publisher = entry.get("publisher")
    _require_text(publisher, "publisher", MAX_TEXT_CHARS)
    if publisher not in ALLOWED_PUBLISHERS:
        raise CatalogError("publisher must be an official Forecasting Research Institute publisher")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS} or {RIGHTS_UNKNOWN}")
    if entry["canonical_url"].startswith(f"https://{LEAP_HOST}") and publisher != PUBLISHER_LEAP:
        raise CatalogError("LEAP pages are published by the Longitudinal Expert AI Panel")
    if entry["canonical_url"].startswith(f"https://{INSTITUTE_HOST}") and publisher != PUBLISHER_INSTITUTE:
        raise CatalogError("institute pages are published by the Forecasting Research Institute")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}") from exc
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be a public Forecasting Research Institute page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or host not in OFFICIAL_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _official_path(host, path)
    ):
        raise CatalogError(f"canonical URL is not a public Forecasting Research Institute page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host in OFFICIAL_HOSTS and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return creative_commons or unknown.

    creative_commons means the page states CC0, CC BY, or CC BY-SA. CC BY-NC,
    CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. The substrings
    "creative commons" and "cc-by" are not CC BY when NonCommercial,
    NoDerivatives, or ShareAlike follows. Script, style, and comment text
    does not count. A copyright notice, a public page, an all-rights-reserved
    line, or a link to terms is not a licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    plain = _plain_text(html).casefold()
    if _states_creative_commons(plain) or any(_states_creative_commons(item.casefold()) for item in _meta_contents(html)):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    A visible Published or First released label is a publication date.
    article:modified_time, og:updated_time, an Updated or Revised label, and a
    copyright year are not publication dates. A date inside script or style
    text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    html = _without_hidden(page_html)
    labeled = _labeled_publication_date(_plain_text(html))
    if labeled:
        return labeled
    metas = _metas(html)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_prefix(metas.get(key, ""))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    html = _without_hidden(page_html)
    metas = _metas(html)
    site = metas.get("og:site_name", "").strip()
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title and not _is_site_name(title, site):
            return title
    title = _heading_title(html)
    if title:
        return title
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    title_tag = _TITLE.search(html)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _metas(_without_hidden(page_html)).get("og:site_name", "").strip()
    if site in ALLOWED_PUBLISHERS:
        return site
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _official_path(host: str, path: str) -> bool:
    lowered = path.casefold()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if host == INSTITUTE_HOST:
        parts = path.split("/")
        slug = parts[2] if len(parts) == 3 else ""
        return len(parts) == 3 and parts[0] == "" and parts[1] == "research" and _SLUG.fullmatch(slug) is not None
    if host == LEAP_HOST:
        if path == "/":
            return True
        if path.endswith("/"):
            return False
        parts = path.split("/")
        if len(parts) == 2 and parts[1] in {"about", "panel", "reports"}:
            return True
        if len(parts) == 3 and parts[1] == "reports" and _SLUG.fullmatch(parts[2] or "") is not None:
            return True
    return False


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")
    if "<" in value or ">" in value:
        raise CatalogError(f"{field} must be plain text")


def _sort_date(value: str) -> tuple[str, str]:
    if value == UNKNOWN_DATE:
        return ("1", "")
    return ("0", value)


def _states_creative_commons(plain: str) -> bool:
    text = plain.casefold().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    return any(pattern.search(text) for pattern in (_CC0_PHRASE, _CC_BY_SA_PHRASE, _CC_BY_PHRASE, _CC_COPYING_URL))


def _labeled_publication_date(plain: str) -> str | None:
    published = _PUBLISHED_LABEL.search(plain)
    if published:
        parsed = _calendar_date(published.group(1), published.group(2), published.group(3))
        if parsed:
            return parsed
    released = _RELEASED_LABEL.search(plain)
    if released:
        parsed = _calendar_date(released.group(2), released.group(1), released.group(3))
        if parsed:
            return parsed
    return None


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _without_hidden(page_text: str) -> str:
    text = _COMMENT.sub(" ", page_text)
    text = _SCRIPT_STYLE.sub(" ", text)
    return _ARIA_HIDDEN.sub(" ", text)


def _heading_title(html: str) -> str:
    """Use the first h1 that is a page heading.

    A hero heading that swaps words with a screen-reader or hidden span is not
    a stable title. The document title is used instead.
    """

    heading = _H1.search(html)
    if heading is None or _DECORATIVE_HEADING.search(heading.group(1)):
        return ""
    return _clean_title(_TAG.sub(" ", heading.group(1)))


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _is_site_name(title: str, site_name: str) -> bool:
    folded = title.casefold()
    if site_name and folded == site_name.casefold():
        return True
    return folded in {PUBLISHER_INSTITUTE.casefold(), PUBLISHER_LEAP.casefold(), "fri"}


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(page_text)


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_contents(html: str) -> list[str]:
    contents: list[str] = []
    for tag in _META.findall(html):
        content = _attrs(tag).get("content", "")
        if content:
            contents.append(content)
    return contents


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return None
    return match.group(1)
