"""Conservative name keys.

Single-letter initials are ignored only when a given name and family name remain.
John Schulman does not match Jonathan Schulman. Meta does not match inside another word
at the institution layer; this module only compares whole name tokens.
"""

from __future__ import annotations

import unicodedata


def normalize_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name or "")
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    lowered = without_marks.lower().replace(".", " ").replace("-", " ").replace("'", "")
    cleaned = "".join(char if char.isalnum() or char.isspace() else " " for char in lowered)
    return " ".join(cleaned.split())


def name_key(name: str) -> tuple[str, ...]:
    tokens = [token for token in normalize_name(name).split() if len(token) > 1]
    return tuple(tokens)


def same_person_name(left: str, right: str) -> bool:
    left_key = name_key(left)
    right_key = name_key(right)
    return bool(left_key) and left_key == right_key
