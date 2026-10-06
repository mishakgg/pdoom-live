"""Metadata catalog of public Cohere Labs research pages.

Cohere For AI's former hosts redirect off-host to https://cohere.com/research.
Those redirects are not stored. The general Cohere product site, docs, and
model playground are not part of this catalog. Each stored URL was confirmed
with one bounded GET. A row keeps the title, publisher, canonical URL, date,
and rights label. Abstracts, page bodies, PDFs, and chart data are not stored.
A Cloudflare challenge, a captcha, an HTTP 202, an Akamai 403, a robots block,
or an off-host redirect is not stored. Rights is ``creative_commons`` only for
a stated CC0, CC BY, or CC BY-SA deed. CC BY-NC, CC BY-ND, CC BY-NC-ND, and
CC BY-NC-SA stay their own tokens. A hyphen continues a licence token, so CC
BY does not match CC BY-NC, and licenses/by does not match licenses/by-nc.
A restricted deed together with CC0, CC BY, or CC BY-SA stays unknown. A sole
restricted deed keeps its own token. A permissive anchor on a restricted or
Public Domain Mark URL stays unknown. The Public Domain Mark is not CC0. apache-2.0 and mit stay their own tokens. A copyright notice,
All rights reserved, a terms link, and a host name are not licences. A page
that does not state a publication date keeps the date unknown. Updated,
modified, and copyright years are not publication dates. The live URL is
stored as confirmed; a different rel=canonical does not replace it. This
module does not fetch and it is not a belief collector. ``runner_wired`` stays
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

CATALOG_ID = "cohere_ai_pages"
CATALOG_FILENAME = "cohere_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Cohere Labs"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY_NC = "cc-by-nc"
RIGHTS_CC_BY_ND = "cc-by-nd"
RIGHTS_CC_BY_NC_SA = "cc-by-nc-sa"
RIGHTS_CC_BY_NC_ND = "cc-by-nc-nd"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
ALLOWED_RIGHTS = frozenset(
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
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "cohere.com"
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
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_RESEARCH_PATH = re.compile(r"^/research(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*/?$")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*(?:\"application/ld\+json\"|'application/ld\+json')[^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINKISH = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
)
_LICENSE_META_KEYS = frozenset(
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
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title", "twitter:title")
_SITE_SUFFIXES = (
    " | Cohere Labs",
    " - Cohere Labs",
    " – Cohere Labs",
    " — Cohere Labs",
    " | Cohere",
    " - Cohere",
    " – Cohere",
    " — Cohere",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_ARTICLE_TYPES = frozenset(
    {
        "article",
        "blogposting",
        "newsarticle",
        "report",
        "scholarlyarticle",
        "techarticle",
    }
)
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "cf-browser-verification",
    "checking your browser",
    "cdn-cgi/challenge",
    "sgcaptcha",
    "hcaptcha",
    "g-recaptcha",
    "attention required",
)
# Confirmed from https://cohere.com/robots.txt. These paths are not stored.
_ROBOTS_DISALLOW = (
    "/helloworld",
    "/labormap",
    "/mcp-expertise",
    "/mcp-landscape",
    "/project-pursue",
    "/studio",
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".epub",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
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
# A hyphen continues the token. Word-boundary \\b would treat the hyphen in
# CC BY-NC as the end of CC BY, and licenses/by would match licenses/by-nc.
_TOKEN_END = r"(?![\w-])"
_CC_TEXT = (
    ("by-nc-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nc[\s-]+nd{_TOKEN_END}")),
    ("by-nc-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nc[\s-]+sa{_TOKEN_END}")),
    ("by-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nd{_TOKEN_END}")),
    ("by-nc", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nc{_TOKEN_END}")),
    ("by-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+sa{_TOKEN_END}")),
    (
        "by",
        re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by(?![\s-]*(?:nc|nd|sa){_TOKEN_END}){_TOKEN_END}"),
    ),
    ("zero", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*0{_TOKEN_END}|(?<![a-z0-9])cc0{_TOKEN_END}")),
)
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    rf"{_TOKEN_END}"
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_ORDER = ("by-nc-nd", "by-nc-sa", "by-nd", "by-nc")
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
}
_GRANT_WINDOW = re.compile(r"(?i)(?:licensed|released)\s+under\b.{0,180}")
_MIT_IN_GRANT = re.compile(r"(?i)mit\s+licen[cs]e")
_APACHE_IN_GRANT = re.compile(
    r"(?i)apache\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0|(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
)
_MIT_URL = re.compile(r"(?i)(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![\w.-])")
_APACHE_URL = re.compile(
    r"(?i)(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![\w.-])"
)
_EXACT_TOKENS = {"mit": RIGHTS_MIT, "apache-2.0": RIGHTS_APACHE}
_SKIP_JSON_KEYS = frozenset(
    {"abstract", "articlebody", "comment", "description", "headline", "text"}
)


class CatalogError(ValueError):
    """A catalog row or page failed the Cohere Labs research page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    _reject_stored_body(document)
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
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _reject_stored_body(entry, path="entry")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be a known token or unknown")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Cohere Labs research page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OFFICIAL_HOST
        or host != OFFICIAL_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or hostname_is_blocked(host)
        or not is_official_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or _is_download(path)
        or robots_disallow(path)
        or _RESEARCH_PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL is not a public Cohere Labs research page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OFFICIAL_HOST and not hostname_is_blocked(host)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the research page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:4000].casefold()
    title = _TITLE.search(page_html)
    title_text = title.group(1).casefold() if title else ""
    return any(marker in head or marker in title_text for marker in _CHALLENGE_MARKERS)


