"""Offline checks for the DAIR Institute page catalog. No network."""

from __future__ import annotations

import ast
import copy
import json
import re
import socket
from pathlib import Path

import pytest

import pdoom_pipeline.catalogs.dair as dair
from pdoom_pipeline.catalogs.dair import (
    CATALOG_ID,
    OFFICIAL_HOST,
    OFFICIAL_HOSTS,
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
    official_dair_host,
    page_record,
    publication_date_from_page,
    record_from_response,
    rights_from_page,
    robots_allows,
    validate_canonical_url,
    validate_catalog,
    validate_date,
)

EXPECTED = [
    [
        "Celebrating Our First Anniversary!",
        "DAIR Institute",
        "https://dair-institute.org/blog/first-year-anniversary/",
        "2022-12-02",
        "unknown"
    ],
    [
        "Statement on the \"AI pause\" letter",
        "DAIR Institute",
        "https://dair-institute.org/blog/letter-statement-March2023/",
        "2023-03-31",
        "creative_commons_attribution"
    ],
    [
        "Possible Futures: Nobody Owns the Technofuture",
        "DAIR Institute",
        "https://dair-institute.org/blog/nobody-owns-the-technofuture/",
        "2023-07-12",
        "unknown"
    ],
    [
        "Applauding Congress holding big tech accountable",
        "DAIR Institute",
        "https://dair-institute.org/blog/turkopticon-applaud/",
        "2023-09-24",
        "unknown"
    ],
    [
        "Ceasefire Now!",
        "DAIR Institute",
        "https://dair-institute.org/blog/palestine-10-25-23/",
        "2023-10-25",
        "unknown"
    ],
    [
        "Celebrating Our Second Anniversary",
        "DAIR Institute",
        "https://dair-institute.org/blog/celebrating-our-second-anniversary/",
        "2023-12-02",
        "unknown"
    ],
    [
        "#NoTechForApartheid",
        "DAIR Institute",
        "https://dair-institute.org/blog/notechforapartheid/",
        "2023-12-04",
        "unknown"
    ],
    [
        "A Bus Model For Global, Human-Centered Education",
        "DAIR Institute",
        "https://dair-institute.org/blog/education/",
        "2024-04-18",
        "unknown"
    ],
    [
        "Notes on Social Media Data Collection",
        "DAIR Institute",
        "https://dair-institute.org/blog/notes-on-scaling-social-media-data-collection/",
        "2024-06-12",
        "unknown"
    ],
    [
        "Possible Futures: An Internet for Our Elders",
        "DAIR Institute",
        "https://dair-institute.org/blog/an-internet-for-our-elders/",
        "2024-06-18",
        "unknown"
    ],
    [
        "Closure for Families of the Missing",
        "DAIR Institute",
        "https://dair-institute.org/blog/eritreans/",
        "2024-08-29",
        "unknown"
    ],
    [
        "Decentralized, Locally-Tailored Technology",
        "DAIR Institute",
        "https://dair-institute.org/blog/decentralized-locally-tailored-technology/",
        "2024-12-03",
        "unknown"
    ],
    [
        "A Future of Thriving Students and Teachers",
        "DAIR Institute",
        "https://dair-institute.org/blog/a-future-of-thriving-students-and-teachers/",
        "2025-01-31",
        "unknown"
    ],
    [
        "A New Escalation of Conflict Between Ethiopia and Eritrea",
        "DAIR Institute",
        "https://dair-institute.org/blog/statement-a-new-escalation-of-conflict-between-ethiopia-and-eritrea/",
        "2025-04-01",
        "unknown"
    ],
    [
        "Imagining a Safer Future for Content Moderators",
        "DAIR Institute",
        "https://dair-institute.org/blog/imagining-a-safer-future-for-content-moderators/",
        "2025-04-30",
        "unknown"
    ],
    [
        "Dr. Milagros Miceli, Named to Third Annual TIME100 AI List",
        "DAIR Institute",
        "https://dair-institute.org/blog/milagros-miceli-time-100-ai-eng/",
        "2025-08-28",
        "unknown"
    ],
    [
        "Dr. Milagros Miceli, entre las 100 de TIME en IA",
        "DAIR Institute",
        "https://dair-institute.org/blog/milagros-miceli-time-100-ai-esp/",
        "2025-08-28",
        "unknown"
    ],
    [
        "Tech for Reclaiming our Oral Histories",
        "DAIR Institute",
        "https://dair-institute.org/blog/tech-for-reclaiming-our-oral-histories/",
        "2025-09-29",
        "unknown"
    ],
    [
        "Driven Down Report",
        "DAIR Institute",
        "https://dair-institute.org/blog/amazon-is-building-a-surveillance-empire-on-the-backs-of-delivery-drivers/",
        "2025-12-02",
        "unknown"
    ],
    [
        "Celebrating Our Fourth Anniversary!",
        "DAIR Institute",
        "https://dair-institute.org/blog/celebrating-our-fourth-anniversary/",
        "2025-12-03",
        "unknown"
    ],
    [
        "Powerful New Report Sheds Light on AI Intimacy",
        "DAIR Institute",
        "https://dair-institute.org/blog/powerful-new-report-sheds-light-on-hidden-world-of-ai-intimacy/",
        "2025-12-12",
        "unknown"
    ],
    [
        "Timnit Gebru Named One of Ten Greatest Minds in Tech",
        "DAIR Institute",
        "https://dair-institute.org/blog/timnit-gebru-named-one-of-ten-greatest-minds-in-tech/",
        "2025-12-14",
        "unknown"
    ],
    [
        "Meet The Humans Behind the Chatbot",
        "DAIR Institute",
        "https://dair-institute.org/blog/meet-the-humans-behind-the-chatbot/",
        "2026-03-16",
        "unknown"
    ],
    [
        "Reimagining Thermal Sensors to Save Lives",
        "DAIR Institute",
        "https://dair-institute.org/blog/reimagining-thermal-sensors-to-save-lives/",
        "2026-04-16",
        "unknown"
    ],
    [
        "Introducing Refugees, Migrants and AI",
        "DAIR Institute",
        "https://dair-institute.org/blog/introducing-refugees-migrants-and-ai/",
        "2026-05-21",
        "unknown"
    ],
    [
        "3 Takeaways: AI Sovereignty in Africa",
        "DAIR Institute",
        "https://dair-institute.org/blog/3-takeaways-ai-sovereignty-in-africa/",
        "2026-08-26",
        "unknown"
    ],
    [
        "Whose Categories? Whose AI?",
        "DAIR Institute",
        "https://dair-institute.org/blog/whose-categories-whose-ai/",
        "2026-08-26",
        "unknown"
    ],
    [
        "Blog Home",
        "DAIR Institute",
        "https://dair-institute.org/blog/",
        "unknown",
        "unknown"
    ],
    [
        "Careers",
        "DAIR Institute",
        "https://dair-institute.org/careers/",
        "unknown",
        "unknown"
    ],
    [
        "Alternative Tech Futures",
        "DAIR Institute",
        "https://dair-institute.org/categories/alternative-tech-futures/",
        "unknown",
        "unknown"
    ],
    [
        "Data for Change",
        "DAIR Institute",
        "https://dair-institute.org/categories/data-for-change/",
        "unknown",
        "unknown"
    ],
    [
        "Frameworks for AI Research & Development",
        "DAIR Institute",
        "https://dair-institute.org/categories/governance-frameworks-for-ai-systems/",
        "unknown",
        "unknown"
    ],
    [
        "The Real Harms of AI Systems",
        "DAIR Institute",
        "https://dair-institute.org/categories/the-real-harms-of-ai-systems/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Events Archive",
        "DAIR Institute",
        "https://dair-institute.org/events-archive/",
        "unknown",
        "unknown"
    ],
    [
        "Events",
        "DAIR Institute",
        "https://dair-institute.org/events/",
        "unknown",
        "unknown"
    ],
    [
        "DAIR's first anniversary",
        "DAIR Institute",
        "https://dair-institute.org/first-anniversary-event/",
        "unknown",
        "unknown"
    ],
    [
        "Imagining Possible Futures",
        "DAIR Institute",
        "https://dair-institute.org/imagining-possible-futures/",
        "unknown",
        "unknown"
    ],
    [
        "The Mystery AI Hype Theater 3000 Podcast",
        "DAIR Institute",
        "https://dair-institute.org/maiht3k/",
        "unknown",
        "unknown"
    ],
    [
        "Newsletters",
        "DAIR Institute",
        "https://dair-institute.org/news/",
        "unknown",
        "unknown"
    ],
    [
        "No Tech For Apartheid",
        "DAIR Institute",
        "https://dair-institute.org/no-tech-for-apartheid-event/",
        "unknown",
        "unknown"
    ],
    [
        "Our 2025 Annual Retreat",
        "DAIR Institute",
        "https://dair-institute.org/our-2025-annual-retreat/",
        "unknown",
        "unknown"
    ],
    [
        "Press Coverage",
        "DAIR Institute",
        "https://dair-institute.org/press-coverage/",
        "unknown",
        "unknown"
    ],
    [
        "Press Release: Announcing DAIR",
        "DAIR Institute",
        "https://dair-institute.org/press-release/",
        "unknown",
        "unknown"
    ],
    [
        "Projects",
        "DAIR Institute",
        "https://dair-institute.org/projects/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "AI-Fueled Inequities",
        "DAIR Institute",
        "https://dair-institute.org/projects/ai-fueled-inequities/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Beyond \"Fairness\" in AI",
        "DAIR Institute",
        "https://dair-institute.org/projects/beyond-fairness-in-ai/",
        "unknown",
        "unknown"
    ],
    [
        "Data Workers' Inquiry",
        "DAIR Institute",
        "https://dair-institute.org/projects/data-workers-inquiry/",
        "unknown",
        "unknown"
    ],
    [
        "Worker Surveillance and Wage Theft",
        "DAIR Institute",
        "https://dair-institute.org/projects/driven-down/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Guidelines for Documentation & Accountability",
        "DAIR Institute",
        "https://dair-institute.org/projects/guidelines-for-documentation-accountability/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Impacts of Spatial Apartheid",
        "DAIR Institute",
        "https://dair-institute.org/projects/impacts-of-spatial-apartheid/",
        "unknown",
        "unknown"
    ],
    [
        "Luddite Lab Worker Resource Hub",
        "DAIR Institute",
        "https://dair-institute.org/projects/luddite-lab/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Mystery AI Hype Theater 3000",
        "DAIR Institute",
        "https://dair-institute.org/projects/mystery-ai-hype-theater-3000/",
        "unknown",
        "unknown"
    ],
    [
        "Need-based Design of AI Systems",
        "DAIR Institute",
        "https://dair-institute.org/projects/need-based-design-of-ai-systems/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Possible Futures Blog Series",
        "DAIR Institute",
        "https://dair-institute.org/projects/possible-futures-blog-series/",
        "unknown",
        "unknown"
    ],
    [
        "Imagining Possible Futures",
        "DAIR Institute",
        "https://dair-institute.org/projects/possible-futures-workshops/",
        "unknown",
        "unknown"
    ],
    [
        "Refugees, Migrants, and AI",
        "DAIR Institute",
        "https://dair-institute.org/projects/refugees-migrants-and-ai/",
        "unknown",
        "unknown"
    ],
    [
        "Research Translation & Creative Outreach",
        "DAIR Institute",
        "https://dair-institute.org/projects/research-translation/",
        "unknown",
        "unknown"
    ],
    [
        "Social Media Harms",
        "DAIR Institute",
        "https://dair-institute.org/projects/social-media-harms/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Social Movements in Higher Education",
        "DAIR Institute",
        "https://dair-institute.org/projects/social-movements-in-higher-education/",
        "unknown",
        "unknown"
    ],
    [
        "Sovereign Language Technologies",
        "DAIR Institute",
        "https://dair-institute.org/projects/sovereign-language-technologies/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Surveillance Watch",
        "DAIR Institute",
        "https://dair-institute.org/projects/surveillance-watch/",
        "unknown",
        "unknown"
    ],
    [
        "The TESCREAL Bundle",
        "DAIR Institute",
        "https://dair-institute.org/projects/tescreal/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "The AI Con",
        "DAIR Institute",
        "https://dair-institute.org/projects/the-ai-con/",
        "unknown",
        "unknown"
    ],
    [
        "The Huniki Federation: Many Models for Many People",
        "DAIR Institute",
        "https://dair-institute.org/projects/the-huniki-federation/",
        "unknown",
        "unknown"
    ],
    [
        "Wage Theft Calculator",
        "DAIR Institute",
        "https://dair-institute.org/projects/wage-theft-calculator/",
        "unknown",
        "unknown"
    ],
    [
        "Publications",
        "DAIR Institute",
        "https://dair-institute.org/publications/",
        "unknown",
        "unknown"
    ],
    [
        "Research Philosophy",
        "DAIR Institute",
        "https://dair-institute.org/research-philosophy/",
        "unknown",
        "unknown"
    ],
    [
        "Stochastic Parrots Day",
        "DAIR Institute",
        "https://dair-institute.org/stochastic-parrots-day/",
        "unknown",
        "unknown"
    ],
    [
        "Support DAIR",
        "DAIR Institute",
        "https://dair-institute.org/support/",
        "unknown",
        "unknown"
    ],
    [
        "Africa",
        "DAIR Institute",
        "https://dair-institute.org/tags/africa/",
        "unknown",
        "unknown"
    ],
    [
        "Blog",
        "DAIR Institute",
        "https://dair-institute.org/tags/blog/",
        "unknown",
        "unknown"
    ],
    [
        "Computer Vision",
        "DAIR Institute",
        "https://dair-institute.org/tags/computer-vision/",
        "unknown",
        "unknown"
    ],
    [
        "Data Workers",
        "DAIR Institute",
        "https://dair-institute.org/tags/data-workers/",
        "unknown",
        "unknown"
    ],
    [
        "Education",
        "DAIR Institute",
        "https://dair-institute.org/tags/education/",
        "unknown",
        "unknown"
    ],
    [
        "Environment",
        "DAIR Institute",
        "https://dair-institute.org/tags/environment/",
        "unknown",
        "unknown"
    ],
    [
        "Events",
        "DAIR Institute",
        "https://dair-institute.org/tags/events/",
        "unknown",
        "unknown"
    ],
    [
        "Human Rights",
        "DAIR Institute",
        "https://dair-institute.org/tags/human-rights/",
        "unknown",
        "unknown"
    ],
    [
        "Labor",
        "DAIR Institute",
        "https://dair-institute.org/tags/labor/",
        "unknown",
        "unknown"
    ],
    [
        "Language Technology",
        "DAIR Institute",
        "https://dair-institute.org/tags/languages/",
        "unknown",
        "unknown"
    ],
    [
        "MAIHT3K",
        "DAIR Institute",
        "https://dair-institute.org/tags/maiht3k/",
        "unknown",
        "unknown"
    ],
    [
        "Media",
        "DAIR Institute",
        "https://dair-institute.org/tags/media/",
        "unknown",
        "unknown"
    ],
    [
        "News",
        "DAIR Institute",
        "https://dair-institute.org/tags/news/",
        "unknown",
        "unknown"
    ],
    [
        "Podcast",
        "DAIR Institute",
        "https://dair-institute.org/tags/podcast/",
        "unknown",
        "unknown"
    ],
    [
        "Policy",
        "DAIR Institute",
        "https://dair-institute.org/tags/policy/",
        "unknown",
        "unknown"
    ],
    [
        "Possible Futures",
        "DAIR Institute",
        "https://dair-institute.org/tags/possible-futures/",
        "unknown",
        "unknown"
    ],
    [
        "Protests",
        "DAIR Institute",
        "https://dair-institute.org/tags/protests/",
        "unknown",
        "unknown"
    ],
    [
        "Refugees & AI",
        "DAIR Institute",
        "https://dair-institute.org/tags/refugees-ai/",
        "unknown",
        "unknown"
    ],
    [
        "Research Frameworks",
        "DAIR Institute",
        "https://dair-institute.org/tags/research-frameworks/",
        "unknown",
        "unknown"
    ],
    [
        "Research",
        "DAIR Institute",
        "https://dair-institute.org/tags/research/",
        "unknown",
        "unknown"
    ],
    [
        "Resources",
        "DAIR Institute",
        "https://dair-institute.org/tags/resources/",
        "unknown",
        "unknown"
    ],
    [
        "Social Media",
        "DAIR Institute",
        "https://dair-institute.org/tags/social-media/",
        "unknown",
        "unknown"
    ],
    [
        "Surveillance",
        "DAIR Institute",
        "https://dair-institute.org/tags/surveillance/",
        "unknown",
        "unknown"
    ],
    [
        "TESCREAL",
        "DAIR Institute",
        "https://dair-institute.org/tags/tescreal/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Tools",
        "DAIR Institute",
        "https://dair-institute.org/tags/tools/",
        "unknown",
        "unknown"
    ],
    [
        "Video",
        "DAIR Institute",
        "https://dair-institute.org/tags/video/",
        "unknown",
        "unknown"
    ],
    [
        "Zines",
        "DAIR Institute",
        "https://dair-institute.org/tags/zines/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR",
        "DAIR Institute",
        "https://dair-institute.org/team/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Adio-Adet Dinika",
        "DAIR Institute",
        "https://dair-institute.org/team/adio-adet-dinika/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Adio-Adet Dinika",
        "DAIR Institute",
        "https://dair-institute.org/team/adio-adet-dinika/work/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Meet DAIR - Adrienne Williams",
        "DAIR Institute",
        "https://dair-institute.org/team/adrienne-williams/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Adrienne Williams",
        "DAIR Institute",
        "https://dair-institute.org/team/adrienne-williams/work/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Meet DAIR - Alex Hanna",
        "DAIR Institute",
        "https://dair-institute.org/team/alex-hanna/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Alex Hanna",
        "DAIR Institute",
        "https://dair-institute.org/team/alex-hanna/work/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Meet DAIR - Ash Rosas",
        "DAIR Institute",
        "https://dair-institute.org/team/ash-rosas/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Ash Rosas",
        "DAIR Institute",
        "https://dair-institute.org/team/ash-rosas/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Asmelash Teka Hadgu",
        "DAIR Institute",
        "https://dair-institute.org/team/asmelash-teka-hadgu/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Asmelash Teka Hadgu",
        "DAIR Institute",
        "https://dair-institute.org/team/asmelash-teka-hadgu/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Cail Forge",
        "DAIR Institute",
        "https://dair-institute.org/team/cail-forge/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Cail Forge",
        "DAIR Institute",
        "https://dair-institute.org/team/cail-forge/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Camilla Salim Wagner",
        "DAIR Institute",
        "https://dair-institute.org/team/camilla-salim-wagner/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Camilla Salim Wagner",
        "DAIR Institute",
        "https://dair-institute.org/team/camilla-salim-wagner/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Christie Taylor",
        "DAIR Institute",
        "https://dair-institute.org/team/christie-taylor/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Christie Taylor",
        "DAIR Institute",
        "https://dair-institute.org/team/christie-taylor/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Ciira wa Maina",
        "DAIR Institute",
        "https://dair-institute.org/team/ciira-wa-maina/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Ciira wa Maina",
        "DAIR Institute",
        "https://dair-institute.org/team/ciira-wa-maina/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Decca Muldowney",
        "DAIR Institute",
        "https://dair-institute.org/team/decca-muldowney/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Decca Muldowney",
        "DAIR Institute",
        "https://dair-institute.org/team/decca-muldowney/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Dylan Baker",
        "DAIR Institute",
        "https://dair-institute.org/team/dylan-baker/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Dylan Baker",
        "DAIR Institute",
        "https://dair-institute.org/team/dylan-baker/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Elaine O. Nsoesie",
        "DAIR Institute",
        "https://dair-institute.org/team/elaine-o-nsoesie/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Elaine O. Nsoesie",
        "DAIR Institute",
        "https://dair-institute.org/team/elaine-o-nsoesie/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Ellen Berrey",
        "DAIR Institute",
        "https://dair-institute.org/team/ellen-berrey/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Ellen Berrey",
        "DAIR Institute",
        "https://dair-institute.org/team/ellen-berrey/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Emily M. Bender",
        "DAIR Institute",
        "https://dair-institute.org/team/emily-m-bender/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Emily M. Bender",
        "DAIR Institute",
        "https://dair-institute.org/team/emily-m-bender/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Esra'a Al Shafei",
        "DAIR Institute",
        "https://dair-institute.org/team/esraa-al-shafei/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Esra'a Al Shafei",
        "DAIR Institute",
        "https://dair-institute.org/team/esraa-al-shafei/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Hannah Lipstein",
        "DAIR Institute",
        "https://dair-institute.org/team/hannah-lipstein/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Hannah Lipstein",
        "DAIR Institute",
        "https://dair-institute.org/team/hannah-lipstein/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Hellina Hailu Nigatu",
        "DAIR Institute",
        "https://dair-institute.org/team/hellina-hailu-nigatu/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Hellina Hailu Nigatu",
        "DAIR Institute",
        "https://dair-institute.org/team/hellina-hailu-nigatu/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Kathleen Siminyu",
        "DAIR Institute",
        "https://dair-institute.org/team/kathleen-siminyu/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Kathleen Siminyu",
        "DAIR Institute",
        "https://dair-institute.org/team/kathleen-siminyu/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Krystal Kauffman",
        "DAIR Institute",
        "https://dair-institute.org/team/krystal-kauffman/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Krystal Kauffman",
        "DAIR Institute",
        "https://dair-institute.org/team/krystal-kauffman/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Meron Estefanos",
        "DAIR Institute",
        "https://dair-institute.org/team/meron-estefanos/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Meron Estefanos",
        "DAIR Institute",
        "https://dair-institute.org/team/meron-estefanos/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Mike Medow",
        "DAIR Institute",
        "https://dair-institute.org/team/mike-medow/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Mike Medow",
        "DAIR Institute",
        "https://dair-institute.org/team/mike-medow/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Milagros Miceli",
        "DAIR Institute",
        "https://dair-institute.org/team/milagros-miceli/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Milagros Miceli",
        "DAIR Institute",
        "https://dair-institute.org/team/milagros-miceli/work/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Meet DAIR - Nathan Kim",
        "DAIR Institute",
        "https://dair-institute.org/team/nathan-kim/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Nathan Kim",
        "DAIR Institute",
        "https://dair-institute.org/team/nathan-kim/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Nuredin Ali",
        "DAIR Institute",
        "https://dair-institute.org/team/nuredin-ali/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Nuredin Ali",
        "DAIR Institute",
        "https://dair-institute.org/team/nuredin-ali/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Nyalleng Moorosi",
        "DAIR Institute",
        "https://dair-institute.org/team/nyalleng-moorosi/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Nyalleng Moorosi",
        "DAIR Institute",
        "https://dair-institute.org/team/nyalleng-moorosi/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Ozzy Llinas Goodman",
        "DAIR Institute",
        "https://dair-institute.org/team/ozzy-llinas-goodman/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Ozzy Llinas Goodman",
        "DAIR Institute",
        "https://dair-institute.org/team/ozzy-llinas-goodman/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Pauline Wee",
        "DAIR Institute",
        "https://dair-institute.org/team/pauline-wee/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Pauline Wee",
        "DAIR Institute",
        "https://dair-institute.org/team/pauline-wee/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Raesetje Sefala",
        "DAIR Institute",
        "https://dair-institute.org/team/raesetje-sefala/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Raesetje Sefala",
        "DAIR Institute",
        "https://dair-institute.org/team/raesetje-sefala/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - S Parker",
        "DAIR Institute",
        "https://dair-institute.org/team/s-parker/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - S Parker",
        "DAIR Institute",
        "https://dair-institute.org/team/s-parker/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Safiya Noble",
        "DAIR Institute",
        "https://dair-institute.org/team/safiya-noble/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Safiya Noble",
        "DAIR Institute",
        "https://dair-institute.org/team/safiya-noble/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Sandra Barcenas Fuerte",
        "DAIR Institute",
        "https://dair-institute.org/team/sandra-barcenas-fuerte/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Sandra Barcenas Fuerte",
        "DAIR Institute",
        "https://dair-institute.org/team/sandra-barcenas-fuerte/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Sophie Song",
        "DAIR Institute",
        "https://dair-institute.org/team/sophie-song/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Sophie Song",
        "DAIR Institute",
        "https://dair-institute.org/team/sophie-song/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Timnit Gebru",
        "DAIR Institute",
        "https://dair-institute.org/team/timnit-gebru/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Timnit Gebru",
        "DAIR Institute",
        "https://dair-institute.org/team/timnit-gebru/work/",
        "unknown",
        "creative_commons_attribution"
    ],
    [
        "Meet DAIR - Tina Park",
        "DAIR Institute",
        "https://dair-institute.org/team/tina-park/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Tina Park",
        "DAIR Institute",
        "https://dair-institute.org/team/tina-park/work/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Zeerak Talat",
        "DAIR Institute",
        "https://dair-institute.org/team/zeerak/",
        "unknown",
        "unknown"
    ],
    [
        "Meet DAIR - Zeerak Talat",
        "DAIR Institute",
        "https://dair-institute.org/team/zeerak/work/",
        "unknown",
        "unknown"
    ],
    [
        "Launching \"The AI Con\"",
        "DAIR Institute",
        "https://dair-institute.org/the-ai-con-book-launch/",
        "unknown",
        "unknown"
    ]
]


