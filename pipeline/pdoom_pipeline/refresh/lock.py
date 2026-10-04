"""Single-host lock so two refreshes cannot assemble the same collection."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class RefreshOverlap(RuntimeError):
    pass


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RefreshLock:
    def __init__(self, path: Path, *, stale_after: float = 6 * 60 * 60):
        self.path = path
        self.stale_after = stale_after
        self._held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            self._reclaim_or_refuse()
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        self._held = True

    def release(self) -> None:
        if self._held and self.path.exists():
            self.path.unlink()
        self._held = False

    def __enter__(self) -> "RefreshLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    def _reclaim_or_refuse(self) -> None:
        try:
            existing = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        pid = int(existing.get("pid") or 0)
        started = existing.get("started_at") or ""
        stale = False
        if started:
            try:
                then = datetime.fromisoformat(started.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - then).total_seconds()
                stale = age > self.stale_after
            except ValueError:
                stale = True
        if _alive(pid) and not stale:
            raise RefreshOverlap(
                f"refresh already running as pid {pid} since {started}. "
                "Wait for it to finish. If that process is gone, delete the lock file and run once again."
            )
        self.path.unlink()
