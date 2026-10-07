"""Separate belief and enrichment staging directories.

A belief refresh must not write the enrichment directory, and the canonical
document is assembled from both inputs on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path
from pdoom_pipeline.ingest.writes import WriteBytes, atomic_bytes


def belief_dir(collection: Path) -> Path:
    return collection / "staging" / "belief"


def enrichment_dir(collection: Path) -> Path:
    return collection / "staging" / "enrichment"


def state_dir(collection: Path) -> Path:
    return collection / "state"


def write_belief_staging(collection: Path, *, observations: list[dict], statements: list[dict], runs: list[dict], summary: dict, write_bytes: WriteBytes | None = None) -> Path:
    directory = belief_dir(collection)
    _jsonl(directory / "observations.jsonl", observations, write_bytes)
    _jsonl(directory / "statements.jsonl", statements, write_bytes)
    _jsonl(directory / "runs.jsonl", runs, write_bytes)
    atomic_bytes(directory / "summary.json", (json.dumps(summary, indent=2) + "\n").encode(), write_bytes)
    return directory


def read_enrichment_sources(collection: Path) -> list[dict]:
    path = enrichment_dir(collection) / "sources.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _jsonl(path: Path, rows: list[dict], write_bytes: WriteBytes | None = None) -> None:
    atomic_bytes(path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode(), write_bytes)
