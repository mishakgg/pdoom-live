"""Metadata catalog of public Technology Innovation Institute AI pages.

The official hosts are www.tii.ae and tii.ae. tii.ae redirects to www.tii.ae,
and that final URL is stored when it stays on www.tii.ae. Other hosts,
including falconllm.tii.ae, are omitted. robots.txt on www.tii.ae is plain
text and allows the public AI research, model, news, and program paths.
An HTML document served in place of robots.txt does not allow a fetch. A
robots disallow is not fetched. Each stored URL was confirmed with one
bounded GET: 12 second timeout, at most 3 redirects, and at most 2000000
bytes. A Cloudflare challenge, a captcha, an authentication wall, a
non-HTML shell, an HTTP error, or a redirect off these hosts is not stored.
An empty entries list is valid.

Rows keep a title, publisher, canonical URL, publication date, and rights
label. Page text, abstracts, quotes, transcripts, PDFs, model weights, and
chart data are not stored. The live URL is stored as confirmed; a different
rel=canonical does not replace it. Publisher is Technology Innovation Institute.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution means CC BY alone, including a specific
/licenses/by/4.0/ URL. creative_commons means CC0, CC BY-SA, or a permissive
mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps
cc_by_nc, cc_by_nd, cc_by_nc_sa, or cc_by_nc_nd. Mixed restricted and
permissive text stays unknown. A CC BY or CC BY-SA anchor on a by-nc, by-nd,
by-nc-sa, by-nc-nd, or publicdomain/mark URL stays unknown. A CC0 anchor on a
publicdomain/mark URL stays unknown. A generic
https://creativecommons.org/licenses or /licenses URL is not a deed. Anchor
text on it, including CC BY, CC BY 4.0, and CC BY-SA, stays unknown. The same
rule covers a missing slash, http, a www host, and a query string. A specific
deed URL still counts. Text elsewhere on the page still counts. A software
licence beside any Creative Commons deed stays unknown. Two software licences
stay unknown. Two different restricted deeds stay unknown. mit, apache-2.0,
and mpl-2.0 are sole software licences. Bare MIT stays unknown. Licensed
under the MIT License is mit. Apache License, Version 2.0, including the
comma, is apache-2.0. The institute's own model or dataset licence stated on
the page may be recorded when it is one of those sole software licences. A
photo credit, caption credit, or image credit that names someone else's
licence stays unknown, including Photo credit: UNDRR, CC BY-NC-ND 2.0 and
Photo: UNDRR, CC BY-NC-ND 2.0. uk_ogl requires the British phrase Open
Government Licence. Open Government License stays unknown. us_government_work
comes only from an explicit rights metadata field. Script, style, and comment
text does not count.

Updated, modified, and copyright years are not publication dates. A missing
date stays unknown. This module does not fetch and it is not a belief
collector. runner_wired stays false.
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

CATALOG_ID = "tii_pages"
CATALOG_FILENAME = "tii_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Technology Innovation Institute"
FETCH_TIMEOUT_SECONDS = 12
FETCH_MAX_REDIRECTS = 3
FETCH_MAX_BYTES = 2_000_000
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
UNKNOWN_DATE = "unknown"
OFFICIAL_HOST = "www.tii.ae"
APEX_HOST = "tii.ae"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST, APEX_HOST})
OGL_PHRASE = "open government licence"
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Metadata for public Technology Innovation Institute AI research, model, news, and program "
    "HTML pages on www.tii.ae and tii.ae. Each URL was one bounded GET (12s, 3 redirects, "
    "2000000 bytes) that stayed on those hosts. robots.txt allows these paths. An HTML "
    "document in place of robots.txt does not allow a fetch. Challenges, captchas, login walls, "
    "non-HTML shells, robots disallows, and off-host redirects are omitted. Other centers, PDFs, and "
    "model weights are omitted. Rows store title, publisher, canonical URL, date, "
    "and rights. Page text is not stored. creative_commons_attribution is CC BY alone. "
    "creative_commons is CC0, CC BY-SA, or a permissive mix. A missing date is unknown. "
    "Updated, modified, and copyright years are not publication dates. Not a belief collector. "
    "runner_wired is false."
)

_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_DOCUMENT_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_SEGMENT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PAGE_SECTIONS = frozenset(
    {
        "news",
        "article",
        "model",
        "models",
        "program",
        "programs",
        "programme",
        "programmes",
    }
)
_AI_TOKENS = frozenset({"ai", "falcon", "llm", "llms", "nlp", "genai", "noor"})
_AI_PHRASES = (
    "artificial-intelligence",
    "machine-learning",
    "deep-learning",
    "language-model",
    "large-language",
    "foundation-model",
)
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_HIDDEN = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_DATE_PUBLISHED = re.compile(r'"datePublished"\s*:\s*"([^"]*)"')
_LD_LICENSE = re.compile(r'"(?:license|licence)"\s*:\s*"(.*?)"', re.I)
_LD_RIGHTS = re.compile(r'"rights"\s*:\s*"(.*?)"', re.I)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>")
_FULL_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>.*?</a>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_SN_DATE = re.compile(r"(?is)<span\b[^>]*\bsn-date\b[^>]*>(.*?)</span>")
_RIGHTS_ELEMENT = re.compile(r"(?is)<(span|div|p|dd|li|td|section)\b([^>]*)>(.*?)</\1>")
_CREDIT_BLOCK = re.compile(r"(?is)<(p|li|figcaption|td|dd|figure)\b([^>]*)>(.*?)</\1>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_PUBLICATION_DATE_KEYS = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.created",
    "dcterms.issued",
    "news_pubdate",
)
_TITLE_KEYS = ("og:title", "citation_title", "dcterms.title")
_PUBLISHER_KEYS = ("og:site_name", "citation_publisher", "dcterms.publisher")
_SITE_SUFFIXES = (
    " | Technology Innovation Institute(TII)",
    " | Technology Innovation Institute (TII)",
    " | Technology Innovation Institute",
    " - Technology Innovation Institute(TII)",
    " - Technology Innovation Institute",
    " – Technology Innovation Institute",
    " — Technology Innovation Institute",
    " | TII UAE",
    " | TII",
    " | AIDRC",
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
    ".bin",
    ".safetensors",
    ".gguf",
    ".pt",
    ".pth",
    ".onnx",
    ".ckpt",
    ".h5",
    ".msgpack",
)
_EXCLUDED_PARTS = frozenset(
    {
        "account",
        "auth",
        "bin",
        "cdn-cgi",
        "login",
        "sign-in",
        "sign-up",
        "signin",
        "signup",
        "wp-admin",
        "wp-content",
        "wp-includes",
    }
)
_HEAD_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "checking your browser",
    "cf-browser-verification",
    "attention required! | cloudflare",
)
_ANYWHERE_MARKERS = (
    "sg-captcha",
    "sgcaptcha",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge-platform",
    "hcaptcha",
    "g-recaptcha",
    "are you a robot",
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
# Longer deeds are listed first. (?!-) makes a hyphen a token boundary, so
# CC BY does not match CC BY-NC and licenses/by does not match licenses/by-nc.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<license>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)(?!-)"
    r"|publicdomain/(?P<pd>zero|mark)(?!-))"
    r"(?![a-z0-9])"
)
_TEXT_DEEDS = (
    (
        "cc-by-nc-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*nd\b"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc[\s-]*sa\b"
            r"|creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nc\b(?!-)"
            r"|creative commons attribution[\s-]*non[\s-]*commercial\b(?!-)"
            r"|\bcc[\s-]*by[\s-]*non[\s-]*commercial\b(?!-)"
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"\bcc[\s-]*by[\s-]*nd\b(?!-)"
            r"|creative commons attribution[\s-]*no[\s-]*deriv"
            r"|\bcc[\s-]*by[\s-]*noderiv"
        ),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"\bcc[\s-]*by[\s-]*sa\b(?!-)"
            r"|creative commons attribution[\s-]*share[\s-]*alike"
        ),
    ),
    (
        "cc0",
        re.compile(r"\bcc[\s-]*0\b|\bcc0\b|\bcc[\s-]*zero\b|creative commons zero\b"),
    ),
    (
        "cc-by",
        re.compile(
            r"\bcc[\s-]*by\b(?!-)"
            r"|creative commons attribution\b(?!-)"
        ),
    ),
)
_PERMISSIVE = frozenset({"cc0", "cc-by", "cc-by-sa"})
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-nd", "cc-by-nc-sa"})
_RESTRICTED_TOKENS = {
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
}
# "modified MIT" is not the MIT licence. The lookbehind is applied after casefold.
_MIT_TEXT = re.compile(r"(?<!modified )(?:\bmit license\b|\blicensed under (?:the )?mit\b(?!-))")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
# The comma in "Apache License, Version 2.0" is part of the licence name.
_APACHE_TEXT = re.compile(
    r"\bapache[\s-]*2\.0\b|\bapache license,?\s*(?:version\s+)?2(?:\.0)?\b"
)
_APACHE_URL = re.compile(r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])")
_MPL_TEXT = re.compile(r"\bmpl[\s-]*2\.0\b|\bmozilla public license(?:[\s-]*version)?[\s-]*2(?:\.0)?\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_SOFTWARE = (
    ("mit", _MIT_TEXT, _MIT_URL),
    ("apache-2.0", _APACHE_TEXT, _APACHE_URL),
    ("mpl-2.0", _MPL_TEXT, _MPL_URL),
)
_SOFTWARE_TOKENS = {
    "mit": RIGHTS_MIT,
    "apache-2.0": RIGHTS_APACHE,
    "mpl-2.0": RIGHTS_MPL,
}
_CREDIT_PHRASE = re.compile(
    r"(?i)(?:^|[>\s])(?:photo|image|caption)(?:\s+credits?\b|\s*:)"
)
_CREDIT_CLASS = re.compile(r"(?i)(?:photo[\s_-]*credit|image[\s_-]*credit|caption[\s_-]*credit|wp-caption)")
_CREDIT_SENTENCE = re.compile(
    r"(?i)(?:^|[>\s])(?:photo|image|caption)(?:\s+credits?\b|\s*:)(?:(?![.?!]).){0,400}"
)
_NEGATED_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:an?\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NOT_PUBLICATION = re.compile(r"(?i)\b(?:updated|modified|copyright)\b|©|last\s+update")
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


class CatalogError(ValueError):
    """A catalog row or page failed the Technology Innovation Institute page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    validate_catalog(document)
    return document


