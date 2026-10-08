"""Read-only readiness inventory. This command never authenticates or collects."""
import inspect
import json
import shutil

from .scratch import HARD_MAX_BYTES, METADATA_RESERVE, TASK_ROOT, ScratchPaths
from .supervisor import MAX_BATCH_BYTES, MAX_FILES


def report(paths: ScratchPaths | None = None) -> dict:
    paths = paths or ScratchPaths(mode="windows")
    root = paths.validate()
    from pdoom_pipeline.refresh.runner import run_refresh
    hook = "write_bytes" in inspect.signature(run_refresh).parameters
    disk = root if root.exists() else (root.parent if paths.mode == "posix" else str(TASK_ROOT))
    return {"status": "blocked_for_live_pilot", "mode": "dry_run_no_network",
            "storage_mode": paths.mode, "scratch_root": str(root),
            "seed_root": str(paths.seed_root) if paths.seed_root is not None else None,
            "hard_max_bytes": HARD_MAX_BYTES,
            "min_free_bytes": 5_000_000_000, "metadata_reserve_bytes": METADATA_RESERVE,
            "batch_max_bytes": MAX_BATCH_BYTES, "batch_max_files": MAX_FILES,
            "disk_free_bytes": shutil.disk_usage(disk).free,
            "continuous_collection_enabled": False, "schedule_enabled": False,
            "public_import_enabled": False, "runner_write_hook_available": hook,
            "blockers": ["action-time confirmed OAuth and secure credential provider",
                         "API account identity, actual quota and private root ID pin",
                         "synthetic Drive write/readback checksum smoke",
                         "reviewed live URL/rights readiness for the pinned eight feeds",
                         "parent release for one metadata-only pilot"]}


if __name__ == "__main__":
    print(json.dumps(report(), indent=2))