def robots_disallow(path: str) -> bool:
    """True when the confirmed robots.txt disallows this path."""

    lowered = (path or "").casefold()
    if lowered != "/" and lowered.endswith("/"):
        lowered = lowered[:-1]
    for prefix in _ROBOTS_DISALLOW:
        if lowered == prefix or lowered.startswith(prefix + "/"):
            return True
    return False


def stays_on_official_host(requested_url: str, final_url: str) -> bool:
    """False when the fetch left the host that was requested."""

    requested = urlparse(requested_url).hostname
    final = urlparse(final_url).hostname
    if not requested or not final:
        return False
    return requested.lower().rstrip(".") == final.lower().rstrip(".")


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a block or challenge.

    HTTP 202, Akamai 403, and any other non-200 status store no row. An
    off-host redirect stores no row. A robots-disallowed path stores no row.
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
            if name in {"sg-captcha", "x-captcha"} and token:
                return False
    target = final_url or page_url
    if final_url is not None and not stays_on_official_host(page_url, final_url):
        return False
    parsed = urlparse(target)
    if robots_disallow(parsed.path or ""):
        return False
    if not is_official_host(parsed.hostname or ""):
        return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict | None = None,
    final_url: str | None = None,
) -> dict | None:
    """Return metadata when the response is the research page HTML.

    A challenge, a captcha, an HTTP 202, an Akamai 403, a robots block, an
    off-host redirect, or a non-HTML response is not stored.
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
    target = final_url or page_url
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights token stated by the page.

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only. A sole CC BY-NC,
    CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND deed keeps its own token and is never
    folded into ``creative_commons``. When one of those restricted deeds is
    also stated with CC0, CC BY, or CC BY-SA, rights stay unknown. A hyphen
    continues the token, so CC BY does not match CC BY-NC and licenses/by does
    not match licenses/by-nc. A generic creativecommons.org/licenses/ URL is
    not a permissive deed. An anchor whose visible text says CC BY, CC BY-SA,
    or CC0 stays unknown when the href is a by-nc, by-nd, by-nc-sa, by-nc-nd,
    or Public Domain Mark URL. The Public Domain Mark is not CC0. ``mit`` and
    ``apache-2.0`` stay their own tokens. A copyright notice, All rights
    reserved, a terms link, and a host name are not licences. Script and
    style text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    pieces = _licence_pieces(page_text)
    codes: set[str] = set()
    named: set[str] = set()
    for piece in pieces:
        folded = piece.casefold().translate(_DASHES)
        codes.update(_cc_codes(folded))
        named.update(_named_tokens(folded))
    restricted = [code for code in _RESTRICTED_ORDER if code in codes]
    permissive = bool(codes & _PERMISSIVE_CC)
    # CC0, CC BY, or CC BY-SA together with a restricted deed or the Public
    # Domain Mark stays unknown. That includes a permissive anchor whose href
    # is by-nc, by-nd, by-nc-sa, by-nc-nd, or publicdomain/mark.
    if permissive and (restricted or "mark" in codes):
        return RIGHTS_UNKNOWN
    if restricted:
        return _RESTRICTED_TOKENS[restricted[0]]
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    if permissive and named:
        return RIGHTS_UNKNOWN
    if len(named) > 1:
        return RIGHTS_UNKNOWN
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    if named:
        return next(iter(named))
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str, *, page_url: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    The date is the article datePublished for this page URL, or a publication
    meta tag. dateModified, og:updated_time, a last-updated line, a copyright
    year, an organization founding date, and a date that belongs to another
    page are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    found = _article_date(page_html, page_url)
    if found:
        return found
    metas = _metas(_HIDDEN.sub(" ", page_html))
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        parsed = _iso_prefix(raw)
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
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
    """Return Cohere Labs when the page states that research-lab name.

    A person named on the page is not the publisher. The product site name
    alone is not the research publisher. The name is not invented when the
    page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _HIDDEN.sub(" ", page_html)
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
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html, page_url=page_url),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _licence_pieces(page_text: str) -> list[str]:
    pieces = [_plain_text(_HIDDEN.sub(" ", page_text))]
    visible = _HIDDEN.sub(" ", page_text)
    pieces.extend(_hrefs(visible))
    metas = _metas(visible)
    for key in _LICENSE_META_KEYS:
        if metas.get(key):
            pieces.append(metas[key])
    for blob in _LDJSON.findall(page_text):
        pieces.extend(_json_license_values(blob))
    return pieces


