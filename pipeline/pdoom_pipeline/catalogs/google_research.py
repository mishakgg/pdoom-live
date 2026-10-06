"""Metadata catalog of public Google Research pages about AI.

The host is research.google. The publisher is Google Research. A row is stored
only after one bounded GET of public HTML that robots.txt allows and that
stays on research.google. Person profiles, product pages, PDFs, and
blog.google are not stored. A challenge page, an HTML document in place of
robots.txt, a host that does not resolve, or a redirect off research.google
is not stored. An empty catalog is correct in those cases.

Each row keeps the title, publisher, canonical URL, date, and rights label.
Page text, abstracts, PDFs, quotes, transcripts, and chart data are not
stored. This catalog does not invent a probability.

Rights stay unknown unless the page states a reuse licence.
creative_commons_attribution is CC BY alone, including a specific
/licenses/by/4.0/ URL. creative_commons is CC0, CC BY-SA, or a permissive mix
of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA, or CC BY-NC-ND keeps
cc_by_nc, cc_by_nd, cc_by_nc_sa, or cc_by_nc_nd. Text cc-by-nc is cc_by_nc.
mit, apache-2.0, and mpl-2.0 are sole software licences. Apache License,
Version 2.0 is apache-2.0. Bare MIT stays unknown. Licensed under the MIT
License is mit. uk_ogl is only the British phrase Open Government Licence.
Open Government License stays unknown. us_government_work comes only from an
explicit rights metadata field.

A generic creativecommons.org/licenses or /licenses URL is not a deed. Anchor
text on it stays unknown, including a missing slash, http, a www host, and a
query string. A specific deed URL still counts. Deceptive permissive anchor
text on a restricted deed URL or a public-domain mark URL stays unknown. A
CC0 anchor on a publicdomain/mark URL stays unknown. A software licence
beside any Creative Commons deed stays unknown. Two software licences stay
unknown. Two different restricted deeds stay unknown. A photo credit, caption
credit, or image credit that names someone else's licence stays unknown,
including Photo credit: UNDRR, CC BY-NC-ND 2.0 and Photo: UNDRR, CC BY-NC-ND
2.0. When the page states its own CC BY licence and a separate photo credit
names another licence, the page stays creative_commons_attribution. Script,
style, and comment text does not count.

Publication dates only. Updated, modified, and copyright years are not
publication dates. A missing date stays unknown. The live URL is stored as
confirmed. A different rel=canonical does not replace it.

This module does not fetch and it does not import requests. It is not a
belief collector. runner_wired stays false. Belief collection stays on
RssCollector.
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

CATALOG_ID = "google_research_pages"
CATALOG_FILENAME = "google_research_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Google Research"
UNKNOWN_DATE = "unknown"
RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CC_ATTRIBUTION = "creative_commons_attribution"
RIGHTS_CC_BY_NC = "cc_by_nc"
RIGHTS_CC_BY_ND = "cc_by_nd"
RIGHTS_CC_BY_NC_SA = "cc_by_nc_sa"
RIGHTS_CC_BY_NC_ND = "cc_by_nc_nd"
RIGHTS_UK_OGL = "uk_ogl"
RIGHTS_US_GOVERNMENT_WORK = "us_government_work"
RIGHTS_MIT = "mit"
RIGHTS_APACHE = "apache-2.0"
RIGHTS_MPL = "mpl-2.0"
RIGHTS_LABELS = frozenset(
    {
        RIGHTS_UNKNOWN,
        RIGHTS_CREATIVE_COMMONS,
        RIGHTS_CC_ATTRIBUTION,
        RIGHTS_CC_BY_NC,
        RIGHTS_CC_BY_ND,
        RIGHTS_CC_BY_NC_SA,
        RIGHTS_CC_BY_NC_ND,
        RIGHTS_UK_OGL,
        RIGHTS_US_GOVERNMENT_WORK,
        RIGHTS_MIT,
        RIGHTS_APACHE,
        RIGHTS_MPL,
    }
)
OFFICIAL_HOST = "research.google"
OFFICIAL_HOSTS = frozenset({OFFICIAL_HOST})
OGL_PHRASE = "open government licence"
MAX_FIELD_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
CATALOG_DESCRIPTION = (
    "Public AI research HTML on research.google. Publisher is Google Research. "
    "Each row was one bounded GET that robots.txt allowed. "
    "Person profiles, product pages, PDFs, and blog.google are not stored. "
    "A challenge page, HTML robots.txt, an unresolved host, or a redirect off research.google stores no row. "
    "An empty catalog is correct then. "
    "Rows keep title, publisher, canonical URL, date, and rights. Page text is omitted. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive mix. "
    "Sole restricted deeds keep their tokens. "
    "uk_ogl is the British phrase Open Government Licence. "
    "A missing publication date stays unknown. Updated, modified, and copyright years are not dates. "
    "Not a belief collector. runner_wired stays false."
)

# Section pages that are the public AI research surface. Individual paper
# landing pages are omitted: they span many fields and this catalog keeps the
# AI sections, AI conference roundups, and AI research blog posts.
_EXACT_PATHS = frozenset(
    {
        "/",
        "/blog/",
        "/pubs/",
        "/research-areas/",
        "/research-areas/machine-intelligence/",
        "/research-areas/machine-perception/",
        "/research-areas/natural-language-processing/",
        "/research-areas/information-retrieval/",
        "/research-areas/responsible-ai/",
        "/research-areas/science-ai/",
        "/research-areas/health-ai/",
        "/research-areas/google-earth-ai/",
        "/teams/cloud-ai-research/",
        "/teams/responsible-ai/",
        "/teams/learning-theory/",
        "/resources/datasets/",
        "/conferences-and-events/",
        "/programs-and-events/past-programs/ai-for-social-good-awards/",
        "/programs-and-events/featured-research-collaborations/artists-machine-intelligence-ami-research-awardees/",
        "/programs-and-events/creating-ml-benchmarks-for-climate-problems/",
        "/programs-and-events/society-centered-ai/",
        "/programs-and-events/society-centered-ai/google-society-centered-ai-research-awardees/",
        "/programs-and-events/making-education-equitable-accessible-and-effective-using-ai/",
        "/programs-and-events/gemini-systems-and-infrastructure-problems/",
        "/programs-and-events/artists-machine-intelligence-ami-research-awards/",
        "/programs-and-events/ai-for-privacy-safety-and-security/",
    }
)
_AI_CONFERENCE = re.compile(
    r"^/conferences-and-events/"
    r"(?:google-at-(?:neurips|icml|iclr|cvpr|iccv|eccv|acl|emnlp|colm|interspeech|icassp|khipu)-\d{4}"
    r"|google-at-deep-learning-indaba-\d{4})"
    r"/$"
)
_BLOG_POST = re.compile(r"^/blog/([a-z0-9]+(?:-[a-z0-9]+)*)/$")
# Hyphen-bounded tokens. "ai" does not match inside another word.
_AI_TOKEN = re.compile(
    r"(?:^|-)(?:ai|ml|llm|nlp|gemini|gemma|imagen|bert|palm|alphafold|"
    r"machine-learning|machine-intelligence|deep-learning|language-model|"
    r"large-language|reinforcement-learning|responsible-ai|computer-vision|"
    r"foundation-model|generative-ai|neural-network|neural-networks|"
    r"multimodal|transformer|transformers)(?:-|$)"
)

_CATALOG_FIELDS = frozenset({"catalog_id", "description", "runner_wired", "entries"})
_ENTRY_FIELDS = frozenset({"title", "publisher", "canonical_url", "date", "rights"})
_FORBIDDEN_KEYS = frozenset(
    {
        "abstract",
        "body",
        "chart",
        "chart_data",
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
        "summary",
        "text",
        "transcript",
        "transcript_text",
    }
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".gif",
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
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<link\b[^>]*>")
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_HREF_ATTR = re.compile(
    r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_PUBLISH_ATTR = re.compile(
    r"""(?is)\bdata-gt-publish-date\s*=\s*["'](\d{8})["']"""
)
_HERO_DATE = re.compile(
    r"""(?is)<div\b[^>]*\bclass\s*=\s*["'][^"']*\bbasic-hero--blog-detail__description\b[^"']*["'][^>]*>(.*?)</div>"""
)
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "cf-mitigated",
    "challenge-platform",
    "/cdn-cgi/challenge",
    "checking your browser",
    "sgcaptcha",
    "sg-captcha",
    "attention required! | cloudflare",
    "are you a robot",
    "akamai bot manager",
    "errors.edgesuite.net",
)
_CHALLENGE_TITLES = frozenset(
    {
        "just a moment...",
        "attention required! | cloudflare",
        "access denied",
    }
)
_SITE_SUFFIXES = (
    " — Google Research",
    " – Google Research",
    " - Google Research",
    " | Google Research",
)
_GENERIC_TITLES = frozenset(
    {
        "google research",
        "google",
        "research",
        "home",
    }
)
_LOGIN_SEGMENTS = frozenset(
    {
        "account",
        "log-in",
        "login",
        "register",
        "sign-in",
        "signin",
        "signup",
        "wp-admin",
        "wp-login",
        "wp-login.php",
    }
)
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_MONTH = "|".join(sorted(_MONTHS, key=len, reverse=True))
_MDY = re.compile(rf"\b({_MONTH})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE)
_DMY = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH})\.?,?\s+(\d{{4}})\b", re.IGNORECASE)
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
# Longer deeds are first. `(?![-a-z0-9])` keeps licenses/by from matching
# licenses/by-nc, and the text patterns refuse a following NC, ND, or SA.
_CC_URL = re.compile(
    r"creativecommons\.org/"
    r"(?:licenses/(?P<code>by-nc-nd|by-nc-sa|by-nc|by-nd|by-sa|by)"
    r"|publicdomain/(?P<pd>zero|mark))"
    r"(?![-a-z0-9])"
)
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cc-by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd\b")),
    (
        "cc-by-nc-nd",
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+no[\s-]*deriv"),
    ),
    ("cc-by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa\b")),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"
        ),
    ),
    (
        "cc-by-nc",
        re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)"),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creative commons attribution[\s-]+non[\s-]*commercial"
            r"(?![\s-]*(?:no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
    ("cc-by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd\b")),
    ("cc-by-nd", re.compile(r"creative commons attribution[\s-]+no[\s-]*deriv")),
    ("cc-by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa\b")),
    ("cc-by-sa", re.compile(r"creative commons attribution[\s-]+share[\s-]*alike")),
    (
        "cc0",
        re.compile(
            r"(?<![a-z0-9])cc[\s-]*0(?![a-z0-9])"
            r"|(?<![a-z0-9])cc[\s-]*zero\b"
            r"|creative commons(?:\s+public\s+domain)?[\s-]+zero\b"
        ),
    ),
    ("cc-by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?![\s-]*(?:nc|nd|sa)\b)")),
    (
        "cc-by",
        re.compile(
            r"creative commons attribution"
            r"(?![\s-]*(?:non[\s-]*commercial|no[\s-]*deriv|share[\s-]*alike))"
        ),
    ),
)
_PD_MARK = re.compile(r"public domain mark\b")
_RESTRICTED = frozenset({"cc-by-nc", "cc-by-nd", "cc-by-nc-sa", "cc-by-nc-nd"})
_PERMISSIVE = frozenset({"cc-by", "cc-by-sa", "cc0"})
_RESTRICTED_TOKEN = {
    "cc-by-nc-nd": RIGHTS_CC_BY_NC_ND,
    "cc-by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "cc-by-nc": RIGHTS_CC_BY_NC,
    "cc-by-nd": RIGHTS_CC_BY_ND,
}
# "modified MIT" is not the MIT licence. Bare "MIT" is not either.
_MIT = re.compile(
    r"(?<!modified )(?:\bmit licen[cs]e\b|\blicensed under (?:the )?mit\b(?!-))"
    r"|opensource\.org/licenses/mit(?![a-z0-9-])"
    r"|spdx\.org/licenses/mit(?![a-z0-9-])"
)
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])"
    r"|\bapache licen[cs]e(?:\s*,\s*version|\s+version|\s*,)?\s*2\.0\b"
    r"|apache\.org/licenses/license-2\.0(?![a-z0-9-])"
    r"|spdx\.org/licenses/apache-2\.0(?![a-z0-9-])"
)
_MPL = re.compile(
    r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])"
    r"|\bmpl\s*2\.0\b"
    r"|\bmozilla public licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_GENERIC_CC_LICENSES = re.compile(
    r"^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:\?[^#]*)?(?:#.*)?$"
)
_CREDIT_PHRASE = re.compile(
    r"(?i)(?:"
    r"\b(?:photo|caption|image)\s+credits?\b"
    r"|\bphoto\s*:"
    r"|\bcourtesy of\b"
    r"|\bcredited to\b"
    r"|\boriginal image\b"
    r"|\bimages are from\b"
    r"|\bimage of\b"
    r"|\bthe image\b"
    r"|\bexcerpt from\b"
    r"|\bposted to flickr\b"
    r"|\bused under\b"
    r"|\bcredit\s*&\s*licen[cs]e\b"
    r"|\bmodified from\b"
    r")"
)
_CREDIT_SENTENCE = re.compile(
    r"(?i)(?:[^.<]|<(?!/?(?:p|figcaption|li)\b)[^>]*>){0,80}"
    r"(?:"
    r"\b(?:photo|caption|image)\s+credits?\b"
    r"|\bphoto\s*:"
    r"|\bcourtesy of\b"
    r"|\bcredited to\b"
    r"|\boriginal image\b"
    r"|\bimages are from\b"
    r"|\bimage of\b"
    r"|\bthe image\b"
    r"|\bexcerpt from\b"
    r"|\bposted to flickr\b"
    r"|\bused under\b"
    r"|\bcredit\s*&\s*licen[cs]e\b"
    r"|\bmodified from\b"
    r")"
    r"(?:[^.<]|<(?!/?(?:p|figcaption|li)\b)[^>]*>){0,500}\.?"
)
_CREDIT_BLOCK = re.compile(r"(?is)<(p|li|figcaption|td|dd|figure|div|span)\b([^>]*)>(.*?)</\1>")
_CREDIT_LINK_PAIR = re.compile(
    r"(?is)<a\b[^>]*>\s*credit\s*</a>\s*(?:&amp;|&)\s*"
    r"<a\b[^>]*\bhref\s*=\s*([\"'])[^\"']*creativecommons\.org[^\"']*\1[^>]*>\s*licen[cs]e\s*</a>"
)
_PAGE_LICENCE_CUE = re.compile(
    r"(?i)\blicensed under\b|\bthis blog post are licensed\b|\bavailable under the\b"
)
_CC_DEED_ANCHOR = re.compile(
    r"(?is)<a\b[^>]*\bhref\s*=\s*([\"'])[^\"']*creativecommons\.org[^\"']*\1[^>]*>.*?</a>"
)
_CC_DEED_TEXT = re.compile(
    r"(?i)https?://(?:www\.)?creativecommons\.org/(?:licenses|publicdomain)/\S+"
)
_US_GOV = re.compile(
    r"\b(?:u\.?\s*s\.?|united states)\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+(?:united states|u\.?\s*s\.?)\s+government\b"
)
_US_GOV_NEGATED = re.compile(
    r"\bnot\s+(?:a\s+)?(?:u\.?\s*s\.?|united states)\s+government\s+works?\b"
    r"|\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united states|u\.?\s*s\.?)\s+government\b"
)
_NON_DATE_WORDS = ("updated", "update", "modified", "modification", "copyright", "©")
_PASSWORD = re.compile(r"(?is)<input\b[^>]*\btype\s*=\s*['\"]password['\"]")