SAMPLE_URL = "https://dair-institute.org/blog/whose-categories-whose-ai/"
BODY = (
    "The harms from so-called AI are real and present. This paragraph is not catalog metadata."
)
REJECTED_URLS = [
    "http://dair-institute.org/blog/",
    "https://dair-institute.com/blog/",
    "https://dair-institute.com/publications/",
    "https://peertube.dair-institute.org/",
    "https://zines.dair-institute.org/",
    "https://cdn.sanity.io/images/example.png",
    "https://dair-community.social/",
    "https://www.linkedin.com/company/dair/",
    "https://dair-institute.org/blog/?label=research",
    "https://dair-institute.org/blog/#research",
    "https://dair-institute.org/login/",
    "https://dair-institute.org/cdn-cgi/l/email-protection/",
    "https://user:pass@dair-institute.org/blog/",
    "https://dair-institute.org:443/blog/",
    "https://dair-institute.org/paper.pdf",
    "https://dair-institute.org/blog",
    "https://127.0.0.1/blog/",
    "https://169.254.169.254/latest/meta-data/",
    "https://dair-institute.org/blog/../publications/",
]
CLOUDFLARE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing dair-institute.org. "
    "cf-mitigated: challenge challenge-platform</body></html>"
)
SITEGROUND_HTML = (
    "<html><head><meta http-equiv=\"refresh\" "
    "content=\"0;/.well-known/sgcaptcha/?r=%2Fblog%2F\"></head>"
    "<body>sg-captcha</body></html>"
)
AKAMAI_HTML = (
    "<html><head><title>Access Denied</title></head>"
    "<body>You don't have permission to access. AkamaiGHost errors.edgesuite.net</body></html>"
)
ROBOTS_404 = "<!DOCTYPE html><html><title>404: Page not found</title><p>Page not found</p></html>"
ROBOTS_ALLOW = "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n"


