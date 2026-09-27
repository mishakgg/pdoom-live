"""Deterministic statement boundary.

Numbers and dates that the source states can become explicit forecasts.
Qualitative wording stays qualitative. A bare topic word is not a signal.
Source text is never treated as an instruction.
"""

from __future__ import annotations

import re

from pdoom_pipeline.belief.taxonomy import KEY_TOPIC, QUESTION_KEYS
from pdoom_pipeline.contracts import REVIEW_STATES

EXTRACTOR_VERSION = "rule-extract-0.3.0"

PROBABILITY_CUE = re.compile(
    r"\b(chance|probability|prob\.?|odds|credence|p\s*\(\s*doom\s*\)|likelihood)\b",
    re.I,
)
PERCENT = re.compile(
    r"(?P<min>\d{1,3}(?:\.\d+)?)\s*%?\s*(?:–|-|to)\s*(?P<max>\d{1,3}(?:\.\d+)?)\s*(?:%|percent\b)|(?P<single>\d{1,3}(?:\.\d+)?)\s*(?:%|percent\b)",
    re.I,
)
ONE_IN = re.compile(r"\b(?P<num>\d{1,4})\s+in\s+(?P<den>\d{1,6})\b", re.I)
FRACTION_CHANCE = re.compile(r"~?\s*(?P<num>\d{1,2})\s*/\s*(?P<den>\d{1,2})\s+chance\b", re.I)
_YEAR = r"(?:20|21)\d{2}"
HORIZON_YEAR = re.compile(rf"\b(?:by|before)\s+(?P<year>{_YEAR})\b", re.I)
HORIZON_IN_YEAR = re.compile(rf"\b(?:around|in)\s+(?P<year>{_YEAR})\b", re.I)
HORIZON_WITHIN = re.compile(r"\bwithin\s+(?P<years>\d{1,3})\s+years\b", re.I)
YEARS_AHEAD = re.compile(
    r"(?:as little as\s+)?(?P<min>\d{1,2})\s*(?:[–\-]|to)\s*(?P<max>\d{1,2})\s+years\s+away\b"
    r"|\bwithin\s+(?P<min2>\d{1,2})\s*(?:[–\-]|to)\s*(?P<max2>\d{1,2})\s+years\b"
    r"|\bwithin\s+(?P<single>\d{1,3})\s+years\b",
    re.I,
)
CONDITION = re.compile(
    r"\b(?:if|unless|given|assuming|conditional on)\b[^.]{0,180}",
    re.I,
)
REVISION = re.compile(
    r"\b(i used to|i previously|i now think|i now believe|updated my|revised my|my current (?:view|credence|estimate))\b",
    re.I,
)
STANCE = re.compile(
    r"\b(expect|forecast|likely|unlikely|risk|will|probability|chance|i think|i believe|serious)\b",
    re.I,
)
NOT_SPEAKER = re.compile(
    r"\b(in this scenario|suppose|if you think|if,\s*say|let's say|lets say|moderator asked|people thought|"
    r"they think|ceos have said|have suggested|have all suggested|according to|out of \d+ people|"
    r"labs themselves|various ceos|i might say|would have sounded|think back to|voluntary human extinction|"
    r"dream scenario|goal to aim for|black solid line|models surpass|highly confident|sympathy for someone|"
    r"the source of|very likely to be influential|if i think i want to measure|paint companies)\b|^q\d+\b",
    re.I,
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
    "it is possible",
    "meaningful risk",
)
TOPIC_CUES = {
    "ai-catastrophe": ("extinction", "catastrophic", "disempowerment"),
    "agi-timelines": ("agi", "asi", "superintelligence"),
    "labor": ("jobs", "employment", "labor", "labour"),
    "alignment": ("alignment",),
}
TOPIC_NEAR = re.compile(
    r"\b(extinction|catastroph(?:ic|e)|disempowerment|loss of control|agi|asi|superintelligence|doom|jobs|automate|automation|unemployment)\b",
    re.I,
)


