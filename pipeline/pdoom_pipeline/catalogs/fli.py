"""Metadata catalog of public Future of Life Institute pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, abstracts, PDFs,
reports, and chart data are not stored. Rights stay unknown unless the page
states a reuse licence. ``creative_commons`` means only CC0, CC BY, or CC
BY-SA. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown.
``uk_ogl`` is used only when the page states the Open Government Licence.
Updated, modified, and copyright years are not publication dates. A missing
date stays unknown. The live URL is stored as confirmed; a different
rel=canonical does not replace it. This module does not fetch and it is not
a belief collector. ``runner_wired`` stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "fli_pages"
CATALOG_FILENAME = "fli_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Future of Life Institute"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_UK_OGL})
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "futureoflife.org"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
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
        "quotation",
        "quote",
        "report_body",
        "text",
        "transcript",
        "transcript_text",
    }
)
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
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
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
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher")
_SITE_SUFFIXES = (
    " | Future of Life Institute",
    " - Future of Life Institute",
    " – Future of Life Institute",
    " — Future of Life Institute",
    " | FLI",
    " - FLI",
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
    ".mp4",
    ".mp3",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".gz",
    ".tgz",
    ".tar",
    ".epub",
)
_BLOCKED_PREFIXES = ("/wp-admin", "/wp-content", "/wp-includes", "/wp-json", "/xmlrpc.php", "/admin")
# creative_commons is only CC0, CC BY, or CC BY-SA. A following NonCommercial,
# NoDerivatives, or ShareAlike token must not be read as plain CC BY.
_CC0_PHRASE = re.compile(r"\bcc[\s-]*0\b|creative commons(?:\s+public\s+domain)?[\s-]+zero\b")
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
_CC_COPYING_URL = re.compile(
    r"creativecommons\.org/(?:licenses/(by-sa|by)/|publicdomain/zero/)"
)
_DISALLOWED_CC_URL = re.compile(
    r"creativecommons\.org/licenses/(?:by-nc-nd|by-nc-sa|by-nc|by-nd)/"
)
# A photo credit is not a licence to copy the page. A grant in the same
# sentence ("licensed under") still counts.
_IMAGE_CREDIT = re.compile(r"\bwikimedia\b|\bown work\b")
_PAGE_GRANT = re.compile(r"\b(?:licensed|licenced|released|available|shared)\s+under\b")
_EXACT_TOPIC_PATHS = frozenset(
    {
        "/our-position-on-ai/",
        "/focus-area/artificial-intelligence/",
        "/our-work/policy-and-research/",
        "/safety/",
        "/ai-safety-breakfasts/",
        "/project/eu-ai-act/",
        "/project/ai-safety-summits/",
        "/project/enhancing-multilateral-engagement-in-the-governance-of-ai/",
        "/project/autonomous-weapons-systems/",
        "/project/ai-convergence-nuclear-biological-cyber/",
        "/project/combatting-deepfakes/",
        "/project/ai-role-in-reshaping-power-distribution/",
        "/project/artificial-escalation/",
        "/open-letter/pause-giant-ai-experiments/",
        "/open-letter/ai-open-letter/",
        "/open-letter/ai-principles/",
        "/open-letter/ai-policy-for-a-better-future-on-addressing-both-present-harms-and-emerging-threats/",
        "/open-letter/foresight-in-ai-regulation-open-letter/",
        "/open-letter/open-letter-autonomous-weapons-ai-robotics/",
        "/open-letter/lethal-autonomous-weapons-pledge/",
        "/open-letter/ai-economics-open-letter/",
        "/open-letter/autonomous-weapons-open-letter-2017/",
        "/open-letter/medical-lethal-autonomous-weapons-open-letter/",
        "/grant-program/global-institutions-governing-ai/",
        "/grant-program/mitigate-ai-driven-power-concentration/",
        "/grant-program/us-china-ai-governance-phd-fellowship/",
        "/grant-program/multistakeholder-engagement-for-safe-and-prosperous-ai/",
        "/resource/ai-policy/",
        "/resource/ai-policy-resources/",
        "/resource/introductory-resources-on-ai-risks/",
        "/resource/catastrophic-ai-scenarios/",
        "/document/policymaking-in-the-pause/",
        "/document/faiia-compare-to-aiara/",
    }
)
_TOPIC_PREFIXES = ("/ai-policy/", "/project_thread/fli-safety-index-")
_DOCUMENT_AI = re.compile(
    r"(?:^|[-/])ai(?:[-/]|$)|artificial|governance|autonomous|gpai|liability|safety-index|deepfake|nist|rmf",
    re.IGNORECASE,
)


class CatalogError(ValueError):
    """A catalog row or page failed the Future of Life Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for the apex futureoflife.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def is_topic_path(path: str) -> bool:
    """True for an HTML path about AI risk, AI policy, or AI governance."""
    bare = _bare_path(path or "")
    if bare in _EXACT_TOPIC_PATHS:
        return True
    if any(bare.startswith(prefix) for prefix in _TOPIC_PREFIXES):
        return True
    if bare.startswith("/document/") and _DOCUMENT_AI.search(bare) is not None:
        return True
    return False