class CatalogError(ValueError):
    """A catalog row or page failed the Google Research page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True only for research.google."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_catalog_path(path: str) -> bool:
    """True for public AI research HTML on research.google.

    Person profiles, product pages, PDFs, and sections that are not about AI
    are false. Individual publication landing pages are false.
    """

    if not isinstance(path, str) or not path.startswith("/") or path != path.casefold():
        return False
    if "//" in path or "\\" in path or ".." in path or "%" in path or " " in path:
        return False
    if path != "/" and not path.endswith("/"):
        return False
    if any(path.endswith(suffix + "/") or path.endswith(suffix) for suffix in _DOWNLOAD_SUFFIXES):
        return False
    if path == "/people/" or path.startswith("/people/"):
        return False
    if path == "/ai-quests/" or path.startswith("/ai-quests/"):
        return False
    if path.startswith("/careers") or path.startswith("/search"):
        return False
    if path in _EXACT_PATHS:
        return True
    if _AI_CONFERENCE.match(path):
        return True
    blog = _BLOG_POST.match(path)
    return blog is not None and _AI_TOKEN.search(blog.group(1)) is not None


def robots_allows(body: str, path: str) -> bool:
    """True when the * group allows path.

    A challenge page or an HTML document served in place of robots.txt does
    not allow a fetch. The longest matching Allow or Disallow pattern wins.
    Equal lengths allow.
    """

    if not isinstance(body, str):
        return False
    sample = body[:800].casefold()
    if "<html" in sample or "<!doctype html" in sample or is_challenge_page(body[:8000]):
        return False
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    if not target.startswith("/"):
        target = "/" + target
    best_allow = -1
    best_disallow = -1
    for kind, pattern in rules:
        if _robots_matches(pattern, target):
            length = len(pattern)
            if kind == "allow":
                best_allow = max(best_allow, length)
            else:
                best_disallow = max(best_disallow, length)
    if best_disallow < 0:
        return True
    if best_allow < 0:
        return False
    return best_allow >= best_disallow


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    base = content_type.split(";", 1)[0].strip().casefold()
    return base in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return True
    match = _TITLE.search(_visible(page_html[:12000]))
    if match is None:
        return False
    title = _plain(match.group(1)).casefold()
    return title in _CHALLENGE_TITLES


def is_login_wall(page_html: str) -> bool:
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if _PASSWORD.search(page_html):
        return True
    title_match = _TITLE.search(page_html[:8000])
    title = _plain(title_match.group(1)).casefold() if title_match else ""
    return any(token in title for token in ("log in", "login", "sign in", "sign-in"))


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    page_url: str,
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge."""

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html) or is_login_wall(page_html):
        return False
    if _challenge_headers(headers):
        return False
    target = final_url or page_url
    if not _on_official_host(target):
        return False
    lowered = page_html[:12000].casefold()
    if "<html" not in lowered and "<!doctype html" not in lowered:
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
    hops: tuple[str, ...] | list[str] | None = None,
) -> dict | None:
    """Return metadata when one bounded GET returned allowed page HTML.

    A challenge, an HTML robots document, a robots disallow, a non-HTML body,
    an authentication wall, or a redirect off research.google is not stored.
    """

    target = final_url or page_url
    if hops and any(not _on_official_host(hop) for hop in hops):
        return None
    if robots_txt is not None and not robots_allows(robots_txt, urlparse(target).path or "/"):
        return None
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=target,
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
    resolved: bool = True,
    status: object = None,
    content_type: object = None,
    page_html: object = None,
    page_url: str = "",
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    robots_txt: str | None = None,
    hops: tuple[str, ...] | list[str] | None = None,
) -> list[dict]:
    """Return catalog rows for one fetch outcome.

    An unresolved host, a challenge page, an HTML document in place of
    robots.txt, or a redirect off research.google contributes an empty catalog
    for that URL.
    """

    if not resolved:
        return []
    record = record_from_response(
        status=status,
        content_type=content_type,
        page_html=page_html,
        page_url=page_url,
        headers=headers,
        final_url=final_url,
        robots_txt=robots_txt,
        hops=hops,
    )
    if record is None:
        return []
    return [record]


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    creative_commons_attribution is CC BY alone. creative_commons is CC0,
    CC BY-SA, or a permissive mix of those. A sole restricted deed keeps its
    token. A permissive label on a restricted or public-domain mark URL stays
    unknown. A generic creativecommons.org/licenses URL is not a deed. A
    photo, caption, or image credit does not count. Script, style, and
    comment text do not count. us_government_work requires a rights metadata
    field.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl, gov = _rights_signals(page_text)
    if "pd-mark" in cc_codes:
        return RIGHTS_UNKNOWN
    restricted = cc_codes & _RESTRICTED
    permissive = cc_codes & _PERMISSIVE
    families = [
        family
        for family in (
            restricted,
            permissive,
            software,
            {RIGHTS_UK_OGL} if ogl else set(),
            {RIGHTS_US_GOVERNMENT_WORK} if gov else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive == {"cc-by"}:
            return RIGHTS_CC_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, a copyright
    year, a year-only citation date, and a date inside script, style, or a
    comment are not publication dates. A listing of other posts is not this
    page's publication date.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    found: list[str] = []
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        _add_date(found, _iso_day(metas.get(key, "")))
    for raw in _PUBLISH_ATTR.findall(visible):
        _add_date(found, _compact_day(raw))
    hero = _HERO_DATE.search(visible)
    if hero:
        _add_date(found, _one_human_date(_plain(hero.group(1))))
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    for heading in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", heading))
        if title and not _generic_title(title):
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title and not _generic_title(title):
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title and not _generic_title(title):
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Google Research when the page states that name.

    A person named on the page is not the publisher. The name is not invented
    when the page does not state it.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    blob = _plain(visible).casefold()
    if "google research" in blob:
        return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A different rel=canonical does not replace it.
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
    """Keep the live URL. A different rel=canonical does not replace it."""

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


def catalog_document(entries: list[dict]) -> dict:
    """Return a validated catalog document for confirmed rows."""

    if not isinstance(entries, list):
        raise CatalogError("entries must be a list")
    ordered = sorted(entries, key=lambda entry: (_sort_date(entry["date"]), entry["canonical_url"]))
    document = {
        "catalog_id": CATALOG_ID,
        "description": CATALOG_DESCRIPTION,
        "runner_wired": False,
        "entries": ordered,
    }
    return validate_catalog(document)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if not isinstance(description, str) or description != description.strip() or not description:
        raise CatalogError("description is required")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog statement")
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


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Google Research page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or not is_official_host(host)
    ):
        raise CatalogError(f"canonical URL must be a public Google Research page: {url}")
    path = parsed.path or "/"
    if path == "":
        path = "/"
    normalized = f"https://{host}{path}"
    if not is_catalog_path(path) or _is_login_url(normalized):
        raise CatalogError(f"canonical URL must be a public Google Research page: {url}")
    return normalized


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool, bool]:
    visible = _visible(page_text)
    gov = _states_us_government_work(visible)
    scanned = _drop_generic_cc_anchors(_drop_credit_licences(visible))
    folded = _fold(scanned)
    return _cc_codes(folded), _software_codes(folded), _states_ogl(scanned), gov