def extract_statements(text: str, *, person_id: str | None = None) -> list[dict]:
    """Return candidate statements. Source text is not interpreted as an instruction."""
    raw = (text or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    sentences = _sentences_with_spans(raw)
    statements: list[dict] = []
    for index, (sentence, start, end) in enumerate(sentences):
        context = _context(sentences, index)
        statements.extend(_explicit(sentence, person_id, start=start, end=end, context=context))
    return statements


def infer_topic_signal(text: str, *, person_id: str | None = None) -> dict | None:
    """Tag a stance-bearing passage. A lone mention of AGI or alignment is not a signal."""
    raw = text or ""
    if not STANCE.search(raw):
        return None
    lowered = raw.lower()
    topics = [topic for topic, cues in TOPIC_CUES.items() if any(re.search(rf"\b{re.escape(cue)}\b", lowered) for cue in cues)]
    if not topics:
        return None
    return {
        "statement_type": "model_inferred_signal",
        "person_id": person_id,
        "normalized_text": "Stance-bearing topic tag derived from source text. Not the speaker's probability.",
        "topics": topics,
        "topic_slug": topics[0],
        "question_key": None,
        "forecast_kind": "classification",
        "value_type": "none",
        "value_numeric": None,
        "value_min": None,
        "value_max": None,
        "value_text": None,
        "unit": None,
        "definition_text": None,
        "condition_text": None,
        "horizon_text": None,
        "evidence_text": raw[:1500],
        "context_text": None,
        "start_char": 0,
        "end_char": min(len(raw), 1500),
        "start_ms": None,
        "extractor_version": EXTRACTOR_VERSION,
        "extractor_name": "stance-topic-signal",
        "confidence": "low",
        "review_state": "unreviewed",
        "inferred": True,
    }


def revision_language(text: str) -> bool:
    return REVISION.search(text or "") is not None


def _explicit(sentence: str, person_id: str | None, *, start: int, end: int, context: str) -> list[dict]:
    if _not_speaker(sentence):
        return []
    if sentence.rstrip().endswith("?") and not re.search(r"\b(i estimate|i think there is|my credence|my p)\b", sentence, re.I):
        return []
    probabilities = _probabilities(sentence, person_id, start, end, context)
    if probabilities:
        return probabilities
    timeline = _timeline(sentence, person_id, start, end, context)
    if timeline:
        return [timeline]
    quantity = _quantity(sentence, person_id, start, end, context)
    if quantity:
        return [quantity]
    qualitative = _qualitative_statement(sentence, person_id, start, end, context)
    if qualitative:
        return [qualitative]
    return []


def _probabilities(sentence: str, person_id: str | None, start: int, end: int, context: str) -> list[dict]:
    if not PROBABILITY_CUE.search(sentence) and "p(doom)" not in sentence.lower() and not _risk_percent(sentence):
        return []
    found = []
    for match in PERCENT.finditer(sentence):
        built = _percent_statement(sentence, match, person_id, start, end, context)
        if built:
            found.append(built)
        if len(found) >= 6:
            return found
    for match in list(FRACTION_CHANCE.finditer(sentence)) + list(ONE_IN.finditer(sentence)):
        if match.re is FRACTION_CHANCE:
            built = _fraction_statement(sentence, match, person_id, start, end, context)
        else:
            built = _one_in_statement(sentence, match, person_id, start, end, context)
        if built:
            found.append(built)
        if len(found) >= 6:
            break
    return found


def _percent_statement(sentence, match, person_id, start, end, context) -> dict | None:
    if match.group("min") and match.group("max"):
        value_min = _percent(match.group("min"))
        value_max = _percent(match.group("max"))
        if value_min is None or value_max is None or value_min > value_max:
            return None
        value = None
        value_text = None
        value_type = "range"
        span = match.group(0)
    elif match.group("single"):
        value = _percent(match.group("single"))
        if value is None:
            return None
        value_min = value_max = None
        value_text = f"{_trim_number(match.group('single'))}%"
        value_type = "point"
        span = value_text
    else:
        return None
    return _probability_record(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        match_at=match.start(),
        span=span,
        value=value,
        value_min=value_min,
        value_max=value_max,
        value_text=value_text,
        value_type=value_type,
        approximate=_approximate(sentence, match.start()),
    )


def _one_in_statement(sentence, match, person_id, start, end, context) -> dict | None:
    numerator = int(match.group("num"))
    denominator = int(match.group("den"))
    if denominator <= 0 or numerator > denominator:
        return None
    return _probability_record(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        match_at=match.start(),
        span=match.group(0),
        value=numerator / denominator,
        value_min=None,
        value_max=None,
        value_text=None,
        value_type="point",
        approximate=False,
    )


def _fraction_statement(sentence, match, person_id, start, end, context) -> dict | None:
    numerator = int(match.group("num"))
    denominator = int(match.group("den"))
    if denominator <= 0 or numerator > denominator:
        return None
    return _probability_record(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        match_at=match.start(),
        span=match.group(0),
        value=numerator / denominator,
        value_min=None,
        value_max=None,
        value_text=None,
        value_type="point",
        approximate="~" in match.group(0),
    )


def _probability_record(sentence, person_id, *, start, end, context, match_at, span, value, value_min, value_max, value_text, value_type, approximate) -> dict | None:
    question_key, definition = _risk_question(sentence)
    arrival = _arrival_key(sentence)
    if question_key is None and arrival and _horizon_near(sentence, match_at):
        question_key = arrival
        definition = _arrival_definition(sentence)
    if question_key is None:
        return None
    horizon = _horizon_near(sentence, match_at) or _horizon(sentence)
    review_state = "needs_review"
    if (
        question_key != "ambiguous_doom"
        and definition
        and horizon
        and not approximate
        and "see above" not in sentence.lower()
        and not sentence.lower().startswith("additional")
        and "additional " not in sentence.lower()
    ):
        review_state = "machine_validated"
    if question_key == "ambiguous_doom" or approximate:
        review_state = "needs_review"
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_numeric",
        forecast_kind="probability",
        question_key=question_key,
        definition_text=definition,
        condition_text=_condition(sentence),
        horizon_text=horizon,
        value_type=value_type,
        value_text=value_text,
        value_numeric=value,
        value_min=value_min,
        value_max=value_max,
        unit="probability",
        review_state=review_state,
        confidence="medium" if review_state == "machine_validated" else "low",
    )


