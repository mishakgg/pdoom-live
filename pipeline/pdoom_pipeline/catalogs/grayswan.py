"""Metadata catalog of public Gray Swan AI pages.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text is not stored.
A Cloudflare challenge, a captcha interstitial, an HTTP 202, an Akamai 403,
a non-HTML response, a robots disallow, or an off-host redirect is not stored.
``creative_commons`` means only a stated CC0, CC BY, or CC BY-SA deed.
CC BY-NC, CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA are their own tokens and are
never folded into ``creative_commons``. A restricted deed wins when a
permissive deed is also stated. A hyphen is a word boundary, so CC BY must
not match CC BY-NC, and licenses/by must not match licenses/by-nc. A generic
creativecommons.org/licenses/ URL is not a permissive deed. The Public Domain
Mark is not CC0. Anchor text that says CC0 or CC BY on a public-domain mark
or by-nc URL does not reclassify that URL. A copyright notice, All rights
reserved, a terms link, and a host name are not licences. ``mit`` and
``apache-2.0`` are their own tokens. A page that does not state a publication
date keeps the date unknown. Updated, modified, last updated, and copyright
years are not publication dates. The live URL is stored as confirmed; a
different rel=canonical does not replace it. This module does not fetch and
it is not a belief collector. runner_wired stays false.
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

CATALOG_ID = "grayswan_pages"
CATALOG_FILENAME = "grayswan_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Gray Swan AI"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_UNKNOWN,
    }
)
UNKNOWN_DATE = "unknown"
GRAYSWAN_HOST = "www.grayswan.ai"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
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
_LICENSE_META_KEYS = frozenset(
    {
        "license",
        "licence",
        "dcterms.license",
        "dcterms.licence",
        "dc.rights",
        "dcterms.rights",
    }
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title", "twitter:title")
_SITE_SUFFIXES = (
    " | Gray Swan News",
    " | Gray Swan Research",
    " | Gray Swan AI",
    " | Gray Swan",
    " - Gray Swan News",
    " - Gray Swan Research",
    " - Gray Swan AI",
    " – Gray Swan",
    " — Gray Swan",
    " - Gray Swan",
)
_GENERIC_TITLES = frozenset(
    {
        "gray swan",
        "gray swan ai",
        "gray swan news",
        "gray swan research",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "errors.edgesuite.net",
    "akamaighost",
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
    ".svg",
)
_BLOCKED_PREFIXES = (
    "/wp-admin",
    "/wp-content",
    "/wp-includes",
    "/wp-json",
    "/.well-known",
    "/cdn-cgi",
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
# Longer deeds are listed first. A hyphen is a word boundary in \b, so the CC BY
# pattern refuses a following hyphen or token. licenses/by is not licenses/by-nc.
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<lic>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_TEXT_DEEDS = (
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nc[-\s]?nd(?![a-z0-9])")),
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nc[-\s]?sa(?![a-z0-9])")),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[-\s]?by[-\s]?sa(?![a-z0-9-])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[-\s]?by(?![a-z0-9-])")),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[-\s]+non[-\s]?commercial[-\s]+no[-\s]?deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"creative commons attribution[-\s]+non[-\s]?commercial[-\s]+share[-\s]?alike"),
    ),
    ("by-nc", re.compile(r"creative commons attribution[-\s]+non[-\s]?commercial")),
    ("by-nd", re.compile(r"creative commons attribution[-\s]+no[-\s]?deriv")),
    ("by-sa", re.compile(r"creative commons attribution[-\s]+share[-\s]?alike")),
    (
        "by",
        re.compile(
            r"creative commons attribution(?![-\s]+(?:non[-\s]?commercial|no[-\s]?deriv|share[-\s]?alike))"
        ),
    ),
    (
        "zero",
        re.compile(
            r"(?<![a-z0-9])(?:cc[-\s]?0|cc[-\s]?zero)(?![a-z0-9])"
            r"|creative commons(?: public domain)? zero(?![a-z])"
        ),
    ),
)
_RESTRICTED_PRIORITY = (
    ("by-nc-nd", RIGHTS_CC_BY_NC_ND),
    ("by-nc-sa", RIGHTS_CC_BY_NC_SA),
    ("by-nc", RIGHTS_CC_BY_NC),
    ("by-nd", RIGHTS_CC_BY_ND),
)
_PERMISSIVE = frozenset({"zero", "by", "by-sa"})
_MIT = re.compile(
    r"(?i)\bmit\s+licen[cs]e\b|\blicen[cs]ed under (?:the )?mit(?:\s+licen[cs]e)?\b"
)
_APACHE = re.compile(
    r"(?i)\bapache-2\.0\b"
    r"|\bapache\s+licen[cs]e(?:\s*,?\s*version)?\s*2(?:\.0)?\b"
    r"|\blicen[cs]ed under (?:the )?apache(?:\s+licen[cs]e)?(?:\s*,?\s*version)?\s*2(?:\.0)?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Gray Swan AI page rules."""


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
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must stay false")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    previous = ""
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        if previous and url < previous:
            raise CatalogError("entries must be ordered by canonical URL")
        seen.add(url)
        previous = url


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be a known token or unknown")


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
        raise CatalogError("canonical URL must be a public Gray Swan AI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != GRAYSWAN_HOST
        or host != GRAYSWAN_HOST
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
        or not _public_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Gray Swan AI page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == GRAYSWAN_HOST and not hostname_is_blocked(host)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    plain = _plain_text(page_html).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def robots_disallows(robots_txt: str, path: str) -> bool:
    """True when robots.txt disallows path, or the body is not a robots file.

    A Cloudflare challenge, a captcha page, or an HTML document is not a grant
    of permission. A file that only names a sitemap allows the public paths.
    """

    if not isinstance(robots_txt, str):
        return True
    if is_challenge_page(robots_txt):
        return True
    sample = robots_txt.lstrip()[:400].casefold()
    if sample.startswith("<!doctype") or sample.startswith("<html") or "<html" in sample:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    groups = _robots_groups(robots_txt)
    if not groups:
        return False
    rules = _wildcard_rules(groups)
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if prefix and target.startswith(prefix):
            if kind == "allow":
                allowed = max(allowed, len(prefix))
            else:
                disallowed = max(disallowed, len(prefix))
    return disallowed > allowed


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or a non-200 status.

    HTTP 202 and HTTP 403, including an Akamai 403, are not stored.
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
            if name == "sg-captcha" and "challenge" in token:
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
    robots_txt: str | None = None,
) -> dict | None:
    """Return metadata when the response is the confirmed page HTML.

    A challenge page, an HTTP 202, an Akamai 403, a robots disallow, an
    off-host redirect, or a non-HTML response is not stored.
    """

    if not isinstance(page_url, str):
        return None
    path = urlparse(page_url).path or "/"
    if robots_txt is not None and robots_disallows(robots_txt, path):
        return None
    landed = final_url if final_url is not None else page_url
    if not isinstance(landed, str):
        return None
    landed_host = (urlparse(landed).hostname or "").lower().rstrip(".")
    if landed_host != GRAYSWAN_HOST or hostname_is_blocked(landed_host):
        return None
    if final_url is not None and not _same_page(final_url, page_url):
        return None
    try:
        validate_canonical_url(page_url)
    except CatalogError:
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
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

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only. CC BY-NC,
    CC BY-ND, CC BY-NC-ND, and CC BY-NC-SA keep their own tokens. A restricted
    deed wins when a permissive deed is also stated. A hyphen is a word
    boundary, so CC BY does not match CC BY-NC and licenses/by does not match
    licenses/by-nc. A generic creativecommons.org/licenses/ URL is not a
    permissive deed. The Public Domain Mark is not CC0. Anchor text on a
    public-domain mark or by-nc URL does not reclassify that URL. A copyright
    notice, All rights reserved, a terms link, and a host name are not
    licences. ``mit`` and ``apache-2.0`` are their own tokens. Script and
    style text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _HIDDEN.sub(" ", page_text)
    codes: set[str] = set()
    for content in _meta_values(visible, _LICENSE_META_KEYS):
        codes.update(_url_codes(content))
        codes.update(_text_codes(content))
    for tag in _LINK.findall(visible):
        codes.update(_url_codes(_attrs(tag).get("href", "")))
    reduced, anchor_codes = _take_creativecommons_anchors(visible)
    codes.update(anchor_codes)
    plain = _plain_text(reduced).casefold().translate(_DASHES)
    codes.update(_text_codes(plain))
    codes.update(_url_codes(plain))
    for code, token in _RESTRICTED_PRIORITY:
        if code in codes:
            return token
    if codes & _PERMISSIVE:
        return RIGHTS_CREATIVE_COMMONS
    licence_text = _plain_text(visible).casefold().translate(_DASHES)
    if _APACHE.search(licence_text):
        return RIGHTS_APACHE
    if _MIT.search(licence_text):
        return RIGHTS_MIT
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, a Webflow
    Last Published comment, and a copyright year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_HIDDEN.sub(" ", page_html))
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        match = _DATE_PREFIX.match(raw.strip())
        if match is None:
            continue
        try:
            date.fromisoformat(match.group(1))
        except ValueError:
            continue
        return match.group(1)
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    for heading in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", heading))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return Gray Swan AI when the page states that name.

    A host name, a terms link, or a person named on the page is not the
    publisher. The name is not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _HIDDEN.sub(" ", page_html)
    site = _metas(visible).get("og:site_name", "")
    if PUBLISHER.casefold() in _clean_text(site).casefold():
        return PUBLISHER
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
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _public_path(path: str) -> bool:
    if path == "":
        return True
    if path == "/" or not path.startswith("/") or path.endswith("/"):
        return False
    lowered = path.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return not lowered.startswith(_BLOCKED_PREFIXES)


