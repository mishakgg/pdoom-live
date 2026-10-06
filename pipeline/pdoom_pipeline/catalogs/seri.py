"""Metadata catalog of public Stanford Existential Risks Initiative pages.

Rows keep a title, publisher, canonical URL, date, and rights label. A row is
stored only when one bounded response is HTML from seri.stanford.edu. A
Cloudflare challenge, a SiteGround captcha, an HTTP 202 response, an Akamai
interstitial, a robot check, a non-HTML body, or a redirect off that host is
not stored. Page bodies are not stored. A missing date is unknown. Updated,
modified, and copyright years are not publication dates.

Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA. Those three
are creative_commons. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay
unknown, and a restricted deed wins when it appears beside a permissive one.
A hyphen continues a licence token, so CC BY does not match CC BY-NC. A
creativecommons.org/licenses/ URL has to name one deed. uk_ogl is used only
when the page states the Open Government Licence. us_government_work is used
only when a rights field says the item is a US government work. A public page,
a copyright notice, all rights reserved, a terms link, and a .edu host are not
licences. Stanford HAI and Stanford CRFM are not this host.

This catalog is not a collector. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "seri_pages"
CATALOG_FILENAME = "seri_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
ALLOWED_RIGHTS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
    }
)
OFFICIAL_HOST = "seri.stanford.edu"
EXCLUDED_HOSTS = frozenset(
    {
        "hai.stanford.edu",
        "www.hai.stanford.edu",
        "crfm.stanford.edu",
        "www.crfm.stanford.edu",
    }
)
PUBLISHER = "Stanford Existential Risks Initiative"
TIMEOUT_SECONDS = 10.0
MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 1_000_000
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
        "chart",
        "content",
        "description_text",
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
_JSONLD = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_RIGHTS_DD = re.compile(
    r"(?is)<(?:dt|th)\b[^>]*>\s*rights\s*</(?:dt|th)>\s*<(?:dd|td)\b[^>]*>(.*?)</(?:dd|td)>"
)
_PUBLISHING_TIME = re.compile(
    r"(?is)<([a-z0-9]+)\b[^>]*\bclass\s*=\s*(['\"])([^'\"]*)\2[^>]*>"
    r"(?:(?!</\1>).){0,600}?"
    r"<time\b[^>]*\bdatetime\s*=\s*(['\"])([^'\"]+)\4"
)
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
    "dc.date.issued",
)
_RIGHTS_META = frozenset(
    {
        "rights",
        "dc.rights",
        "dcterms.rights",
        "license",
        "dc.license",
        "dcterms.license",
    }
)
_SITE_SUFFIXES = (
    " | Stanford Existential Risks Initiative",
    " | Existential Risks Initiative",
    " — Stanford Existential Risks Initiative",
    " — Existential Risks Initiative",
    " – Stanford Existential Risks Initiative",
    " – Existential Risks Initiative",
    " - Stanford Existential Risks Initiative",
    " - Existential Risks Initiative",
)
_SITE_NAMES = frozenset(
    {
        "existential risks initiative",
        "stanford existential risks initiative",
    }
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
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".mp3",
    ".mp4",
    ".css",
    ".js",
)
_DISALLOWED_PREFIXES = (
    "/admin",
    "/comment",
    "/core",
    "/filter",
    "/honeypot",
    "/index.php",
    "/media/oembed",
    "/node/add",
    "/profiles",
    "/saml",
    "/search",
    "/sso",
    "/user",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "cf-browser-verification",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "enable javascript and cookies",
    "sgcaptcha",
    "sg-captcha",
    "siteground captcha",
    "errors.edgesuite.net",
    "akamai bot manager",
    "are you a robot",
    "verify you are a human",
    "robot interstitial",
    "pardon our interruption",
)
# Longer restricted deeds are listed before shorter ones. A hyphen is not the end
# of a deed, so licenses/by does not match licenses/by-nc.
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:publicdomain/(?P<pd>zero|mark)"
    r"|licenses/(?P<deed>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by))"
    r"(?![a-z0-9-])"
)
_TEXT_CODES = (
    ("by-nc-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])")),
    ("by-nc-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])")),
    ("by-nc", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9])")),
    ("by-nd", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    (
        "by-nc-nd",
        re.compile(
            r"(?i)creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*derivatives"
        ),
    ),
    (
        "by-nc-sa",
        re.compile(
            r"(?i)creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    ("by-nc", re.compile(r"(?i)creative commons attribution[\s-]+non[\s-]*commercial")),
    ("by-nd", re.compile(r"(?i)creative commons attribution[\s-]+no[\s-]*derivatives")),
    ("mark", re.compile(r"(?i)public domain mark\b")),
    ("by-sa", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9])")),
    ("by-sa", re.compile(r"(?i)creative commons attribution[\s-]+share[\s-]*alike")),
    ("zero", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])|\bcreative commons zero\b|\bcc zero\b")),
    ("by", re.compile(r"(?i)(?<![a-z0-9])cc[\s-]*by(?![a-z0-9-])")),
    (
        "by",
        re.compile(
            r"(?i)creative commons attribution(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_RESTRICTED_DEEDS = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_PERMISSIVE_DEEDS = frozenset({"by", "by-sa", "zero"})
_OGL = re.compile(r"(?i)open government licence\b|open-government-licence")
_GOV_WORK = re.compile(
    r"(?i)\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"(?i)\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)


class CatalogError(ValueError):
    """A catalog row or page failed the Stanford Existential Risks Initiative rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_seri_host(hostname: str) -> bool:
    """True only for the confirmed seri.stanford.edu host."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    if host in EXCLUDED_HOSTS:
        return False
    return host == OFFICIAL_HOST


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str, headers: Mapping[str, str] | None = None) -> bool:
    """True when the response is an interstitial rather than the SERI page."""

    if headers:
        for key, value in headers.items():
            if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
                return True
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    plain = _plain(page_html).casefold()
    return any(marker in lowered or marker in plain for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> bool:
    """A row requires one HTML response from the official host inside the bounds."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if redirect_count > MAX_REDIRECTS:
        return False
    if elapsed_seconds is not None and elapsed_seconds > TIMEOUT_SECONDS:
        return False
    if len(page_html.encode("utf-8")) > MAX_RESPONSE_BYTES:
        return False
    if not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html, headers):
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
    redirect_count: int = 0,
    elapsed_seconds: float | None = None,
) -> dict | None:
    """Return metadata when the bounded response is the page HTML.

    An HTTP 202 challenge, a non-HTML body, a robot interstitial, or a final
    URL off seri.stanford.edu is not stored.
    """

    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        redirect_count=redirect_count,
        elapsed_seconds=elapsed_seconds,
    ):
        return None
    assert isinstance(page_html, str)
    return metadata_from_page(page_html, page_url=page_url)


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    creative_commons is only CC0, CC BY, or CC BY-SA. A restricted deed, a
    public-domain mark, a copyright notice, or a .edu host stays unknown.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _visible_html(page_text)
    codes = _licence_codes(visible + " " + " ".join(_jsonld_licence_strings(page_text)))
    if codes & _RESTRICTED_DEEDS:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_DEEDS:
        return RIGHTS_CREATIVE_COMMONS
    if _us_government_work(" ".join(_rights_fields(page_text))):
        return RIGHTS_US_GOVERNMENT_WORK
    if _OGL.search(_plain(visible)):
        return RIGHTS_UK_OGL
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years do not count."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(_visible_html(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        found = _iso_prefix(metas.get(key))
        if found:
            return found
    published = []
    for raw in _jsonld_values(page_html, "datepublished"):
        found = _iso_prefix(raw)
        if found:
            published.append(found)
    unique = set(published)
    if len(unique) == 1:
        return next(iter(unique))
    times = _single_publishing_date(page_html)
    if times:
        return times
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    headings = [_clean_title(_plain(inner)) for inner in _H1.findall(visible)]
    for heading in headings:
        if heading and heading.casefold() not in _SITE_NAMES:
            return heading
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_plain(title_tag.group(1)))
        if title:
            return title
    for heading in headings:
        if heading:
            return heading
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    blob = " ".join(
        (
            metas.get("og:site_name", ""),
            metas.get("og:title", ""),
            _plain(visible)[:2000],
        )
    ).casefold()
    if "existential risks initiative" not in blob:
        raise CatalogError("publisher must be the Stanford Existential Risks Initiative")
    return PUBLISHER


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the response
    URL. A rel=canonical on another host or path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_join(live, href))
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
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
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
    if entry["rights"] not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an https seri.stanford.edu page")
    if any(mark in url for mark in ("@", "?", "#", "\\")):
        raise CatalogError(f"canonical URL must be an https seri.stanford.edu page: {url}")
    prefix = f"https://{OFFICIAL_HOST}"
    if url.startswith(prefix + ":443"):
        raise CatalogError(f"canonical URL must be an https seri.stanford.edu page: {url}")
    if not url.startswith(prefix):
        raise CatalogError(f"canonical URL must be an https seri.stanford.edu page: {url}")
    rest = url[len(prefix) :]
    if rest == "":
        path = "/"
        normalized = prefix + "/"
    elif rest.startswith("/"):
        path = rest
        normalized = url
    else:
        raise CatalogError(f"canonical URL must be an https seri.stanford.edu page: {url}")
    host = OFFICIAL_HOST
    if (
        not official_seri_host(host)
        or ".." in path
        or "//" in path
        or not _html_path(path)
    ):
        raise CatalogError(f"canonical URL must be an https seri.stanford.edu page: {url}")
    return normalized


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _html_path(path: str) -> bool:
    bare = path if path == "/" else path.rstrip("/")
    lowered = bare.lower()
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if bare != "/":
        for prefix in _DISALLOWED_PREFIXES:
            root = prefix.rstrip("/")
            if bare == root or bare.startswith(root + "/"):
                return False
    return True


