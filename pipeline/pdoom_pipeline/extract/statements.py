"""Deterministic statement boundary.

Numbers and dates that the source states can become explicit forecasts.
Qualitative wording stays qualitative. A bare topic word is not a signal.
Source text is never treated as an instruction.
"""

from __future__ import annotations

import re

from pdoom_pipeline.belief.taxonomy import KEY_TOPIC, QUESTION_KEYS
from pdoom_pipeline.contracts import REVIEW_STATES

EXTRACTOR_VERSION = "rule-extract-0.4.1"
SPEAKER_GAP = "<<<SPEAKER_GAP>>>"
# Statement evidence is an excerpt. A longer source page is not stored whole.
# infer_topic_signal keeps its own 1500-character cap.
EVIDENCE_EXCERPT_LIMIT = 1200
MAX_PROBABILITY_EXPRESSIONS = 6

PROBABILITY_CUE = re.compile(
    r"\b(chance|probability|prob\.?|odds|credence|p\s*\(\s*doom\s*\)|likelihood)\b",
    re.I,
)
_PERCENT_NUMBER = r"(?:\d{1,3}(?:\.\d+)?|\.\d+)"
_PERCENT_UNIT = r"(?:%|percent\b)"
_NUMBER_START = r"(?<![\w.,/+−-])"
# The unit may be "%" or the word "percent". "10 and 20 percent" is one range.
# A bare 10 is not a probability, and the word does not mean the integer 10.
PERCENT = re.compile(
    rf"{_NUMBER_START}(?P<min>{_PERCENT_NUMBER})\s*(?:{_PERCENT_UNIT})?\s*(?:–|-|to|and)\s*(?P<max>{_PERCENT_NUMBER})\s*{_PERCENT_UNIT}(?![\w%])"
    rf"|{_NUMBER_START}(?P<single>{_PERCENT_NUMBER})\s*{_PERCENT_UNIT}(?![\w%])",
    re.I,
)
# A leading-dot or zero-point decimal is already on the 0–1 scale. "0.10" is not 10%.
_DECIMAL_NUMBER = r"0?\.\d+"
DECIMAL_PROBABILITY = re.compile(
    rf"{_NUMBER_START}(?P<min>{_DECIMAL_NUMBER})(?![\w.%])\s*(?:–|-|to|and)\s*(?P<max>{_DECIMAL_NUMBER})(?![\w.%])"
    rf"|{_NUMBER_START}(?P<single>{_DECIMAL_NUMBER})(?![\w.%])"
)
ONE_IN = re.compile(rf"{_NUMBER_START}(?P<num>\d{{1,4}})\s+in\s+(?P<den>\d{{1,6}})(?![\w%]|[.,]\d)", re.I)
FRACTION_CHANCE = re.compile(rf"{_NUMBER_START}~?\s*(?P<num>\d{{1,2}})\s*/\s*(?P<den>\d{{1,2}})\s+chance\b", re.I)
_YEAR = r"(?:20|21)\d{2}"
_NUMWORD = r"(?:\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty|forty|fifty)"
WORD_VALUE = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
}
HORIZON_YEAR = re.compile(rf"\b(?P<prep>by|before)\s+(?P<year>{_YEAR})\b", re.I)
HORIZON_IN_YEAR = re.compile(rf"\b(?:around|in)\s+(?P<year>{_YEAR})\b", re.I)
HORIZON_WITHIN = re.compile(rf"\bwithin\s+(?P<years>{_NUMWORD})\s+years\b", re.I)
YEARS_AHEAD = re.compile(
    rf"(?:as little as\s+)?(?P<min>{_NUMWORD})\s*(?:[–\-]|to)\s*(?P<max>{_NUMWORD})\s+years\s+away\b"
    rf"|\bwithin\s+(?P<min2>{_NUMWORD})\s*(?:[–\-]|to)\s*(?P<max2>{_NUMWORD})\s+years\b"
    rf"|\bwithin\s+(?P<single>{_NUMWORD})\s+years\b"
    rf"|\b(?P<min3>{_NUMWORD})\s*(?:[–\-]|to)\s*(?P<max3>{_NUMWORD})\s+years\b",
    re.I,
)
YEAR_SPAN = re.compile(rf"\b(?:between\s+)?(?P<start>{_YEAR})\s*(?:[–\-]|to|and)\s*(?P<end>{_YEAR})\b", re.I)
DECADE = re.compile(rf"\b(?:(?P<part>early|mid|late)\s+)?(?P<decade>(?:20|21)\d0)s\b", re.I)
THIS_DECADE = re.compile(r"\bthis decade\b", re.I)
NEXT_DECADE = re.compile(r"\b(?:(?:over|in|within)\s+)?the next decade\b", re.I)
LIST_CONTINUATION = re.compile(
    r"^(?:[*\-]\s*)?(?:roughly\s+)?~?(?P<num>\d{1,3}(?:\.\d+)?)%\s+probability\s+by\s+(?P<year>(?:20|21)\d{2})\b",
    re.I,
)
PRIOR_PROBABILITY = re.compile(
    r"\bprobability of\s+(?P<what>transformative ai|human extinction|extinction|superintelligence|agi|asi)\b",
    re.I,
)
MEDIAN_YEARS = re.compile(
    r"\bmy own median timelines of\s+~?\s*(?P<years>\d{1,3})\s+years\s+until\b"
    r"|\b(?P<years2>\d{1,3})\s+years as a median estimate\b",
    re.I,
)
ANAPHORA = re.compile(r"^(?:by that i mean|that means|i mean|which means|in other words|that is,)\b", re.I)
SPEAKER_LABEL = re.compile(r"^[A-Z][A-Za-z .'\-]{0,60}:\s")
CONDITION = re.compile(
    r"\b(?:if|unless|given|assuming|conditional on)\b[^.]{0,180}",
    re.I,
)
REVISION = re.compile(
    r"\b(i used to|i previously|previously, my|i now think|i now believe|i now expect|updated my|revised my|"
    r"my current (?:view|credence|estimate)|my (?:personal )?timelines have)\b",
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
    r"the source of|very likely to be influential|if i think i want to measure|paint companies|"
    r"some people interpreted|even before ai|nuclear war|offhandedly mentioned|the precipice gives|"
    r"don't want to set it|in our scenario|we could live in a world|expert survey|if you say what's the chance|"
    r"holden wrote|holden felt|none of them really had|deploying ai systems only when|"
    r"hypothetically|in a hypothetical|imagine that|what if|"
    r"ignore (?:your|previous|all|these) instructions|disregard (?:your|previous|all) instructions)\b|^q\d+\b",
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
    statements: list[dict] = []
    cursor = 0
    for part in raw.split(SPEAKER_GAP):
        statements.extend(_extract_part(part, person_id, cursor))
        cursor += len(part) + len(SPEAKER_GAP)
    for statement in statements:
        statement["review_flags"] = _review_flags(statement)
        _cap_evidence_text(statement)
    return statements


def _cap_evidence_text(statement: dict) -> None:
    evidence = statement.get("evidence_text") or ""
    if len(evidence) > EVIDENCE_EXCERPT_LIMIT:
        statement["evidence_text"] = evidence[:EVIDENCE_EXCERPT_LIMIT]


def _extract_part(text: str, person_id: str | None, offset: int) -> list[dict]:
    sentences = _sentences_with_spans(text)
    if offset:
        sentences = [(sentence, start + offset, end + offset) for sentence, start, end in sentences]
    statements: list[dict] = []
    covered: set[int] = set()
    for index, (sentence, start, end) in enumerate(sentences):
        context = _context(sentences, index)
        found = _explicit(sentence, person_id, start=start, end=end, context=context)
        if not found:
            continue
        covered.add(index)
        for row in found:
            row["sentence_index"] = index
        statements.extend(found)
    _attach_neighbor_horizon(sentences, statements)
    statements.extend(_anaphora_windows(sentences, covered, person_id))
    statements.extend(_list_continuations(sentences, covered, person_id))
    statements.extend(_for_that_answers(sentences, covered, person_id))
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
    if _not_speaker(sentence) or _attributes_to_someone_else(sentence) or _negated_claim(sentence) or _quoted_third_party(sentence):
        return []
    if sentence.rstrip().endswith("?") and not re.search(r"\b(i estimate|i think there is|my credence|my p)\b", sentence, re.I):
        return []
    probabilities = _probabilities(sentence, person_id, start, end, context)
    if probabilities:
        return probabilities
    if _probability_context(sentence) and re.search(r"\d", sentence):
        # Failed probability parsing is abstention, not an arrival-year forecast
        # inferred from a remaining year in the same sentence.
        return []
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
    if not _probability_context(sentence) or _ambiguous_probability_outcome(sentence):
        return []
    matches = []
    occupied: list[tuple[int, int]] = []
    for pattern in (PERCENT, DECIMAL_PROBABILITY, FRACTION_CHANCE, ONE_IN):
        for match in pattern.finditer(sentence):
            if _span_overlaps(match.start(), match.end(), occupied):
                continue
            occupied.append((match.start(), match.end()))
            matches.append(match)
            if len(matches) > MAX_PROBABILITY_EXPRESSIONS:
                # Do not collect unbounded match lists or publish only a prefix
                # of a dense numeric passage whose binding is unsupported.
                return []
    matches.sort(key=lambda match: match.start())
    if matches and not _same_outcome_continuations(sentence, matches):
        return []
    found = []
    for match in matches:
        if _unsupported_probability_prefix(sentence, match.start()):
            continue
        if match.re not in (PERCENT, DECIMAL_PROBABILITY) or match.group("single"):
            if _dangling_range_endpoint(sentence, match.start()) or _dangling_range_start(sentence, match.end()):
                continue
        if match.re is PERCENT:
            built = _percent_statement(sentence, match, person_id, start, end, context)
        elif match.re is DECIMAL_PROBABILITY:
            built = _decimal_statement(sentence, match, person_id, start, end, context)
        elif match.re is FRACTION_CHANCE:
            built = _fraction_statement(sentence, match, person_id, start, end, context)
        else:
            built = _one_in_statement(sentence, match, person_id, start, end, context)
        if built:
            found.append(built)
        if len(found) >= MAX_PROBABILITY_EXPRESSIONS:
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
        value_text = match.group(0).strip()
        # Canonical value_text accepts 0.5%, not .5%; evidence retains the exact
        # source spelling and character offsets rather than adding a source zero.
        if value_text.startswith("."):
            value_text = "0" + value_text
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


def _decimal_statement(sentence, match, person_id, start, end, context) -> dict | None:
    """A decimal already on the 0–1 scale. The source spelling stays in value_text."""
    if match.group("min") and match.group("max"):
        value_min = _unit_interval(match.group("min"))
        value_max = _unit_interval(match.group("max"))
        if value_min is None or value_max is None or value_min > value_max:
            return None
        value = None
        value_text = None
        value_type = "range"
        span = match.group(0)
    elif match.group("single"):
        value = _unit_interval(match.group("single"))
        if value is None:
            return None
        value_min = value_max = None
        value_text = match.group("single")
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
    outcome_text = _probability_outcome_text(sentence)
    question_key, definition = _risk_question(outcome_text)
    if question_key == "extinction_unconditional" and _risk_question(sentence)[0] == "extinction_conditional_agi":
        question_key = "extinction_conditional_agi"
    arrival = _arrival_key(outcome_text)
    if question_key is None and arrival and _horizon_near(sentence, match_at):
        question_key = arrival
        definition = _arrival_definition(outcome_text)
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
    return bool(re.search(r"\brisk\b", sentence, re.I) and re.search(r"%|\bpercent\b", sentence, re.I))


def _probability_context(sentence: str) -> bool:
    return bool(PROBABILITY_CUE.search(sentence) or "p(doom)" in sentence.lower() or _risk_percent(sentence))


def _signed_token(sentence: str, start: int) -> bool:
    prefix = sentence[:start]
    return prefix.rstrip().endswith(("-", "−", "+")) or bool(re.search(r"\b(?:plus|minus|negative|positive)\s*$", prefix, re.I))


def _unsupported_probability_prefix(sentence: str, start: int) -> bool:
    # Also used by adjacent-sentence extraction, which must not salvage a signed
    # or grouped token that the single-sentence probability path rejected.
    return _signed_token(sentence, start) or bool(re.search(r"\d[\s']+$", sentence[:start]))


def _dangling_range_endpoint(sentence: str, start: int) -> bool:
    prefix = sentence[:start]
    earlier = re.search(r"(?P<value>[\d.,]+)\s*(?:to|and|[–-])\s*$", prefix, re.I)
    if not earlier:
        return False
    # A year that cannot be a percent may precede an independent next estimate.
    return not (
        re.fullmatch(_YEAR, earlier.group("value"))
        and re.search(r"\b(?:by|before|in|around)\s*$", prefix[:earlier.start()], re.I)
        and re.search(r"\band\s*$", prefix, re.I)
    )


def _dangling_range_start(sentence: str, end: int) -> bool:
    # A valid-looking left point must not survive when the range parser cannot
    # consume the right endpoint (signed, grouped, out of range, or wrong scale).
    return bool(re.match(r"\s*(?:to|and|[–-])\s*[+−-]?\s*(?:\d|\.\d)", sentence[end:], re.I))


def _probability_outcome_text(sentence: str) -> str:
    # Named entities in an explicit condition are not a second forecast outcome.
    # Keep the original sentence for evidence, condition and horizon extraction.
    text = re.sub(r"\b(?:if|unless|given|assuming|conditional on)\b[^,;.!?]{0,180}", " ", sentence, flags=re.I)
    # A named cause (AGI, or a takeover causing deaths) is not a second event
    # probability. The cause remains verbatim in evidence and question text.
    text = re.sub(r"\b(?:from|caused by|due to|because of|of building)\s+(?:(?:an?|the|advanced|powerful|ai)\s+)*(?:agi|asi|superintelligence|takeover|catastrophe)\b", " ", text, flags=re.I)
    text = re.sub(r"\b(?:agi|asi|superintelligence)(?=-caused\b|\s+(?:will|could|would|may)\s+(?:cause|lead to|result in)\b)", " ", text, flags=re.I)
    return text


def _ambiguous_probability_outcome(sentence: str) -> bool:
    text = _probability_outcome_text(sentence)
    if re.search(r"\b(?:no|not|never|without|avoid\w*|prevent\w*|avert\w*|escape\w*|absence|unlike|versus)\b|n't\b|\bfail\w*\s+to\b|\b(?:rather than|instead of|compared with|compared to)\b", text, re.I):
        return True
    families = (
        r"\bextinction\b",
        r"\bcatastroph(?:ic|e)\b",
        r"\bdisempower(?:ed|ment)\b|\bloss of control\b",
        r"\b(?:most humans die|humans die|kill everyone)\b",
        r"\btakeover\b",
        r"\bhuman[-\s]level\b",
        r"\btransformative\b",
        r"\b(?:asi|superintelligence)\b",
        r"\bagi\b|\bartificial general intelligence\b",
        r"\b(?:jobs?|workers?|employment|unemployment)\b",
        r"\b(?:tasks?|coding|software engineering)\b",
        r"\b(?:productivity|gdp|wages?|economic growth)\b",
    )
    outcomes = sum(bool(re.search(pattern, text, re.I)) for pattern in families)
    return outcomes > 1


def _same_outcome_continuations(sentence: str, matches: list[re.Match]) -> bool:
    """Every numeric clause must name the event or use a bounded continuation.

    Check the prefix before the first number even for a single expression.
    Unknown nouns (rain, a benchmark score, etc.) must not borrow an extinction
    or arrival question from another clause in the sentence.
    """
    continuation_words = {
        "a", "an", "the", "and", "or", "but", "of", "for", "that", "this", "it",
        "chance", "probability", "credence", "likelihood", "odds", "percent",
        "i", "we", "my", "we'll", "i'll", "will", "would", "could", "may", "might",
        "estimate", "assign", "expect", "think", "believe", "see", "happen", "occur", "arrive",
        "there", "give", "put", "risk", "personal", "currently",
        "between", "greater", "lower", "upper", "high", "low", "disturbingly",
        "live", "human", "species", "permanently", "involuntarily",
        "by", "before", "within", "in", "at", "end", "over", "next", "year", "years",
        "decade", "decades", "century", "centuries", "roughly", "about", "around",
        "more", "less", "than", "least", "most", "is", "to",
        "above", "from", "now", "posting", "report",
    }
    prefix = _probability_outcome_text(sentence[:matches[0].start()])
    introductions = list(re.finditer(r"\b(?:chance|probability|credence|likelihood|odds|risk)\b", prefix, re.I))
    regions = []
    if introductions:
        # Inspect the event phrase after the latest probability introducer. A
        # harmless preamble before it need not belong to the continuation grammar.
        regions.append(prefix[introductions[-1].start():])
    else:
        stop = matches[1].start() if len(matches) > 1 else len(sentence)
        following = re.split(r"[;,]|\b(?:and|or|but)\b", sentence[matches[0].end():stop], flags=re.I)[0]
        explicitly_bound_after = _probability_context(following) and (_risk_question(following)[0] or _arrival_key(following))
        if not explicitly_bound_after:
            regions.append(prefix)
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(sentence)
        regions.append(sentence[match.end():stop])
    for region in regions:
        tail = _probability_outcome_text(region)
        # Preserve the existing attributed-byline form without treating the
        # speaker's name as an unsupported event noun.
        tail = re.sub(r"^[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){1,3}\s+(?:writes|wrote)\s+that\s+", "", tail)
        for clause in re.split(r"[;,]|\b(?:and|or|but)\b", tail, flags=re.I):
            if _risk_question(clause)[0] or _arrival_key(clause):
                continue
            if set(re.findall(r"[a-z]+(?:'[a-z]+)?", clause.lower())) - continuation_words:
                return False
    return True


def _timeline(sentence: str, person_id: str | None, start: int, end: int, context: str) -> dict | None:
    if PERCENT.search(sentence) or ONE_IN.search(sentence) or FRACTION_CHANCE.search(sentence):
        return None
    decade = _decade(sentence, person_id, start, end, context)
    if decade:
        return decade
    span = _year_span(sentence, person_id, start, end, context)
    if span:
        return span
    median = _median_years(sentence, person_id, start, end, context)
    if median:
        return median
    years = _forward_years(sentence)
    horizon = _horizon(sentence)
    if years and not HORIZON_YEAR.search(sentence):
        if _past_time(sentence) and not years.group("single") and not years.group("min"):
            return None
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
    if _past_time(sentence):
        return None
    question_key = _timeline_key(sentence) or ("capability_milestone" if re.search(r"\b(powerful ai|interpretability)\b", sentence, re.I) else None)
    if question_key is None:
        return None
    low = match.group("min") or match.group("min2") or match.group("min3")
    high = match.group("max") or match.group("max2") or match.group("max3")
    if low and high:
        value_min = float(_num_value(low))
        value_max = float(_num_value(high))
        value = None
        value_type = "range"
        horizon = match.group(0).strip()
    else:
        value = float(_num_value(match.group("single")))
        value_min = value_max = None
        value_type = "point"
        horizon = match.group(0).strip()
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
    if not re.search(rf"\b(expect|forecast|will|would|could|i think|we'll|going to|by {_YEAR}|within \d+ years|automat\w*|displace\w*|affect\w*|unemployment)\b", sentence, re.I):
        return None
    value = _percent(match.group("single"))
    if value is None:
        return None
    question_key, unit, definition = _quantity_question(sentence)
    if not question_key:
        return None
    horizon = _horizon(sentence)
    approximate = _approximate(sentence, match.start())
    review_state = "needs_review" if approximate or not horizon or not _first_person(sentence) else "machine_validated"
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
        review_state=review_state,
        confidence="medium" if review_state == "machine_validated" else "low",
    )