def _same_page(left: str, right: str) -> bool:
    one = urlparse(left)
    other = urlparse(right)
    if (one.hostname or "").lower().rstrip(".") != (other.hostname or "").lower().rstrip("."):
        return False
    return (one.path or "").rstrip("/") == (other.path or "").rstrip("/")


def _robots_groups(text: str) -> list[list[tuple[str, str]]]:
    groups: list[list[tuple[str, str]]] = []
    rules: list[tuple[str, str]] = []
    saw_agent = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules:
                groups.append(rules)
                rules = []
            saw_agent = value == "*"
            continue
        if key in {"allow", "disallow"} and saw_agent:
            rules.append((key, value))
    if rules:
        groups.append(rules)
    return groups


def _wildcard_rules(groups: list[list[tuple[str, str]]]) -> list[tuple[str, str]]:
    merged: list[tuple[str, str]] = []
    for rules in groups:
        merged.extend(rules)
    return merged


def _take_creativecommons_anchors(visible: str) -> tuple[str, set[str]]:
    codes: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        href = _attrs("<a" + match.group(1) + ">").get("href", "")
        if "creativecommons.org" not in href.casefold():
            return match.group(0)
        codes.update(_url_codes(href))
        return " "

    return _ANCHOR.sub(replace, visible), codes


def _url_codes(value: str) -> set[str]:
    found: set[str] = set()
    for match in _CC_URL.finditer(unescape(value).casefold().translate(_DASHES)):
        kind = match.group("pd")
        licence = match.group("lic")
        if kind == "zero":
            found.add("zero")
        elif licence:
            found.add(licence)
    return found


def _text_codes(value: str) -> set[str]:
    folded = unescape(value).casefold().translate(_DASHES)
    found: set[str] = set()
    for code, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            found.add(code)
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if metas.get(name)]


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
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _usable_title(title: str) -> bool:
    return bool(title) and title.casefold() not in _GENERIC_TITLES


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