def _risk_percent(sentence: str) -> bool:
    return bool(re.search(r"\brisk\b", sentence, re.I) and PERCENT.search(sentence))


def _timeline(sentence: str, person_id: str | None, start: int, end: int, context: str) -> dict | None:
    if PERCENT.search(sentence) or ONE_IN.search(sentence) or FRACTION_CHANCE.search(sentence):
        return None
    years = YEARS_AHEAD.search(sentence)
    horizon = _horizon(sentence)
    if years and not HORIZON_YEAR.search(sentence):
        return _years_ahead(sentence, years, person_id, start, end, context)
    if not horizon or not re.search(_YEAR, horizon):
        return None
    question_key = _timeline_key(sentence)
    if not question_key:
        return None
    year = int(re.search(_YEAR, horizon).group(0))
    if re.search(rf"\bin\s+{_YEAR}\b", sentence, re.I) and not re.search(rf"\b(by|before)\s+{_YEAR}\b", sentence, re.I) and year < 2024:
        return None
    if question_key == "coding_automation" and not re.search(r"\bautomat", sentence, re.I):
        return None
    definition = _timeline_definition(sentence, question_key)
    review_state = "machine_validated" if definition and _first_person(sentence) else "needs_review"
    if not definition:
        review_state = "needs_review"
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_numeric",
        forecast_kind="timeline",
        question_key=question_key,
        definition_text=definition,
        condition_text=_condition(sentence),
        horizon_text=horizon,
        value_type="point",
        value_text=None,
        value_numeric=float(year),
        value_min=None,
        value_max=None,
        unit="year",
        review_state=review_state,
        confidence="medium" if review_state == "machine_validated" else "low",
    )


