"""Metadata catalog of public Conjecture pages on the official host.

The official host is www.conjecture.dev. conjecture.dev redirects there, and
canonical links use the www host. Rows keep a title, publisher, canonical URL,
date, and rights label. Page bodies are not stored. A date the page does not
state stays unknown. Updated, modified, and copyright years are not publication
dates. Rights stay unknown unless the page states CC0, CC BY, or CC BY-SA and
does not also state a restricted deed. CC BY-NC, CC BY-ND, CC BY-NC-SA, and
CC BY-NC-ND stay unknown. A hyphen continues a licence token, so CC BY does not
match CC BY-NC. Public Domain Mark is not CC0. mit and apache-2.0 stay their
own tokens. A public page, a copyright notice, or a terms link is not a
licence. This catalog is not a collector and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "conjecture_pages"
CATALOG_FILENAME = "conjecture_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_LABELS = frozenset(
    {RIGHTS_UNKNOWN, RIGHTS_CREATIVE_COMMONS, RIGHTS_MIT, RIGHTS_APACHE}
)
OFFICIAL_HOST = "www.conjecture.dev"
PUBLISHER = "Conjecture"
MAX_FIELD_CHARS = 400
MAX_DESCRIPTION_CHARS = 800

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
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
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_PUBLISHED_META = frozenset({"article:published_time", "citation_publication_date", "citation_date"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-browser-verification",
    "checking your browser",
    "attention required",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SLASH_DATE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})")
_URL = re.compile(
    r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*)://(?P<authority>[^/?#]*)(?P<path>/[^?#]*)?(?:\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?$"
)
_SEGMENT = re.compile(r"^[a-z0-9](?:[a-z0-9()-]*[a-z0-9)])?$")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"license"\s*:\s*"(.*?)"')
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_H2 = re.compile(r"(?is)<h2\b[^>]*>(.*?)</h2>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_LATEST = re.compile(r"(?is)<h[1-6]\b[^>]*>\s*Latest Articles\s*</h[1-6]>")
_FRAMER_NAME = re.compile(r"""(?i)data-framer-name\s*=\s*["']([^"']+)["']""")
_DATE_P = re.compile(r"(?is)<p\b[^>]*>(.*?)</p>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s+[-|–—]\s*conjecture\s*$")
_CHROME_TITLES = frozenset({"company", "resources"})
_NON_DATE_LABEL = re.compile(r"(?i)\b(?:updated|modified|copyright)\b|©")
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_HEADER_DATE = re.compile(
    r"(?i)^(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
    r"sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2}),\s+(\d{4})$"
)
# A hyphen continues the token. CC BY must not match inside CC BY-NC or CC BY-SA.
_TOKEN_END = r"(?![\w-])"
_CC_TEXT = (
    ("by-nc-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nc[\s-]+nd{_TOKEN_END}")),
    ("by-nc-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nc[\s-]+sa{_TOKEN_END}")),
    ("by-nd", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nd{_TOKEN_END}")),
    ("by-nc", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+nc{_TOKEN_END}")),
    ("by-sa", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]+by[\s-]+sa{_TOKEN_END}")),
    (
        "by",
        re.compile(
            rf"(?i)(?<![a-z0-9])cc[\s-]+by(?![\s-]*(?:nc|nd|sa){_TOKEN_END}){_TOKEN_END}"
        ),
    ),
    ("zero", re.compile(rf"(?i)(?<![a-z0-9])cc[\s-]*0{_TOKEN_END}")),
)
_CC_URL = re.compile(
    r"(?i)creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?=/|[?#]|$)"
)
_PERMISSIVE_CC = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_CC = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_MIT = re.compile(rf"(?i)licen[cs]ed under (?:the )?mit licen[cs]e{_TOKEN_END}")
_APACHE = re.compile(rf"(?i)licen[cs]ed under (?:the )?apache licen[cs]e\s*2\.0{_TOKEN_END}")
_EXACT_TOKENS = {"mit": RIGHTS_MIT, "apache-2.0": RIGHTS_APACHE}


class CatalogError(ValueError):
    """A catalog row or page failed the Conjecture page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_conjecture_host(hostname: str) -> bool:
    """True only for the official www.conjecture.dev host."""
    host = (hostname or "").strip().lower()
    if host.endswith("."):
        host = host[:-1]
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host == OFFICIAL_HOST


