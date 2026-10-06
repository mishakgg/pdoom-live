"""Metadata catalog of public LawZero pages.

The nonprofit at lawzero.org is the publisher. www.lawzero.org redirects to
lawzero.org. A row is stored only when one bounded GET stays on an official
LawZero host and returns HTML. A Cloudflare challenge, a captcha, an HTTP 202,
an Akamai block, a TLS failure, a robots disallow, a consent interstitial, or
a redirect off the official host stores nothing. An empty entry list is valid
when every confirming GET is blocked. This module does not fetch.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, quotes, transcripts, and chart data are not stored.
A missing date is unknown. Updated, modified, and copyright years are not
publication dates. The live URL is stored as confirmed.

Rights stay unknown unless the page states a reuse licence. creative_commons
is only CC0 or CC BY-SA. A page that states CC BY together with CC0 or CC
BY-SA may use creative_commons. creative_commons_attribution is only a CC BY
deed that does not state NC, ND, or SA. cc_by_nc, cc_by_nd, cc_by_nc_nd, and
cc_by_nc_sa stay their own tokens. A hyphen is a word boundary, so CC BY does
not match CC BY-NC and licenses/by does not match licenses/by-nc. Longer deeds
are checked first. A restricted deed beside a permissive deed stays unknown.
A deceptive anchor, a bare creativecommons.org/licenses/ URL, and the Public
Domain Mark stay unknown. uk_ogl requires the British phrase open government
licence. us_government_work requires a rights field. mit, apache-2.0, and
mpl-2.0 stay their own tokens. Mixed software licences stay unknown. This
catalog is not a belief collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "lawzero_pages"
CATALOG_FILENAME = "lawzero_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
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
RIGHTS_LABELS = frozenset(
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
OFFICIAL_HOSTS = frozenset({"lawzero.org", "www.lawzero.org"})
PUBLISHERS = frozenset({"LawZero", "LoiZéro"})
MAX_RESPONSE_BYTES = 1_000_000
FETCH_TIMEOUT_SECONDS = 15
MAX_REDIRECTS = 3
OGL_PHRASE = "open government licence"
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
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>.*?</a>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_BODY_CLASS = re.compile(r"(?is)<body\b[^>]*\bclass\s*=\s*['\"]([^'\"]*)['\"]")
_POST_DATE = re.compile(
    r"(?is)field--name-node-post-date\b.{0,500}?(\d{2}) (\d{2}) (\d{4})"
)
_RIGHTS_CELL = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_LICENSE_META = frozenset(
    {"license", "licence", "dc.license", "dcterms.license", "rights", "dc.rights", "dcterms.rights"}
)
_PUBLISHED_META = frozenset(
    {"article:published_time", "citation_publication_date", "datepublished", "dcterms.issued"}
)
_SITE_SUFFIX = re.compile(r"\s*(?:\||\u2758|\u2013|\u2014|-)\s*(lawzero|loizéro)\s*$")
_SITE_PREFIX = re.compile(r"^(lawzero|loizéro)\s*(?:\||\u2758|\u2013|\u2014|-)\s*")
_TITLE_SUFFIX = re.compile(r"(?i)\s*(?:\||\u2758|\u2013|\u2014|-)\s*(?:LawZero|LoiZéro)\s*$")
_TITLE_PREFIX = re.compile(r"(?i)^(?:LawZero|LoiZéro)\s*(?:\||\u2758|\u2013|\u2014|-)\s*")
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
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
    ".xml",
    ".zip",
)
_BLOCKED_PREFIXES = (
    "/admin",
    "/comment/reply",
    "/composer",
    "/core",
    "/filter/tips",
    "/index.php",
    "/media/oembed",
    "/modules",
    "/node/add",
    "/profiles",
    "/search",
    "/themes",
    "/user/login",
    "/user/logout",
    "/user/password",
    "/user/register",
)
_PATH = re.compile(r"/[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*/?")
_CHALLENGE_MARKERS = (
    "akamai bot manager",
    "akamaighost",
    "are you a robot",
    "are you human",
    "attention required",
    "cf-browser-verification",
    "cf-mitigated",
    "challenge-platform",
    "checking your browser",
    "consent interstitial",
    "enable javascript and cookies",
    "errors.edgesuite.net",
    "just a moment",
    "performing security verification",
    "please verify you are a human",
    "robot interstitial",
    "sgcaptcha",
    "siteground captcha",
    "/cdn-cgi/challenge",
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
# Longer deeds are listed first. A hyphen is a word boundary: (?![a-z0-9-])
# keeps CC BY from matching CC BY-NC and licenses/by from matching licenses/by-nc.
_DEED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "by-nc-nd",
        re.compile(
            r"(?:creativecommons\.org/licenses/by-nc-nd(?![a-z0-9-])"
            r"|\bcc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv)"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?:creativecommons\.org/licenses/by-nc-sa(?![a-z0-9-])"
            r"|\bcc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike)"
        ),
    ),
    (
        "by-nc",
        re.compile(
            r"(?:creativecommons\.org/licenses/by-nc(?![a-z0-9-])"
            r"|\bcc[\s-]*by[\s-]*nc(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution[\s-]+non[\s-]*commercial(?![a-z0-9-]))"
        ),
    ),
    (
        "by-nd",
        re.compile(
            r"(?:creativecommons\.org/licenses/by-nd(?![a-z0-9-])"
            r"|\bcc[\s-]*by[\s-]*nd(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution[\s-]+no[\s-]*deriv)"
        ),
    ),
    (
        "by-sa",
        re.compile(
            r"(?:creativecommons\.org/licenses/by-sa(?![a-z0-9-])"
            r"|\bcc[\s-]*by[\s-]*sa(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution[\s-]+share[\s-]*alike(?![a-z0-9-]))"
        ),
    ),
    (
        "by",
        re.compile(
            r"(?:creativecommons\.org/licenses/by(?![a-z0-9-])"
            r"|\bcc[\s-]*by(?![a-z0-9-])"
            r"|creative\s+commons\s+attribution(?![a-z0-9-])(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike)))"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?:creativecommons\.org/publicdomain/zero(?![a-z0-9-])"
            r"|\bcc0(?![a-z0-9-])"
            r"|\bcc[\s-]+0(?![a-z0-9-])"
            r"|\bcc[\s-]*zero\b"
            r"|creative\s+commons(?:\s+public\s+domain)?[\s-]+zero\b)"
        ),
    ),
    (
        "mark",
        re.compile(
            r"(?:creativecommons\.org/publicdomain/mark(?![a-z0-9-])"
            r"|public\s+domain\s+mark\b)"
        ),
    ),
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
_MIT = re.compile(r"(?:\bmit\s+licen[cs]e\b|\blicen[cs]ed\s+under\s+(?:the\s+)?mit(?:\s+licen[cs]e)?\b)")
_APACHE = re.compile(
    r"(?:\bapache-2\.0\b|\bapache\s+licen[cs]e(?:\s*,?\s*version)?\s*2(?:\.0)?\b"
    r"|\blicen[cs]ed\s+under\s+(?:the\s+)?apache(?:\s+licen[cs]e)?(?:\s*,?\s*version)?\s*2(?:\.0)?\b)"
)
_MPL = re.compile(r"(?:\bmpl-2\.0\b|\bmpl\s*2\.0\b|\bmozilla\s+public\s+licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b)")
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_PUBLISHER_CANONICAL = {"lawzero": "LawZero", "loizéro": "LoiZéro"}


class CatalogError(ValueError):
    """A catalog row or page failed the LawZero page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for lawzero.org and www.lawzero.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str, headers: Mapping[str, str] | None = None) -> bool:
    """True when the response is a block, captcha, or consent interstitial."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    if headers:
        for key, value in headers.items():
            folded = f"{key} {value}".casefold()
            if "cf-mitigated" in folded or "edgesuite" in folded or "akamai" in folded:
                return True
    return False


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that stayed on an official LawZero host."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html, headers):
        return False
    try:
        validate_canonical_url(page_url)
    except CatalogError:
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
    """Return metadata when the response is LawZero HTML.

    A challenge page, an HTTP 202 response, a non-HTML body, or a URL that is
    not on an official LawZero host is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label stated by the page, or unknown.

    creative_commons is only CC0 or CC BY-SA, including a page that also states
    CC BY. creative_commons_attribution is CC BY alone. Restricted deeds keep
    their own tokens. A hyphen does not end CC BY early. Mixed restricted and
    permissive deeds, a deceptive CC BY anchor, a bare licences URL, and the
    Public Domain Mark stay unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes = _page_deed_codes(page_text)
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    groups = 0
    if codes & _RESTRICTED:
        groups += 1
    if codes & _PERMISSIVE:
        groups += 1
    software = _software_tokens(page_text)
    if software:
        groups += 1
    ogl = _states_uk_ogl(page_text)
    gov = _states_us_government_work(page_text)
    if ogl:
        groups += 1
    if gov:
        groups += 1
    if groups != 1:
        return RIGHTS_UNKNOWN
    if codes & _RESTRICTED:
        found = codes & _RESTRICTED
        if len(found) != 1:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(found))]
    if codes & _PERMISSIVE:
        return _permissive_label(codes & _PERMISSIVE)
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
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
    for raw in _meta_values(page_text, _PUBLISHED_META):
        found = _iso_prefix(raw)
        if found:
            return found
    if _is_index_page(page_text):
        return UNKNOWN_DATE
    posted = _post_dates(page_text)
    if len(posted) == 1:
        return posted[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if _usable_title(title):
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return LawZero or LoiZéro when the page states that organization name.

    A person named in the title is not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title"):
        publisher = _publisher_name(metas.get(key, ""))
        if publisher:
            return publisher
    title_tag = _TITLE.search(visible)
    if title_tag:
        publisher = _publisher_name(title_tag.group(1))
        if publisher:
            return publisher
    for key in ("og:site_name", "apple-mobile-web-app-title"):
        publisher = _publisher_name(_clean_text(metas.get(key, "")))
        if publisher:
            return publisher
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
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
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if description != description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if "p(doom)" in description.casefold():
        raise CatalogError("description must not store a p(doom) figure")
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
    if entry["publisher"] not in PUBLISHERS:
        raise CatalogError("publisher must be LawZero or LoiZéro")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be an official LawZero page")
    parsed = _parse_https(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an official LawZero page: {url}")
    host, port, path = parsed
    lowered = path.casefold()
    if (
        port is not None
        or not is_official_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or not _html_path(path)
        or lowered.endswith(_DOWNLOAD_SUFFIXES)
        or "/media/oembed" in lowered
        or _blocked_prefix(lowered)
    ):
        raise CatalogError(f"canonical URL must be an official LawZero page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _permissive_label(codes: frozenset[str] | set[str]) -> str:
    """CC0 or CC BY-SA is creative_commons. CC BY alone is attribution."""

    if codes <= {"by", "by-sa", "zero"} and codes & {"by-sa", "zero"}:
        return RIGHTS_CREATIVE_COMMONS
    if codes == {"by"}:
        return RIGHTS_CC_BY
    return RIGHTS_UNKNOWN


def _page_deed_codes(page_text: str) -> set[str]:
    codes: set[str] = set()
    visible = _without_hidden(page_text)
    kept: list[str] = []
    cursor = 0
    for match in _ANCHOR.finditer(visible):
        kept.append(visible[cursor : match.start()])
        cursor = match.end()
        href = _attrs(match.group(0)).get("href", "")
        inner = _plain(match.group(0))
        href_codes = _deed_codes(_fold(href))
        text_codes = _deed_codes(_fold(inner))
        href_bad = href_codes & (_RESTRICTED | {"mark"})
        if href_bad and (text_codes & _PERMISSIVE) and not (text_codes & _RESTRICTED):
            continue
        codes.update(href_codes)
        codes.update(text_codes)
    kept.append(visible[cursor:])
    codes.update(_deed_codes(_fold(_plain(" ".join(kept)))))
    for tag in _LINK.findall(visible):
        href = _attrs(tag).get("href", "")
        if href:
            codes.update(_deed_codes(_fold(href)))
    for content in _meta_values(visible, _LICENSE_META):
        codes.update(_deed_codes(_fold(content)))
    for value in _jsonld_strings(page_text, "license"):
        codes.update(_deed_codes(_fold(value)))
    return codes


def _deed_codes(folded: str) -> set[str]:
    found: set[str] = set()
    if not folded:
        return found
    for name, pattern in _DEED_PATTERNS:
        if pattern.search(folded):
            found.add(name)
    return found


def _software_tokens(page_text: str) -> set[str]:
    visible = _fold(_plain(_without_hidden(page_text)))
    pieces = [visible]
    for content in _meta_values(_without_hidden(page_text), _LICENSE_META):
        pieces.append(_fold(content))
    for value in _jsonld_strings(page_text, "license"):
        pieces.append(_fold(value))
    blob = "\n".join(pieces)
    found: set[str] = set()
    if _MIT.search(blob):
        found.add(RIGHTS_MIT)
    if _APACHE.search(blob):
        found.add(RIGHTS_APACHE)
    if _MPL.search(blob):
        found.add(RIGHTS_MPL)
    return found


def _states_uk_ogl(page_text: str) -> bool:
    visible = _fold(_plain(_without_hidden(page_text)))
    fields = _rights_field_text(page_text)
    return OGL_PHRASE in visible or OGL_PHRASE in fields


def _states_us_government_work(page_text: str) -> bool:
    fields = _rights_field_text(page_text)
    if not fields or _NEGATED_GOV_WORK.search(fields):
        return False
    return _GOV_WORK.search(fields) is not None


def _rights_field_text(page_text: str) -> str:
    visible = _without_hidden(page_text)
    parts = list(_meta_values(visible, _LICENSE_META))
    for cell in _RIGHTS_CELL.findall(visible):
        parts.append(_plain(cell))
    parts.extend(_jsonld_strings(page_text, "rights"))
    parts.extend(_jsonld_strings(page_text, "license"))
    return _fold("\n".join(parts))


def _is_index_page(page_html: str) -> bool:
    match = _BODY_CLASS.search(page_html)
    if not match:
        return False
    classes = match.group(1).casefold().split()
    if "frontpage" in classes:
        return True
    return any("listing" in name for name in classes)


def _post_dates(page_html: str) -> list[str]:
    found: list[str] = []
    for day_text, month_text, year_text in _POST_DATE.findall(page_html):
        try:
            parsed = date(int(year_text), int(month_text), int(day_text))
        except ValueError:
            continue
        iso = parsed.isoformat()
        if iso not in found:
            found.append(iso)
    return found


def _parse_https(url: str) -> tuple[str, str | None, str] | None:
    if not url.startswith("https://"):
        return None
    rest = url[len("https://") :]
    if not rest or any(mark in rest for mark in "?#@"):
        return None
    if "/" in rest:
        authority, path_rest = rest.split("/", 1)
        path = "/" + path_rest
    else:
        authority = rest
        path = "/"
    if not authority or authority.count(":") > 1:
        return None
    port: str | None = None
    if ":" in authority:
        host, port = authority.rsplit(":", 1)
        if not port.isdigit():
            return None
    else:
        host = authority
    if not host or host.endswith(".") or host.startswith("."):
        return None
    return host.casefold(), port, path


def _html_path(path: str) -> bool:
    if path == "/":
        return True
    return _PATH.fullmatch(path) is not None


def _blocked_prefix(path: str) -> bool:
    for prefix in _BLOCKED_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value or "://" in value:
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


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for pattern in (_TITLE_SUFFIX, _TITLE_PREFIX):
            match = pattern.search(text)
            if match and match.group(0) != text:
                text = (text[: match.start()] + text[match.end() :]).strip()
                changed = True
    return text


def _usable_title(title: str) -> bool:
    if not title or len(title) > MAX_FIELD_CHARS or "<" in title or ">" in title or "://" in title:
        return False
    return title.casefold() not in {"lawzero", "loizéro"}


def _publisher_name(value: str) -> str | None:
    folded = _fold(value)
    if not folded:
        return None
    exact = _PUBLISHER_CANONICAL.get(folded)
    if exact:
        return exact
    for pattern in (_SITE_PREFIX, _SITE_SUFFIX):
        match = pattern.search(folded)
        if match:
            return _PUBLISHER_CANONICAL.get(match.group(1))
    return None


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found.setdefault(key.casefold(), unescape(double or single or bare).strip())
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _jsonld_strings(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    wanted = key.casefold()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for name, value in node.items():
                if str(name).casefold() == wanted:
                    found.extend(_text_values(value))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for blob in _LDJSON.findall(page_html):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        walk(data)
    return found


def _text_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        for key in ("name", "url", "@id"):
            item = value.get(key)
            if isinstance(item, str):
                return [item]
        return []
    if isinstance(value, list):
        found: list[str] = []
        for item in value:
            found.extend(_text_values(item))
        return found
    return []


def _iso_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match and _iso_date(match.group(1)):
        return match.group(1)
    return None


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True
