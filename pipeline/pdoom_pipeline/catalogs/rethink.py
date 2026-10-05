"""Metadata catalog of public AI-related pages on rethinkpriorities.org.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, chart data, and quotes are not stored. A row is
recorded only after one bounded GET returned the page HTML. A Cloudflare
challenge, a SiteGround captcha, an HTTP 202, an Akamai block, a robot
interstitial, or a redirect off rethinkpriorities.org is not stored. This
module does not fetch.

Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA. Those
three are labeled creative_commons. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A hyphen is a word boundary, so CC BY does not
match CC BY-NC. Longer restricted deeds are checked first, and a restricted
deed wins when it appears beside a permissive one. A public-domain mark is
not CC0. A public page, a copyright notice, All rights reserved, or a terms
link is not a licence. uk_ogl is used only when the page states the Open
Government Licence. us_government_work is used only when a rights field says
the item is a US government work.

A missing date is unknown. Updated, modified, and copyright years are not
publication dates. runner_wired stays false. This catalog is not a belief
collector.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "rethink_pages"
CATALOG_FILENAME = "rethink_pages.json"
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
OFFICIAL_HOST = "rethinkpriorities.org"
PUBLISHER = "Rethink Priorities"
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
        "pdoom",
        "p_doom",
        "pdf",
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
_PATH = re.compile(r"^/(?:research-area/)?[a-z0-9]+(?:-[a-z0-9]+)*/$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_RIGHTS_DD = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
)
_RIGHTS_META = frozenset(
    {
        "rights",
        "dc.rights",
        "dcterms.rights",
        "license",
        "dc.license",
        "dcterms.license",
    }
)
_SITE_SUFFIXES = (
    " | Rethink Priorities",
    " – Rethink Priorities",
    " — Rethink Priorities",
    " - Rethink Priorities",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".epub",
    ".mp3",
    ".mp4",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_BLOCKED_PREFIXES = ("team-member", "wp-admin", "wp-content", "wp-includes", "wp-json", "feed")
# Longer restricted deeds are listed first. A hyphen is a boundary, so the
# "by" alternative is not allowed to consume "by-nc" or "by-nd".
_CC_LICENSE_URL = re.compile(
    r"(?<![a-z0-9])creativecommons\.org/licenses/"
    r"(by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"(?=/|[?#]|$)"
)
_CC_PD_URL = re.compile(
    r"(?<![a-z0-9])creativecommons\.org/publicdomain/(zero|mark)(?=/|[?#]|$)"
)
# A licence statement or a versioned deed counts. "CC-BY Author Name" is a
# citation of someone else's note, not a licence for this page.
_UNDER = (
    r"(?:licen[cs]ed|released|available|published)\s+under\s+"
    r"(?:the\s+)?(?:terms\s+of\s+)?(?:a\s+|the\s+)?"
)
_NOT_NAME = r"(?!\s*[a-z])"
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("by-nc-sa", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    (
        "by-nc-nd",
        re.compile(
            r"creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "by-nc",
        re.compile(r"creative\s+commons\s+attribution[\s-]*non[\s-]*commercial\b"),
    ),
    (
        "by-nd",
        re.compile(r"creative\s+commons\s+attribution[\s-]*no[\s-]*deriv"),
    ),
    (
        "by-sa",
        re.compile(
            _UNDER + r"cc[\s-]*by[\s-]*sa\b"
            r"|\bcc[\s-]*by[\s-]*sa\b"
            + _NOT_NAME
            + r"|creative\s+commons\s+attribution[\s-]*share[\s-]*alike\b"
        ),
    ),
    ("cc0", re.compile(r"\bcc[\s-]*0\b|\bcc[\s-]*zero\b|\bcreative\s+commons\s+zero\b")),
    ("mark", re.compile(r"\bpublic\s+domain\s+mark\b")),
    (
        "by",
        re.compile(
            _UNDER + r"cc[\s-]*by\b(?![\s-]*(?:nc|nd)\b)"
            r"|\bcc[\s-]*by\b(?![\s-]*(?:nc|nd)\b)"
            + _NOT_NAME
            + r"|creative\s+commons\s+attribution\b(?![\s-]*(?:non|no[\s-]*deriv|share))"
        ),
    ),
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "cc0", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_OGL = re.compile(r"\bopen\s+government\s+licence\b")
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "cf-mitigated",
    "just a moment",
    "attention required! | cloudflare",
    "performing security verification",
    "enable javascript and cookies",
    "sgcaptcha",
    "sg-captcha",
    "siteground captcha",
    "/.well-known/sgcaptcha",
    "errors.edgesuite.net",
    "akamaighost",
    "akamai-ghost",
    "verify you are human",
    "are you a robot",
    "robot interstitial",
)


class CatalogError(ValueError):
    """A catalog row or page failed the Rethink Priorities page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_rethink_host(hostname: str) -> bool:
    """True only for the official rethinkpriorities.org host."""
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
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:12000].casefold()
    if any(marker in head for marker in _CHALLENGE_MARKERS):
        return True
    title = _TITLE.search(head)
    if title is None:
        return False
    label = _plain(title.group(1)).casefold()
    if label in {"just a moment...", "access denied", "attention required! | cloudflare"}:
        return True
    if "akamai" in head and "access denied" in label:
        return True
    return False


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from HTML on the official host that is not a challenge."""

    if status == 202 or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html):
        return False
    confirmed = final_url if final_url is not None else page_url
    if _host_of(confirmed) != OFFICIAL_HOST or not official_rethink_host(_host_of(confirmed)):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            folded = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in folded:
                return False
            if "captcha" in name or ("captcha" in folded and "siteground" in folded):
                return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
) -> dict | None:
    """Return metadata when the response is the page HTML.

    A challenge page, an HTTP 202, a non-HTML body, or a redirect off
    rethinkpriorities.org is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
    ):
        return None
    assert isinstance(page_html, str)
    confirmed = final_url if final_url is not None else page_url
    return page_record(page_html, page_url=confirmed)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    creative_commons is only CC0, CC BY, or CC BY-SA. Noncommercial,
    no-derivatives, and the public-domain mark stay unknown. A restricted
    deed wins when a permissive deed is also present.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    plain = _plain(visible)
    blobs = [plain, *_hrefs(visible), *_rights_fields(visible, page_text)]
    codes = _cc_codes("\n".join(blobs))
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    if _OGL.search(plain.casefold()):
        return RIGHTS_UK_OGL
    rights_text = "\n".join(_rights_fields(visible, page_text)).casefold()
    if rights_text and not _NEGATED_GOV_WORK.search(rights_text) and _GOV_WORK.search(rights_text):
        return RIGHTS_US_GOVERNMENT_WORK
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
        if _usable_title(title):
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    title_tag = _TITLE.search(visible)
    if title_tag and PUBLISHER in _clean_text(title_tag.group(1)):
        return PUBLISHER
    if re.search(rf"\b{re.escape(PUBLISHER)}\b", _plain(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the URL
    that returned HTML. A different rel=canonical does not replace it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
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
        raise CatalogError("canonical URL must be an https rethinkpriorities.org page")
    parsed = _parse_https_url(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https rethinkpriorities.org page: {url}")
    host, path = parsed
    if not official_rethink_host(host) or not _html_path(path):
        raise CatalogError(f"canonical URL must be an https rethinkpriorities.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _parse_https_url(url: str) -> tuple[str, str] | None:
    if not url.startswith("https://"):
        return None
    rest = url[len("https://") :]
    if not rest or any(char in rest for char in "?#"):
        return None
    slash = rest.find("/")
    if slash == -1:
        authority, path = rest, "/"
    else:
        authority, path = rest[:slash], rest[slash:]
    if not authority or "@" in authority or ":" in authority or authority.endswith("."):
        return None
    return authority.lower(), path


def _host_of(url: str) -> str:
    parsed = _parse_https_url(url) if isinstance(url, str) else None
    if parsed is None:
        return ""
    return parsed[0]


def _html_path(path: str) -> bool:
    if not path.startswith("/") or ".." in path or "\\" in path or "//" in path or "%" in path:
        return False
    parts = [part for part in path.split("/") if part]
    if any(part in _BLOCKED_PREFIXES or part.startswith("wp-") for part in parts):
        return False
    bare = path[:-1] if path.endswith("/") and path != "/" else path
    if bare.lower().endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _PATH.fullmatch(path) is not None


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
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    return title.casefold() not in {"research", "home", "page not found"}


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


def _meta_values(html: str, names: tuple[str, ...] | frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _rights_fields(visible: str, page_text: str) -> list[str]:
    fields: list[str] = []
    metas = _metas(visible)
    for key in _RIGHTS_META:
        if metas.get(key):
            fields.append(metas[key])
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel or "licence" in rel:
            if attrs.get("href"):
                fields.append(attrs["href"])
    for block in _RIGHTS_DD.findall(visible):
        fields.append(_plain(block))
    for blob in _LDJSON.findall(page_text):
        for key in ("license", "rights"):
            for match in re.finditer(rf'"{key}"\s*:\s*"(.*?)"', blob, re.I):
                fields.append(match.group(1).replace("\\/", "/"))
    return fields


def _cc_codes(value: str) -> set[str]:
    folded = value.casefold().replace("–", "-").replace("—", "-")
    codes: set[str] = set()
    for match in _CC_LICENSE_URL.finditer(folded):
        codes.add(match.group(1))
    for match in _CC_PD_URL.finditer(folded):
        code = match.group(1)
        codes.add("cc0" if code == "zero" else "mark")
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