def _years_ahead(sentence, match, person_id, start, end, context) -> dict | None:
    question_key = _timeline_key(sentence) or ("capability_milestone" if re.search(r"\b(powerful ai|interpretability)\b", sentence, re.I) else None)
    if question_key is None:
        return None
    low = match.group("min") or match.group("min2")
    high = match.group("max") or match.group("max2")
    if low and high:
        value_min = float(low)
        value_max = float(high)
        value = None
        value_type = "range"
        horizon = f"{low}-{high} years ahead"
    else:
        value = float(match.group("single"))
        value_min = value_max = None
        value_type = "point"
        horizon = f"within {match.group('single')} years"
    definition = _timeline_definition(sentence, question_key) or ("powerful AI" if "powerful ai" in sentence.lower() else "interpretability" if "interpretability" in sentence.lower() else None)
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_numeric",
        forecast_kind="timeline",
        question_key=question_key,
        definition_text=definition,
        condition_text=_condition(sentence),
        horizon_text=horizon,
        value_type=value_type,
        value_text=None,
        value_numeric=value,
        value_min=value_min,
        value_max=value_max,
        unit="years_ahead",
        review_state="needs_review",
        confidence="low",
    )


def _quantity(sentence: str, person_id: str | None, start: int, end: int, context: str) -> dict | None:
    match = PERCENT.search(sentence)
    if not match or not match.group("single"):
        return None
    if PROBABILITY_CUE.search(sentence):
        return None
    if re.search(r"\b(so far|has so far|we've been seeing|we have been seeing|is below|unemployment is|puzzle|puzzles)\b", sentence, re.I):
        return None
    if not re.search(rf"\b(expect|forecast|will|would|could|i think|we'll|going to|by {_YEAR}|within \d+ years|automat\w*|displace\w*|unemployment)\b", sentence, re.I):
        return None
    value = _percent(match.group("single"))
    if value is None:
        return None
    question_key, unit, definition = _quantity_question(sentence)
    if not question_key:
        return None
    horizon = _horizon(sentence)
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_numeric",
        forecast_kind="quantity",
        question_key=question_key,
        definition_text=definition,
        condition_text=_condition(sentence),
        horizon_text=horizon,
        value_type="point",
        value_text=f"{_trim_number(match.group('single'))}%",
        value_numeric=value,
        value_min=None,
        value_max=None,
        unit=unit,
        review_state="machine_validated" if horizon and _first_person(sentence) else "needs_review",
        confidence="medium" if horizon else "low",
    )


def _qualitative_statement(sentence: str, person_id: str | None, start: int, end: int, context: str) -> dict | None:
    lowered = sentence.lower()
    if not any(phrase in lowered for phrase in QUALITATIVE):
        return None
    if PERCENT.search(sentence) or FRACTION_CHANCE.search(sentence) or (PROBABILITY_CUE.search(sentence) and ONE_IN.search(sentence)):
        return None
    if not _stance_near_topic(sentence):
        return None
    if _not_speaker(sentence):
        return None
    question_key, definition = _risk_question(sentence)
    if question_key is None:
        question_key = _timeline_key(sentence)
        definition = _timeline_definition(sentence, question_key) if question_key else None
    topic_key = question_key if question_key in QUESTION_KEYS else None
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_qualitative",
        forecast_kind="qualitative",
        question_key=topic_key,
        definition_text=definition,
        condition_text=_condition(sentence),
        horizon_text=_horizon(sentence) or _loose_horizon(sentence),
        value_type="none",
        value_text=None,
        value_numeric=None,
        value_min=None,
        value_max=None,
        unit=None,
        review_state="unreviewed",
        confidence="low",
    )


def _base(sentence: str, person_id: str | None, *, start: int, end: int, context: str, **fields) -> dict:
    if fields["review_state"] not in REVIEW_STATES or fields["review_state"] == "human_verified":
        raise ValueError(fields["review_state"])
    question_key = fields.get("question_key")
    return {
        "person_id": person_id,
        "normalized_text": " ".join(sentence.split())[:600],
        "evidence_text": sentence,
        "context_text": context[:800] if context else None,
        "start_char": start,
        "end_char": end,
        "start_ms": None,
        "extractor_version": EXTRACTOR_VERSION,
        "extractor_name": "rule-extract",
        "question_text": sentence[:600],
        "topic_slug": KEY_TOPIC.get(question_key or "", "ai-risk-qualitative"),
        **fields,
    }