def _qualitative_statement(sentence: str, person_id: str | None, start: int, end: int, context: str) -> dict | None:
    lowered = sentence.lower()
    if not any(phrase in lowered for phrase in QUALITATIVE):
        return None
    if PERCENT.search(sentence) or FRACTION_CHANCE.search(sentence) or (PROBABILITY_CUE.search(sentence) and ONE_IN.search(sentence)):
        return None
    if not _stance_near_topic(sentence):
        return None
    if _not_speaker(sentence) or _attributes_to_someone_else(sentence):
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
    target_start, target_end = _target_dates(fields.get("horizon_text"))
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
        "target_date_start": target_start,
        "target_date_end": target_end,
        "resolution_criteria": None,
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
    if re.search(r"\bdisempowered\b", lowered):
        return "disempowerment", "disempowered"
    if re.search(r"\bdisempowerment\b", lowered):
        return "disempowerment", "disempowerment"
    if re.search(r"\bloss of control\b", lowered):
        return "disempowerment", "loss of control"
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
    if re.search(r"\bfull automation of remote work\b", lowered) or (
        re.search(r"\bremote work\b", lowered) and re.search(r"\bautomat", lowered)
    ):
        return "remote_work_automation"
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
    if question_key == "remote_work_automation":
        if "full automation of remote work" in lowered:
            return "full automation of remote work"
        return "remote work automation"
    if question_key == "capability_milestone":
        if "powerful ai" in lowered:
            return "powerful AI"
        if "interpretability" in lowered:
            return "interpretability"
    return None


