"""Metadata catalog of public ITIF pages on artificial intelligence.

Hosts are itif.org and www.itif.org. www.itif.org redirects to itif.org.
robots.txt allows the public site. Each stored URL was confirmed with one
bounded GET that stayed on one of those hosts. Pages are the Artificial
Intelligence issue and the publications and events listed there, which cover
artificial intelligence, machine learning, and AI policy. Other issues, person
profiles, PDFs, login walls, and off-host redirects are not stored.

A Cloudflare challenge, a captcha, an authentication wall, or a path that
does not resolve contributes no rows. This module does not bypass those
controls.

A row keeps the title, publisher, canonical URL, date, and rights label.
Page text, abstracts, quotes, transcripts, chart data, and PDFs are not
stored. The live URL is stored as confirmed. A different rel=canonical does
not replace it.

Rights stay unknown unless the page states a reuse licence.
``creative_commons_attribution`` is CC BY alone, including a
https://creativecommons.org/licenses/by/4.0/ URL. ``creative_commons`` is
CC0, CC BY-SA, or a permissive mix of those. A sole CC BY-NC, CC BY-ND,
CC BY-NC-SA, or CC BY-NC-ND keeps ``cc_by_nc``, ``cc_by_nd``,
``cc_by_nc_sa``, or ``cc_by_nc_nd``. A hyphen is a word boundary, so CC BY
does not match CC BY-NC and licenses/by does not match licenses/by-nc. Two
different restricted deeds stay unknown. A permissive anchor on a restricted
deed URL or on a public-domain mark URL stays unknown, and a CC0 anchor on
a publicdomain/mark URL stays unknown. A generic
https://creativecommons.org/licenses/ URL stays unknown, including a missing
slash, http, a www host, and a query string. Anchor text on that generic URL
stays unknown. A specific deed URL still counts. A software licence beside
any Creative Commons deed stays unknown. Two software licences stay unknown.
A sole MIT License is mit. A sole MPL-2.0 is mpl-2.0. Apache License,
Version 2.0 is apache-2.0. ``uk_ogl`` is only the British phrase Open
Government Licence. Open Government License stays unknown.
``us_government_work`` comes only from an explicit rights metadata field. A
photo credit, caption credit, image credit, "Photo:" line, or Wikimedia
Commons credit that names someone else's licence stays unknown, including
"Photo credit: UNDRR, CC BY-NC-ND 2.0" and "Photo: UNDRR, CC BY-NC-ND 2.0".
A page licence stated outside that credit still counts. Script, style, and
comment text does not count.

Updated, modified, and copyright years are not publication dates. A comment
in robots.txt is not a per-page rights statement. This module does not fetch.
It is not a belief collector, and runner_wired stays false.
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

CATALOG_ID = "itif_ai_pages"
CATALOG_FILENAME = "itif_ai_pages.json"
RUNNER_WIRED = False
PUBLISHER = "Information Technology and Innovation Foundation"
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
OFFICIAL_HOSTS = frozenset({"itif.org", "www.itif.org"})
MAX_TEXT_CHARS = 500
MAX_DESCRIPTION_CHARS = 800
# Confirmed from one GET of https://itif.org/robots.txt. www.itif.org/robots.txt
# redirects there. Allow: / is the only rule. No path was disallowed.
CONFIRMED_ROBOTS_TXT = (
    "User-agent: *\n"
    "Allow: /\n"
    "\n"
    "# ITIF content is licensed under CC BY 4.0.\n"
    "# AI crawlers and search engines are welcome.\n"
    "# See /llms.txt for guidance for LLM systems.\n"
    "\n"
    "Sitemap: https://itif.org/sitemap.xml\n"
)
# Discovery paths that a challenge, captcha, authentication wall, robots
# disallow, or failed resolution kept out of the catalog. None of the fetched
# on-host AI paths were blocked that way.
SKIPPED_LISTING_PATHS: tuple[str, ...] = ()
CATALOG_DESCRIPTION = (
    "Metadata for public Information Technology and Innovation Foundation pages on artificial "
    "intelligence, machine learning, or AI policy. Hosts are itif.org and www.itif.org. "
    "www.itif.org redirects to itif.org. Each row was confirmed with one bounded GET that stayed "
    "on those hosts. robots.txt allows the public site. Person profiles, PDFs, login walls, "
    "challenges, captchas, authentication walls, and off-host redirects are not "
    "stored. Rows keep a title, publisher, canonical URL, date, and rights. Page text is not stored. "
    "creative_commons_attribution is CC BY alone. creative_commons is CC0, CC BY-SA, or a permissive "
    "mix of those. A missing date is unknown. Updated, modified, and copyright years are not "
    "publication dates. This catalog is not a belief collector and runner_wired is false."
)

# BEGIN CONFIRMED_AI_PATHS
CONFIRMED_AI_PATHS = frozenset(
    {
        '/events/2015/06/30/are-super-intelligent-computers-really-threat-humanity/',
        '/events/2017/03/23/ai-robotics-and-future-work/',
        '/events/2018/03/27/can-eu-lead-ai-after-arrival-gdpr/',
        '/events/2018/12/04/why-its-time-united-states-develop-national-ai-strategy/',
        '/events/2018/12/06/g7-multistakeholder-conference-artificial-intelligence/',
        '/events/2019/01/28/impact-ai-diplomacy-and-international-relations/',
        '/events/2019/02/20/using-ai-fight-disinformation-european-elections/',
        '/events/2019/04/04/european-ai-strategies-where-do-member-states-stand-and-where-are-they-headed/',
        '/events/2019/05/30/whats-next-standards-setting-ai/',
        '/events/2019/07/03/enhancing-transatlantic-cooperation-ai/',
        '/events/2019/09/10/how-united-states-can-maintain-its-lead-global-ai-race/',
        '/events/2020/02/06/what-should-europe-do-embrace-ai-powered-manufacturing/',
        '/events/2020/03/25/european-ai-priorities-over-next-6-months/',
        '/events/2020/04/22/how-deepen-transatlantic-ties-ai-and-cybersecurity/',
        '/events/2020/07/15/is-eu-ai-policy-headed-right-direction/',
        '/events/2020/10/14/how-will-quantum-computing-shape-future-ai/',
        '/events/2020/12/01/european-ai-policy-conference/',
        '/events/2021/03/23/how-deepen-transatlantic-cooperation-ai-defense/',
        '/events/2021/05/05/whats-next-eus-proposed-ai-law/',
        '/events/2022/03/23/book-talk-human-centered-ai-ben-shneiderman/',
        '/events/2022/05/24/how-can-ai-improve-educational-outcomes-united-states/',
        '/events/2022/09/13/should-the-eu-regulate-general-purpose-ai-systems/',
        '/events/2022/10/07/how-ai-and-open-data-can-help-combat-climate-crisis-inequity-and-more/',
        '/events/2022/10/13/government-perspective-deepfakes-and-restoring-trust-online/',
        '/events/2022/10/18/building-the-nist-ai-risk-management-framework/',
        '/events/2023/02/16/chatgpt-in-the-classroom-and-data-for-social-good/',
        '/events/2023/02/23/where-should-u-s-ai-policy-be-headed-next/',
        '/events/2023/03/06/policy-dialogue-on-ai-and-data-for-society/',
        '/events/2023/03/07/will-chatgpt-forever-change-education/',
        '/events/2023/03/21/ai-generated-art-boom-or-bust-for-human-creativity/',
        '/events/2023/04/12/can-eu-directive-to-combat-violence-against-women-stop-a-i-enabled-intimate-image-abuse/',
        '/events/2023/04/17/ai-ethics-and-data-governance/',
        '/events/2023/04/26/broadband-breakfast-should-ai-be-regulated/',
        '/events/2023/05/04/generative-ai-and-time-for-a-time-out/',
        '/events/2023/05/16/ai-education-and-childrens-privacy-concerns/',
        '/events/2023/06/06/does-us-need-new-ai-regulator/',
        '/events/2023/06/13/transatlantic-approaches-to-ai-regulation-in-times-of-great-power-competition/',
        '/events/2023/07/13/artificial-intelligence-and-innovation-ai-use-cases-across-sectors/',
        '/events/2023/07/18/age-verification-tech-for-social-media/',
        '/events/2023/08/29/data-as-the-foundation-privacy-policy-and-artificial-intelligence/',
        '/events/2023/09/07/unveiling-ai-policy-insights-global-trends-and-regulatory-strategies/',
        '/events/2023/09/21/2023-florida-tech-and-innovation-summit/',
        '/events/2023/09/21/fp-tech-forum-unga78/',
        '/events/2023/12/05/unveiling-ai-policy-insights-global-trends-regulatory-strategies/',
        '/events/2024/02/12/ai-and-creativity-at-the-20th-annual-state-of-the-net/',
        '/events/2024/03/27/generative-ai-and-congressional-action/',
        '/events/2024/04/16/how-can-uk-encourage-uptake-of-ai-in-public-sector/',
        '/events/2024/04/24/harnessing-ai-for-carbon-neutrality/',
        '/events/2024/05/09/impact-generative-ai-misinformation-disinformation-malinformation/',
        '/events/2024/05/15/how-can-policymakers-address-ai-voice-cloning-scams/',
        '/events/2024/05/16/data-driven-policy-and-innovation-with-ai/',
        '/events/2024/05/20/debunking-tech-myths-about-privacy-jobs-ai-and-todays-innovation-economy/',
        '/events/2024/05/21/insights-on-us-public-opinion-on-ai/',
        '/events/2024/06/05/policy-governance-and-ethical-considerations-in-ai/',
        '/events/2024/07/17/how-can-canadian-policymakers-improve-artificial-intelligence-and-data-act/',
        '/events/2024/08/13/the-ai-regulatory-landscape/',
        '/events/2024/08/28/responsible-practices-and-use-of-ai/',
        '/events/2024/09/05/past-and-future-threats-and-opportunities-of-ai/',
        '/events/2024/10/02/capital-goods-artificial-intelligence-data-centres-electrification-automation/',
        '/events/2024/10/17/oxford-generative-ai-summit-2024/',
        '/events/2024/10/22/safe-and-responsible-use-of-ai-ethical-guidelines-and-guardrails/',
        '/events/2024/10/28/enhancing-cybersecurity-with-ai/',
        '/events/2024/10/29/artificial-intelligence-in-education/',
        '/events/2024/10/30/the-impact-of-ai-on-cybersecurity/',
        '/events/2024/11/21/economic-potential-of-artificial-intelligence/',
        '/events/2024/11/21/from-data-policy-to-practice-bridging-the-gap/',
        '/events/2024/11/21/how-policymakers-should-navigate-tensions-in-global-ai-governance/',
        '/events/2025/01/16/balancing-national-security-and-economic-competitiveness-in-ai-export-controls/',
        '/events/2025/01/21/worst-tech-policies-of-2024/',
        '/events/2025/02/07/exploring-ais-impact-policy-innovation-and-governance/',
        '/events/2025/03/20/chinas-ai-leap-no-surprise-if-you-know-where-to-look/',
        '/events/2025/03/29/advancing-global-ai-safety-through-systematic-monitoring/',
        '/events/2025/04/08/uk-needs-broad-text-and-data-mining-exception-to-support-ai-innovation/',
        '/events/2025/04/17/is-us-policy-ready-for-agentic-ai/',
        '/events/2025/04/24/ai-business-how-generative-ai-is-reshaping-industries/',
        '/events/2025/04/25/the-future-is-now-the-rise-of-ai-in-america/',
        '/events/2025/05/13/how-americans-feel-about-ai-and-why-it-matters-for-policy/',
        '/events/2025/05/19/striking-the-right-balance-between-ai-regulation-and-innovation/',
        '/events/2025/06/03/usa-artificial-intelligence-summit-2025/',
        '/events/2025/06/11/should-policymakers-regulate-human-ai-relationships/',
        '/events/2025/06/13/ai-and-the-architecture-of-modern-economies-and-societies/',
        '/events/2025/06/17/ai-automation-new-era-of-safety-and-compliance-management/',
        '/events/2025/06/19/watermarking-and-the-future-of-trust-in-generative-ai/',
        '/events/2025/06/26/addressing-concerns-over-ais-energy-consumption-responsible-ai-use-policy-support-measures/',
        '/events/2025/06/26/introduction-to-ai-policy/',
        '/events/2025/07/16/geofencing-ai-chips-evaluating-call-home-mandates-for-semiconductor-security/',
        '/events/2025/07/17/wrong-question-wrong-answer-time-to-rescope-the-debate-on-ai-regulation/',
        '/events/2025/07/30/artificial-intelligence-and-antitrust/',
        '/events/2025/08/27/cpsc-agenda-and-priorities-for-the-fiscal-year/',
        '/events/2025/09/16/what-it-will-take-to-bring-the-global-south-into-the-us-ai-alliance/',
        '/events/2025/09/24/ai-in-drug-discovery-and-development/',
        '/events/2025/10/01/no-data-no-ai/',
        '/events/2025/11/06/4th-annual-geopolitics-of-technology-in-east-asia/',
        '/events/2025/11/12/to-bot-or-not-to-bot/',
        '/events/2025/11/18/us-japan-technology-cooperation-shaping-future-ai-quantum/',
        '/events/2025/12/12/the-state-of-open-source-ai-and-why-it-matters/',
        '/events/2026/01/20/advancing-multilateral-ai-partnerships-pre-summit-event-for-2026-ai-impact-summit/',
        '/events/2026/01/22/building-global-consensus-on-ai/',
        '/events/2026/03/05/context-matters-building-trust-in-digital-content/',
        '/events/2026/04/15/reimagining-multilateralism-for-the-future/',
        '/events/2026/06/10/partnerships-for-autonomous-science-workshop-policy-perspectives/',
        '/events/2026/06/11/indo-us-working-group-policy-ai-training-data-and-copyright/',
        '/events/2026/06/16/how-to-protect-kids-from-chatbots-without-bans/',
        '/events/2026/06/23/governance-oversight-accountability-technology-enabled-emergency-management/',
        '/events/2026/07/08/frontier-ai-firms-as-security-actors-workshop/',
        '/events/2026/07/24/capitol-hill-conference-on-ai-cyber-and-tech-policy-priorities/',
        '/events/2026/07/27/2026-ncsl-legislative-summit/',
        '/events/2026/08/05/indo-us-working-group-ai-export-controls-and-indo-us-tech-corridor/',
        '/events/2026/08/26/can-the-united-states-win-ai-race-if-americans-oppose-data-centers/',
        '/events/2026/09/09/internet-governance-forum-usa-ai-and-data-centers-in-the-usa/',
        '/events/2026/09/30/the-2026-stepi-intelligence-dialogue/',
        '/issues/artificial-intelligence/',
        '/publications/2016/01/20/artificial-intelligence-and-robotics-poised-destroy-all-jobs-one/',
        '/publications/2016/06/06/its-going-kill-us-and-other-myths-about-future-artificial-intelligence/',
        '/publications/2016/07/06/5-myths-about-future-ai/',
        '/publications/2016/07/22/comments-white-house-office-science-and-technology-policy-artificial/',
        '/publications/2016/10/10/promise-artificial-intelligence-70-real-world-examples/',
        '/publications/2016/12/16/how-artificial-intelligence-will-usher-next-stage-e-government/',
        '/publications/2017/01/25/eus-right-explanation-harmful-restriction-artificial-intelligence/',
        '/publications/2017/09/19/artificial-intelligence-robotics-and-future-work-myths-and-facts/',
        '/publications/2017/10/10/fact-week-united-states-developed-75-percent-all-artificial-intelligence/',
        '/publications/2017/12/12/digital-decision-making-building-blocks-machine-learning-and-artificial/',
        '/publications/2017/12/13/prediction-rise-ai-and-robotics-wont-drive-mass-unemployment/',
        '/publications/2018/01/12/ai-offers-opportunity-increase-privacy-users/',
        '/publications/2018/01/25/economic-and-labor-force-implications-artificial-intelligence/',
        '/publications/2018/03/26/impact-eu-new-data-protection-regulation-ai/',
        '/publications/2018/05/21/how-policymakers-can-foster-algorithmic-accountability/',
        '/publications/2018/05/25/europe-about-lose-global-ai-race-thanks-gdpr/',
        '/publications/2018/06/15/essay-european-investment-bank-artificial-intelligence-europe/',
        '/publications/2018/06/15/eu-cannot-shape-future-ai-regulation/',
        '/publications/2018/07/26/how-and-how-not-fix-ai/',
        '/publications/2018/08/01/why-us-could-fall-behind-global-ai-race/',
        '/publications/2018/09/17/fact-week-ai-driven-machine-translation-increased-ebays-international-trade/',
        '/publications/2018/10/09/ai-superpowers-china-silicon-valley-and-new-world-order/',
        '/publications/2018/10/25/comments-nitrd-updates-2016-national-ai-rd-strategic-plan/',
        '/publications/2018/12/03/using-dynamic-legal-injunctions-and-ai-fight-piracy-real-time-united-kingdom/',
        '/publications/2018/12/04/to-do-develop-sector-specific-ai-strategies/',
        '/publications/2018/12/04/to-do-develop-shared-pools-of-high-quality-app-specific-training-and-validation-data/',
        '/publications/2018/12/04/to-do-encourage-states-to-foster-ai-industry-development/',
        '/publications/2018/12/04/why-united-states-needs-national-artificial-intelligence-strategy-and-what/',
        '/publications/2018/12/05/how-can-smaller-cities-join-growing-ai-economy/',
        '/publications/2019/02/01/recommendations-european-commission-its-draft-ai-ethics-guidelines/',
        '/publications/2019/02/04/ten-ways-precautionary-principle-undermines-progress-artificial-intelligence/',
        '/publications/2019/02/05/eus-softball-approach-artificial-intelligence-will-lose/',
        '/publications/2019/02/15/comments-ftc-algorithms-ai-and-predictive-analytics/',
        '/publications/2019/02/25/us-finally-moving-towards-ai-strategy/',
        '/publications/2019/03/12/deep-medicine-how-artificial-intelligence-can-make-healthcare-human-again/',
        '/publications/2019/04/01/will-ai-destroy-more-jobs-it-creates-over-next-decade/',
        '/publications/2019/05/10/comments-nist-ai-standards/',
        '/publications/2019/05/23/want-europe-have-best-ai-reform-gdpr/',
        '/publications/2019/08/06/manufacturing-evolution-how-ai-will-transform-manufacturing-and-workforce/',
        '/publications/2019/08/06/to-do-expand-investments-in-ai-talent/',
        '/publications/2019/08/07/europe-will-be-left-behind-if-it-focuses-ethics-and-not-keeping-pace-ai/',
        '/publications/2019/08/09/comments-omb-federal-data-and-models-ai-rd/',
        '/publications/2019/08/19/who-winning-ai-race-china-eu-or-united-states/',
        '/publications/2019/08/23/what-will-brexit-mean-ai-eu/',
        '/publications/2019/09/19/podcast-ai-adoption-and-the-innovation-cycle-with-rob-atkinson/',
        '/publications/2019/10/28/could-ai-help-reduce-gender-bias-europe/',
        '/publications/2019/11/11/how-uk-can-secure-its-standing-ai-leader-post-brexit/',
        '/publications/2020/01/10/comments-us-patent-and-trademark-office-impact-artificial-intelligence/',
        '/publications/2020/05/04/27-percent-of-inventors-who-have-earned-ai-patents-have-also-published-ai-papers/',
        '/publications/2020/06/12/response-public-consultation-european-commissions-white-paper-european/',
        '/publications/2020/06/14/response-european-commission’s-consultation-white-paper-artificial/',
        '/publications/2020/07/07/eu-policymakers-should-ignore-ai-concern-trolls/',
        '/publications/2020/08/10/podcast-case-killer-robots-robert-marks/',
        '/publications/2020/09/10/response-european-commission’s-roadmap-requirements-artificial-intelligence/',
        '/publications/2020/10/15/comments-nist-explainable-ai/',
        '/publications/2020/10/22/adaptive-antipiracy-tools-update-dynamic-and-live-blocking-injunctions/',
        '/publications/2020/11/27/us-states-can-succeed-ai-looking-singapore/',
        '/publications/2020/12/07/fact-week-artificial-intelligence-can-save-pharmaceutical-companies-almost/',
        '/publications/2021/01/25/who-winning-ai-race-china-eu-or-united-states-2021-update/',
        '/publications/2021/02/08/podcast-promise-artificial-intelligence-steven-shwartz/',
        '/publications/2021/03/01/how-congress-and-biden-administration-could-jumpstart-smart-cities-ai/',
        '/publications/2021/03/22/podcast-hype-hope-and-practical-realities-artificial-intelligence-pedro/',
        '/publications/2021/05/10/fact-week-firms-more-1000-employees-are-10-times-more-use-ai-firms-5-10/',
        '/publications/2021/07/26/how-much-will-artificial-intelligence-act-cost-europe/',
        '/publications/2021/08/02/feedback-adapting-liability-rules-digital-age-and-artificial-intelligence/',
        '/publications/2021/08/09/principles-promote-responsible-use-ai-workforce-decisions/',
        '/publications/2021/08/12/comments-european-commission-proposed-artificial-intelligence-act/',
        '/publications/2021/09/01/case-artificial-intelligence-recruiting-it-talent/',
        '/publications/2021/09/20/podcast-ai-and-defense-innovation-lt-gen-jack-shanahan/',
        '/publications/2021/09/23/comments-canadas-department-innovation-science-and-economic-development/',
        '/publications/2021/09/29/comments-ostp-and-nsf-national-ai-research-resource-nairr/',
        '/publications/2021/10/21/creating-ai-bill-rights-distraction/',
        '/publications/2021/12/01/more-meets-ai-hidden-costs-european-software-law/',
        '/publications/2021/12/07/ai-could-help-get-government-records-paper-and-online/',
        '/publications/2022/01/06/calm-down-ai-isnt-magic-just-software/',
        '/publications/2022/01/10/ai-start-ups-attracted-over-21-percent-worlds-venture-capital-2020/',
        '/publications/2022/02/14/increasing-industrial-use-of-ai-improves-purchasing-power-and-reduces-regional-inequality/',
        '/publications/2022/03/14/fact-week-large-firms-implementing-artificial-intelligence-enjoyed/',
        '/publications/2022/04/11/fact-week-investing-ai-significantly-reduced-business-risk-during-covid-19/',
        '/publications/2022/04/25/ai-bias-correctable-human-bias-not-so-much/',
        '/publications/2022/04/25/how-ai-can-improve-k-12-education-united-states/',
        '/publications/2022/05/02/podcast-back-future-historical-lessons-us-ai-policy-arthur-herman/',
        '/publications/2022/07/19/industry-university-partnerships-to-create-ai-universities/',
        '/publications/2022/07/22/defining-a-person-analyzing-the-legal-ip-issues-of-ai-inventorship-and-creatorship/',
        '/publications/2022/07/27/us-ai-policy-report-card/',
        '/publications/2022/08/23/podcast-the-center-for-data-innovation-ai-report-card-with-hodan-omaar/',
        '/publications/2022/09/22/testimony-on-the-stop-discrimination-by-algorithms-act-of-2021/',
        '/publications/2022/10/17/comments-to-ita-on-ai-export-competitiveness/',
        '/publications/2022/11/10/beware-of-tech-principles-in-sheep-clothing/',
        '/publications/2022/12/02/slow-progress-is-taking-the-fear-out-of-artificial-intelligence/',
        '/publications/2023/02/01/the-ai-act-should-be-technology-neutral/',
        '/publications/2023/02/08/ten-principles-for-regulation-that-does-not-harm-ai-innovation/',
        '/publications/2023/02/13/openais-chatgpt-user-base-has-grown-faster-than-tiktoks-or-instagrams/',
        '/publications/2023/03/20/critics-of-generative-ai-are-worrying-about-the-wrong-ip-issues/',
        '/publications/2023/03/27/canadas-reasons-for-an-ai-law-do-not-stand-up-to-scrutiny/',
        '/publications/2023/04/05/ai-could-make-age-verification-more-accurate-and-less-invasive/',
        '/publications/2023/04/10/labeling-incorrect-ai-output-as-deceptive-would-be-misguided-overreach-by-the-ftc/',
        '/publications/2023/04/12/generative-ai-is-the-next-challenge-for-section-230/',
        '/publications/2023/04/17/claims-about-generative-ai-replacing-jobs-are-hyperbolic-and-misleading/',
        '/publications/2023/04/17/us-ranks-10th-among-oecd-countries-in-share-of-employees-with-ai-related-skills/',
        '/publications/2023/04/19/an-overview-of-the-uks-new-approach-to-ai/',
        '/publications/2023/04/28/the-eu-should-learn-from-how-the-uk-regulates-ai-to-stay-competitive/',
        '/publications/2023/04/28/us-regulators-should-support-the-adoption-of-ai-that-addresses-human-bias/',
        '/publications/2023/05/01/tech-panics-generative-ai-and-the-need-for-regulatory-caution/',
        '/publications/2023/05/11/us-policymakers-should-learn-from-countries-choosing-not-to-regulate-ai/',
        '/publications/2023/05/15/senator-schumer-should-maintain-resolve-in-the-us-approach-to-ai-regulation/',
        '/publications/2023/05/21/korea-needs-to-slow-down-regulation-speed-up-support-for-ai/',
        '/publications/2023/05/22/access-to-ai-based-conversation-assistant-increased-customer-service-productivity/',
        '/publications/2023/06/02/comments-to-the-competition-and-markets-authority-on-ai-foundation-models/',
        '/publications/2023/06/02/preparing-for-an-ai-apocalypse-is-as-preposterous-as-preparing-for-an-alien-invasion/',
        '/publications/2023/06/02/states-should-welcome-the-worlds-first-actual-robot-lawyer/',
        '/publications/2023/06/15/little-evidence-for-ai-alarmism/',
        '/publications/2023/06/21/podcast-what-is-washington-doing-to-regulate-ai-with-daniel-castro/',
        '/publications/2023/06/23/senator-schumers-proposal-for-ai-legislation-is-on-the-right-track/',
        '/publications/2023/06/26/declining-test-scores-in-the-united-states-signal-the-need-for-ai-solutions/',
        '/publications/2023/06/28/generative-ai-offers-federal-agencies-common-sense-opportunities-to-simplify-and-improve/',
        '/publications/2023/07/10/customer-support-agents-using-ai-gpt-tool-saw-nearly-14-percent-increase-in-productivity/',
        '/publications/2023/07/11/comments-to-ostp-on-national-priorities-for-artificial-intelligence/',
        '/publications/2023/07/17/podcast-seizing-the-opportunities-for-ai-with-daniel-castro/',
        '/publications/2023/07/17/to-do-enumerate-plans-to-use-ai-to-improve-cyber-resilience/',
        '/publications/2023/07/17/white-house-should-update-cybersecurity-strategy-to-consider-impact-of-ai/',
        '/publications/2023/07/19/the-department-of-education-shouldnt-treat-human-in-the-loop-as-a-silver-bullet-for-ai/',
        '/publications/2023/07/26/3-guidelines-for-crafting-a-strong-federal-ai-policy/',
        '/publications/2023/07/28/no-we-arent-in-an-oppenheimer-moment-for-ai/',
        '/publications/2023/08/08/the-ftc-should-avoid-unduly-restricting-the-us-ai-industry/',
        '/publications/2023/08/14/ai-enabled-automation-positively-associated-with-changes-in-occupation-employment-shares/',
        '/publications/2023/08/21/is-mona-lisa-happy-eu-would-ban-ai-that-could-answer-this-question/',
        '/publications/2023/09/01/in-the-wake-of-generative-ai-industry-led-standards-for-data-scraping-are-a-must/',
        '/publications/2023/09/11/regulation-by-outrage-detriment-to-emerging-technologies-with-patrick-grady/',
        '/publications/2023/09/11/the-ftc-should-not-treat-openai-like-public-enemy-no-1/',
        '/publications/2023/09/12/comments-on-the-need-for-transparency-in-ai/',
        '/publications/2023/09/13/global-declaration-on-free-and-open-ai/',
        '/publications/2023/09/26/the-federal-government-is-falling-behind-on-ai-skills-but-here-is-how-it-can-catch-up/',
        '/publications/2023/10/06/biden-prediction-of-more-technological-progress-is-almost-certainly-wrong/',
        '/publications/2023/10/16/no-ai-is-not-a-surveillance-technology/',
        '/publications/2023/11/01/statement-to-us-senate-ai-insight-forum-on-ai-and-workforce/',
        '/publications/2023/11/02/top-10-things-i-disagreed-with-in-the-senate-ai-insight-forum-on-the-workforce/',
        '/publications/2023/11/03/jumping-on-the-bletchley-declarations-existential-ai-risk-bandwagon-hurts-the-us-and-ai/',
        '/publications/2023/11/08/statement-to-us-senate-ai-insight-forum-ai-privacy-liability/',
        '/publications/2023/11/17/airia-bill-would-force-commerce-department-to-bite-off-more-than-it-can-chew/',
        '/publications/2023/11/20/eu-ai-act-is-a-cautionary-tale-in-open-source-ai-regulation/',
        '/publications/2023/12/04/policymakers-should-use-the-seti-model-to-prepare-for-ai-doomsday-scenarios/',
        '/publications/2023/12/06/statement-to-the-us-senate-ai-insight-forum-on-risk-alignment-and-doomsday-scenarios/',
        '/publications/2023/12/14/comments-to-uks-competition-markets-authority-on-microsofts-partnership-with-openai/',
        '/publications/2024/01/04/can-canada-still-lay-claim-to-pro-innovation-nation/',
        '/publications/2024/01/16/new-york-times-openai-lawsuit-threatens-future-of-ai-and-fair-use/',
        '/publications/2024/01/22/the-ftc-is-meddling-in-ai-creativity/',
        '/publications/2024/01/28/blame-lawmakers-not-ai-for-failing-to-prevent-fake-explicit-images-of-taylor-swift/',
        '/publications/2024/01/29/rethinking-concerns-about-ai-energy-use/',
        '/publications/2024/01/29/to-do-develop-energy-transparency-standards-for-ai-models/',
        '/publications/2024/01/29/using-artificial-intelligence-to-augment-workflow-with-nitin-mittal/',
        '/publications/2024/02/05/cma-chair-falls-into-the-trap-of-ai-fear-mongering-as-he-reframes-old-risks-as-new/',
        '/publications/2024/02/07/an-agile-sector-specific-approach-to-uk-ai-regulation-is-promising/',
        '/publications/2024/02/16/virginias-ai-executive-order-is-a-model-for-other-states/',
        '/publications/2024/02/20/california-bill-to-regulate-ai-undercuts-federal-efforts/',
        '/publications/2024/02/21/podcast-artificial-intelligence-regulation-around-the-world-with-daniel-castro/',
        '/publications/2024/03/01/comments-to-canadian-house-of-commons-regarding-the-ai-and-data-act/',
        '/publications/2024/03/01/comments-to-ico-on-training-generative-ai-models-using-web-scraped-data/',
        '/publications/2024/03/04/the-eu-ai-act-creates-regulatory-complexity-for-open-source-ai/',
        '/publications/2024/03/08/comments-to-dg-comp-on-virtual-worlds-and-generative-ai/',
        '/publications/2024/03/08/joe-biden-did-not-approve-this-fake-message/',
        '/publications/2024/03/11/podcast-itifs-daniel-castro-on-energy-efficient-ai-and-climate-change/',
        '/publications/2024/03/18/chinas-annual-parliamentary-meeting-shows-national-commitment-to-advancing-ai/',
        '/publications/2024/03/21/us-policymakers-should-reject-kill-switches-for-ai/',
        '/publications/2024/03/25/whats-next-after-the-two-sessions-for-ai-in-china/',
        '/publications/2024/03/27/comments-ntia-dual-use-foundation-ai-models-widely-available-model-weights/',
        '/publications/2024/04/01/supply-chain-origins-and-innovations-with-yossi-sheffi/',
        '/publications/2024/04/04/tracking-ai-incidents-and-vulnerabilities/',
        '/publications/2024/04/12/comments-to-the-uk-ico-on-generative-ai/',
        '/publications/2024/04/13/to-do-create-an-ai-similarity-checker-for-music/',
        '/publications/2024/04/19/canadas-2024-federal-budget-the-good-bad-maybe-for-innovation/',
        '/publications/2024/04/22/navigating-deepfakes-while-promoting-innovation-with-ryan-long/',
        '/publications/2024/04/25/letter-in-support-of-the-the-future-of-ai-innovation-act/',
        '/publications/2024/04/29/comments-to-omb-on-responsible-ai-procurement/',
        '/publications/2024/04/30/shift-on-ai-and-biothreats-is-lesson-on-risks-of-premature-regulation/',
        '/publications/2024/05/01/comments-to-the-ico-on-the-accuracy-of-training-data-and-model-outputs-for-generative-ai/',
        '/publications/2024/05/03/canada-ai-competition/',
        '/publications/2024/05/07/ai-fears-scapegoats-and-myths-with-rob-atkinson/',
        '/publications/2024/05/07/technology-fears-and-scapegoats/',
        '/publications/2024/05/09/comments-competition-markets-authority-regarding-amazon-anthropic-partnership/',
        '/publications/2024/05/09/comments-competition-markets-authority-regarding-microsoft-inflection-ai/',
        '/publications/2024/05/09/comments-competition-markets-authority-regarding-microsoft-mistral-ai-partnership/',
        '/publications/2024/05/20/picking-the-right-policy-solutions-for-ai-concerns/',
        '/publications/2024/05/20/to-do-ban-financial-institutions-from-relying-solely-on-voice-authentication/',
        '/publications/2024/05/20/to-do-pass-the-ai-incident-reporting-and-security-enhancement-act/',
        '/publications/2024/05/21/what-does-the-public-think-about-ai-us/',
        '/publications/2024/05/23/podcast-data-driven-policy-and-innovation-with-ai/',
        '/publications/2024/05/29/pros-and-cons-to-new-tech-stupidity-productivity-and-whales/',
        '/publications/2024/05/29/state-dept-risks-overlooking-potential-of-ai-for-human-rights/',
        '/publications/2024/06/03/to-do-research-ai-age-estimation/',
        '/publications/2024/06/05/us-china-ai-dialogue-would-benefit-from-more-stakeholders/',
        '/publications/2024/06/06/podcast-big-techs-critics-have-gotten-a-lot-wrong-on-ai/',
        '/publications/2024/06/10/how-generative-ai-is-changing-the-global-souths-it-services-sector/',
        '/publications/2024/06/10/remaining-realistic-optimistic-about-promise-of-future-with-jim-pethokoukis/',
        '/publications/2024/06/11/evidence-shows-productivity-benefits-of-ai/',
        '/publications/2024/06/18/omb-should-help-create-standard-contractual-terms-to-streamline-us-govt-procuring-ai/',
        '/publications/2024/06/18/to-do-streamline-ai-procurement/',
        '/publications/2024/06/27/irish-dpas-request-to-meta-is-a-misguided-move/',
        '/publications/2024/06/27/podcast-busting-tech-myths-with-rob-atkinson-and-david-moschella/',
        '/publications/2024/06/28/information-technology-is-increasingly-critical-and-increasingly-demonized-with-daniel-castro/',
        '/publications/2024/07/01/ai-robotics-adoption-boost-local-technological-innovation-in-chinese-cities/',
        '/publications/2024/07/01/dont-blame-technology-for-misinformation-polarization-and-electoral-distrust/',
        '/publications/2024/07/01/two-key-moves-the-eus-new-ai-office-should-make-to-foster-innovation/',
        '/publications/2024/07/08/at-least-10-percent-scientific-research-being-co-authored-by-ai/',
        '/publications/2024/07/09/ai-acts-watermarking-requirement-is-a-misstep-in-the-quest-for-transparency/',
        '/publications/2024/07/15/comments-us-department-of-justice-antitrust-division-regarding-promoting-competition-ai/',
        '/publications/2024/07/15/policymakers-should-focus-on-turning-ai-aspirations-into-reality/',
        '/publications/2024/07/15/what-does-the-public-think-about-ai-uk/',
        '/publications/2024/07/25/four-ai-priorities-for-eus-new-political-leaders/',
        '/publications/2024/07/31/what-to-expect-for-ai-from-uks-new-labour-government/',
        '/publications/2024/08/01/podcast-a-positive-spin-on-ai-with-david-moschella/',
        '/publications/2024/08/05/general-purpose-technologies-rise-great-nations-with-jeffrey-ding/',
        '/publications/2024/08/06/policymakers-should-capitalize-on-public-opinion-promote-beneficial-ai-use/',
        '/publications/2024/08/07/podcast-rob-atkinson-on-technology-and-innovation-myths/',
        '/publications/2024/08/09/podcast-the-one-with-the-emerging-technology-myth-debunker/',
        '/publications/2024/08/12/how-experts-china-united-kingdom-view-ai-risks-collaboration/',
        '/publications/2024/08/15/comments-to-ministry-of-information-and-communications-dti/',
        '/publications/2024/08/15/watermarking-images-will-not-solve-ai-generated-content-abuse/',
        '/publications/2024/08/26/how-innovative-is-china-in-ai/',
        '/publications/2024/08/26/to-do-create-a-national-roadmap-for-ai-adoption/',
        '/publications/2024/08/30/comments-to-the-fcc-on-ai-generated-content-in-political-ads/',
        '/publications/2024/09/11/ai-adoption-is-key-to-uk-ai-opportunities-action-plan/',
        '/publications/2024/09/16/ai-rice-farming-technology-nigeria-reduces-water-use-by-30-percent/',
        '/publications/2024/09/17/comments-european-ai-office-on-trustworthy-general-purpose-ai-models/',
        '/publications/2024/09/17/comments-to-dsit-on-the-ai-opportunities-action-plan/',
        '/publications/2024/09/18/podcast-busting-technology-myths-ai-jobs-politics-and-privacy/',
        '/publications/2024/09/18/why-watermarking-text-fails-to-stop-misinformation-and-plagiarism/',
        '/publications/2024/09/20/podcast-agree-to-disagree-are-we-living-in-an-age-of-techno-pessimism/',
        '/publications/2024/09/23/over-13-percent-firms-use-artificial-intelligence-have-expanded-workforce/',
        '/publications/2024/09/24/europe-tap-switzerland-to-unlock-llm-innovation-in-the-continent/',
        '/publications/2024/09/25/draghis-competitiveness-report-shows-eu-pro-innovation-approach-towards-ai/',
        '/publications/2024/10/02/us-should-seize-global-ai-stage-in-california-to-shift-gears-to-post-deployment-safety/',
        '/publications/2024/10/04/comments-australian-dept-industry-science-resources-proposed-mandatory-guardrails-ai/',
        '/publications/2024/10/07/boom-in-state-digital-replica-legislation-fuels-need-for-federal-publicity-right/',
        '/publications/2024/10/10/california-legislators-not-equipped-to-rework-ai-law/',
        '/publications/2024/10/11/comments-bureau-industry-securitys-proposed-rule-establish-ai-reporting-requirements/',
        '/publications/2024/10/15/studies-show-ai-triggers-delirium-in-leading-experts/',
        '/publications/2024/10/18/audio-watermarking-wont-solve-the-real-dangers-of-ai-voice-manipulation/',
        '/publications/2024/10/25/national-security-reminds-policymakers-what-is-at-stake-for-the-us-in-global-ai-race/',
        '/publications/2024/10/28/breaking-up-google-whole-of-government-approach-to-ai-leadership/',
        '/publications/2024/11/04/californias-ai-transparency-law-is-a-misstep-other-states-should-avoid/',
        '/publications/2024/11/12/for-trump-delivering-for-voters-means-delivering-on-ai/',
        '/publications/2024/11/15/harnessing-ai-to-accelerate-innovation-in-the-biopharmaceutical-industry/',
        '/publications/2024/11/15/to-do-accelerate-ai-adoption-in-biopharma-research/',
        '/publications/2024/11/15/to-do-improve-the-datasets-needed-for-biomedical-research/',
        '/publications/2024/11/15/to-do-invest-in-ai-and-data-science-training-for-drug-development/',
        '/publications/2024/11/15/to-do-pass-the-privacy-enhancing-technology-research-act/',
        '/publications/2024/11/18/key-facts-missing-creative-communitys-statement-unlicensed-ai-training/',
        '/publications/2024/11/18/policymakers-should-further-study-the-benefits-risks-of-ai-companions/',
        '/publications/2024/11/25/denying-copyright-for-ai-assisted-art-threatens-innovation/',
        '/publications/2024/11/25/digital-transformation-should-heart-uk-economic-agenda/',
        '/publications/2024/12/12/chinas-ai-unicorns-five-startups-vying-rival-western-counterparts/',
        '/publications/2024/12/12/zhipu-ai-chinas-generative-trailblazer-grappling-with-rising-competition/',
        '/publications/2024/12/16/eight-ways-the-new-administration-can-pursue-a-post-techlash-agenda/',
        '/publications/2024/12/16/why-ai-generated-content-labeling-mandates-fall-short/',
        '/publications/2025/01/05/dojs-proposal-break-up-google-would-hurt-competitiveness-ai/',
        '/publications/2025/01/10/moonshot-ai-betting-big-long-context-confronting-challenges-scale-reliability/',
        '/publications/2025/01/17/its-time-the-us-speaks-with-one-voice-on-ai/',
        '/publications/2025/01/21/after-bidens-tech-industrial-complex-warning-trump-has-opportunity-for-fresh-start/',
        '/publications/2025/01/22/podcast-big-pivot-from-techlash-to-trump/',
        '/publications/2025/01/26/texas-ai-law-wont-deliver-the-accountability-it-promises/',
        '/publications/2025/01/27/finnish-employees-highly-exposed-generative-ai-greater-wage-growth/',
        '/publications/2025/01/28/why-the-pursuit-of-sovereign-ai-is-not-the-right-call-for-the-uk/',
        '/publications/2025/01/30/deepseek-is-reality-check-washington-cant-afford-to-get-wrong/',
        '/publications/2025/01/30/will-ai-regulation-avoid-past-mistakes-make-different-ones/',
        '/publications/2025/02/06/cbp-ai-to-manage-surge-inspections-after-partial-end-de-minimis/',
        '/publications/2025/02/07/ftc-working-temu-china-advances-ai/',
        '/publications/2025/02/13/reevaluating-us-ai-strategy-against-china/',
        '/publications/2025/02/20/selective-outrage-over-ai-and-copyright/',
        '/publications/2025/02/21/comments-california-privacy-protection-agencys-proposed-ai-regulations/',
        '/publications/2025/02/25/comments-to-the-uk-government-proposed-changes-cdpa-1988/',
        '/publications/2025/03/03/from-fast-follower-to-innovation-leader-restructuring-south-koreas-technology-regulation/',
        '/publications/2025/03/06/ai-is-key-to-trumps-education-overhaul/',
        '/publications/2025/03/14/comments-to-ostp-on-development-of-ai-action-plan/',
        '/publications/2025/03/24/virginias-ai-bill-is-a-misfire/',
        '/publications/2025/03/27/eu-should-resist-calls-to-regulate-ai-under-the-dma/',
        '/publications/2025/03/30/us-ai-policy-is-stuck-in-training-mode/',
        '/publications/2025/04/03/testimony-house-judiciary-committee-artificial-intelligence-trends-innovation-competition/',
        '/publications/2025/04/04/cpsc-should-leverage-ai-to-modernize-product-safety/',
        '/publications/2025/04/07/ai-is-powering-the-us-economy-but-whos-powering-ai/',
        '/publications/2025/04/08/ai-can-improve-us-small-business-productivity/',
        '/publications/2025/04/11/three-steps-trump-should-take-to-advance-government-ai-adoption/',
        '/publications/2025/04/14/antitrust-and-ai-key-takeaways-from-my-congressional-testimony/',
        '/publications/2025/04/15/strengthening-product-safety-enforcement-on-chinese-e-commerce-platforms/',
        '/publications/2025/04/16/an-it-policy-playbook-for-canada/',
        '/publications/2025/04/22/unlocking-promise-of-ai-for-state-department/',
        '/publications/2025/04/29/testimony-to-the-alaska-state-senate-regarding-ai-deepfakes-cybersecurity-and-data-transfers/',
        '/publications/2025/05/01/canada-should-harness-its-ai-advantage-not-squander-it/',
        '/publications/2025/05/01/countries-dont-have-to-build-their-own-ai-just-their-place-in-it/',
        '/publications/2025/05/05/export-controls-chip-away-us-ai-leadership/',
        '/publications/2025/05/07/congress-should-preempt-onslaught-of-state-ai-laws/',
        '/publications/2025/05/09/frequent-generative-ai-users-report-saving-hours-weekly-at-work/',
        '/publications/2025/05/12/if-ai-training-is-theft-then-everyones-thief/',
        '/publications/2025/05/21/ai-companions-risk-over-regulation-with-state-legislation/',
        '/publications/2025/05/29/comments-ostp-nitrd-development-national-artificial-intelligence-rd-strategic-plan/',
        '/publications/2025/05/30/fragmented-ai-laws-will-slow-federal-it-modernization-in-the-us/',
        '/publications/2025/06/02/germanys-new-digital-ministry-will-make-or-break-the-governments-ai-ambitions/',
        '/publications/2025/06/05/no-ai-robots-wont-take-all-our-jobs/',
        '/publications/2025/06/05/why-america-must-embrace-job-killing-technology/',
        '/publications/2025/06/06/comments-european-commission-regarding-apply-ai-strategy/',
        '/publications/2025/06/06/comments-european-commission-regarding-future-cloud-ai-policies-in-the-eu/',
        '/publications/2025/07/02/five-reasons-why-critics-were-wrong-about-the-ai-moratorium/',
        '/publications/2025/07/07/the-case-for-smarter-ai-regulation-with-matt-perault/',
        '/publications/2025/07/14/without-a-federal-moratorium-us-ai-policy-will-fragment-further/',
        '/publications/2025/07/21/letting-us-companies-sell-second-tier-chips-to-china-is-the-right-move/',
        '/publications/2025/07/22/comments-to-the-cma-on-its-proposed-google-sms-designation/',
        '/publications/2025/07/24/the-uk-should-learn-from-trump-on-ai-and-copyright/',
        '/publications/2025/07/25/the-ai-action-plan-puts-the-us-back-at-the-helm-of-global-ai-leadership/',
        '/publications/2025/07/28/ai-has-improved-monsoon-forecast-accuracy-in-india-by-20-percent/',
        '/publications/2025/08/01/ai-can-help-clean-philadelphia-up-and-give-workers-a-better-deal/',
        '/publications/2025/08/04/south-korea-should-choose-friends-over-foes-for-semiconductor-production/',
        '/publications/2025/08/08/comments-competition-bureau-of-canada-regarding-algorithmic-pricing-competition/',
        '/publications/2025/08/08/history-shows-why-creators-should-embrace-ai-not-fear-it/',
        '/publications/2025/08/15/the-hard-part-wont-be-exporting-us-ai-itll-be-making-it-stick/',
        '/publications/2025/08/22/why-the-airbus-model-wont-work-for-european-digital-policy/',
        '/publications/2025/08/28/the-growing-risks-of-fragmented-state-ai-laws/',
        '/publications/2025/09/04/ai-sovereignty-makes-everyone-weaker-the-us-can-lead-differently/',
        '/publications/2025/09/05/podcast-trumps-intel-deal-nvidias-next-moves-and-the-future-of-ai-regulation-with-daniel-castro/',
        '/publications/2025/09/08/americas-ai-action-plan-implications-for-biopharmaceutical-innovation/',
        '/publications/2025/09/11/how-some-states-are-resisting-unnecessary-ai-regulations/',
        '/publications/2025/09/18/hey-ai-job-doomers-wanna-bet/',
        '/publications/2025/09/22/ai-is-much-more-evolutionary-than-revolutionary/',
        '/publications/2025/09/25/china-not-the-us-is-the-eus-strategic-rival-in-tech/',
        '/publications/2025/09/29/one-law-sets-south-koreas-ai-policy-one-weak-link-could-break-it/',
        '/publications/2025/10/01/californias-restrictions-on-ai-in-the-workplace-will-hurt-workers/',
        '/publications/2025/10/01/koreas-ai-law-risks-stalling-the-engine-it-seeks-to-build/',
        '/publications/2025/10/03/californias-ai-safety-law-gets-more-wrong-than-right/',
        '/publications/2025/10/09/bernie-sanders-worker-dystopia-never-lose-job-never-get-raise/',
        '/publications/2025/10/16/wake-up-europe-its-time-to-get-serious-about-innovation/',
        '/publications/2025/10/27/data-center-capacity-will-need-increase-130-percent-by-2030-meet-demand-for-ai/',
        '/publications/2025/11/04/an-ai-job-apocalypse-watch-this-chart/',
        '/publications/2025/11/13/koreas-next-frontier-competing-through-physical-ai/',
        '/publications/2025/11/13/what-senator-blackburn-gets-wrong-about-google-s-ai/',
        '/publications/2025/11/17/the-ai-related-job-impacts-clarity-act-will-only-create-confusion/',
        '/publications/2025/11/19/bans-on-ai-companions-hurt-the-kids-they-aim-to-protect/',
        '/publications/2025/11/24/china-us-can-compete-and-cooperate-on-ai/',
        '/publications/2025/11/24/why-objections-to-federal-preemption-of-state-ai-laws-are-wrong/',
        '/publications/2025/12/04/banning-ai-superintelligence-would-be-a-historic-mistake/',
        '/publications/2025/12/05/getting-koreas-narrative-right-agi-is-a-productivity-shock-not-a-justification-for-public-compute/',
        '/publications/2025/12/12/why-the-dma-interoperability-investigations-poison-innovation/',
        '/publications/2025/12/15/comments-international-trade-administration-regarding-american-ai-exports-program/',
        '/publications/2025/12/15/will-ai-be-the-next-growth-engine-lets-hope-so/',
        '/publications/2025/12/18/ais-job-impact-gains-outpace-losses/',
        '/publications/2025/12/18/misunderstanding-the-british-industrial-revolution-is-reinforcing-technology-pessimism-about-ai/',
        '/publications/2025/12/18/trump-administration-gets-h200-chip-sales-to-china-right-and-wrong/',
        '/publications/2026/01/05/commuting-areas-far-from-ai-hotspots-experienced-17-percent-lower-growth-ai-jobs/',
        '/publications/2026/01/05/how-yesterdays-web-crawling-policies-will-shape-tomorrows-ai-leadership/',
        '/publications/2026/01/05/top-10-tech-policy-pronouncements-prognostications-and-questions-for-2026/',
        '/publications/2026/01/07/new-yorks-ai-safety-law-claims-national-alignment-but-delivers-fragmentation/',
        '/publications/2026/01/08/ten-ways-policymakers-should-respond-to-the-grok-bikini-fiasco/',
        '/publications/2026/01/12/construction-industry-facing-worker-shortage-driven-by-growth-of-data-centers/',
        '/publications/2026/02/04/the-sane-insanity-of-digital-sovereignty/',
        '/publications/2026/02/05/public-sector-ai-adoption-index/',
        '/publications/2026/02/13/event-recap-pre-summit-event-for-2026-ai-impact-summit/',
        '/publications/2026/02/18/are-we-in-the-middle-of-an-ai-boom-or-bubble/',
        '/publications/2026/02/19/hyundai-motors-humanoid-robot-debate-and-koreas-real-ai-challenge/',
        '/publications/2026/02/19/the-grid-act-is-the-wrong-way-to-protect-consumers-from-price-spikes/',
        '/publications/2026/02/26/survey-most-americans-say-tech-companies-should-allowed-set-ai-limits/',
        '/publications/2026/02/26/why-congress-should-step-into-the-anthropic-pentagon-dispute/',
        '/publications/2026/03/02/36-8-percent-individuals-oecd-countries-used-generative-ai-tools-2025/',
        '/publications/2026/03/02/higher-ed-has-a-ghost-problem-time-to-bust-it-with-digital-ids/',
        '/publications/2026/03/02/why-eu-whatsapp-third-party-ai-assistants-threatens-american-tech-leadership/',
        '/publications/2026/03/04/the-european-parliament-should-manage-built-in-ai-not-disable-it/',
        '/publications/2026/03/12/ubi-unbelievably-bad-idea/',
        '/publications/2026/03/13/how-rules-for-publicly-available-data-are-shaping-the-future-of-ai/',
        '/publications/2026/03/14/koreas-real-jobs-problem-isnt-ai/',
        '/publications/2026/03/15/will-artificial-intelligence-turn-out-to-be-a-dream-killer/',
        '/publications/2026/03/18/why-korea-should-rethink-data-localization-become-powerhouse/',
        '/publications/2026/03/19/polling-propaganda-blue-rose-research-ai-survey-misleads/',
        '/publications/2026/03/20/kctu-digital-policy-push-risks-protecting-yesterdays-jobs-expense-tomorrows-workers/',
        '/publications/2026/03/20/utah-shows-how-states-should-regulate-ai-in-healthcare/',
        '/publications/2026/03/23/agentic-commerce-is-coming-but-regulation-meant-for-humans-will-slow-it-down/',
        '/publications/2026/03/23/ai-and-kids-safety-need-separate-solutions-not-new-problems/',
        '/publications/2026/03/27/will-ai-really-eliminate-entry-level-jobs/',
        '/publications/2026/04/02/made-in-usa-claims-need-better-data-not-more-liability/',
        '/publications/2026/04/06/five-concerns-about-ai-data-centers-and-what-to-do-about-them/',
        '/publications/2026/04/07/four-reasons-new-ai-data-centers-wont-overwhelm-the-electricity-grid/',
        '/publications/2026/04/14/2026-antitrust-spring-meeting-jonathan-barnett-how-competition-enforcers-undermining-competition/',
        '/publications/2026/04/15/the-promise-of-wearable-ai-opportunities-across-emergency-response/',
        '/publications/2026/04/16/comments-to-house-oversight-regarding-ai-and-american-power/',
        '/publications/2026/04/16/no-ai-will-not-skyrocket-income-inequality/',
        '/publications/2026/04/17/federal-government-should-partner-with-frontier-ai-labs-on-cybersecurity-defense/',
        '/publications/2026/04/20/congress-should-support-innovation-in-freight-rail-not-stand-in-its-way/',
        '/publications/2026/04/26/japans-draft-ai-ip-code-misses-the-mark-undermining-us-alignment/',
        '/publications/2026/05/07/memorization-wont-prepare-students-for-the-age-of-agentic-ai/',
        '/publications/2026/05/11/pre-approval-for-ai-models-would-slow-innovation-without-improving-safety/',
        '/publications/2026/05/12/canadas-privacy-ruling-on-ai-training-data-sets-a-bad-precedent/',
        '/publications/2026/05/14/ai-not-going-reduce-labors-share-of-income-or-destroy-tax-base/',
        '/publications/2026/05/18/ai-is-a-productivity-engine-for-the-us-economy/',
        '/publications/2026/05/25/ai-is-not-another-tower-of-babel/',
        '/publications/2026/05/28/adapting-cybercorps-sfs-to-ai-threats-is-key-for-the-future-of-cybersecurity/',
        '/publications/2026/05/28/how-personalization-drives-consumer-choice-and-autonomy/',
        '/publications/2026/05/29/vaticans-ai-monopolies-talk-risks-encouraging-bad-tech-policy/',
        '/publications/2026/06/02/ai-drug-discovery-systems-could-strengthen-biopharmaceutical-innovation/',
        '/publications/2026/06/04/states-should-move-ai-pilot-programs-from-siloed-tests-to-statewide-deployment/',
        '/publications/2026/06/08/taxing-ai-compute-would-be-a-mistake/',
        '/publications/2026/06/09/the-cnn-perplexity-lawsuit-is-not-just-another-ai-copyright-case/',
        '/publications/2026/06/10/the-china-chip-strategy-that-is-backfiring-on-america/',
        '/publications/2026/06/11/popes-ai-encyclical-marks-triumph-social-capitalism-over-neoliberalism-part-i/',
        '/publications/2026/06/18/popes-ai-encyclical-marks-triumph-social-capitalism-over-neoliberalism-part-ii/',
        '/publications/2026/06/18/the-cities-getting-ai-right-are-investing-in-workforce-upskilling/',
        '/publications/2026/06/19/bad-taxes-would-slow-ai-innovation/',
        '/publications/2026/06/24/comments-european-commission-regarding-copyright-environment-in-europe/',
        '/publications/2026/06/26/the-united-states-needs-a-strategic-response-to-adversarial-ai-distillation/',
        '/publications/2026/06/29/the-guard-act-fails-to-guard-kids-best-interests-on-ai-companions/',
        '/publications/2026/06/30/new-evidence-contradicts-myth-that-ai-is-destroying-jobs/',
        '/publications/2026/07/02/what-chinas-hbm-catch-up-should-teach-korea/',
        '/publications/2026/07/06/the-data-center-water-problem-is-soluble/',
        '/publications/2026/07/13/no-50-robots-didnt-replace-1000-gm-workers/',
        '/publications/2026/07/13/universities-must-rethink-ai-education-for-the-ai-economy/',
        '/publications/2026/07/28/how-to-fix-the-ai-model-theft-bill-before-it-becomes-law/',
        '/publications/2026/07/31/time-for-18-month-moratorium-on-data-center-moratoriums/',
        '/publications/2026/08/03/congress-can-bring-clarity-to-ai-shutdown-authority/',
        '/publications/2026/08/04/meeting-the-ai-water-challenge/',
        '/publications/2026/08/10/how-policymakers-should-shouldnt-address-chatbot-safety-for-children/',
        '/publications/2026/08/14/labor-displacing-technology-is-good-for-labor/',
        '/publications/2026/08/17/canada-cant-subsidize-its-way-to-ai-adoption/',
        '/publications/2026/08/19/canadas-ai-strategy-focuses-on-wrong-firms/',
        '/publications/2026/08/20/getting-ais-workforce-impact-right-starts-with-better-data/',
        '/publications/2026/08/28/ai-companies-are-destroying-books-thats-not-nearly-as-scary-as-it-sounds/',
        '/publications/2026/08/28/ais-frontier-is-moving-its-legal-definition-should-too/',
        '/publications/2026/08/31/in-q1-2026-five-unicorn-firms-accounted-for-78-percent-of-all-deal-value/',
        '/publications/2026/09/01/america-is-building-ai-guardrails-but-where-is-the-road-forward/',
        '/publications/2026/09/04/pax-silica-timeline/',
        '/publications/2026/09/07/what-communities-stand-to-lose-by-blocking-data-centers/',
        '/publications/2026/09/08/gtipa-perspectives-making-ai-policy-to-drive-innovation/',
        '/publications/2026/09/08/investing-more-ai-experienced-roughly-one-percentage-point-productivity-growth-per-year/',
        '/publications/2026/09/08/transatlantic-subnational-innovation-competitiveness-index-3-0/',
        '/publications/2026/09/16/the-case-for-safer-ai-without-slowing-progress/',
        '/publications/2026/09/17/dont-sacrifice-american-capitalism-to-ai-anxiety/',
        '/publications/2026/09/18/ai-kill-switches-won-t-solve-the-rogue-ai-problem/',
        '/publications/2026/09/18/ai-triumphalists-complain-about-the-fear-they-induce/',
        '/publications/2026/09/22/the-eu-ai-acts-costs-to-american-innovation/',
        '/publications/2026/09/29/democrats-should-treat-data-centers-like-clean-energy/',
        '/publications/2026/09/30/europe-should-double-down-on-its-open-source-ai-bet/',
        '/publications/2026/10/02/developing-safety-standards-is-not-inherently-anticompetitive/',
        '/publications/2026/10/05/ai-infrastructure-could-draw-trillions-in-us-investment-through-2032/',
    }
)
# END CONFIRMED_AI_PATHS

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
    "citation_date",
    "citation_publication_date",
    "publish_date",
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
_PUBLISHER_KEYS = ("citation_publisher", "og:site_name", "dcterms.publisher", "publisher", "dc.publisher")
_GENERIC_TITLES = frozenset(
    {
        "itif",
        "information technology and innovation foundation",
        "information technology & innovation foundation",
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
_LINK = re.compile(r"(?is)<(?:link|a)\b[^>]*>")
_ANCHOR_ELEMENT = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
_CREDIT_PHRASE = re.compile(
    r"(?i)(?:\b(?:photo|caption|image)\s+credits?\b|\bphoto\s*:|\bwikimedia commons\b)"
)
_CREDIT_CLOSE = re.compile(
    r"(?i)</(?:p|figcaption|li|div|h[1-6]|blockquote|section|article|td|dd|cite|span|small|figure)\b"
)
_H1 = re.compile(r"(?is)<h1\b[^>]*>(.*?)</h1>")
_TITLE = re.compile(r"(?is)<title\b[^>]*>(.*?)</title>")
_ATTR = re.compile(
    r"""(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))"""
)
_DATED_PATH = re.compile(
    r"^/(?:publications|events)/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/"
    r"(?P<slug>[a-z0-9\u2019]+(?:-[a-z0-9\u2019]+)*)/$"
)
_SITE_SUFFIXES = (
    " | information technology and innovation foundation",
    " - information technology and innovation foundation",
    " – information technology and innovation foundation",
    " — information technology and innovation foundation",
    " | itif",
    " - itif",
    " – itif",
    " — itif",
)
_GENERIC_CC_HOSTS = frozenset({"creativecommons.org", "www.creativecommons.org"})
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
    ".md",
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
    "/admin",
)
_DONATE_MARKERS = ("/donate", "/donate-now", "/donation", "/donations", "/give")
_EXCLUDED_PREFIXES = (
    "/person/",
    "/people/",
    "/author-publications/",
    "/events-presentations/",
    "/feed/",
    "/search",
    "/cdn-cgi/",
)
_CHALLENGE_MARKERS = (
    "performing security verification",
    "challenge-platform",
    "cf-mitigated",
    "cdn-cgi/challenge",
    "sg-captcha",
    "sgcaptcha",
    "/.well-known/sgcaptcha/",
    "akamaighost",
    "errors.edgesuite.net",
    "hcaptcha",
    "g-recaptcha",
)
_CHALLENGE_TITLES = (
    "just a moment",
    "attention required",
    "checking your browser",
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
_US_GOV_WORK = re.compile(
    r"\b(?:united states|u\.s\.|us)\s+government\s+works?\b"
    r"|\bworks?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
)
_NEGATED_US_GOV = re.compile(
    r"\bnot\s+(?:a\s+)?(?:united states|u\.s\.|us)\s+government\s+works?\b"
    r"|\bnot\s+(?:a\s+)?works?\s+of\s+the\s+(?:united\s+states|u\.s\.|us)\s+government\b"
)
_MIT = re.compile(
    r"(?<!modified )(?:\bmit licen[cs]e\b|\blicen[cs]ed under (?:the )?mit licen[cs]e\b)"
)
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
    """A catalog row or page failed the ITIF AI page rules."""


def catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "catalogs" / CATALOG_FILENAME


def load_catalog(path: Path | None = None) -> dict:
    target = catalog_path() if path is None else Path(path)
    document = json.loads(target.read_text(encoding="utf-8"))
    return validate_catalog(document)


def is_official_host(hostname: str) -> bool:
    """True for itif.org and www.itif.org."""

    host = (hostname or "").strip().lower().rstrip(".")
    if not host or ".." in host or hostname_is_blocked(host):
        return False
    return host in OFFICIAL_HOSTS


def is_topic_path(path: str) -> bool:
    """True for a confirmed AI, machine-learning, or AI-policy HTML path."""

    if not isinstance(path, str) or not path.startswith("/") or not path.endswith("/"):
        return False
    if ".." in path or "//" in path or "\\" in path or "%" in path or any(char.isupper() for char in path):
        return False
    bare = path[:-1]
    if bare.endswith(_DOWNLOAD_SUFFIXES):
        return False
    if any(bare == marker or bare.startswith(marker + "/") for marker in _LOGIN_MARKERS):
        return False
    if any(bare == marker or bare.startswith(marker + "/") for marker in _DONATE_MARKERS):
        return False
    if any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
        return False
    if path not in CONFIRMED_AI_PATHS:
        return False
    if path == "/issues/artificial-intelligence/":
        return True
    match = _DATED_PATH.fullmatch(path)
    if match is None:
        return False
    try:
        date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    except ValueError:
        return False
    return True


def is_html_content_type(content_type: object) -> bool:
    if not isinstance(content_type, str) or not content_type.strip():
        return False
    return content_type.split(";", 1)[0].strip().casefold() in _HTML_TYPES


def is_challenge_page(page_html: str) -> bool:
    """True when the response is an interstitial rather than the page.

    A phrase such as "just a moment" inside the article body is not a challenge.
    """

    if not isinstance(page_html, str) or not page_html.strip():
        return False
    title = _TITLE.search(page_html[:12000])
    if title and any(marker in _plain(title.group(1)).casefold() for marker in _CHALLENGE_TITLES):
        return True
    head = page_html[:6000].casefold()
    return any(marker in head for marker in _CHALLENGE_MARKERS)


def robots_allows_path(robots_text: str, path: str, user_agent: str = "pdoom.live-collector") -> bool:
    """True when robots.txt does not disallow path for this collector.

    A challenge page served in place of robots.txt does not allow a fetch.
    """

    if not isinstance(robots_text, str):
        return False
    sample = robots_text[:800].casefold()
    if "<html" in sample or is_challenge_page(robots_text[:8000]):
        return False
    groups = _robots_groups(robots_text)
    if not groups:
        return True
    rules = _matching_rules(groups, user_agent)
    if rules is None:
        return True
    return _path_allowed(rules, path or "/")


def listing_is_blocked(
    path: str,
    *,
    status: object = None,
    content_type: object = None,
    page_html: object = None,
    headers: Mapping[str, str] | None = None,
    robots_txt: str | None = None,
    resolved: bool = True,
) -> bool:
    """True when a sitemap or listing must contribute an empty catalog.

    A Cloudflare challenge, a captcha, an authentication status, a failed
    resolution, or a robots.txt disallow blocks that path.
    """

    if resolved is False:
        return True
    if not isinstance(path, str) or not path.startswith("/"):
        return True
    if path in SKIPPED_LISTING_PATHS:
        return True
    if robots_txt is not None and not robots_allows_path(robots_txt, path):
        return True
    if status in {401, 403, 202, 429}:
        return True
    if isinstance(page_html, str) and is_challenge_page(page_html):
        return True
    if headers and _blocked_headers(headers):
        return True
    if status == 200 and page_html is not None and not response_stores_a_page(
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
    ):
        return True
    return False


def rows_for_listing(
    path: str,
    *,
    status: object = None,
    content_type: object = None,
    page_html: object = None,
    headers: Mapping[str, str] | None = None,
    robots_txt: str | None = None,
    resolved: bool = True,
) -> list[dict]:
    """Return no rows when a listing path is blocked.

    A readable listing is not itself a stored row unless that URL is confirmed
    separately. Child pages are recorded after their own GET.
    """

    if listing_is_blocked(
        path,
        status=status,
        content_type=content_type,
        page_html=page_html,
        headers=headers,
        robots_txt=robots_txt,
        resolved=resolved,
    ):
        return []
    return []


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
    or an off-host redirect is not stored.
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
    that names someone else's licence stays unknown, including a line that
    begins "Photo:". A software licence beside any Creative Commons deed stays
    unknown. Two software licences stay unknown. Two different restricted
    deeds stay unknown. Script, style, and comment text does not count.
    Apache License, Version 2.0 is apache-2.0.
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

    datePublished, article:published_time, citation_date, and publish_date
    count. article:modified_time, og:updated_time, dateModified, an updated or
    modified label, and a copyright year do not. Disagreeing publication dates
    stay unknown. Script text that is not publication metadata does not count.
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
    heading = _H1.search(visible)
    if heading:
        title = _usable_title(_TAG.sub(" ", heading.group(1)))
        if title:
            return title
    title_tag = _TITLE.search(visible)
    if title_tag:
        title = _usable_title(_TAG.sub(" ", title_tag.group(1)))
        if title:
            return title
    raise CatalogError("title is required")


def publisher_from_page(page_html: str) -> str:
    """Return the foundation name when the page states that name.

    A person named on the page is not the publisher. The ampersand form is
    not a substitute for the name.
    """

    if not isinstance(page_html, str):
        raise CatalogError("page must be text")
    visible = _without_hidden(page_html)
    metas = _metas(visible)
    for key in _PUBLISHER_KEYS:
        if PUBLISHER.casefold() in _clean_text(metas.get(key, "")).casefold():
            return PUBLISHER
    for raw in _jsonld_publisher_names(page_html):
        if PUBLISHER.casefold() in _clean_text(raw).casefold():
            return PUBLISHER
    if PUBLISHER.casefold() in _plain(visible).casefold():
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
        raise CatalogError("canonical URL must be a public ITIF artificial-intelligence page")
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
        or not is_topic_path(path)
    ):
        raise CatalogError(f"canonical URL is not a public ITIF artificial-intelligence page: {url}")
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
        if name in {"sg-captcha", "x-captcha"} or "captcha" in name:
            return True
        if name == "www-authenticate":
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


def _jsonld_publisher_names(page_html: str) -> list[str]:
    found: list[str] = []
    for block in _LDJSON.findall(page_html):
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        _collect_publisher_names(payload, found)
    return found


def _collect_publisher_names(payload: object, found: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_publisher_names(item, found)
        return
    if not isinstance(payload, dict):
        return
    publisher = payload.get("publisher")
    if isinstance(publisher, str):
        found.append(publisher)
    elif isinstance(publisher, dict):
        name = publisher.get("name")
        if isinstance(name, str):
            found.append(name)
    for value in payload.values():
        if isinstance(value, (dict, list)):
            _collect_publisher_names(value, found)


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

    A credit such as ``Photo credit: UNDRR, CC BY-NC-ND 2.0.`` or
    ``Photo: UNDRR, CC BY-NC-ND 2.0.`` is someone else's licence for an image.
    It is not a licence for the page. A decimal in a version number does not
    end the sentence.
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
        sentence_start = match.start()
        rewind = sentence_start - 1
        while rewind >= cursor:
            char = page_html[rewind]
            if char in "<>":
                rewind += 1
                break
            if char == ".":
                nxt = page_html[rewind + 1] if rewind + 1 < len(page_html) else ""
                if nxt.isdigit():
                    rewind -= 1
                    continue
                rewind += 1
                break
            rewind -= 1
        else:
            rewind = cursor
        out.append(page_html[cursor:rewind])
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