def _page(title: str, canonical: str, *, published: str | None = None, updated: str | None = None) -> str:
    published_tag = (
        f'<meta property="article:published_time" content="{published}">' if published else ""
    )
    updated_tag = f'<meta property="article:modified_time" content="{updated}">' if updated else ""
    return (
        "<html><head>"
        f"<title>{title} | DAIR</title>"
        f'<meta property="og:title" content="{title}">'
        '<meta property="og:site_name" content="DAIR (Distributed AI Research Institute)">'
        f"{published_tag}{updated_tag}"
        f'<link rel="canonical" href="{canonical}">'
        "</head><body>"
        f"<h1>{title}</h1>"
        f"<p>{BODY}</p>"
        "<p>By Timnit Gebru.</p>"
        "<footer>&copy; 2025. All Rights Reserved. DAIR Institute.</footer>"
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
    assert catalog_path().name == "dair_pages.json"
    assert document["runner_wired"] is False
    assert RUNNER_WIRED is False
    description = document["description"]
    assert OFFICIAL_HOST in description
    assert "bounded GET" in description
    assert "robots.txt" in description
    assert "creative_commons_attribution" in description
    assert "creative_commons" in description
    assert "runner_wired is false" in description
    assert "belief collector" in description
    assert len(description) <= 800
    raw = catalog_path().read_text(encoding="utf-8")
    assert "<html" not in raw.casefold()
    assert ".pdf" not in raw.casefold()
    assert BODY not in raw
    parsed = json.loads(raw)
    assert set(parsed) == {"catalog_id", "description", "runner_wired", "entries"}
    entries = document["entries"]
    assert [
        tuple(entry[field] for field in ("title", "publisher", "canonical_url", "date", "rights"))
        for entry in entries
    ] == [tuple(row) for row in EXPECTED]
    rights_counts = {label: 0 for label in (
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
    )}
    unknown_dates = 0
    hosts = set()
    forbidden = {"abstract", "body", "chart", "chart_data", "quote", "transcript", "page_text", "pdf"}
    for entry in entries:
        assert set(entry) == {"title", "publisher", "canonical_url", "date", "rights"}
        assert forbidden.isdisjoint(entry)
        assert entry["publisher"] == PUBLISHER
        host = entry["canonical_url"].split("/")[2]
        hosts.add(host)
        assert official_dair_host(host)
        assert host == OFFICIAL_HOST
        assert entry["date"] == UNKNOWN_DATE or re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"])
        assert entry["date"] != "2024-05-08"
        rights_counts[entry["rights"]] += 1
        if entry["date"] == UNKNOWN_DATE:
            unknown_dates += 1
    assert hosts == {OFFICIAL_HOST}
    assert len(entries) == 168
    assert rights_counts[RIGHTS_UNKNOWN] == 151
    assert rights_counts[RIGHTS_CREATIVE_COMMONS_ATTRIBUTION] == 17
    assert rights_counts[RIGHTS_CREATIVE_COMMONS] == 0
    assert unknown_dates == 141
    assert sum(rights_counts.values()) == 168
    by_url = {entry["canonical_url"]: entry for entry in entries}
    blog = by_url["https://dair-institute.org/blog/"]
    assert blog["title"] == "Blog Home"
    assert blog["date"] == UNKNOWN_DATE
    letter = by_url["https://dair-institute.org/blog/letter-statement-March2023/"]
    assert letter["date"] == "2023-03-31"
    assert letter["rights"] == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert by_url["https://dair-institute.org/publications/"]["title"] == "Publications"
    assert by_url["https://dair-institute.org/publications/"]["date"] == UNKNOWN_DATE
    assert by_url["https://dair-institute.org/research-philosophy/"]["title"] == "Research Philosophy"
    assert "www.dair-institute.org" not in {entry["canonical_url"].split("/")[2] for entry in entries}
    for entry in entries:
        assert "dair-institute.com" not in entry["canonical_url"]
        assert "www.dair-institute.org" not in entry["canonical_url"]
        assert "peertube.dair-institute.org" not in entry["canonical_url"]


def test_sole_restricted_deeds_keep_their_tokens():
    assert rights_from_page("<p>CC BY-NC</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>cc-by-nc</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>Creative Commons Attribution-NonCommercial</p>") == RIGHTS_CC_BY_NC
    assert rights_from_page("<p>CC BY-ND</p>") == RIGHTS_CC_BY_ND
    assert rights_from_page("<p>CC BY-NC-ND</p>") == RIGHTS_CC_BY_NC_ND
    assert rights_from_page("<p>CC BY-NC-SA</p>") == RIGHTS_CC_BY_NC_SA
    assert rights_from_page("<p>CC BY-NC and CC BY-ND</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>CC BY</p>") == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page("<p>CC BY</p>") != RIGHTS_CC_BY_NC
    source = Path(dair.__file__).read_text(encoding="utf-8")
    assert "(?!-)" in source


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


def test_misleading_anchors_and_non_licences_stay_unknown():
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
        "<footer>© 2025. All rights reserved. DAIR Institute.</footer>",
        "<p>This page is Public. See the terms. Hosted at dair-institute.org.</p>",
        '<a href="https://dair-institute.org/">DAIR Institute</a>',
        "<script>CC BY 4.0</script><p>All rights reserved.</p>",
        "<!-- CC BY 4.0 --><style>CC BY-SA 4.0</style><p>All rights reserved.</p>",
        "<p>Public Domain Mark</p>",
    ]
    for html in cases:
        assert rights_from_page(html) == RIGHTS_UNKNOWN, html
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by-nc/4.0/">licence</a>') == RIGHTS_CC_BY_NC
    assert rights_from_page('<a href="https://creativecommons.org/licenses/by/4.0/">licence</a>') == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION
    assert rights_from_page('<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>') == RIGHTS_CREATIVE_COMMONS
    assert rights_from_page('<link rel="license" href="https://creativecommons.org/licenses/by-nc-nd/4.0/">') == RIGHTS_CC_BY_NC_ND
    specific = '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>'
    assert rights_from_page(specific) == RIGHTS_CREATIVE_COMMONS_ATTRIBUTION


