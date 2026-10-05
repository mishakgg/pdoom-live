"""Metadata catalog of public EleutherAI pages on eleuther.ai.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, papers, and model
weights are not stored. Publisher is EleutherAI. Rights stay unknown unless the
page states a reuse licence, which is kept only as a short token.
creative_commons means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. apache-2.0 and mit stay their own
tokens when the page states those licences. A public page, a copyright notice,
an all-rights-reserved line, or a terms link is not a licence. A page that
does not state a publication date keeps the date unknown. Updated times,
modified times, copyright years, and dates on listed items are not publication
dates. The live URL is stored as confirmed; a different rel=canonical does not
replace it. This module does not fetch and it is not a belief collector.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "eleuther_pages"
CATALOG_FILENAME = "eleuther_pages.json"
PUBLISHER = "EleutherAI"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
ALLOWED_RIGHTS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_MIT, RIGHTS_APACHE}
)
UNKNOWN_DATE = "unknown"
OFFICIAL_HOSTS = frozenset({"eleuther.ai", "www.eleuther.ai"})
MAX_TEXT_CHARS = 300
MAX_DESCRIPTION_CHARS = 800

_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SLASH_DATE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(r"(?is)<script\b[^>]*application/ld\+json[^>]*>(.*?)</script>")
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>|<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s+(?:[-–—|]\s*EleutherAI)\s*$")
_PUBLICATION_DATE_KEYS = (
    "citation_date",
    "citation_publication_date",
    "article:published_time",
    "dcterms.created",
    "dcterms.issued",
)
_DOWNLOAD_SUFFIXES = (
    ".pdf",
    ".zip",
    ".csv",
    ".json",
    ".xml",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".bmp",
    ".avif",
    ".tif",
    ".tiff",
    ".js",
    ".css",
    ".bin",
    ".pt",
    ".pth",
    ".safetensors",
    ".gguf",
    ".onnx",
    ".ckpt",
    ".h5",
    ".msgpack",
    ".npz",
    ".tar",
    ".gz",
    ".tgz",
    ".7z",
    ".rar",
    ".model",
    ".weights",
)
# Longer codes are listed first so by-nc is not read as by.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?=/|\b|[?#]|$)"
)
_CC_TEXT_CODES = (
    ("by-nc-nd", re.compile(r"\b(?:cc[-\s]?)?by-nc-nd\b")),
    ("by-nc-sa", re.compile(r"\b(?:cc[-\s]?)?by-nc-sa\b")),
    ("by-nc", re.compile(r"\b(?:cc[-\s]?)?by-nc\b")),
    ("by-nd", re.compile(r"\b(?:cc[-\s]?)?by-nd\b")),
    ("by-sa", re.compile(r"\b(?:cc[-\s]?)?by-sa\b")),
    ("zero", re.compile(r"\bcc0\b|\bcreative commons zero\b|\bcc zero\b")),
    ("by", re.compile(r"\bcc[-\s]by\b")),
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_MIT = re.compile(r"licen[cs]ed under (?:the )?mit licen[cs]e\b")
_APACHE = re.compile(
    r"licen[cs]ed under (?:the )?apache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?:\b|/|$)")
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?:\b|/|$)"
)


class CatalogError(ValueError):
    """A catalog row or page failed the EleutherAI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document has unexpected fields")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    _require_text(description, "description", MAX_DESCRIPTION_CHARS)
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
    seen: set[str] = set()
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError("rights must be unknown or a short reuse-licence token")
    return entry


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
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError(f"canonical URL must be a public EleutherAI page: {url}")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    netloc = (parsed.netloc or "").lower()
    if (
        parsed.scheme != "https"
        or host.endswith(".")
        or netloc not in OFFICIAL_HOSTS
        or host not in OFFICIAL_HOSTS
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
        or _is_download(path)
    ):
        raise CatalogError(f"canonical URL must be a public EleutherAI page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower()
    if not host or host.endswith("."):
        return False
    return host in OFFICIAL_HOSTS and not hostname_is_blocked(host)


def rights_from_page(page_text: str) -> str:
    """Return a short rights token, or unknown when the page states no reuse licence.

    creative_commons means only CC0, CC BY, or CC BY-SA. CC BY-NC, CC BY-ND,
    CC BY-NC-SA, and CC BY-NC-ND stay unknown. A restricted licence on the page
    keeps the label unknown even when a permissive licence is also present.
    Script, style, and comment text does not count. A copyright notice, an
    all-rights-reserved line, a public page, or a link to terms is not a
    licence. The licence sentence itself is not returned.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _strip_hidden(page_text)
    plain = _plain_text(visible).casefold()
    codes = _cc_codes_in_text(plain)
    license_hrefs: list[str] = []
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = attrs.get("rel", "").casefold().split()
        if "license" not in rel and "licence" not in rel:
            continue
        href = attrs.get("href", "")
        codes.update(_cc_codes_in_text(href))
        license_hrefs.append(href.casefold())
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        return RIGHTS_CREATIVE_COMMONS
    if _MIT.search(plain) or any(_MIT_URL.search(href) for href in license_hrefs):
        return RIGHTS_MIT
    if _APACHE.search(plain) or any(_APACHE_URL.search(href) for href in license_hrefs):
        return RIGHTS_APACHE
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, dateModified, updated labels,
    copyright years, and dates on listed items are not publication dates.
    A date in the URL is not a publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for raw in _jsonld_date_published(page_html):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    metas = _metas(_strip_hidden(page_html))
    for key in _PUBLICATION_DATE_KEYS:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _strip_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
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


def publisher_from_page(page_html: str) -> str:
    """Return EleutherAI when the page states that name.

    A person's name in citation metadata is not the publisher.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _strip_hidden(page_html)
    site = _metas(visible).get("og:site_name", "").strip()
    if site == PUBLISHER:
        return PUBLISHER
    if re.search(rf"\b{re.escape(PUBLISHER)}\b", _plain_text(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the page text. ``page_url`` is the live URL
    that returned the page HTML. A rel=canonical pointing somewhere else is
    not used. The publisher is EleutherAI when the page states that name.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def _jsonld_date_published(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        text = block.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            found.extend(_DATE_PUBLISHED.findall(text))
            continue
        _collect_date_published(payload, found)
    return found


def _collect_date_published(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_date_published(item, found)
        return
    if not isinstance(payload, dict):
        return
    if "@graph" in payload:
        _collect_date_published(payload["@graph"], found)
    published = payload.get("datePublished")
    if isinstance(published, str):
        found.append(published)


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    slash = _SLASH_DATE.match(text)
    if slash:
        text = f"{slash.group(1)}-{slash.group(2)}-{slash.group(3)}" + text[slash.end() :]
    match = _DATE_PREFIX.match(text)
    if match is None:
        return None
    value = match.group(1)
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _is_download(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered.endswith(_DOWNLOAD_SUFFIXES)


def _cc_codes_in_text(plain: str) -> set[str]:
    """Return CC licence codes stated in text. Restricted codes are not permissive."""

    folded = plain.casefold().replace("–", "-").replace("—", "-")
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT_CODES:
        if pattern.search(folded):
            codes.add(code)
    if "creative commons" not in folded:
        return codes
    noncommercial = re.search(r"non-?commercial", folded) is not None
    noderiv = re.search(r"no-?deriv", folded) is not None
    sharealike = re.search(r"share-?alike", folded) is not None
    if noncommercial and noderiv:
        codes.add("by-nc-nd")
    elif noncommercial and sharealike:
        codes.add("by-nc-sa")
    elif noncommercial:
        codes.add("by-nc")
    elif noderiv:
        codes.add("by-nd")
    elif sharealike:
        codes.add("by-sa")
    elif re.search(r"\battribution\b", folded):
        codes.add("by")
    return codes


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _clean_title(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"\s+", " ", text).strip()
    changed = True
    while changed and text:
        changed = False
        updated = _SITE_SUFFIX.sub("", text).strip()
        if updated != text:
            text = updated
            changed = True
    return text


def _strip_hidden(page_html: str) -> str:
    without_comments = _COMMENT.sub(" ", page_html)
    return _HIDDEN.sub(" ", without_comments)


def _plain_text(page_html: str) -> str:
    text = _TAG.sub(" ", page_html)
    text = unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


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
