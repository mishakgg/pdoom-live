"""Offline regressions for complete probability tokens and unambiguous outcomes."""
import pytest

from pdoom_pipeline.extract.statements import extract_statements
from pdoom_pipeline.export.corpus import _forecast


@pytest.mark.parametrize("token,value,spelling", [
    (".5%", 0.005, "0.5%"), ("0.5%", 0.005, "0.5%"),
    (".5 percent", 0.005, "0.5 percent"), ("10%", 0.1, "10%"),
    ("100%", 1.0, "100%"), ("0%", 0.0, "0%"),
    (".10", 0.1, ".10"), ("0.10", 0.1, "0.10"),
])
def test_complete_probability_token_preserves_value_and_evidence(token, value, spelling):
    sentence = f"I estimate a {token} chance of human extinction caused by AI by 2070."
    text = f"Earlier context. {sentence} Later context."
    rows = extract_statements(text, person_id="person:ada-example")
    assert len(rows) == 1
    row = rows[0]
    assert row["value_numeric"] == value
    assert row["value_text"] == spelling
    assert row["evidence_text"] == sentence
    assert text[row["start_char"]:row["end_char"]].strip() == sentence
    assert "Earlier context" in row["context_text"] and "Later context" in row["context_text"]
    assert row["review_state"] != "human_verified"
    exported = _forecast(row, "fixture")
    assert exported["value_numeric"] == value and exported["value_text"] == spelling


@pytest.mark.parametrize("token", [
    "1000%", "120%", "-10%", "+10%", "−10%", "- 10%", "+ 10 percent",
    "1,000%", "0,5%", "1e-3%", "1.2.5%", "1000 percent",
    "100/10", "1000/99", "-1 in 10", "- 1 in 10", "1 in 0", "20 in 10",
])
def test_unsupported_probability_tokens_are_not_salvaged_or_recast_as_timeline(token):
    assert extract_statements(f"I estimate a {token} chance of AGI by 2030.") == []


def test_year_is_not_a_percent_range_endpoint():
    rows = extract_statements("I estimate a 10% chance of AGI by 2030 and 50% by 2040.")
    assert [(row["value_numeric"], row["horizon_text"]) for row in rows] == [(0.1, "by 2030"), (0.5, "by 2040")]


@pytest.mark.parametrize("token,minimum,maximum", [
    ("5-20%", 0.05, 0.2), ("10 and 20 percent", 0.1, 0.2),
    (".5–1.5%", 0.005, 0.015), ("0.05 to 0.20", 0.05, 0.2),
])
def test_single_outcome_ranges_stay_ranges(token, minimum, maximum):
    rows = extract_statements(f"My credence is {token} for catastrophic harm by 2035.")
    assert len(rows) == 1
    assert rows[0]["value_type"] == "range"
    assert rows[0]["value_numeric"] is None
    assert rows[0]["value_min"] == minimum and rows[0]["value_max"] == maximum


@pytest.mark.parametrize("token,value", [("1 in 10", 0.1), ("2/3", 2 / 3)])
def test_supported_odds_still_extract(token, value):
    rows = extract_statements(f"I estimate a {token} chance of human extinction by 2070.")
    assert len(rows) == 1 and rows[0]["value_numeric"] == value


@pytest.mark.parametrize("text", [
    "I estimate 10% chance of human extinction by 2070; I estimate 50% chance of AGI by 2030.",
    "I estimate a 10% chance of human extinction and a 20% chance of catastrophe by 2070.",
    "I assign a 50% chance to AGI by 2030 and a 20% chance to superintelligence by 2040.",
    "My probability of avoiding human extinction by 2070 is 95%.",
    "I estimate a 10% chance of no human extinction by 2070.",
    "I estimate a 10% chance that AGI will not arrive by 2030.",
    "I estimate a 10% chance of preventing catastrophe by 2070.",
    "I assign a 10% probability to AGI failing to arrive by 2030.",
    "I estimate a 10% chance that AGI won't arrive by 2030.",
    "The probability of human extinction and catastrophe is unclear. 10% probability by 2070.",
    "We may avoid human extinction by 2070. I'll give a probability of 95% for that.",
    "I estimate a probability of 10%. By that I mean avoiding human extinction by 2070.",
])
def test_mixed_or_complement_outcomes_abstain_without_inventing_probabilities(text):
    assert extract_statements(text) == []


@pytest.mark.parametrize("text,key", [
    ("I assign a 10% chance to human extinction by 2070 if we build AGI.", "extinction_conditional_agi"),
    ("If we build AGI, I assign a 10% chance to human extinction by 2070.", "extinction_conditional_agi"),
    ("I assign a 10% chance to human extinction by 2070 if AGI is not aligned.", "extinction_conditional_agi"),
    ("I assign a 10% chance to human extinction caused by AGI by 2070.", "extinction_unconditional"),
    ("I assign a 10% chance to human extinction from AGI by 2070.", "extinction_unconditional"),
    ("If a catastrophe occurs, I assign a 50% chance to AGI by 2030.", "agi_by_year_probability"),
])
def test_conditions_and_causal_entities_are_not_independent_forecast_outcomes(text, key):
    rows = extract_statements(text)
    assert len(rows) == 1
    assert rows[0]["question_key"] == key
    assert rows[0]["review_state"] != "human_verified"


