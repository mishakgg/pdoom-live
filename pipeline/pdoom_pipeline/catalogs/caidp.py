"""Metadata catalog of public Center for AI and Digital Policy pages.

Each stored URL was confirmed with one bounded GET that returned HTML on
www.caidp.org. caidp.org redirects there. A row keeps the title, publisher,
canonical URL, date, and rights label. Page bodies, abstracts, quotes,
transcripts, and chart data are not stored. A Cloudflare challenge, a
SiteGround captcha, an HTTP 202 challenge, an Akamai 403, a robots disallow,
a login page, a non-HTML response, or a redirect off www.caidp.org is not
stored.

Rights stay unknown unless the page states a reuse licence. A sole CC BY-NC,
CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its own token. CC BY alone is
``creative_commons_attribution``. CC0, CC BY-SA, or a permissive mix of those
is ``creative_commons``. Mixed restricted and permissive text stays unknown.
A software licence beside any Creative Commons deed stays unknown. A CC BY or
CC BY-SA anchor on a by-nc, by-nd, by-nc-sa, by-nc-nd, or public-domain mark
URL stays unknown. A CC0 anchor on a publicdomain/mark URL stays unknown.
Public Domain Mark, all rights reserved, terms, and the host name stay
unknown. MIT, Apache-2.0, and MPL-2.0 keep their own tokens. Mixed software
licences stay unknown. ``uk_ogl`` requires the British phrase Open Government
Licence. A generic creativecommons.org/licenses/ URL stays unknown. A missing
publication date stays unknown. Updated, modified, and copyright years are
not publication dates.

This module does not fetch. runner_wired stays false. It is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "caidp_pages"
CATALOG_FILENAME = "caidp_pages.json"
CATALOG_DESCRIPTION = (
    "Metadata for confirmed public Center for AI and Digital Policy research, "
    "publication, and policy pages on www.caidp.org. caidp.org redirects to "
    "that host. Each URL was confirmed by one bounded GET. Login "
    "pages, challenges, robots disallows, and off-host redirects are omitted. "
    "Rows keep a title, publisher, canonical URL, date, and rights. Page "
    "bodies, abstracts, quotes, transcripts, and chart data are omitted. A "
    "sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its own token. "
    "CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a "
    "permissive mix of those is creative_commons. Mixed licences stay unknown. "
    "uk_ogl requires the phrase Open Government Licence. Updated, modified, "
    "and copyright years are not dates. This catalog is not a belief "
    "collector and runner_wired is false."
)
RUNNER_WIRED = False
PUBLISHER = "Center for AI and Digital Policy"
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
OFFICIAL_HOST = "www.caidp.org"
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
_TOPIC_PREFIXES = (
    "/california",
    "/cases",
    "/caidp-update",
    "/public-voice",
    "/reports",
    "/resources",
    "/statements",
    "/universal-guidelines-for-ai",
)
_LOGIN_SEGMENTS = frozenset(
    {
        "account",
        "accounts",
        "auth",
        "log-in",
        "log-out",
        "login",
        "logout",
        "sign-in",
        "signin",
        "wp-login.php",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_REFRESH = re.compile(
    r"(?is)<meta\b[^>]*http-equiv\s*=\s*['\"]refresh['\"][^>]*>"
)
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_TYPE = re.compile(r'"@type"\s*:\s*"([^"]+)"')
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')
_ARTICLE_TYPES = frozenset(
    {"article", "blogposting", "newsarticle", "report", "scholarlyarticle"}
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dc.date.issued",
    "dcterms.issued",
)
_LICENSE_META = frozenset(
    {
        "dc.rights",
        "dcterms.license",
        "dcterms.rights",
        "licence",
        "license",
        "rights",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_SITE_SUFFIXES = (
    " - Center for AI and Digital Policy",
    " | Center for AI and Digital Policy",
    " – Center for AI and Digital Policy",
    " — Center for AI and Digital Policy",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "/.well-known/sgcaptcha",
    "/cdn-cgi/challenge-platform/",
    "akamaighost",
    "attention required",
    "cf-mitigated",
    "challenge-platform",
    "checking your browser",
    "enable javascript and cookies",
    "errors.edgesuite.net",
    "just a moment",
    "performing security verification",
    "sg-captcha",
    "sgcaptcha",
    "sorry, you have been blocked",
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
        "\u00a0": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
# Longer deeds are listed first. `(?!-)` makes a hyphen a word boundary, so
# CC BY and licenses/by do not match CC BY-NC or licenses/by-nc.
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "by-nc-nd",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])"),
    ),
    (
        "by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])"),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9])")),
    (
        "by-nc",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial"),
    ),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    ("by-nd", re.compile(r"creative commons attribution[\s-]*no[\s-]*deriv")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9])")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]*share[\s-]*alike")),
    (
        "zero",
        re.compile(r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])"),
    ),
    (
        "zero",
        re.compile(r"creative commons(?:\s+public\s+domain)?[\s-]*zero(?![a-z])"),
    ),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![a-z0-9])")),
    (
        "by",
        re.compile(
            r"creative commons attribution(?![\s-]*(?:non|no[\s-]*deriv|share))"
        ),
    ),
    ("mark", re.compile(r"public domain mark")),
)
_URL_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("by-nc-nd", re.compile(r"creativecommons\.org/licenses/by-nc-nd(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(r"creativecommons\.org/licenses/by-nc-sa(?![a-z0-9-])")),
    ("by-nc", re.compile(r"creativecommons\.org/licenses/by-nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"creativecommons\.org/licenses/by-nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"creativecommons\.org/licenses/by-sa(?![a-z0-9-])")),
    ("by", re.compile(r"creativecommons\.org/licenses/by(?!-)(?![a-z0-9])")),
    ("zero", re.compile(r"creativecommons\.org/publicdomain/zero(?![a-z0-9-])")),
    ("mark", re.compile(r"creativecommons\.org/publicdomain/mark(?![a-z0-9-])")),
)
_RESTRICTED_TOKENS = {
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
}
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_MIT_PHRASE = re.compile(r"\bmit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_PHRASE = re.compile(r"\bapache-2\.0\b|\bapache licen[cs]e(?:\s+version)?\s*2\.0\b")
_APACHE_URL = re.compile(
    r"(?:www\.)?apache\.org/licenses/license-2\.0(?![a-z0-9])|spdx\.org/licenses/apache-2\.0(?![a-z0-9-])"
)
_MPL_PHRASE = re.compile(r"\bmpl-2\.0\b|\bmozilla public licen[cs]e(?:\s*2\.0)?\b")
_MPL_URL = re.compile(r"mozilla\.org/mpl/2\.0(?![a-z0-9])")
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")


class CatalogError(ValueError):
    """A catalog row or page failed the Center for AI and Digital Policy page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_caidp_host(hostname: str) -> bool:
    """True only for the confirmed www.caidp.org host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_topic_path(path: str) -> bool:
    """True for a research, publication, or policy path on the official host."""
    bare = _bare_path(path)
    if _is_login_path(bare) or _is_download(bare):
        return False
    if bare == "/":
        return True
    return any(bare == prefix or bare.startswith(prefix + "/") for prefix in _TOPIC_PREFIXES)


def robots_allows(body: str, path: str) -> bool:
    """True when the * group allows path. An empty Disallow allows every path."""
    if not isinstance(body, str) or not isinstance(path, str):
        return False
    if "<html" in body[:500].casefold():
        return True
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
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


def is_redirect_document(page_html: str) -> bool:
    """True when the HTML is an on-page refresh rather than the page itself."""
    if not isinstance(page_html, str):
        return False
    return _REFRESH.search(page_html[:4000]) is not None


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge.

    HTTP 202, HTTP 403, a Cloudflare or SiteGround challenge, an Akamai
    block, a login path, a robots disallow, and a final URL on another host
    are not stored.
    """
    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if is_redirect_document(page_html):
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
    target = final_url
    if target is not None and not _on_official_host(target):
        return False
    if target is not None:
        path = urlparse(target).path or "/"
        if not is_topic_path(path) or _is_login_path(path):
            return False
        if robots_txt is not None and not robots_allows(robots_txt, path):
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
    """Return metadata when the response is the confirmed page HTML."""
    target = final_url or page_url
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=target,
        robots_txt=robots_txt,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label stated by the page, or unknown.

    Restricted deeds are matched before permissive ones. A hyphen is a word
    boundary, so CC BY does not match CC BY-NC. A page that states both a
    restricted deed and a permissive deed stays unknown.
    ``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is
    CC0, CC BY-SA, or a permissive mix of CC0, CC BY, and CC BY-SA. Public
    Domain Mark is not CC0. A CC BY or CC BY-SA label on a restricted or
    public-domain mark URL stays unknown, as does a CC0 label on a
    publicdomain/mark URL. MIT, Apache-2.0, and MPL-2.0 stay their own
    tokens. A software licence beside any Creative Commons deed stays
    unknown. ``uk_ogl`` requires the phrase Open Government Licence.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    plain = _plain(visible)
    folded = plain.casefold().translate(_DASHES)
    codes = _text_codes(folded)
    hrefs = _hrefs(visible)
    for href in hrefs:
        codes |= _url_code(href.casefold().translate(_DASHES))
    licence_bits: list[str] = []
    for key, content in _meta_pairs(visible):
        if key not in _LICENSE_META:
            continue
        chunk = _plain(content).casefold().translate(_DASHES)
        licence_bits.append(chunk)
        codes |= _text_codes(chunk)
        codes |= _url_code(chunk)
    scanned = " ".join([folded, *licence_bits, *(href.casefold() for href in hrefs)])
    mit = bool(_MIT_PHRASE.search(scanned) or any(_MIT_URL.search(href.casefold()) for href in hrefs))
    apache = bool(
        _APACHE_PHRASE.search(scanned) or any(_APACHE_URL.search(href.casefold()) for href in hrefs)
    )
    mpl = bool(_MPL_PHRASE.search(scanned) or any(_MPL_URL.search(href.casefold()) for href in hrefs))
    return _label(
        codes,
        mit=mit,
        apache=apache,
        mpl=mpl,
        ogl=bool(_OGL_PHRASE.search(folded)),
    )


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    Updated, modified, and copyright years are not publication dates. A date
    inside script, style, or comment text does not count, except a
    datePublished field on an article-like JSON-LD object.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for blob in _LDJSON.findall(page_html):
        types = {match.group(1).casefold() for match in _LD_TYPE.finditer(blob)}
        if not types & _ARTICLE_TYPES:
            continue
        for raw in _DATE_PUBLISHED.findall(blob):
            found = _iso_prefix(raw)
            if found:
                return found
    metas = _metas(_without_hidden(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key))
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
    title_tag = _TITLE.search(visible)
    document_title = _clean_title(title_tag.group(1) if title_tag else "")
    if document_title:
        return document_title
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the Center for AI and Digital Policy when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical does not replace it.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
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
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog contract")
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
        raise CatalogError(f"rights must be a known label or unknown: {entry.get('rights')}")
    if "p(doom)" in entry["title"].casefold():
        raise CatalogError("title must not store a p(doom) figure")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public www.caidp.org page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not official_caidp_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or not is_topic_path(path)
        or not robots_allows(_CONFIRMED_ROBOTS, path)
        or not _path_shape(path)
    ):
        raise CatalogError(f"canonical URL must be a public www.caidp.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


_CONFIRMED_ROBOTS = """User-agent: *
Disallow: /app/
Disallow: /j/
Allow: /app/module/webproduct/goto/
Allow: /app/download/
Crawl-Delay: 5
"""


def _label(
    codes: set[str],
    *,
    mit: bool,
    apache: bool,
    mpl: bool,
    ogl: bool,
) -> str:
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    restricted = codes & set(_RESTRICTED_TOKENS)
    permissive = codes & _PERMISSIVE
    families = [
        name
        for name, present in (
            ("restricted", bool(restricted)),
            ("permissive", bool(permissive)),
            ("mit", mit),
            ("apache", apache),
            ("mpl", mpl),
            ("ogl", ogl),
        )
        if present
    ]
    if len(families) != 1:
        return RIGHTS_UNKNOWN
    if restricted:
        if len(restricted) != 1:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if permissive:
        if permissive == {"by"}:
            return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if ogl:
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def _text_codes(folded: str) -> set[str]:
    found: list[tuple[int, int, str]] = []
    for code, pattern in _TEXT_DEEDS:
        for match in pattern.finditer(folded):
            start, end = match.span()
            if any(start < prev_end and end > prev_start for prev_start, prev_end, _code in found):
                continue
            found.append((start, end, code))
    return {code for _start, _end, code in found}


def _url_code(value: str) -> set[str]:
    for code, pattern in _URL_DEEDS:
        if pattern.search(value):
            return {code}
    return set()


def _bare_path(path: str) -> str:
    bare = path or "/"
    if bare != "/" and bare.endswith("/"):
        bare = bare[:-1]
    return bare or "/"


def _is_login_path(path: str) -> bool:
    segments = [segment.casefold() for segment in (path or "").split("/") if segment]
    return any(segment in _LOGIN_SEGMENTS for segment in segments)


def _is_download(path: str) -> bool:
    bare = _bare_path(path).casefold()
    return bare.endswith(_DOWNLOAD_SUFFIXES)


def _path_shape(path: str) -> bool:
    if path in {"", "/"}:
        return True
    if not path.startswith("/"):
        return False
    body = path[1:]
    if body.endswith("/"):
        body = body[:-1]
    if not body:
        return True
    return all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", segment) for segment in body.split("/"))


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and official_caidp_host(parsed.hostname or "")


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
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    if not text or len(text) > MAX_TEXT_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip()


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
        limit = MAX_DESCRIPTION_CHARS if path == "$.description" else MAX_TEXT_CHARS
        if path == "$.description":
            return
        if len(value) > limit:
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
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


def _hrefs(visible_html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in [*_LINK.findall(visible_html), *_ANCHOR.findall(visible_html)]:
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _meta_pairs(visible_html: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for tag in _META.findall(visible_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs:
            pairs.append((key, attrs["content"]))
    return pairs


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, content in _meta_pairs(page_html):
        found.setdefault(key, content)
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