def _states_us_government_work(visible_html: str) -> bool:
    """True only when a rights metadata field states a US government work."""

    for value in _rights_meta_values(visible_html):
        text = _fold(value)
        if _US_GOV_NEGATED.search(text):
            continue
        if _US_GOV.search(text):
            return True
    return False


def _rights_meta_values(visible_html: str) -> list[str]:
    values: list[str] = []
    for tag in _META.findall(visible_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key in _RIGHTS_META or key.endswith(".rights") or key.endswith(":rights"):
            content = attrs.get("content", "")
            if content:
                values.append(content)
    return values


def _drop_generic_cc_anchors(html: str) -> str:
    """Remove anchors that point at the generic Creative Commons licences URL."""

    def replace(match: re.Match[str]) -> str:
        href_match = _HREF_ATTR.search(match.group(1))
        if href_match is None:
            return match.group(0)
        href = href_match.group(1) or href_match.group(2) or href_match.group(3) or ""
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace, html)


def _is_generic_cc_licenses_url(href: str) -> bool:
    folded = _fold(href).replace(" ", "")
    return _GENERIC_CC_LICENSES.fullmatch(folded) is not None


def _drop_credit_licences(html: str) -> str:
    """Drop a photo, caption, or image credit, including a licence it names.

    A page licence outside that credit stays. A deed URL that only documents
    the credit does not become the page licence.
    """

    html = _CREDIT_LINK_PAIR.sub(" ", html)

    def replace_block(match: re.Match[str]) -> str:
        body = match.group(3)
        if len(body) > 4000 or not _CREDIT_PHRASE.search(body):
            return match.group(0)
        cleaned = _CREDIT_SENTENCE.sub(" ", body)
        if _CREDIT_PHRASE.search(cleaned):
            return " "
        if not _PAGE_LICENCE_CUE.search(cleaned):
            cleaned = _CC_DEED_TEXT.sub(" ", _CC_DEED_ANCHOR.sub(" ", cleaned))
        return f"<{match.group(1)}{match.group(2)}>{cleaned}</{match.group(1)}>"

    stripped = _CREDIT_BLOCK.sub(replace_block, html)

    def replace_anchor(match: re.Match[str]) -> str:
        if _CREDIT_PHRASE.search(match.group(0)):
            return " "
        return match.group(0)

    return _ANCHOR.sub(replace_anchor, _CREDIT_SENTENCE.sub(" ", stripped))


