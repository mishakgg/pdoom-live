"""Content hashes cover normalized source payload, not observation time."""

from __future__ import annotations

import hashlib
import json


def content_hash(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def observation_fingerprint(*, title: str | None, texts: list[str], published_at: str | None, upstream_version: str | None) -> str:
    return content_hash(
        {
            "title": title or "",
            "texts": texts,
            "published_at": published_at or "",
            "upstream_version": upstream_version or "",
        }
    )
