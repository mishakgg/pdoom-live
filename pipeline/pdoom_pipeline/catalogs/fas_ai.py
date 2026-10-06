"""Metadata catalog of public Federation of American Scientists AI pages.

Hosts are fas.org and www.fas.org. www.fas.org redirects to fas.org. Rows are
pages whose topic is artificial intelligence, machine learning, or AI policy:
AI publication-term archives, the artificial-intelligence and AI x global-risk
initiatives, AI accelerators and events, and publications carrying those AI
terms. Unrelated federation topics, login walls, and donation pages are
omitted. Each stored URL was confirmed with one bounded GET that stayed on
those hosts. A Cloudflare challenge, a captcha, an authentication wall, a
robots disallow, a non-HTML response, or a redirect off these hosts is not
stored. Public sitemaps and AI listings returned without a challenge.

A row keeps the title, publisher, canonical URL, date, and rights label.
Page bodies, abstracts, PDFs, quotes, transcripts, and chart data are not
stored. The live URL is stored as confirmed. A different rel=canonical does
not replace it.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is CC0,
CC BY-SA, or a permissive mix of those. One sole restricted deed keeps
``cc_by_nc``, ``cc_by_nd``, ``cc_by_nc_sa``, or ``cc_by_nc_nd``. A hyphen is
a word boundary, so CC BY does not match CC BY-NC and licenses/by does not
match licenses/by-nc. Two different restricted deeds stay unknown. A software
licence beside any Creative Commons deed stays unknown. Two software licences
stay unknown. A generic creativecommons.org/licenses or /licenses/ URL is not
a deed: anchor text on it, including CC BY, CC BY 4.0, and CC BY-SA, stays
unknown. The same rule covers a missing trailing slash, http, a www host, and
a query string. A specific deed URL still counts. Text elsewhere on the page
still counts. Deceptive permissive anchor text on a restricted deed URL or on
a public-domain mark URL stays unknown. A CC0 anchor on a public-domain mark
URL stays unknown. A photo credit, caption credit, or image credit that names
someone else's licence stays unknown. ``uk_ogl`` requires the British phrase
Open Government Licence. ``us_government_work`` requires an explicit rights
metadata field. Apache License, Version 2.0 is apache-2.0. Script, style, and
comment text does not count.

Updated, modified, and copyright years are not publication dates. This module
does not fetch. It is not a belief collector, and runner_wired stays false.
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

CATALOG_ID = "fas_ai_pages"
CATALOG_FILENAME = "fas_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Federation of American Scientists"
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
OFFICIAL_HOSTS = frozenset({"fas.org", "www.fas.org"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
# Discovery paths that a challenge, captcha, authentication wall, or robots
# disallow kept out of the catalog. Each one contributes no rows.
SKIPPED_CHALLENGE_PATHS: tuple[str, ...] = ()
CATALOG_DESCRIPTION = (
    "Metadata for public Federation of American Scientists pages about artificial intelligence, "
    "machine learning, or AI policy on fas.org and www.fas.org. Each row was confirmed with one "
    "bounded GET on those hosts. Challenges, captchas, login walls, donation pages, robots "
    "disallows, and unrelated topics are omitted. Rows store title, publisher, canonical URL, "
    "date, and rights. Page text is not stored. creative_commons_attribution is CC BY alone. "
    "creative_commons is CC0, CC BY-SA, or a permissive mix of those. A missing date is unknown. "
    "Updated, modified, and copyright years are not publication dates. This catalog is not a "
    "belief collector and runner_wired is false."
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
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_PUBLICATION_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_PAGE_DATE_TYPES = frozenset(
    {"webpage", "article", "newsarticle", "blogposting", "report", "scholarlyarticle"}
)
_RIGHTS_META = frozenset({"rights", "dc.rights", "dcterms.rights"})
_LICENSE_META = frozenset(
    {"license", "licence", "dcterms.license", "dcterms.licence"}
) | _RIGHTS_META
_TITLE_KEYS = ("og:title", "citation_title", "twitter:title", "dcterms.title")
_GENERIC_TITLES = frozenset({"federation of american scientists", "fas"})
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
    r"(?is)<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>"
)
_TAG = re.compile(r"(?is)<[^>]+>")
_META = re.compile(r"(?is)<meta\b[^>]*>")
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_ELEMENT = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_CREDIT_PHRASE = re.compile(r"(?i)\b(?:photo|caption|image)\s+credits?\b")
_CREDIT_CLOSE = re.compile(
    r"(?i)</(?:p|figcaption|li|div|h[1-6]|blockquote|section|article|td|dd|cite|span|small|figure)\b"
)
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_SITE_SUFFIXES = (
    " | federation of american scientists",
    " - federation of american scientists",
    " – federation of american scientists",
    " — federation of american scientists",
)
_PUBLISHER_WORD = re.compile(r"Federation of American Scientists")
_GENERIC_CC_HOSTS = frozenset({"creativecommons.org", "www.creativecommons.org"})
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EXACT_PATHS = frozenset(
    {
        "/initiative/artificial-intelligence",
        "/initiative/ai-x-global-risk-nexus-project",
        "/accelerator/source-code",
        "/accelerator/policy-ideas-for-a-safer-ai-future",
        "/accelerator/ai-energy-policy-sprint-2025",
        "/accelerator/ai-legislation",
        "/accelerator/bio-ai-policy-sprint",
        "/event/ai-global-risk-gala",
        "/event/ai-global-risk-summit",
        "/kbyg-ai-x-global-risk-summit",
        "/ai-x-global-risk-summit",
        "/fas-statement-on-generative-ai-use",
        "/day-one-project/emerging-tech",
    }
)
_TERM_SLUGS = frozenset(
    {
        "artificial-intelligence",
        "artifical-intelligence",
        "machine-learning",
        "ai-policy",
        "ai-safety",
        "ai-impact-awards",
        "ai-legislative-sprint",
        "ai-x-energy-sprint",
        "nist-ai-800-1",
        "deep-fakes",
        "aisi",
    }
)
AI_PUBLICATION_SLUGS = frozenset({
    "a-fair-artificial-intelligence-research-regulation-fairr-bureau",
    "a-focused-research-organization-for-superconducting-optoelectronic-intelligence",
    "a-national-ai-for-good-initiative",
    "a-national-center-for-advanced-ai-reliability-and-security",
    "a-national-framework-for-ai-procurement",
    "a-national-program-for-building-artificial-intelligence-within-communities",
    "a-national-training-program-for-ai-ready-students",
    "accelerating-ai-interpretability",
    "accelerating-materials-science-with-ai-and-robotics",
    "accelerating-rd-for-critical-ai",
    "adaptive-reuse-legacy-coal-infrastructure",
    "advance-ai-with-cleaner-air-and-healthier-outcomes",
    "advancing-american-ai-through-national-public-private-partnerships-for-ai-research",
    "ai-analyze-grant-data-science-frontiers",
    "ai-bills-house",
    "ai-corps-hhs-transformation",
    "ai-energy-climate-whats-at-stake",
    "ai-entrepreneur-visa-legislative-sprint",
    "ai-evaluation-clearinghouse",
    "ai-for-medicaid-initiative",
    "ai-for-science",
    "ai-health-care",
    "ai-in-action-help",
    "ai-in-education",
    "ai-sandcastles-skyscrapers",
    "ai-use-case-current-level-of-detail",
    "an-early-warning-system-for-ai",
    "analytical-literacy-first",
    "antitrust-in-the-ai-era",
    "artificial-intelligence-crs",
    "automating-scientific-discovery",
    "balanced-ai-in-education",
    "biden-artificial-intelligence-executive-order",
    "blank-checks-for-black-boxes",
    "cali-ai-governance-state-implementation",
    "childrens-online-voice-privacy",
    "codifying-expanding-continuous-ai-benchmarking",
    "collaborative-datasets-life-sciences",
    "community-benefit-agreements-data-center-development",
    "converging-risks-report-ai-impact-awards",
    "creating-an-ai-testbed-for-government",
    "creating-auditing-tools-for-ai-equity",
    "data-sharing-standards-healthcare",
    "decision-subject-representative-program-for-ai-systems",
    "digital-content-authentication-ecosystem",
    "dod-ai-crs",
    "enabling-responsible-u-s-leadership-on-global-ai-regulation",
    "enhancing-us-power-grid-by-using-ai-to-accelerate-permitting",
    "ensuring-child-safety-ai-era",
    "establishing-an-ai-incident-reporting-system",
    "expanding-state-local-capacity-ai-procurement",
    "fair-in-education-act",
    "faircare-verification",
    "fas-ansi-nist",
    "fas-opposes-ai-regulation-preemption",
    "federal-policy-recommendations-biology-to-harness-the-potential-of-artificial-intelligence",
    "fy24-ndaa-ai-tracker",
    "genaira",
    "grants-enhancing-state-local-ai-capacity",
    "guidance-platform-ai-acquisition",
    "healthcare-ai-tools",
    "how-do-openais-efforts-to-make-gpt-4-safer-stack-up-against-the-nist-ai-risk-management-framework",
    "improving-health-equity-through-ai",
    "innovation-in-ai-wont-wait",
    "leveraging-machine-learning-to-reduce-cost-burden-of-reviewing-research-proposals-at-s-t-agencies",
    "making-rural-communities-visible-ai",
    "measuring-and-standardizing-ais-energy-footprint",
    "modernizing-ai-fairness-analysis-in-education-contexts",
    "national-talent-surge-ai-era-teachers",
    "nist-ai-800-1",
    "nist-foundation",
    "nist-funding-responsible-ai",
    "omb-ai-use-case-inventories",
    "policy-agenda-fairness-trust-ai-source-code",
    "public-comment-executive-agency-handling-cai",
    "put-people-first-in-ai-decision-making",
    "reporting-ai-impact-to-build-public-trust",
    "rfi-development-of-artificial-intelligence-ai-action-plan",
    "risk-assessment-framework-ai-nuclear-weapons",
    "safe-harbor-for-ai-researchers",
    "scaling-ai-safety",
    "settlement-wins-digital-resilience-funds",
    "six-ideas-for-national-ai-strategy",
    "source-code-launch-blog",
    "speed-grid-connection-smart-ai-fast-lanes",
    "strengthening-information-integrity-provenance",
    "student-safety-ai-procurement-guardrails",
    "teacher-ai-literacy-development",
    "teacher-education-clearinghouse-for-ai-and-data-science",
    "tracking-ai-provisions-in-fy24-appropriations-bills",
    "trump-administrations-ai-action-plan",
    "trust-issues",
    "unlocking-ai-grid-modernization-potential",
    "unlocking-american-competitiveness-ai-eo",
})
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
    ".ico",
)
_LOGIN_MARKERS = (
    "/login",
    "/log-in",
    "/signin",
    "/sign-in",
    "/account",
    "/wp-login",
    "/wp-admin",
    "/users/sign_in",
)
_DONATE_MARKERS = ("/donate", "/donation", "/donations", "/give")
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
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "errors.edgesuite.net",
    "are you a robot",
    "are you human",
)
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
# Longer deeds are listed first. A hyphen continues the token, so CC BY does
# not match CC BY-NC and licenses/by does not match licenses/by-nc.
_TEXT_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("by-nc-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*nd(?![a-z0-9])")),
    (
        "by-nc-nd",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*no[\s-]*deriv"),
    ),
    ("by-nc-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc[\s-]*sa(?![a-z0-9])")),
    (
        "by-nc-sa",
        re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial[\s-]*share[\s-]*alike"),
    ),
    ("by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![a-z0-9])")),
    ("by-nc", re.compile(r"creative commons attribution[\s-]*non[\s-]*commercial")),
    ("by-nd", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nd(?![a-z0-9])")),
    ("by-nd", re.compile(r"creative commons attribution[\s-]*no[\s-]*deriv")),
    ("by-sa", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*sa(?![a-z0-9])")),
    ("by-sa", re.compile(r"creative commons attribution[\s-]*share[\s-]*alike")),
    ("zero", re.compile(r"(?<![a-z0-9])(?:cc[\s-]*0|cc[\s-]*zero)(?![a-z0-9])")),
    ("zero", re.compile(r"creative commons(?:\s+public\s+domain)?[\s-]*zero(?![a-z])")),
    ("by", re.compile(r"(?<![a-z0-9])cc[\s-]*by(?!-)(?![a-z0-9])")),
    (
        "by",
        re.compile(r"creative commons attribution(?![\s-]*(?:non|no[\s-]*deriv|share))"),
    ),
    ("mark", re.compile(r"public domain mark")),
)
_URL_DEEDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("by-nc-nd", re.compile(r"creativecommons\.org/licenses/by-nc-nd(?![a-z0-9-])")),
    ("by-nc-sa", re.compile(r"creativecommons\.org/licenses/by-nc-sa(?![a-z0-9-])")),
    ("by-nc", re.compile(r"creativecommons\.org/licenses/by-nc(?![a-z0-9-])")),
    ("by-nd", re.compile(r"creativecommons\.org/licenses/by-nd(?![a-z0-9-])")),
    ("by-sa", re.compile(r"creativecommons\.org/licenses/by-sa(?![a-z0-9-])")),
    ("by", re.compile(r"creativecommons\.org/licenses/by(?!-)(?![a-z0-9])")),
    ("zero", re.compile(r"creativecommons\.org/publicdomain/zero(?![a-z0-9-])")),
    ("mark", re.compile(r"creativecommons\.org/publicdomain/mark(?![a-z0-9-])")),
)
_RESTRICTED = frozenset({"by-nc", "by-nd", "by-nc-sa", "by-nc-nd"})
_PERMISSIVE = frozenset({"by", "by-sa", "zero"})
_RESTRICTED_TOKENS = {
    "by-nc": RIGHTS_CC_BY_NC,
    "by-nd": RIGHTS_CC_BY_ND,
    "by-nc-sa": RIGHTS_CC_BY_NC_SA,
    "by-nc-nd": RIGHTS_CC_BY_NC_ND,
}
_OGL_PHRASE = re.compile(r"open government licence(?![a-z])")
_US_GOV_WORK = re.compile(r"\b(?:united states|u\.s\.|us)\s+government\s+work\b")
_NEGATED_US_GOV = re.compile(r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+work\b")
_MIT = re.compile(r"\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit licen[cs]e\b")
_MIT_URL = re.compile(r"(?:opensource\.org/licenses/mit|spdx\.org/licenses/mit)(?![a-z0-9-])")
_APACHE = re.compile(
    r"(?<![a-z0-9])apache-2\.0(?![a-z0-9])|\bapache licen[cs]e(?:\s*,?\s*version)?\s*2\.0\b"
)
_APACHE_URL = re.compile(
    r"(?:apache\.org/licenses/license-2\.0|spdx\.org/licenses/apache-2\.0)(?![a-z0-9-])"
)
_MPL = re.compile(r"(?<![a-z0-9])mpl-2\.0(?![a-z0-9])|\bmozilla public licen[cs]e\s*2\.0\b")
_MPL_URL = re.compile(r"(?:mozilla\.org/mpl/2\.0|spdx\.org/licenses/mpl-2\.0)(?![a-z0-9-])")
_ROBOTS_END = "$"


class CatalogError(ValueError):
    """A catalog row or page failed the Federation of American Scientists page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for fas.org and www.fas.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_topic_path(path: str) -> bool:
    """True for an AI, machine-learning, or AI-policy HTML path on the official hosts."""

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    if ".." in path or "//" in path or "\\" in path or "%" in path:
        return False
    lowered = path.casefold()
    bare = lowered[:-1] if lowered.endswith("/") and lowered != "/" else lowered
    if bare.endswith(_DOWNLOAD_SUFFIXES) or bare.endswith("/feed"):
        return False
    if any(bare == marker or bare.startswith(marker + "/") for marker in _LOGIN_MARKERS):
        return False
    if any(bare == marker or bare.startswith(marker + "/") for marker in _DONATE_MARKERS):
        return False
    if bare == "/search" or bare.startswith("/search/"):
        return False
    if bare in _EXACT_PATHS:
        return True
    parts = [part for part in bare.split("/") if part]
    if len(parts) == 2 and parts[0] == "publication-term" and parts[1] in _TERM_SLUGS:
        return True
    if len(parts) == 2 and parts[0] == "publication" and parts[1] in AI_PUBLICATION_SLUGS:
        return _SLUG.fullmatch(parts[1]) is not None
    return False


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    return content_type.split(";", 1)[0].strip().casefold() in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page."""

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    sample = page_html[:12000].casefold()
    title_match = _TITLE.search(sample)
    title = _plain(title_match.group(1)).casefold() if title_match else ""
    return any(marker in sample[:4000] or marker in title for marker in _CHALLENGE_MARKERS)


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
    headers: Mapping[str, str] | None = None,
    final_url: str | None = None,
    requested_urls: list[str] | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a block or challenge."""

    if isinstance(status, bool) or not isinstance(status, int) or status != 200:
        return False
    if not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    if headers and _blocked_headers(headers):
        return False
    urls = list(requested_urls or [])
    if final_url:
        urls.append(final_url)
    for url in urls:
        if not _on_official_host(url):
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
    requested_urls: list[str] | None = None,
    robots_text: str | None = None,
) -> dict | None:
    """Return metadata when one bounded GET confirmed an on-topic page.

    A challenge, a captcha, a non-HTML body, a robots disallow, a login page,
    a donation page, or an off-host redirect is not stored.
    """

    if robots_text is not None:
        for url in [page_url, *(requested_urls or []), final_url or ""]:
            if not url:
                continue
            if not robots_allows_path(robots_text, _robots_path(url)):
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
    stored_url = final_url or page_url
    try:
        return page_record(page_html, page_url=stored_url)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    A hyphen is a word boundary, so CC BY-NC is not CC BY. Anchor text on a
    generic creativecommons.org/licenses URL does not count, including CC BY,
    CC BY 4.0, and CC BY-SA. A missing trailing slash, http, a www host, and
    a query string on that path stay unknown. Text elsewhere still counts. A
    specific deed URL still counts. Deceptive permissive anchor text on a
    restricted or public-domain mark URL stays unknown, including a CC0
    anchor on a public-domain mark URL. A photo, caption, or image credit
    that names someone else's licence stays unknown. A software licence beside
    any Creative Commons deed stays unknown. Two software licences stay
    unknown. Two different restricted deeds stay unknown. Script, style, and
    comment text does not count. Apache License, Version 2.0 is apache-2.0.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    visible = _without_image_credits(_without_hidden(page_text))
    kept = _without_generic_cc_license_anchors(visible)
    plain = _plain(kept).casefold().translate(_DASHES)
    blobs = [plain]
    for key, content in _meta_pairs(visible):
        if key in _LICENSE_META:
            blobs.append(_plain(content).casefold().translate(_DASHES))
    for key_name in ("license", "licence", "rights"):
        for raw in _jsonld_values(page_text, key_name):
            blobs.append(_plain(raw).casefold().translate(_DASHES))
    codes: set[str] = set()
    for blob in blobs:
        codes |= _text_codes(blob)
        codes |= _url_codes(blob)
    for href in _hrefs(kept):
        folded = unescape(href).casefold().translate(_DASHES)
        codes |= _url_codes(folded)
    scanned = " ".join(blobs + [unescape(href).casefold() for href in _hrefs(kept)])
    mit = bool(_MIT.search(scanned) or _MIT_URL.search(scanned))
    apache = bool(_APACHE.search(scanned) or _APACHE_URL.search(scanned))
    mpl = bool(_MPL.search(scanned) or _MPL_URL.search(scanned))
    return _label(
        codes,
        mit=mit,
        apache=apache,
        mpl=mpl,
        ogl=bool(_OGL_PHRASE.search(plain)),
        us_gov=_states_us_government_work(page_text),
    )


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    datePublished, article:published_time, and citation_publication_date count.
    article:modified_time, og:updated_time, dateModified, an updated or
    modified label, and a copyright year do not. Disagreeing publication
    dates stay unknown. Script text that is not publication metadata does
    not count.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    found: list[str] = []
    for raw in _page_date_published_values(page_html):
        parsed = _iso_day(raw)
        if parsed:
            found.append(parsed)
    visible = _without_hidden(page_html)
    for key, content in _meta_pairs(visible):
        if key not in _PUBLICATION_META:
            continue
        parsed = _iso_day(content)
        if parsed:
            found.append(parsed)
    distinct = set(found)
    if len(distinct) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in _TITLE_KEYS:
        title = _usable_title(metas.get(key, ""))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _usable_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    heading = _H1.search(visible)
    if heading:
        title = _usable_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return Federation of American Scientists when the page states that name."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site == PUBLISHER:
        return PUBLISHER
    if _PUBLISHER_WORD.search(_plain(visible)):
        return PUBLISHER
    for key in ("citation_publisher", "publisher"):
        if _PUBLISHER_WORD.search(_metas(visible).get(key, "")):
            return PUBLISHER
    raise CatalogError("publisher is required")


def page_record(page_html: str, *, page_url: str) -> dict:
    """Return metadata for one confirmed page.

    The record does not include the document body. ``page_url`` is the live
    URL that returned HTML. A rel=canonical pointing somewhere else is not used.
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
    return validate_entry(record)


def validate_catalog(document: dict) -> dict:
    if not isinstance(document, dict):
        raise CatalogError("catalog must be an object")
    _reject_stored_body(document)
    if set(document) != _CATALOG_FIELDS:
        raise CatalogError("catalog fields must be catalog_id, description, runner_wired, and entries")
    if document.get("catalog_id") != CATALOG_ID:
        raise CatalogError(f"catalog_id must be {CATALOG_ID}")
    description = document.get("description")
    if description != CATALOG_DESCRIPTION:
        raise CatalogError("description must match the catalog contract")
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
    _require_text(entry.get("title"), "title", MAX_TEXT_CHARS)
    if entry.get("publisher") != PUBLISHER:
        raise CatalogError(f"publisher must be {PUBLISHER}")
    validate_canonical_url(entry.get("canonical_url"))
    validate_date(entry.get("date"))
    if entry.get("rights") not in RIGHTS_LABELS:
        raise CatalogError("rights must be a known label or unknown")
    return entry


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or _DATE.fullmatch(value) is None or _iso_day(value) is None:
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public Federation of American Scientists AI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or not is_official_host(host)
        or parsed.netloc.lower() != host
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or path != path.casefold()
        or not is_topic_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public Federation of American Scientists AI page: {url}")
    return url


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and is_official_host(parsed.hostname or "")


def _robots_path(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def _blocked_headers(headers: Mapping[str, str]) -> bool:
    for key, value in headers.items():
        name = str(key).casefold()
        token = str(value).casefold()
        if name == "cf-mitigated" and "challenge" in token:
            return True
        if name in {"sg-captcha", "x-captcha"}:
            return True
        if "captcha" in name:
            return True
    return False


def _label(
    codes: set[str],
    *,
    mit: bool,
    apache: bool,
    mpl: bool,
    ogl: bool,
    us_gov: bool,
) -> str:
    if "mark" in codes:
        return RIGHTS_UNKNOWN
    restricted = codes & _RESTRICTED
    permissive = codes & _PERMISSIVE
    families = [
        name
        for name, present in (
            ("restricted", bool(restricted)),
            ("permissive", bool(permissive)),
            ("mit", mit),
            ("apache", apache),
            ("mpl", mpl),
            ("ogl", ogl),
            ("us", us_gov),
        )
        if present
    ]
    if len(families) != 1:
        return RIGHTS_UNKNOWN
    if restricted:
        if len(restricted) != 1:
            return RIGHTS_UNKNOWN
        return _RESTRICTED_TOKENS[next(iter(restricted))]
    if permissive:
        if permissive == {"by"}:
            return RIGHTS_CC_ATTRIBUTION
        if permissive <= _PERMISSIVE and permissive & {"by-sa", "zero"}:
            return RIGHTS_CREATIVE_COMMONS
        return RIGHTS_UNKNOWN
    if mit:
        return RIGHTS_MIT
    if apache:
        return RIGHTS_APACHE
    if mpl:
        return RIGHTS_MPL
    if ogl:
        return RIGHTS_UK_OGL
    if us_gov:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def _text_codes(folded: str) -> set[str]:
    found: list[tuple[int, int, str]] = []
    for code, pattern in _TEXT_DEEDS:
        for match in pattern.finditer(folded):
            start, end = match.span()
            if any(start < prev_end and end > prev_start for prev_start, prev_end, _code in found):
                continue
            found.append((start, end, code))
    return {code for _start, _end, code in found}


def _url_codes(value: str) -> set[str]:
    found: set[str] = set()
    for code, pattern in _URL_DEEDS:
        if pattern.search(value):
            found.add(code)
    return found


def _states_us_government_work(page_html: str) -> bool:
    """True only when a rights metadata field says the item is a US government work."""

    visible = _without_hidden(page_html)
    fields = [content for key, content in _meta_pairs(visible) if key in _RIGHTS_META]
    fields.extend(_jsonld_values(page_html, "rights"))
    for raw in fields:
        text = _plain(raw).casefold().translate(_DASHES)
        if not text or _NEGATED_US_GOV.search(text):
            continue
        if _US_GOV_WORK.search(text):
            return True
    return False


def _page_date_published_values(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        nodes: list[object]
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            nodes = list(payload["@graph"])
        elif isinstance(payload, list):
            nodes = list(payload)
        else:
            nodes = [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            types = node.get("@type", "")
            if isinstance(types, str):
                types = [types]
            if not isinstance(types, list):
                continue
            names = {str(item).casefold() for item in types}
            if not names & _PAGE_DATE_TYPES:
                continue
            raw = node.get("datePublished")
            if isinstance(raw, str):
                found.append(raw)
    return found


def _jsonld_values(page_html: str, key: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _collect_key(payload, key.casefold(), found)
    return found


def _collect_key(payload: object, key: str, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_key(item, key, found)
        return
    if not isinstance(payload, dict):
        return
    for name, value in payload.items():
        if str(name).casefold() == key and isinstance(value, str):
            found.append(value)
        elif isinstance(value, (dict, list)):
            _collect_key(value, key, found)


def _without_image_credits(page_html: str) -> str:
    """Drop photo, caption, and image credit sentences, including links inside them.

    A credit such as ``Photo credit: UNDRR, CC BY-NC-ND 2.0.`` is someone
    else's licence for an image. It is not a licence for the page. A decimal
    in a version number does not end the sentence.
    """

    out: list[str] = []
    cursor = 0
    while cursor < len(page_html):
        match = _CREDIT_PHRASE.search(page_html, cursor)
        if match is None:
            out.append(page_html[cursor:])
            break
        previous_open = page_html.rfind("<", cursor, match.start())
        previous_close = page_html.rfind(">", cursor, match.start())
        if previous_open > previous_close:
            out.append(page_html[cursor:match.end()])
            cursor = match.end()
            continue
        out.append(page_html[cursor:match.start()])
        index = match.end()
        while index < len(page_html):
            if page_html[index] == "<":
                if _CREDIT_CLOSE.match(page_html, index) or re.match(r"(?i)<br\b", page_html[index:]):
                    break
                end = page_html.find(">", index)
                if end == -1:
                    index = len(page_html)
                    break
                index = end + 1
                continue
            if page_html[index] == ".":
                nxt = page_html[index + 1] if index + 1 < len(page_html) else ""
                if nxt.isdigit():
                    index += 1
                    continue
                index += 1
                break
            index += 1
        cursor = index
    return "".join(out)


def _is_generic_cc_licenses_url(href: str) -> bool:
    """True for the Creative Commons licences index, not a deed.

    http and https, a www host, a missing trailing slash, and a query string
    stay on that generic path. A schemeless creativecommons.org/licenses URL
    is the same index. A deed such as /licenses/by/4.0/ is not.
    """

    text = unescape(href or "").strip()
    if not text:
        return False
    if text.startswith("//"):
        text = "https:" + text
    elif "://" not in text:
        bare = text.lstrip("/")
        lowered = bare.casefold()
        if lowered.startswith("creativecommons.org") or lowered.startswith("www.creativecommons.org"):
            text = "https://" + bare
        else:
            return False
    parsed = urlparse(text)
    if parsed.scheme.casefold() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host not in _GENERIC_CC_HOSTS:
        return False
    path = (parsed.path or "").casefold()
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path == "/licenses"


def _without_generic_cc_license_anchors(page_html: str) -> str:
    """Drop anchors whose href is only the generic licences index.

    The visible text of that anchor, including CC BY, CC BY 4.0, and CC BY-SA,
    is not a licence statement. Other text on the page is left in place.
    """

    def replace(match: re.Match[str]) -> str:
        href = _attrs("<a" + match.group(1) + ">").get("href", "")
        if _is_generic_cc_licenses_url(href):
            return " "
        return match.group(0)

    return _ANCHOR_ELEMENT.sub(replace, page_html)


def _iso_day(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    match = _DATE_PREFIX.match(raw.strip())
    if match is None:
        return None
    value = match.group(1)
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


def _require_text(value: object, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CatalogError(f"{field} is required")
    if len(value) > max_length or "<" in value or ">" in value or "\n" in value:
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
        if len(value) > MAX_DESCRIPTION_CHARS and path != "$.description":
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _usable_title(value: str) -> str:
    title = _clean_title(value)
    if not title or title.casefold() in _GENERIC_TITLES:
        return ""
    return title


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    lowered = text.casefold()
    changed = True
    while changed and text:
        changed = False
        for suffix in _SITE_SUFFIXES:
            if lowered.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                lowered = text.casefold()
                changed = True
                break
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _without_hidden(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, content in _meta_pairs(page_html):
        found.setdefault(key, content)
    return found


def _meta_pairs(page_html: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and attrs.get("content"):
            found.append((key, attrs["content"]))
    return found


def _hrefs(page_html: str) -> list[str]:
    found: list[str] = []
    for tag in _LINK.findall(page_html):
        href = _attrs(tag).get("href", "")
        if href:
            found.append(href)
    return found


def _attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, double, single, bare in _ATTR.findall(tag):
        raw = double or single or bare
        attrs.setdefault(name.lower(), unescape(raw).strip())
    return attrs


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
    wildcard: list[tuple[str, str]] = []
    saw_wildcard = False
    for agents, rules in groups:
        matched_specific = False
        for agent in agents:
            if agent == "*":
                saw_wildcard = True
                wildcard.extend(rules)
                continue
            if product.startswith(agent) or (haystack.startswith(agent) and agent):
                matched_specific = True
        if matched_specific:
            specific.append((max(len(agent) for agent in agents if agent != "*"), rules))
    if specific:
        return max(specific, key=lambda item: item[0])[1]
    if saw_wildcard:
        return wildcard
    return None


def _path_allowed(rules: list[tuple[str, str]], path: str) -> bool:
    allowed = -1
    disallowed = -1
    for kind, pattern in rules:
        if not pattern or not _robots_pattern_matches(pattern, path):
            continue
        weight = len(pattern)
        if kind == "allow":
            allowed = max(allowed, weight)
        else:
            disallowed = max(disallowed, weight)
    if allowed < 0 and disallowed < 0:
        return True
    return allowed >= disallowed


def _robots_pattern_matches(pattern: str, path: str) -> bool:
    anchored = pattern.endswith(_ROBOTS_END)
    body = pattern[:-1] if anchored else pattern
    parts: list[str] = []
    for char in body:
        if char == "*":
            parts.append(".*")
        else:
            parts.append(re.escape(char))
    expression = "".join(parts)
    if anchored:
        return re.search(f"^{expression}$", path) is not None
    return re.search(f"^{expression}", path) is not None
