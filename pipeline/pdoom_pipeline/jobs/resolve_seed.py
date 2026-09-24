"""Export the reviewed cohort and optionally resolve OpenAlex identities."""

from __future__ import annotations

import argparse
import json

from pdoom_pipeline.identity.live import resolve_live
from pdoom_pipeline.quality.report import write_report
from pdoom_pipeline.seed.build import write_seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the pdoom.live seed cohort.")
    parser.add_argument("--resolve", action="store_true", help="Query the OpenAlex API. This uses the network.")
    args = parser.parse_args()
    resolution = resolve_live() if args.resolve else None
    counts = write_seed(resolution=resolution)
    report = write_report()
    print(json.dumps({"files": counts, "academic_identifier_percent": report["percent_with_academic_identifier"]}, indent=2))


if __name__ == "__main__":
    main()
