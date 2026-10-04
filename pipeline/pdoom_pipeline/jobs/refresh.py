"""Run one bounded collection refresh. This does not enable a schedule."""

from __future__ import annotations

import argparse
import json
import signal

from pdoom_pipeline.jobs.collect_beliefs import COLLECTION, run
from pdoom_pipeline.refresh.lock import RefreshLock
from pdoom_pipeline.seed.build import SEED_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh public sources once and assemble a canonical document.")
    parser.add_argument("--once", action="store_true", help="Run a single bounded pass and exit.")
    parser.add_argument("--max-sources", type=int, default=40)
    parser.add_argument("--max-seconds", type=float, default=900)
    args = parser.parse_args()
    if not args.once:
        raise SystemExit("Refusing to run without --once. The refresh timer is not enabled.")
    if args.max_sources < 1 or args.max_seconds < 1:
        raise SystemExit("max-sources and max-seconds must be positive.")
    stop = {"value": False}

    def _stop(signum, _frame) -> None:
        stop["value"] = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    lock_path = COLLECTION / "state" / "refresh.lock"
    with RefreshLock(lock_path):
        if stop["value"]:
            raise SystemExit("refresh cancelled before start")
        summary = run(
            SEED_DIR,
            max_sources=args.max_sources,
            max_seconds=args.max_seconds,
            cancelled=lambda: stop["value"],
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
