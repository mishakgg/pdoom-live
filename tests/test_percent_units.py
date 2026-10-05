from pdoom_pipeline.extract.statements import extract_statements


def test_percent_sign_and_decimal_keep_wording_and_normalized_probability():
    percent = extract_statements("I think there is a 10% chance of human extinction by 2040.")
    assert percent[0]["statement_type"] == "explicit_numeric"
    assert percent[0]["value_type"] == "point"
    assert percent[0]["value_text"] == "10%"
    assert percent[0]["value_numeric"] == 0.10
    assert percent[0]["unit"] == "probability"
    assert "10%" in percent[0]["evidence_text"]

    decimal = extract_statements("I think there is a 0.10 chance of human extinction by 2040.")
    assert decimal[0]["statement_type"] == "explicit_numeric"
    assert decimal[0]["value_type"] == "point"
    assert decimal[0]["value_text"] == "0.10"
    assert decimal[0]["value_numeric"] == 0.10
    assert decimal[0]["unit"] == "probability"
    assert "0.10" in decimal[0]["evidence_text"]


def test_percent_word_is_not_read_as_ten():
    found = extract_statements("I think there is a 10 percent chance of human extinction by 2040.")
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


def test_unlikely_stays_qualitative_without_a_fabricated_number():
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

    decimal = extract_statements("My credence is 0.05 to 0.20 for catastrophic harm by 2035.")
    assert len(decimal) == 1
    assert decimal[0]["value_type"] == "range"
    assert decimal[0]["value_numeric"] is None
    assert decimal[0]["value_text"] is None
    assert decimal[0]["value_min"] == 0.05
    assert decimal[0]["value_max"] == 0.20
    assert decimal[0]["unit"] == "probability"