def _cc_codes(folded: str) -> set[str]:
    codes: set[str] = set()
    for match in _CC_URL.finditer(folded):
        code = match.group("code")
        if code:
            codes.add(f"cc-{code}")
            continue
        if match.group("pd") == "zero":
            codes.add("cc0")
        elif match.group("pd") == "mark":
            codes.add("pd-mark")
    for name, pattern in _TEXT_DEEDS:
        if pattern.search(folded):
            codes.add(name)
    if _PD_MARK.search(folded):
        codes.add("pd-mark")
    return codes


def _software_codes(folded: str) -> set[str]:
    found: set[str] = set()
    if _MIT.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _states_ogl(visible_html: str) -> bool:
    folded = _fold(_plain(visible_html))
    return OGL_PHRASE in folded


def _one_human_date(text: str) -> str | None:
    folded = text.casefold()
    if any(word in folded for word in _NON_DATE_WORDS):
        return None
    found: list[str] = []
    for match in _MDY.finditer(text):
        _add_date(found, _ymd(int(match.group(3)), _MONTHS[match.group(1).casefold()], int(match.group(2))))
    for match in _DMY.finditer(text):
        _add_date(found, _ymd(int(match.group(3)), _MONTHS[match.group(2).casefold()], int(match.group(1))))
    if len(found) == 1:
        return found[0]
    return None