def test_software_licences_and_open_government_licence():
    assert rights_from_page("<p>MIT License</p>") == RIGHTS_MIT
    assert rights_from_page("<p>Apache License, Version 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Apache License 2.0</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>under the Apache 2.0 license</p>") == RIGHTS_APACHE
    assert rights_from_page("<p>Mozilla Public License 2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MPL-2.0</p>") == RIGHTS_MPL
    assert rights_from_page("<p>MIT License and Apache-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and MPL-2.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Apache-2.0 and CC BY-SA 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MIT License and CC BY 4.0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>MPL-2.0 and CC0.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>A collaboration with MIT and NYU.</p>") == RIGHTS_UNKNOWN
    assert rights_from_page("<p>Open Government Licence v3.0</p>") == RIGHTS_UK_OGL
    assert rights_from_page("<p>Licensed under the Open Government License v3.0.</p>") == RIGHTS_UNKNOWN
    archives = '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">terms</a>'
    assert rights_from_page(archives) == RIGHTS_UNKNOWN
    rights_field = '<meta name="dc.rights" content="This is a work of the United States Government.">'
    assert rights_from_page(rights_field) == RIGHTS_US_GOVERNMENT_WORK
    assert rights_from_page("<p>This is a work of the United States Government.</p>") == RIGHTS_UNKNOWN
    hidden = '<script type="application/ld+json">{"license":"https://creativecommons.org/licenses/by/4.0/"}</script><p>All rights reserved.</p>'
    assert rights_from_page(hidden) == RIGHTS_UNKNOWN


