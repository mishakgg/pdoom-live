"""Metadata catalog of public Data & Society pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, quotes, and chart data are not stored. A missing date
stays unknown. Updated, modified, and copyright years are not publication
dates. creative_commons is only CC0, CC BY-SA, or a mix of those.
creative_commons_attribution is CC BY alone. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps cc_by_nc, cc_by_nd, cc_by_nc_sa, or
cc_by_nc_nd. A generic creativecommons.org/licenses/ URL is not a deed, and
anchor text on that path does not count. A public-domain mark is not CC0.
A software licence beside a Creative Commons deed stays unknown. A photo,
caption, or image credit does not set the page licence. uk_ogl is only the
British phrase Open Government Licence. us_government_work is only an
explicit rights field. Script, style, and comment text does not count. This
module does not fetch. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "datasociety_pages"
CATALOG_FILENAME = "datasociety_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
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
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
OFFICIAL_HOST = "datasociety.net"
PUBLISHER = "Data & Society"
MAX_FIELD_CHARS = 500
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
_DATE_PREFIX = re.compile(r"^(\d{4})[-/](\d{2})[-/](\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_ANCHOR_FULL = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_CREDIT_PHRASE = re.compile(
    r"(?i)\b(?:photo|caption|image)\s+credit\b"
    r"|\billustration\s*:"
    r"|\billustration by\b"
    r"|\bheader image\b"
    r"|\bimage from\b"
    r"|\bimage\s*:"
    r"|\d(?:\.\d)?\s*-licen[cs]ed\b"
)
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_GOV_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META = frozenset(
    {
        "license",
        "licence",
        "dc.license",
        "dcterms.license",
        "rights",
        "dc.rights",
        "dcterms.rights",
    }
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "citation_date",
    "dcterms.issued",
    "dcterms.created",
    "dc.date",
    "dc.date.issued",
)
_RIGHTS_DD = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_SITE_SUFFIXES = (
    " | Data & Society",
    " - Data & Society",
    " – Data & Society",
    " — Data & Society",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_TITLE_CHALLENGES = (
    "just a moment",
    "attention required",
    "access denied",
    "are you a robot",
    "verify you are human",
    "please wait while your request is being verified",
    "robot check",
    "checking your browser",
)
_RAW_CHALLENGES = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "sg-captcha",
    "sgcaptcha",
    "errors.edgesuite.net",
    "akamai-ghost",
)
_BLOCKED_PREFIXES = (
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
    "/xmlrpc.php",
    "/cgi-bin",
    "/cdn-cgi",
    "/feed",
    "/es",
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
    ".gz",
    ".tgz",
    ".tar",
)
# Longer deeds are listed first. A hyphen is a word boundary, so CC BY must
# not match CC BY-NC. licenses/by does not match licenses/by-nc. A bare
# licenses/ path is not a deed.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![a-z0-9-])"
)
_TEXT_CODES = (
    ("by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("by-nc-sa", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b(?![\s-]*(?:sa|nd)\b)")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*non[\s-]*commercial\b")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*no[\s-]*deriv")),
    ("by-sa", re.compile(r"\bcc[\s-]*by[\s-]*sa\b(?![\s-]*(?:nc|nd)\b)")),
    (
        "zero",
        re.compile(
            r"\bcc0\b|\bcc[\s-]*0\b|\bcc[\s-]*zero\b|"
            r"\bcreative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    (
        "by",
        re.compile(
            r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)"
            r"(?![\s-]*(?:non[\s-]*commercial\b|no[\s-]*deriv))"
        ),
    ),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    ),
    (
        "by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial\b"
            r"(?![\s-]*(?:share[\s-]*alike|no[\s-]*deriv))"
        ),
    ),
    ("by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike\b")),
    (
        "by",
        re.compile(
            r"creative commons attribution\b"
            r"(?![\s-]*(?:non[\s-]*commercial\b|no[\s-]*deriv|share[\s-]*alike\b|nc\b|nd\b|sa\b))"
        ),
    ),
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_DEED_CODES = _PERMISSIVE | _RESTRICTED
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
}
_MIT_PHRASE = re.compile(r"\bmit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE_PHRASE = re.compile(r"\bapache-2\.0\b|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b")
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL_PHRASE = re.compile(r"\bmpl-2\.0\b|\bmozilla public license(?:\s*,?\s*version)?\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_OGL_PHRASE = re.compile(r"\bopen government licence\b")
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Data & Society page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_datasociety_host(hostname: str) -> bool:
    """True only for the official datasociety.net host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    head = page_html[:15000].casefold()
    title = ""
    match = _TITLE.search(head)
    if match:
        title = _clean_text(match.group(1)).casefold()
    if any(marker in title for marker in _TITLE_CHALLENGES):
        return True
    return any(marker in head for marker in _RAW_CHALLENGES)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML on datasociety.net that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html) or _challenge_headers(headers):
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
    """Return metadata when one response is the page HTML.

    HTTP 202, a non-HTML body, a challenge interstitial, and a URL that is not
    on datasociety.net are not stored.
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
    """Return a rights label from a reuse licence the page itself states.

    creative_commons is CC0, CC BY-SA, or a mix of those. CC BY alone is
    creative_commons_attribution. A sole restricted deed keeps cc_by_nc,
    cc_by_nd, cc_by_nc_sa, or cc_by_nc_nd. Two restricted deeds, a restricted
    deed beside a permissive one, and a software licence beside any Creative
    Commons deed stay unknown. A generic licenses/ URL is not a deed, and
    anchor text on that path or on a public-domain mark URL does not count.
    A photo, caption, or image credit does not set the page licence. uk_ogl
    is only the British phrase Open Government Licence. us_government_work
    is only an explicit rights field. Script, style, and comment text does
    not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes, mit, apache, mpl = _licence_signals(page_text)
    government = _states_us_government_work(page_text)
    ogl = _states_open_government_licence(page_text)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    software = (mit, apache, mpl)
    if (restricted or permissive) and any(software):
        return RIGHTS_UNKNOWN
    if sum(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) > 1 or (restricted and permissive):
        return RIGHTS_UNKNOWN
    if len(restricted) == 1 and (ogl or government):
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if permissive and (ogl or government):
        return RIGHTS_UNKNOWN
    if permissive <= {"zero", "by-sa"} and permissive:
        return RIGHTS_CREATIVE_COMMONS
    if permissive == {"by"}:
        return RIGHTS_CC_ATTRIBUTION
    if permissive:
        return RIGHTS_UNKNOWN
    if ogl and government:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if government:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years do not count."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for match in _DATE_PUBLISHED.finditer(blob):
            if _iso_date(match.group(1)):
                return match.group(1)
    metas = _metas(page_text)
    for key in _PUBLICATION_DATE_KEYS:
        found = _normalize_date(metas.get(key, ""))
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    for match in _H1.finditer(visible):
        title = _clean_title(match.group(1))
        if _usable_title(title):
            return title
    metas = _metas(visible)
    for key in ("citation_title", "og:title", "dcterms.title"):
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
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_without_hidden(page_html))
    for key in ("og:site_name", "citation_publisher"):
        if _clean_text(metas.get(key, "")) == PUBLISHER:
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the URL
    that returned HTML. A rel=canonical on another path is not substituted.
    A challenge page is not stored.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    return page_record(page_html, page_url=page_url)


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_absolute_https(live, href))
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
    if document["catalog_id"] != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document["description"]
    if not isinstance(description, str) or not description.strip():
        raise CatalogError("description is required")
    if description != description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if "p(doom)" in description.casefold():
        raise CatalogError("description must not store a p(doom) figure")
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
    if "p(doom)" in entry["title"].casefold():
        raise CatalogError("title must not store a p(doom) figure")
    return entry