def _add_date(found: list[str], value: str | None) -> None:
    if value and value not in found:
        found.append(value)


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


def _robots_matches(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "^" + ".*".join(re.escape(chunk) for chunk in body.split("*"))
    if anchored:
        regex += "$"
    return re.search(regex, path) is not None


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    if parsed.username or parsed.password or parsed.port is not None:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return is_official_host(host)


def _is_login_url(url: str) -> bool:
    if not isinstance(url, str) or "://" not in url:
        return False
    path = (urlparse(url).path or "/").casefold()
    segments = {part for part in path.split("/") if part}
    if segments & _LOGIN_SEGMENTS:
        return True
    return "wp-login" in path or path.startswith("/wp-admin")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _same_page(left: str, right: str) -> bool:
    return left.rstrip("/") == right.rstrip("/")


def _join_official(base: str, href: str) -> str:
    ref = unescape(href).strip()
    parsed = urlparse(ref)
    if parsed.scheme in {"http", "https"}:
        host = (parsed.hostname or "").lower().rstrip(".")
        path = parsed.path or "/"
        return f"https://{host}{path}"
    if ref.startswith("/"):
        host = (urlparse(base).hostname or OFFICIAL_HOST).lower()
        path = ref.split("#", 1)[0].split("?", 1)[0]
        return f"https://{host}{path}"
    return ref


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    year, month, day = (int(part) for part in match.group(1).split("-"))
    return _ymd(year, month, day)


def _compact_day(raw: str) -> str | None:
    if len(raw) != 8 or not raw.isdigit():
        return None
    return _ymd(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))