def test_publication_dates_ignore_updated_modified_and_copyright_years():
    stated = (
        '<time datetime="2024-05-08">March 31, 2023</time>'
        '<meta property="article:modified_time" content="2026-10-01T00:00:00Z">'
        '<meta property="og:updated_time" content="2026-11-01T00:00:00Z">'
        "<p>© 2025 DAIR Institute</p>"
    )
    assert publication_date_from_page(stated) == "2023-03-31"
    agree = '<time datetime="2026-09-28T00:00:00+09:00">September 28, 2026</time>'
    assert publication_date_from_page(agree) == "2026-09-28"
    attribute_only = '<time datetime="2024-03-21T00:00:00+09:00"></time>'
    assert publication_date_from_page(attribute_only) == "2024-03-21"
    listing = (
        '<time datetime="2026-01-01">January 1, 2026</time>'
        '<time datetime="2026-02-02">February 2, 2026</time>'
        '<meta property="article:published_time" content="2020-01-01T00:00:00Z">'
    )
    assert publication_date_from_page(listing) == UNKNOWN_DATE
    updated = "<p>Last update: May 2026.</p><p>Updated 2024-05-01</p><p>© 2020 DAIR Institute</p>"
    assert publication_date_from_page(updated) == UNKNOWN_DATE
    modified = '<meta property="article:modified_time" content="2024-04-18T14:43:38.000Z">'
    assert publication_date_from_page(modified) == UNKNOWN_DATE
    meta_only = '<meta property="article:published_time" content="2024-03-21T00:00:00+09:00">'
    assert publication_date_from_page(meta_only) == "2024-03-21"
    assert validate_date(UNKNOWN_DATE) == UNKNOWN_DATE
    assert validate_date("2024-03-21") == "2024-03-21"
    with pytest.raises(CatalogError, match="date"):
        validate_date("21 March 2024")
    with pytest.raises(CatalogError, match="date"):
        validate_date("2024-02-31")