def rights_from_page(page_text: str) -> str:
    """Return a reuse-licence label stated by the page, or unknown.

    ``creative_commons`` means the page states CC0, CC BY, or CC BY-SA.
    CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. The
    substrings "creative commons" and "cc-by" are not CC BY when
    NonCommercial, NoDerivatives, or ShareAlike follows. A public page, a
    copyright notice, an all-rights-reserved line, a terms link, and a photo
    credit are not a licence to copy the page. ``uk_ogl`` is used only when
    the page states the Open Government Licence. Script, style, and comment
    text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_text)
    plain = _plain(html).casefold()
    meta_text = " ".join(item.casefold() for item in _meta_contents(html))
    if _states_creative_commons(plain) or _states_creative_commons(meta_text):
        return RIGHTS_CREATIVE_COMMONS
    if OGL_PHRASE in plain:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, and a copyright year are not
    publication dates. A date inside script or style text does not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    html = _without_hidden(page_html)
    metas = _metas(html)
    for key in _MODIFIED_DATE_KEYS:
        metas.pop(key, None)
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key, ""))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_without_hidden(page_html))
    for key in _PUBLISHER_KEYS:
        publisher = _clean_text(metas.get(key, ""))
        if publisher and not publisher.startswith(("http://", "https://")):
            return publisher
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
    return validate_entry(record)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    if "p(doom)" in description.casefold():
        raise CatalogError("description must not store a p(doom) figure")
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
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
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    if "p(doom)" in entry["title"].casefold():
        raise CatalogError("title must not store a p(doom) figure")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Future of Life Institute page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OFFICIAL_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
        or not _html_page_path(path)
        or not is_topic_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Future of Life Institute AI page: {url}")
    return url


def _html_page_path(path: str) -> bool:
    if not path.startswith("/") or ".." in path or "\\" in path or "//" in path:
        return False
    bare = _bare_path(path)
    lowered = bare.casefold()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    for prefix in _BLOCKED_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "/"):
            return False
    return True


def _bare_path(path: str) -> str:
    if path != "/" and not path.endswith("/"):
        return path + "/"
    return path


def _states_creative_commons(plain: str) -> bool:
    text = plain.casefold().replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    text = _DISALLOWED_CC_URL.sub(" ", text)
    for pattern in (_CC0_PHRASE, _CC_BY_SA_PHRASE, _CC_BY_PHRASE, _CC_COPYING_URL):
        for match in pattern.finditer(text):
            window = text[max(0, match.start() - 160) : match.end() + 160]
            if _IMAGE_CREDIT.search(window) and _PAGE_GRANT.search(window) is None:
                continue
            return True
    return False


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


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


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


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
        if len(value) > MAX_DESCRIPTION_CHARS and path == "$.description":
            raise CatalogError("description is too long")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


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
