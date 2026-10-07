"""One atomic output seam for a leased, quota enforcing collection sink."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

WriteBytes = Callable[[Path, bytes], None]


def atomic_bytes(path: Path, payload: bytes, write_bytes: WriteBytes | None = None) -> None:
    if write_bytes is not None:
        # The external sink owns reservation, temporary bytes and atomic replace.
        write_bytes(path.absolute(), payload)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
