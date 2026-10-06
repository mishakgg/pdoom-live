"""Metadata catalog of public Brookings Institution artificial-intelligence pages.

The official host is www.brookings.edu. brookings.edu redirects there. Rows keep
a title, publisher, canonical URL, date, and rights label. Page bodies,
abstracts, quotes, transcripts, and chart data are not stored. Only pages in
the artificial-intelligence section that stay on that host are eligible.
Login pages and the rest of the Brookings site are omitted. A Cloudflare
challenge, a captcha, a non-HTML response, a robots disallow, or a redirect
off this host is not stored.

A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its own token.
CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a permissive
mix of those is creative_commons. Mixed restricted and permissive text stays
unknown. MIT plus CC BY stays unknown. A CC BY or CC BY-SA anchor on a
by-nc, by-nd, by-nc-sa, by-nc-nd, or public-domain mark URL stays unknown. A
CC0 anchor on a publicdomain/mark URL stays unknown. The Public Domain Mark,
all rights reserved, terms, and the host name stay unknown. MIT, Apache-2.0,
and MPL-2.0 stay their own tokens. Mixed software licences stay unknown.
uk_ogl requires the British phrase Open Government Licence. A generic
creativecommons.org/licenses/ URL stays unknown, and the visible text of an
anchor that points there does not count. A hyphen continues a deed token, so
CC BY does not match CC BY-NC.

Updated, modified, and copyright years are not publication dates. A missing
publication date stays unknown. This module does not fetch and it is not a
belief collector. runner_wired stays false.
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

CATALOG_ID = "brookings_ai_pages"
CATALOG_FILENAME = "brookings_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Brookings Institution"
OFFICIAL_HOST = "www.brookings.edu"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_UK_OGL = "uk_ogl"
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
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_UK_OGL,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
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
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_SITE_NAMES = frozenset({"Brookings", "Brookings Institution", "The Brookings Institution"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SECTION_PATH = re.compile(
    r"^/(?:"
    r"topics/artificial-intelligence(?:/[a-z0-9-]+)*"
    r"|(?:articles|events|books|book|news|collection)/[a-z0-9-]+(?:/[a-z0-9-]+)*"
    r")/?$"
)
_LOGIN_PREFIXES = ("/wp-login.php", "/wp-admin", "/login", "/signin", "/sign-in", "/account")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_BLOCK = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " | the brookings institution",
    " | brookings institution",
    " | brookings",
    " - the brookings institution",
    " - brookings institution",
    " - brookings",
    " – the brookings institution",
    " – brookings institution",
    " – brookings",
    " — the brookings institution",
    " — brookings institution",
    " — brookings",
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
    ".svg",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "cdn-cgi/challenge",
    "attention required",
    "sorry, you have been blocked",
    "access denied",
    "hcaptcha",
    "g-recaptcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
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
# Longer deeds are listed first. A hyphen continues the token, so licenses/by
# does not match licenses/by-nc and CC BY does not match CC BY-NC.
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
        re.compile(r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"creative commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    ),
    (
        "by-nc",
        re.compile(
            r"creative commons\s+attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
        ),
    ),
    ("by-nd", re.compile(r"creative commons\s+attribution[\s-]+no[\s-]*deriv")),
    ("by-sa", re.compile(r"creative commons\s+attribution[\s-]+share[\s-]*alike")),
    (
        "by",
        re.compile(
            r"creative commons\s+attribution(?![\s-]*(?:"
            r"share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|sa\b|nc\b|nd\b))"
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
_MIT = re.compile(r"\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_ROBOTS_END = "$"


class CatalogError(ValueError):
    """A catalog row or page failed the Brookings artificial-intelligence page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for the www.brookings.edu host that returned HTML."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_section_path(path: str) -> bool:
    """True for an artificial-intelligence section path on the official host."""

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    lowered = path.lower()
    bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
    if bare.startswith(_LOGIN_PREFIXES) or bare == "/search" or bare.startswith("/search/"):
        return False
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _SECTION_PATH.fullmatch(lowered) is not None


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    head = sample[:4000]
    title_match = _TITLE.search(sample)
    title = _plain(title_match.group(1)).casefold() if title_match else ""
    return any(marker in head or marker in title for marker in _CHALLENGE_MARKERS)