def validate_canonical_url(url: object) -> str:
    parsed = _parse_https_url(url)
    if parsed is None:
        raise CatalogError("canonical URL must be an https datasociety.net page")
    host, path = parsed
    if not official_datasociety_host(host) or not _html_path(path):
        raise CatalogError(f"canonical URL must be an https datasociety.net page: {url}")
    return str(url)


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _parse_https_url(url: object) -> tuple[str, str] | None:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        return None
    if not url.startswith("https://"):
        return None
    rest = url[len("https://") :]
    if not rest or any(char in rest for char in ("@", "?", "#")):
        return None
    slash = rest.find("/")
    if slash == -1:
        host, path = rest, "/"
    else:
        host, path = rest[:slash], rest[slash:]
    if not host or ":" in host:
        return None
    hostname = host.lower().rstrip(".")
    if not hostname or ".." in hostname:
        return None
    return hostname, path


def _html_path(path: str) -> bool:
    if not path.startswith("/") or ".." in path or "\\" in path or "//" in path or "%" in path:
        return False
    bare = path[:-1] if path != "/" and path.endswith("/") else path
    lowered = bare.casefold()
    if lowered in {"", "/"}:
        return False
    if lowered.endswith(_DOWNLOAD_SUFFIXES) or lowered.endswith("/feed"):
        return False
    for prefix in _BLOCKED_PREFIXES:
        if lowered == prefix or lowered.startswith(prefix + "/"):
            return False
    return True


def _absolute_https(base: str, href: str) -> str:
    value = unescape(href).strip()
    if value.startswith("https://") or value.startswith("http://"):
        return value
    parsed = _parse_https_url(base)
    if parsed is None:
        return value
    host, path = parsed
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("/"):
        return f"https://{host}{value}"
    parent = path.rsplit("/", 1)[0]
    return f"https://{host}{parent}/{value}"


