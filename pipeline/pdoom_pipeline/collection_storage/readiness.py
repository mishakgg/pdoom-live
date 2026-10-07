"""Read-only readiness inventory. This command never authenticates or collects."""
import json
import shutil

from .scratch import COLLECTION_ROOT, HARD_MAX_BYTES, METADATA_RESERVE, TASK_ROOT, _plain, validate_windows_path
from .supervisor import MAX_BATCH_BYTES, MAX_FILES


def report() -> dict:
    validate_windows_path(str(COLLECTION_ROOT))
    _plain(COLLECTION_ROOT)
    disk = COLLECTION_ROOT if COLLECTION_ROOT.exists() else str(TASK_ROOT)
    return {"status": "blocked_for_live_pilot", "mode": "dry_run_no_network",
            "scratch_root": str(COLLECTION_ROOT), "hard_max_bytes": HARD_MAX_BYTES,
            "min_free_bytes": 5_000_000_000, "metadata_reserve_bytes": METADATA_RESERVE,
            "batch_max_bytes": MAX_BATCH_BYTES, "batch_max_files": MAX_FILES,
            "disk_free_bytes": shutil.disk_usage(disk).free,
            "schedule_enabled": False, "public_import_enabled": False,
            "blockers": ["action-time confirmed OAuth and secure credential provider",
                         "API account identity, actual quota and private root ID pin",
                         "synthetic Drive write/readback checksum smoke",
                         "reviewed exact eight-feed identity/rights pins and integrated write gateway",
                         "parent release for one metadata-only pilot"]}


if __name__ == "__main__":
    print(json.dumps(report(), indent=2))
