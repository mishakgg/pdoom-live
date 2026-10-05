"""Metadata catalog of public articles on the official host distill.pub.

Each stored URL was confirmed with one bounded GET that returned HTML. A row
keeps the title, publisher, canonical URL, date, and rights label. Article
bodies, figures, and explanations are not stored. A Cloudflare challenge, a
captcha, a robot interstitial, a non-HTML response, or a final URL off
distill.pub is not stored. An empty catalog is a valid result. A missing date
is unknown. Updated, modified, and copyright years are not publication dates.
Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA, which are
labeled creative_commons. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND
stay unknown. A restricted deed wins when it appears beside a permissive one.
The Public Domain Mark is not CC0. A public page or a copyright notice is not
a licence. This module does not fetch and it is not a belief collector.
runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "distill_pages"
CATALOG_FILENAME = "distill_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_LABELS = frozenset({RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS})
OFFICIAL_HOST = "distill.pub"
PUBLISHER = "Distill"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800
DESCRIPTION = (
    "Metadata for public articles on the official host distill.pub. Each stored "
    "URL was confirmed with one bounded GET that returned HTML. A Cloudflare "
    "challenge, a captcha, a robot interstitial, a non-HTML response, or a "
    "redirect off distill.pub stores no row. An empty catalog is valid. Rows "
    "store the title, publisher, canonical URL, date, and rights. Article "
    "bodies, figures, and explanations are not stored. A missing date is "
    "unknown. Updated, modified, and copyright years are not publication dates. "
    "Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA, labeled "
    "creative_commons. CC BY-NC, CC BY-ND, CC BY-NC-SA, and CC BY-NC-ND stay "
    "unknown. A public page or a copyright notice is not a licence. runner_wired "
    "is false."
)

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
        "caption",
        "content",
        "excerpt",
        "explanation",
        "explanations",
        "figure",
        "figures",
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
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = (
    "citation_publication_date",
    "article:published_time",
    "article:published",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SLASH_DATE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})")
_SEGMENT = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_PATH = re.compile(rf"^/20\d{{2}}/{_SEGMENT}(?:/{_SEGMENT})*/$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_HREF_TAG = re.compile(r"(?is)<(?:a|link)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_SITE_SUFFIX = re.compile(r"(?i)\s+[|–—-]\s+Distill\s*$")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# Longer restricted deeds are listed first. A hyphen is not a token boundary:
# "CC BY" must not match "CC BY-NC", and "licenses/by" must not match
# "licenses/by-nc". A bare creativecommons.org/licenses/ URL is not a deed.
_RESTRICTED_DEED = re.compile(
    r"creativecommons\.org/licenses/by-nc-nd(?![\w-])|"
    r"creativecommons\.org/licenses/by-nc-sa(?![\w-])|"
    r"creativecommons\.org/licenses/by-nc(?![\w-])|"
    r"creativecommons\.org/licenses/by-nd(?![\w-])|"
    r"creativecommons\.org/publicdomain/mark(?![\w-])|"
    r"(?<![\w])cc[\s-]*by[\s-]*nc[\s-]*nd(?![\s-]*(?:sa|nd)\b)(?![\w])|"
    r"(?<![\w])cc[\s-]*by[\s-]*nc[\s-]*sa(?![\w])|"
    r"(?<![\w])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)(?![\w])|"
    r"(?<![\w])cc[\s-]*by[\s-]*nd(?![\w])|"
    r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv|"
    r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike|"
    r"creative commons attribution[\s-]*non[\s-]*commercial|"
    r"creative commons attribution[\s-]*no[\s-]*deriv|"
    r"public[\s-]*domain[\s-]*mark(?![\w])"
)
_PERMITTED_DEED = re.compile(
    r"creativecommons\.org/publicdomain/zero(?![\w-])|"
    r"creativecommons\.org/licenses/by-sa(?![\w-])|"
    r"creativecommons\.org/licenses/by(?![\w-])|"
    r"(?<![\w])cc[\s-]*0(?![\w])|"
    r"creative commons zero|"
    r"\bcc zero\b|"
    r"creative commons attribution[\s-]*share[\s-]*alike|"
    r"creative commons attribution(?![\s-]*non[\s-]*commercial)"
    r"(?![\s-]*no[\s-]*deriv)(?![\s-]*share[\s-]*alike)|"
    r"(?<![\w])cc[\s-]*by[\s-]*sa(?![\w])|"
    r"(?<![\w])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)(?![\w])"
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "cf-mitigated",
    "g-recaptcha",
    "hcaptcha",
    "cf-challenge",
)
_CHALLENGE_TEXT = (
    "just a moment",
    "enable javascript and cookies",
    "performing security verification",
    "checking your browser",
    "verify you are human",
    "are you a robot",
    "bot verification",
    "captcha",
)
_CHALLENGE_TITLES = frozenset(
    {
        "just a moment...",
        "just a moment",
        "attention required! | cloudflare",
        "access denied",
    }
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


class CatalogError(ValueError):
    """A catalog row or page failed the Distill article rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_distill_host(hostname: str) -> bool:
    """True only for the official distill.pub host."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or host != OFFICIAL_HOST or ".." in host or hostname_is_blocked(host):
        return False
    return True


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is a challenge, captcha, or robot interstitial."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    lowered = page_html.casefold()
    if any(marker in lowered for marker in _CHALLENGE_MARKERS):
        return True
    head = lowered[:8000]
    if any(marker in head for marker in _CHALLENGE_TEXT):
        return True
    title = _TITLE.search(page_html[:8000])
    if title is None:
        return False
    text = _clean_text(title.group(1)).casefold()
    if text in _CHALLENGE_TITLES:
        return True
    return "cloudflare" in text or "captcha" in text or "robot check" in text


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A row is stored only from HTML on distill.pub that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not is_html_content_type(content_type):
        return False
    if is_challenge_page(page_html):
        return False
    if headers:
        for key, value in headers.items():
            if str(key).casefold() == "cf-mitigated" and "challenge" in str(value).casefold():
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
    """Return metadata when the response is the article HTML.

    A challenge page, an error status, a non-HTML body, or a URL that is not
    an official distill.pub article is not stored.
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
    """Return creative_commons only for a stated CC0, CC BY, or CC BY-SA licence.

    CC BY-NC, CC BY-ND, CC BY-NC-SA, CC BY-NC-ND, and the Public Domain Mark
    stay unknown. Restricted deeds are checked first, and a restricted deed
    wins when a permissive one is also present. A hyphen does not end the
    token, so CC BY does not match CC BY-NC. A creativecommons.org/licenses/
    URL counts only for the deed it names. Script, style, and comment text
    does not count. A public page or a copyright notice is not a licence.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    stated = _rights_blobs(page_text)
    if _RESTRICTED_DEED.search(stated):
        return RIGHTS_UNKNOWN
    if _PERMITTED_DEED.search(stated):
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years do not count."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    metas = _metas(page_text)
    for key in _PUBLISHED_META:
        parsed = _iso_day(metas.get(key, ""))
        if parsed:
            return parsed
    for blob in _LDJSON.findall(page_text):
        for raw in _DATE_PUBLISHED.findall(blob):
            parsed = _iso_day(raw)
            if parsed:
                return parsed
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    heading = _H1.search(visible)
    if heading:
        title = _clean_title(_TAG.sub(" ", heading.group(1)))
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    site = _clean_text(_metas(_without_hidden(page_html)).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed article.

    The record does not include the article body. ``page_url`` is the URL that
    returned HTML. A different rel=canonical is not substituted. A challenge
    page is not stored.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    if is_challenge_page(page_html):
        raise CatalogError("a challenge page is not stored")
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
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be an https distill.pub article")
    if any(mark in url for mark in ("?", "#", "\\", "@")):
        raise CatalogError(f"canonical URL must be an https distill.pub article: {url}")
    if not url.startswith("https://"):
        raise CatalogError(f"canonical URL must be an https distill.pub article: {url}")
    rest = url[len("https://") :]
    if "/" in rest:
        host, path = rest.split("/", 1)
        path = "/" + path
    else:
        host, path = rest, "/"
    if (
        not host
        or host != OFFICIAL_HOST
        or ":" in host
        or not official_distill_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or _PATH.fullmatch(path) is None
    ):
        raise CatalogError(f"canonical URL must be an https distill.pub article: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_day(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _rights_blobs(page_text: str) -> str:
    parts: list[str] = []
    for blob in _LDJSON.findall(page_text):
        for raw in _LD_LICENSE.findall(blob):
            parts.append(raw.replace("\\/", "/"))
    visible = _without_hidden(page_text)
    for tag in _HREF_TAG.findall(visible):
        href = _attrs(tag).get("href", "")
        if "creativecommons.org" in href.casefold():
            parts.append(href)
    for content in _meta_values(visible, _LICENSE_META):
        parts.append(content)
    parts.append(_plain(visible))
    return _fold("\n".join(parts))


def _fold(value: str) -> str:
    return value.casefold().translate(_DASHES)


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


def _without_hidden(page_text: str) -> str:
    without_data = _LDJSON.sub(" ", page_text)
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", without_data))


def _plain(page_text: str) -> str:
    text = unescape(_TAG.sub(" ", page_text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: str) -> str:
    return _plain(value)


def _clean_title(value: str) -> str:
    return _SITE_SUFFIX.sub("", _clean_text(value)).strip()


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


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    slash = _SLASH_DATE.match(text)
    if slash:
        text = f"{slash.group(1)}-{slash.group(2)}-{slash.group(3)}" + text[slash.end() :]
    match = _DATE_PREFIX.match(text)
    if match is None:
        return None
    value = match.group(1)
    if _DATE.fullmatch(value) is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value
