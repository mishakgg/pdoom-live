"""Metadata catalog of public CNIL pages about artificial intelligence.

Rows keep a title, publisher, canonical URL, date, and rights label. Page bodies
are not stored. A date the page does not state stays unknown. Rights stay
unknown unless that page states a reuse licence that allows copying. A public
page, a copyright notice, a link to the legal notice, or a licence mentioned
for a dataset, model, or software component is not a licence for the page.

Allowed hosts are www.cnil.fr and cnil.fr. This catalog is not a collector
and runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cnil_ai_pages"
CATALOG_FILENAME = "cnil_ai_pages.json"
RUNNER_WIRED = False
UNKNOWN_DATE = "unknown"
PUBLISHER = "Commission nationale de l'informatique et des libertés"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CC_BY_4_0 = "cc_by_4_0"
RIGHTS_CC_BY_ND_4_0 = "cc_by_nd_4_0"
RIGHTS_CC_BY_NC_ND_4_0 = "cc_by_nc_nd_4_0"
RIGHTS_LICENCE_OUVERTE = "licence_ouverte"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CC_BY_4_0,
        RIGHTS_CC_BY_ND_4_0,
        RIGHTS_CC_BY_NC_ND_4_0,
        RIGHTS_LICENCE_OUVERTE,
    }
)
OFFICIAL_HOSTS = frozenset({"www.cnil.fr", "cnil.fr"})
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
        "quotation",
        "quote",
        "text",
        "transcript",
        "transcript_text",
    }
)
_HOST_LABEL = re.compile(r"[a-z0-9-]+")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FR_DATE = re.compile(r"^(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})$")
_FR_MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_P = re.compile(r"(?is)<p\b([^>]*)>(.*?)</p>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIX = re.compile(r"(?i)\s+\|\s+CNIL\s*$")
_DOWNLOAD = re.compile(
    r"(?i)\.(?:pdf|zip|docx?|xlsx?|pptx?|csv|json|xml|jpg|jpeg|png|gif|webp|mp3|mp4|wav)$"
)
_BLOCKED_PATH = ("/admin/", "/user/", "/search/", "/node/add/", "/core/", "/comment/")
_LICENCE_NAME = (
    r"(?:"
    r"cc[-\s]?by[-\s]?nc[-\s]?nd(?:[-\s]?4\.0)?(?:\s+fr)?"
    r"|cc[-\s]?by[-\s]?nd(?:[-\s]?4\.0)?(?:\s+fr)?"
    r"|cc[-\s]?by(?:[-\s]?4\.0)?(?:\s+international)?"
    r"|ouverte"
    r"|open\s+licen[cs]e(?:\s+2\.0)?"
    r"|creative\s+commons\s+attribution\s+4\.0"
    r")"
)
_GRANT = re.compile(
    r"(?i)(?:"
    r"mis(?:es)?\s+[àa]\s+disposition\s+(?:par\s+d[ée]faut\s+)?selon\s+les\s+termes\s+de\s+(?:la\s+)?licen[cs]e\s+"
    r"|conditions\s+de\s+r[ée]utilisation\s*:\s*licen[cs]e\s+"
    r"|(?:r[ée]utilisation\s+(?:des\s+contenus\s+)?(?:est\s+)?autoris[ée]e|reuse\s+is\s+authori[sz]ed|licensed\s+under)"
    r"\s+(?:sous\s+|selon\s+|under\s+(?:the\s+)?)?(?:les\s+termes\s+de\s+)?(?:la\s+|an?\s+)?(?:licen[cs]e\s+)?"
    r")(?P<name>"
    + _LICENCE_NAME
    + r")"
)


class CatalogError(ValueError):
    """A catalog row or page failed the CNIL page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def official_cnil_host(hostname: str) -> bool:
    """True for www.cnil.fr and cnil.fr."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    labels = host.split(".")
    if any(not label or _HOST_LABEL.fullmatch(label) is None for label in labels):
        return False
    return host in OFFICIAL_HOSTS


def rights_from_page(page_text: str) -> str:
    """Return a rights label. Public availability alone stays unknown.

    The label is set only when the visible page states that its contents are
    available under a named reuse licence that allows copying. A licence named
    for someone else's dataset, model, or software does not qualify.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    match = _GRANT.search(_visible_text(page_text))
    if match is None:
        return RIGHTS_UNKNOWN
    return _rights_label(match.group("name"))


