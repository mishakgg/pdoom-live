"""Metadata catalog of public Palisade Research pages.

Each stored URL was confirmed with one bounded GET that returned HTML from
palisaderesearch.org. www.palisaderesearch.org answered HTTP 522 and is not a
stored host. A Cloudflare challenge, a SiteGround sg-captcha, an HTTP 202
challenge, an Akamai 403, a robots disallow, a redirect off-host, or a
non-HTML response is not stored. Rows keep the title, publisher, canonical
URL, date, and rights label. Page text is not stored.

Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means only CC0, CC BY, or CC BY-SA.
``creative_commons_attribution`` means CC BY without NC, ND, or SA.
CC BY-NC, CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA stay their own tokens and are
never folded into those labels. A hyphen is a word boundary, so CC BY does not
match CC BY-NC, and licenses/by does not match licenses/by-nc. Restricted
deeds are checked first. When a restricted deed and a permissive deed both
appear, rights stay unknown. Public Domain Mark is not CC0. A copyright
notice, All rights reserved, a terms link, and the words Public or Disclosed
are not licences. A .gov, .edu, or .org host is not a licence. ``uk_ogl``
requires the British phrase "open government licence". ``us_government_work``
requires a rights field that says the item is a US government work. mit,
apache-2.0, and mpl-2.0 stay their own tokens. mit or apache mixed with a
permissive CC deed stays unknown.

A page that does not state a publication date keeps the date unknown. Updated,
modified, and copyright years are not publication dates. A non-midnight site
publish clock is not a publication date. The live URL is stored as confirmed;
a different rel=canonical does not replace it. This module does not fetch and
it is not a belief collector. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "palisade_pages"
CATALOG_FILENAME = "palisade_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Palisade Research"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_BY,
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
UNKNOWN_DATE = "unknown"
PALISADE_HOST = "palisaderesearch.org"
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STAMP = re.compile(
    r"^(\d{4}-\d{2}-\d{2})"
    r"(?:[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"((?:\\.|[^"\\])*)"')
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"((?:\\.|[^"\\])*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_REFRESH = re.compile(r"(?is)<meta\b[^>]*http-equiv\s*=\s*['\"]refresh['\"]")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "citation_date",
    "dcterms.issued",
)
_LICENSE_META_KEYS = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights.license",
    }
)
_SITE_SUFFIXES = (
    " | Palisade Research",
    " - Palisade Research",
    " – Palisade Research",
    " — Palisade Research",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "cf-browser-verification",
    "checking your browser",
    "cdn-cgi/challenge",
    "sg-captcha",
    "sgcaptcha",
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
    ".css",
    ".js",
)
_BLOCKED_PREFIXES = ("/wp-admin", "/wp-content", "/wp-includes", "/wp-json", "/assets", "/cdn-cgi")
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
# Longer restricted deeds are listed before CC BY. `(?!-)` keeps CC BY from
# matching CC BY-NC, and licenses/by from matching licenses/by-nc.
_TEXT_DEEDS = (
    ("cc_by_nc_nd", re.compile(r"(?i)\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nc(?:\s+|-\s*)nd\b")),
    ("cc_by_nc_sa", re.compile(r"(?i)\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nc(?:\s+|-\s*)sa\b")),
    ("cc_by_nc", re.compile(r"(?i)\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nc\b(?!-)")),
    ("cc_by_nd", re.compile(r"(?i)\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nd\b(?!-)")),
    ("cc_by_sa", re.compile(r"(?i)\bcc(?:\s+|-\s*)by(?:\s+|-\s*)sa\b")),
    (
        "cc_by_nc_nd",
        re.compile(
            r"(?i)creative commons attribution(?:\s*|-)+non-?commercial(?:\s*|-)+no-?deriv"
        ),
    ),
    (
        "cc_by_nc_sa",
        re.compile(
            r"(?i)creative commons attribution(?:\s*|-)+non-?commercial(?:\s*|-)+share-?alike"
        ),
    ),
    (
        "cc_by_nc",
        re.compile(
            r"(?i)creative commons attribution(?:\s*|-)+non-?commercial\b(?![\s-]*(?:share-?alike|no-?deriv))"
        ),
    ),
    ("cc_by_nd", re.compile(r"(?i)creative commons attribution(?:\s*|-)+no-?deriv")),
    ("cc_by_sa", re.compile(r"(?i)creative commons attribution(?:\s*|-)+share-?alike")),
    (
        "cc_by",
        re.compile(
            r"(?i)creative commons attribution(?!-)(?!\s*-?\s*(?:non-?commercial|no-?deriv|share-?alike))"
        ),
    ),
    (
        "cc0",
        re.compile(
            r"(?i)(?<![a-z0-9])cc0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero\b"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    ("cc_by", re.compile(r"(?i)\bcc(?:\s+|-\s*)by\b(?!-)")),
    ("mark", re.compile(r"(?i)public\s+domain\s+mark\b")),
)
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_MIT = re.compile(
    r"(?i)(?<![a-z0-9])mit[\s-]+licen[cs]e\b"
    r"|licensed under (?:the )?mit\b"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
)
_APACHE = re.compile(
    r"(?i)apache[\s-]*2\.0\b"
    r"|apache[\s-]+licen[cs]e(?:[\s,]+version)?[\s-]+2(?:\.0)?\b"
    r"|apache\.org/licenses/license-2\.0"
)
_MPL = re.compile(
    r"(?i)(?<![a-z0-9])mpl[\s-]*2\.0\b"
    r"|mozilla public licen[cs]e[\s-]+2\.0\b"
    r"|mozilla\.org/mpl/2\.0(?![a-z0-9-])"
)
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_URL_LICENSE = {
    "by": "cc_by",
    "by-sa": "cc_by_sa",
    "by-nc": "cc_by_nc",
    "by-nd": "cc_by_nd",
    "by-nc-sa": "cc_by_nc_sa",
    "by-nc-nd": "cc_by_nc_nd",
}
_RESTRICTED = frozenset({"cc_by_nc", "cc_by_nd", "cc_by_nc_nd", "cc_by_nc_sa", "mark"})
_PERMISSIVE = frozenset({"cc0", "cc_by", "cc_by_sa"})
_SOFTWARE = {
    "mit": RIGHTS_MIT,
    "apache-2.0": RIGHTS_APACHE,
    "mpl-2.0": RIGHTS_MPL,
}
_DEED_LABELS = {
    "cc_by_nc": RIGHTS_CC_BY_NC,
    "cc_by_nd": RIGHTS_CC_BY_ND,
    "cc_by_nc_nd": RIGHTS_CC_BY_NC_ND,
    "cc_by_nc_sa": RIGHTS_CC_BY_NC_SA,
}


class CatalogError(ValueError):
    """A catalog row or page failed the Palisade Research page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


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
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if len(order) > 1 and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict):
        raise CatalogError("entry must be an object")
    _reject_stored_body(entry)
    if set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_date(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Palisade Research page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != PALISADE_HOST
        or host != PALISADE_HOST
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
        raise CatalogError(f"canonical URL is not a public Palisade Research page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == PALISADE_HOST and not hostname_is_blocked(host)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:4000].casefold()
    return any(marker in sample for marker in _CHALLENGE_MARKERS)


def is_redirect_document(page_html: str) -> bool:
    """True when the HTML is an on-page refresh rather than the page itself."""

    if not isinstance(page_html, str):
        return False
    return _REFRESH.search(page_html[:4000]) is not None


def robots_disallows(robots_text: str, path: str) -> bool:
    """True when robots.txt disallows ``path`` for the collector or for ``*``.

    A disallowed path is not stored. An empty robots file allows the path.
    """

    if not isinstance(robots_text, str) or not isinstance(path, str):
        raise CatalogError("robots text and path must be strings")
    target = path if path.startswith("/") else f"/{path}"
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, list(rules)))
        agents = []
        rules = []

    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules:
                flush()
            agents.append(value.lower())
            continue
        if key in {"allow", "disallow"} and agents:
            rules.append((key, value))
    flush()
    chosen: list[tuple[str, str]] | None = None
    wildcard: list[tuple[str, str]] | None = None
    for group_agents, group_rules in groups:
        for agent in group_agents:
            if agent == "*":
                wildcard = group_rules
            elif agent.startswith("pdoom"):
                chosen = group_rules
    selected = chosen if chosen is not None else wildcard
    if not selected:
        return False
    allowed = 0
    disallowed = 0
    for kind, prefix in selected:
        if prefix and target.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return disallowed > allowed


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict[str, str] | None = None,
    robots_text: str | None = None,
    path: str | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or a disallow.

    HTTP 202, HTTP 403 (including an Akamai 403), a Cloudflare challenge, and
    a SiteGround sg-captcha do not confirm a row.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html) or is_redirect_document(page_html):
        return False
    if robots_text is not None and path is not None and robots_disallows(robots_text, path):
        return False
    lowered = page_html[:8000].casefold()
    if "<html" not in lowered and "<!doctype html" not in lowered:
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "sg-captcha":
                return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict[str, str] | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when the response is the page HTML.

    A challenge, an HTTP 202, an Akamai 403, a robots disallow, an off-host
    URL, or a non-HTML response is not stored.
    """

    path = urlparse(page_url).path or "/"
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        robots_text=robots_text,
        path=path,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted phrases and URLs are checked before permissive ones. CC BY-NC
    is not CC BY. A by-nc URL is not ``creative_commons``. Public Domain Mark
    is not CC0. A generic creativecommons.org/licenses/ URL is not a deed.
    Mixed restricted and permissive text stays unknown. Mixed mit or apache
    and a permissive CC deed stays unknown. Script and style text does not
    count. A host ending in .gov, .edu, or .org is not a licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes = _licence_codes(page_text)
    software = {name for name in _SOFTWARE if name in codes}
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    ogl = "uk_ogl" in codes
    gov = "us_government_work" in codes
    if restricted and permissive:
        return RIGHTS_UNKNOWN
    if software and permissive:
        return RIGHTS_UNKNOWN
    if software and restricted:
        return RIGHTS_UNKNOWN
    if len(software) > 1:
        return RIGHTS_UNKNOWN
    if ogl and (restricted or permissive or software or gov):
        return RIGHTS_UNKNOWN
    if gov and (restricted or permissive or software):
        return RIGHTS_UNKNOWN
    if restricted:
        if restricted == {"mark"} or len(restricted) != 1:
            return RIGHTS_UNKNOWN
        return _DEED_LABELS[next(iter(restricted))]
    if software:
        return _SOFTWARE[next(iter(software))]
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    if permissive & {"cc0", "cc_by_sa"}:
        return RIGHTS_CREATIVE_COMMONS
    if permissive == {"cc_by"}:
        return RIGHTS_CC_BY
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, and a copyright
    year are not publication dates. A timestamp with a non-zero clock is the
    site publish time, not a publication date. A midnight date-only stamp is
    kept.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        found = _publication_day(metas.get(key))
        if found:
            return found
    for raw in _jsonld_dates(page_html):
        found = _publication_day(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
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


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return Palisade Research when the page states that name.

    An author named on the page is not the publisher. The organization name is
    not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _HIDDEN.sub(" ", page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site.casefold() == PUBLISHER.casefold():
        return PUBLISHER
    if PUBLISHER.casefold() in _plain_text(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    if is_redirect_document(page_html):
        raise CatalogError("redirect document is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    bare = lowered[:-1] if lowered.endswith("/") else lowered
    return not bare.startswith(_BLOCKED_PREFIXES)


def _licence_codes(page_text: str) -> set[str]:
    visible = _HIDDEN.sub(" ", page_text)
    blobs = [_plain_text(visible), *_hrefs(visible), *_license_meta(visible)]
    blobs.extend(_jsonld_licenses(page_text))
    folded = _fold(" ".join(blobs))
    codes = _cc_codes(folded)
    if _MIT.search(folded):
        codes.add("mit")
    if _APACHE.search(folded):
        codes.add("apache-2.0")
    if _MPL.search(folded):
        codes.add("mpl-2.0")
    # The British phrase is spaces, not hyphens. A National Archives URL does
    # not count, and the American spelling "license" does not count.
    if OGL_PHRASE in _plain_text(visible).casefold():
        codes.add("uk_ogl")
    for value in _rights_fields(page_text, visible):
        if _states_us_government_work(value):
            codes.add("us_government_work")
    return codes


def _cc_codes(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            mapped = _URL_LICENSE.get(license_code)
            if mapped:
                codes.add(mapped)
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
        elif match.group("pd") == "mark":
            codes.add("mark")
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(code)
    if "cc_by" in codes and codes & {"cc_by_nc", "cc_by_nd", "cc_by_nc_nd", "cc_by_nc_sa"}:
        # A hyphen boundary should already have rejected this. Drop a plain
        # CC BY hit when the same text also states a longer restricted deed
        # that the permissive pattern still overlapped.
        if not _plain_cc_by(folded):
            codes.discard("cc_by")
    return codes


def _plain_cc_by(folded: str) -> bool:
    """True when a CC BY deed remains after restricted deeds are removed."""

    stripped = re.sub(
        r"(?i)\bcc(?:\s+|-\s*)by(?:\s+|-\s*)nc(?:\s+|-\s*)(?:nd|sa)\b"
        r"|\bcc(?:\s+|-\s*)by(?:\s+|-\s*)(?:nc|nd|sa)\b"
        r"|creativecommons\.org/licenses/by-(?:nc(?:-nd|-sa)?|nd|sa)(?![a-z0-9-])",
        " ",
        folded,
    )
    return bool(
        re.search(r"(?i)\bcc(?:\s+|-\s*)by\b(?!-)", stripped)
        or re.search(r"(?i)creativecommons\.org/licenses/by(?!-)(?![a-z0-9-])", stripped)
        or re.search(
            r"(?i)creative commons attribution(?!-)(?!\s*-?\s*(?:non-?commercial|no-?deriv|share-?alike))",
            stripped,
        )
    )


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _plain_text(value))
    return _GOV_WORK.search(text) is not None


def _rights_fields(page_text: str, visible: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(visible).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            found.append(value)
    for block in _LDJSON.findall(page_text):
        found.extend(item.replace("\\/", "/") for item in _LD_RIGHTS.findall(block))
    return found


def _publication_day(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _STAMP.fullmatch(value.strip())
    if match is None:
        return None
    day, hour, minute, second = match.group(1), match.group(2), match.group(3), match.group(4)
    if hour is not None and (hour, minute, second) != ("00", "00", "00"):
        return None
    return _iso_date(day)


def _iso_date(value: str) -> str | None:
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _jsonld_dates(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        found.extend(_DATE_PUBLISHED.findall(block))
    return found


def _jsonld_licenses(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        found.extend(item.replace("\\/", "/") for item in _LD_LICENSE.findall(block))
    return found


def _license_meta(visible: str) -> list[str]:
    found: list[str] = []
    metas = _metas(visible)
    for key, value in metas.items():
        if key in _LICENSE_META_KEYS or key.endswith(".license") or key.endswith(".licence"):
            found.append(value)
    return found


def _hrefs(visible: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} is too long to store")


def _reject_stored_body(value: object) -> None:
    if isinstance(value, dict):
        found = _FORBIDDEN_KEYS.intersection(value)
        if found:
            names = ", ".join(sorted(found))
            raise CatalogError(f"catalog must not store page text ({names})")
        for item in value.values():
            if isinstance(item, (dict, list)):
                _reject_stored_body(item)
        return
    if isinstance(value, list):
        for item in value:
            _reject_stored_body(item)


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ")
    text = text.translate(_DASHES)
    return re.sub(r"\s+", " ", text).casefold()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
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


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
