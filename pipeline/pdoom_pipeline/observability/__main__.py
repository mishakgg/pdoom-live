"""Pipeline quality check.

    python -m pdoom_pipeline.observability check --snapshot report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pdoom_pipeline.observability.evaluate import evaluate, quality_exit_code
from pdoom_pipeline.observability.logging import log_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pdoom_pipeline.observability")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--snapshot", required=True)
    check.add_argument("--baseline")
    check.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    if args.command != "check":
        return 2
    try:
        snapshot = _read(args.snapshot, "snapshot")
        baseline = _read(args.baseline, "baseline") if args.baseline else None
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    report = evaluate(snapshot, baseline, scope="snapshot")
    print(report["summary"], file=sys.stderr)
    print(json.dumps(report))
    log_event(level="info" if report["ok"] else "error", operation="quality_check", outcome="succeeded" if report["ok"] else "failed", run_id=report["run_id"])
    return quality_exit_code(report, args.strict)


def _read(path: str, label: str):
    file = Path(path)
    if not file.is_file() or file.stat().st_size > 32 * 1024 * 1024:
        raise ValueError(f"could not read {label} file")
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} file is not valid JSON") from error


if __name__ == "__main__":
    sys.exit(main())