def test_page_record_keeps_metadata_and_not_the_document_body():
    record = page_record(_page("Whose Categories? Whose AI?", SAMPLE_URL), page_url=SAMPLE_URL)
    assert record["title"] == "Whose Categories? Whose AI?"
    assert record["publisher"] == PUBLISHER
    assert record["canonical_url"] == SAMPLE_URL
    assert record["date"] == UNKNOWN_DATE
    assert record["rights"] == RIGHTS_UNKNOWN
    assert set(record) == {"title", "publisher", "canonical_url", "date", "rights"}
    stored = json.dumps(record)
    assert BODY not in stored
    assert "Timnit Gebru" not in stored
    dated = page_record(
        _page("Whose Categories? Whose AI?", SAMPLE_URL, published="2026-08-26T00:00:00Z", updated="2026-10-01T00:00:00Z"),
        page_url=SAMPLE_URL,
    )
    assert dated["date"] == "2026-08-26"
    assert "2026-10-01" not in json.dumps(dated)


def test_a_different_canonical_link_does_not_replace_the_live_url():
    html = _page("Whose Categories? Whose AI?", "https://dair-institute.com/blog/whose-categories-whose-ai/")
    record = page_record(html, page_url=SAMPLE_URL)
    assert record["canonical_url"] == SAMPLE_URL


