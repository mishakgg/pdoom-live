"""Offline checks for the MIT FutureTech page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import re
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.futuretech as futuretech
from pdoom_pipeline.catalogs.futuretech import (
    CATALOG_ID,
    OFFICIAL_HOST,
    PUBLISHER,
    RIGHTS_APACHE,
    RIGHTS_CC_BY_NC,
    RIGHTS_CC_BY_NC_ND,
    RIGHTS_CC_BY_NC_SA,
    RIGHTS_CC_BY_ND,
    RIGHTS_CREATIVE_COMMONS,
    RIGHTS_CREATIVE_COMMONS_ATTRIBUTION,
    RIGHTS_MIT,
    RIGHTS_MPL,
    RIGHTS_UK_OGL,
    RIGHTS_UNKNOWN,
    RIGHTS_US_GOVERNMENT_WORK,
    RUNNER_WIRED,
    UNKNOWN_DATE,
    CatalogError,
    catalog_path,
    confirmed_fetch_url,
    is_challenge_page,
    load_catalog,
    official_futuretech_host,
    page_record,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    robots_allows,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

# Titles, publishers, canonical URLs, dates, and rights confirmed from one bounded GET each.
# The research index lists many works, so it has no single publication date.
# Publication pages state a date in pub-date-source. None of these pages state a reuse licence.
EXPECTED = [
    (
        "The Economic Impact of Moore's Law: Evidence from When it Faltered",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-economic-impact-of-moores-law-evidence-from-when-it-faltered",
        "2017-01-01",
        "unknown",
    ),
    (
        "Does Winning a Patent Race lead to more follow-on Innovation?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/does-winning-a-patent-race-lead-to-more-follow-on-innovation",
        "2017-01-15",
        "unknown",
    ),
    (
        "University licensing and the flow of scientific knowledge",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/university-licensing-and-the-flow-of-scientific-knowledge",
        "2017-07-01",
        "unknown",
    ),
    (
        "Science Is Shaped by Wikipedia: Evidence From a Randomized Control Trial",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/science-is-shaped-by-wikipedia-evidence-from-a-randomized-control-trial",
        "2017-09-01",
        "unknown",
    ),
    (
        "First Solar",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/first-solar",
        "2017-09-13",
        "unknown",
    ),
    (
        "Decomposing the \"Tacit Knowledge Problem:\" Codification of Knowledge and Access in CRISPR Gene-Editing",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/decomposing-the-tacit-knowledge-problem-codification-of-knowledge-and-access-in-crispr-gene-editing",
        "2017-11-01",
        "unknown",
    ),
    (
        "Trade Offs in Firm Culture? Nope You Can Have it All",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/trade-offs-firm-culture-nope-you-can-have-it-all",
        "2018-08-20",
        "unknown",
    ),
    (
        "Gene synthesis allows biologists to source genes from farther away in the tree of life",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/gene-synthesis-allows-biologists-to-source-genes-from-farther-away-in-the-tree-of-life",
        "2018-10-01",
        "unknown",
    ),
    (
        "How to Measure and Draw Causal Inferences with Patent Scope",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/how-to-measure-draw-causal-inferences-patent-scope",
        "2019-05-30",
        "unknown",
    ),
    (
        "The Close Relationship Between Management Practices and Corporate Culture",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/close-relationship-management-practices-corporate-culture",
        "2019-10-11",
        "unknown",
    ),
    (
        "Why Innovation's Future Isn't (Just) Open",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/why-innovations-future-isnt-just-open",
        "2020-05-11",
        "unknown",
    ),
    (
        "Building the algorithm commons: Who discovered the algorithms that underpin computing in the modern enterprise?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/building-the-algorithm-commons-who-discovered-the-algorithms-that-underpin-computing-in-the-modern-enterprise",
        "2020-06-01",
        "unknown",
    ),
    (
        "There's plenty of room at the Top: What will drive computer performance after Moore's law?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/theres-plenty-of-room-at-the-top-what-will-drive-computer-performance-after-moores-law",
        "2020-06-01",
        "unknown",
    ),
    (
        "The Computational Limits of Deep Learning",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-computational-limits-of-deep-learning",
        "2020-07-01",
        "unknown",
    ),
    (
        "The Decline of Computers as a General Purpose Technology",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-decline-of-computers-as-a-general-purpose-technology",
        "2021-03-01",
        "unknown",
    ),
    (
        "How Fast do Algorithms Improve?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/how-fast-do-algorithms-improve",
        "2021-09-01",
        "unknown",
    ),
    (
        "Deep Learning's Diminishing Returns: The Cost of Improvement is Becoming Unsustainable",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/deep-learning-diminishing-returns",
        "2021-10-08",
        "unknown",
    ),
    (
        "Compute Trends Across Three Eras of Machine Learning",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/compute-trends-across-three-eras-of-machine-learning",
        "2022-02-01",
        "unknown",
    ),
    (
        "The Importance of (Exponentially More) Computing Power",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-importance-of-exponentially-more-computing-power",
        "2022-06-01",
        "unknown",
    ),
    (
        "Trial by Internet: A Response to Judicial Critics",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/trial-by-internet-response-to-judicial-critics",
        "2022-06-14",
        "unknown",
    ),
    (
        "Trial by Internet: A Randomized Field Experiment on Wikipedia's Influence on Judges' Legal Reasoning",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/trial-by-internet-randomized-field-experiment",
        "2022-08-01",
        "unknown",
    ),
    (
        "Intentional and serendipitous diffusion of ideas: Evidence from academic conferences",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/intentional-serendipitous-diffusion-ideas",
        "2022-09-02",
        "unknown",
    ),
    (
        "Why Innovators in China Stay Close to the Market",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/why-innovators-china-stay-close-market",
        "2022-09-13",
        "unknown",
    ),
    (
        "The growing influence of industry in AI research",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-growing-influence-of-industry-in-ai-research",
        "2023-03-01",
        "unknown",
    ),
    (
        "Democratising case law while teaching students: writing Wikipedia articles on legal cases",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/democratising-case-law-teaching-students",
        "2023-06-01",
        "unknown",
    ),
    (
        "The Grand Illusion: The Myth of Software Portability and Implications for ML Progress",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/grand-illusion-myth-software-portability",
        "2023-09-12",
        "unknown",
    ),
    (
        "Unleash the Unexpected for Radical Innovation",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/unleash-unexpected-radical-innovation",
        "2023-09-12",
        "unknown",
    ),
    (
        "Large Language Model Routing with Benchmark Datasets",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/large-language-model-routing-benchmark-datasets",
        "2023-09-27",
        "unknown",
    ),
    (
        "What should be done about the growing influence of industry in AI research?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/what-should-be-done-growing-influence-industry-ai-research",
        "2023-12-05",
        "unknown",
    ),
    (
        "The Compute Divide in Machine Learning: A Threat to Academic Contribution and Scrutiny?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/compute-divide-machine-learning",
        "2024-01-08",
        "unknown",
    ),
    (
        "Beyond AI Exposure: Which Tasks are Cost-Effective to Automate with Computer Vision?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/beyond-ai-exposure-which-tasks-are-cost-effective-to-automate-with-computer-vision",
        "2024-02-08",
        "unknown",
    ),
    (
        "Algorithmic progress in language models",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/algorithmic-progress-in-language-models",
        "2024-03-09",
        "unknown",
    ),
    (
        "User-generated content shapes judicial reasoning: Evidence from a randomized control trial on Wikipedia",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/user-generated-content-shapes-judicial-reasoning",
        "2024-03-19",
        "unknown",
    ),
    (
        "A Model for Estimating the Economic Costs of Computer Vision Systems That Use Deep Learning",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/model-for-estimating-economic-costs-computer-vision",
        "2024-03-24",
        "unknown",
    ),
    (
        "Neural Scaling Laws for Embodied AI",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/neural-scaling-laws-embodied-ai",
        "2024-05-22",
        "unknown",
    ),
    (
        "Neural Scaling Laws in Robotics",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/neural-scaling-laws-robotics",
        "2024-05-22",
        "unknown",
    ),
    (
        "The AI Risk Repository: A Comprehensive Meta-Review, Database, and Taxonomy of Risks From Artificial Intelligence",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-ai-risk-repository",
        "2024-08-14",
        "unknown",
    ),
    (
        "The last mile problem: Why job automation will be slower than technological progress suggests",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/last-mile-problem-job-automation",
        "2024-08-29",
        "unknown",
    ),
    (
        "Economic impacts of AI-augmented R&D",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/economic-impacts-ai-augmented-rd",
        "2024-09-01",
        "unknown",
    ),
    (
        "Environmental uncertainty and entrepreneurial orientation in collectivist and individualist cultures: evidence from Brazil and Belgium",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/environmental-uncertainty-entrepreneurial-orientation",
        "2024-09-28",
        "unknown",
    ),
    (
        "Damocles's Switchboard: Information Externalities and the Autocratic Logic of Internet Control",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/damocless-switchboard-information-externalities-and-the-autocratic-logic-of-internet-control",
        "2024-10-31",
        "unknown",
    ),
    (
        "The dual edges of AI: Advancing knowledge while reducing diversity",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-dual-edges-of-ai",
        "2025-05-03",
        "unknown",
    ),
    (
        "Expertise",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/expertise",
        "2025-06-01",
        "unknown",
    ),
    (
        "Meek Models Shall Inherit the Earth",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/meek-models-shall-inherit-the-earth",
        "2025-06-05",
        "unknown",
    ),
    (
        "The Quantum Tortoise and the Classical Hare: When Will Quantum Computers Outpace Classical Ones and When Will They Be Left Behind?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-quantum-tortoise-and-the-classical-hare",
        "2025-06-19",
        "unknown",
    ),
    (
        "Introducing the Quantum Economic Advantage Online Calculator",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/introducing-the-quantum-economic-advantage-online-calculator",
        "2025-08-28",
        "unknown",
    ),
    (
        "Quantum Advantage in Computational Chemistry?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/quantum-advantage-in-computational-chemistry",
        "2025-08-28",
        "unknown",
    ),
    (
        "Mapping the Impact of Foundation Models on the UN Sustainable Development Goals",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/mapping-the-impact-of-foundation-models-on-the-un-sustainable-development-goals-kse1w",
        "2025-09-01",
        "unknown",
    ),
    (
        "Do Larger Firms Exert More Market Power? Markups and Markdowns along the Size Distribution",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/market-power-size",
        "2025-09-01",
        "unknown",
    ),
    (
        "Reconceiving the National Research Enterprise",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/reconceiving-the-national-research-enterprise",
        "2025-10-08",
        "unknown",
    ),
    (
        "Mapping the AI Governance Landscape",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/mapping-the-ai-governance-landscape",
        "2025-10-15",
        "unknown",
    ),
    (
        "LLMs in Citation Intent Classification: Progress, Precision, and Reproducibility Challenge",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/llms-in-citation-intent-classification-progress-precision-and-reproducibility-challenge",
        "2025-10-21",
        "unknown",
    ),
    (
        "Quantum Deep Learning Still Needs a Quantum Leap",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/quantum-deep-learning-still-needs-a-quantum-leap",
        "2025-11-03",
        "unknown",
    ),
    (
        "The Rapid Growth of AI Foundation Model Usage in Science",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-rapid-growth-of-ai-foundation-model-usage-in-science",
        "2025-11-21",
        "unknown",
    ),
    (
        "EvilGenie: A Reward Hacking Benchmark",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/evilgenie-a-reward-hacking-benchmark",
        "2025-11-26",
        "unknown",
    ),
    (
        "On the Origin of Algorithmic Progress in AI",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/on-the-origin-of-algorithmic-progress-in-ai-u7f18",
        "2025-11-26",
        "unknown",
    ),
    (
        "How fast are algorithms reducing the demands on memory? A survey of progress in space complexity",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/how-fast-are-algorithms-reducing-the-demands-on-memory-a-survey-of-progress-in-space-complexity",
        "2025-11-27",
        "unknown",
    ),
    (
        "The Price of Progress: Algorithmic Efficiency and the Falling Cost of AI Inference",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-price-of-progress-algorithmic-efficiency-and-the-falling-cost-of-ai-inference",
        "2025-11-28",
        "unknown",
    ),
    (
        "Mapping AI Risk Mitigations: Evidence Scan and Preliminary AI Risk Mitigation Taxonomy",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/mapping-ai-risk-mitigations-evidence-scan-and-preliminary-ai-risk-mitigation-taxonomy",
        "2025-12-12",
        "unknown",
    ),
    (
        "AI and Scale: A Quantitative Task-Based Theory of Automation",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/ai-and-scale-a-quantitative-task-based-theory-of-automation",
        "2026-01-01",
        "unknown",
    ),
    (
        "Four Facts About U.S.-China AI Competition in Science",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/four-facts-about-u-s--china-ai-competition-in-science",
        "2026-01-16",
        "unknown",
    ),
    (
        "How Much Progress Has There Been in NVIDIA Datacenter GPUs?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/how-much-progress-has-there-been-in-nvidia-datacenter-gpus",
        "2026-01-27",
        "unknown",
    ),
    (
        "Is there \"Secret Sauce'' in Large Language Model Development?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/is-there-secret-sauce-in-large-language-model-development",
        "2026-02-06",
        "unknown",
    ),
    (
        "Identifying Rent-Sharing using Firms’ Energy Input Mix",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/identifying-rent-sharing-using-firms-energy-input-mix",
        "2026-02-20",
        "unknown",
    ),
    (
        "The AI risk repository: A meta-review, database, and taxonomy of risks from artificial intelligence",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-ai-risk-repository-a-meta-review-database-and-taxonomy-of-risks-from-artificial-intelligence",
        "2026-03-30",
        "unknown",
    ),
    (
        "From Shares to Machines: How Common Ownership Drives Automation",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/from-shares-to-machines-how-common-ownership-drives-automation",
        "2026-04-16",
        "unknown",
    ),
    (
        "AI Incident Monitoring through a Public Health Lens",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/ai-incident-monitoring-through-a-public-health-lens",
        "2026-04-21",
        "unknown",
    ),
    (
        "A simple classification of AI incident trajectories",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/a-simple-classification-of-ai-incident-trajectories",
        "2026-04-23",
        "unknown",
    ),
    (
        "AI and Scale: A Quantitative Task-Based Theory of Automation",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/ai-and-scale-a-quantitative-task-based-theory-of-automation-2",
        "2026-05-05",
        "unknown",
    ),
    (
        "Risks Create a Jagged Frontier of LLM Productivity Gains Across Computer Occupations",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/risks-create-a-jagged-frontier-of-llm-productivity-gains-across-computer-occupations",
        "2026-05-13",
        "unknown",
    ),
    (
        "Prioritization of Risks from Artificial Intelligence: A Delphi Study of 272 International Experts",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/prioritization-of-risks-from-artificial-intelligence-a-delphi-study-of-272-international-experts",
        "2026-06-04",
        "unknown",
    ),
    (
        "The Shrinking Lifespan of LLMs in Science",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-shrinking-lifespan-of-llms-in-science",
        "2026-06-12",
        "unknown",
    ),
    (
        "Two AI Metrics Diverged: Will it Make All the Difference?",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/two-ai-metrics-diverged-will-it-make-all-the-difference",
        "2026-07-01",
        "unknown",
    ),
    (
        "AI Adoption in S&P 500 Firms",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/ai-adoption-in-s-p-500-firms",
        "2026-07-13",
        "unknown",
    ),
    (
        "Crashing Waves vs. Rising Tides: Preliminary Findings on AI Automation from Thousands of Worker Evaluations of Labor Market Tasks",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/crashing-waves-vs-rising-tides-preliminary-findings-on-ai-automation-from-thousands-of-worker-evaluations-of-labor-market-tasks",
        "2026-07-21",
        "unknown",
    ),
    (
        "Birth, Life, and Death of AI Models",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/birth-life-and-death-of-ai-models",
        "2026-09-09",
        "unknown",
    ),
    (
        "Scientific Work",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/scientific-work",
        "2026-09-14",
        "unknown",
    ),
    (
        "The AI-Enabled Scientific Frontier",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-ai-enabled-scientific-frontier-3h8uh",
        "2026-09-14",
        "unknown",
    ),
    (
        "AI in Science: Early Insights",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/ai-in-science-early-insights",
        "2026-09-16",
        "unknown",
    ),
    (
        "Mapping U.S. Federal AI Governance Against Sector Vulnerability",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/mapping-u-s-federal-ai-governance-against-sector-vulnerability",
        "2026-09-16",
        "unknown",
    ),
    (
        "The Shrinking Lifespan of LLMs in Science",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/the-shrinking-lifespan-of-llms-in-science-2",
        "2026-09-25",
        "unknown",
    ),
    (
        "Open Science, Closed Models: How Funding Shapes AI in Science",
        "MIT FutureTech",
        "https://futuretech.mit.edu/publication/open-science-closed-models-how-funding-shapes-ai-in-science",
        "2026-09-26",
        "unknown",
    ),
    (
        "Research",
        "MIT FutureTech",
        "https://futuretech.mit.edu/research",
        "unknown",
        "unknown",
    ),
]

SAMPLE_URL = "https://futuretech.mit.edu/publication/a-simple-classification-of-ai-incident-trajectories"
BODY = (
    "We classify public AI incident reports into a small set of trajectories. "
    "This paragraph is not catalog metadata."
)
REJECTED_URLS = [
    "http://futuretech.mit.edu/research",
    "https://www.futuretech.mit.edu/research",
    "https://mit.edu/research",
    "https://www.mit.edu/research",
    "https://news.mit.edu/2024/futuretech",
    "https://accessibility.mit.edu/",
    "https://cdn.prod.website-files.com/6501f77fe3413fa9dbfbd69d/file",
    "https://arxiv.org/abs/2604.19914",
    "https://futuretech.mit.edu/publication/paper.pdf",
    "https://futuretech.mit.edu/publication/a-simple-classification-of-ai-incident-trajectories/",
    "https://futuretech.mit.edu/research/",
    "https://futuretech.mit.edu/",
    "https://futuretech.mit.edu/team",
    "https://futuretech.mit.edu/news",
    "https://futuretech.mit.edu/about",
    "https://futuretech.mit.edu/datasets",
    "https://futuretech.mit.edu/search",
    "https://futuretech.mit.edu/publication/foo?download=1",
    "https://futuretech.mit.edu/research#papers",
    "https://user:pass@futuretech.mit.edu/research",
    "https://futuretech.mit.edu:443/research",
    "https://127.0.0.1/research",
    "https://169.254.169.254/latest/meta-data/",
    "https://futuretech.mit.edu/publication/../research",
    "https://futuretech.mit.edu/login",
]
CLOUDFLARE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing futuretech.mit.edu. "
    "cf-mitigated: challenge challenge-platform</body></html>"
)
SITEGROUND_HTML = (
    "<html><head><meta http-equiv=\"refresh\" "
    "content=\"0;/.well-known/sgcaptcha/?r=%2Fresearch\"></head>"
    "<body>sg-captcha</body></html>"
)
AKAMAI_HTML = (
    "<html><head><title>Access Denied</title></head>"
    "<body>You don't have permission to access. AkamaiGHost errors.edgesuite.net</body></html>"
)
ROBOTS_SITEMAP = "Sitemap: https://futuretech.mit.edu/sitemap.xml\n"
ROBOTS_404 = "<!DOCTYPE html><html><title>404: Page not found</title><p>Page not found</p></html>"


def _page(title: str, canonical: str, *, published: str | None = None, updated: str | None = None) -> str:
    published_tag = (
        f'<meta property="article:published_time" content="{published}">' if published else ""
    )
    updated_tag = f'<meta property="article:modified_time" content="{updated}">' if updated else ""
    return (
        "<html><head>"
        f"<title>FutureTech</title>"
        f'<meta property="og:title" content="{title}">'
        '<meta property="og:site_name" content="MIT FutureTech">'
        f"{published_tag}{updated_tag}"
        f'<link rel="canonical" href="{canonical}">'
        "</head><body>"
        f'<h1 class="heading-copy">{title}</h1>'
        '<h1 class="heading-6">Neil Thompson</h1>'
        f"<p>{BODY}</p>"
        "<footer><strong>MIT\u00a0FutureTech</strong><br>© 2026 FutureTech. All rights reserved.</footer>"
        "</body></html>"
    )


def test_catalog_load_does_not_use_the_network(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("catalog load must not use the network")

    monkeypatch.setattr(socket, "socket", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    document = load_catalog()
    assert document["catalog_id"] == CATALOG_ID
    assert document["runner_wired"] is False
    assert len(document["entries"]) == len(EXPECTED)


def test_committed_catalog_matches_confirmed_pages():
    document = load_catalog()
    assert catalog_path().name == "futuretech_pages.json"
    assert document["runner_wired"] is False
    assert RUNNER_WIRED is False
    description = document["description"]
    assert OFFICIAL_HOST in description
    assert "bounded GET" in description
    assert "robots.txt" in description
    assert "creative_commons" in description
    assert "creative_commons_attribution" in description
    assert "runner_wired is false" in description
    assert "belief collector" in description
    assert len(description) <= 800
    raw = catalog_path().read_text(encoding="utf-8")
    for host in (
        "www.futuretech.mit.edu",
        "www.mit.edu",
        "news.mit.edu",
        "accessibility.mit.edu",
        "arxiv.org",
        "cdn.prod.website-files.com",
        "twitter.com",
        "youtube.com",
    ):
        assert host not in raw
    assert "<html" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert BODY not in raw
    parsed = json.loads(raw)
    assert set(parsed) == {"catalog_id", "description", "runner_wired", "entries"}
    entries = document["entries"]
    assert [
        tuple(entry[field] for field in ("title", "publisher", "canonical_url", "date", "rights"))
        for entry in entries
    ] == list(EXPECTED)
    rights_counts = {
        label: 0
        for label in (
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
        )
    }
    unknown_dates = 0
    hosts = set()
    forbidden = {"abstract", "body", "chart", "chart_data", "quote", "transcript", "page_text", "pdf"}
    for entry in entries:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert forbidden.isdisjoint(entry)
        assert entry["publisher"] == PUBLISHER
        host = entry["canonical_url"].split("/")[2]
        hosts.add(host)
        assert host == OFFICIAL_HOST
        assert official_futuretech_host(host)
        assert entry["date"] == UNKNOWN_DATE or re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
        rights_counts[entry["rights"]] += 1
        if entry["date"] == UNKNOWN_DATE:
            unknown_dates += 1
    assert hosts == {OFFICIAL_HOST}
    assert len(entries) == 83
    assert rights_counts[RIGHTS_UNKNOWN] == 83
    assert unknown_dates == 1
    assert sum(rights_counts.values()) == 83
    by_url = {entry["canonical_url"]: entry for entry in entries}
    research = by_url["https://futuretech.mit.edu/research"]
    assert research["title"] == "Research"
    assert research["date"] == UNKNOWN_DATE
    assert research["rights"] == RIGHTS_UNKNOWN
    paper = by_url[SAMPLE_URL]
    assert paper["title"] == "A simple classification of AI incident trajectories"
    assert paper["date"] == "2026-04-23"
    assert paper["publisher"] == PUBLISHER
    assert "<" not in paper["title"]


def test_sole_restricted_deeds_keep_their_tokens():
    assert rights_from_page("<p>CC BY-NC</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>cc-by-nc</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY-ND</p>") == RIGHTS_CC_BY_ND
    assert rights_from_page("<p>CC BY-NC-ND</p>") == RIGHTS_CC_BY_NC_ND
    assert rights_from_page("<p>CC BY-NC-SA</p>") == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>CC BY</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>CC BY</p>") != RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY-NC and CC BY-ND</p>") == RIGHTS_UNKNOWN
    source = Path(futuretech.__file__).read_text(encoding="utf-8")
    assert "(?!-)" in source
    assert "cc-by-nc" not in source.split("RIGHTS_CC_BY_NC = ")[1].split("\n", 1)[0]


def test_permissive_deeds_and_mixed_text():
    assert rights_from_page("<p>This work is licensed under CC BY 4.0.</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>This work is licensed under CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>This work is licensed under CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC0 and CC BY-SA 4.0.</p>") == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page("<p>CC BY 4.0 and CC0.</p>") == RIGHTS_CREATIVE_COMMONS
    mixed = "<p>This work is CC BY 4.0 and also CC BY-NC.</p>"
    assert rights_from_page(mixed) == RIGHTS_UNKNOWN
    both_urls = (
        '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>'
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC</a>'
    )
    assert rights_from_page(both_urls) == RIGHTS_UNKNOWN


def test_misleading_anchors_and_generic_license_urls_stay_unknown():
    cases = [
        '<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/by-nd/4.0/">CC BY-SA</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC BY</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC BY-SA</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">CC0</a>',
        '<a href="https://creativecommons.org/publicdomain/mark/1.0/">Public Domain Mark</a>',
        '<a href="https://creativecommons.org/licenses/">CC BY</a>',
        '<a href="https://creativecommons.org/licenses/">CC BY 4.0</a>',
        '<a href="https://creativecommons.org/licenses/">CC BY-SA</a>',
        '<a href="https://creativecommons.org/licenses/">Creative Commons</a>',
        "<footer>© 2026 FutureTech. All rights reserved.</footer>",
        "<p>This page is Public. See the terms. Hosted at futuretech.mit.edu.</p>",
        '<a href="https://futuretech.mit.edu/">MIT FutureTech</a>',
        "<script>CC BY 4.0</script><p>All rights reserved.</p>",
        "<style>CC BY 4.0</style><p>All rights reserved.</p>",
        "<!-- CC BY 4.0 --><p>All rights reserved.</p>",
    ]
    for html in cases:
        assert rights_from_page(html) == RIGHTS_UNKNOWN, html
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">licence</a>') == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">CC BY</a>') == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<link rel="license" href="https://creativecommons.org/licenses/by-nc-nd/4.0/">') == RIGHTS_CC_BY_NC_ND
    generic_plus_zero = (
        '<p>This work is licensed under CC0.</p>'
        '<a href="https://creativecommons.org/licenses/">CC BY</a>'
    )
    assert rights_from_page(generic_plus_zero) == RIGHTS_CREATIVE_COMMONS


def test_software_licences_and_open_government_licence():
    assert rights_from_page("<p>MIT License</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Apache License, Version 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache License 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Mozilla Public License 2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MPL-2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>The Massachusetts Institute of Technology.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and Apache-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and MPL-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and CC BY-SA 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and CC BY-NC.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MPL-2.0 and CC0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Open Government Licence v3.0</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>Licensed under the Open Government License v3.0.</p>") == RIGHTS_UNKNOWN
    archives = '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">terms</a>'
    assert rights_from_page(archives) == RIGHTS_UNKNOWN
    rights_field = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(rights_field) == RIGHTS_US_GOVERNMENT_WORK
    assert rights_from_page("<p>This is a work of the United States Government.</p>") == RIGHTS_UNKNOWN


def test_publication_dates_ignore_updated_modified_and_copyright_years():
    stated = (
        '<div class="pub-date-source visually-hidden">April 23, 2026</div>'
        '<div class="publication-card-text date">September 2026</div>'
        '<meta property="article:modified_time" content="2026-10-01T00:00:00Z">'
        '<meta property="og:updated_time" content="2026-11-01T00:00:00Z">'
        "<!-- Last Published: Fri Oct 02 2026 20:24:59 GMT+0000 (Coordinated Universal Time) -->"
        "<p>© 2026 FutureTech. All rights reserved.</p>"
    )
    assert publication_date_from_page(stated) == "2026-04-23"
    listing = (
        '<div class="pub-date-source">January 1, 2017</div>'
        '<div class="pub-date-source">June 12, 2026</div>'
    )
    assert publication_date_from_page(listing) == UNKNOWN_DATE
    updated = "<p>Last update: May 2026.</p><p>Updated 2024-05-01</p><p>© 2020 FutureTech</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    modified = '<meta property="article:modified_time" content="2024-04-18T14:43:38.000Z">'
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    meta_only = '<meta property="article:published_time" content="2024-03-21T00:00:00+09:00">'
    assert publication_date_from_page(meta_only) == "2024-03-21"
    many_times = (
        '<time datetime="2026-01-01T00:00:00Z">January 1, 2026</time>'
        '<time datetime="2026-02-02T00:00:00Z">February 2, 2026</time>'
        '<div class="pub-date-source">April 23, 2026</div>'
    )
    assert publication_date_from_page(many_times) == UNKNOWN_DATE
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2026-04-23") == "2026-04-23"
    with pytest.raises(CatalogError, match="date"):
        validate_date("23 April 2026")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    html = (
        "<html><head><title>FutureTech</title></head><body>"
        '<h1 class="heading-copy">A simple classification of AI incident trajectories</h1>'
        '<h1 class="heading-6">Isaak Mengesha</h1>'
        f"<p>{BODY}</p>"
        '<div class="pub-date-source">April 23, 2026</div>'
        "<footer><strong>MIT\u00a0FutureTech</strong> © 2026 FutureTech</footer>"
        "</body></html>"
    )
    record = page_record(html, page_url=SAMPLE_URL)
    assert record["title"] == "A simple classification of AI incident trajectories"
    assert record["publisher"] == PUBLISHER
    assert record["canonical_url"] == SAMPLE_URL
    assert record["date"] == "2026-04-23"
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    stored = json.dumps(record)
    assert BODY not in stored
    assert "Isaak Mengesha" not in stored
    assert "2026-10-02" not in stored


def test_a_different_canonical_link_does_not_replace_the_live_url():
    html = _page("A simple classification of AI incident trajectories", "https://arxiv.org/abs/2604.19914")
    record = page_record(html, page_url=SAMPLE_URL)
    assert record["canonical_url"] == SAMPLE_URL


def test_a_person_is_not_the_publisher():
    record = page_record(_page("A simple classification of AI incident trajectories", SAMPLE_URL), page_url=SAMPLE_URL)
    assert record["publisher"] == PUBLISHER
    assert record["title"] == "A simple classification of AI incident trajectories"
    missing = (
        "<html><head><title>A note</title></head><body>"
        "<h1>A note</h1><p>By Neil Thompson.</p></body></html>"
    )
    with pytest.raises(CatalogError, match="publisher"):
        page_record(missing, page_url=SAMPLE_URL)


def test_challenge_status_and_off_host_redirect_are_not_stored():
    assert is_challenge_page(CLOUDFLARE_HTML)
    assert is_challenge_page(SITEGROUND_HTML)
    assert record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=CLOUDFLARE_HTML,
        page_url=SAMPLE_URL,
        headers={"cf-mitigated": "challenge"},
    ) is None
    assert record_from_response(
        status=200,
        content_type="text/html",
        page_html=SITEGROUND_HTML,
        page_url=SAMPLE_URL,
        headers={"sg-captcha": "challenge"},
    ) is None
    assert record_from_response(
        status=202,
        content_type="text/html; charset=UTF-8",
        page_html=_page("Research", "https://futuretech.mit.edu/research"),
        page_url="https://futuretech.mit.edu/research",
    ) is None
    assert record_from_response(
        status=403,
        content_type="text/html",
        page_html=AKAMAI_HTML,
        page_url=SAMPLE_URL,
        headers={"server": "AkamaiGHost"},
    ) is None
    assert record_from_response(
        status=404,
        content_type="text/html",
        page_html=_page("Research", "https://futuretech.mit.edu/research"),
        page_url="https://futuretech.mit.edu/research",
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7 synthetic",
        page_url=SAMPLE_URL,
    ) is None
    assert confirmed_fetch_url(SAMPLE_URL, "https://arxiv.org/abs/2604.19914") is None
    assert confirmed_fetch_url("https://futuretech.mit.edu/research", "https://news.mit.edu/research") is None
    assert confirmed_fetch_url(SAMPLE_URL, "https://futuretech.mit.edu/research") is None
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page(
            "A simple classification of AI incident trajectories",
            SAMPLE_URL,
            published="2026-04-23T00:00:00Z",
            updated="2026-10-02T00:00:00Z",
        ),
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
    )
    assert stored is not None
    assert stored["canonical_url"] == SAMPLE_URL
    assert stored["date"] == "2026-04-23"
    assert BODY not in json.dumps(stored)


def test_robots_sitemap_allows_research_paths_and_a_disallow_blocks_them():
    assert robots_allows(ROBOTS_SITEMAP, "/research")
    assert robots_allows(ROBOTS_SITEMAP, "/publication/a-simple-classification-of-ai-incident-trajectories")
    assert robots_allows(ROBOTS_404, "/research")
    assert robots_allows("", "/research")
    blocked = "User-agent: *\nDisallow: /\n"
    assert robots_allows(blocked, "/research") is False
    assert robots_allows(blocked, "/publication/a-simple-classification-of-ai-incident-trajectories") is False
    private = "User-agent: *\nDisallow: /publication/\nAllow: /research\n"
    assert robots_allows(private, "/research") is True
    assert robots_allows(private, "/publication/a-simple-classification-of-ai-incident-trajectories") is False


def test_non_futuretech_urls_are_rejected():
    for rejected in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(rejected)


@pytest.mark.parametrize(
    "url",
    [
        "https://futuretech.mit.edu/research",
        SAMPLE_URL,
        "https://futuretech.mit.edu/publication/four-facts-about-u-s--china-ai-competition-in-science",
    ],
)
def test_official_futuretech_urls_are_accepted(url: str):
    assert validate_canonical_url(url) == url
    assert official_futuretech_host(url.split("/")[2])


def test_validator_rejects_bad_rights_and_accepts_an_empty_list():
    document = copy.deepcopy(load_catalog())
    document["entries"] = []
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = RIGHTS_CC_BY_NC
    validate_catalog(document)
    document["entries"][0]["rights"] = "cc-by-nc"
    with pytest.raises(CatalogError, match="rights"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["body"] = BODY
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["abstract"] = "a stored abstract"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["quote"] = "a stored quote"
    with pytest.raises(CatalogError):
        validate_catalog(document)
    document = copy.deepcopy(load_catalog())
    document["entries"][0]["pdf"] = "https://futuretech.mit.edu/paper.pdf"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["canonical_url"] = "https://news.mit.edu/research"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0], document["entries"][1] = document["entries"][1], document["entries"][0]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)


def test_catalog_is_not_wired_into_belief_collection():
    module = Path(futuretech.__file__).read_text(encoding="utf-8")
    tree = ast.parse(module)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "requests" not in imported
    assert "pdoom_pipeline.fetch" not in imported
    assert "pdoom_pipeline.belief" not in imported
    assert "pdoom_pipeline.belief.collect" not in imported
    assert not re.search(r"(?m)^\s*(?:import|from)\s+requests\b", module)
    assert "hostname_is_blocked" in module
    assert "runner_wired = True" not in module

    root = Path(__file__).resolve().parents[1]
    init = (root / "pipeline" / "pdoom_pipeline" / "catalogs" / "__init__.py").read_text(encoding="utf-8")
    assert init.strip() == '"""Package marker."""'
    assert "futuretech" not in init
    collectors = (root / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py").read_text(encoding="utf-8")
    assert collectors.strip() == '"""Package marker."""'
    assert "futuretech" not in collectors
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "futuretech_pages" not in text
        assert "catalogs.futuretech" not in text
    collect = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in collect
