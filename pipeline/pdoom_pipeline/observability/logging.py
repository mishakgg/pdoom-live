"""Structured logs. Only stable fields are emitted."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Callable

from pdoom_pipeline.observability.catalog import allowed
from pdoom_pipeline.observability.metrics import normalize_adapter

TOKEN = re.compile(r"^[a-z0-9_.:-]{1,64}$")
ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
SECRET = re.compile(r"postgres(?:ql)?:\/\/|bearer\s+\S+|password\s*=|authorization\s*:|cookie\s*:|-----begin", re.I)

_sink: Callable[[str], None] | None = None


def set_log_sink(sink: Callable[[str], None] | None) -> None:
    global _sink
    _sink = sink


def log_event(**fields: object) -> None:
    line = format_log(fields)
    if _sink is None:
        sys.stderr.write(line + "\n")
    else:
        _sink(line)


def format_log(fields: dict) -> str:
    operation = _token(fields.get("operation"), "unknown")
    record: dict[str, object] = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": fields.get("level") if fields.get("level") in {"info", "warn", "error"} else "info",
        "operation": operation,
    }
    for key, pattern in (("request_id", ID), ("run_id", ID)):
        value = fields.get(key)
        if isinstance(value, str) and pattern.fullmatch(value):
            record[key] = value
    adapter = fields.get("adapter")
    if isinstance(adapter, str) and adapter:
        record["adapter"] = normalize_adapter(adapter)
    outcome = fields.get("outcome")
    if isinstance(outcome, str):
        record["outcome"] = _token(outcome, "unknown")
    duration = fields.get("duration_ms")
    if isinstance(duration, (int, float)) and 0 <= float(duration) < 1_000_000_000:
        record["duration_ms"] = int(round(float(duration)))
    error_class = fields.get("error_class")
    if isinstance(error_class, str):
        record["error_class"] = allowed("error_class", error_class, "unknown")
    line = json.dumps(record, separators=(",", ":"), sort_keys=True)
    if SECRET.search(line):
        return json.dumps(
            {"error_class": "unknown", "level": "error", "operation": "log_redacted", "outcome": "failed"},
            separators=(",", ":"),
            sort_keys=True,
        )
    return line


def _token(value: object, fallback: str) -> str:
    if isinstance(value, str) and TOKEN.fullmatch(value) and not SECRET.search(value):
        return value
    return fallback