def validate_catalog(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != _DOCUMENT_FIELDS:
        raise CatalogError("catalog document fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    _require_text(document.get("description"), "description", MAX_DESCRIPTION_CHARS)
    if document.get("runner_wired") is not False:
        raise CatalogError("runner_wired must be false")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    seen: set[str] = set()
    order: list[tuple[str, str]] = []
    for entry in entries:
        validate_entry(entry)
        url = entry["canonical_url"]
        if url in seen:
            raise CatalogError(f"duplicate canonical URL: {url}")
        seen.add(url)
        order.append((_sort_date(entry["date"]), url))
        if len(order) > 1 and order[-1] < order[-2]:
            raise CatalogError("entries must be ordered by date, then canonical URL")


def validate_entry(entry: dict) -> None:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise CatalogError("entry fields must be title, publisher, canonical URL, date, and rights")
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError(f"rights must be a known label or {RIGHTS_UNKNOWN}")


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or "%" in url:
        raise CatalogError("canonical URL must be a public Technology Innovation Institute AI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    netloc = parsed.netloc.lower()
    if (
        parsed.scheme != "https"
        or netloc != host
        or host not in OFFICIAL_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
        or hostname_is_blocked(host)
        or ".." in path
        or "\\" in path
        or "//" in path
        or not _public_page_path(path)
    ):
        raise CatalogError(
            f"canonical URL is not a public Technology Innovation Institute AI page: {url}"
        )
    return url


def is_official_host(hostname: str) -> bool:
    host = (hostname or "").strip().lower().rstrip(".")
    return host in OFFICIAL_HOSTS and not hostname_is_blocked(host)


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
    if any(marker in lowered for marker in _ANYWHERE_MARKERS):
        return True
    head = lowered[:8000]
    title_match = _TITLE.search(page_html[:8000])
    title = title_match.group(1).casefold() if title_match else ""
    blob = head + "\n" + title
    return any(marker in blob for marker in _HEAD_MARKERS)


def robots_allows(body: str, path: str) -> bool:
    """True when robots.txt does not disallow ``path``.

    An empty or comment-only body allows the path. A challenge page or an HTML
    document served in place of robots.txt does not allow a fetch. A Disallow
    rule blocks the longest matching pattern unless a longer Allow pattern
    wins. ``*`` is a wildcard and ``$`` anchors the end.
    """

    if not isinstance(body, str):
        return False
    sample = body.lstrip()[:8000].casefold()
    if is_challenge_page(sample) or any(marker in sample for marker in _ANYWHERE_MARKERS + _HEAD_MARKERS):
        return False
    if "<html" in sample[:1500] or sample.startswith("<!doctype html"):
        return False
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    allowed = 0
    disallowed = 0
    for kind, pattern in rules:
        if not pattern or not _robots_pattern_matches(pattern, target):
            continue
        if kind == "allow":
            allowed = max(allowed, len(pattern))
        else:
            disallowed = max(disallowed, len(pattern))
    return allowed >= disallowed


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: Mapping[str, str] | None = None,
) -> bool:
    """A page is stored only from HTML that is not a challenge or an HTTP error."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    lowered = page_html[:12000].casefold()
    if "<html" not in lowered and "<!doctype html" not in lowered:
        return False
    if re.search(r"(?is)<input\b[^>]*\btype\s*=\s*['\"]password['\"]", page_html):
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            text = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in text:
                return False
            if name == "sg-captcha" or "sg-captcha" in text:
                return False
            if name == "www-authenticate":
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
    """Return metadata when the response is an allowed on-host HTML page.

    A challenge page, a captcha, an authentication wall, a non-HTML shell, an
    error status, a robots disallow, or an off-host URL is not stored. A
    redirect from tii.ae to www.tii.ae stores the www URL when the path stays
    an AI research, model, news, or program page.
    """

    target = final_url or page_url
    parsed = urlparse(target)
    if not is_official_host(parsed.hostname or ""):
        return None
    if robots_txt is not None and not robots_allows(robots_txt, parsed.path or "/"):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return None
    if not isinstance(page_html, str):
        return None
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rows_for_response(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
) -> list[dict]:
    """Return catalog rows for one response.

    A Cloudflare challenge, a captcha, an authentication wall, a non-HTML
    shell, a robots disallow, an HTML robots document, or an off-host redirect
    contributes an empty list.
    """

    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        robots_txt=robots_txt,
    )
    if record is None:
        return []
    return [record]


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps its own token.
    CC BY alone is creative_commons_attribution. CC0, CC BY-SA, or a permissive
    mix of those is creative_commons. Mixed restricted and permissive text
    stays unknown. A CC BY or CC BY-SA anchor on a restricted or public-domain
    mark URL stays unknown. A CC0 anchor on a publicdomain/mark URL stays
    unknown. A generic creativecommons.org/licenses or /licenses/ URL is not a
    deed, including a missing slash, http, a www host, or a query string.
    Anchor text on that URL stays unknown. Text elsewhere on the page still
    counts. A specific deed URL still counts. A photo credit, caption credit,
    or image credit that names someone else's licence stays unknown, including
    Photo: UNDRR, CC BY-NC-ND 2.0. Two different restricted deeds stay unknown.
    A software licence beside any Creative Commons deed stays unknown. Two
    software licences stay unknown. Bare MIT stays unknown. Licensed under the
    MIT License is mit. Apache License, Version 2.0, including the comma, is
    apache-2.0. uk_ogl requires the British phrase Open Government Licence.
    us_government_work comes only from an explicit rights field. Script, style,
    and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    codes, gov = _licence_signals(page_text)
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    software = codes & set(_SOFTWARE_TOKENS)
    ogl = "uk_ogl" in codes
    if restricted and (permissive or software or ogl or gov):
        return RIGHTS_UNKNOWN
    if len(restricted) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if software and (permissive or ogl or gov):
        return RIGHTS_UNKNOWN
    if len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(software) == 1:
        return _SOFTWARE_TOKENS[next(iter(software))]
    if gov and (permissive or ogl):
        return RIGHTS_UNKNOWN
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    if ogl and permissive:
        return RIGHTS_UNKNOWN
    if ogl:
        return RIGHTS_UK_OGL
    if permissive == frozenset({"cc-by"}):
        return RIGHTS_CC_BY
    if permissive:
        return RIGHTS_CREATIVE_COMMONS
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    JSON-LD datePublished and the article sn-date are publication dates when
    they agree. A listing of other posts' times, article:modified_time,
    og:updated_time, and a copyright year are not publication dates.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    without_comments = _COMMENT.sub(" ", page_html)
    found: list[str] = []
    for raw in _DATE_PUBLISHED.findall(" ".join(_LDJSON.findall(without_comments))):
        _add_date(found, _loose_date(raw))
    visible = _HIDDEN.sub(" ", without_comments)
    for raw in _SN_DATE.findall(visible):
        _add_date(found, _loose_date(_plain_text(raw)))
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
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
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        if metas.get(key):
            title = _clean_title(metas[key])
            if title:
                return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Technology Innovation Institute when the page states that name.

    A person named on the page is not the publisher. The hostname is not the
    publisher. The name is not invented when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible_html(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if _states_publisher(metas.get(key, "")):
            return PUBLISHER
    if _states_publisher(_plain_text(visible)):
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document text. ``page_url`` is the live
    URL that was fetched. A rel=canonical pointing somewhere else is not used.
    """

    if is_challenge_page(page_html):
        raise CatalogError("challenge page is not stored")
    record = {
        "title": title_from_page(page_html),
        "publisher": publisher_from_page(page_html),
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    validate_entry(record)
    return record


def _public_page_path(path: str) -> bool:
    if path != path.lower() or ".." in path:
        return False
    trimmed = path[:-1] if path.endswith("/") and len(path) > 1 else path
    if trimmed != path:
        return False
    if _is_download(trimmed):
        return False
    parts = [part for part in trimmed.split("/") if part]
    if not parts or any(part in _EXCLUDED_PARTS for part in parts):
        return False
    if not all(_SEGMENT.fullmatch(part) is not None for part in parts):
        return False
    if not _ai_subject(trimmed):
        return False
    if parts[0] == "ai-and-digital-science" and len(parts) <= 3:
        return True
    return len(parts) == 2 and parts[0] in _PAGE_SECTIONS


def _ai_subject(path: str) -> bool:
    tokens = [token for token in re.split(r"[^a-z0-9]+", path.lower()) if token]
    if any(token in _AI_TOKENS or token.startswith("aidrc") for token in tokens):
        return True
    joined = "-".join(tokens)
    return any(phrase in joined for phrase in _AI_PHRASES)


def _is_download(path: str) -> bool:
    return path.lower().endswith(_DOWNLOAD_SUFFIXES)


def _states_publisher(value: str) -> bool:
    text = _clean_text(value).casefold()
    return "technology innovation institute" in text


def _strip_mark_anchors(page_html: str) -> str:
    """Drop anchors whose URL is the Public Domain Mark, including their text.

    A CC0, CC BY, or CC BY-SA label on that URL is not a licence statement.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        folded = _fold(href)
        if "creativecommons.org/publicdomain/mark" in folded:
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for creativecommons.org/licenses with no specific deed.

    A missing slash, http, a www host, and a query string are still generic.
    """

    folded = _fold(href)
    if "creativecommons.org/licenses" not in folded:
        return False
    return not any(match.group("license") for match in _CC_URL.finditer(folded))


def _strip_generic_license_anchors(page_html: str) -> str:
    """Drop anchors whose URL is a generic creativecommons.org/licenses page.

    CC BY, CC BY 4.0, or CC BY-SA text on that URL is not a licence statement.
    Text outside the anchor still counts.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs(f"<a {match.group(1)}>").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _FULL_ANCHOR.sub(replace, page_html)


def _strip_image_credits(page_html: str) -> str:
    """Drop photo, caption, and image credits that name someone else's licence.

    The credit is not a licence to reuse the page. A reuse licence stated
    outside that credit still counts.
    """

    def replace_block(match: re.Match[str]) -> str:
        attrs = match.group(2)
        body = match.group(3)
        if len(body) > 800:
            return match.group(0)
        if _CREDIT_CLASS.search(attrs) or _CREDIT_PHRASE.search(body) or _CREDIT_PHRASE.search(attrs):
            return " "
        return match.group(0)

    stripped = _CREDIT_BLOCK.sub(replace_block, page_html)

    def replace_anchor(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(match.group(0)):
            return " "
        return match.group(0)

    stripped = _FULL_ANCHOR.sub(replace_anchor, stripped)
    return _CREDIT_SENTENCE.sub(" ", stripped)


def _licence_signals(page_text: str) -> tuple[set[str], bool]:
    page_text = _strip_image_credits(page_text)
    page_text = _strip_generic_license_anchors(_strip_mark_anchors(page_text))
    without_comments = _COMMENT.sub(" ", page_text)
    codes: set[str] = set()
    gov = False
    for license_text, rights_text in _jsonld_rights(without_comments):
        codes |= _codes_in_string(license_text)
        codes |= _codes_in_string(rights_text)
        if _states_us_government_work(rights_text):
            gov = True
    visible = _HIDDEN.sub(" ", without_comments)
    for value in _license_meta_texts(visible):
        codes |= _codes_in_string(value)
    for value in _rights_field_texts(visible):
        if _states_us_government_work(value):
            gov = True
        codes |= _codes_in_string(value)
    plain = _plain_text(visible)
    folded = _fold(plain)
    codes |= _codes_in_folded(folded)
    if OGL_PHRASE in folded:
        codes.add("uk_ogl")
    for href in _hrefs(visible):
        codes |= _codes_in_string(href)
    return codes, gov


def _codes_in_string(value: str) -> set[str]:
    if not value:
        return set()
    return _codes_in_folded(_fold(value))


def _codes_in_folded(folded: str) -> set[str]:
    """Licence codes in one folded string. Restricted deeds are matched first."""

    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        license_code = match.group("license")
        if license_code:
            codes.add(f"cc-{license_code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
    hits: list[tuple[int, int, int, str]] = []
    for code, pattern in _TEXT_DEEDS:
        for match in pattern.finditer(folded):
            hits.append((match.end() - match.start(), match.start(), match.end(), code))
    hits.sort(key=lambda item: (-item[0], item[1]))
    occupied: list[tuple[int, int]] = []
    for _length, start, end, code in hits:
        if any(start < right and end > left for left, right in occupied):
            continue
        occupied.append((start, end))
        codes.add(code)
    for code, text_pattern, url_pattern in _SOFTWARE:
        if text_pattern.search(folded) or url_pattern.search(folded):
            codes.add(code)
    return codes


def _states_us_government_work(value: str) -> bool:
    text = _NEGATED_GOV.sub(" ", _fold(value))
    return _GOV_WORK.search(text) is not None


def _jsonld_rights(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for block in _LDJSON.findall(page_html):
        licenses = [item.replace("\\/", "/") for item in _LD_LICENSE.findall(block)]
        rights = [item.replace("\\/", "/") for item in _LD_RIGHTS.findall(block)]
        if not licenses and not rights:
            continue
        width = max(len(licenses), len(rights), 1)
        licenses.extend([""] * (width - len(licenses)))
        rights.extend([""] * (width - len(rights)))
        found.extend(zip(licenses, rights, strict=True))
    return found


def _license_meta_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key in {"license", "licence"} or key.endswith((".license", ".licence", ":license", ":licence")):
            found.append(value)
    return found


def _rights_field_texts(page_html: str) -> list[str]:
    found: list[str] = []
    for key, value in _metas(page_html).items():
        if key == "rights" or key.endswith(".rights") or key.endswith(":rights"):
            found.append(value)
    for _tag, attrs, body in _RIGHTS_ELEMENT.findall(page_html):
        if not _is_rights_element(attrs):
            continue
        text = _plain_text(body)
        if text and len(text) <= MAX_TEXT_CHARS:
            found.append(text)
    return found


def _is_rights_element(attrs: str) -> bool:
    parsed = _attrs(f"<x {attrs}>")
    if parsed.get("itemprop", "").casefold() == "rights":
        return True
    for key in ("id", "class"):
        raw = parsed.get(key, "").replace("-", " ").replace("_", " ")
        if any(token.casefold() == "rights" for token in raw.split()):
            return True
    return False


def _add_date(found: list[str], value: str | None) -> None:
    if value and value not in found:
        found.append(value)


def _loose_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = _clean_text(value)
    if not text or _NOT_PUBLICATION.search(text):
        return None
    iso = _iso_day(text)
    if iso and (text == iso or text[len(iso) : len(iso) + 1] in {"T", " "}):
        return iso
    day_first = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if day_first:
        return _calendar_date(day_first.group(2), day_first.group(1), day_first.group(3))
    month_first = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", text)
    if month_first:
        return _calendar_date(month_first.group(1), month_first.group(2), month_first.group(3))
    return None


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


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
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value))
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(page_text: str) -> str:
    return _clean_text(_visible_html(page_text))


def _visible_html(page_text: str) -> str:
    return _HIDDEN.sub(" ", _COMMENT.sub(" ", page_text))


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).casefold()


def _iso_day(value: object) -> str | None:
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


def _calendar_date(month_name: str, day_text: str, year_text: str) -> str | None:
    month = _MONTHS.get(month_name.casefold())
    if month is None:
        return None
    try:
        parsed = date(int(year_text), month, int(day_text))
    except ValueError:
        return None
    return parsed.isoformat()


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    for attrs in _ANCHOR.findall(page_html):
        href = _attrs(f"<a {attrs}>").get("href", "")
        if href:
            found.append(href)
    return found


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


def _robots_pattern_matches(pattern: str, target: str) -> bool:
    if "*" not in pattern and not pattern.endswith("$"):
        return target.startswith(pattern)
    end = pattern.endswith("$")
    body = pattern[:-1] if end else pattern
    parts = [re.escape(part) for part in body.split("*")]
    regex = ".*".join(parts)
    if end:
        return re.match(f"^{regex}$", target) is not None
    return re.match(f"^{regex}", target) is not None


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