def test_a_person_is_not_the_publisher():
    record = page_record(_page("Whose Categories? Whose AI?", SAMPLE_URL), page_url=SAMPLE_URL)
    assert record["publisher"] == PUBLISHER
    missing = "<html><head><title>A note</title></head><body><h1>A note</h1><p>By Timnit Gebru.</p></body></html>"
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
        page_html=_page("Blog Home", "https://dair-institute.org/blog/"),
        page_url="https://dair-institute.org/blog/",
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
        page_html=_page("Missing", SAMPLE_URL),
        page_url=SAMPLE_URL,
    ) is None
    assert record_from_response(
        status=200,
        content_type="application/pdf",
        page_html="%PDF-1.7 synthetic",
        page_url=SAMPLE_URL,
    ) is None
    assert confirmed_fetch_url(SAMPLE_URL, "https://dair-institute.com/blog/whose-categories-whose-ai/") is None
    assert confirmed_fetch_url("https://www.dair-institute.org/blog/", "https://dair-institute.org/blog/") is None
    assert confirmed_fetch_url("https://dair-institute.org/blog/", "https://dair-institute.org/publications/") is None
    assert confirmed_fetch_url("https://dair-institute.org/categories/", "https://dair-institute.org/") is None
    stored = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page("Whose Categories? Whose AI?", SAMPLE_URL, published="2026-08-26T00:00:00Z"),
        page_url=SAMPLE_URL,
        final_url=SAMPLE_URL,
    )
    assert stored is not None
    assert stored["canonical_url"] == SAMPLE_URL
    assert stored["date"] == "2026-08-26"
    assert BODY not in json.dumps(stored)
    stayed = record_from_response(
        status=200,
        content_type="text/html; charset=UTF-8",
        page_html=_page("Blog Home", "https://www.dair-institute.org/blog/"),
        page_url="https://www.dair-institute.org/blog/",
        final_url="https://www.dair-institute.org/blog/",
    )
    assert stayed is not None
    assert stayed["canonical_url"] == "https://www.dair-institute.org/blog/"


