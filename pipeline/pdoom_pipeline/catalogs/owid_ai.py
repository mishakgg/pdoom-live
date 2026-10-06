"""Metadata catalog of public Our World in Data pages about artificial intelligence.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page bodies, abstracts,
chart data, CSV downloads, and Grapher payloads are not stored. A Cloudflare
challenge, a captcha, an HTTP 202, an Akamai 403, a robots disallow, a
non-HTML response, or an off-host redirect is not stored, so the catalog may
be empty. Rights stay unknown unless the page states a reuse licence.
``creative_commons`` means only a stated CC0, CC BY, or CC BY-SA deed, and
only when the page does not also state a restricted deed. CC BY-NC, CC BY-ND,
CC BY-NC-SA, and CC BY-NC-ND stay unknown. A hyphen is a word boundary, so
CC BY does not match CC BY-NC, and licenses/by does not match licenses/by-nc.
A generic creativecommons.org/licenses/ URL is not a permissive deed. The
Public Domain Mark is not CC0. A copyright notice, All rights reserved, or a
terms link is not a licence. Updated, modified, and copyright years are not
publication dates. A missing date stays unknown. The live URL is stored as
confirmed; a different rel=canonical does not replace it. This module does
not fetch and it is not a belief collector. runner_wired stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "owid_ai_pages"
CATALOG_FILENAME = "owid_ai_pages.json"
PUBLISHER = "Our World in Data"
OWID_HOST = "ourworldindata.org"
RUNNER_WIRED = False
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_UNKNOWN = "unknown"
ALLOWED_RIGHTS = frozenset({RIGHTS_CREATIVE_COMMONS, RIGHTS_UNKNOWN})
UNKNOWN_DATE = "unknown"
MAX_TEXT_CHARS = 400
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
        "csv",
        "download",
        "excerpt",
        "full_text",
        "grapher",
        "html",
        "page",
        "page_text",
        "payload",
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
_SLASH_DATE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})\b")
_HIDDEN = re.compile(r"(?is)<!--.*?-->|<(script|style|noscript|svg)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"([^"]*)"')
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
)
_LICENSE_META = frozenset({"license", "dcterms.license", "dc.rights", "dcterms.rights"})
_SITE_SUFFIXES = (
    " | Our World in Data",
    " - Our World in Data",
    " – Our World in Data",
    " — Our World in Data",
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "cf-mitigated",
    "checking your browser",
    "cdn-cgi/challenge",
    "attention required",
    "sorry, you have been blocked",
    "access denied",
    "hcaptcha",
    "g-recaptcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "errors.edgesuite.net",
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".epub",
    ".gif",
    ".gz",
    ".jpeg",
    ".jpg",
    ".json",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_BLOCKED_PREFIXES = ("/grapher", "/api", "/assets", "/cdn-cgi", "/explorers", "/fonts", "/uploads")
# artificial-intelligence, generative-ai, or ai as its own hyphen or slash token.
_AI_TOKEN = re.compile(
    r"(?:artificial-intelligence|generative-ai|(?:^|/)ai(?:[-/]|$)|(?:^|-)ai(?:[-/]|$))"
)
_PATH_CHARS = re.compile(r"/[a-z0-9/-]+")
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
# Longer deeds are listed first. A hyphen is a word boundary, so a bare
# boundary after BY would also match BY-NC. The CC BY pattern therefore
# refuses a following NC, ND, or SA token, and licenses/by refuses by-nc.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?![a-z0-9-])"
    r"|publicdomain/(?P<pd>zero|mark)(?![a-z0-9-]))"
)
_CC_TEXT = (
    ("by-nc-nd", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    ("by-nc-sa", re.compile(r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    ("by-nc", re.compile(r"\bcc[\s-]*by[\s-]*nc\b")),
    ("by-nd", re.compile(r"\bcc[\s-]*by[\s-]*nd\b")),
    ("by-sa", re.compile(r"\bcc[\s-]*by[\s-]*sa\b")),
    (
        "zero",
        re.compile(
            r"\bcc0\b|\bcc[\s-]*zero\b|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    ("by", re.compile(r"\bcc[\s-]*by\b(?![\s-]*(?:nc|nd|sa)\b)")),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    ),
    (
        "by-nc-sa",
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    ),
    ("by-nc", re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial\b")),
    ("by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike\b")),
    (
        "by",
        re.compile(
            r"creative commons attribution\b"
            r"(?![\s-]*(?:share[\s-]*alike|non[\s-]*commercial|no[\s-]*deriv|nc|nd|sa)\b)"
        ),
    ),
    ("by-nc", re.compile(r"creative commons by\b(?=[\s-]*(?:nc)\b)")),
    ("by-nd", re.compile(r"creative commons by\b(?=[\s-]*(?:nd)\b)")),
    ("by-sa", re.compile(r"creative commons by\b(?=[\s-]*sa\b)")),
    ("by", re.compile(r"creative commons by\b(?![\s-]*(?:nc|nd|sa)\b)")),
    ("mark", re.compile(r"public domain mark\b")),
)
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd", "mark"})
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_LICENSE_KEYS = frozenset({"license", "licence"})


class CatalogError(ValueError):
    """A catalog row or page failed the Our World in Data AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
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
    return document