def _quantity_question(sentence: str) -> tuple[str | None, str | None, str | None]:
    lowered = sentence.lower()
    geography = _geography_phrase(sentence)
    if re.search(r"\b(productivity|economic growth|gdp growth)\b", lowered):
        definition = "productivity" if "productivity" in lowered or "economic growth" in lowered else "gdp growth"
        if geography:
            definition = f"{definition} in {geography}"
        return "productivity_growth", "growth_rate", definition
    if re.search(r"\bwages?\b", lowered) and re.search(r"\b(grow\w*|fall|rise|risen|decline|increase|decrease|stagnat\w*)\b", lowered):
        definition = f"wages in {geography}" if geography else "wages"
        return "wage_effect", "wage_change_rate", definition
    activities = bool(re.search(r"\bwhat humans do\b", lowered))
    if (re.search(r"\btasks?\b", lowered) or activities) and re.search(r"\b(automat\w*|affect\w*|replac\w*)\b", lowered) and not re.search(r"\b(unemployment|jobs?|employment|workforce)\b", lowered):
        geo = "stated-geography" if geography else "global"
        if activities and not re.search(r"\btasks?\b", lowered):
            definition = f"what humans do in {geography}" if geography else "what humans do"
        else:
            definition = f"tasks in {geography}" if geography else "tasks"
        return "task_automation", f"share_of_tasks_{geo}", definition
    if re.search(r"\b(job|jobs|employment|unemployment|workforce|workers)\b", lowered) and re.search(r"\b(automat\w*|displace\w*|replac\w*|out of a job|unemploy\w*)\b", lowered):
        geo = "stated-geography" if geography else "global"
        if "unemployment" in lowered:
            kind = "unemployment"
        elif re.search(r"\bworkers\b", lowered) and not re.search(r"\bjobs?\b", lowered):
            kind = "workers"
        else:
            kind = "jobs"
        definition = f"{kind} in {geography}" if geography else kind
        return "job_displacement", f"share_of_jobs_{geo}", definition
    if re.search(r"\b(lines of code|coding|software engineering)\b", lowered) and re.search(r"\bautomat", lowered):
        return "coding_automation", "share_of_coding", "coding"
    if re.search(r"\b(compute|flops|gpus?)\b", lowered) and re.search(rf"\b(expect|will need|constraint|by {_YEAR})\b", lowered) and not re.search(r"\b(salary|salaries|grant money|more efficient)\b", lowered):
        return "compute_scaling", "stated_share", "compute"
    return None, None, None


