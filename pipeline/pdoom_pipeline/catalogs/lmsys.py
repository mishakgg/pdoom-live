"""Metadata catalog of public LMSYS pages.

Each stored URL was confirmed with one bounded GET of HTML on www.lmsys.org.
https://lmsys.org redirects to that host. A row keeps the title, publisher,
canonical URL, date, and rights label. Conversation logs, model outputs,
leaderboard chart data, and page text are not stored. A Cloudflare challenge,
a captcha, HTTP 202, an Akamai 403, a non-HTML response, or an off-host
redirect is not stored.

``creative_commons`` means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND are their own tokens (``cc_by_nc``, ``cc_by_nd``,
``cc_by_nc_sa``, ``cc_by_nc_nd``) and are never folded into ``creative_commons``.
A page that states both a restricted deed and a permissive deed stays unknown.
A hyphen is a word boundary, so CC BY does not match CC BY-NC, and
licenses/by does not match licenses/by-nc. A generic creativecommons.org/licenses/
URL is not a permissive deed. The Public Domain Mark is not CC0. An anchor
whose visible text says CC BY, CC BY-SA, or CC0 while the link is a restricted
or Public Domain Mark URL stays unknown. apache-2.0 and mit are their own
tokens and are not folded into ``creative_commons``.
A copyright notice, All rights reserved, a terms link, and a host name are
not licences.

A page that does not state a publication date keeps the date unknown.
Updated, modified, and copyright years are not publication dates. The live
URL is stored as confirmed; a different rel=canonical does not replace it.
This module does not fetch and it is not a belief collector. runner_wired
stays false.
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

CATALOG_ID = "lmsys_pages"
CATALOG_FILENAME = "lmsys_pages.json"
RUNNER_WIRED = False
PUBLISHER = "LMSYS Org"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_UNKNOWN,
    }
)
UNKNOWN_DATE = "unknown"
STORED_HOST = "www.lmsys.org"
OFFICIAL_HOSTS = frozenset({"lmsys.org", "www.lmsys.org"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"((?:\\.|[^"\\])*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_LINKISH = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_SITE_SUFFIXES = (
    " - LMSYS Org",
    " | LMSYS Org",
    " – LMSYS Org",
    " — LMSYS Org",
    " - LMSYS",
    " | LMSYS",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "cf-turnstile",
    "sorry, you have been blocked",
    "verify you are human",
    "please complete the security check",
    "akamaighost",
    "errors.edgesuite.net",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".jsonl",
    ".xml",
    ".txt",
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
    ".js",
    ".css",
    ".woff",
    ".woff2",
    ".parquet",
    ".arrow",
    ".safetensors",
    ".bin",
)
_BLOCKED_PREFIXES = ("/_next", "/images", "/api", "/static", "/fonts", "/wp-admin", "/wp-content")
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
_MONTH_DATE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
    r")\s+(\d{1,2}),?\s+(\d{4})\b",
    re.I,
)
_DASHES = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# Longer deeds are listed first. A hyphen is a non-word character, so a bare
# word boundary after "by" would also match "by-nc". The CC BY pattern refuses
# a following NC, ND, or SA token. licenses/by refuses a following hyphen.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])",
    re.I,
)
_TEXT_CODES = (
    ("by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("by-nc-sa", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    ("by-sa", re.compile(r"\bcc[\s-]*by[\s-]*sa\b")),
    (
        "zero",
        re.compile(
            r"\bcc[\s-]*0\b|\bcc[\s-]*zero\b|"
            r"\bcreative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    ("by", re.compile(r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)")),
)
_RESTRICTED_TOKENS = (
    ("by-nc-nd", RIGHTS_CC_BY_NC_ND),
    ("by-nc-sa", RIGHTS_CC_BY_NC_SA),
    ("by-nc", RIGHTS_CC_BY_NC),
    ("by-nd", RIGHTS_CC_BY_ND),
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_GRANT = re.compile(
    r"(?i)\b(?:licensed|released|made available|available) under\b.{0,180}"
)
_MIT_PHRASE = re.compile(r"\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit\b")
_APACHE_PHRASE = re.compile(
    r"\bapache licen[cs]e\b|(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
)
_MIT_URL = re.compile(
    r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])",
    re.I,
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])",
    re.I,
)
_EXACT_MIT = frozenset({"mit", "mit-license", "mit-licence"})
_EXACT_APACHE = frozenset({"apache-2.0", "apache-2", "apache2.0"})
# Leaderboard rows write model licences as hyphenated version tokens such as
# CC-BY-NC-4.0 or CC-BY-SA 3.0. Those chart cells are not the page licence.
# A grant such as "released under CC-BY-NC-4.0" is scanned separately.
_CHART_DEED = re.compile(
    r"\bcc-by(?:-nc)?(?:-sa|-nd)?(?:-\d+(?:\.\d+)?| \d+(?:\.\d+)?)\b"
)
# Visible CC BY, CC BY-SA, or CC0 on a restricted or Public Domain Mark URL.
_DECEPTIVE_LABEL = re.compile(
    r"\bcc[\s-]*by[\s-]*sa\b"
    r"|\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
    r"|\bcc[\s-]*0\b|\bcc0\b|\bcc[\s-]*zero\b"
)
_DECEPTIVE_HREF = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?:by-nc-nd|by-nc-sa|by-nc|by-nd)|publicdomain/mark)"
    r"(?![a-z0-9-])",
    re.I,
)


class CatalogError(ValueError):
    """A catalog row or page failed the LMSYS page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    previous = ""
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        if url < previous:
            raise CatalogError("entries must be ordered by canonical URL")
        seen.add(url)
        previous = url
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be a short reuse-licence token or unknown")
    return entry


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
        raise CatalogError(f"canonical URL must be a public LMSYS page: {url}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != STORED_HOST
        or host != STORED_HOST
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
        raise CatalogError(f"canonical URL must be a public LMSYS page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    """True for lmsys.org and www.lmsys.org.

    https://lmsys.org redirects to www.lmsys.org. Stored pages use the www host
    that returned the HTML. Any other hostname is off-host.
    """

    host = (hostname or "").strip().lower().rstrip(".")
    return bool(host) and host in OFFICIAL_HOSTS and not hostname_is_blocked(host)


def official_page_url(url: object) -> str | None:
    """Return a normalized www.lmsys.org page URL, or None when it is off-host."""

    if not isinstance(url, str) or not url or url != url.strip():
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or host != STORED_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or hostname_is_blocked(host)
    ):
        return None
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    if "//" in path or ".." in path or "\\" in path:
        return None
    normalized = f"https://{STORED_HOST}" if path == "/" else f"https://{STORED_HOST}{path}"
    try:
        return validate_canonical_url(normalized)
    except CatalogError:
        return None


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
    plain = _plain_text(page_html).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or a 202 response."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            folded = str(key).casefold()
            haystack = str(value).casefold()
            if folded == "cf-mitigated" and "challenge" in haystack:
                return False
            if folded == "server" and "akamaighost" in haystack:
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
    """Return metadata when the response is LMSYS page HTML.

    HTTP 202, a challenge, an HTTP 403, a non-HTML body, and an off-host URL
    are not stored. The title comes from the HTML. Chart data is not copied.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    confirmed = official_page_url(page_url)
    if confirmed is None:
        return None
    assert isinstance(page_html, str)
    return page_record(page_html, page_url=confirmed)


def _deceptive_permissive_anchor(visible_html: str) -> bool:
    """True when anchor text says CC BY, CC BY-SA, or CC0 but the href does not."""

    for attrs, inner in _ANCHOR.findall(visible_html):
        href = _attrs(f"<a{attrs}>").get("href", "")
        if not href or _DECEPTIVE_HREF.search(_normalize_licence_text(href)) is None:
            continue
        label = _plain_text(inner).casefold().translate(_DASHES)
        if _DECEPTIVE_LABEL.search(label):
            return True
    return False


def rights_from_page(page_text: str) -> str:
    """Return a rights token from a reuse licence the page itself states.

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only. A sole CC BY-NC,
    CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND deed stays its own token. When a
    restricted deed and a permissive deed are both present, the label stays
    unknown. An anchor whose text says CC BY, CC BY-SA, or CC0 and whose href
    is a restricted or Public Domain Mark URL stays unknown. The Public Domain
    Mark is not CC0. apache-2.0 and mit stay their own tokens. A copyright
    notice, All rights reserved, a terms link, a host name, and a model-licence
    cell are not the page licence. Script and style text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _HIDDEN.sub(" ", page_text)
    plain = _plain_text(visible).casefold().translate(_DASHES)
    if _deceptive_permissive_anchor(visible):
        return RIGHTS_UNKNOWN
    # Chart cells are removed from the prose scan. Grant sentences keep them.
    codes = _cc_codes(_CHART_DEED.sub(" ", plain))
    for href in _hrefs(visible):
        codes.update(_cc_codes(_normalize_licence_text(href)))
    for match in _GRANT.finditer(plain):
        codes.update(_cc_codes(_normalize_licence_text(match.group(0))))
    restricted = [token for code, token in _RESTRICTED_TOKENS if code in codes]
    permissive = bool(codes & _PERMISSIVE)
    if restricted and permissive:
        return RIGHTS_UNKNOWN
    if restricted:
        return restricted[0]
    if "mark" in codes or "public domain mark" in plain:
        return RIGHTS_UNKNOWN
    scopes = _licence_scopes(page_text, visible, plain)
    mit = any(_states_mit(scope) for scope in scopes)
    apache = any(_states_apache(scope) for scope in scopes)
    if permissive and (mit or apache):
        return RIGHTS_UNKNOWN
    if mit and apache:
        return RIGHTS_UNKNOWN
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, and dates on listed items are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_HIDDEN.sub(" ", page_html))
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _parse_publication_value(metas.get(key, ""))
        if parsed:
            return parsed
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for match in _DATE_PUBLISHED.finditer(blob):
            parsed = _parse_publication_value(match.group(1))
            if parsed and parsed not in found:
                found.append(parsed)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    candidates: list[str] = []
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            candidates.append(metas[key])
    title_tag = _TITLE.search(visible)
    if title_tag:
        candidates.append(_TAG.sub(" ", title_tag.group(1)))
    heading = _H1.search(visible)
    if heading:
        candidates.append(_TAG.sub(" ", heading.group(1)))
    cleaned = [title for item in candidates if (title := _clean_title(item))]
    for title in cleaned:
        if title.casefold() not in {"lmsys org", "lmsys"}:
            return title
    if cleaned:
        return cleaned[0]
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return LMSYS Org when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    site = _metas(visible).get("og:site_name", "")
    title_tag = _TITLE.search(visible)
    title = title_tag.group(1) if title_tag else ""
    blob = _plain_text(" ".join((site, title, visible))).casefold()
    if "lmsys org" in blob:
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body, conversation text, model
    output, or leaderboard chart data. ``page_url`` is the live URL that was
    fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    confirmed = official_page_url(page_url)
    if confirmed is None:
        raise CatalogError("canonical URL must be a public LMSYS page")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed,
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _public_path(path: str) -> bool:
    if path == "":
        return True
    if path == "/" or not path.startswith("/") or path.endswith("/"):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return not lowered.startswith(_BLOCKED_PREFIXES)


def _cc_codes(text: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(text):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code.casefold())
    for code, pattern in _TEXT_CODES:
        if pattern.search(text):
            codes.add(code)
    if "creative commons" in text:
        if re.search(r"attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv", text):
            codes.add("by-nc-nd")
        if re.search(r"attribution[\s-]*non[\s-]*commercial[\s-]*share", text):
            codes.add("by-nc-sa")
        if re.search(r"attribution[\s-]*non[\s-]*commercial\b", text):
            codes.add("by-nc")
        if re.search(r"attribution[\s-]*no[\s-]*deriv", text):
            codes.add("by-nd")
        if re.search(
            r"attribution[\s-]*share[\s-]*alike\b(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv))",
            text,
        ):
            codes.add("by-sa")
        if re.search(
            r"\battribution\b(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike|nc|nd|sa))",
            text,
        ):
            codes.add("by")
    if re.search(r"\bpublic domain mark\b", text):
        codes.add("mark")
    return codes


def _licence_scopes(page_html: str, visible: str, plain: str) -> list[str]:
    scopes: list[str] = []
    metas = _metas(visible)
    for key in _LICENSE_META:
        if metas.get(key):
            scopes.append(metas[key])
    for tag in _LINKISH.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").casefold().split()
        if "license" in rel or "licence" in rel:
            href = attrs.get("href", "")
            if href:
                scopes.append(href)
    for blob in _LDJSON.findall(page_html):
        for match in _LD_LICENSE.finditer(blob):
            scopes.append(match.group(1).replace(r"\/", "/"))
    for match in _GRANT.finditer(plain):
        scopes.append(match.group(0))
    return scopes


def _states_mit(value: str) -> bool:
    text = _normalize_licence_text(value).strip()
    if text in _EXACT_MIT:
        return True
    return _MIT_URL.search(text) is not None or _MIT_PHRASE.search(text) is not None


def _states_apache(value: str) -> bool:
    text = _normalize_licence_text(value).strip()
    if text in _EXACT_APACHE:
        return True
    return _APACHE_URL.search(text) is not None or _APACHE_PHRASE.search(text) is not None


def _parse_publication_value(raw: str) -> str | None:
    if not isinstance(raw, str):
        return None
    text = unescape(raw).strip()
    if not text:
        return None
    iso = _DATE_PREFIX.match(text)
    if iso and _iso_date(iso.group(1)):
        return iso.group(1)
    match = _MONTH_DATE.search(text)
    if match is None:
        return None
    month = _MONTHS.get(match.group(1).casefold())
    if month is None:
        return None
    try:
        parsed = date(int(match.group(3)), month, int(match.group(2)))
    except ValueError:
        return None
    return parsed.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _normalize_licence_text(value: str) -> str:
    text = unescape(value).casefold().replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text)


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    for suffix in _SITE_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(_HIDDEN.sub(" ", page_text))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINKISH.findall(page_html):
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