def validate_entry(entry: dict) -> dict:
    if not isinstance(entry, dict):
        raise CatalogError("entry must be an object")
    _reject_stored_body(entry, path="entry")
    if set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    _require_text(entry.get("publisher"), "publisher", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    rights = entry.get("rights")
    if rights not in ALLOWED_RIGHTS:
        raise CatalogError(f"rights must be {RIGHTS_CREATIVE_COMMONS} or {RIGHTS_UNKNOWN}")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip():
        raise CatalogError("canonical URL must be a public Our World in Data AI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != OWID_HOST
        or host != OWID_HOST
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
        or not _ai_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Our World in Data AI page: {url}")
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host == OWID_HOST and not hostname_is_blocked(host)


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial challenge rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    head = sample[:4000]
    title_match = _TITLE.search(sample)
    title = _plain(title_match.group(1)).casefold() if title_match else ""
    return any(marker in head or marker in title for marker in _CHALLENGE_MARKERS)


def robots_allows_path(robots_text: str, path: str, user_agent: str = "pdoom.live-collector") -> bool:
    """True when robots.txt does not disallow path for this collector.

    A challenge page served in place of robots.txt does not allow a fetch.
    """

    if not isinstance(robots_text, str):
        return False
    sample = robots_text[:800].casefold()
    if "<html" in sample or any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
    groups = _robots_groups(robots_text)
    if not groups:
        return True
    rules = _matching_rules(groups, user_agent)
    if rules is None:
        return True
    return _path_allowed(rules, path or "/")


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
    requested_urls: list[str] | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a block or challenge.

    HTTP 202, Akamai 403, other non-200 statuses, captcha pages, Cloudflare
    challenges, and redirects that leave ourworldindata.org are not stored.
    """

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers and _blocked_headers(headers):
        return False
    urls = list(requested_urls or [])
    if final_url:
        urls.append(final_url)
    for url in urls:
        if not _on_catalog_host(url):
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
    requested_urls: list[str] | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when one bounded GET confirmed an Our World in Data AI page.

    A Cloudflare challenge, a captcha, an HTTP 202, an Akamai 403, a robots
    disallow, a non-HTML body, or an off-host redirect is not stored.
    """

    if robots_text is not None:
        path = urlparse(page_url).path or "/"
        if not robots_allows_path(robots_text, path):
            return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=final_url,
        requested_urls=requested_urls,
    ):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=page_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons`` means CC0, CC BY, or CC BY-SA only, and only when no
    restricted deed is also stated. A hyphen is a word boundary, so CC BY does
    not match CC BY-NC and licenses/by does not match licenses/by-nc. The
    Public Domain Mark is not CC0. A generic creativecommons.org/licenses/ URL,
    a copyright notice, All rights reserved, and a terms link are not licences.
    Script and style text does not count. Restricted deeds win when both appear.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes: set[str] = set()
    for raw in _jsonld_licenses(page_text):
        codes.update(_cc_codes(raw))
    visible = _HIDDEN.sub(" ", page_text)
    codes.update(_cc_codes(_plain(visible)))
    for href in _hrefs(visible):
        codes.update(_cc_codes(href))
    for raw in _meta_values(visible, _LICENSE_META):
        codes.update(_cc_codes(raw))
    if codes & _RESTRICTED:
        return RIGHTS_UNKNOWN
    if codes & _PERMISSIVE:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, updatedAt, a last-updated line, and
    a copyright year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    for raw in _jsonld_published(page_html):
        found = _flexible_date(raw)
        if found:
            return found
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in _PUBLICATION_DATE_KEYS:
        raw = metas.get(key)
        if not isinstance(raw, str):
            continue
        found = _flexible_date(raw)
        if found:
            return found
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _HIDDEN.sub(" ", page_html)
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "twitter:title"):
        title = _clean_title(metas.get(key, ""))
        if _usable_title(title):
            return title
    for inner in _H1.findall(visible):
        title = _clean_title(inner)
        if _usable_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(title_tag.group(1))
        if _usable_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str, *, page_url: str) -> str:
    """Return Our World in Data when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    validate_canonical_url(page_url)
    visible = _HIDDEN.sub(" ", page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site.casefold() == PUBLISHER.casefold():
        return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body, chart data, or a Grapher
    payload. ``page_url`` is the live URL that was fetched. A rel=canonical
    pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html, page_url=page_url),
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
        declared = validate_canonical_url(_resolve(live, href.strip()))
    except CatalogError:
        return live
    if declared == live:
        return declared
    return live


def _ai_path(path: str) -> bool:
    if path in {"", "/"} or path != path.lower() or not path.startswith("/") or path.endswith("/"):
        return False
    if ".." in path or "\\" in path or "//" in path or "%" in path:
        return False
    if _PATH_CHARS.fullmatch(path) is None:
        return False
    if any(path == prefix or path.startswith(prefix + "/") for prefix in _BLOCKED_PREFIXES):
        return False
    if path.endswith(_DOWNLOAD_SUFFIXES):
        return False
    return _AI_TOKEN.search(path) is not None


def _on_catalog_host(url: str) -> bool:
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and is_official_host(host)


def _blocked_headers(headers: dict[str, str]) -> bool:
    """True for a Cloudflare or captcha challenge header.

    An Akamai 403 is omitted by status before this check. A 200 response is
    not dropped only because a header name mentions Akamai.
    """

    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name in {"sg-captcha", "x-captcha"} and token:
            return True
    return False


def _cc_codes(value: str) -> set[str]:
    folded = _fold(value)
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("license") or match.group("pd")
        if code:
            codes.add(code)
    for code, pattern in _CC_TEXT:
        if pattern.search(folded):
            codes.add(code)
    return codes


def _jsonld_licenses(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        text = blob.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            found.extend(raw.replace("\\/", "/") for raw in _LD_LICENSE.findall(text))
            continue
        _collect_licenses(payload, found)
    return found


def _collect_licenses(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_licenses(item, found)
        return
    if not isinstance(payload, dict):
        return
    for key, value in payload.items():
        if str(key).casefold() in _LICENSE_KEYS:
            if isinstance(value, str):
                found.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        found.append(item)
                    else:
                        _collect_licenses(item, found)
            else:
                _collect_licenses(value, found)
            continue
        _collect_licenses(value, found)


def _jsonld_published(page_html: str) -> list[str]:
    found: list[str] = []
    for blob in _LDJSON.findall(page_html):
        text = blob.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        _collect_published(payload, found)
    return found


def _collect_published(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_published(item, found)
        return
    if not isinstance(payload, dict):
        return
    published = payload.get("datePublished")
    if isinstance(published, str):
        found.append(published)
    for key, value in payload.items():
        if key in {"datePublished", "dateModified", "dateCreated", "uploadDate"}:
            continue
        _collect_published(value, found)


def _flexible_date(raw: str) -> str:
    text = raw.strip()
    match = _DATE_PREFIX.match(text)
    if match and _iso_date(match.group(1)):
        return match.group(1)
    slash = _SLASH_DATE.match(text)
    if slash:
        candidate = f"{slash.group(1)}-{slash.group(2)}-{slash.group(3)}"
        if _iso_date(candidate):
            return candidate
    return ""


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _robots_groups(text: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw_line in text.splitlines():
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
    return groups


def _matching_rules(
    groups: list[tuple[list[str], list[tuple[str, str]]]],
    user_agent: str,
) -> list[tuple[str, str]] | None:
    product = (user_agent or "").split("/", 1)[0].strip().lower()
    haystack = (user_agent or "").strip().lower()
    specific: list[tuple[int, list[tuple[str, str]]]] = []
    wildcard: list[tuple[str, str]] | None = None
    for agents, rules in groups:
        for agent in agents:
            if agent == "*":
                wildcard = rules
                continue
            if product.startswith(agent) or (haystack.startswith(agent) and agent):
                specific.append((len(agent), rules))
    if specific:
        return max(specific, key=lambda item: item[0])[1]
    return wildcard


def _path_allowed(rules: list[tuple[str, str]], path: str) -> bool:
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix or not path.startswith(prefix):
            continue
        if kind == "allow":
            allowed = max(allowed, len(prefix))
        else:
            disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _resolve(page_url: str, href: str) -> str:
    target = unescape(href).strip()
    if target.startswith("https://") or target.startswith("http://"):
        return target
    if target.startswith("/") and not target.startswith("//"):
        return f"https://{OWID_HOST}{target}"
    base = page_url.rsplit("/", 1)[0]
    return f"{base}/{target}"


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{field} is required")
    if value != value.strip():
        raise CatalogError(f"{field} must not have surrounding whitespace")
    if len(value) > max_length or "<" in value or ">" in value:
        raise CatalogError(f"{field} is too long to store" if len(value) > max_length else f"{field} must be plain text")


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


def _usable_title(title: str) -> bool:
    if not title or title.casefold() == PUBLISHER.casefold():
        return False
    return len(title) <= MAX_TEXT_CHARS and "<" not in title and ">" not in title


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    for suffix in _SITE_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(_HIDDEN.sub(" ", page_text))


def _fold(value: str) -> str:
    text = unescape(value).casefold().replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text)


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(html: str, names: frozenset[str]) -> list[str]:
    metas = _metas(html)
    return [metas[name] for name in names if name in metas and metas[name]]


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _ANCHOR.findall(page_html) + _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _canonical_href(page_html: str) -> str:
    visible = _HIDDEN.sub(" ", page_html)
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        rel = {part.casefold() for part in attrs.get("rel", "").split()}
        if "canonical" in rel and attrs.get("href"):
            return attrs["href"]
    return ""
