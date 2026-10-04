"""Load the authoritative comparability registry.

The TypeScript registry in ``packages/contracts/src/comparability.ts`` is the
source of truth. This module reads the committed JSON snapshot and does not
keep a second taxonomy.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "src" / "comparability-registry.json"


@lru_cache(maxsize=1)
def load_comparability_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def registry_questions() -> list[dict[str, Any]]:
    questions = load_comparability_registry()["questions"]
    return list(questions)


def question_by_key(key: str) -> dict[str, Any] | None:
    for question in registry_questions():
        if question["key"] == key:
            return question
    return None
