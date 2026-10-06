"""Metadata catalog of public MATS Program pages.

Each stored URL was confirmed with one bounded GET on www.matsprogram.org.
A row keeps the title, publisher, canonical URL, date, and rights label.
Page bodies, abstracts, PDFs, and chart data are not stored. A Cloudflare
challenge, a SiteGround captcha, an HTTP 202, an Akamai 403, a robots
disallow, or a redirect off www.matsprogram.org is not stored. Stanford SERI
and any other host are not catalogued. Rights stay unknown unless the page
states a reuse licence. ``creative_commons`` means CC0, CC BY, or CC BY-SA.
``creative_commons_attribution`` means CC BY without NC, ND, or SA. A hyphen
is a word boundary, so CC BY does not match CC BY-NC. Restricted deeds are
not folded into those labels. A missing date stays unknown. Updated,
modified, and copyright years are not publication dates. The live URL is
stored as confirmed; a different rel=canonical does not replace it. This
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

CATALOG_ID = "mats_pages"
CATALOG_FILENAME = "mats_pages.json"
CATALOG_DESCRIPTION = (
    "Metadata for confirmed public MATS Program pages on www.matsprogram.org. "
    "Person profiles, mentor streams, job posts, and individual research "
    "records are not rows. Each URL was confirmed by one bounded GET of HTML. "
    "Cloudflare, SiteGround captcha, HTTP 202, Akamai 403, a "
    "robots disallow, or a redirect off-host stores no row. Stanford SERI and "
    "other hosts are omitted. Rows keep a title, publisher, canonical URL, "
    "date, and rights. Bodies, abstracts, and PDFs are omitted. Rights stay "
    "unknown unless the page states a reuse licence. creative_commons is CC0, "
    "CC BY, or CC BY-SA. creative_commons_attribution is CC BY without NC, ND, "
    "or SA. A missing date stays unknown. Updated, modified, and copyright "
    "years are not publication dates. This catalog is not a belief collector "
    "and runner_wired is false."
)
RUNNER_WIRED = False
PUBLISHER = "MATS Program"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
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
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
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
OFFICIAL_HOST = "www.matsprogram.org"
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
        "text",
        "transcript",
        "transcript_text",
    }
)
_LICENSE_META = frozenset({"license", "licence", "dcterms.license", "dc.rights", "dcterms.rights"})
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = ("article:published_time", "citation_publication_date", "dcterms.created")
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PAGE_URL = re.compile(
    r"^https://www\.matsprogram\.org"
    r"(?P<path>/(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*)?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"((?:\\.|[^"\\])*)"')
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"((?:\\.|[^"\\])*)"')
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_TYPE = re.compile(r'"@type"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_HREF = re.compile(r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " | MATS Program",
    " | MATS Research",
    " - MATS Program",
    " - MATS Research",
    " – MATS Program",
    " – MATS Research",
    " — MATS Program",
    " — MATS Research",
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
_OGL_DASHES = str.maketrans(
    {
        "\u00a0": " ",
        "\u2010": " ",
        "\u2011": " ",
        "\u2012": " ",
        "\u2013": " ",
        "\u2014": " ",
        "\u2212": " ",
    }
)
# Longer deeds are listed first. `(?!-)` makes a hyphen a word boundary, so
# licenses/by and CC BY do not match licenses/by-nc or CC BY-NC.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-))"
    r"(?![a-z0-9-])"
)
_TEXT_DEEDS = (
    ("cc-by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("cc-by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("cc-by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)")),
    ("cc-by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd\b")),
    ("cc-by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa\b")),
    (
        "cc-by-nc-nd",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv"),
    ),
    (
        "cc-by-sa",
        re.compile(r"creative commons attribution[\s-]+share[\s-]*alike"),
    ),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    (
        "cc0",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero\b"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
            r"|creative commons public domain dedication(?![\s-]*mark)"
        ),
    ),
    (
        "cc-by",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![\s-]*(?:nc|nd|sa)\b)"),
    ),
)
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_SOFTWARE = frozenset({RIGHTS_MIT, RIGHTS_APACHE, RIGHTS_MPL})
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
    r"|\bapache licen[cs]e(?:\s*2\.0)?\b"
    r"|apache\.org/licenses/license-2\.0(?![a-z0-9-])"
    r"|spdx\.org/licenses/apache-2\.0(?![a-z0-9-])"
)
_MPL = re.compile(
    r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])"
    r"|\bmpl\s*2\.0\b"
    r"|\bmozilla public licen[cs]e\s*2\.0\b"
)
_OGL_PHRASE = "open government licence"
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the MATS Program page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for www.matsprogram.org."""
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
    """Return metadata when the response is the confirmed page HTML."""
    target = final_url or page_url
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=target,
    ):
        return None
    if robots_txt is not None and not robots_path_allowed(target, robots_txt):
        return None
    if not _on_official_host(target):
        return None
    assert isinstance(page_html, str)
    return metadata_from_page(page_html, page_url=target)