def response_confirms_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict | None = None,
) -> bool:
    """True when one response is the page HTML rather than a block or challenge."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not _html_content_type(content_type):
        return False
    if _challenge(page_html, headers):
        return False
    return True


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    ``creative_commons`` is only CC0, CC BY, or CC BY-SA, and only when the page
    does not also state a restricted deed. A by-nc URL stays unknown even when
    the anchor text says CC BY. mit and apache-2.0 are not folded into
    ``creative_commons``.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_hidden(page_text)
    plain = _plain(visible)
    pieces = [plain, *_hrefs(visible), *_meta_values(visible, _LICENSE_META)]
    for blob in _LDJSON.findall(page_text):
        pieces.extend(raw.replace("\\/", "/") for raw in _LD_LICENSE.findall(blob))
    blob = _fold("\n".join(pieces))
    codes = _cc_codes(blob)
    named = _named_tokens(blob)
    if codes & _RESTRICTED_CC:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE_CC:
        if named:
            return RIGHTS_UNKNOWN
        return RIGHTS_CREATIVE_COMMONS
    if named == {RIGHTS_MIT}:
        return RIGHTS_MIT
    if named == {RIGHTS_APACHE}:
        return RIGHTS_APACHE
    return RIGHTS_UNKNOWN


def date_from_page(page_text: str) -> str:
    """Use a stated publication date. Updated, modified, and copyright years stay unknown."""

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    for blob in _LDJSON.findall(page_text):
        for raw in _DATE_PUBLISHED.findall(blob):
            parsed = _iso_day(raw)
            if parsed:
                return parsed
    for raw in _meta_values(page_text, _PUBLISHED_META):
        parsed = _iso_day(raw)
        if parsed:
            return parsed
    header = _header_date(_without_hidden(page_text))
    if header:
        return header
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
    for inner in _H1.findall(visible):
        title = _clean_title(_plain(inner))
        if _usable_title(title):
            return title
    for inner in _H2.findall(visible):
        title = _clean_title(_plain(inner))
        if _usable_title(title):
            return title
    found = _TITLE.search(visible)
    if found:
        title = _clean_title(_plain(found.group(1)))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    site = _clean_title(metas.get("og:site_name", ""))
    if site and site.casefold() != PUBLISHER.casefold():
        raise CatalogError(f"publisher must be {PUBLISHER}")
    blob = " ".join(
        (
            site,
            metas.get("og:title", ""),
            _plain(_TITLE.search(visible).group(1) if _TITLE.search(visible) else ""),
        )
    ).casefold()
    if "conjecture" not in blob:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    return PUBLISHER


def metadata_from_page(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that was fetched. A rel=canonical on another path is not substituted.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    return {
        "title": title_from_page(page_html),
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
        declared = validate_canonical_url(_absolute(live, href.strip()))
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
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be an https www.conjecture.dev page")
    match = _URL.fullmatch(url)
    if match is None:
        raise CatalogError(f"canonical URL must be an https www.conjecture.dev page: {url}")
    scheme = match.group("scheme")
    authority = match.group("authority") or ""
    path = match.group("path") or ""
    if (
        scheme != "https"
        or authority != OFFICIAL_HOST
        or not official_conjecture_host(authority)
        or match.group("query") is not None
        or match.group("fragment") is not None
        or "@" in authority
        or ":" in authority
        or not path.startswith("/")
        or ".." in path
        or "\\" in path
        or "//" in path
        or "%" in path
        or (path != "/" and path.endswith("/"))
        or not _path_segments(path)
    ):
        raise CatalogError(f"canonical URL must be an https www.conjecture.dev page: {url}")
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
    left_match = _URL.fullmatch(left)
    right_match = _URL.fullmatch(right)
    if left_match is None or right_match is None:
        return False
    return left_match.group("authority") == right_match.group("authority") and (
        (left_match.group("path") or "/").rstrip("/") == (right_match.group("path") or "/").rstrip("/")
    )


def _absolute(base: str, href: str) -> str:
    if href.startswith("https://") or href.startswith("http://"):
        return href
    slash = base.find("/", len("https://"))
    origin = base if slash == -1 else base[:slash]
    if href.startswith("/"):
        return origin + href
    return origin + "/" + href


def _path_segments(path: str) -> bool:
    if path == "/":
        return True
    parts = path.split("/")
    if parts[0] != "" or any(part == "" for part in parts[1:]):
        return False
    return all(_SEGMENT.fullmatch(part) is not None for part in parts[1:])


def _html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    return content_type.split(";", 1)[0].strip().casefold() in _HTML_TYPES


def _challenge(page_html: str, headers: dict | None) -> bool:
    lowered = page_html.casefold()
    if any(marker in lowered for marker in _CHALLENGE_MARKERS):
        return True
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


def _fold(value: str) -> str:
    return (
        value.casefold()
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )


def _clean_title(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"\s+", " ", text).strip()
    return _SITE_SUFFIX.sub("", text).strip()


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    if title.casefold() in _CHROME_TITLES:
        return False
    return len(title) <= MAX_FIELD_CHARS and "<" not in title and ">" not in title


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
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            hrefs.append(href)
    return hrefs


def _cc_codes(blob: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(blob):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(blob):
            codes.add(code)
    if re.search(r"public\s+domain\s+mark", blob):
        codes.add("mark")
    if re.search(r"creative\s+commons\s+(?:public\s+domain\s+)?zero\b|\bcc\s+zero\b", blob):
        codes.add("zero")
    if "creative commons" not in blob:
        return codes
    noncommercial = re.search(r"non[\s-]?commercial", blob) is not None
    noderiv = re.search(r"no[\s-]?deriv", blob) is not None
    sharealike = re.search(r"share[\s-]?alike", blob) is not None
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
    elif re.search(r"\battribution\b", blob):
        codes.add("by")
    return codes


def _named_tokens(blob: str) -> set[str]:
    found: set[str] = set()
    if _MIT.search(blob):
        found.add(RIGHTS_MIT)
    if _APACHE.search(blob):
        found.add(RIGHTS_APACHE)
    for line in blob.splitlines():
        token = line.strip().casefold()
        if token in _EXACT_TOKENS:
            found.add(_EXACT_TOKENS[token])
    return found


def _header_date(visible: str) -> str | None:
    latest = _LATEST.search(visible)
    head = visible[: latest.start()] if latest else visible
    for marker in _FRAMER_NAME.finditer(head):
        if marker.group(1).casefold() != "date":
            continue
        window = head[max(0, marker.start() - 1200) : marker.start()]
        names = [item.group(1).casefold() for item in _FRAMER_NAME.finditer(window)]
        if not names or names[-1] != "author":
            continue
        paragraph = _DATE_P.search(head[marker.end() : marker.end() + 700])
        if paragraph is None:
            continue
        text = _plain(paragraph.group(1))
        if _NON_DATE_LABEL.search(text):
            continue
        parsed = _month_date(text) or (_iso_date(text) and text)
        if parsed:
            return parsed
    return None


def _month_date(value: str) -> str | None:
    match = _HEADER_DATE.fullmatch(value.strip())
    if match is None:
        return None
    month = _MONTHS.get(match.group(1).casefold())
    if month is None:
        return None
    iso = f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(2)):02d}"
    if not _iso_date(iso):
        return None
    return iso


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    slash = _SLASH_DATE.match(text)
    if slash:
        text = f"{slash.group(1)}-{slash.group(2)}-{slash.group(3)}" + text[slash.end() :]
    match = _DATE_PREFIX.match(text)
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
