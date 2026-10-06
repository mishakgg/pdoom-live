"""Metadata catalog of public MLCommons pages.

The official host is mlcommons.org. www.mlcommons.org is the same site. A row
is stored only after one bounded GET returns HTML from that host: 12 second
timeout, at most 3 redirects, and at most 400000 bytes. A Cloudflare
challenge, a captcha, HTTP 202, an Akamai 403, a robots disallow, or an
off-host redirect stores no row, so the catalog may be empty.

A row keeps the title, publisher, canonical URL, date, and rights label.
Page bodies, benchmark result tables, chart data, and dataset files are not
stored. A missing date is the string unknown. Updated, modified, and
copyright years are not publication dates. ``creative_commons`` means only a
stated CC0, CC BY, or CC BY-SA deed. CC BY-NC, CC BY-ND, CC BY-NC-ND, and
CC BY-NC-SA are their own tokens and are never folded into creative_commons.
A hyphen is a word boundary in a naive pattern, so CC BY must not match
CC BY-NC, and licenses/by must not match licenses/by-nc. Restricted deeds
win when a permissive deed is also present. apache-2.0 and mit are their own
tokens. Mixed apache or mit plus permissive CC stays unknown. A generic
creativecommons.org/licenses/ URL is not a permissive deed. The Public
Domain Mark is not CC0. A copyright notice, All rights reserved, a terms
link, or a host name is not a licence. The live URL is stored as confirmed.
This module does not fetch and it is not a belief collector. runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "mlcommons_pages"
CATALOG_FILENAME = "mlcommons_pages.json"
RUNNER_WIRED = False
PUBLISHER = "MLCommons"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_MIT,
        RIGHTS_APACHE,
    }
)
OFFICIAL_HOSTS = frozenset({"mlcommons.org", "www.mlcommons.org"})
FETCH_TIMEOUT_SECONDS = 12
FETCH_MAX_REDIRECTS = 3
FETCH_MAX_BYTES = 400_000
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
        "dataset",
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
        "table",
        "text",
        "transcript",
        "transcript_text",
    }
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "challenges.cloudflare.com",
    "cf-browser-verification",
    "attention required",
    "cdn-cgi/challenge",
    "sgcaptcha",
    "g-recaptcha",
    "hcaptcha",
    "cf-turnstile",
    "errors.edgesuite.net",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_URL = re.compile(
    r"^(?P<scheme>https)://"
    r"(?:(?P<userinfo>[^/@\s]+)@)?"
    r"(?P<host>[A-Za-z0-9.-]+)"
    r"(?::(?P<port>\d+))?"
    r"(?P<path>/[^?#\s]*)?"
    r"(?:\?(?P<query>[^#\s]*))?"
    r"(?:#(?P<fragment>\S*))?$"
)
_SEGMENT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_LABELED_PUBLISHED = re.compile(
    r"(?<![a-z])(?:date published|publication date|published)\s*:\s*(\d{4}-\d{2}-\d{2})\b"
)
_SITE_SUFFIXES = (
    " | mlcommons",
    " - mlcommons",
    " – mlcommons",
    " — mlcommons",
    " | ml commons",
)
# Longer deeds are listed first. A hyphen is a word-boundary character, so a
# bare "CC BY" or "licenses/by" pattern must not succeed inside CC BY-NC.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])")),
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])")),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)(?![a-z0-9]))(?![a-z0-9])")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![\s-]*(?:nc|nd)(?![a-z0-9]))(?![a-z0-9])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)(?![a-z0-9]))(?![a-z0-9])")),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero(?![a-z0-9])"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero(?![a-z])"
        ),
    ),
    ("mark", re.compile(r"public\s+domain\s+mark(?![a-z])")),
)
_PROSE = (
    ("by-nc-nd", re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv")),
    ("by-nc-sa", re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike")),
    (
        "by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial(?![\s-]+(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "by",
        re.compile(
            r"creative commons attribution(?![\s-]+(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
}
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_MIT_GRANT = re.compile(
    r"(?<!not )(?:licensed|released|available) under (?:the )?mit licen[cs]e(?![a-z0-9])"
)
_APACHE_GRANT = re.compile(
    r"(?<!not )(?:licensed|released|available) under (?:the )?apache licen[cs]e(?:\s*,?\s*version)?\s*2\.0(?![a-z0-9])"
)
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9])")
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|www\.apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9])"
)
_EXACT_MIT = frozenset({"mit", "mit license", "mit licence"})
_EXACT_APACHE = frozenset(
    {"apache-2.0", "apache 2.0", "apache license 2.0", "apache licence 2.0"}
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
_ARTIFACT_SUFFIXES = (
    ".7z",
    ".arrow",
    ".bz2",
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".h5",
    ".jpeg",
    ".jpg",
    ".json",
    ".npy",
    ".parquet",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".tar",
    ".tsv",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_BLOCKED_PREFIXES = ("/wp-admin", "/wp-content", "/wp-includes", "/wp-json", "/xmlrpc.php")
_OMITTED_SEGMENTS = frozenset(
    {"chart-data", "charts", "dataset", "datasets", "leaderboard", "leaderboards", "results"}
)


class CatalogError(ValueError):
    """A catalog row or page failed the MLCommons page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for mlcommons.org and www.mlcommons.org when the host is not blocked."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    return content_type.split(";", 1)[0].strip().casefold() in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the body is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12_000].casefold()
    plain = _plain(page_html[:12_000]).casefold()
    return any(marker in sample or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict[str, str] | None = None,
) -> bool:
    """True only for an HTML 200 that is not a challenge or block page."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    mitigated = _header(headers, "cf-mitigated")
    if "challenge" in mitigated.casefold():
        return False
    return True


def robots_disallows(robots_text: str, path: str) -> bool:
    """True when robots.txt disallows the path, or the body is not robots text."""

    if not isinstance(robots_text, str):
        raise CatalogError("robots text must be a string")
    if "<html" in robots_text[:800].casefold():
        return True
    rules = _robots_star_rules(robots_text)
    if rules is None:
        return False
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix:
            continue
        if target.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return disallowed > allowed


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict[str, str] | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when the response is a confirmed official HTML page.

    HTTP 202, a 403, a Cloudflare or Akamai challenge, a non-HTML body, an
    off-host URL, and a robots disallow store no row.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    if _official_url_or_none(page_url) is None:
        return None
    if robots_text is not None and robots_disallows(robots_text, _url_path(page_url)):
        return None
    assert isinstance(page_html, str)
    return page_record(page_html, page_url=page_url)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA. Sole CC BY-NC,
    CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND keep their own tokens. A restricted
    deed wins when a permissive deed is also present. A by-nc URL stays a
    restricted token even when the anchor text says CC BY. apache-2.0 and mit
    are their own tokens. Mixed apache or mit plus permissive CC stays unknown.
    The Public Domain Mark is not CC0.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes, mit, apache = _licence_signals(page_text)
    restricted = _restricted_rights(codes)
    if restricted is not None:
        return restricted
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    permissive = bool(codes & _PERMISSIVE)
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


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for raw in _DATE_PUBLISHED.findall(blob):
            parsed = _iso_day(raw)
            if parsed:
                return parsed
    visible = _without_hidden(page_text)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            return parsed
    labeled = _LABELED_PUBLISHED.search(_plain(visible).casefold())
    if labeled:
        parsed = _iso_day(labeled.group(1))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
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
    """Return MLCommons when the page states that name."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if "mlcommons" in site.casefold():
        return PUBLISHER
    if "mlcommons" in _plain(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
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
    _require_text(entry, "title")
    _require_text(entry, "publisher")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError("rights must be unknown or a stated reuse-licence token")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public MLCommons page")
    match = _URL.fullmatch(url)
    if match is None:
        raise CatalogError(f"canonical URL must be a public MLCommons page: {url}")
    host = match.group("host")
    path = match.group("path") or ""
    if (
        match.group("userinfo")
        or match.group("query") is not None
        or match.group("fragment") is not None
        or match.group("port") is not None
        or host != host.lower()
        or host.endswith(".")
        or not is_official_host(host)
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL must be a public MLCommons page: {url}")
    return url


def _official_url_or_none(url: str) -> str | None:
    try:
        return validate_canonical_url(url)
    except CatalogError:
        return None


def _url_path(url: str) -> str:
    match = _URL.fullmatch(url)
    if match is None:
        return "/"
    return match.group("path") or "/"


def _public_path(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/") or path != path.lower():
        return False
    if ".." in path or "\\" in path or "//" in path or "%" in path:
        return False
    bare = path[:-1] if path.endswith("/") else path
    if bare.endswith(_ARTIFACT_SUFFIXES) or bare.startswith(_BLOCKED_PREFIXES):
        return False
    segments = [segment for segment in bare.split("/") if segment]
    if not segments:
        return False
    if any(segment in _OMITTED_SEGMENTS for segment in segments):
        return False
    return all(_SEGMENT.fullmatch(segment) for segment in segments)


def _licence_signals(page_text: str) -> tuple[set[str], bool, bool]:
    visible = _without_hidden(page_text)
    pieces = [_plain(visible), *_hrefs(visible), *_meta_values(visible, _LICENSE_META)]
    for blob in _LDJSON.findall(page_text):
        pieces.extend(raw.replace("\\/", "/") for raw in _LD_LICENSE.findall(blob))
    codes: set[str] = set()
    mit = False
    apache = False
    for piece in pieces:
        codes.update(_cc_codes(piece))
        mit = mit or _states_mit(piece)
        apache = apache or _states_apache(piece)
    return codes, mit, apache


def _restricted_rights(codes: set[str]) -> str | None:
    restricted = {code for code in codes if code in _RESTRICTED_TOKENS}
    if not restricted:
        return None
    if "by-nc-nd" in restricted and restricted <= {"by-nc-nd", "by-nc", "by-nd"}:
        return RIGHTS_CC_BY_NC_ND
    if "by-nc-sa" in restricted and restricted <= {"by-nc-sa", "by-nc"}:
        return RIGHTS_CC_BY_NC_SA
    if restricted == {"by-nc"}:
        return RIGHTS_CC_BY_NC
    if restricted == {"by-nd"}:
        return RIGHTS_CC_BY_ND
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    return RIGHTS_UNKNOWN


def _cc_codes(value: str) -> set[str]:
    folded = _fold(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    for code, pattern in _PROSE:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _states_mit(value: str) -> bool:
    folded = _fold(value).strip()
    if folded in _EXACT_MIT:
        return True
    return _MIT_GRANT.search(folded) is not None or _MIT_URL.search(folded) is not None


def _states_apache(value: str) -> bool:
    folded = _fold(value).strip()
    if folded in _EXACT_APACHE:
        return True
    return _APACHE_GRANT.search(folded) is not None or _APACHE_URL.search(folded) is not None


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return text.casefold()


def _robots_star_rules(text: str) -> list[tuple[str, str]] | None:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
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
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            return group_rules
    return None


def _require_text(entry: dict, field: str) -> None:
    value = entry.get(field)
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


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", _without_hidden(page_text))).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAG.sub(" ", value)).replace("\xa0", " ")).strip()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    folded = text.casefold()
    for suffix in _SITE_SUFFIXES:
        if folded.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _header(headers: dict[str, str] | None, name: str) -> str:
    if not headers:
        return ""
    for key, value in headers.items():
        if str(key).casefold() == name:
            return str(value)
    return ""


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(page_html)
    return [metas[name] for name in names if metas.get(name)]


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
        attrs.setdefault(name.casefold(), unescape(double or single or bare).strip())
    return attrs
