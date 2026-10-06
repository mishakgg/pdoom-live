"""Metadata catalog of public Simon Institute for Longterm Governance pages.

Each stored URL was confirmed with one bounded GET of HTML on simoninstitute.ch.
www.simoninstitute.ch redirects there. silg.ch and www.silg.ch do not resolve
and are omitted. A row keeps the title, publisher, canonical URL, date, and
rights label. Page bodies, abstracts, quotes, transcripts, and chart data are
not stored. A Cloudflare challenge, a SiteGround captcha, an HTTP 202, an
Akamai 403, a robots disallow, a login page, or a redirect off
simoninstitute.ch is not stored.

Rights stay unknown unless the page states a reuse licence. A sole CC BY-NC,
CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its own token. CC BY alone is
``creative_commons_attribution``. CC0, CC BY-SA, or a permissive mix of those
is ``creative_commons``. Mixed restricted and permissive text stays unknown.
A software licence beside any Creative Commons deed stays unknown. MIT,
Apache-2.0, and MPL-2.0 keep their own tokens; mixed software licences stay
unknown. A CC BY or CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or
public-domain mark URL stays unknown. A CC0 anchor on a publicdomain/mark URL
stays unknown. Public Domain Mark, all rights reserved, terms, and a host
name stay unknown. ``uk_ogl`` requires the British phrase Open Government
Licence. A generic creativecommons.org/licenses/ URL stays unknown, and the
text inside that anchor does not count. A photo credit, caption credit, or
image credit that names someone else's licence does not count. Script, style,
and comment text do not count. A hyphen is a word boundary, so CC BY does not
match CC BY-NC. The canonical Apache notice may include a comma.

A missing publication date stays unknown. Updated, modified, and copyright
years are not publication dates. The live URL is stored as confirmed. This
module does not fetch and it is not a belief collector. runner_wired stays
false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "silg_pages"
CATALOG_FILENAME = "silg_pages.json"
CATALOG_DESCRIPTION = (
    "Confirmed research, publication, and program pages on simoninstitute.ch. "
    "Each URL was one bounded GET. www.simoninstitute.ch redirects there. silg.ch and "
    "www.silg.ch are omitted. Challenges, robots disallows, login pages, and off-host "
    "redirects are not stored. Rows keep a title, publisher, canonical URL, date, and "
    "rights. Bodies, abstracts, quotes, transcripts, and chart data are omitted. Sole "
    "CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND keep their tokens. CC BY alone is "
    "creative_commons_attribution. CC0, CC BY-SA, or a permissive mix is creative_commons. "
    "Mixed deeds stay unknown. uk_ogl requires the British phrase Open Government Licence. "
    "Missing publication dates stay unknown. Updated, modified, and copyright years are "
    "not dates. Not a belief collector and runner_wired is false."
)
RUNNER_WIRED = False
PUBLISHER = "Simon Institute for Longterm Governance"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
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
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
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
OFFICIAL_HOST = "simoninstitute.ch"
OMITTED_HOSTS = ("silg.ch", "www.silg.ch", "www.simoninstitute.ch")
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
_PAGE_URL = re.compile(
    r"^https://simoninstitute\.ch"
    r"(?:/our-work|/blog/post/[a-z0-9]+(?:-[a-z0-9]+)*)$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_TYPE = re.compile(r'"@type"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_DATE_EL = re.compile(
    r"""(?is)<(div|span|time|p)\b([^>]*\bclass\s*=\s*["'][^"']*\bdate\b[^"']*["'][^>]*)>(.*?)</\1>"""
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_ARTICLE_TYPES = frozenset(
    {"article", "blogposting", "newsarticle", "scholarlyarticle", "report"}
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "/cdn-cgi/challenge-platform/",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "errors.edgesuite.net",
    "akamaighost",
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
    ".xml",
    ".zip",
)
_LOGIN_SEGMENTS = frozenset(
    {
        "account",
        "log-in",
        "login",
        "register",
        "sign-in",
        "sign-up",
        "signin",
        "signup",
        "wp-admin",
        "wp-login",
        "wp-login.php",
    }
)
_SITE_SUFFIXES = (
    " | Simon Institute for Longterm Governance",
    " - Simon Institute for Longterm Governance",
    " – Simon Institute for Longterm Governance",
    " — Simon Institute for Longterm Governance",
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
_MONTH_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{1,2}),\s+(\d{4})\b",
    re.I,
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
# Longer deeds are listed first. `(?!-)` keeps licenses/by from matching
# licenses/by-nc, and the text patterns refuse a following NC, ND, or SA.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![-a-z0-9])"
)
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cc-by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    (
        "cc-by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    ("cc-by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)"),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("cc-by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd\b")),
    ("cc-by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("cc-by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa\b")),
    ("cc-by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "cc0",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero\b"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    (
        "cc-by",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)"),
    ),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_PD_MARK = re.compile(r"public domain mark\b")
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_RESTRICTED_TOKEN = {
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
}
_MIT = re.compile(
    r"\bmit licen[cs]e\b"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
)
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,\s*version|\s+version|\s*,)?\s*2\.0\b"
    r"|apache\.org/licenses/license-2\.0(?![a-z0-9-])"
    r"|spdx\.org/licenses/apache-2\.0(?![a-z0-9-])"
)
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_HREF_ATTR = re.compile(
    r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# A deed path such as /licenses/by/4.0/ is not generic. Optional slash, query,
# http, and a www host still leave the URL generic.
_GENERIC_CC_LICENSES = re.compile(
    r"^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:\?[^#]*)?(?:#.*)?$"
)
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|caption|image)\s+credit\b")
_CREDIT_OPEN = re.compile(
    r"(?is)<(p|figcaption|li|em|span|caption|figure|small|cite|dd|td|div)\b[^>]*>"
)
_CREDIT_CLOSE = re.compile(
    r"(?is)</(?:p|figcaption|li|em|span|caption|figure|small|cite|dd|td|div)\s*>"
)
_MPL = re.compile(
    r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])"
    r"|\bmpl\s*2\.0\b"
    r"|\bmozilla public licen[cs]e(?:\s*2\.0)?\b"
)
_OGL_PHRASE = "open government licence"


