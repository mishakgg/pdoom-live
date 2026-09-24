"""Rule-based statement boundary.

Numbers supplied by the source can become explicit_numeric forecasts.
Qualitative wording stays qualitative. Keyword classifiers are model_inferred_signal
records and do not invent a probability.
"""

from __future__ import annotations

import re

from pdoom_pipeline.contracts import REVIEW_STATES

EXTRACTOR_VERSION = "rule-extract-0.1.0"

PROBABILITY_CUE = re.compile(r"\b(chance|probability|prob\.?|odds|credence|p\s*\(\s*doom\s*\)|risk)\b", re.I)
PERCENT = re.compile(
    r"(?P<min>\d{1,3}(?:\.\d+)?)\s*(?:–|-|to)\s*(?P<max>\d{1,3}(?:\.\d+)?)\s*%|(?P<single>\d{1,3}(?:\.\d+)?)\s*%",
    re.I,
)
ONE_IN = re.compile(r"\b(?P<num>\d{1,4})\s+in\s+(?P<den>\d{1,6})\b", re.I)
HORIZON = re.compile(
    r"\b(?:by|before|around|in)\s+(?P<year>20\d{2})\b|\bwithin\s+(?P<years>\d{1,3})\s+years\b",
    re.I,
)
DEFINITIONS = (
    "extinction",
    "catastrophic",
    "disempowerment",
    "agi",
    "asi",
    "transformative",
)
QUALITATIVE = (
    "unlikely",
    "plausible",
    "serious risk",
    "serious concern",
    "doubtful",
    "improbable",
    "quite likely",
    "very likely",
    "a real possibility",
)
TOPIC_CUES = {
    "ai-catastrophe": ("extinction", "catastrophic", "doom", "disempowerment"),
    "agi-timelines": ("agi", "asi", "timeline"),
    "labor": ("jobs", "employment", "labor", "labour"),
    "alignment": ("alignment", "evaluation", "evaluations"),
}


def extract_statements(text: str, *, person_id: str | None = None) -> list[dict]:
    """Return candidate statements. Source text is not interpreted as an instruction."""
    sentences = _sentences(text or "")
    statements: list[dict] = []
    for sentence in sentences:
        numeric = _numeric_statement(sentence, person_id)
        if numeric:
            statements.append(numeric)
            continue
        qualitative = _qualitative_statement(sentence, person_id)
        if qualitative:
            statements.append(qualitative)
    return statements


def infer_topic_signal(text: str, *, person_id: str | None = None) -> dict | None:
    lowered = (text or "").lower()
    topics = [topic for topic, cues in TOPIC_CUES.items() if any(cue in lowered for cue in cues)]
    if not topics:
        return None
    return {
        "statement_type": "model_inferred_signal",
        "person_id": person_id,
        "normalized_text": "Keyword topic tags derived from source text.",
        "topics": topics,
        "value_numeric": None,
        "value_min": None,
        "value_max": None,
        "unit": None,
        "evidence_text": text,
        "extractor_version": EXTRACTOR_VERSION,
        "extractor_name": "keyword-topic-signal",
        "confidence": "low",
        "review_state": "unreviewed",
        "inferred": True,
    }


def _numeric_statement(sentence: str, person_id: str | None) -> dict | None:
    if not PROBABILITY_CUE.search(sentence):
        return None
    match = PERCENT.search(sentence)
    one_in = ONE_IN.search(sentence)
    if not match and not one_in:
        return None
    value = value_min = value_max = None
    if match and match.group("min") and match.group("max"):
        value_min = _percent(match.group("min"))
        value_max = _percent(match.group("max"))
        if value_min is None or value_max is None:
            return None
    elif match and match.group("single"):
        value = _percent(match.group("single"))
        if value is None:
            return None
    elif one_in:
        numerator = int(one_in.group("num"))
        denominator = int(one_in.group("den"))
        if denominator <= 0 or numerator > denominator:
            return None
        value = numerator / denominator
    horizon = _horizon(sentence)
    definitions = _definitions(sentence)
    review_state = "unreviewed" if horizon and definitions else "needs_review"
    return _base(
        sentence,
        person_id,
        statement_type="explicit_numeric",
        value_numeric=value,
        value_min=value_min,
        value_max=value_max,
        unit="probability",
        horizon_text=horizon,
        definition_text=", ".join(definitions) if definitions else None,
        review_state=review_state,
        confidence="medium" if horizon and definitions else "low",
    )


def _qualitative_statement(sentence: str, person_id: str | None) -> dict | None:
    lowered = sentence.lower()
    if not any(phrase in lowered for phrase in QUALITATIVE):
        return None
    if PERCENT.search(sentence) or (PROBABILITY_CUE.search(sentence) and ONE_IN.search(sentence)):
        return None
    return _base(
        sentence,
        person_id,
        statement_type="explicit_qualitative",
        value_numeric=None,
        value_min=None,
        value_max=None,
        unit=None,
        horizon_text=_horizon(sentence),
        definition_text=", ".join(_definitions(sentence)) or None,
        review_state="unreviewed",
        confidence="low",
    )


def _base(sentence: str, person_id: str | None, **fields) -> dict:
    if fields["review_state"] not in REVIEW_STATES:
        raise ValueError(fields["review_state"])
    start = 0
    return {
        "person_id": person_id,
        "normalized_text": " ".join(sentence.split()),
        "evidence_text": sentence,
        "start_char": start,
        "end_char": len(sentence),
        "extractor_version": EXTRACTOR_VERSION,
        "extractor_name": "rule-extract",
        "forecast_kind": "probability" if fields["statement_type"] == "explicit_numeric" else None,
        "question_text": sentence if fields["statement_type"] != "model_inferred_signal" else None,
        **fields,
    }


def _percent(raw: str) -> float | None:
    number = float(raw)
    if number < 0 or number > 100:
        return None
    return number / 100.0


def _horizon(sentence: str) -> str | None:
    match = HORIZON.search(sentence)
    if not match:
        return None
    if match.group("year"):
        return f"by {match.group('year')}"
    return f"within {match.group('years')} years"


def _definitions(sentence: str) -> list[str]:
    lowered = sentence.lower()
    return [term for term in DEFINITIONS if re.search(rf"\b{term}\b", lowered)]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]
