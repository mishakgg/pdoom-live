"""Shared observability catalog. Thresholds live in one JSON file."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def catalog_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "packages" / "observability" / "catalog.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("observability catalog")


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    return json.loads(catalog_path().read_text(encoding="utf-8"))


def allowed(group: str, value: str | None, fallback: str) -> str:
    labels = load_catalog()["labels"].get(group, [])
    if value in labels:
        return str(value)
    if fallback in labels:
        return fallback
    return "other"
