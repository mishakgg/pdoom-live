"""Stable public identifiers for refreshed statements and evidence.

Slugs do not use collection order. Version 1 source-item slugs stay
`item-` plus the SHA-256 prefix of the canonical URL, which is the slug
shape already published from this pipeline. Later content versions use a
different slug so the first version's row remains addressable.
"""

from __future__ import annotations

import hashlib
import json


def canonical_claim_number(value: object) -> str:
    """Match the TypeScript candidate-key number spelling."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, str):
        return value
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if number != number:
        return ""
    if number.is_integer():
        return str(int(number))
    return json.dumps(number)


def statement_material(statement: dict) -> str:
    return "\n".join(
        [
            statement.get("person_slug") or "",
            statement.get("source_url") or "",
            statement.get("statement_type") or "",
            statement.get("extractor_version") or "",
            statement.get("question_key") or "",
            statement.get("horizon_text") or "",
            statement.get("unit") or "",
            statement.get("value_type") or "",
            canonical_claim_number(statement.get("value_numeric")),
            canonical_claim_number(statement.get("value_min")),
            canonical_claim_number(statement.get("value_max")),
            _int_text(statement.get("start_char")),
            _int_text(statement.get("end_char")),
        ]
    )


def evidence_material(statement: dict) -> str:
    text = (statement.get("evidence_text") or "")[:2000]
    return "\n".join(
        [
            statement.get("source_url") or "",
            text,
            _int_text(statement.get("start_char")),
            _int_text(statement.get("start_ms")),
        ]
    )


def candidate_material(
    *,
    person_slug: str,
    source_content_hash: str,
    evidence_hash: str,
    extractor_name: str,
    extractor_version: str,
    statement_type: str,
    question_key: str | None,
    horizon_text: str | None,
    unit: str | None,
    value_type: str | None,
    value_numeric: object,
    value_min: object,
    value_max: object,
) -> str:
    return "\n".join(
        [
            person_slug,
            source_content_hash,
            evidence_hash,
            extractor_name,
            extractor_version,
            statement_type,
            question_key or "",
            horizon_text or "",
            unit or "",
            value_type or "",
            canonical_claim_number(value_numeric),
            canonical_claim_number(value_min),
            canonical_claim_number(value_max),
        ]
    )


def candidate_key_for(statement: dict, *, source_content_hash: str, evidence_text: str) -> str:
    version = statement.get("extractor_version") or ""
    name = version.split("/")[0] or version
    evidence_hash = sha256_hex(evidence_text[:2000])
    return sha256_hex(
        candidate_material(
            person_slug=statement.get("person_slug") or "",
            source_content_hash=_hex_hash(source_content_hash),
            evidence_hash=evidence_hash,
            extractor_name=name,
            extractor_version=version,
            statement_type=statement.get("statement_type") or "",
            question_key=statement.get("question_key"),
            horizon_text=statement.get("horizon_text"),
            unit=statement.get("unit"),
            value_type=statement.get("value_type"),
            value_numeric=statement.get("value_numeric"),
            value_min=statement.get("value_min"),
            value_max=statement.get("value_max"),
        )
    )


def statement_slug(statement: dict) -> str:
    return _prefixed("st", statement_material(statement))


def evidence_slug(statement: dict) -> str:
    return _prefixed("ev", evidence_material(statement))


def source_item_slug(canonical_url: str, content_hash: str, content_version: int) -> str:
    if content_version <= 1:
        return _prefixed("item", canonical_url)
    return _prefixed("item", f"{canonical_url}\n{_hex_hash(content_hash)}\n{content_version}")


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _prefixed(prefix: str, raw: str) -> str:
    return f"{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _hex_hash(value: str | None) -> str:
    text = value or ""
    if text.startswith("sha256:"):
        text = text.split(":", 1)[1]
    return text


def _int_text(value: object) -> str:
    if value is None or value == "":
        return ""
    return str(int(value))  # type: ignore[arg-type]