def _forward_years(sentence: str):
    """A relative horizon. '50-100 years of progress' is a duration, not a forecast date."""
    for match in YEARS_AHEAD.finditer(sentence or ""):
        if re.match(r"\s+of\b", sentence[match.end() :], re.I):
            continue
        return match
    return None


def _median_years(sentence, person_id, start, end, context) -> dict | None:
    """A first-person median stated in years. Another person's number is not used."""
    if _past_time(sentence):
        return None
    match = MEDIAN_YEARS.search(sentence)
    if not match:
        return None
    if not re.search(r"\bremote work\b", sentence, re.I) or not re.search(r"\bautomat", sentence, re.I):
        return None
    years = match.group("years") or match.group("years2")
    if "full automation of remote work" in sentence.lower():
        definition = "full automation of remote work"
    else:
        definition = "remote work automation"
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_numeric",
        forecast_kind="timeline",
        question_key="remote_work_automation",
        definition_text=definition,
        condition_text=_condition(sentence),
        horizon_text=" ".join(match.group(0).split()),
        value_type="point",
        value_text=None,
        value_numeric=float(years),
        value_min=None,
        value_max=None,
        unit="years_ahead",
        review_state="needs_review",
        confidence="low",
    )


def _decade(sentence, person_id, start, end, context) -> dict | None:
    if _past_time(sentence):
        return None
    question_key = _timeline_key(sentence)
    if not question_key:
        return None
    if THIS_DECADE.search(sentence) and not DECADE.search(sentence):
        return _base(
            sentence,
            person_id,
            start=start,
            end=end,
            context=context,
            statement_type="explicit_qualitative",
            forecast_kind="timeline",
            question_key=question_key,
            definition_text=_timeline_definition(sentence, question_key),
            condition_text=_condition(sentence),
            horizon_text="this decade",
            value_type="none",
            value_text=None,
            value_numeric=None,
            value_min=None,
            value_max=None,
            unit=None,
            review_state="needs_review",
            confidence="low",
        )
    match = DECADE.search(sentence)
    if not match or int(match.group("decade")) < 2020:
        return None
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_numeric",
        forecast_kind="timeline",
        question_key=question_key,
        definition_text=_timeline_definition(sentence, question_key),
        condition_text=_condition(sentence),
        horizon_text=" ".join(match.group(0).split()),
        value_type="point",
        value_text=None,
        value_numeric=float(match.group("decade")),
        value_min=None,
        value_max=None,
        unit="decade",
        review_state="needs_review",
        confidence="low",
    )