def _risk_question(sentence: str) -> tuple[str | None, str | None]:
    lowered = sentence.lower()
    conditional = bool(re.search(r"\b(if|given|conditional on|assuming)\b.{0,80}\b(agi|asi|superintelligence)\b", lowered)) or bool(
        re.search(r"\bof building\b.{0,40}\b(ai|agi|asi)\b", lowered)
    )
    if re.search(r"\bextinction\b", lowered):
        key = "extinction_conditional_agi" if conditional else "extinction_unconditional"
        return key, "extinction"
    if re.search(r"\b(disempowerment|loss of control)\b", lowered):
        return "disempowerment", "disempowerment" if "disempowerment" in lowered else "loss of control"
    if re.search(r"\b(most humans die|humans die|kill everyone)\b", lowered):
        return "mass_human_death", "most humans die"
    if re.search(r"\btakeover\b", lowered):
        return "ai_takeover", "takeover"
    if re.search(r"\bcatastroph(?:ic|e)\b", lowered):
        return "catastrophe_broad", "catastrophic" if "catastrophic" in lowered else "catastrophe"
    if re.search(r"\b(irreversibly messed up|messed up our future)\b", lowered):
        return "ambiguous_doom", "irreversible future loss"
    if re.search(r"\bexistential risk\b", lowered):
        return "ambiguous_doom", "existential risk"
    if re.search(r"p\s*\(\s*doom\s*\)|\bdoom\b", lowered):
        return "ambiguous_doom", "doom"
    return None, None


def _arrival_key(sentence: str) -> str | None:
    lowered = sentence.lower()
    if re.search(r"\bhuman[-\s]level\b", lowered):
        return "human_level_ai_by_year_probability"
    if re.search(r"\btransformative\b", lowered):
        return "transformative_ai_by_year_probability"
    if re.search(r"\b(asi|superintelligence)\b", lowered):
        return "asi_by_year_probability"
    if re.search(r"\bagi\b", lowered):
        return "agi_by_year_probability"
    return None


def _arrival_definition(sentence: str) -> str | None:
    lowered = sentence.lower()
    if "human" in lowered and "level" in lowered:
        return "human-level"
    if "transformative" in lowered:
        return "transformative"
    if re.search(r"\basi\b", lowered):
        return "asi"
    if "superintelligence" in lowered:
        return "superintelligence"
    if re.search(r"\bagi\b", lowered):
        return "agi"
    return None


def _timeline_key(sentence: str) -> str | None:
    lowered = sentence.lower()
    if re.search(r"\bhuman[-\s]level\b", lowered):
        return "human_level_ai_timeline"
    if re.search(r"\btransformative\b", lowered):
        return "transformative_ai_timeline"
    if re.search(r"\b(asi|superintelligence)\b", lowered):
        return "asi_timeline"
    if re.search(r"\bagi\b", lowered):
        return "agi_timeline"
    if re.search(r"\b(cod(?:e|ing)|software engineering)\b", lowered) and re.search(r"\bautomat", lowered):
        return "coding_automation"
    if re.search(r"\b(powerful ai|interpretability)\b", lowered):
        return "capability_milestone"
    return None


def _timeline_definition(sentence: str, question_key: str | None) -> str | None:
    if not question_key:
        return None
    lowered = sentence.lower()
    if question_key in {"human_level_ai_timeline", "human_level_ai_by_year_probability"} and "human" in lowered:
        return "human-level"
    if question_key in {"transformative_ai_timeline", "transformative_ai_by_year_probability"} and "transformative" in lowered:
        return "transformative"
    if question_key in {"asi_timeline", "asi_by_year_probability"}:
        return "asi" if re.search(r"\basi\b", lowered) else "superintelligence" if "superintelligence" in lowered else None
    if question_key in {"agi_timeline", "agi_by_year_probability"} and re.search(r"\bagi\b", lowered):
        return "agi"
    if question_key == "coding_automation":
        return "coding"
    if question_key == "capability_milestone":
        if "powerful ai" in lowered:
            return "powerful AI"
        if "interpretability" in lowered:
            return "interpretability"
    return None