def date_from_page(page_html: str) -> str:
    """Return the publication date stated under the title, or unknown.

    CNIL prints that date in ``ctn-gen-auteur``. Dates on related-page cards
    and modification notes are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page text must be a string")
    html = _without_hidden(page_html)
    for attrs, inner in _P.findall(html):
        classes = _attrs(attrs).get("class", "").split()
        if "ctn-gen-auteur" not in classes:
            continue
        parsed = _parse_stated_date(_plain_fragment(inner))
        return parsed if parsed else UNKNOWN_DATE
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    metas = _metas(page_html)
    for key in ("og:title", "citation_title", "dcterms.title"):
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    heading = _H1.search(page_html)
    if heading:
        title = _clean_title(heading.group(1))
        if title:
            return title
    title_tag = _TITLE.search(page_html)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if title:
            return title
    raise CatalogError("title is required")


def canonical_url_from_page(page_html: str, *, page_url: str) -> str:
    """Use rel=canonical when it is an official CNIL page, else the fetched URL."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for tag in _LINK.findall(page_html):
        attrs = _attrs(tag)
        if "canonical" not in attrs.get("rel", "").lower().split():
            continue
        href = attrs.get("href", "").strip()
        if not href:
            continue
        candidate = urljoin(page_url, href)
        if _is_official_url(candidate):
            return validate_canonical_url(candidate)
        break
    return validate_canonical_url(page_url)


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed CNIL page.

    The record does not include the document body. A page that does not state
    a publication date gets date unknown. Rights stay unknown unless the page
    states a reuse licence that allows copying.
    """

    record = {
        "title": title_from_page(page_html),
        "publisher": PUBLISHER,
        "canonical_url": canonical_url_from_page(page_html, page_url=page_url),
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
    if not isinstance(entries, list) or not entries:
        raise CatalogError("entries must be a non-empty list")
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
    if entry["publisher"] != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry["canonical_url"])
    validate_date(entry["date"])
    if entry["rights"] not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or unknown: {entry['rights']}")
    return entry


def validate_canonical_url(url: object) -> str:
    if not _is_official_url(url):
        raise CatalogError(f"canonical URL must be an official CNIL https page: {url}")
    return str(url)


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE!r}")
    return value


def _is_official_url(url: object) -> bool:
    if not isinstance(url, str) or not url or url != url.strip():
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or not official_cnil_host(host)
        or ".." in path
        or "\\" in path
        or "//" in path
    ):
        return False
    return _official_path(path)


def _official_path(path: str) -> bool:
    if not (path.startswith("/fr/") or path.startswith("/en/")):
        return False
    if path.rstrip("/") in {"/fr", "/en"}:
        return False
    lowered = path.lower()
    if _DOWNLOAD.search(path) or "/sites/default/files/" in lowered:
        return False
    return not any(bit in lowered for bit in _BLOCKED_PATH)


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


def _rights_label(name: str) -> str:
    compact = re.sub(r"\s+", "-", name.casefold())
    if "ouverte" in compact or compact.startswith("open-licen"):
        return RIGHTS_LICENCE_OUVERTE
    if "creative-commons-attribution" in compact:
        return RIGHTS_CC_BY_4_0
    code = re.sub(r"[^a-z0-9]", "", compact)
    if "ccbyncnd" in code:
        return RIGHTS_CC_BY_NC_ND_4_0
    if "ccbynd" in code:
        return RIGHTS_CC_BY_ND_4_0
    if code.startswith("ccby") and "nc" not in code and "nd" not in code and "sa" not in code:
        return RIGHTS_CC_BY_4_0
    return RIGHTS_UNKNOWN


def _parse_stated_date(value: str) -> str | None:
    text = re.sub(r"\s+", " ", value).strip()
    if _DATE.fullmatch(text) and _iso_date(text):
        return text
    match = _FR_DATE.fullmatch(text)
    if match is None:
        return None
    month = _FR_MONTHS.get(match.group(2).casefold())
    if month is None:
        return None
    try:
        found = date(int(match.group(3)), month, int(match.group(1)))
    except ValueError:
        return None
    return found.isoformat()


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _without_hidden(page_text: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_text))


def _visible_text(page_text: str) -> str:
    text = _TAG.sub(" ", _without_hidden(page_text))
    text = unescape(text)
    text = (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


def _plain_fragment(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(value: str) -> str:
    text = _plain_fragment(value)
    return _SITE_SUFFIX.sub("", text).strip()


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    visible = _without_hidden(page_html)
    for tag in _META.findall(visible):
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
