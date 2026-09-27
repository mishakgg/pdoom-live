"""Candidate relationships only when the later text says the view was revised."""

from __future__ import annotations

from pdoom_pipeline.extract.statements import revision_language


def view_change_candidates(statements: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for statement in statements:
        key = statement.get("question_key")
        if not key or statement.get("statement_type") != "explicit_numeric":
            continue
        grouped.setdefault((statement.get("person_id"), key, statement.get("horizon_text")), []).append(statement)
    relationships = []
    for rows in grouped.values():
        ordered = sorted(rows, key=lambda row: ((row.get("published_at") or ""), row.get("source_url") or ""))
        previous = None
        for later in ordered:
            earlier = previous
            previous = later
            if earlier is None:
                continue
            if earlier.get("evidence_text") == later.get("evidence_text"):
                continue
            if earlier.get("horizon_text") != later.get("horizon_text"):
                continue
            if (earlier.get("published_at") or "") >= (later.get("published_at") or ""):
                continue
            if not revision_language(later.get("evidence_text") or ""):
                continue
            if _value_signature(earlier) == _value_signature(later):
                kind = "repeats"
            elif _changed_number(earlier, later):
                kind = "updates"
            else:
                continue
            relationships.append(
                {
                    "from_person_id": later.get("person_id"),
                    "earlier_evidence": earlier.get("evidence_text"),
                    "later_evidence": later.get("evidence_text"),
                    "question_key": later.get("question_key"),
                    "relationship_type": kind,
                    "method": "revision-language-0.1",
                    "confidence": 0.45,
                    "review_state": "unreviewed",
                    "earlier_local_id": earlier.get("local_id"),
                    "later_local_id": later.get("local_id"),
                }
            )
    return relationships


def _value_signature(statement: dict) -> tuple:
    return (statement.get("value_numeric"), statement.get("value_min"), statement.get("value_max"), statement.get("horizon_text"))


def _changed_number(earlier: dict, later: dict) -> bool:
    if earlier.get("unit") != later.get("unit"):
        return False
    left = earlier.get("value_numeric") if earlier.get("value_numeric") is not None else earlier.get("value_min")
    right = later.get("value_numeric") if later.get("value_numeric") is not None else later.get("value_min")
    return left is not None and right is not None and left != right
