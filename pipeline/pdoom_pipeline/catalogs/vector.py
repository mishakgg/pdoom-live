"""Metadata catalog of confirmed public Vector Institute pages.

Rows keep a title, publisher, canonical URL, date, and rights label. Page
bodies, abstracts, PDFs, and chart data are not stored. A date the page does
not state stays unknown. Updated times, modified times, and copyright years
are not publication dates. ``creative_commons`` means the page states CC0,
CC BY, or CC BY-SA and does not also state a restricted deed. CC BY-NC,
CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen is a word
boundary, so CC BY does not match CC BY-NC. A generic licence-chooser URL is
not a deed. Public Domain Mark is not CC0. A public page, a copyright notice,
a terms link, or a Canadian government page is not a licence. An empty entry
list is valid. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "vector_pages"
CATALOG_FILENAME = "vector_pages.json"
CATALOG_DESCRIPTION = (
    "Metadata for confirmed public pages on the Vector Institute site "
    "vectorinstitute.ai. This is not every page on the site. Each stored URL "
    "was confirmed with one bounded GET that returned HTML. Challenge pages "
    "are omitted. Rows keep the title, publisher, canonical URL, date, and "
    "rights. Page bodies, abstracts, PDFs, and chart data are not stored. A "
    "missing date is unknown. Updated, modified, and copyright years are not "
    "publication dates. Rights stay unknown unless the page states CC0, CC BY, "
    "or CC BY-SA and does not also state a restricted deed. A public page or a "
    "Canadian government page is not a licence. runner_wired is false."
)
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "vectorinstitute.ai"
PUBLISHER = "Vector Institute"
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
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date"})
_ARTICLE_TYPES = frozenset(
    {"article", "blogposting", "newsarticle", "scholarlyarticle", "report"}
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge-platform/",
    "checking your browser",
    "enable javascript and cookies",
    "cf-mitigated",
    "sorry, you have been blocked",
    "please verify you are a human",
    "verify you are human",
)
_GENERIC_TITLES = frozenset(
    {
        "home",
        "log in",
        "menu",
        "search",
        "sign in",
        "vector institute for artificial intelligence",
    }
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_PATH = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)*$")
_HTTPS_URL = re.compile(
    r"^https://(?P<host>[a-z0-9.-]+)(?::(?P<port>\d{1,5}))?(?P<path>/[a-z0-9/-]*)?$"
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b([^>]*)>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_HREF = re.compile(
    r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))"""
)
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(
    r"(?i)\s+(?:\|\s*|[-–—]\s+)Vector Institute(?: for Artificial Intelligence)?\s*$"
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"((?:\\.|[^"\\])*)"')
_DEED_TAIL = r"(?=$|[\s,.;:)/]|\d)"
# Restricted deeds are listed before any permissive CC BY check. A hyphen is a
# word boundary, so CC BY must not match CC BY-NC, CC BY-ND, or the longer deeds.
_CC_URL_RESTRICTED = re.compile(
    r"creativecommons\.org/licenses/by-nc-nd(?=/|$|\?|#)"
    r"|creativecommons\.org/licenses/by-nc-sa(?=/|$|\?|#)"
    r"|creativecommons\.org/licenses/by-nc(?=/|$|\?|#)"
    r"|creativecommons\.org/licenses/by-nd(?=/|$|\?|#)"
)
_CC_URL_PERMISSIVE = re.compile(
    r"creativecommons\.org/publicdomain/zero(?=/|$|\?|#)"
    r"|creativecommons\.org/licenses/by-sa(?=/|$|\?|#)"
    r"|creativecommons\.org/licenses/by(?=/|$|\?|#)"
)
_CC_TEXT_RESTRICTED = re.compile(
    r"(?<![a-z0-9])cc[\s-]+by[\s-]+nc[\s-]+nd"
    + _DEED_TAIL
    + r"|(?<![a-z0-9])cc[\s-]+by[\s-]+nc[\s-]+sa"
    + _DEED_TAIL
    + r"|(?<![a-z0-9])cc[\s-]+by[\s-]+nc"
    + _DEED_TAIL
    + r"|(?<![a-z0-9])cc[\s-]+by[\s-]+nd"
    + _DEED_TAIL
    + r"|creative commons attribution[\s-]+non[\s-]?commercial[\s-]+no[\s-]?deriv"
    + r"|creative commons attribution[\s-]+non[\s-]?commercial[\s-]+share[\s-]?alike"
    + r"|creative commons attribution[\s-]+non[\s-]?commercial\b"
    + r"|creative commons attribution[\s-]+no[\s-]?deriv"
)
_CC_TEXT_PERMISSIVE = re.compile(
    r"(?<![a-z0-9])cc0(?![a-z0-9])"
    r"|creative commons (?:cc0|zero)\b"
    r"|(?<![a-z0-9])cc[\s-]+zero\b"
    r"|(?<![a-z0-9])cc[\s-]+by[\s-]+sa"
    + _DEED_TAIL
    + r"|creative commons attribution[\s-]+share[\s-]?alike\b"
    r"|(?<![a-z0-9])cc[\s-]+by(?![\s-]*(?:nc|nd|sa|non|no))"
    + _DEED_TAIL
    + r"|creative commons attribution(?![\s-]*(?:non|no[\s-]?deriv|share))"
    + _DEED_TAIL
)


