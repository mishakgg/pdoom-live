"""Metadata catalog of public Meta FAIR research pages on ai.meta.com.

Each stored URL was confirmed with one bounded GET that returned the page
HTML. A row keeps the title, publisher, canonical URL, date, and rights
label. Abstracts, page bodies, PDFs, datasets, and model weights are not
stored. A Cloudflare challenge, a SiteGround captcha, an HTTP 202 challenge,
an Akamai 403, a robots disallow, a non-HTML response, or a redirect
off-host is not stored.

Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means only CC0, CC BY, or CC BY-SA.
``creative_commons_attribution`` means CC BY without NC, ND, or SA.
CC BY-NC, CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA keep their own tokens and
are never folded into those permissive labels. A hyphen is a word boundary,
so CC BY does not match CC BY-NC. Restricted deeds are checked before
permissive ones. When a restricted deed and a permissive deed both appear,
rights stay unknown. Public Domain Mark is not CC0. A copyright notice,
All rights reserved, a terms link, the words Public or Disclosed, and a
company research blog are not licences. ``uk_ogl`` requires the British
phrase "open government licence". ``us_government_work`` requires a rights
field that says the item is a US government work. ``mit``, ``apache-2.0``,
and ``mpl-2.0`` stay their own tokens. MIT or Apache mixed with a permissive
Creative Commons deed stays unknown.

Updated, modified, and copyright years are not publication dates. A page
that does not state a publication date keeps the date unknown. The live URL
is stored as confirmed; a different rel=canonical does not replace it. This
module does not fetch and it is not a belief collector. ``runner_wired``
stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "meta_fair_pages"
CATALOG_FILENAME = "meta_fair_pages.json"
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
OFFICIAL_HOST = "ai.meta.com"
OFFICIAL_ORIGIN = "https://ai.meta.com"
PUBLISHERS = frozenset({"AI at Meta", "Meta AI", "Meta FAIR", "Facebook AI Research"})
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
        "dataset",
        "excerpt",
        "full_text",
        "html",
        "model_card",
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
        "weights",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
)
_RIGHTS_META = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dc.rights",
        "dcterms.rights",
        "dc.rights.license",
    }
)
_SITE_SUFFIXES = (
    " | Research - AI at Meta",
    " - Research - AI at Meta",
    " | Facebook AI Research",
    " - Facebook AI Research",
    " | AI at Meta",
    " - AI at Meta",
    " | Meta AI",
    " - Meta AI",
)
_PUBLISHER_NAMES = (
    "Facebook AI Research",
    "Meta FAIR",
    "AI at Meta",
    "Meta AI",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "attention required",
    "errors.edgesuite.net",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".gz",
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
    ".bin",
    ".pt",
    ".pth",
    ".safetensors",
    ".ckpt",
)
_ROBOTS_PREFIXES = (
    "/ajax/",
    "/tealium/",
    "/intern/",
    "/internal/",
    "/login/",
    "/oidc/callback/",
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
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_MONTH = "|".join(sorted(_MONTHS, key=len, reverse=True))
_LONG_DATE = re.compile(rf"\b({_MONTH})\s+(\d{{1,2}}),\s+(\d{{4}})\b", re.IGNORECASE)
_CARD_CUT = re.compile(r"(?i)listview-card|<h2\b|related publications|related posts")
_SLUG = r"[a-z0-9]+(?:-+[a-z0-9]+)*"
_RESEARCH_PATH = re.compile(
    rf"^(?:/?$|/research/?|/blog/?|/results/?|/resources/?|"
    rf"/resources/(?:demos|frameworks-and-tools)/?|"
    rf"/blog/{_SLUG}/?|/research/publications/{_SLUG}/?)$"
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
# Longer deeds are listed first. (?!-) keeps licenses/by from matching licenses/by-nc
# and keeps CC BY from matching CC BY-NC. A hyphen is a word boundary.
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by(?!-)))"
    r"(?![a-z0-9-])"
)
_TEXT_DEEDS = (
    ("by-nc-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("by-nc-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("by-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?!-)\b")),
    ("by-nc", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?!-)(?![\s-]*(?:sa|nd)\b)")),
    ("by-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?!-)\b")),
    (
        "by",
        re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b)"),
    ),
)
_PROSE_DEEDS = (
    (
        "by-nc-nd",
        re.compile(
            r"(?i)creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*derivatives"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?i)creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "by-nd",
        re.compile(r"(?i)creative commons attribution[\s-]*no[\s-]*derivatives\b"),
    ),
    (
        "by-nc",
        re.compile(
            r"(?i)creative commons attribution[\s-]*non[\s-]*commercial"
            r"(?![\s-]*(?:share[\s-]*alike|no[\s-]*derivatives))"
        ),
    ),
    (
        "by-sa",
        re.compile(r"(?i)creative commons attribution[\s-]*share[\s-]*alike\b"),
    ),
    (
        "by",
        re.compile(
            r"(?i)creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*derivatives|share[\s-]*alike))"
        ),
    ),
)
_CC0 = re.compile(
    r"(?i)(?:(?<![a-z0-9])cc0\b|(?<![a-z0-9])cc[\s-]*0\b|(?<![a-z0-9])cc[\s-]*zero\b|"
    r"creative commons(?:\s+public\s+domain)?[\s-]+zero\b)"
)
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
_MIT = re.compile(
    r"(?i)(?:\bmit licen[cs]e\b|opensource\.org/licenses/mit(?![a-z0-9-])|"
    r"spdx\.org/licenses/mit(?![a-z0-9-]))"
)
_APACHE = re.compile(
    r"(?i)(?:(?<![a-z0-9])apache-2\.0(?![a-z0-9])|"
    r"\bapache[\s-]+2\.0[\s-]+licen[cs]e\b|"
    r"\bapache[\s-]*licen[cs]e(?:\s+version)?[\s-]+2\.0\b|"
    r"apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)"
)
_MPL = re.compile(
    r"(?i)(?:(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|"
    r"mozilla public licen[cs]e(?:\s+version)?\s+2\.0\b|"
    r"mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)"
)
_OGL = re.compile(r"(?i)open government licence(?![a-z])")
_US_GOV = re.compile(r"(?i)\b(?:u\.?\s*s\.?|united states)\s+government\s+work\b")
_RIGHTS_LABEL = re.compile(
    r"(?i)\brights\b\s*[:=]\s*([^<\n.]{0,160})"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Meta FAIR page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
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
    for index, entry in enumerate(entries):
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if index and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _reject_stored_body(entry, path="entry")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    publisher = entry.get("publisher")
    _require_text(publisher, "publisher", MAX_TEXT_CHARS)
    if publisher not in PUBLISHERS:
        raise CatalogError("publisher must be the site name the page states")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")


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
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Meta FAIR page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
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
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or path != path.lower()
        or not _research_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Meta FAIR page: {url}")
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
    lowered = page_html.casefold()
    plain = _plain_text(page_html).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    final_url: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if not _same_official_page(page_url, final_url):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "sg-captcha":
                return False
            if name in {"server", "x-akamai-transformed"} and "akamai" in token and status != 200:
                return False
    return True


def record_from_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    final_url: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict | None:
    """Return metadata when the bounded GET returned the page HTML.

    HTTP 202, HTTP 403, a challenge body, a non-HTML type, or a final host
    other than ai.meta.com is not stored. A page without a title is omitted.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        final_url=final_url,
        headers=headers,
    ):
        return None
    assert isinstance(page_html, str)
    stored_url = page_url
    if final_url:
        try:
            stored_url = validate_canonical_url(final_url)
        except CatalogError:
            stored_url = page_url
    try:
        return page_record(page_html, page_url=stored_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons`` is CC0, CC BY, or CC BY-SA, and only when no
    restricted deed is also stated. ``creative_commons_attribution`` is CC BY
    alone. A by-nc URL is not ``creative_commons``, even when the anchor text
    says CC BY. Public Domain Mark, All rights reserved, a public page, and a
    company research blog stay unknown. Script and style text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _HIDDEN.sub(" ", page_text)
    plain = _plain_text(visible).casefold().translate(_DASHES)
    codes = _cc_codes(visible, plain)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    mit = bool(_MIT.search(plain) or _MIT.search(visible))
    apache = bool(_APACHE.search(plain) or _APACHE.search(visible))
    mpl = bool(_MPL.search(plain) or _MPL.search(visible))
    software = sum((mit, apache, mpl))
    ogl = _OGL.search(plain) is not None
    us_gov = _states_us_government_work(visible)
    if restricted and permissive:
        return RIGHTS_UNKNOWN
    if permissive and (mit or apache or mpl):
        return RIGHTS_UNKNOWN
    if restricted and (software or ogl or us_gov):
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if permissive and (software or ogl or us_gov):
        return RIGHTS_UNKNOWN
    if software > 1 or (software and (ogl or us_gov)):
        return RIGHTS_UNKNOWN
    if ogl and us_gov:
        return RIGHTS_UNKNOWN
    if permissive:
        if permissive == {"by"}:
            return RIGHTS_CC_BY
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
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, and a date on a related card are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_prefix(metas.get(key))
        if parsed:
            return parsed
    heading = _H1.search(visible)
    if heading is None:
        return UNKNOWN_DATE
    window = visible[heading.end() : heading.end() + 800]
    cut = _CARD_CUT.search(window)
    if cut:
        window = window[: cut.start()]
    plain = _plain_text(window)
    found = _LONG_DATE.search(plain)
    if found is None:
        return UNKNOWN_DATE
    prefix = plain[: found.start()].casefold()
    if len(prefix) > 40:
        return UNKNOWN_DATE
    if any(word in prefix for word in ("updat", "modif", "copyright", "©")):
        return UNKNOWN_DATE
    return _calendar_date(found.group(1), found.group(2), found.group(3))


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
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return the site name the page states.

    The paper venue and a person named on the page are not the publisher.
    The name is not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    site = _clean_text(metas.get("og:site_name", ""))
    if site in PUBLISHERS:
        return site
    title_tag = _TITLE.search(visible)
    raw_title = _plain_text(title_tag.group(1)) if title_tag else ""
    blob = f"{raw_title} {_clean_text(metas.get('og:title', ''))}"
    for name in _PUBLISHER_NAMES:
        if name in blob:
            return name
    plain = _plain_text(visible)
    for name in _PUBLISHER_NAMES:
        if name in plain:
            return name
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
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _research_path(path: str) -> bool:
    if path.endswith(_DOWNLOAD_SUFFIXES) or path.endswith(".php"):
        return False
    lowered = path.lower()
    if lowered.startswith(_ROBOTS_PREFIXES) or lowered.startswith("/datasets/"):
        return False
    if "/tools/system-cards" in lowered:
        return False
    return _RESEARCH_PATH.fullmatch(path) is not None


def _same_official_page(page_url: str, final_url: str | None) -> bool:
    try:
        validate_canonical_url(page_url)
    except CatalogError:
        return False
    if not final_url:
        return True
    final = urlparse(final_url)
    host = (final.hostname or "").lower().rstrip(".")
    if host != OFFICIAL_HOST or hostname_is_blocked(host):
        return False
    if final.scheme != "https":
        return False
    return True


def _cc_codes(visible_html: str, plain: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(visible_html):
        if match.group("pd"):
            kind = match.group("pd").lower()
            if kind == "zero":
                codes.add("zero")
            continue
        code = (match.group("code") or "").lower()
        if code:
            codes.add(code)
    folded = plain.translate(_DASHES)
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(code)
    for code, pattern in _PROSE_DEEDS:
        if pattern.search(folded):
            codes.add(code)
    if _CC0.search(folded):
        codes.add("zero")
    return codes


def _states_us_government_work(visible_html: str) -> bool:
    metas = _metas(visible_html)
    for key in _RIGHTS_META:
        raw = metas.get(key, "")
        if raw and _US_GOV.search(raw):
            return True
    plain = _plain_text(visible_html)
    for match in _RIGHTS_LABEL.finditer(plain):
        if _US_GOV.search(match.group(1)):
            return True
    return False


def _iso_prefix(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _DATE_PREFIX.match(value.strip())
    if match is None:
        return None
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
    except ValueError:
        return None
    return match.group(1)


def _calendar_date(month: str, day: str, year: str) -> str:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return UNKNOWN_DATE
    try:
        parsed = date(int(year), month_number, int(day))
    except ValueError:
        return UNKNOWN_DATE
    return parsed.isoformat()


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _reject_stored_body(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        found = _FORBIDDEN_KEYS.intersection(value)
        if found:
            names = ", ".join(sorted(found))
            raise CatalogError(f"{path} must not store page text ({names})")
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                _reject_stored_body(item, path=path)


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length:
        raise CatalogError(f"{field} is too long to store")


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    changed = True
    while changed and text:
        changed = False
        folded = text.casefold()
        for suffix in _SITE_SUFFIXES:
            if folded.endswith(suffix.casefold()) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
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


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs
