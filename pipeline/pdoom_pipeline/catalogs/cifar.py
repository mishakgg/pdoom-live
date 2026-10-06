"""Metadata catalog of public CIFAR pages about artificial intelligence.

Hosts are cifar.ca and www.cifar.ca. www.cifar.ca redirects to cifar.ca, so a
stored URL is the page that returned HTML on one of those hosts. Pages are
limited to artificial intelligence, machine learning, and the Pan-Canadian AI
Strategy. Unrelated CIFAR programs, login walls, and donation pages are
omitted. A Cloudflare challenge, a captcha, an authentication wall, or a
robots disallow stores no row.

Each stored URL was confirmed with one bounded GET. A row keeps the title,
publisher, canonical URL, date, and rights label. Page text, abstracts, PDFs,
quotes, transcripts, and chart data are not stored. Publisher is CIFAR.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is CC0,
CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND, CC BY-NC-SA,
or CC BY-NC-ND keeps its own token. Two different restricted deeds stay
unknown. A software licence beside any Creative Commons deed stays unknown.
Two software licences stay unknown. ``mit``, ``apache-2.0``, and ``mpl-2.0``
are sole software licences. Apache License, Version 2.0 is ``apache-2.0``.
``uk_ogl`` is only the British phrase Open Government Licence.
``us_government_work`` comes only from an explicit rights metadata field.

A generic creativecommons.org/licenses or /licenses/ URL is not a deed. Anchor
text on it, including CC BY, CC BY 4.0, and CC BY-SA, stays unknown. That
covers a missing slash, http, a www host, and a query string. A specific deed
URL still counts. Text elsewhere on the page still counts. Deceptive
permissive anchor text on a restricted deed URL or a public-domain mark URL
stays unknown. A CC0 anchor on a public-domain mark URL stays unknown. A
photo credit, caption credit, or image credit that names someone else's
licence stays unknown. Publication dates only are kept. Modified, updated,
and copyright years stay unknown. Script, style, and comment text does not
count.

This module does not fetch. It is not a belief collector, and runner_wired
stays false.
"""

from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from pdoom_pipeline.urls import hostname_is_blocked

CATALOG_ID = "cifar_ai_pages"
CATALOG_FILENAME = "cifar_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "CIFAR"
UNKNOWN_DATE = "unknown"
OFFICIAL_HOSTS = frozenset({"cifar.ca", "www.cifar.ca"})
CATALOG_DESCRIPTION = (
    "Public CIFAR pages on artificial intelligence, machine learning, and the Pan-Canadian AI Strategy. "
    "Hosts are cifar.ca and www.cifar.ca. Each URL was one bounded GET. "
    "Challenges, logins, donations, robots disallows, and other programs are omitted. "
    "Rows store title, publisher, canonical URL, date, and rights. "
    "Bodies, abstracts, PDFs, quotes, transcripts, and chart data are not stored. "
    "Publisher is CIFAR. creative_commons_attribution is CC BY alone. "
    "creative_commons is CC0, CC BY-SA, or a permissive mix of those. "
    "Sole restricted deeds keep their tokens. Mixed deeds stay unknown. "
    "uk_ogl is the British Open Government Licence. us_government_work needs a rights field. "
    "Missing dates stay unknown. Updated, modified, and copyright years are not dates. "
    "Not a belief collector. runner_wired is false."
)

RIGHTS_UNKNOWN = "unknown"
RIGHTS_CREATIVE_COMMONS = "creative_commons"
RIGHTS_CREATIVE_COMMONS_ATTRIBUTION = "creative_commons_attribution"
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
        RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
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
MAX_FIELD_CHARS = 500
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
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_COMMENT = re.compile(r"(?is)<!--.*?-->")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")
_LDJSON = re.compile(
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
_PUBLISHED_META = (
    "article:published_time",
    "citation_publication_date",
    "dcterms.issued",
    "dc.date.issued",
)
_PUBLISHED_TYPES = frozenset(
    {
        "aboutpage",
        "article",
        "blogposting",
        "collectionpage",
        "newsarticle",
        "report",
        "scholarlyarticle",
        "webpage",
    }
)
_RIGHTS_META = frozenset(
    {
        "dc.rights",
        "dcterms.license",
        "dcterms.licence",
        "dcterms.rights",
        "licence",
        "license",
        "rights",
    }
)
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "enable javascript and cookies",
    "challenge-platform",
    "/cdn-cgi/challenge-platform/",
    "cf-mitigated",
    "checking your browser",
    "attention required",
    "sorry, you have been blocked",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha",
    "errors.edgesuite.net",
    "akamaighost",
    "are you a robot",
    "are you human",
)
_DOWNLOAD_SUFFIXES = (
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".json",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".svg",
    ".webp",
    ".xml",
    ".zip",
)
_BLOCKED_PARTS = frozenset(
    {
        "account",
        "auth",
        "donate",
        "donatenow",
        "donatenow-corporate",
        "donatenow-us",
        "donation",
        "donation-thank-you",
        "log-in",
        "login",
        "pcaistest",
        "pcaistestfrench",
        "sign-in",
        "sign-up",
        "signin",
        "signup",
        "test",
        "wp-admin",
        "wp-content",
        "wp-json",
        "wp-login",
        "wp-login.php",
    }
)
_AI_PREFIXES = (
    "/ai",
    "/fr/ia",
    "/topics/cifar-pan-canadian-ai-strategy",
    "/fr/sujets/strategie-pancanadienne-en-matiere-dia",
    "/cifarnews/ai_strategy",
    "/fr/cifarnews/ai_strategy",
)
_EXACT_PATHS = frozenset(
    {
        "/research-programs/learning-in-machines-brains",
        "/fr/programmes-de-recherche/apprentissage-automatique-apprentissage-biologiques",
        "/topics/research/learning-in-machines-brains",
        "/accelerating-climate-solutions-through-ai",
        "/fr/les-changements-climatiques-et-lutilisation-de-lia",
        "/international-roundtable-on-ai-and-covid-19",
        "/fr/table-ronde-internationale-sur-lia-et-la-covid-19",
        "/next-generation/training-programs/deep-learning-reinforcement-learning-summer-school",
        "/fr/initiatives-a-lintention-de-la-prochaine-generation/programmes-de-formation/ecole-dete-sur-lapprentissage-profond-et-lapprentissage-par-renforcement",
        "/next-generation/cifar-ai-frontiers-school",
        "/fr/initiatives-a-lintention-de-la-prochaine-generation/ecole-frontieres-de-lia-du-cifar",
        "/action-on-covid-19/ai-and-covid-19-catalyst-grants",
        "/fr/mesures-de-lutte-contre-la-covid-19/subventions-catalyseur-ia-covid-19",
        "/use-of-generative-ai-by-applicants",
        "/use-of-generative-ai-in-the-review-of-applications-reviewers",
        "/fr/utilisation-de-lia-generative-par-les-candidates-et-candidats",
        "/fr/utilisation-de-lia-generative-dans-levaluation-des-demandes-evaluatrices-et-evaluateurs",
        "/publications-reports/reach/ai-powered-robots",
        "/fr/publications-et-rapports/la-revue-reach/robots-dintelligence-artificielle",
    }
)
_NEXTGEN_PREFIXES = (
    "/cifarnews/nextgen-initiative",
    "/fr/cifarnews/nextgen-initiative",
)
_NEWS_PATH = re.compile(
    r"^/(?:fr/)?cifarnews/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[a-z0-9-]+)$"
)
_SITE_SUFFIXES = (
    " | CIFAR",
    " - CIFAR",
    " – CIFAR",
    " — CIFAR",
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
}
_PUBLISHED_ISO = re.compile(r"(?i)(?<![a-z])published\s*:\s*(\d{4}-\d{2}-\d{2})\b")
_PUBLISHED_MONTH = re.compile(
    r"(?i)(?<![a-z])published\s*:\s*"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+(\d{1,2}),\s+(\d{4})\b"
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
# Longer deeds are listed first. `(?!-)` keeps licenses/by from matching
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
        re.compile(r"creative commons attribution[\s-]+non[\s-]*commercial[\s-]+share[\s-]*alike"),
    ),
    ("cc-by-nc", re.compile(r"(?<![a-z0-9])cc[\s-]*by[\s-]*nc(?![\s-]*(?:sa|nd)\b)")),
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
_MIT = re.compile(
    r"\bmit licen[cs]e\b"
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
    r"|\bmozilla public licen[cs]e(?:\s*2\.0)?\b"
)
_OGL_PHRASE = "open government licence"
_GOV_WORK = re.compile(
    r"\b(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\b(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_NEGATED_GOV_WORK = re.compile(
    r"\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
    r"|\bnot\s+(?:a\s+)?(?:united\s+states|u\.s\.|us)\s+government\s+works?\b"
)
_ANCHOR = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_HREF_ATTR = re.compile(
    r"""(?is)\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
# A deed path such as /licenses/by/4.0/ is not generic. Optional slash, query,
# http, and a www host still leave the URL generic.
_GENERIC_CC_LICENSES = re.compile(
    r"^(?:https?:)?//(?:www\.)?creativecommons\.org/licenses/?(?:\?[^#]*)?(?:#.*)?$"
)
# Photo, caption, and image credits name someone else's licence. A parenthetical
# "(Credit: ...)" on a figure is the same kind of credit.
_CREDIT_PHRASE = re.compile(
    r"(?i)(?:\b(?:photo|caption|image)\s+credit\b|\(\s*credit\s*:)"
)
_CREDIT_BLOCK_CLOSE = re.compile(
    r"(?is)</(?:p|figcaption|li|caption|figure|blockquote|dd|div)\s*>"
)
_AI_TOKENS = frozenset({"ai", "aican", "ai4good", "ia"})
_AI_PHRASES = (
    "machine-learning",
    "deep-learning",
    "reinforcement-learning",
    "artificial-intelligence",
    "generative-ai",
    "apprentissage-profond",
    "apprentissage-par-renforcement",
    "apprentissage-automatique",
    "intelligence-artificielle",
    "lia-responsable",
    "sur-lia",
    "en-ia",
)
# Confirmed news slugs from the Pan-Canadian AI Strategy and Learning in
# Machines & Brains categories. A dated /cifarnews/ path is stored only when
# its slug is one of these.
_NEWS_SLUGS = frozenset({
    "a-recipe-for-canada-s-ai-revolution",
    "the-economist-the-founding-of-maple-valley",
    "dr-elissa-strome-appointed-to-head-cifar-pan-canadian-ai-strategy",
    "cifar-announces-distinguished-advisory-committee-for-125m-pan-canadian-artificial-intelligence-strategy",
    "canada-s-ai-explosion-visit-three-labs-where-machines-are-being-taught-to-think-like-people",
    "cifar-launches-ai-society-workshop-call-for-proposals",
    "ai-success-holds-innovation-lessons-for-canada",
    "a-quantum-shield-to-protect-cryptocurrencies",
    "the-leading-edge",
    "q-a-with-yoshua-bengio",
    "canada-france-and-the-uk-join-forces-to-examine-the-social-and-ethical-dimensions-of-artificial-intelligence",
    "cifar-summer-school-brings-together-the-next-generation-of-ai-researchers",
    "cifar-announces-winning-ai-society-workshops",
    "accountability-in-ai-promoting-greater-social-trust",
    "building-an-ai-world-report-on-national-and-regional-ai-strategies",
    "amii-s-alona-fyshe-on-what-it-means-to-be-appointed-a-ccai",
    "turing-award-honours-cifar-s-pioneers-of-ai",
    "understanding-intelligence",
    "annual-report-of-the-cifar-pan-canadian-ai-strategy",
    "cifar-announces-new-research-programs-and-ai-chairs",
    "cifar-expands-canada-cifar-ai-chairs-program-to-46",
    "canada-france-uk-launch-research-workshops-exploring-societal-implications-of-artificial-intelligence",
    "three-cifar-fellows-earn-prestigious-killam-program-awards",
    "understanding-machine-behaviour",
    "ai-society-workshop-explores-the-risks-of-ai-on-children",
    "new-partnership-to-create-more-opportunities-for-women-in-artificial-intelligence-for-good",
    "members-of-cifar-community-to-advise-canada-on-ai",
    "the-memory-hunters",
    "in-conversation-canadas-role-in-the-future-of-artificial-intelligence",
    "ai-futures-policy-labs-engage-policy-leaders-in-understanding-the-future-policy-implications-of-ai",
    "how-canada-is-supporting-the-next-generation-of-women-ai-leaders",
    "media-advisory-dlrl-summer-school-brings-global-ai-experts-to-canada",
    "the-world-s-top-ai-talent-convene-in-edmonton-for-the-dlrl-summer-school",
    "ethical-ai-a-discussion",
    "in-memoriam-ian-kerr-1965-2019",
    "creating-smart-computers-using-the-human-brain",
    "ai-research-detects-online-trolls-in-canadian-election",
    "cifar-receives-grant-from-alfred-p-sloan-foundation-to-support-research-for-more-versatile-ai-systems",
    "the-brains-behind-ai",
    "ai-researcher-pioneers-new-subfield-of-ai",
    "canada-s-top-international-ai-talent-grows-to-80",
    "outsmarting-humans-at-their-own-game",
    "the-art-of-ai-conversation",
    "the-centre-of-the-ai-universe",
    "report-on-canada-us-ai-symposium-on-economic-innovation",
    "ai-research-enables-astronomy-breakthrough",
    "ai-training-program-for-women-launches-in-edmonton",
    "cifar-receives-grant-from-alfred-p-sloan-foundation-to-support-research-for-more-versatile-ai-systems-2",
    "using-ai-to-track-cancer-evolution",
    "training-ai-to-reason",
    "building-an-ai-world-report-on-national-and-regional-ai-strategies-2nd-edition",
    "cifar-funds-nine-high-risk-high-reward-ai-projects",
    "building-a-learning-health-system-for-canadians",
    "centering-indigenous-perspectives-in-designing-ai",
    "social-connection-key-to-human-wellbeing-and-survival",
    "empowering-machines-with-lifelong-learning",
    "training-ai-qa-with-chelsea-finn",
    "sanja-fidler-is-taking-data-to-the-next-level-with-ai-assisted-annotation-tool",
    "an-ai-for-health-strategy-will-be-a-gamechanger-for-canada",
    "ai-pioneer-joelle-pineau-is-transforming-personalized-health-care",
    "ai-radiology-tool-supports-real-time-diagnosis-of-covid-19-related-pneumonia",
    "playing-the-long-game-with-ai",
    "a-look-toward-2030",
    "ontario-researchers-use-ai-to-diagnose-and-treat-covid-19",
    "canada-cifar-ai-chairs-program-surges-past-100",
    "four-ai-researchers-to-watch-in-2021",
    "ai-health-care-a-fusion-of-law-science",
    "a-focus-on-ethics-in-ai-research",
    "a-culture-of-ethical-ai",
    "ai-in-biodiversity-research-crucial-to-our-survival",
    "ai-holds-promise-for-our-other-global-threats-energy-and-the-environment",
    "ai-health-care-a-fusion-of-law-science-part-two",
    "recommendation-algorithms-could-contribute-to-inequality",
    "global-research-network-to-boost-economic-opportunities-for-women-agricultural-workers-in-india",
    "ai-talent-in-western-canada-grows",
    "leading-with-generosity",
    "irina-rish-wants-to-solve-one-of-ais-biggest-challenges",
    "worlds-premier-ai-training-program-welcomes-300-students-from-around-the-world",
    "predicting-the-perfect-storm",
    "equity-diversity-and-inclusion-in-ai-climate-change-research-2",
    "reducing-discrimination-and-bias-in-ai-qa-with-golnoosh-farnadi",
    "artificial-intelligence-ai-provides-sustainable-solutions-for-clean-drinking-water-in-rural-community",
    "cifar-and-mila-name-five-new-canada-cifar-ai-chairs",
    "5-rising-stars-the-ai-pathfinder-2",
    "leaps-and-boundaries",
    "mou-between-cifar-the-nrc-and-canadas-three-national-ai-institutes-opens-doors-to-collaboration-across-sectors",
    "catalyst-grants-announced-for-four-collaborative-projects-using-synthetic-data-for-better-health-research",
    "ai4good-lab-expands-to-three-canadian-cities",
    "cifar-announces-plans-for-second-phase-of-the-pan-canadian-artificial-intelligence-strategy",
    "what-steps-can-organizers-of-ai-conferences-take-to-encourage-reflection-on-the-societal-impacts-of-ai-research",
    "believe-the-impossible-the-future-of-fairness-in-ai",
    "dlrl-2022-thats-a-wrap-and-a-return-to-in-person-learning-in-2023",
    "cifar-amii-and-the-vector-institute-name-eight-new-canada-cifar-ai-chairs",
    "cifar-at-the-science-summit-during-the-united-nations-general-assembly",
    "cifar-partners-with-actua-for-indigenous-next-generation-training-in-ai",
    "what-will-be-the-impact-of-ai-assisted-robotics-on-humanity",
    "international-womens-day-2023-a-call-for-innovation-and-technology-for-gender-equality",
    "canadas-three-national-ai-institutes-advance-ai-solutions-for-energy-and-the-environment",
    "cifar-hosts-ai-for-energy-the-environment-symposium",
    "machine-md-case-study-1",
    "machine-md-case-study-2",
    "machine-md-case-study-3",
    "machine-md-case-study-4",
    "canadas-ai-leadership-strengthened-through-new-and-renewed-canada-cifar-ai-chairs-under-the-pan-canadian-ai-strategy",
    "report-cifar-symposium-on-ai-for-energy-and-the-environment",
    "ai-in-2063",
    "nothing-about-us-without-us",
    "cifar-announces-launch-of-two-ai-for-health-solution-networks",
    "cifar-ai-insights-policy-brief-outlines-strategies-for-federated-health-data-access-in-canada",
    "towards-a-proportionate-and-risk-based-approach-to-federated-data-access-in-canada",
    "cifar-ai-insights-towards-measuring-and-mitigating-the-environmental-impacts-of-large-language-models",
    "generative-ai-doesnt-have-to-generate-climate-disaster",
    "deloitte-report-canada-leads-the-world-in-ai-talent-concentration",
    "cifar-dlrl-summer-school-showcasing-canada-for-the-worlds-brightest-next-gen-ai-talent",
    "canadas-foundational-role-in-generative-ai",
    "national-ai-institutes-propel-responsible-ai-commercialization-across-canada",
    "open-call-for-high-school-students-participate-in-positively-ai-a-think-tank-by-cifar-and-telus",
    "cifar-ai-insights-regulatory-transformation-in-the-age-of-ai",
    "policy-advice-for-navigating-regulation-in-the-age-of-ai-think-bigger",
    "industry-leaders-gather-for-cifar-rbc-generative-ai-leadership-forum",
    "ai-canada-premier-global-ai-conference-includes-strong-canadian-representation",
    "machine-md-case-study-5",
    "celebrating-20-years-of-dlrl",
    "cifar-welcomes-five-new-canada-cifar-ai-chairs",
    "cifars-ai-for-health-solution-networks-hold-first-meetings",
    "sun-life-gift-helps-train-canadas-workforce-for-the-responsible-adoption-of-ai",
    "beyond-privacy-its-time-for-a-rights-based-approach-to-regulating-ai-for-children",
    "cifar-ai-insights-responsible-ai-and-children-insights-implications-and-best-practices",
    "how-can-we-make-ai-that-works-for-everyone",
    "six-new-cifar-ai-catalyst-grants-awarded",
    "racing-for-cause",
    "indigenous-perspectives-in-ai",
    "canada-cifar-ai-chairs-gather-in-banff-for-annual-aican-meeting",
    "twentieth-edition-of-cifars-deep-learning-reinforcement-learning-summer-school-brings-the-worlds-top-ai-talent-to-canada",
    "three-new-canada-cifar-ai-chairs-appointed-at-the-vector-institute",
    "long-time-cifar-fellow-geoffrey-hinton-awarded-2024-nobel-prize-in-physics",
    "three-2024-nobel-laureates-among-cifars-acclaimed-community-of-researchers",
    "government-of-canada-announces-canadian-ai-safety-institute",
    "data-communities-for-inclusion-recentering-technology-in-the-knowledge-and-well-being-of-the-collective",
    "nicolas-papernot-and-catherine-regis-appointed-co-directors-of-the-caisi-research-program-at-cifar",
    "canadian-research-on-full-display-at-neurips-2024-conference",
    "caisi-research-program-at-cifar-announces-council-membership",
    "cifar-funds-seven-high-risk-high-reward-ai-projects",
    "looking-ahead-the-future-of-ai-in-canada",
    "rich-sutton-honoured-with-turing-award-for-major-contributions-to-ai",
    "the-value-of-community-engagement-in-ai-deployment",
    "strengthening-canadas-ai-talent-ecosystem",
    "new-program-provides-expert-ai-advice-for-policymakers",
    "from-research-to-real-world-impact",
    "cifar-announces-first-ai-safety-catalyst-grants-under-new-national-program",
    "new-and-returning-ai-talent-at-cifar",
    "supporting-the-next-generation-of-ai-talent",
    "calls-open-for-global-ai-alignment-research-initiative",
    "derek-nowrouzezahrai-advancing-ai-driven-game-physics",
    "using-ai-to-prevent-dangerous-drug-interactions",
    "advancing-ai-research-in-canada-meet-the-newest-canada-cifar-ai-chairs",
    "cifar-launches-new-ai-safety-solution-networks",
    "building-safer-ai-with-advanced-evaluation-methods",
    "cifar-welcomes-new-and-renewed-canada-cifar-ai-chairs",
    "a-year-of-impact-for-ai-safety-in-canada",
    "how-angelica-lim-is-building-robots-that-understand-us",
    "cifar-commits-1m-to-global-ai-safety-initiative",
    "privacy-by-design",
    "cifar-awards-over-1m-to-support-sociotechnical-challenges-in-ai-safety",
    "new-frontier-of-ai-and-neurology",
    "de-risking-and-de-mystifying-large-scale-ai",
    "government-of-canada-and-cifar-announce-24m-investment-in-top-ai-talent",
    "beyond-the-magic-toolbox",
    "nick-frosst-sovereign-ai",
    "pathways-prompts-and-pedagogy-educating-gen-alpha",
    "young-innovators-build-ai-social-good",
})


class CatalogError(ValueError):
    """A catalog row or page failed the CIFAR page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for cifar.ca and www.cifar.ca."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_ai_topic_path(path: str) -> bool:
    """True for an on-site HTML path about AI, machine learning, or the strategy."""

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    bare = path[:-1] if path.endswith("/") and path != "/" else path
    lowered = bare.casefold()
    parts = [part for part in lowered.split("/") if part]
    if any(part in _BLOCKED_PARTS for part in parts):
        return False
    # z- categories and the homepage feature bucket are CMS listings, not pages.
    if parts and (parts[-1].startswith("z-") or parts[-1] in {"pcais-home-featured", "pcais-home-featured-fr"}):
        return False
    if lowered.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if lowered in _EXACT_PATHS:
        return True
    if any(lowered == prefix or lowered.startswith(prefix + "/") for prefix in _AI_PREFIXES):
        return True
    if any(lowered == prefix or lowered.startswith(prefix + "/") for prefix in _NEXTGEN_PREFIXES):
        return _slug_is_ai(parts[-1] if parts else "")
    if lowered.startswith("/events/"):
        return _slug_is_ai(parts[-1] if parts else "")
    match = _NEWS_PATH.fullmatch(lowered)
    if match is None:
        return False
    return match.group("slug") in _NEWS_SLUGS


def robots_allows(body: str, path: str) -> bool:
    """True when the * group allows path.

    A challenge or captcha in place of robots.txt does not allow a fetch.
    An HTML document that is not a challenge is not a disallow list.
    """

    if not isinstance(body, str):
        return False
    sample = body[:4000].casefold()
    if any(marker in sample for marker in _CHALLENGE_MARKERS):
        return False
    if "<html" in sample[:800] or sample.lstrip().startswith("<!doctype html"):
        return True
    rules = _wildcard_rules(body)
    if rules is None:
        return True
    target = path or "/"
    allowed = 0
    disallowed = 0
    for kind, prefix in rules:
        if not prefix or not target.startswith(prefix):
            continue
        if kind == "allow":
            allowed = max(allowed, len(prefix))
        else:
            disallowed = max(disallowed, len(prefix))
    return allowed >= disallowed


def robots_path_allowed(url: str, robots_txt: str | None = None) -> bool:
    """A missing robots document does not block. A disallow blocks the path."""

    if not _on_official_host(url):
        return False
    if robots_txt is None:
        return True
    path = urlparse(url).path or "/"
    return robots_allows(robots_txt, path.split("?", 1)[0].split("#", 1)[0])


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
    return any(marker in sample for marker in _CHALLENGE_MARKERS)


def response_stores_a_page(
    *,
    status: object,
    content_type: object,
    page_html: object,
    headers: dict[str, str] | None = None,
    final_url: str | None = None,
) -> bool:
    """A page is stored only from on-host HTML that is not a challenge."""

    if status != 200 or not isinstance(page_html, str) or not page_html.strip():
        return False
    if not is_html_content_type(content_type) or is_challenge_page(page_html):
        return False
    lowered = page_html[:12000].casefold()
    if "<html" not in lowered and "<!doctype html" not in lowered:
        return False
    if headers:
        for key, value in headers.items():
            name = str(key).casefold()
            token = str(value).casefold()
            if name == "cf-mitigated" and "challenge" in token:
                return False
            if name == "sg-captcha":
                return False
            if name == "www-authenticate":
                return False
    if final_url is not None and not _on_official_host(final_url):
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
    robots_txt: str | None = None,
) -> dict | None:
    """Return metadata when the response is a confirmed on-host AI page."""

    target = final_url or page_url
    if not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        final_url=target,
    ):
        return None
    if robots_txt is not None and not robots_path_allowed(target, robots_txt):
        return None
    assert isinstance(page_html, str)
    try:
        return page_record(page_html, page_url=target)
    except CatalogError:
        return None


def rights_from_page(page_text: str) -> str:
    """Return a rights label from a reuse licence the page itself states.

    ``creative_commons_attribution`` is CC BY alone. ``creative_commons`` is
    CC0, CC BY-SA, or a permissive mix of CC0, CC BY, and CC BY-SA. A sole
    restricted deed keeps its token. Two different restricted deeds stay
    unknown. A software licence beside any Creative Commons deed stays
    unknown. Anchor text on a generic creativecommons.org/licenses/ URL does
    not count. A photo, caption, or image credit that names another licence
    does not count. Script, style, and comment text does not count.
    """

    if not isinstance(page_text, str):
        raise CatalogError("page text must be a string")
    cc_codes, software, ogl = _rights_signals(page_text)
    if "pd-mark" in cc_codes:
        return RIGHTS_UNKNOWN
    restricted = cc_codes & _RESTRICTED
    permissive = cc_codes & _PERMISSIVE
    government = _us_government_work(page_text)
    families = [
        family
        for family in (
            restricted,
            permissive,
            software,
            {"uk_ogl"} if ogl else set(),
            {RIGHTS_US_GOVERNMENT_WORK} if government else set(),
        )
        if family
    ]
    if len(families) > 1 or len(restricted) > 1 or len(software) > 1:
        return RIGHTS_UNKNOWN
    if len(restricted) == 1:
        return _RESTRICTED_TOKEN[next(iter(restricted))]
    if permissive:
        if permissive == {"cc-by"}:
            return RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
        return RIGHTS_CREATIVE_COMMONS
    if len(software) == 1:
        return next(iter(software))
    if ogl:
        return RIGHTS_UK_OGL
    if government:
        return RIGHTS_US_GOVERNMENT_WORK
    return RIGHTS_UNKNOWN


def publication_date_from_page(page_html: str) -> str:
    """Return a YYYY-MM-DD publication date, or unknown when the page has none.

    article:modified_time, og:updated_time, a last-updated line, and a
    copyright year are not publication dates. A date inside script prose,
    style, or a comment does not count. A JSON-LD datePublished on the page
    itself does.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    found: list[str] = []

    def add(raw: object) -> None:
        parsed = _iso_day(raw) if isinstance(raw, str) else None
        if parsed and parsed not in found:
            found.append(parsed)

    for parsed in _jsonld_published_dates(page_html):
        add(parsed)
    visible = _visible(page_html)
    metas = _metas(visible)
    for key in _PUBLISHED_META:
        add(metas.get(key, ""))
    plain = _plain(visible).casefold()
    iso = _PUBLISHED_ISO.search(plain)
    if iso:
        add(iso.group(1))
    month = _PUBLISHED_MONTH.search(plain)
    if month:
        parsed = _month_day(month.group(1), month.group(2), month.group(3))
        if parsed:
            add(parsed)
    if len(found) == 1:
        return found[0]
    return UNKNOWN_DATE


def title_from_page(page_html: str) -> str:
    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    for heading in _H1.findall(visible):
        title = _clean_title(_TAG.sub(" ", heading))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _clean_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    metas = _metas(visible)
    for key in ("og:title", "citation_title", "dcterms.title"):
        title = _clean_title(metas.get(key, ""))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return CIFAR when the page names that publisher."""

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _visible(page_html)
    site = _clean_text(_metas(visible).get("og:site_name", ""))
    if site.casefold() == PUBLISHER.casefold():
        return PUBLISHER
    title_tag = _TITLE.search(visible)
    title = _clean_text(_TAG.sub(" ", title_tag.group(1))) if title_tag else ""
    if re.search(r"(?i)\bcifar\b", f"{title} {_plain(visible)}"):
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
        "canonical_url": validate_canonical_url(page_url),
        "date": publication_date_from_page(page_html),
        "rights": rights_from_page(page_html),
    }
    return validate_entry(record)


def build_catalog(entries: list[dict]) -> dict:
    """Validate and order metadata rows. An empty list is a valid catalog."""

    ordered = sorted(entries, key=lambda entry: (_sort_date(entry["date"]), entry["canonical_url"]))
    document = {
        "catalog_id": CATALOG_ID,
        "description": CATALOG_DESCRIPTION,
        "runner_wired": RUNNER_WIRED,
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
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise CatalogError("description is too long")
    if "runner_wired is false" not in description:
        raise CatalogError("description must state that runner_wired is false")
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


def validate_canonical_url(url: object) -> str:
    if not isinstance(url, str) or not url or url != url.strip() or any(char.isspace() for char in url):
        raise CatalogError("canonical URL must be a public CIFAR AI page")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path or "/"
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is not None
        or parsed.netloc.lower() != host
        or not is_official_host(host)
        or ".." in path
        or "\\" in url
        or "//" in path
        or "%" in path
        or not is_ai_topic_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public CIFAR AI page: {url}")
    return url


def validate_date(value: object) -> str:
    if value == UNKNOWN_DATE:
        return UNKNOWN_DATE
    if not isinstance(value, str) or not _iso_date(value):
        raise CatalogError(f"date must be YYYY-MM-DD or {UNKNOWN_DATE}")
    return value


def _slug_is_ai(slug: str) -> bool:
    parts = set(slug.casefold().split("-"))
    if parts & _AI_TOKENS:
        return True
    blob = slug.casefold()
    return any(phrase in blob for phrase in _AI_PHRASES)


def _rights_signals(page_text: str) -> tuple[set[str], set[str], bool]:
    visible = _drop_generic_cc_anchors(_drop_credit_licences(_visible(page_text)))
    return _cc_codes(visible), _software_codes(visible), _states_ogl(visible)


def _drop_generic_cc_anchors(html: str) -> str:
    """Remove anchors that point at the generic Creative Commons licences URL.

    The anchor text is not a deed. Text outside the anchor still is.
    """

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
    folded = _fold(href).split()
    if not folded:
        return False
    return _GENERIC_CC_LICENSES.fullmatch(folded[0]) is not None


def _drop_credit_licences(html: str) -> str:
    """Drop a photo, caption, or image credit, including a licence it names.

    Text before the credit phrase in the same element still counts.
    """

    spans: list[tuple[int, int]] = []
    for match in _CREDIT_PHRASE.finditer(html):
        close = _CREDIT_BLOCK_CLOSE.search(html[match.end() : match.end() + 1000])
        end = match.end() + close.end() if close is not None else min(len(html), match.end() + 500)
        spans.append((match.start(), end))
    if not spans:
        return html
    spans.sort()
    merged: list[tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    pieces: list[str] = []
    cursor = 0
    for start, end in merged:
        pieces.append(html[cursor:start])
        pieces.append(" ")
        cursor = end
    pieces.append(html[cursor:])
    return "".join(pieces)


def _cc_codes(value: str) -> set[str]:
    folded = _fold(value)
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


def _software_codes(value: str) -> set[str]:
    folded = _fold(value)
    found: set[str] = set()
    if _MIT.search(folded):
        found.add(RIGHTS_MIT)
    if _APACHE.search(folded):
        found.add(RIGHTS_APACHE)
    if _MPL.search(folded):
        found.add(RIGHTS_MPL)
    return found


def _states_ogl(visible_html: str) -> bool:
    text = _plain(visible_html).replace("\xa0", " ")
    folded = re.sub(r"\s+", " ", text).casefold()
    return _OGL_PHRASE in folded


def _us_government_work(page_text: str) -> bool:
    """True only when a rights metadata field says the item is a US government work."""

    fields = _meta_values(_visible(page_text), _RIGHTS_META)
    fields.extend(_jsonld_rights_values(page_text))
    text = _plain("\n".join(fields)).casefold().translate(_DASHES)
    if not text or _NEGATED_GOV_WORK.search(text):
        return False
    return _GOV_WORK.search(text) is not None


def _jsonld_rights_values(page_html: str) -> list[str]:
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if str(key).casefold() in {"license", "licence", "rights"} and isinstance(value, str):
                found.append(value)
            elif isinstance(value, (dict, list)):
                walk(value)

    for blob in _LDJSON.findall(page_html):
        try:
            walk(json.loads(blob))
        except json.JSONDecodeError:
            continue
    return found


def _jsonld_published_dates(page_html: str) -> list[str]:
    found: list[str] = []

    def add(raw: object) -> None:
        parsed = _iso_day(raw) if isinstance(raw, str) else None
        if parsed and parsed not in found:
            found.append(parsed)

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        types = node.get("@type")
        names: set[str] = set()
        if isinstance(types, str):
            names.add(types.casefold())
        elif isinstance(types, list):
            names.update(item.casefold() for item in types if isinstance(item, str))
        if names & _PUBLISHED_TYPES:
            add(node.get("datePublished"))
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    for blob in _LDJSON.findall(page_html):
        try:
            walk(json.loads(blob))
        except json.JSONDecodeError:
            continue
    return found


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


def _on_official_host(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    parsed = urlparse(url)
    return is_official_host(parsed.hostname or "")


def _visible(page_html: str) -> str:
    return _SCRIPT_STYLE.sub(" ", _COMMENT.sub(" ", page_html))


def _plain(page_text: str) -> str:
    return _clean_text(page_text)


def _fold(value: str) -> str:
    text = unescape(value).replace("\\/", "/").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _clean_title(value: str) -> str:
    text = _clean_text(value)
    for suffix in _SITE_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)].strip()
            break
    if not text or text.casefold() == "cifar":
        return ""
    if len(text) > MAX_FIELD_CHARS or "<" in text or ">" in text or "\n" in text:
        return ""
    return text


def _clean_text(value: str) -> str:
    text = unescape(_TAG.sub(" ", value)).replace("\xa0", " ").translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip()


def _require_text(value: object, field: str) -> None:
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
        if len(value) > MAX_DESCRIPTION_CHARS and path != "$.description":
            raise CatalogError(f"{path} is too long to be metadata")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise CatalogError(f"{path} has an unsupported JSON type")


def _sort_date(value: str) -> str:
    return "9999-99-99" if value == UNKNOWN_DATE else value


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
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _month_day(month: str, day: str, year: str) -> str | None:
    month_number = _MONTHS.get(month.casefold())
    if month_number is None:
        return None
    try:
        return date(int(year), month_number, int(day)).isoformat()
    except ValueError:
        return None


def _metas(page_html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key and "content" in attrs and key not in found:
            found[key] = attrs["content"]
    return found


def _meta_values(page_html: str, keys: frozenset[str]) -> list[str]:
    values: list[str] = []
    for tag in _META.findall(page_html):
        attrs = _attrs(tag)
        key = (attrs.get("property") or attrs.get("name") or "").casefold()
        if key in keys and attrs.get("content"):
            values.append(attrs["content"])
    return values


def _attrs(tag: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, double, single, bare in _ATTR.findall(tag):
        found.setdefault(key.casefold(), unescape(double or single or bare).strip())
    return found