class CatalogError(ValueError):
    """A catalog row or page failed the Vector Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_vector_host(hostname: str) -> bool:
    """True only for the official vectorinstitute.ai host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def confirmed_html_page(body: str, *, content_type: str) -> bool:
    """True when one response is an HTML document rather than a challenge.

    A Cloudflare interstitial, a robot block, or a non-HTML body is not a
    catalog page. The check does not solve a challenge or reuse a clearance
    cookie.
    """

    if not isinstance(body, str) or not isinstance(content_type, str):
        return False
    media = content_type.split(";", 1)[0].strip().casefold()
    if media not in _HTML_TYPES:
        return False
    if "<html" not in body[:12000].casefold() and "<!doctype html" not in body[:12000].casefold():
        return False
    prefix = body[:1500].casefold()
    if any(marker in prefix for marker in _CHALLENGE_MARKERS):
        return False
    head = body[:12000].casefold()
    return "challenge-platform" not in head and "cf-mitigated" not in head


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the
    page does not also state CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND.
    A by-nc URL stays unknown even when the anchor text says CC BY. Public
    Domain Mark is not CC0. A generic creativecommons.org/licenses/ URL is not
    a deed.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    blobs = _licence_blobs(page_text)
    visible = _without_hidden(page_text)
    blobs.extend(_hrefs(visible))
    blobs.extend(_meta_values(visible, _LICENSE_META))
    folded_blobs = "\n".join(blobs).casefold().replace("\\/", "/")
    folded_plain = _plain(visible).casefold()
    if _states_restricted_deed(folded_blobs) or _states_restricted_deed(folded_plain):
        return RIGHTS_UNKNOWN
    if _states_permissive_deed(folded_blobs) or _states_permissive_deed(folded_plain):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""
    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    article_dates: list[str] = []
    page_dates: list[str] = []
    for blob in _LDJSON.findall(page_text):
        payload = _load_json(blob)
        if payload is None:
            continue
        _collect_published_dates(payload, article_dates, page_dates)
    for raw in article_dates + page_dates:
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    visible = _without_hidden(page_text)
    for raw in _meta_values(visible, _PUBLISHED_META):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str, *, page_url: str | None = None) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    headline = _article_headline(page_html)
    if headline:
        return headline
    for heading in _headings(page_html):
        if _heading_matches_url(heading, page_url):
            return heading
    document = _document_title(page_html)
    if document:
        return document
    for heading in _headings(page_html):
        return heading
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Vector Institute when the page identifies that organization."""
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    names = [_metas(page_html).get("og:site_name", "")]
    for blob in _LDJSON.findall(page_html):
        payload = _load_json(blob)
        if payload is not None:
            names.extend(_organization_names(payload))
    if "vector institute" in " ".join(names).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return {
        "title": title_from_page(page_html, page_url=page_url),
        "publisher": publisher_from_page(page_html),
        "canonical_url": confirmed_url(page_html, page_url),
        "date": date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }


def confirmed_url(page_html: str, page_url: str) -> str:
    live = validate_canonical_url(page_url)
    href = _canonical_href(page_html)
    if not href:
        return live
    try:
        declared = validate_canonical_url(_join_url(live, href))
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
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be an https vectorinstitute.ai page")
    parsed = _HTTPS_URL.fullmatch(url)
    if parsed is None:
        raise CatalogError(f"canonical URL must be an https vectorinstitute.ai page: {url}")
    host = parsed.group("host")
    path = parsed.group("path") or ""
    if (
        parsed.group("port") is not None
        or not official_vector_host(host)
        or host != OFFICIAL_HOST
        or ".." in path
        or "\\" in path
        or "//" in path
        or _PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL must be an https vectorinstitute.ai page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


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
    left_path = _HTTPS_URL.fullmatch(left)
    right_path = _HTTPS_URL.fullmatch(right)
    if left_path is None or right_path is None:
        return False
    return left_path.group("host") == right_path.group("host") and (
        (left_path.group("path") or "").rstrip("/") == (right_path.group("path") or "").rstrip("/")
    )


def _join_url(base: str, href: str) -> str:
    ref = unescape(href).strip()
    if ref.startswith("https://") or ref.startswith("http://"):
        return ref
    if ref.startswith("//"):
        return "https:" + ref
    parsed = _HTTPS_URL.fullmatch(base)
    if parsed is None:
        return ref
    origin = f"https://{parsed.group('host')}"
    if ref.startswith("/"):
        return origin + ref.split("?", 1)[0].split("#", 1)[0]
    base_path = parsed.group("path") or "/"
    directory = base_path if base_path.endswith("/") else base_path.rsplit("/", 1)[0] + "/"
    relative = ref.split("?", 1)[0].split("#", 1)[0]
    return origin + directory + relative


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _plain(value)).strip()


def _usable_title(title: str) -> bool:
    if not title or title.casefold() in _GENERIC_TITLES:
        return False
    return len(title) <= MAX_FIELD_CHARS and "<" not in title and ">" not in title and "\n" not in title


def _states_restricted_deed(value: str) -> bool:
    return _CC_URL_RESTRICTED.search(value) is not None or _CC_TEXT_RESTRICTED.search(value) is not None


def _states_permissive_deed(value: str) -> bool:
    return _CC_URL_PERMISSIVE.search(value) is not None or _CC_TEXT_PERMISSIVE.search(value) is not None


def _licence_blobs(page_text: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_text):
        payload = _load_json(blob)
        if payload is None:
            found.extend(item.replace("\\/", "/") for item in _LD_LICENSE.findall(blob))
            continue
        found.extend(_license_values(payload))
    return found


def _license_values(payload: object) -> list[str]:
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key.casefold() in {"license", "licence"}:
                if isinstance(value, str):
                    found.append(value)
                elif isinstance(value, dict):
                    for sub in ("@id", "url", "name"):
                        raw = value.get(sub)
                        if isinstance(raw, str):
                            found.append(raw)
                continue
            if isinstance(value, (dict, list)):
                walk(value)

    walk(payload)
    return found


def _collect_published_dates(payload: object, article_dates: list[str], page_dates: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_published_dates(item, article_dates, page_dates)
        return
    if not isinstance(payload, dict):
        return
    published = payload.get("datePublished")
    if isinstance(published, str):
        types = _types(payload)
        if types & _ARTICLE_TYPES:
            article_dates.append(published)
        elif "webpage" in types:
            page_dates.append(published)
    for value in payload.values():
        if isinstance(value, (dict, list)):
            _collect_published_dates(value, article_dates, page_dates)


def _organization_names(payload: object) -> list[str]:
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        if "organization" in _types(node):
            name = node.get("name")
            if isinstance(name, str):
                found.append(name)
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    walk(payload)
    return found


def _article_headline(page_html: str) -> str:
    for blob in _LDJSON.findall(page_html):
        payload = _load_json(blob)
        if payload is None:
            continue
        headline = _headline(payload)
        if headline:
            return headline
    return ""


def _headline(payload: object) -> str:
    if isinstance(payload, list):
        for item in payload:
            found = _headline(item)
            if found:
                return found
        return ""
    if not isinstance(payload, dict):
        return ""
    if _types(payload) & _ARTICLE_TYPES:
        raw = payload.get("headline")
        if isinstance(raw, str):
            title = _clean_title(raw)
            if _usable_title(title):
                return title
    for value in payload.values():
        if isinstance(value, (dict, list)):
            found = _headline(value)
            if found:
                return found
    return ""


def _headings(page_html: str) -> list[str]:
    found: list[str] = []
    for attrs, inner in _H1.findall(page_html):
        if "site-name" in attrs.casefold() or "logo" in attrs.casefold():
            continue
        title = _clean_title(inner)
        if _usable_title(title):
            found.append(title)
    return found


def _heading_matches_url(heading: str, page_url: str | None) -> bool:
    if not page_url:
        return False
    parsed = _HTTPS_URL.fullmatch(page_url)
    if parsed is None:
        return False
    segments = [part for part in (parsed.group("path") or "").split("/") if part]
    if not segments:
        return False
    folded = heading.casefold()
    tokens = [token for token in segments[-1].split("-") if len(token) >= 2]
    if not tokens:
        return False
    return all(
        re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", folded) is not None for token in tokens
    )


def _document_title(page_html: str) -> str:
    metas = _metas(page_html)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    match = _TITLE.search(page_html)
    if not match:
        return ""
    title = _clean_title(match.group(1))
    if _usable_title(title):
        return title
    return ""


def _types(node: dict) -> set[str]:
    raw = node.get("@type")
    if isinstance(raw, str):
        return {raw.casefold()}
    if isinstance(raw, list):
        return {str(item).casefold() for item in raw if isinstance(item, str)}
    return set()


def _load_json(blob: str) -> object | None:
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


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
    year, month, day = (int(part) for part in value.split("-"))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


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


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _canonical_href(page_html: str) -> str:
    for tag in _LINK.findall(page_html):
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