def test_robots_allows_public_paths_and_a_disallow_blocks_them():
    assert robots_allows(ROBOTS_404, "/blog/")
    assert robots_allows(ROBOTS_404, "/publications/")
    assert robots_allows("", "/research-philosophy/")
    assert robots_allows(ROBOTS_ALLOW, "/blog/")
    assert robots_allows(ROBOTS_ALLOW, "/publications/")
    assert robots_allows(ROBOTS_ALLOW, "/projects/data-workers-inquiry/")
    blocked = "User-agent: *\nDisallow: /\n"
    assert robots_allows(blocked, "/blog/") is False
    assert robots_allows(blocked, "/publications/") is False
    private = "User-agent: *\nDisallow: /private/\nAllow: /blog/\n"
    assert robots_allows(private, "/publications/") is True
    assert robots_allows(private, "/blog/") is True
    assert robots_allows(private, "/private/draft/") is False


def test_non_dair_urls_are_rejected():
    for rejected in REJECTED_URLS:
        with pytest.raises(CatalogError):
            validate_canonical_url(rejected)


@pytest.mark.parametrize(
    "url",
    [
        "https://dair-institute.org/",
        "https://dair-institute.org/blog/",
        "https://dair-institute.org/publications/",
        "https://dair-institute.org/projects/data-workers-inquiry/",
        "https://dair-institute.org/blog/letter-statement-March2023/",
        "https://www.dair-institute.org/blog/",
    ],
)
def test_official_dair_urls_are_accepted(url: str):
    assert validate_canonical_url(url) == url
    assert official_dair_host(url.split("/")[2])
    assert url.split("/")[2] in OFFICIAL_HOSTS


def test_validator_rejects_bad_rights_and_accepts_an_empty_list():
    document = copy.deepcopy(load_catalog())
    document["entries"] = []
    validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["rights"] = RIGHTS_APACHE
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
    document["runner_wired"] = True
    with pytest.raises(CatalogError, match="runner_wired"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"].append(dict(document["entries"][0]))
    with pytest.raises(CatalogError, match="duplicate canonical URL"):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0]["canonical_url"] = "https://dair-institute.com/blog/"
    with pytest.raises(CatalogError):
        validate_catalog(document)

    document = copy.deepcopy(load_catalog())
    document["entries"][0], document["entries"][1] = document["entries"][1], document["entries"][0]
    with pytest.raises(CatalogError, match="ordered"):
        validate_catalog(document)


def test_catalog_is_not_wired_into_belief_collection():
    module = Path(dair.__file__).read_text(encoding="utf-8")
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
    assert "dair" not in init
    collectors = (root / "pipeline" / "pdoom_pipeline" / "collectors" / "__init__.py").read_text(encoding="utf-8")
    assert collectors.strip() == '"""Package marker."""'
    assert "dair" not in collectors
    for relative in (
        "pipeline/pdoom_pipeline/belief/collect.py",
        "pipeline/pdoom_pipeline/jobs/collect_beliefs.py",
        "pipeline/pdoom_pipeline/collectors/__init__.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "dair_pages" not in text
        assert "catalogs.dair" not in text
    collect = (root / "pipeline" / "pdoom_pipeline" / "belief" / "collect.py").read_text(encoding="utf-8")
    assert "RssCollector" in collect