def robots_allows_path(robots_text: str, path: str, user_agent: str = "pdoom.live-collector") -> bool:
    """True when robots.txt does not disallow path for this collector.

    A challenge page served in place of robots.txt does not allow a fetch.
    Wildcard rules and the query string are honored. An empty disallow does
    not erase a more specific disallow in another group for the same agent.
    """

    if not isinstance(robots_text, str):
        return False
    sample = robots_text[:800].casefold()
    if "<html" in sample or any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
    groups = _robots_groups(robots_text)
    if not groups:
        return True
    rules = _matching_rules(groups, user_agent)
    if rules is None:
        return True
    return _path_allowed(rules, path or "/")


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    requested_urls: list[str] | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a block or challenge.

    HTTP 202, other non-200 statuses, captcha pages, Cloudflare challenges,
    and redirects that leave www.brookings.edu are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers and _blocked_headers(headers):
        return False
    urls = list(requested_urls or [])
    if final_url:
        urls.append(final_url)
    for url in urls:
        if not _on_official_host(url):
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
    requested_urls: list[str] | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when one bounded GET confirmed a section page.

    A challenge, a captcha, a non-HTML body, a robots disallow, a login page,
    or an off-host redirect is not stored.
    """

    if robots_text is not None:
        for url in [page_url, *(requested_urls or []), final_url or ""]:
            if not url:
                continue
            if not robots_allows_path(robots_text, _robots_path(url)):
                return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=final_url,
        requested_urls=requested_urls,
    ):
        return None
    assert isinstance(page_html, str)
    stored_url = final_url or page_url
    try:
        return page_record(page_html, page_url=stored_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    A hyphen is a word boundary, so CC BY-NC is not CC BY and licenses/by
    does not match licenses/by-nc. Anchor text does not override the licence
    URL it points at. A generic creativecommons.org/licenses/ URL, with or
    without a trailing slash, is not a licence: http, a www host, and a query
    string on that path stay unknown, and the visible text of that anchor
    does not count. Text elsewhere on the page still counts. A specific deed
    URL such as licenses/by/4.0/ still counts. Mixed restricted and permissive
    text stays unknown. A software licence beside any Creative Commons deed
    stays unknown. Two software licences stay unknown. Two restricted deeds
    stay unknown. Public Domain Mark is not CC0. A copyright notice, All
    rights reserved, a terms link, and the host name are not licences.
    Apache License, Version 2.0 is apache-2.0. uk_ogl requires the British
    phrase Open Government Licence. Script, style, and comment text does not
    count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    ld_values = _jsonld_values(page_text, "license") + _jsonld_values(page_text, "licence")
    visible = _without_hidden(page_text)
    plain = _plain(_without_generic_licence_anchors(visible)).casefold().translate(_DASHES)
    hrefs = [href for href in _hrefs(visible) if not _generic_cc_licences_url(href)]
    blobs = [plain, *(_meta_values(visible, _LICENSE_META)), *ld_values, *hrefs]
    codes: set[str] = set()
    mit = False
    apache = False
    mpl = False
    for blob in blobs:
        folded = unescape(blob).casefold().translate(_DASHES)
        codes.update(_cc_codes(folded))
        mit = mit or bool(_MIT.search(folded) or _MIT_URL.search(folded))
        apache = apache or bool(_APACHE.search(folded) or _APACHE_URL.search(folded))
        mpl = mpl or bool(_MPL.search(folded) or _MPL_URL.search(folded))
    software = {name for name, present in (("mit", mit), ("apache", apache), ("mpl", mpl)) if present}
    ogl = _OGL_PHRASE.search(plain) is not None
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    other = bool(software or ogl)
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    if restricted and (permissive or other):
        return RIGHTS_UNKNOWN
    if permissive and other:
        return RIGHTS_UNKNOWN
    if len(software) > 1 or (software and ogl):
        return RIGHTS_UNKNOWN
    if restricted:
        named = restricted - {"mark"}
        if named == {"by-nc"}:
            return RIGHTS_CC_BY_NC
        if named == {"by-nd"}:
            return RIGHTS_CC_BY_ND
        if named == {"by-nc-sa"}:
            return RIGHTS_CC_BY_NC_SA
        if named == {"by-nc-nd"}:
            return RIGHTS_CC_BY_NC_ND
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
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    datePublished, article:published_time, and citation_publication_date count.
    article:modified_time, og:updated_time, dateModified, an updated or
    modified label, and a copyright year do not.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for raw in _jsonld_values(page_html, "datePublished"):
        found = _iso_day(raw)
        if found:
            return found
    visible = _without_hidden(page_html)
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
        if title and title.casefold() not in {"brookings", "the brookings institution"}:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title and title.casefold() not in {"brookings", "the brookings institution"}:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title and title.casefold() not in {"brookings", "the brookings institution"}:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Brookings Institution when the page names that publisher."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _clean_text(_metas(_without_hidden(page_html)).get("og:site_name", ""))
    if site in _SITE_NAMES:
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
        raise CatalogError("canonical URL must be a public Brookings artificial-intelligence page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OFFICIAL_HOST
        or not is_official_host(host)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not host
        or ".." in path
        or "\\" in path
        or "//" in path
        or not is_section_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Brookings artificial-intelligence page: {url}")
    return url


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and is_official_host(parsed.hostname or "")


def _robots_path(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _blocked_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name in {"sg-captcha", "x-captcha"}:
            return True
        if name == "server" and "akamai" in token:
            return True
    return False


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


def _jsonld_values(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    wanted = key.casefold()
    for block in _LDJSON.findall(page_html):
        text = block.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        _collect_key(payload, wanted, found)
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
        return
    if isinstance(value, str):
        if len(value) > MAX_DESCRIPTION_CHARS:
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    lowered = text.casefold()
    for suffix in _SITE_SUFFIXES:
        if lowered.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            lowered = text.casefold()
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


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


def _without_generic_licence_anchors(page_html: str) -> str:
    """Drop anchors whose href is only the generic Creative Commons licences path.

    The anchor's visible text is not a licence statement. Surrounding text stays.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a{match.group(1)}>").get("href", "")
        if _generic_cc_licences_url(href):
            return " "
        return match.group(0)

    return _ANCHOR_BLOCK.sub(replace, page_html)


