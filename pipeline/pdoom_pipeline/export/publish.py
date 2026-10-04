"""Decide whether a canonical file may be published.

A failed refresh is not imported. A partial refresh can be imported, and the
publication record says so. Import failure is left to the database transaction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def publication_decision(document: dict) -> str:
    runs = [row for row in document.get("ingestion_runs") or [] if row.get("collector") in {"belief-corpus", "refresh"}]
    if not runs:
        return "publish"
    status = runs[-1].get("status")
    if status == "failed":
        return "refuse"
    if status == "partial":
        return "publish_partial"
    return "publish"


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] != "--file":
        raise SystemExit("usage: python -m pdoom_pipeline.export.publish --file canonical.json")
    document = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    decision = publication_decision(document)
    print(decision)
    if decision == "refuse":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
