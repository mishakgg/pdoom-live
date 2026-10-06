"""Metadata catalog of public Berkman Klein Center pages about AI.

Rows keep a title, publisher, canonical URL, date, and rights label for official
HTML pages on cyber.harvard.edu. Page bodies, abstracts, and PDFs are not
stored. A date the page does not state stays unknown. Updated, modified, and
copyright years are not publication dates. Rights stay unknown unless the page
states CC0, CC BY, or CC BY-SA and does not also state a restricted deed.
CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen is a
word boundary, so CC BY does not match CC BY-NC. A public page, a copyright
notice, all rights reserved, a terms link, and a Harvard or Berkman copyright
line are not a reuse licence. Public Domain Mark is not CC0. This catalog is
not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "berkman_ai_pages"
CATALOG_FILENAME = "berkman_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "cyber.harvard.edu"
PUBLISHER = "Berkman Klein Center"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

# Confirmed AI HTML paths. A Berkman page outside this set is not catalogued.
AI_PAGE_PATHS = frozenset(
    {
        "/ethics-and-governance-ai-reading-list",
        "/ethics-and-governance-ai-supporters-collaborators-and-friends",
        "/podcast/when-a-bot-is-the-judge",
        "/projects/ai-autonomous-vehicles",
        "/projects/ai-educational-activities",
        "/projects/ai-global-governance-and-inclusion",
        "/projects/ai-initiative/responsible-generative-ai-accountable-technical-oversight",
        "/projects/ai-media-and-information-quality",
        "/projects/ai-policy-research-clinic-city-helsinki",
        "/projects/ai-transparency-and-explainability",
        "/projects/algorithms-and-justice",
        "/projects/artificial-intelligence-and-law",
        "/publication/2018/3-practical-tools-help-regulators-develop-better-laws-and-policies",
        "/publication/2018/5-technological-factors-regulators-and-policymakers-need-know",
        "/publication/2018/artificial-intelligence-human-rights",
        "/publication/2018/assessing-assessments",
        "/publication/2018/harm-reduction-framework-algorithmic-fairness",
        "/publication/2018/smart-move-24-essentials-swot-analysis-policymakers-need-consider",
        "/publication/2018/what-governments-across-globe-are-doing-seize-benefits-autonomous-vehicles",
        "/publication/2019/youth-and-artificial-intelligence/where-we-stand",
        "/publication/2020/modulate-case-study",
        "/publication/2020/principled-ai",
        "/publication/2023/vectors-ai-governance",
        "/publication/2025/inside-black-box",
        "/publication/2026/ai-magic",
        "/publications/2017/11/AIExplanation",
        "/publications/2018/05/AGTech",
        "/research/AGTechForum",
        "/research/ai/advance",
        "/research/ai/rio-inclusion",
        "/research/harmfulspeech/algosworkshop",
        "/teaching/2019-01/applied-ethical-and-governance-challenges-ai-spring-2019",
        "/teaching/debates-frontier-artificial-intelligence-governance-ai-triad",
        "/topics/ethics-and-governance-ai",
    }
)

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
_MODIFIED_DATE_KEYS = (
    "article:modified_time",
    "og:updated_time",
    "dcterms.modified",
    "dc.date.modified",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_UPDATED_TIME = re.compile(r"(?is)<time\b[^>]*\bupdated(?:_date)?\b[^>]*>.*?</time>")
_PUBLISHED_TIME = re.compile(
    r"(?is)\bpublished\b(?:\s|<[^>]+>)*<time\b[^>]*\bdatetime\s*=\s*[\"'](\d{4}-\d{2}-\d{2})"
)
_PUBLISHED_TEXT = re.compile(
    r"\b(?:date published|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
_SITE_SUFFIXES = (
    " | Berkman Klein Center",
    " - Berkman Klein Center",
    " – Berkman Klein Center",
    " — Berkman Klein Center",
    " | Harvard Berkman Klein Center",
    " - Harvard Berkman Klein Center",
)
_GENERIC_TITLES = frozenset(
    {
        "main navigation",
        "secondary navigation",
        "footer",
        "homepage",
        "berkman klein center",
        "harvard berkman klein center",
    }
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
    ".mp3",
    ".mp4",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".epub",
    ".gz",
)
# robots.txt Disallow prefixes for User-agent: *.
_ROBOTS_DISALLOW_PREFIXES = (
    "/team",
    "/lists",
    "/msdoj/discuss/",
    "/zittrain/",
    "/cite/",
    "/opengovernment",
    "/blogs",
    "/blogsupport",
    "/brooklaw",
    "/cyberlaw2005/wiki",
    "/cyberone/wiki",
    "/h2owiki",
    "/ipc",
    "/iptheory",
    "/jamaicavoices",
    "/netizenship",
    "/ocs_global",
    "/ocs_intranet",
    "/oni-ras",
    "/practical_lawyering",
    "/publicmediaforge",
    "/techwiki",
)
# creative_commons is only CC0, CC BY, or CC BY-SA. A hyphen is a word
# boundary: CC BY must not match CC BY-NC, and a by-nc URL is not CC BY.
_CC0_PHRASE = re.compile(
    r"\bcc[\s-]*0\b"
    r"|creative commons(?:\s+public\s+domain)?[\s-]+(?:zero|cc[\s-]*0)\b"
)
_CC_BY_SA_PHRASE = re.compile(
    r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)"
    r"|creative commons\s+attribution[\s-]*(?:share[\s-]*alike|sa)\b"
    r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?|nc|nd)\b)"
)
_CC_BY_PHRASE = re.compile(
    r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
    r"|creative commons\s+attribution\b"
    r"(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv(?:ative)?s?|sa|nc|nd)\b)"
)
_CC_HOST = r"(?:www\.)?creativecommons\.org/"
_PERMISSIVE_URL = re.compile(
    _CC_HOST
    + r"(?:licenses/(?:by-sa|by)(?:/\d+\.\d+)?(?:/(?:deed|legalcode)(?:\.[a-z0-9]+)*)?"
    + r"|publicdomain/zero(?:/\d+\.\d+)?)"
    + r"/?(?=$|[\s\"'<>),.;])"
)
_RESTRICTED_URL = re.compile(
    _CC_HOST
    + r"licenses/(?:by-nc-nd|by-nc-sa|by-nc|by-nd)(?:/\d+\.\d+)?"
    + r"(?:/(?:deed|legalcode)(?:\.[a-z0-9]+)*)?"
    + r"/?(?=$|[\s\"'<>),.;])"
)
_RESTRICTED_PHRASE = re.compile(
    r"\bcc[\s-]*by[\s-]*(?:nc(?:[\s-]*(?:sa|nd))?|nd)\b"
    r"|creative commons\s+attribution[\s-]*non[\s-]*commercial\b"
    r"|creative commons\s+attribution[\s-]*no[\s-]*deriv(?:ative)?s?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Berkman Klein page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_berkman_host(hostname: str) -> bool:
    """True only for the official cyber.harvard.edu host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def rights_from_page(page_text: str) -> str:
    """Return a rights label.

    ``creative_commons`` means the page states CC0, CC BY, or CC BY-SA and does
    not also state a restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
    CC BY-NC-ND stay unknown. A by-nc URL stays unknown even when its anchor
    text says CC BY. Public Domain Mark is not CC0. A generic
    creativecommons.org/licenses/ URL is not a licence. A public page, a
    copyright notice, all rights reserved, a terms link, and a Harvard or
    Berkman copyright line stay unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    permissive = False
    restricted = False
    for blob in _licence_blobs(_without_hidden(page_text)):
        allows, limits = _deed_flags(blob)
        permissive = permissive or allows
        restricted = restricted or limits
    if restricted or not permissive:
        return RIGHTS_UNKNOWN
    return RIGHTS_CREATIVE_COMMONS


def date_from_page(page_text: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated, modified, and copyright years are not publication dates. A date
    inside script, style, or comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    metas = _metas(html)
    for key in _MODIFIED_DATE_KEYS:
        metas.pop(key, None)
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    visible = _UPDATED_TIME.sub(" ", html)
    match = _PUBLISHED_TIME.search(visible)
    if match and _iso_date(match.group(1)):
        return match.group(1)
    labeled = _PUBLISHED_TEXT.search(_plain(visible))
    if labeled and _iso_date(labeled.group(1)):
        return labeled.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return validate_entry(
        {
            "title": title_from_page(page_html),
            "publisher": PUBLISHER,
            "canonical_url": validate_canonical_url(page_url),
            "date": date_from_page(page_html),
            "rights": rights_from_page(page_html),
        }
    )


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
    if description != description.strip():
        raise CatalogError("description must not have surrounding whitespace")
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
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an official cyber.harvard.edu AI page")
    parsed = _parse_https_url(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an official cyber.harvard.edu AI page: {url}")
    host, path = parsed
    if not official_berkman_host(host) or host != OFFICIAL_HOST or not _ai_html_path(path):
        raise CatalogError(f"canonical URL must be an official cyber.harvard.edu AI page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _ai_html_path(path: str) -> bool:
    if not path.startswith("/") or ".." in path or "\\" in path or "//" in path:
        return False
    if path != "/" and path.endswith("/"):
        return False
    lowered = path.casefold()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    for prefix in _ROBOTS_DISALLOW_PREFIXES:
        blocked = prefix if prefix.endswith("/") else prefix + "/"
        if lowered == prefix.rstrip("/") or lowered.startswith(blocked):
            return False
    return path in AI_PAGE_PATHS


def _parse_https_url(url: str) -> tuple[str, str] | None:
    if not url.startswith("https://") or any(mark in url for mark in "?#@"):
        return None
    rest = url[len("https://") :]
    if "/" in rest:
        hostport, raw_path = rest.split("/", 1)
        path = "/" + raw_path
    else:
        hostport, path = rest, "/"
    if not hostport or ":" in hostport:
        return None
    if hostport != OFFICIAL_HOST:
        return None
    return hostport, path


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


def _licence_blobs(html: str) -> list[str]:
    blobs = [_plain(html)]
    blobs.extend(unescape(left or right).strip() for left, right in _HREF.findall(html))
    blobs.extend(_meta_contents(html))
    return [blob for blob in blobs if blob]


def _deed_flags(value: str) -> tuple[bool, bool]:
    text = _norm(value)
    restricted = bool(_RESTRICTED_PHRASE.search(text) or _RESTRICTED_URL.search(text))
    cleaned = _RESTRICTED_URL.sub(" ", text)
    cleaned = _RESTRICTED_PHRASE.sub(" ", cleaned)
    permissive = bool(
        _CC0_PHRASE.search(cleaned)
        or _CC_BY_SA_PHRASE.search(cleaned)
        or _CC_BY_PHRASE.search(cleaned)
        or _PERMISSIVE_URL.search(cleaned)
    )
    return permissive, restricted


def _norm(value: str) -> str:
    text = value.casefold()
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    return text


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain(value)
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


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() not in _GENERIC_TITLES


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


def _meta_contents(html: str) -> list[str]:
    contents: list[str] = []
    for tag in _META.findall(html):
        content = _attrs(tag).get("content", "")
        if content:
            contents.append(content)
    return contents


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
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
