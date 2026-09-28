"""Stable question keys for forecasts that can be compared with each other.

Two records share a key only when a later statistical comparison would be meaningful.
AGI, human-level AI, and transformative AI are different keys.
"""

from __future__ import annotations

QUESTION_KEYS: dict[str, str] = {
    "extinction_unconditional": "Probability of AI-caused human extinction, not conditioned on AGI or ASI already existing.",
    "extinction_conditional_agi": "Probability of human extinction conditional on building AGI or ASI.",
    "catastrophe_broad": "Probability of a broader catastrophic AI outcome that is not specifically extinction or disempowerment.",
    "disempowerment": "Probability of permanent human disempowerment or loss of control to AI.",
    "ai_takeover": "Probability of AI takeover as the speaker worded it. Not pooled with extinction or with generic disempowerment.",
    "mass_human_death": "Probability that most humans die. Not pooled with extinction unless the speaker says extinction.",
    "ambiguous_doom": "A numeric doom, p(doom), or existential-risk figure whose definition was not one of the more specific keys.",
    "agi_timeline": "When the speaker expects AGI, using the speaker's own wording for AGI.",
    "asi_timeline": "When the speaker expects ASI or superintelligence.",
    "transformative_ai_timeline": "When the speaker expects transformative AI. This is not an AGI date.",
    "human_level_ai_timeline": "When the speaker expects human-level AI. This is not automatically AGI.",
    "agi_by_year_probability": "Probability the speaker assigns to AGI by a stated horizon. The value is a probability, not a year.",
    "asi_by_year_probability": "Probability the speaker assigns to ASI or superintelligence by a stated horizon.",
    "transformative_ai_by_year_probability": "Probability the speaker assigns to transformative AI by a stated horizon. Not an AGI probability.",
    "human_level_ai_by_year_probability": "Probability the speaker assigns to human-level AI by a stated horizon. Not an AGI probability.",
    "remote_work_automation": "When the speaker expects full automation of remote work. Not an AGI, ASI, or job-displacement date.",
    "coding_automation": "When or to what degree coding or software-engineering work is automated.",
    "job_displacement": "Share or timing of jobs displaced. Not a task share and not a wage forecast. Geography is kept when the speaker states it.",
    "task_automation": "Share of tasks automated or affected. Not a job or unemployment share.",
    "wage_effect": "A direct forecast about wages. Not a job-displacement share.",
    "productivity_growth": "Productivity, GDP, or economic-growth magnitude. Not a job-displacement share.",
    "capability_milestone": "A stated capability threshold that is not AGI, ASI, or coding automation.",
    "compute_scaling": "Compute, scaling, or energy constraint on AI progress.",
}

TOPICS: dict[str, str] = {
    "ai-extinction": "Statements about AI-caused human extinction.",
    "ai-catastrophe": "Statements about catastrophic AI outcomes other than a named extinction or disempowerment forecast.",
    "ai-disempowerment": "Statements about permanent disempowerment or loss of control.",
    "ai-takeover": "Statements that use AI takeover language rather than extinction or generic disempowerment.",
    "mass-human-death": "Statements that most humans die, kept apart from extinction.",
    "agi-timeline": "Statements about when AGI arrives.",
    "asi-timeline": "Statements about when ASI or superintelligence arrives.",
    "transformative-ai": "Statements about transformative AI timing or impact.",
    "human-level-ai": "Statements that use human-level AI rather than AGI.",
    "remote-work-automation": "Statements about when remote work would be fully automated. Not an AGI timeline.",
    "coding-automation": "Statements about automating coding or software engineering.",
    "labor": "Statements about jobs or employment.",
    "task-automation": "Statements about automating tasks, kept apart from job displacement.",
    "wages": "Statements that forecast wages.",
    "productivity": "Statements about productivity or economic growth.",
    "capability": "Statements about a capability milestone.",
    "compute": "Statements about compute, scaling, or energy.",
    "ai-risk-qualitative": "Qualitative risk language that does not supply a number.",
}

KEY_TOPIC = {
    "extinction_unconditional": "ai-extinction",
    "extinction_conditional_agi": "ai-extinction",
    "catastrophe_broad": "ai-catastrophe",
    "disempowerment": "ai-disempowerment",
    "ai_takeover": "ai-takeover",
    "mass_human_death": "mass-human-death",
    "ambiguous_doom": "ai-catastrophe",
    "agi_timeline": "agi-timeline",
    "asi_timeline": "asi-timeline",
    "transformative_ai_timeline": "transformative-ai",
    "human_level_ai_timeline": "human-level-ai",
    "agi_by_year_probability": "agi-timeline",
    "asi_by_year_probability": "asi-timeline",
    "transformative_ai_by_year_probability": "transformative-ai",
    "human_level_ai_by_year_probability": "human-level-ai",
    "remote_work_automation": "remote-work-automation",
    "coding_automation": "coding-automation",
    "job_displacement": "labor",
    "task_automation": "task-automation",
    "wage_effect": "wages",
    "productivity_growth": "productivity",
    "capability_milestone": "capability",
    "compute_scaling": "compute",
}
