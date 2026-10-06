"""Metadata catalog of public Inflection AI research and news pages.

The confirmed host is inflection.ai. www.inflection.ai redirects there.
robots.txt allows ``/``. Rows are blog pages, the labs page, and the
consumer-AI research report. Product chat apps, login pages, and off-host
redirects are omitted. A challenge page is not stored.

Each row keeps the title, publisher, canonical URL, date, and rights label.
Page bodies, abstracts, quotes, transcripts, and chart data are not stored.
Publication dates only; an updated, modified, or copyright year stays
unknown. Rights tokens:

- a sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc,
  cc_by_nd, cc_by_nc_sa, or cc_by_nc_nd;
- CC BY alone is creative_commons_attribution;
- CC0, CC BY-SA, or a permissive mix of those is creative_commons;
- mixed restricted and permissive text stays unknown;
- MIT plus CC BY stays unknown;
- a CC BY or CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or
  public-domain mark URL stays unknown;
- a CC0 anchor on a publicdomain/mark URL stays unknown;
- the Public Domain Mark, all rights reserved, terms, and the host name stay
  unknown;
- MIT, Apache-2.0, and MPL-2.0 keep their own tokens, and mixed software
  licences stay unknown;
- uk_ogl requires the exact phrase Open Government Licence;
- a generic creativecommons.org/licenses/ URL stays unknown.

This module does not fetch. It is not a belief collector. runner_wired stays
false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "inflection_pages"
CATALOG_FILENAME = "inflection_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Inflection AI"
OFFICIAL_HOST = "inflection.ai"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC_BY = "creative_commons_attribution"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC_BY,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
        RIGHTS_UK_OGL,
    }
)
OMITTED_HOSTS = frozenset(
    {
        "www.inflection.ai",
        "pi.ai",
        "hey.pi.ai",
        "help.pi.ai",
        "heypi.com",
        "www.businesswire.com",
    }
)
COLLECTOR_TOKEN = "pdoom.live-collector"
DESCRIPTION = (
    "Public Inflection AI research and news metadata from inflection.ai. "
    "A bounded GET confirmed the host; www.inflection.ai redirects there and robots.txt allows /. "
    "Rows are blog pages, labs, and the consumer-AI research report. "
    "Product chat apps, login pages, and off-host redirects are omitted. "
    "Fields are title, publisher, canonical URL, date, and rights. "
    "No page body, abstract, quote, transcript, or chart data. "
    "Publication dates only; updated, modified, and copyright years stay unknown. "
    "Rights tokens: cc_by_nc, cc_by_nd, cc_by_nc_sa, cc_by_nc_nd, "
    "creative_commons_attribution for CC BY alone, creative_commons for CC0 or CC BY-SA "
    "or a permissive mix of those, mit, apache-2.0, and mpl-2.0. "
    "Mixed restricted and permissive text, MIT plus CC BY, and mixed software licences stay unknown. "
    "uk_ogl requires Open Government Licence. "
    "A generic creativecommons.org/licenses/ URL, the Public Domain Mark, all rights reserved, "
    "terms, and the host name stay unknown. "
    "Stored rights are unknown. Not a belief collector. runner_wired is false."
)
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 1200

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
_GENERIC_TITLES = frozenset({"about", "home", "index"})
_PRODUCT_SLUGS = frozenset({"pi-journeys", "login", "chat", "app", "signin", "sign-in"})
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
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf-mitigated",
    "challenge-platform",
    "checking your browser",
    "enable javascript and cookies",
    "attention required",
    "cdn-cgi/challenge",
    "sorry, you have been blocked",
    "access denied",
)
_LICENSE_META = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dc.rights.license",
        "dcterms.rights",
    }
)
_PUBLISHED_META = ("article:published_time", "citation_publication_date", "dcterms.issued")
_OGL_PHRASE = "Open Government Licence"
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_SOFTWARE = frozenset({"mit", "apache-2.0", "mpl-2.0"})
_TOKEN = {
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by": RIGHTS_CC_BY,
    "cc-by-sa": RIGHTS_CREATIVE_COMMONS,
    "cc0": RIGHTS_CREATIVE_COMMONS,
    "mit": RIGHTS_MIT,
    "apache-2.0": RIGHTS_APACHE,
    "mpl-2.0": RIGHTS_MPL,
}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_MARKUP_TOKEN = re.compile(r"(?is)<(/?)(a|time)\b([^>]*)>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_H2 = re.compile(r"(?is)<h2\b[^>]*>(.*?)</h2>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_PREFIX = re.compile(r"(?i)^inflection ai\s*(?:\||[-–—])\s+")
_SITE_SUFFIX = re.compile(r"(?i)\s*(?:\||[-–—])\s+inflection ai\s*$")
_LABELED_PUBLISHED = re.compile(
    r"(?i)(?<![\w-])(?<!last\s)(?<!not\s)(?:date\s+published|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b"
)
_CC_URL = re.compile(
    r"creativecommons\.org/(?:licenses/(?P<deed>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))(?=[^a-z0-9-]|$)",
    re.I,
)
_URL_DEED = {
    "by-nc-nd": "cc-by-nc-nd",
    "by-nc-sa": "cc-by-nc-sa",
    "by-nc": "cc-by-nc",
    "by-nd": "cc-by-nd",
    "by-sa": "cc-by-sa",
    "by": "cc-by",
    "zero": "cc0",
    "mark": "pd-mark",
}
# Longer deeds are first so CC BY-NC is not also read as CC BY.
_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "cc-by-nc-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
            r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
            r"|attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
            r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
            r"|attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nd\b(?![\s-]*(?:sa|nc)\b)"
            r"|creative\s+commons\s+attribution[\s-]*no[\s-]*deriv"
            r"|attribution[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)"
            r"|creative\s+commons\s+attribution[\s-]*non[\s-]*commercial\b(?![\s-]*(?:share|no)\b)"
            r"|attribution[\s-]*non[\s-]*commercial\b(?![\s-]*(?:share|no)\b)"
        ),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)"
            r"|creative\s+commons\s+attribution[\s-]*share[\s-]*alike\b"
            r"|attribution[\s-]*share[\s-]*alike\b"
        ),
    ),
    (
        "cc0",
        re.compile(
            r"\bcc[\s-]*0\b|\bcc0\b|\bcc[\s-]*zero\b"
            r"|creative\s+commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    (
        "cc-by",
        re.compile(
            r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
            r"|creative\s+commons\s+attribution\b(?![\s-]*(?:non|no|share)\b)"
        ),
    ),
    ("pd-mark", re.compile(r"public\s+domain\s+mark\b")),
    (
        "apache-2.0",
        re.compile(
            r"\bapache-2\.0\b"
            r"|\bapache\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
            r"|\blicen[cs]ed\s+under\s+(?:the\s+)?apache(?:\s+licen[cs]e)?(?:\s*,?\s*version)?\s*2\.0\b"
        ),
    ),
    (
        "mpl-2.0",
        re.compile(
            r"\bmpl-2\.0\b"
            r"|\bmozilla\s+public\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
        ),
    ),
    (
        "mit",
        re.compile(
            r"\bmit\s+licen[cs]e\b"
            r"|\blicen[cs]ed\s+under\s+(?:the\s+)?mit(?:\s+licen[cs]e)?\b"
        ),
    ),
)
_UNICODE_DASHES = ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212")


class CatalogError(ValueError):
    """A catalog row or page failed the Inflection AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for the confirmed apex host inflection.ai."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def html_response_is_confirmable(*, status: int, content_type: str, body: str) -> bool:
    """True when one bounded GET returned an HTML page rather than a block.

    A redirect, a non-HTML body, a Cloudflare challenge, or a robot block does
    not confirm a catalog row.
    """

    if status != 200 or not isinstance(body, str) or not body.strip():
        return False
    if not isinstance(content_type, str):
        return False
    media = content_type.split(";", 1)[0].strip().lower()
    if media not in _HTML_TYPES:
        return False
    sample = body[:8000].casefold()
    if "<html" not in sample and "<!doctype html" not in sample:
        return False
    return not any(marker in sample for marker in _CHALLENGE_MARKERS)