def test_separate_sentences_keep_their_distinct_outcomes():
    rows = extract_statements("I assign a 10% chance to extinction by 2070. I assign a 50% chance to AGI by 2030.")
    assert [(row["question_key"], row["value_numeric"]) for row in rows] == [("extinction_unconditional", 0.1), ("agi_by_year_probability", 0.5)]


@pytest.mark.parametrize("text", [
    "I assign a 10% chance to extinction by 2070 and a 50% chance to rain by 2030.",
    "I assign a 50% chance to rain by 2030 and a 10% chance to extinction by 2070.",
    "I assign a 10% chance to extinction by 2070; a benchmark score is 50% by 2030.",
    "I assign a 10% chance to extinction by 2070 and a 50% chance to job displacement by 2030.",
])
def test_unknown_or_quantity_outcomes_do_not_borrow_the_known_question(text):
    assert extract_statements(text) == []


def test_leading_dot_probability_in_anaphora_keeps_both_source_sentences():
    text = "I estimate a probability of .5%. By that I mean human extinction by 2070."
    rows = extract_statements(text)
    assert len(rows) == 1
    assert rows[0]["value_numeric"] == 0.005
    assert rows[0]["value_text"] == "0.5%"
    assert rows[0]["evidence_text"] == text
    assert rows[0]["review_state"] == "needs_review"


@pytest.mark.parametrize("token", ["1000 to 20%", "1000 and 20 percent", "-10 to 20%", "1.5 to .2"])
def test_invalid_range_cannot_leave_a_valid_looking_endpoint(token):
    assert extract_statements(f"I assign a {token} chance to AGI by 2030.") == []


def test_dense_probability_passage_abstains_instead_of_partial_binding():
    continuation = "; ".join(f"a {value}% chance of extinction by 2070" for value in range(1, 8))
    assert extract_statements(f"I assign {continuation}.") == []
    supported = "; ".join(f"a {value}% chance of extinction by 2070" for value in range(1, 7))
    assert len(extract_statements(f"I assign {supported}.")) == 6


@pytest.mark.parametrize("token", ["10%%", "1 in 1000%", "1 in 10.5", "minus 10%", "1 000%", "1'000%", "1\u202f000%"])
def test_malformed_units_and_other_grouping_do_not_change_the_number(token):
    assert extract_statements(f"I assign a {token} chance to AGI by 2030.") == []


def test_one_in_odds_at_sentence_end_keep_the_terminal_punctuation():
    text = "The probability of human extinction by 2070 is 1 in 10."
    rows = extract_statements(text)
    assert len(rows) == 1 and rows[0]["value_numeric"] == 0.1
    assert rows[0]["evidence_text"] == text


@pytest.mark.parametrize("answer", [
    "I'll give a probability of - 10% for that.",
    "I'll give a probability of 1 000% for that.",
    "I'll give a probability of 1000 to 20% for that.",
    "-10% probability by 2070.",
    "- 10% probability by 2070.",
])
def test_adjacent_sentence_paths_cannot_salvage_rejected_probability_tokens(answer):
    assert extract_statements(f"The probability of human extinction is uncertain. {answer}") == []


def test_unambiguous_asterisk_probability_continuation_remains_supported():
    rows = extract_statements("The probability of human extinction is uncertain. * 10% probability by 2070.")
    assert len(rows) == 1 and rows[0]["value_numeric"] == 0.1
    assert rows[0]["review_state"] == "needs_review"


def test_causal_takeover_does_not_replace_the_mass_death_outcome():
    text = "Probability that most humans die because of an AI takeover: 11%"
    rows = extract_statements(text)
    assert len(rows) == 1
    assert rows[0]["question_key"] == "mass_human_death"
    assert rows[0]["value_numeric"] == 0.11
    assert rows[0]["evidence_text"] == text


@pytest.mark.parametrize("text", [
    "The chance of rain is 50%, and extinction is 10% by 2070.",
    "The chance of rain is 50%; human extinction by 2070 is unclear.",
    "Extinction is a concern, but the chance of rain is 50% by 2070.",
    "The probability of human extinction is uncertain. I'll give a probability of rain of 50% for that.",
    "The probability of human extinction is uncertain. 50% probability by 2070 for rain.",
])
def test_unknown_outcome_prefix_and_single_number_clauses_abstain(text):
    assert extract_statements(text) == []


@pytest.mark.parametrize("token", [
    "10% to -20%", "10% to 1000%", "10% to 1,000%", "0.1 to 1.5",
    "10% and 1000%", "10%–1,000%", "10% to +20%",
])
def test_invalid_right_range_endpoint_cannot_leave_the_left_point(token):
    assert extract_statements(f"I assign a {token} chance to AGI by 2030.") == []


def test_a_preamble_does_not_hide_a_direct_number_to_outcome_binding():
    text = "Using this framework, I will justify a value of 47% for the probability of AGI arriving before 2043."
    rows = extract_statements(text)
    assert len(rows) == 1
    assert rows[0]["question_key"] == "agi_by_year_probability"
    assert rows[0]["value_numeric"] == 0.47


def test_unparsed_odds_range_is_not_two_independent_points():
    assert extract_statements("I assign a 1 in 10 to 2 in 10 chance of AGI by 2030.") == []
