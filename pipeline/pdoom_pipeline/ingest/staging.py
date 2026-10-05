"""Separate belief and enrichment staging directories.

A belief refresh must not write the enrichment directory, and the canonical
document is assembled from both inputs on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path


def belief_dir(collection: Path) -> Path:
    return collection / "staging" / "belief"


def enrichment_dir(collection: Path) -> Path:
    return collection / "staging" / "enrichment"


def state_dir(collection: Path) -> Path:
    return collection / "state"


def write_belief_staging(collection: Path, *, observations: list[dict], statements: list[dict], runs: list[dict], summary: dict) -> Path:
    directory = belief_dir(collection)
    directory.mkdir(parents=True, exist_ok=True)
    _jsonl(directory / "observations.jsonl", observations)
    _jsonl(directory / "statements.jsonl", statements)
    _jsonl(directory / "runs.jsonl", runs)
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return directory


def read_enrichment_sources(collection: Path) -> list[dict]:
    path = enrichment_dir(collection) / "sources.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