def robots_allows(body: str, path: str, user_agent: str = COLLECTOR_TOKEN) -> bool:
    """Return whether robots.txt allows path for this collector.

    An HTML challenge is not a robots grant. The matching user-agent group
    wins over the wildcard group. The longest matching Allow and Disallow
    prefixes decide.
    """

    if not isinstance(body, str) or not isinstance(path, str) or not path.startswith("/"):
        raise CatalogError("robots path must be a site path")
    sample = body[:800].casefold()
    if "<html" in sample or "<!doctype" in sample:
        return False
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
    rules = _robots_rules(body, user_agent)
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if prefix and path.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def rights_from_page(page_text: str) -> str:
    """Return the rights token stated by the page.

    Public availability, a copyright year, all rights reserved, a terms link,
    the host name, and the Public Domain Mark stay unknown. Script, style, and
    comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    uncommented = _COMMENT.sub(" ", page_text)
    licences = [_normalize(value) for value in _jsonld_licenses(uncommented)]
    visible = _SCRIPT_STYLE.sub(" ", uncommented)
    if _anchor_mismatch(visible):
        return RIGHTS_UNKNOWN
    codes: set[str] = set()
    for href in _hrefs(visible):
        codes |= _codes_in_url(href)
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").casefold().replace("licence", "license")
        if "license" in rel.split():
            href = attrs.get("href", "")
            codes |= _codes_in_url(href)
            codes |= _codes_in_text(href)
    metas = _metas(visible)
    for key, value in metas.items():
        if key in _LICENSE_META:
            codes |= _codes_in_url(value)
            codes |= _codes_in_text(value)
    for value in licences:
        codes |= _codes_in_url(value)
        codes |= _codes_in_text(value)
    plain = _plain(visible)
    codes |= _codes_in_text(plain)
    codes |= _codes_in_url(plain)
    return _rights_label(codes, ogl=_OGL_PHRASE in plain)


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown.

    article:modified_time, og:updated_time, dcterms.modified, dateModified,
    and copyright years are not publication dates. A date inside a link is an
    item date, not the page's own publication date. HTML comments do not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    uncommented = _COMMENT.sub(" ", page_html)
    found: list[str] = []
    json_dates = _unique(_jsonld_dates(uncommented))
    if len(json_dates) == 1:
        found.append(json_dates[0])
    visible = _SCRIPT_STYLE.sub(" ", uncommented)
    meta_dates: list[str] = []
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_prefix(metas.get(key, ""))
        if parsed:
            meta_dates.append(parsed)
    meta_dates = _unique(meta_dates)
    if len(meta_dates) > 1:
        return UNKNOWN_DATE
    if len(meta_dates) == 1:
        found.append(meta_dates[0])
    labeled = _unique(_LABELED_PUBLISHED.findall(_plain(visible)))
    if len(labeled) > 1:
        return UNKNOWN_DATE
    if len(labeled) == 1 and _iso_date(labeled[0]):
        found.append(labeled[0])
    times = _unique(_outside_anchor_dates(visible))
    if len(times) > 1:
        return UNKNOWN_DATE
    if len(times) == 1:
        found.append(times[0])
    distinct = _unique(found)
    if len(distinct) == 1:
        return distinct[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    for pattern in (_H1, _H2):
        for inner in pattern.findall(visible):
            title = _clean_title(inner)
            if _usable_title(title):
                return title
    raw = _metas(visible).get("og:title", "")
    title = _clean_title(raw)
    if _usable_title(title):
        return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))
    site = _normalize(_metas(visible).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    title_tag = _TITLE.search(visible)
    titled = _normalize(title_tag.group(1)) if title_tag else ""
    if PUBLISHER in titled or PUBLISHER in _plain(visible):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another host is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
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
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if description != DESCRIPTION:
        raise CatalogError("description must match the catalog statement")
    if len(description) > MAX_DESCRIPTION_CHARS:
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
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an https inflection.ai research or news page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or parsed.netloc.lower() != OFFICIAL_HOST
        or host != OFFICIAL_HOST
        or not is_official_host(host)
        or not _research_or_news_path(path)
    ):
        raise CatalogError(f"canonical URL must be an https inflection.ai research or news page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _research_or_news_path(path: str) -> bool:
    if not path.startswith("/") or path.endswith("/") or "\\" in path or "//" in path or ".." in path or "%" in path:
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if path in {"/blog", "/labs", "/state-of-consumer-ai-2026"}:
        return True
    if not path.startswith("/blog/"):
        return False
    slug = path[len("/blog/") :]
    if slug in _PRODUCT_SLUGS or not _SLUG.fullmatch(slug):
        return False
    return True


def _rights_label(codes: set[str], *, ogl: bool) -> str:
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    software = codes & _SOFTWARE
    pd_mark = "pd-mark" in codes
    if pd_mark:
        return RIGHTS_UNKNOWN
    if restricted and (permissive or software or ogl or len(restricted) > 1):
        return RIGHTS_UNKNOWN
    if len(restricted) == 1 and not permissive and not software and not ogl:
        return _TOKEN[next(iter(restricted))]
    if software and (permissive or ogl or restricted or len(software) > 1):
        return RIGHTS_UNKNOWN
    if len(software) == 1 and not permissive and not ogl:
        return _TOKEN[next(iter(software))]
    if permissive == {"cc-by"} and not ogl:
        return RIGHTS_CC_BY
    if permissive and permissive <= {"cc-by", "cc-by-sa", "cc0"} and not ogl:
        return RIGHTS_CREATIVE_COMMONS
    if ogl and not codes:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def _anchor_mismatch(visible_html: str) -> bool:
    """True when anchor text claims a permissive deed the href does not grant."""
    for attrs, inner in _ANCHOR.findall(visible_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        href_codes = _codes_in_url(href)
        if not (href_codes & (_RESTRICTED | {"pd-mark"})):
            continue
        text_codes = _codes_in_text(_plain(inner))
        if text_codes & {"cc-by", "cc-by-sa"}:
            return True
        if "cc0" in text_codes and "pd-mark" in href_codes:
            return True
    return False


def _codes_in_url(value: str) -> set[str]:
    text = _normalize(value).casefold()
    codes: set[str] = set()
    for match in _CC_URL.finditer(text):
        slug = (match.group("deed") or match.group("pd") or "").lower()
        code = _URL_DEED.get(slug)
        if code:
            codes.add(code)
    return codes


def _codes_in_text(value: str) -> set[str]:
    text = _normalize(value).casefold()
    found: set[str] = set()
    occupied = bytearray(len(text))
    for code, pattern in _TEXT_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if start == end or any(occupied[start:end]):
                continue
            occupied[start:end] = b"\1" * (end - start)
            found.add(code)
    return found


def _hrefs(visible_html: str) -> list[str]:
    found: list[str] = []
    for attrs, _inner in _ANCHOR.findall(visible_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        if href:
            found.append(href)
    return found


def _outside_anchor_dates(visible_html: str) -> list[str]:
    depth = 0
    found: list[str] = []
    for match in _MARKUP_TOKEN.finditer(visible_html):
        closing = bool(match.group(1))
        tag = match.group(2).lower()
        attrs = match.group(3) or ""
        if tag == "a":
            if closing:
                depth = max(0, depth - 1)
            elif not attrs.rstrip().endswith("/"):
                depth += 1
            continue
        if tag == "time" and not closing and depth == 0:
            parsed = _iso_prefix(_attrs(f"<time {attrs}>").get("datetime", ""))
            if parsed:
                found.append(parsed)
    return found


def _jsonld_dates(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for match in _DATE_PUBLISHED.finditer(blob):
            parsed = _iso_prefix(match.group(1))
            if parsed:
                found.append(parsed)
    return found


def _jsonld_licenses(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        for match in _LD_LICENSE.finditer(blob):
            found.append(unescape(match.group(1)))
    return found


def _robots_rules(body: str, user_agent: str) -> list[tuple[str, str]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw_line in body.splitlines():
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
    haystack = (user_agent or "").strip().lower()
    product = haystack.split("/", 1)[0]
    specific: list[tuple[int, list[tuple[str, str]]]] = []
    wildcard: list[tuple[str, str]] | None = None
    for group_agents, group_rules in groups:
        for agent in group_agents:
            if agent == "*":
                wildcard = group_rules
                continue
            if agent and (product.startswith(agent) or haystack.startswith(agent)):
                specific.append((len(agent), group_rules))
    if specific:
        return max(specific, key=lambda item: item[0])[1]
    return wildcard or []


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


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() not in _GENERIC_TITLES


def _clean_title(value: str) -> str:
    text = _normalize(_TAG.sub(" ", value))
    changed = True
    while changed and text:
        changed = False
        if _SITE_PREFIX.match(text):
            text = _SITE_PREFIX.sub("", text).strip()
            changed = True
        if _SITE_SUFFIX.search(text):
            text = _SITE_SUFFIX.sub("", text).strip()
            changed = True
    return text


def _plain(page_html: str) -> str:
    return _normalize(_TAG.sub(" ", page_html))


def _normalize(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ")
    for dash in _UNICODE_DASHES:
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text).strip()


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


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _unique(values: list[str]) -> list[str]:
    found: list[str] = []
    for value in values:
        if value not in found:
            found.append(value)
    return found


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value