class CatalogError(ValueError):
    """A catalog row or page failed the Simon Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for the confirmed simoninstitute.ch host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def robots_allows(body: str, path: str) -> bool:
    """True when the * group allows path. An empty Disallow allows every path."""
    if not isinstance(body, str):
        return False
    if "<html" in body[:500].casefold():
        return True
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix or not target.startswith(prefix):
            continue
        if kind == "allow":
            allowed = max(allowed, len(prefix))
        else:
            disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    return any(marker in lowered for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge.

    HTTP 202, HTTP 403, a Cloudflare or SiteGround challenge, an Akamai
    block, and a final URL on another host are not stored.
    """
    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    lowered = page_html[:12000].casefold()
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
    if final_url is not None and not _on_official_host(final_url):
        return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> dict | None:
    """Return metadata when the response is a confirmed on-host page."""
    target = final_url or page_url
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=target,
    ):
        return None
    if not _on_official_host(target) or _is_login_url(target):
        return None
    if robots_txt is not None and not robots_path_allowed(target, robots_txt):
        return None
    try:
        validate_canonical_url(target)
    except CatalogError:
        return None
    assert isinstance(page_html, str)
    return metadata_from_page(page_html, page_url=target)


def robots_path_allowed(url: str, robots_txt: str | None = None) -> bool:
    """A missing robots document does not block. A disallow blocks the path."""
    if robots_txt is None:
        return _on_official_host(url)
    if not _on_official_host(url):
        return False
    path = url[len("https://" + OFFICIAL_HOST) :] or "/"
    if path != "/" and not path.startswith("/"):
        return False
    return robots_allows(robots_txt, path.split("?", 1)[0].split("#", 1)[0])


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary, so CC BY-NC is not CC BY and licenses/by is not licenses/by-nc.
    A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its token.
    ``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is
    CC0, CC BY-SA, or a permissive mix of CC0, CC BY, and CC BY-SA. Mixed
    restricted and permissive text stays unknown. Public Domain Mark is not
    CC0, and a CC0, CC BY, or CC BY-SA label on a mark or other deed URL stays
    unknown. MIT, Apache-2.0, and MPL-2.0 stay their own tokens. A software
    licence beside any Creative Commons deed stays unknown. ``uk_ogl`` requires
    the British phrase Open Government Licence in the visible page text. The
    text of an anchor whose href is only creativecommons.org/licenses/ does not
    count. A photo, caption, or image credit that names another licence does
    not count. Script, style, and comment text do not count.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl = _rights_signals(page_text)
    if "pd-mark" in cc_codes:
        return RIGHTS_UNKNOWN
    restricted = cc_codes & _RESTRICTED
    permissive = cc_codes & _PERMISSIVE
    families = [
        family
        for family in (
            restricted,
            permissive,
            software,
            {"uk_ogl"} if ogl else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive == {"cc-by"}:
            return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated label, and a
    copyright year are not publication dates.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for blob in _LDJSON.findall(page_html):
        types = {match.group(1).casefold() for match in _LD_TYPE.finditer(blob)}
        if not types & _ARTICLE_TYPES:
            continue
        for raw in _DATE_PUBLISHED.findall(blob):
            parsed = _iso_day(raw)
            if parsed:
                return parsed
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            return parsed
    for parsed in _date_labels(visible):
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    for heading in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", heading))
        if title:
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the institute when the page names it.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    title_tag = _TITLE.search(visible)
    title = _clean_text(_TAG.sub(" ", title_tag.group(1))) if title_tag else ""
    if PUBLISHER.casefold() in title.casefold() or PUBLISHER.casefold() in site.casefold():
        return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another host is not used.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_join_official(live, href))
    except CatalogError:
        return live
    if _same_page(declared, live):
        return declared
    return live


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or description != description.strip():
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
    _require_text(entry.get("title"), "title")
    _require_text(entry.get("publisher"), "publisher")
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or _PAGE_URL.fullmatch(url) is None:
        raise CatalogError(f"canonical URL must be a public simoninstitute.ch page: {url}")
    path = url[len("https://" + OFFICIAL_HOST) :]
    if (
        not is_official_host(OFFICIAL_HOST)
        or hostname_is_blocked(OFFICIAL_HOST)
        or _is_login_url(url)
        or ".." in path
        or "\\" in path
        or "//" in path
        or path.lower().endswith(_DOWNLOAD_SUFFIXES)
    ):
        raise CatalogError(f"canonical URL must be a public simoninstitute.ch page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool]:
    visible = _drop_generic_cc_anchors(_drop_credit_licences(_visible(page_text)))
    return _cc_codes(visible), _software_codes(visible), _states_ogl(visible)


def _drop_generic_cc_anchors(html: str) -> str:
    """Remove anchors that point at the generic Creative Commons licences URL.

    The anchor text is not a deed. Text outside the anchor still is.
    """

    def replace(match: re.Match[str]) -> str:
        href_match = _HREF_ATTR.search(match.group(1))
        if href_match is None:
            return match.group(0)
        href = href_match.group(1) or href_match.group(2) or href_match.group(3) or ""
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    folded = _fold(href)
    return _GENERIC_CC_LICENSES.fullmatch(folded) is not None


def _drop_credit_licences(html: str) -> str:
    """Drop a photo, caption, or image credit, including a licence it names."""
    spans: list[tuple[int, int]] = []
    for match in _CREDIT_PHRASE.finditer(html):
        start_region = max(0, match.start() - 500)
        opens = list(_CREDIT_OPEN.finditer(html[start_region : match.start()]))
        removed = False
        if opens:
            last = opens[-1]
            abs_open = start_region + last.start()
            close = re.search(
                rf"(?is)</{last.group(1)}\s*>",
                html[match.end() : match.end() + 1500],
            )
            if close is not None:
                abs_end = match.end() + close.end()
                if abs_end - abs_open <= 2000:
                    spans.append((abs_open, abs_end))
                    removed = True
        if removed:
            continue
        close = _CREDIT_CLOSE.search(html[match.end() : match.end() + 1200])
        end = match.end() + close.end() if close is not None else min(match.end() + 800, len(html))
        spans.append((match.start(), end))
    if not spans:
        return html
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    pieces: list[str] = []
    cursor = 0
    for start, end in merged:
        pieces.append(html[cursor:start])
        pieces.append(" ")
        cursor = end
    pieces.append(html[cursor:])
    return "".join(pieces)


def _cc_codes(value: str) -> set[str]:
    folded = _fold(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("code")
        if code:
            codes.add(f"cc-{code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
        elif match.group("pd") == "mark":
            codes.add("pd-mark")
    for name, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(name)
    if _PD_MARK.search(folded):
        codes.add("pd-mark")
    return codes


def _software_codes(value: str) -> set[str]:
    folded = _fold(value)
    found: set[str] = set()
    if _MIT.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _states_ogl(visible_html: str) -> bool:
    text = _plain(visible_html).replace("\xa0", " ")
    folded = re.sub(r"\s+", " ", text).casefold()
    return _OGL_PHRASE in folded


def _wildcard_rules(body: str) -> list[tuple[str, str]] | None:
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
    for group_agents, group_rules in groups:
        if "*" in group_agents:
            return group_rules
    return None


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    host = url[len("https://") :].split("/", 1)[0].split(":", 1)[0].lower().rstrip(".")
    return is_official_host(host)


def _is_login_url(url: str) -> bool:
    if not isinstance(url, str) or "://" not in url:
        return False
    path = url.split("://", 1)[1].split("/", 1)
    tail = "/" + path[1] if len(path) > 1 else "/"
    tail = tail.split("?", 1)[0].split("#", 1)[0].casefold()
    segments = {part for part in tail.split("/") if part}
    if segments & _LOGIN_SEGMENTS:
        return True
    return "wp-login" in tail or tail.startswith("/wp-admin")


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    for suffix in _SITE_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    if not text or len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _require_text(value: object, field: str) -> None:
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
        if len(value) > MAX_DESCRIPTION_CHARS and path != "$.description":
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _same_page(left: str, right: str) -> bool:
    return left.rstrip("/") == right.rstrip("/")


def _join_official(base: str, href: str) -> str:
    ref = unescape(href).strip()
    if ref.startswith("https://") or ref.startswith("http://"):
        return ref.split("#", 1)[0].split("?", 1)[0]
    if ref.startswith("/"):
        return "https://" + OFFICIAL_HOST + ref.split("#", 1)[0].split("?", 1)[0]
    return ref


def _iso_day(raw: object) -> str | None:
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


def _date_labels(visible_html: str) -> list[str]:
    found: list[str] = []
    for _tag, attrs, body in _DATE_EL.findall(visible_html):
        parsed_attrs = _attrs(f"<x {attrs}>")
        class_name = parsed_attrs.get("class", "").replace("-", " ").replace("_", " ")
        tokens = {token.casefold() for token in class_name.split()}
        if "date" not in tokens:
            continue
        if tokens & {"updated", "modified", "copyright"}:
            continue
        text = _clean_text(body)
        folded = text.casefold()
        if any(word in folded for word in ("updated", "modified", "copyright")):
            continue
        parsed = _month_day(text) or _iso_day(text)
        if parsed:
            found.append(parsed)
    return found


def _month_day(text: str) -> str | None:
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


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(_visible(page_html)):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""