def _same_page(left: str, right: str) -> bool:
    a = _parse_https_url(left)
    b = _parse_https_url(right)
    if a is None or b is None:
        return False
    return a[0] == b[0] and a[1].rstrip("/") == b[1].rstrip("/")


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


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
            return True
    return False


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.casefold().endswith(suffix.casefold()):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() != PUBLISHER.casefold()


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found[key.casefold()] = unescape(double or single or bare).strip()
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
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _licence_signals(page_html: str) -> tuple[set[str], bool, bool, bool]:
    prepared = _prepare_licence_html(page_html)
    folded = _fold(prepared)
    codes = _cc_codes(folded)
    mit, apache, mpl = _software_flags(folded)
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for name in _LICENSE_META:
        if not metas.get(name):
            continue
        value = _fold(metas[name])
        kind = _cc_href_kind(metas[name])
        if kind in _DEED_CODES:
            codes.add(kind)
        elif kind not in {"generic", "mark"}:
            codes.update(_cc_codes(value))
        mit, apache, mpl = _merge_software((mit, apache, mpl), _software_flags(value))
    return codes, mit, apache, mpl


def _prepare_licence_html(page_html: str) -> str:
    """Drop hidden text, credits, generic licence URLs, and public-domain marks."""

    visible = _blank_credits(_without_hidden(page_html))

    def replace_anchor(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        kind = _cc_href_kind(href)
        if kind in {"generic", "mark"}:
            return " "
        return match.group(0)

    return _ANCHOR_FULL.sub(replace_anchor, visible)


def _blank_credits(html: str) -> str:
    """Ignore photo, caption, and image credits. They are not the page licence."""

    blanked = re.sub(
        r"(?is)<(p|figcaption|span|li|cite|figure|h6|i|em)\b[^>]*\b(?:caption|photo-credit|image-credit|wp-caption)\b[^>]*>.*?</\1>",
        " ",
        html,
    )

    def blank_phrase(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(_plain(match.group(0))):
            return " "
        return match.group(0)

    blanked = re.sub(
        r"(?is)<(p|figcaption|li|cite|figure|h6|i|em)\b[^>]*>.*?</\1>",
        blank_phrase,
        blanked,
    )
    return re.sub(
        r"(?is)\b(?:photo|caption|image)\s+credit\b[^<.]{0,300}",
        " ",
        blanked,
    )


def _cc_href_kind(href: str) -> str | None:
    """Classify one Creative Commons URL. A bare licenses/ path is generic."""

    raw = unescape(href).strip().replace("\\/", "/")
    raw = raw.split("#", 1)[0]
    path_part = raw.partition("?")[0].strip()
    match = re.match(
        r"(?i)^(?:https?:)?//(?:www\.)?creativecommons\.org(?P<path>/[^?#]*)?$",
        path_part,
    )
    if match is None:
        return None
    parts = [part.casefold() for part in (match.group("path") or "/").split("/") if part]
    if not parts:
        return None
    if parts[0] == "licenses":
        if len(parts) == 1:
            return "generic"
        code = parts[1]
        if code in _DEED_CODES:
            return code
        return "generic"
    if parts[0] == "publicdomain" and len(parts) > 1:
        if parts[1] == "zero":
            return "zero"
        if parts[1] == "mark":
            return "mark"
    return None


def _cc_codes(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            codes.add(license_code.casefold())
            continue
        public_domain = (match.group("pd") or "").casefold()
        if public_domain == "zero":
            codes.add("zero")
        elif public_domain == "mark":
            codes.add("mark")
    for code, pattern in _TEXT_CODES:
        if pattern.search(folded):
            codes.add(code)
    codes.discard("mark")
    return codes


def _software_flags(folded: str) -> tuple[bool, bool, bool]:
    return (
        bool(_MIT_PHRASE.search(folded) or _MIT_URL.search(folded)),
        bool(_APACHE_PHRASE.search(folded) or _APACHE_URL.search(folded)),
        bool(_MPL_PHRASE.search(folded) or _MPL_URL.search(folded)),
    )


def _merge_software(
    left: tuple[bool, bool, bool], right: tuple[bool, bool, bool]
) -> tuple[bool, bool, bool]:
    return (left[0] or right[0], left[1] or right[1], left[2] or right[2])


def _states_open_government_licence(page_html: str) -> bool:
    prepared = _fold(_prepare_licence_html(page_html))
    return _OGL_PHRASE.search(prepared) is not None


def _states_us_government_work(page_html: str) -> bool:
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    fields = [metas[name] for name in _GOV_META if metas.get(name)]
    fields.extend(_plain(block) for block in _RIGHTS_DD.findall(visible))
    for field in fields:
        text = _fold(field)
        if _NEGATED_GOV_WORK.search(text):
            continue
        if _GOV_WORK.search(text):
            return True
    return False


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ")
    for src in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        text = text.replace(src, "-")
    return re.sub(r"\s+", " ", text).casefold()


def _normalize_date(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    found = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    if _iso_date(found):
        return found
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