def robots_path_allowed(url: str, robots_txt: str | None = None) -> bool:
    """A missing robots document does not block. A disallow blocks the path."""
    if robots_txt is None:
        return _on_official_host(url)
    if not _on_official_host(url):
        return False
    path = _PAGE_URL.fullmatch(url)
    target = "/" if path is None or not path.group("path") else path.group("path")
    return robots_allows(robots_txt, target)


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    Restricted deeds are checked before permissive ones. A hyphen is a word
    boundary, so CC BY-NC is not CC BY and licenses/by is not licenses/by-nc.
    A restricted deed beside a permissive deed stays unknown. Sole CC BY-NC,
    CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA keep their own tokens.
    ``creative_commons_attribution`` is CC BY without NC, ND, or SA.
    ``creative_commons`` is CC0 or CC BY-SA, and also CC BY when a broader
    permissive deed is stated with it. Public Domain Mark is not CC0. A
    generic creativecommons.org/licenses/ URL, a copyright notice, All rights
    reserved, a terms link, and the words Public or Disclosed are not
    licences. ``uk_ogl`` requires the British phrase "open government
    licence". ``us_government_work`` requires a rights field that says the
    item is a US government work. MIT, Apache-2.0, and MPL-2.0 stay their
    own tokens. MIT or Apache beside a permissive CC deed stays unknown.
    """
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl, gov = _rights_signals(page_text)
    restricted = cc_codes & _RESTRICTED
    permissive = cc_codes & _PERMISSIVE
    families = [
        family
        for family in (
            restricted,
            permissive,
            software,
            {"uk_ogl"} if ogl else set(),
            {"us_government_work"} if gov else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive & {"cc0", "cc-by-sa"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-published comment, and a
    copyright year are not publication dates.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for blob in _LDJSON.findall(page_html):
        if not _LD_TYPE.search(blob):
            continue
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
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
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
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return MATS Program when the page names that site.

    A person named on the page is not the publisher. Stanford SERI is not
    the publisher. The name is not invented when the page does not state it.
    """
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    for blob in _LDJSON.findall(page_html):
        if '"website"' in blob.casefold() and f'"name" : "{PUBLISHER}"' in blob:
            return PUBLISHER
        if re.search(rf'"name"\s*:\s*"{re.escape(PUBLISHER)}"', blob):
            folded = blob.casefold()
            if '"@type"' in folded and "website" in folded:
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
        raise CatalogError(f"canonical URL must be a public www.matsprogram.org page: {url}")
    parsed_host = OFFICIAL_HOST
    path = url[len("https://" + OFFICIAL_HOST) :]
    if (
        not is_official_host(parsed_host)
        or hostname_is_blocked(parsed_host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or path.lower().endswith(_DOWNLOAD_SUFFIXES)
    ):
        raise CatalogError(f"canonical URL must be a public www.matsprogram.org page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    cc_codes: set[str] = set()
    software: set[str] = set()
    gov = False
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            cc_codes |= _cc_codes(raw)
            software |= _software_codes(raw)
        for raw in _LD_RIGHTS.findall(blob):
            if _states_us_government_work(raw):
                gov = True
            cc_codes |= _cc_codes(raw)
            software |= _software_codes(raw)
    visible = _visible(page_text)
    for key, value in _metas(visible).items():
        if key in _LICENSE_META or key in _RIGHTS_META:
            cc_codes |= _cc_codes(value)
            software |= _software_codes(value)
        if key in _RIGHTS_META and _states_us_government_work(value):
            gov = True
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(visible):
        if not _is_rights_element(attrs):
            continue
        text = _plain(body)
        if text and len(text) <= MAX_FIELD_CHARS and _states_us_government_work(text):
            gov = True
    folded_visible = _fold(_plain(visible))
    cc_codes |= _cc_codes(folded_visible)
    software |= _software_codes(folded_visible)
    for href in _hrefs(visible):
        cc_codes |= _cc_codes(href)
        software |= _software_codes(href)
    ogl = _OGL_PHRASE in _plain(visible).casefold().translate(_OGL_DASHES)
    return cc_codes, software, ogl, gov


def _cc_codes(value: str) -> set[str]:
    folded = _fold(unescape(value).replace("\\/", "/"))
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("code")
        if code:
            codes.add(f"cc-{code}" if not code.startswith("cc-") else code)
            if code in {"by", "by-sa", "by-nc", "by-nd", "by-nc-sa", "by-nc-nd"}:
                codes.add(f"cc-{code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _software_codes(value: str) -> set[str]:
    folded = _fold(unescape(value).replace("\\/", "/"))
    found: set[str] = set()
    if _MIT.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _fold(value))
    return _GOV_WORK.search(text) is not None


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
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ").translate(_DASHES)
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


def _hrefs(page_html: str) -> list[str]:
    hrefs: list[str] = []
    for match in _HREF.finditer(page_html):
        href = unescape(match.group(1) or match.group(2) or match.group(3) or "").strip()
        if href:
            hrefs.append(href)
    return hrefs


def _is_rights_element(attrs: str) -> bool:
    parsed = _attrs(f"<x {attrs}>")
    if parsed.get("itemprop", "").casefold() == "rights":
        return True
    for key in ("id", "class"):
        raw = parsed.get(key, "").replace("-", " ").replace("_", " ")
        if any(token.casefold() == "rights" for token in raw.split()):
            return True
    return False
