"""Add verified identities and sources without attaching one id to two people."""

from __future__ import annotations

import hashlib
import re

COLLECTABLE_METHODS = {"rss_feed", "openalex_api", "github_api", "arxiv_api"}


def merge_records(existing: list[dict], additions: list[dict], *, key_fields: tuple[str, ...]) -> tuple[list[dict], list[dict]]:
    rows = list(existing)
    index: dict[tuple, dict] = {}
    for row in rows:
        index.setdefault(tuple(row.get(field) for field in key_fields), row)
    ambiguities = []
    for addition in additions:
        key = tuple(addition.get(field) for field in key_fields)
        current = index.get(key)
        if current is None:
            rows.append(addition)
            index[key] = addition
            continue
        if current.get("person_id") == addition.get("person_id") and current.get("owner_person_id") == addition.get("owner_person_id"):
            continue
        left = current.get("person_id") or current.get("owner_person_id")
        right = addition.get("person_id") or addition.get("owner_person_id")
        if left != right:
            ambiguities.append(
                {
                    "kind": "duplicate_external_id" if key_fields == ("namespace", "external_id") else "duplicate_source_url",
                    "namespace": addition.get("namespace"),
                    "external_id": addition.get("external_id"),
                    "canonical_url": addition.get("canonical_url"),
                    "person_ids": [left, right],
                    "reason": "enrichment_conflict",
                }
            )
    return rows, ambiguities


def identity_record(*, person_id: str, namespace: str, external_id: str, canonical_url: str, handle: str | None, verification_method: str, confidence: str, verified_at: str, evidence: dict) -> dict:
    digest = hashlib.sha256(f"{namespace}:{external_id}".encode("utf-8")).hexdigest()[:12]
    safe = re.sub(r"[^A-Za-z0-9._@-]", "-", external_id)[:40]
    return {
        "id": f"eid:{person_id}:{namespace}:{safe}-{digest}",
        "person_id": person_id,
        "namespace": namespace,
        "external_id": external_id,
        "canonical_url": canonical_url,
        "handle": handle,
        "verification_method": verification_method,
        "confidence": confidence,
        "verified_at": verified_at,
        "review_state": "machine_validated" if confidence == "high" else "needs_review",
        "evidence": evidence,
    }


def source_record(*, person_id: str, source_type: str, name: str, canonical_url: str, platform: str, collection_method: str, enabled: bool, verification_method: str, rights_notes: str) -> dict:
    collectible = enabled and collection_method in COLLECTABLE_METHODS
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"src:{person_id}:{source_type}:{digest}",
        "source_type": source_type,
        "name": name,
        "canonical_url": canonical_url,
        "platform": platform,
        "owner_person_id": person_id,
        "owner_organization_id": None,
        "collection_method": collection_method,
        "rights_notes": rights_notes,
        "enabled": enabled,
        "continuously_collectible": collectible,
        "review_state": "machine_validated",
        "verification_method": verification_method,
    }