def _year_span(sentence, person_id, start, end, context) -> dict | None:
    match = YEAR_SPAN.search(sentence)
    if not match or _past_time(sentence):
        return None
    start_year = int(match.group("start"))
    end_year = int(match.group("end"))
    if end_year <= start_year or end_year < 2024:
        return None
    if not re.search(r"\b(between|expect|forecast|will|i think|timeline|arrive|arrival)\b", sentence, re.I):
        return None
    question_key = _timeline_key(sentence)
    if not question_key:
        return None
    return _base(
        sentence,
        person_id,
        start=start,
        end=end,
        context=context,
        statement_type="explicit_numeric",
        forecast_kind="timeline",
        question_key=question_key,
        definition_text=_timeline_definition(sentence, question_key),
        condition_text=_condition(sentence),
        horizon_text=" ".join(match.group(0).split()),
        value_type="range",
        value_text=None,
        value_numeric=None,
        value_min=float(start_year),
        value_max=float(end_year),
        unit="year",
        review_state="needs_review",
        confidence="low",
    )


def _past_time(sentence: str) -> bool:
    return bool(re.search(r"\b(ago|last year|last decade|in the past|in the last|years ago)\b", sentence, re.I))


def _num_value(token: str) -> int:
    if token.isdigit():
        return int(token)
    return WORD_VALUE[token.lower()]