def _iso_date(value: str) -> bool:
    if _DATE.fullmatch(value) is None:
        return False
    year, month, day = (int(part) for part in value.split("-"))
    return _ymd(year, month, day) == value


def _ymd(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in _ATTR.finditer(tag):
        found[match.group(1).casefold()] = unescape(match.group(2) or match.group(3) or match.group(4) or "")
    return found


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
        if key and key not in found:
            found[key] = attrs.get("content", "")
    return found


def _canonical_href(page_html: str) -> str:
    visible = _visible(page_html)
    for tag in _LINK.findall(visible):
        attrs = _attrs(tag)
        if attrs.get("rel", "").casefold().split() == ["canonical"] or "canonical" in attrs.get("rel", "").casefold().split():
            return attrs.get("href", "")
    return ""


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(value: str) -> str:
    return _clean_text(value)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = _plain(value)
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    if not text or len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _generic_title(value: str) -> bool:
    return value.casefold() in _GENERIC_TITLES


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > MAX_FIELD_CHARS or "<" in value or ">" in value or "\n" in value:
        raise CatalogError(f"{field} must be a short plain-text field")


def _reject_stored_body(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        found = _FORBIDDEN_KEYS.intersection(str(key).casefold() for key in value)
        if found:
            raise CatalogError(f"page text is not stored: {', '.join(sorted(found))}")
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


def _challenge_headers(headers: Mapping[str, str] | None) -> bool:
    if not headers:
        return False
    for key, value in headers.items():
        name = str(key).casefold()
        text = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in text:
            return True
        if name == "sg-captcha" or "sg-captcha" in text:
            return True
    return False
