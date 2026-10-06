"""Metadata catalog of public SaferAI pages.

Each stored URL was confirmed with one bounded GET on www.safer-ai.org that
returned the page HTML. A row keeps the title, publisher, canonical URL, date,
and rights label. Page bodies, abstracts, and PDFs are not stored. The live
URL is stored as confirmed; a different rel=canonical does not replace it.

A Cloudflare challenge, a SiteGround captcha, an HTTP 202 challenge, an
Akamai 403, a non-HTML response, a robots disallow, or a redirect off this
host is not stored. Rights stays unknown unless the page states a reuse
licence. ``creative_commons`` means CC0 or CC BY-SA, including a page that
states CC BY together with one of those deeds. ``creative_commons_attribution``
means a CC BY deed that does not state NC, ND, or SA. CC BY-NC,
CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA stay their own tokens and are never
folded into those labels. A hyphen is a word boundary, so CC BY does not match
CC BY-NC. Public Domain Mark is not CC0. A copyright notice, All rights
reserved, a terms link, and the words Public or Disclosed are not licences.
``uk_ogl`` requires the British phrase open government licence.
``us_government_work`` requires a rights field that says the item is a US
government work. mit, apache-2.0, and mpl-2.0 stay their own tokens.

A page that does not state a publication date keeps the date unknown.
Updated, modified, and copyright years are not publication dates. Yoast's
datePublished clock is not a publication date; the visible Publication date
label is. This module does not fetch. It is not a belief collector, and
runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "saferai_pages"
CATALOG_FILENAME = "saferai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "SaferAI"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_ATTRIBUTION,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
SAFERAI_HOST = "www.safer-ai.org"
MAX_TEXT_CHARS = 400
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
        "summary",
        "text",
        "transcript",
        "transcript_text",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_PUBLICATION_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
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
_MONTH_NAME = (
    r"January|February|March|April|May|June|July|August|September|October|November|December"
)
_PUBLICATION_LABEL = re.compile(
    rf"(?is)<h6\b[^>]*>\s*publication\s+date\s*</h6>\s*"
    rf"<(?:div|p|span|time)\b[^>]*>\s*(?:({_MONTH_NAME})\s+(\d{{1,2}}),\s+(\d{{4}})|(\d{{4}}-\d{{2}}-\d{{2}}))"
)
_SITE_SUFFIXES = (
    " | saferai",
    " - saferai",
    " – saferai",
    " — saferai",
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
_BLOCKED_PREFIXES = (
    "/.well-known",
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
    "/xmlrpc.php",
)
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
)
_DASHES = str.maketrans(
    {
        "\u00a0": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# Longer deeds are listed first. A hyphen is not a word boundary here: the
# (?!-) lookahead stops licenses/by and CC BY from matching CC BY-NC.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])")),
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])")),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9-])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b)")),
    (
        "by-nc-nd",
        re.compile(
            r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "by-nc",
        re.compile(r"creative commons\s+attribution[\s-]+non[\s-]*commercial"),
    ),
    ("by-nd", re.compile(r"creative commons\s+attribution[\s-]+no[\s-]*deriv")),
    ("by-sa", re.compile(r"creative commons\s+attribution[\s-]+share[\s-]*alike")),
    (
        "by",
        re.compile(
            r"creative commons\s+attribution(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|sa|nc|nd)\b)"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero(?![a-z])"
        ),
    ),
    ("mark", re.compile(r"\bpublic domain mark\b")),
)
_URL_CODES = {
    "by": "by",
    "by-sa": "by-sa",
    "by-nc": "by-nc",
    "by-nd": "by-nd",
    "by-nc-sa": "by-nc-sa",
    "by-nc-nd": "by-nc-nd",
    "zero": "zero",
    "mark": "mark",
}
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_US_GOV_WORK = re.compile(r"\b(?:united states|u\.s\.|us)\s+government\s+work\b")
_NEGATED_US_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+work\b"
)
_MIT = re.compile(r"\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(
    r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b"
)
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")


class CatalogError(ValueError):
    """A catalog row or page failed the SaferAI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for the www.safer-ai.org host that returned HTML."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == SAFERAI_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge response.

    HTTP 202, a non-200 status, a Cloudflare or SiteGround challenge, and an
    Akamai 403 are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "sg-captcha":
                return False
            if name == "server" and "akamai" in token:
                return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> dict | None:
    """Return metadata when the response is page HTML on the SaferAI host.

    A challenge, an HTTP 202, an Akamai 403, a non-HTML body, or an off-host
    URL is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary, so CC BY-NC is not CC BY and licenses/by does not match
    licenses/by-nc. Mixed restricted and permissive text stays unknown.
    Mixed mit or apache plus a permissive CC deed stays unknown. Public
    Domain Mark is not CC0. A generic creativecommons.org/licenses/ URL, a
    copyright notice, All rights reserved, a terms link, and the words Public
    or Disclosed are not licences. A .gov, .edu, or .org host is not a licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    ld_values = _jsonld_rights_and_licenses(page_text)
    visible = _without_hidden(page_text)
    plain = _plain(visible).casefold().translate(_DASHES)
    blobs = [plain, *(_meta_values(visible, _LICENSE_META)), *ld_values, *_hrefs(visible)]
    codes: set[str] = set()
    mit = False
    apache = False
    mpl = False
    for blob in blobs:
        folded = blob.casefold().translate(_DASHES)
        codes.update(_cc_codes(folded))
        mit = mit or bool(_MIT.search(folded) or _MIT_URL.search(folded))
        apache = apache or bool(_APACHE.search(folded) or _APACHE_URL.search(folded))
        mpl = mpl or bool(_MPL.search(folded) or _MPL_URL.search(folded))
    software = {name for name, present in (("mit", mit), ("apache", apache), ("mpl", mpl)) if present}
    ogl = _OGL_PHRASE.search(plain) is not None
    us_gov = _states_us_government_work(page_text, visible)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    other = bool(software or ogl or us_gov)
    if restricted and (permissive or other):
        return RIGHTS_UNKNOWN
    if permissive and other:
        return RIGHTS_UNKNOWN
    if len(software) > 1 or (software and (ogl or us_gov)) or (ogl and us_gov):
        return RIGHTS_UNKNOWN
    if restricted:
        named = restricted - {"mark"}
        if named == {"by-nc"}:
            return RIGHTS_CC_BY_NC
        if named == {"by-nd"}:
            return RIGHTS_CC_BY_ND
        if named == {"by-nc-nd"}:
            return RIGHTS_CC_BY_NC_ND
        if named == {"by-nc-sa"}:
            return RIGHTS_CC_BY_NC_SA
        return RIGHTS_UNKNOWN
    if permissive:
        if permissive <= {"by"}:
            return RIGHTS_CC_ATTRIBUTION
        if permissive <= _PERMISSIVE and permissive & {"by-sa", "zero"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_UNKNOWN
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if ogl:
        return RIGHTS_UK_OGL
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    The visible Publication date label is the publication date. article:modified_time,
    og:updated_time, a last-updated line, a copyright year, and Yoast datePublished
    are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    for match in _PUBLICATION_LABEL.finditer(visible):
        if match.group(4):
            found = _iso_day(match.group(4))
        else:
            found = _calendar_day(match.group(1), match.group(2), match.group(3))
        if found:
            return found
    metas = _metas(visible)
    for key in _PUBLICATION_META:
        found = _iso_day(metas.get(key, ""))
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
    """Return SaferAI when the page names that publisher.

    A person named on the page is not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _clean_text(_metas(_without_hidden(page_html)).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
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
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or not description.strip() or description != description.strip():
        raise CatalogError("description is required")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
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
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError("rights must be a known label or unknown")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public SaferAI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != SAFERAI_HOST
        or host != SAFERAI_HOST
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
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public SaferAI page: {url}")
    return url


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    lowered = path.lower()
    bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return not bare.startswith(_BLOCKED_PREFIXES)


def _cc_codes(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("code") or match.group("pd")
        if code:
            codes.add(_URL_CODES.get(code, code))
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _states_us_government_work(page_html: str, visible: str) -> bool:
    """True only when a rights field says the item is a US government work."""

    fields = list(_meta_values(visible, _RIGHTS_META))
    for value in _jsonld_values(page_html, "rights"):
        fields.append(value)
    for raw in fields:
        text = _plain(raw).casefold().translate(_DASHES)
        if not text or _NEGATED_US_GOV.search(text):
            continue
        if _US_GOV_WORK.search(text):
            return True
    return False


def _jsonld_rights_and_licenses(page_html: str) -> list[str]:
    found: list[str] = []
    for key in ("license", "rights"):
        found.extend(_jsonld_values(page_html, key))
    return found


def _jsonld_values(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        text = block.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        _collect_key(payload, key.casefold(), found)
    return found


def _collect_key(payload: object, key: str, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_key(item, key, found)
        return
    if not isinstance(payload, dict):
        return
    for name, value in payload.items():
        if str(name).casefold() == key and isinstance(value, str):
            found.append(value)
        elif isinstance(value, (dict, list)):
            _collect_key(value, key, found)


def _calendar_day(month: str, day: str, year: str) -> str | None:
    try:
        return date(int(year), _MONTHS[month.casefold()], int(day)).isoformat()
    except (KeyError, ValueError):
        return None


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    value = match.group(1)
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
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


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    lowered = text.casefold()
    for suffix in _SITE_SUFFIXES:
        if lowered.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(_without_hidden(page_text))


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, keys: frozenset[str] | tuple[str, ...]) -> list[str]:
    wanted = {key.lower() for key in keys}
    found: list[str] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in wanted and attrs.get("content"):
            found.append(attrs["content"])
    return found


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
