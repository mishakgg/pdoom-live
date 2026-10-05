from pdoom_pipeline.extract.statements import extract_statements


def test_bare_people_count_is_not_a_probability():
    found = extract_statements("I think 10 people would be affected.")
    for row in found:
        assert row["statement_type"] != "explicit_numeric"
        assert row["unit"] != "probability"
        assert row["value_text"] not in {"10", "0.10", "10%", "10 percent"}
        assert row["value_numeric"] not in {10, 0.10}
        assert row["value_min"] not in {10, 0.10}
        assert row["value_max"] not in {10, 0.10}


def test_percent_chance_stays_explicit_numeric_with_source_spelling():
    found = extract_statements("There is a 10 percent chance of human extinction by 2040.")
    assert len(found) == 1
    row = found[0]
    assert row["statement_type"] == "explicit_numeric"
    assert row["value_type"] == "point"
    assert row["value_text"] == "10 percent"
    assert row["value_numeric"] == 0.10
    assert row["value_numeric"] != 10
    assert row["value_min"] is None
    assert row["value_max"] is None
    assert row["unit"] == "probability"
    assert "10 percent" in row["evidence_text"]


def test_unlikely_stays_qualitative_without_a_number():
    found = extract_statements("Extinction from AI is unlikely.")
    assert len(found) == 1
    row = found[0]
    assert row["statement_type"] == "explicit_qualitative"
    assert row["value_type"] == "none"
    assert row["value_text"] is None
    assert row["value_numeric"] is None
    assert row["value_min"] is None
    assert row["value_max"] is None
    assert row["unit"] is None


def test_range_stays_a_range():
    hyphen = extract_statements("My credence is 5-20% for catastrophic harm by 2035.")
    assert len(hyphen) == 1
    assert hyphen[0]["statement_type"] == "explicit_numeric"
    assert hyphen[0]["value_type"] == "range"
    assert hyphen[0]["value_numeric"] is None
    assert hyphen[0]["value_text"] is None
    assert hyphen[0]["value_min"] == 0.05
    assert hyphen[0]["value_max"] == 0.20
    assert hyphen[0]["unit"] == "probability"

    spelled = extract_statements("My credence is between 10 and 20 percent for catastrophic harm by 2035.")
    numeric = [row for row in spelled if row["statement_type"] == "explicit_numeric"]
    assert len(numeric) == 1
    assert numeric[0]["value_type"] == "range"
    assert numeric[0]["value_numeric"] is None
    assert numeric[0]["value_text"] is None
    assert numeric[0]["value_min"] == 0.10
    assert numeric[0]["value_max"] == 0.20
    assert numeric[0]["unit"] == "probability"