def _json_license_values(blob: str) -> list[str]:
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        return []
    found: list[str] = []
    _collect_license_values(payload, found)
    return found


def _collect_license_values(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_license_values(item, found)
        return
    if not isinstance(payload, dict):
        return
    for key, value in payload.items():
        if str(key).casefold() in _SKIP_JSON_KEYS:
            continue
        if str(key).casefold() in {"license", "licence"}:
            if isinstance(value, str):
                found.append(value)
            else:
                _collect_license_values(value, found)
            continue
        _collect_license_values(value, found)


def _article_date(page_html: str, page_url: str) -> str | None:
    dates: list[str] = []
    for blob in _LDJSON.findall(page_html):
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            continue
        _collect_article_dates(payload, page_url, dates)
    unique = list(dict.fromkeys(dates))
    if len(unique) == 1:
        return unique[0]
    return None


def _collect_article_dates(payload: object, page_url: str, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_article_dates(item, page_url, found)
        return
    if not isinstance(payload, dict):
        return
    if "@graph" in payload:
        _collect_article_dates(payload["@graph"], page_url, found)
    if _is_article(payload.get("@type")) and _node_matches_page(payload, page_url):
        parsed = _iso_prefix(payload.get("datePublished"))
        if parsed:
            found.append(parsed)
    for key, value in payload.items():
        if key == "@graph":
            continue
        if isinstance(value, (dict, list)):
            _collect_article_dates(value, page_url, found)


def _is_article(value: object) -> bool:
    if isinstance(value, str):
        return value.casefold() in _ARTICLE_TYPES
    if isinstance(value, list):
        return any(isinstance(item, str) and item.casefold() in _ARTICLE_TYPES for item in value)
    return False


def _node_matches_page(node: dict, page_url: str) -> bool:
    candidates: list[str] = []
    main = node.get("mainEntityOfPage")
    if isinstance(main, str):
        candidates.append(main)
    elif isinstance(main, dict):
        for key in ("@id", "url"):
            if isinstance(main.get(key), str):
                candidates.append(main[key])
    if isinstance(node.get("url"), str):
        candidates.append(node["url"])
    if isinstance(node.get("@id"), str):
        candidates.append(node["@id"])
    return any(_same_page(candidate, page_url) for candidate in candidates)


def _same_page(left: str, right: str) -> bool:
    def norm(value: str) -> tuple[str, str, str]:
        parsed = urlparse(value.strip())
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        return (parsed.scheme.casefold(), (parsed.hostname or "").casefold().rstrip("."), path)
    try:
        return norm(left) == norm(right)
    except ValueError:
        return False


def _cc_codes(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    if re.search(r"public\s+domain\s+mark", folded):
        codes.add("mark")
    if re.search(r"creative\s+commons(?:\s+public\s+domain)?[\s-]+zero\b|\bcc[\s-]+zero\b", folded):
        codes.add("zero")
    if "creative commons" not in folded:
        return codes
    noncommercial = re.search(r"non[\s-]?commercial", folded) is not None
    noderiv = re.search(r"no[\s-]?deriv", folded) is not None
    sharealike = re.search(r"share[\s-]?alike", folded) is not None
    if noncommercial and noderiv:
        codes.add("by-nc-nd")
    elif noncommercial and sharealike:
        codes.add("by-nc-sa")
    elif noncommercial:
        codes.add("by-nc")
    elif noderiv:
        codes.add("by-nd")
    elif sharealike and re.search(r"\battribution\b", folded):
        codes.add("by-sa")
    elif re.search(r"\battribution\b(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv))", folded):
        codes.add("by")
    return codes


def _named_tokens(folded: str) -> set[str]:
    found: set[str] = set()
    if _MIT_URL.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE_URL.search(folded):
        found.add(RIGHTS_APACHE)
    for window in _GRANT_WINDOW.findall(folded):
        if _MIT_IN_GRANT.search(window):
            found.add(RIGHTS_MIT)
        if _APACHE_IN_GRANT.search(window):
            found.add(RIGHTS_APACHE)
    for line in folded.splitlines():
        token = line.strip()
        if token in _EXACT_TOKENS:
            found.add(_EXACT_TOKENS[token])
    return found


def _iso_prefix(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None or not _iso_date(match.group(1)):
        return None
    return match.group(1)


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_download(path: str) -> bool:
    lowered = path.casefold()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
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