def _geography_phrase(lowered: str) -> str | None:
    match = re.search(r"\b(united states|the us|u\.s\.|america|china|europe)\b", lowered, re.I)
    if not match:
        return None
    return match.group(0)


def _speaker_label(sentence: str) -> bool:
    return SPEAKER_LABEL.match(sentence or "") is not None


def _competing_percent(left: str, right: str) -> bool:
    def values(text: str) -> set[float]:
        found = set()
        for match in PERCENT.finditer(text):
            if match.group("single"):
                value = _percent(match.group("single"))
                if value is not None:
                    found.add(round(value, 4))
        return found

    left_values = values(left)
    right_values = values(right)
    return bool(left_values and right_values and left_values != right_values)


def _has_bare_probability(sentence: str) -> bool:
    if _not_speaker(sentence) or _speaker_label(sentence):
        return False
    if not (PROBABILITY_CUE.search(sentence) or _risk_percent(sentence)):
        return False
    if not PERCENT.search(sentence) and not ONE_IN.search(sentence) and not FRACTION_CHANCE.search(sentence):
        return False
    if _risk_question(sentence)[0] or _arrival_key(sentence):
        return False
    return True


def _attach_neighbor_horizon(sentences: list[tuple[str, int, int]], statements: list[dict]) -> None:
    for statement in statements:
        if statement.get("horizon_text") or statement.get("forecast_kind") not in {"probability", "timeline", "quantity"}:
            continue
        index = statement.get("sentence_index")
        if index is None or index < 1:
            continue
        previous, start, _end = sentences[index - 1]
        if _not_speaker(previous) or _speaker_label(previous) or previous.rstrip().endswith("?"):
            continue
        if _competing_percent(statement.get("evidence_text") or "", previous):
            continue
        horizon = _horizon(previous)
        if not horizon:
            continue
        if not re.match(r"^(within|if|by|before|assuming|given|unless)\b", previous, re.I):
            continue
        other_key = _risk_question(previous)[0]
        if other_key and other_key != statement.get("question_key"):
            continue
        combined = f"{previous} {statement['evidence_text']}"
        statement["evidence_text"] = combined
        statement["normalized_text"] = " ".join(combined.split())[:600]
        statement["question_text"] = combined[:600]
        statement["start_char"] = start
        statement["horizon_text"] = horizon
        if not statement.get("condition_text"):
            statement["condition_text"] = _condition(previous)
        statement["review_state"] = "needs_review"
        statement["confidence"] = "low"
        statement.setdefault("review_flags", []).append("multi_sentence_evidence")


def _anaphora_windows(sentences: list[tuple[str, int, int]], covered: set[int], person_id: str | None) -> list[dict]:
    found = []
    for index, (sentence, start, end) in enumerate(sentences):
        if index in covered or index + 1 >= len(sentences) or not _has_bare_probability(sentence):
            continue
        nxt, _nstart, nend = sentences[index + 1]
        if _not_speaker(nxt) or _speaker_label(nxt) or nxt.rstrip().endswith("?") or not ANAPHORA.match(nxt):
            continue
        if _competing_percent(sentence, nxt):
            continue
        if not (_risk_question(nxt)[0] or _arrival_key(nxt) or _timeline_key(nxt)):
            continue
        combined = f"{sentence} {nxt}"
        rows = _probabilities(combined, person_id, start, nend, combined)
        for row in rows:
            definition = (row.get("definition_text") or "").lower()
            if definition and definition not in nxt.lower():
                continue
            if row.get("value_text") and not _probability_spelling_in_source(row["value_text"], sentence):
                continue
            row["evidence_text"] = combined
            row["normalized_text"] = " ".join(combined.split())[:600]
            row["question_text"] = combined[:600]
            row["start_char"] = start
            row["end_char"] = nend
            row["context_text"] = combined[:800]
            row["review_state"] = "needs_review"
            row["confidence"] = "low"
            row["sentence_index"] = index
            row.setdefault("review_flags", []).append("multi_sentence_evidence")
            found.append(row)
            break
    return found