def _generic_cc_licences_url(href: str) -> bool:
    """True for creativecommons.org/licenses with no deed, slash, or query optional."""

    if not isinstance(href, str) or not href.strip():
        return False
    parsed = urlparse(unescape(href).strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    path = (parsed.path or "").lower()
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return (
        parsed.scheme.lower() in {"http", "https"}
        and host in {"creativecommons.org", "www.creativecommons.org"}
        and path == "/licenses"
    )


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _robots_groups(text: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw_line in text.splitlines():
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
    return groups


def _matching_rules(
    groups: list[tuple[list[str], list[tuple[str, str]]]],
    user_agent: str,
) -> list[tuple[str, str]] | None:
    product = (user_agent or "").split("/", 1)[0].strip().lower()
    haystack = (user_agent or "").strip().lower()
    specific: list[tuple[int, list[tuple[str, str]]]] = []
    wildcard: list[tuple[str, str]] = []
    saw_wildcard = False
    for agents, rules in groups:
        matched_specific = False
        for agent in agents:
            if agent == "*":
                saw_wildcard = True
                wildcard.extend(rules)
                continue
            if product.startswith(agent) or (haystack.startswith(agent) and agent):
                matched_specific = True
        if matched_specific:
            specific.append((max(len(agent) for agent in agents if agent != "*"), rules))
    if specific:
        return max(specific, key=lambda item: item[0])[1]
    if saw_wildcard:
        return wildcard
    return None


def _path_allowed(rules: list[tuple[str, str]], path: str) -> bool:
    allowed = -1
    disallowed = -1
    for kind, pattern in rules:
        if not pattern or not _robots_pattern_matches(pattern, path):
            continue
        weight = len(pattern)
        if kind == "allow":
            allowed = max(allowed, weight)
        else:
            disallowed = max(disallowed, weight)
    if allowed < 0 and disallowed < 0:
        return True
    return allowed >= disallowed


def _robots_pattern_matches(pattern: str, path: str) -> bool:
    anchored = pattern.endswith(_ROBOTS_END)
    body = pattern[:-1] if anchored else pattern
    parts: list[str] = []
    for char in body:
        if char == "*":
            parts.append(".*")
        else:
            parts.append(re.escape(char))
    expression = "".join(parts)
    if anchored:
        return re.search(f"^{expression}$", path) is not None
    return re.search(f"^{expression}", path) is not None
