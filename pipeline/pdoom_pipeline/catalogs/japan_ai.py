"""Metadata catalog of public Japanese government pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
are not stored. A date the page does not state stays unknown. Rights stay
unknown unless the page states a reuse licence that allows copying. A public
page, a copyright notice, or a link to a site policy is not a licence.

Allowed hosts are go.jp and its subdomains, including digital.go.jp and
meti.go.jp. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "japan_ai_pages"
CATALOG_FILENAME = "japan_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_STANDARD_TERMS = "government_of_japan_standard_terms"
RIGHTS_PUBLIC_DATA = "public_data_terms"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_STANDARD_TERMS,
        RIGHTS_PUBLIC_DATA,
        RIGHTS_CREATIVE_COMMONS,
    }
)
OFFICIAL_HOST_SUFFIX = "go.jp"
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
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_ISSUED_META = frozenset(
    {
        "article:published_time",
        "citation_publication_date",
        "dcterms.issued",
        "dcterms:issued",
    }
)
_MODIFIED_META = frozenset(
    {
        "article:modified_time",
        "dcterms.modified",
        "dcterms:modified",
    }
)
_ERA_BASE = {"令和": 2018, "平成": 1988, "昭和": 1925}
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>.*?</h1>")
_ATTR = re.compile(r"""([:\w.-]+)\s*=\s*(['"])(.*?)\2""")
_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_JP_DATE = (
    r"(?:(?P<era>令和|平成|昭和)(?P<ey>\d{1,2}|元)年(?P<em>\d{1,2})月(?P<ed>\d{1,2})日|"
    r"(?P<y>\d{4})年(?P<m>\d{1,2})月(?P<d>\d{1,2})日|"
    r"(?P<iso>\d{4}-\d{2}-\d{2}))"
)
_LABELED_PUBLISHED = re.compile(rf"(?:公開日|掲載日)\s*:\s*{_JP_DATE}")
_LABELED_MODIFIED = re.compile(rf"最終更新日\s*:\s*{_JP_DATE}")
_PUBLISHED_ISO = re.compile(r"(?:date published|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b")
_LAST_UPDATED = re.compile(
    r"last updated\s*:\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2}),\s*(\d{4})\b"
)
_MODIFIED_ISO = re.compile(r"date modified\s*:\s*(\d{4}-\d{2}-\d{2})\b")
_DECISION = re.compile(rf"{_JP_DATE}\s*(?:閣議決定|本部決定)")
_LEADING = re.compile(rf"^{_JP_DATE}")
_STANDARD_VERSION = re.compile(
    r"政府標準利用規約\s*[（(]\s*第\s*[0-9.]+\s*版\s*[）)]|"
    r"government of japan standard terms of use\s*\(\s*version"
)
_STANDARD_GRANT = re.compile(
    r"政府標準利用規約.{0,160}(?:自由に利用|複製)|"
    r"(?:自由に利用|複製).{0,160}政府標準利用規約|"
    r"under the government of japan standard terms of use"
)
_PUBLIC_DATA_VERSION = re.compile(r"公共データ利用規約\s*[（(]\s*第\s*[0-9.]+\s*版\s*[）)]")
_PUBLIC_DATA_GRANT = re.compile(
    r"公共データ利用規約.{0,160}(?:自由に利用|複製)|"
    r"(?:自由に利用|複製).{0,160}公共データ利用規約"
)
# creative_commons is only CC0, CC BY, or CC BY-SA. NonCommercial and
# NoDerivatives deeds, and a generic "Creative Commons" mention, stay unknown.
_CC_RESTRICTED = re.compile(
    r"creativecommons\.org/licenses/by-nc(?:-sa|-nd)?\b|"
    r"creativecommons\.org/licenses/by-nd\b|"
    r"attribution\s*[-–—]\s*non\s*[-–—]?\s*commercial|"
    r"attribution\s*[-–—]\s*no\s*[-–—]?\s*deriv|"
    r"\bnon\s*[-–—]?\s*commercial\b|"
    r"\bno\s*[-–—]?\s*derivatives\b|"
    r"非営利|"
    r"改変禁止"
)
_CC_PERMISSIVE = re.compile(
    r"creativecommons\.org/licenses/by-sa\b|"
    r"creativecommons\.org/licenses/by/(?=\d)|"
    r"creativecommons\.org/publicdomain/zero\b|"
    r"licen[cs]ed under (?:a |the )?creative commons attribution(?!\s*[-–—]\s*(?:non|no))|"
    r"licen[cs]ed under (?:a |the )?creative commons (?:cc0|zero)\b|"
    r"\bcc0\b|"
    r"クリエイティブ・コモンズ(?:・ライセンス)?\s*表示\s*[-－ー]\s*継承|"
    r"クリエイティブ・コモンズ(?:・ライセンスの|\s+)表示\s*4\.0(?!\s*国際と互換)|"
    r"クリエイティブ・コモンズ・ライセンス[（(]\s*表示\s*[）)]"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Japanese government page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_japan_host(hostname: str) -> bool:
    """True for go.jp and its subdomains, including digital.go.jp and meti.go.jp."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return host == OFFICIAL_HOST_SUFFIX or host.endswith("." + OFFICIAL_HOST_SUFFIX)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, including the
    Japanese name クリエイティブ・コモンズ 表示 4.0. A NonCommercial or
    NoDerivatives phrase stays unknown. A copyright line or a site-policy
    link stays unknown.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    plain = _fold(_plain(page_text))
    if _STANDARD_VERSION.search(plain) or _STANDARD_GRANT.search(plain):
        return RIGHTS_STANDARD_TERMS
    if _PUBLIC_DATA_VERSION.search(plain) or _PUBLIC_DATA_GRANT.search(plain):
        return RIGHTS_PUBLIC_DATA
    if _CC_RESTRICTED.search(plain):
        return RIGHTS_UNKNOWN
    if _CC_PERMISSIVE.search(plain):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date, then a stated modified or decision date.

    A date that appears only inside a sentence, a law number, or a script stays
    unknown. Updated text that is not labeled as the page date stays unknown.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible(page_text)
    folded = _fold(_plain(visible))
    issued = _first_iso_date(_meta_values(visible, _ISSUED_META))
    if issued:
        return issued
    published = _match_japanese(_LABELED_PUBLISHED, folded) or _iso_or_none(_PUBLISHED_ISO, folded)
    if published:
        return published
    modified = _first_iso_date(_meta_values(visible, _MODIFIED_META))
    if modified:
        return modified
    labeled_modified = _match_japanese(_LABELED_MODIFIED, folded) or _english_updated(folded)
    if labeled_modified:
        return labeled_modified
    modified_iso = _iso_or_none(_MODIFIED_ISO, folded)
    if modified_iso:
        return modified_iso
    decision = _match_japanese(_DECISION, folded)
    if decision:
        return decision
    leading = _date_after_h1(visible)
    if leading:
        return leading
    return UNKNOWN_DATE


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
        raise CatalogError("canonical URL must be an https go.jp page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
        or parsed.port not in (None, 443)
        or not official_japan_host(host)
        or not path
        or path == "/"
        or ".." in path
        or "\\" in path
        or "//" in path
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be an https go.jp page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _is_download(path: str) -> bool:
    lowered = path.casefold()
    return any(lowered.endswith(suffix) for suffix in _DOWNLOAD_SUFFIXES)


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
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", _visible(page_text)))
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _fold(text: str) -> str:
    folded = text.translate(_DIGITS)
    folded = folded.replace("．", ".").replace("：", ":").replace("·", "・").replace("･", "・")
    return folded.casefold()


def _attrs(tag: str) -> dict[str, str]:
    return {key.casefold(): unescape(value).strip() for key, _, value in _ATTR.findall(tag)}


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    found: list[str] = []
    for tag in _META.findall(html):
        attrs = _attrs(tag)
        key = attrs.get("name") or attrs.get("property") or ""
        if key.casefold() in names:
            found.append(attrs.get("content", ""))
    return found


def _first_iso_date(values: list[str]) -> str | None:
    for value in values:
        prefix = value.strip()[:10]
        if _iso_date(prefix):
            return prefix
    return None


def _iso_or_none(pattern: re.Pattern[str], folded: str) -> str | None:
    match = pattern.search(folded)
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return None


def _english_updated(folded: str) -> str | None:
    match = _LAST_UPDATED.search(folded)
    if not match:
        return None
    return _iso(int(match.group(3)), _MONTHS[match.group(1)], int(match.group(2)))


def _match_japanese(pattern: re.Pattern[str], folded: str) -> str | None:
    match = pattern.search(folded)
    if not match:
        return None
    return _japanese_groups(match)


def _date_after_h1(visible_html: str) -> str | None:
    match = _H1.search(visible_html)
    if not match:
        return None
    return _match_japanese(_LEADING, _fold(_plain(visible_html[match.end() :])))


def _japanese_groups(match: re.Match[str]) -> str | None:
    if match.group("iso"):
        return match.group("iso") if _iso_date(match.group("iso")) else None
    if match.group("era"):
        year_text = match.group("ey")
        year_num = 1 if year_text == "元" else int(year_text)
        return _iso(_ERA_BASE[match.group("era")] + year_num, int(match.group("em")), int(match.group("ed")))
    return _iso(int(match.group("y")), int(match.group("m")), int(match.group("d")))


def _iso(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    return _iso(year, month, day) == value