def _for_that_answers(sentences: list[tuple[str, int, int]], covered: set[int], person_id: str | None) -> list[dict]:
    """An answer of the form 'I'll give a probability of N% for that' uses the previous sentence's outcome."""
    found = []
    for index, (sentence, start, end) in enumerate(sentences):
        if index in covered or index < 1:
            continue
        if not re.search(r"\bi'll give a probability of\b", sentence, re.I) or not re.search(r"\bfor that\b", sentence, re.I):
            continue
        if _attributes_to_someone_else(sentence) or _not_speaker(sentence):
            continue
        match = PERCENT.search(sentence)
        if not match or not match.group("single"):
            continue
        if _unsupported_probability_prefix(sentence, match.start()) or _dangling_range_endpoint(sentence, match.start()) or _dangling_range_start(sentence, match.end()):
            continue
        if len(list(PERCENT.finditer(sentence))) != 1:
            continue
        if not _same_outcome_continuations(sentence, [match]):
            continue
        previous, prev_start, _prev_end = sentences[index - 1]
        question_key, definition = _risk_question(previous)
        if not question_key or not definition or definition.lower() not in previous.lower():
            continue
        if _risk_question(sentence)[0] and _risk_question(sentence)[0] != question_key:
            continue
        value = _percent(match.group("single"))
        if value is None:
            continue
        value_text = f"{_trim_number(match.group('single'))}%"
        if value_text not in sentence:
            continue
        if value_text.startswith("."):
            value_text = "0" + value_text
        combined = f"{previous} {sentence}"
        if _ambiguous_probability_outcome(combined):
            continue
        row = _base(
            sentence,
            person_id,
            start=prev_start,
            end=end,
            context=combined,
            statement_type="explicit_numeric",
            forecast_kind="probability",
            question_key=question_key,
            definition_text=definition,
            condition_text=_condition(previous),
            horizon_text=_horizon(sentence) or _horizon(previous),
            value_type="point",
            value_text=value_text,
            value_numeric=value,
            value_min=None,
            value_max=None,
            unit="probability",
            review_state="needs_review",
            confidence="low",
        )
        row["evidence_text"] = combined
        row["normalized_text"] = " ".join(combined.split())[:600]
        row["question_text"] = combined[:600]
        row["context_text"] = combined[:800]
        row["sentence_index"] = index
        row["review_flags"] = ["multi_sentence_evidence"]
        found.append(row)
        break
    return found


def _list_continuations(sentences: list[tuple[str, int, int]], covered: set[int], person_id: str | None) -> list[dict]:
    """A bullet may omit the outcome when the previous sentence just stated it.

    The window is the two adjacent sentences. The number comes only from the
    continuation. A previous sentence that does not itself say "probability of"
    an outcome does not lend its topic.
    """
    found = []
    for index, (sentence, start, end) in enumerate(sentences):
        if index in covered or index < 1:
            continue
        match = LIST_CONTINUATION.match(sentence)
        if not match or _risk_question(sentence)[0] or _arrival_key(sentence) or _attributes_to_someone_else(sentence):
            continue
        if _unsupported_probability_prefix(sentence, match.start("num")):
            continue
        percent_match = PERCENT.search(sentence)
        if not percent_match or not _same_outcome_continuations(sentence, [percent_match]):
            continue
        previous, prev_start, _prev_end = sentences[index - 1]
        prior = PRIOR_PROBABILITY.search(previous)
        if not prior:
            continue
        what = prior.group("what").lower()
        if what in {"transformative ai"}:
            question_key = "transformative_ai_by_year_probability"
            definition = "transformative"
        elif what in {"extinction", "human extinction"}:
            question_key = "extinction_unconditional"
            definition = "extinction"
        elif what == "superintelligence":
            question_key = "asi_by_year_probability"
            definition = "superintelligence"
        elif what == "asi":
            question_key = "asi_by_year_probability"
            definition = "asi"
        elif what == "agi":
            question_key = "agi_by_year_probability"
            definition = "agi"
        else:
            continue
        if definition not in previous.lower() and what not in previous.lower():
            continue
        value = _percent(match.group("num"))
        if value is None:
            continue
        value_text = f"{_trim_number(match.group('num'))}%"
        if value_text not in sentence:
            continue
        combined = f"{previous} {sentence}"
        if _ambiguous_probability_outcome(combined):
            continue
        row = _base(
            sentence,
            person_id,
            start=prev_start,
            end=end,
            context=combined,
            statement_type="explicit_numeric",
            forecast_kind="probability",
            question_key=question_key,
            definition_text=definition if definition in previous.lower() else what,
            condition_text=_condition(sentence) or _condition(previous),
            horizon_text=f"by {match.group('year')}",
            value_type="point",
            value_text=value_text,
            value_numeric=value,
            value_min=None,
            value_max=None,
            unit="probability",
            review_state="needs_review",
            confidence="low",
        )
        row["evidence_text"] = combined
        row["normalized_text"] = " ".join(combined.split())[:600]
        row["question_text"] = combined[:600]
        row["start_char"] = prev_start
        row["context_text"] = combined[:800]
        row["sentence_index"] = index
        row["review_flags"] = ["multi_sentence_evidence"]
        found.append(row)
    return found


def _review_flags(statement: dict) -> list[str]:
    flags = list(statement.get("review_flags") or [])
    if statement.get("statement_type") == "explicit_numeric" and not statement.get("horizon_text"):
        flags.append("missing_horizon")
    if statement.get("question_key") == "ambiguous_doom" or (
        statement.get("statement_type") == "explicit_numeric" and not statement.get("definition_text")
    ):
        flags.append("ambiguous_definition")
    if statement.get("value_type") == "range":
        flags.append("range_value")
    if not statement.get("question_key"):
        flags.append("question_key_uncertain")
    evidence = statement.get("evidence_text") or ""
    if (
        statement.get("statement_type") == "explicit_numeric"
        and re.search(r"\b(might|maybe|perhaps)\b", evidence, re.I)
        and not statement.get("condition_text")
    ):
        flags.append("conditionality_unclear")
    if revision_language(evidence):
        flags.append("possible_revision")
    return sorted(set(flags))