def _require_text(entry: dict, field: str) -> None:
    value = entry[field]
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
        if len(value) > MAX_DESCRIPTION_CHARS:
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _same_page(left: str, right: str) -> bool:
    return left.rstrip("/") == right.rstrip("/") or (left.rstrip("/") == f"https://{OFFICIAL_HOST}" and right.rstrip("/") == f"https://{OFFICIAL_HOST}")


def _join(base: str, href: str) -> str:
    link = href.strip()
    if link.startswith("https://") or link.startswith("http://"):
        return link
    if link.startswith("//"):
        return "https:" + link
    if link.startswith("/"):
        return f"https://{OFFICIAL_HOST}{link}"
    parent = base.rsplit("/", 1)[0]
    return parent + "/" + link


def _visible_html(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


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
    for tag in _LINK.findall(_visible_html(page_html)):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""


def _rights_fields(page_html: str) -> list[str]:
    fields: list[str] = []
    visible = _visible_html(page_html)
    for tag in _META.findall(visible):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key in _RIGHTS_META and attrs.get("content"):
            fields.append(attrs["content"][:2000])
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "license" in rel and attrs.get("href"):
            fields.append(attrs["href"][:2000])
    for block in _RIGHTS_DD.findall(visible):
        fields.append(_plain(block)[:2000])
    fields.extend(_jsonld_licence_strings(page_html))
    return fields


def _jsonld_licence_strings(page_html: str) -> list[str]:
    found: list[str] = []
    for node in _jsonld_dicts(page_html):
        for key, value in node.items():
            if key.casefold() in {"license", "rights"}:
                found.extend(part[:2000] for part in _text_values(value))
    return found


def _jsonld_values(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    for node in _jsonld_dicts(page_html):
        for name, value in node.items():
            if name.casefold() == key:
                found.extend(_text_values(value))
    return found


def _jsonld_dicts(page_html: str) -> list[dict]:
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for block in _JSONLD.findall(page_html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        walk(data)
    return found


def _text_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        for key in ("@value", "url", "@id", "name"):
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


def _licence_codes(page_text: str) -> set[str]:
    codes: set[str] = set()
    text = page_text
    for match in list(_CC_URL.finditer(text)):
        pd = (match.group("pd") or "").lower()
        deed = (match.group("deed") or "").lower()
        if pd == "mark":
            codes.add("mark")
        elif pd == "zero":
            codes.add("zero")
        elif deed:
            codes.add(deed)
        text = text.replace(match.group(0), " ", 1)
    plain = _plain(text)
    for code, pattern in _TEXT_CODES:
        if pattern.search(plain):
            codes.add(code)
            plain = pattern.sub(" ", plain)
    return codes


def _us_government_work(rights_text: str) -> bool:
    if not rights_text.strip():
        return False
    if _NEGATED_GOV_WORK.search(rights_text):
        return False
    return _GOV_WORK.search(rights_text) is not None


def _single_publishing_date(page_html: str) -> str:
    found: list[str] = []
    visible = _visible_html(page_html)
    for _tag, _quote, classes, _mark, raw in _PUBLISHING_TIME.findall(visible):
        folded = classes.casefold()
        if "publishing-date" not in folded:
            continue
        if "modified" in folded or "updated" in folded:
            continue
        parsed = _iso_prefix(raw)
        if parsed:
            found.append(parsed)
    if len(found) == 1:
        return found[0]
    return ""


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
