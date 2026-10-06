"""Metadata catalog of public German BSI pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
are not stored. A date the page does not state stays unknown. An updated or
modified time is not a publication date. Rights stay unknown unless the page
states CC0, CC BY, CC BY-SA, or a Datenlizenz Deutschland reuse licence.
CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A public page,
a copyright notice, or a link to terms is not a licence.

The only allowed host is www.bsi.bund.de. This catalog is not a collector and
runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "bsi_ai_pages"
CATALOG_FILENAME = "bsi_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_DL_DE_BY_2_0 = "dl_de_by_2_0"
RIGHTS_DL_DE_ZERO_2_0 = "dl_de_zero_2_0"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_DL_DE_BY_2_0,
        RIGHTS_DL_DE_ZERO_2_0,
        RIGHTS_CREATIVE_COMMONS,
    }
)
PUBLISHER_DE = "Bundesamt für Sicherheit in der Informationstechnik"
PUBLISHER_EN = "Federal Office for Information Security"
OFFICIAL_HOST = "www.bsi.bund.de"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "content",
        "excerpt",
        "full_text",
        "html",
        "page",
        "page_text",
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_DIRECTORY_PREFIXES = (
    "/DE/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kuenstliche-Intelligenz/",
    "/EN/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kuenstliche-Intelligenz/",
    "/DE/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kryptografie/KI-in-der-Kryptografie/",
    "/EN/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kryptografie/KI-in-der-Kryptografie/",
    "/DE/Themen/Verbraucherinnen-und-Verbraucher/Informationen-und-Empfehlungen/Technologien_sicher_gestalten/Kuenstliche-Intelligenz/",
    "/EN/Themen/Verbraucherinnen-und-Verbraucher/Informationen-und-Empfehlungen/Technologien_sicher_gestalten/Kuenstliche-Intelligenz/",
    "/DE/Themen/Verbraucherinnen-und-Verbraucher/Informationen-und-Empfehlungen/Wie-geht-Internet/KI-",
    "/EN/Themen/Verbraucherinnen-und-Verbraucher/Informationen-und-Empfehlungen/Wie-geht-Internet/KI-",
    "/DE/Service-Navi/Publikationen/Studien/QML/",
    "/EN/Service-Navi/Publikationen/Studien/QML/",
    "/SharedDocs/Downloads/DE/BSI/KI/",
    "/SharedDocs/Downloads/EN/BSI/KI/",
    "/SharedDocs/Downloads/EN/BSI/Publications/Studies/KI/",
    "/SharedDocs/Downloads/EN/BSI/Publications/Studies/ML-SAST/",
    "/SharedDocs/Downloads/DE/BSI/CloudComputing/AIC4/",
    "/SharedDocs/Downloads/EN/BSI/CloudComputing/AIC4/",
)
_EXACT_PATHS = frozenset(
    {
        "/SharedDocs/Downloads/DE/BSI/Publikationen/Broschueren/Wegweiser_Checklisten_Flyer/Brosch_A6_Kuenstliche_Intelligenz.html",
        "/SharedDocs/Cybersicherheitswarnungen/DE/2023/2023-249034-1032_csw.html",
        "/SharedDocs/Cybersicherheitswarnungen/DE/2026/2026-262788-1032.html",
    }
)
_NAV_TITLES = frozenset(
    {
        "navigation und service",
        "navigation and service",
        "fußbereich",
        "fussbereich",
        "footer",
    }
)
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(r"""([:\w.-]+)\s*=\s*(['"])(.*?)\2""")
_DOC_DATA = re.compile(
    r"(?is)<p\b[^>]*class\s*=\s*['\"][^'\"]*\bdocData\b[^'\"]*['\"][^>]*>(.*?)</p>"
)
_LABELED_DATE = re.compile(
    r"(?is)<strong\b[^>]*>\s*(Datum|Date)\s*</strong>\s*"
    r"<span\b[^>]*>\s*(\d{2}\.\d{2}\.\d{4})\s*</span>"
)
_DL_BY = re.compile(
    r"datenlizenz deutschland\s*-\s*namensnennung\s*-\s*version 2\.0"
    r"|dl-de/(?:by-2-0|by/2-0)"
    r"|govdata\.de/dl-de/by-2-0"
)
_DL_ZERO = re.compile(
    r"datenlizenz deutschland\s*-\s*zero\s*-\s*version 2\.0"
    r"|dl-de/(?:zero-2-0|zero/2-0)"
    r"|govdata\.de/dl-de/zero-2-0"
)
# creative_commons is only CC0, CC BY, or CC BY-SA. Noncommercial and
# no-derivatives deeds stay unknown.
_CC_RESTRICTED_NAME = r"(?:non[\s-]?commercial|no[\s-]?deriv)"
_CC_GRANT = re.compile(
    r"creative commons zero"
    r"|\bcc0\b"
    r"|creative commons attribution(?![\s-]*"
    + _CC_RESTRICTED_NAME
    + r")(?:[\s-]share[\s-]?alike)?"
    r"|\bcc[\s-]*by(?![\s-]*(?:nc|nd)\b)(?:[\s-]*sa\b)?(?![\s-]*(?:nc|nd)\b)"
)
_CC_URL = re.compile(
    r"creativecommons\.org/licenses/by-sa(?:/|[^\w-]|$)"
    r"|creativecommons\.org/licenses/by(?:/|[^\w-]|$)"
    r"|creativecommons\.org/publicdomain/zero/"
)


class CatalogError(ValueError):
    """A catalog row or page failed the BSI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_bsi_host(hostname: str) -> bool:
    """True only for the public www.bsi.bund.de host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
    CC BY-NC-SA, and CC BY-NC-ND stay unknown.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    plain = _plain_from_visible(visible)
    hrefs = " ".join(unescape(a or b) for a, b in _HREF.findall(visible)).casefold()
    if _DL_BY.search(plain) or _DL_BY.search(hrefs):
        return RIGHTS_DL_DE_BY_2_0
    if _DL_ZERO.search(plain) or _DL_ZERO.search(hrefs):
        return RIGHTS_DL_DE_ZERO_2_0
    if _CC_GRANT.search(plain) or _CC_URL.search(plain) or _CC_URL.search(hrefs):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use the labeled publication Datum or Date. Otherwise unknown.

    ``og:updated_time`` and other modification times are not publication dates.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    for block in _DOC_DATA.findall(visible):
        match = _LABELED_DATE.search(block)
        if match is None:
            continue
        parsed = _iso_from_german(match.group(2))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    meta = _metas(visible)
    for key in ("og:title", "twitter:title", "dcterms.title"):
        title = _clean_title(meta.get(key, ""))
        if title and title.casefold() not in _NAV_TITLES:
            return title
    for heading in _H1.findall(visible):
        title = _clean_title(heading)
        if title and title.casefold() not in _NAV_TITLES:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        title = re.sub(r"(?i)^bsi\s+-\s+", "", title).strip()
        if title and title.casefold() not in _NAV_TITLES:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _metas(_visible(page_html)).get("og:site_name", "").strip()
    if site in {PUBLISHER_DE, PUBLISHER_EN}:
        return site
    plain = _plain_from_visible(_visible(page_html))
    found = [name for name in (PUBLISHER_DE, PUBLISHER_EN) if name.casefold() in plain]
    if len(found) == 1:
        return found[0]
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the URL that
    was fetched. A different rel=canonical does not replace it.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
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
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a www.bsi.bund.de https page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not official_bsi_host(host)
        or not _ai_html_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public BSI artificial-intelligence page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _ai_html_path(path: str) -> bool:
    if not path.endswith(".html") or path.endswith("_node.html"):
        return False
    lowered = path.lower()
    if (
        lowered.endswith(".pdf")
        or "/siteglobals/" in lowered
        or ".." in path
        or "\\" in path
        or "//" in path
        or "(s(" in lowered
    ):
        return False
    if path in _EXACT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _DIRECTORY_PREFIXES)


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


def _visible(page_text: str) -> str:
    return _HIDDEN.sub(" ", page_text)


def _plain_from_visible(visible: str) -> str:
    text = _TAG.sub(" ", visible)
    text = unescape(text)
    text = (
        text.replace("\u00ad", "")
        .replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _metas(visible: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(visible):
        attrs = {key.casefold(): unescape(value).strip() for key, _, value in _ATTR.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _iso_from_german(value: str) -> str | None:
    day_text, month_text, year_text = value.split(".")
    try:
        parsed = date(int(year_text), int(month_text), int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