def _not_speaker(sentence: str) -> bool:
    return NOT_SPEAKER.search(sentence or "") is not None


def _attributes_to_someone_else(sentence: str) -> bool:
    """A named person's forecast in the sentence is not the tracked speaker's number."""
    if re.search(r"\bobservers estimating\b", sentence or "", re.I):
        return True
    return bool(
        re.search(
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z.'-]+)+\s+(?:still\s+|also\s+)?(?:thinks|believes?|estimates|says|said|argues|asked|claims|claimed)\b",
            sentence or "",
        )
    )


def _quoted_third_party(sentence: str) -> bool:
    """A quotation attributed to someone else is not this speaker's forecast."""
    if not re.search(r'["“”]', sentence or ""):
        return False
    if re.search(r"\b(i|i'm|i've|i’d)\s+(said|wrote|say|write)\b", sentence or "", re.I):
        return False
    return bool(re.search(r"\b(said|says|wrote|writes|asked|according to|told)\b", sentence or "", re.I))


def _negated_claim(sentence: str) -> bool:
    """A denied probability is not the speaker's estimate."""
    return bool(
        re.search(
            r"\b(do not|don't|does not|doesn't|did not|didn't|never|no longer)\b.{0,80}\b(think|believe|expect|estimate|assign|give|put)\b",
            sentence or "",
            re.I,
        )
    )


def _target_dates(horizon: str | None) -> tuple[str | None, str | None]:
    """Calendar bounds only when the horizon itself names a year. Relative wording stays open."""
    if not horizon:
        return None, None
    by_year = re.fullmatch(r"by (\d{4})", horizon.strip(), flags=re.I)
    if by_year:
        return None, f"{by_year.group(1)}-12-31"
    in_year = re.fullmatch(r"in (\d{4})", horizon.strip(), flags=re.I)
    if in_year:
        year = in_year.group(1)
        return f"{year}-01-01", f"{year}-12-31"
    before = re.fullmatch(r"before (\d{4})", horizon.strip(), flags=re.I)
    if before:
        year = int(before.group(1)) - 1
        if year < 2000:
            return None, None
        return None, f"{year}-12-31"
    return None, None


def _first_person(sentence: str) -> bool:
    return bool(re.search(r"\b(i expect|i think|i estimate|we'll|we will|my current|my timeline|my credence)\b", sentence, re.I))


def _approximate(sentence: str, index: int) -> bool:
    window = sentence[max(0, index - 24) : index]
    return bool(re.search(r"~|more than|at least|greater than|around|roughly|about", window, re.I))


def _condition(sentence: str) -> str | None:
    match = CONDITION.search(sentence)
    if match:
        return " ".join(match.group(0).split())[:400]
    built = re.search(r"\bof building [^.]{0,80}", sentence, re.I)
    if built:
        return " ".join(built.group(0).split())[:400]
    return None


def _percent(raw: str) -> float | None:
    """'10' in '10%' or '10 percent' is 0.10, not the integer 10."""
    number = float(raw)
    if number < 0 or number > 100:
        return None
    return number / 100.0


def _unit_interval(raw: str) -> float | None:
    number = float(raw)
    if number < 0 or number > 1:
        return None
    return number


def _span_overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < stop and end > begin for begin, stop in spans)


def _trim_number(raw: str) -> str:
    if raw.endswith(".0"):
        return raw[:-2]
    return raw


def _probability_spelling_in_source(value: str, text: str) -> bool:
    return value in text or (value.startswith("0.") and value[1:] in text)


def _horizon(sentence: str, *, relative: bool = True) -> str | None:
    match = HORIZON_YEAR.search(sentence)
    if match:
        return f"{match.group('prep').lower()} {match.group('year')}"
    within = HORIZON_WITHIN.search(sentence)
    if within:
        return f"within {within.group('years')} years"
    if relative:
        ahead = re.search(rf"\bin\s+(?P<years>{_NUMWORD})\s+years\b", sentence, re.I)
        if ahead and not _past_time(sentence):
            return f"in {ahead.group('years')} years"
    inn = HORIZON_IN_YEAR.search(sentence)
    if inn and not (int(inn.group("year")) < 2024 and re.search(rf"\bin\s+{_YEAR}\b", sentence, re.I)):
        return f"in {inn.group('year')}"
    decade = DECADE.search(sentence)
    if decade:
        return " ".join(decade.group(0).split())
    nxt = NEXT_DECADE.search(sentence)
    if nxt:
        return " ".join(nxt.group(0).split()).lower()
    if THIS_DECADE.search(sentence):
        return "this decade"
    return None


def _horizon_near(sentence: str, index: int) -> str | None:
    window = sentence[index : index + 110]
    match = HORIZON_YEAR.search(window)
    if match:
        return f"{match.group('prep').lower()} {match.group('year')}"
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
        if TOPIC_NEAR.search(window) or _horizon(window, relative=False) or _loose_horizon(sentence):
            return True
    return False


def _sentences_with_spans(text: str) -> list[tuple[str, int, int]]:
    # Leading-dot decimals are numeric tokens too: ".5%" must not become "5%".
    spans = []
    for match in re.finditer(r"(?:\d*\.\d+|[^.!?\n])+(?:[.!?]+|(?=\n)|$)", text):
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
