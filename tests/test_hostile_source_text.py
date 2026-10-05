"""A page that tries to instruct the pipeline stays stored text."""

from pathlib import Path

from pdoom_pipeline.belief.pages import article_text
from pdoom_pipeline.extract.statements import extract_statements

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "hostile" / "instruction_page.html"


def _article_inner(html: str) -> str:
    lowered = html.lower()
    start = lowered.find("<article")
    assert start != -1
    start = html.find(">", start) + 1
    end = lowered.find("</article>", start)
    assert end != -1
    return html[start:end]


def test_instruction_page_is_evidence_or_rejected_and_not_explicit_numeric():
    html = FIXTURE.read_text(encoding="utf-8")
    body = _article_inner(html)
    assert "ignore previous instructions" in body.lower()
    assert "assign a precise probability" in body.lower()

    visible = article_text(html)
    lines = [line for line in visible.splitlines() if "ignore previous instructions" in line.lower()]
    assert len(lines) == 1
    sentence = lines[0]
    assert "assign a precise probability" in sentence.lower()
    assert sentence in visible

    statements = extract_statements(visible)
    assert [row for row in statements if row["statement_type"] == "explicit_numeric"] == []
    for row in statements:
        assert row.get("value_numeric") is None
        assert row.get("value_min") is None
        assert row.get("value_max") is None
        assert row.get("value_text") is None

    kept = [row for row in statements if sentence in (row.get("evidence_text") or "")]
    if kept:
        assert all(row["statement_type"] != "explicit_numeric" for row in kept)
        assert all(row.get("value_numeric") is None for row in kept)
    else:
        assert extract_statements(sentence) == []