def _quantity_question(sentence: str) -> tuple[str | None, str | None, str | None]:
    lowered = sentence.lower()
    if re.search(r"\b(productivity|economic growth|gdp growth)\b", lowered):
        return "productivity_growth", "growth_rate", "productivity"
    if re.search(r"\b(job|jobs|employment|unemployment|workforce)\b", lowered) and re.search(r"\b(automat\w*|displace\w*|out of a job|unemploy\w*)\b", lowered):
        geo = "stated-geography" if re.search(r"\b(united states|u\.s\.|america|china|europe)\b", lowered) else "global"
        return "job_displacement", f"share_of_jobs_{geo}", "jobs"
    if re.search(r"\b(lines of code|coding|software engineering)\b", lowered) and re.search(r"\bautomat", lowered):
        return "coding_automation", "share_of_coding", "coding"
    if re.search(r"\b(compute|flops|gpus?)\b", lowered) and re.search(rf"\b(expect|will need|constraint|by {_YEAR})\b", lowered) and not re.search(r"\b(salary|salaries|grant money|more efficient)\b", lowered):
        return "compute_scaling", "stated_share", "compute"
    return None, None, None


def _not_speaker(sentence: str) -> bool:
    return NOT_SPEAKER.search(sentence or "") is not None


def _first_person(sentence: str) -> bool:
    return bool(re.search(r"\b(i expect|i think|i estimate|we'll|we will|my current|my timeline|my credence)\b", sentence, re.I))


def _approximate(sentence: str, index: int) -> bool:
    window = sentence[max(0, index - 24) : index]
    return bool(re.search(r"~|more than|at least|greater than", window, re.I))


def _condition(sentence: str) -> str | None:
    match = CONDITION.search(sentence)
    if match:
        return " ".join(match.group(0).split())[:400]
    built = re.search(r"\bof building [^.]{0,80}", sentence, re.I)
    if built:
        return " ".join(built.group(0).split())[:400]
    return None


def _percent(raw: str) -> float | None:
    number = float(raw)
    if number < 0 or number > 100:
        return None
    return number / 100.0


def _trim_number(raw: str) -> str:
    if raw.endswith(".0"):
        return raw[:-2]
    return raw


def _horizon(sentence: str) -> str | None:
    match = HORIZON_YEAR.search(sentence)
    if match:
        return f"by {match.group('year')}"
    within = HORIZON_WITHIN.search(sentence)
    if within:
        return f"within {within.group('years')} years"
    inn = HORIZON_IN_YEAR.search(sentence)
    if inn and not (int(inn.group("year")) < 2024 and re.search(rf"\bin\s+{_YEAR}\b", sentence, re.I)):
        return f"in {inn.group('year')}"
    return None


def _horizon_near(sentence: str, index: int) -> str | None:
    window = sentence[index : index + 110]
    match = HORIZON_YEAR.search(window)
    if match:
        return f"by {match.group('year')}"
    within = HORIZON_WITHIN.search(window)
    if within:
        return f"within {within.group('years')} years"
    return None


def _loose_horizon(sentence: str) -> str | None:
    match = re.search(r"\bin a few thousand days\b", sentence, re.I)
    if match:
        return "in a few thousand days"
    return None


def _stance_near_topic(sentence: str) -> bool:
    for phrase in QUALITATIVE:
        start = sentence.lower().find(phrase)
        if start < 0:
            continue
        window = sentence[max(0, start - 140) : start + len(phrase) + 140]
        if TOPIC_NEAR.search(window) or _horizon(window) or _loose_horizon(sentence):
            return True
    return False


def _sentences_with_spans(text: str) -> list[tuple[str, int, int]]:
    spans = []
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|(?=\n)|$)", text):
        sentence = " ".join(match.group(0).split())
        if sentence:
            spans.append((sentence, match.start(), match.end()))
    return spans


def _context(sentences: list[tuple[str, int, int]], index: int) -> str:
    parts = []
    if index > 0:
        parts.append(sentences[index - 1][0])
    parts.append(sentences[index][0])
    if index + 1 < len(sentences):
        parts.append(sentences[index + 1][0])
    return " ".join(parts)


def _sentences(text: str) -> list[str]:
    return [sentence for sentence, _, _ in _sentences_with_spans(text)]
