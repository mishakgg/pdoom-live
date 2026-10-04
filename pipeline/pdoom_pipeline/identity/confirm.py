"""Confirm a platform profile only with a name match plus a corroborating link.

Name similarity is not enough. Joe does not match Joseph. A single-letter
initial does not expand to a given name. An organization account does not
become a person. Two people who would receive the same external id both lose it.
"""

from __future__ import annotations

from pdoom_pipeline.identity.names import name_key, same_person_name


def accepted_names(person: dict) -> list[str]:
    names = [person.get("display_name") or ""]
    names.extend(person.get("name_variants") or [])
    return [name for name in names if name]


def confirm_linked_profile(
    *,
    person: dict,
    profile_names: list[str],
    linked_from_owned_source: bool = False,
    profile_website: str | None = None,
    known_urls: set[str] | None = None,
) -> dict:
    """Return a decision. Accepted profiles still need a human before `human_verified`."""
    known = {url.rstrip("/") for url in (known_urls or set()) if url}
    website = (profile_website or "").rstrip("/")
    names = [name for name in profile_names if name and name.strip()]
    if not names:
        return _decision(False, "empty_profile_name", "low")
    matched = [name for name in names if any(same_person_name(name, candidate) for candidate in accepted_names(person))]
    if not matched:
        partial = _partial_overlap(names, accepted_names(person))
        reason = "name_similar_not_equal" if partial else "name_mismatch"
        return _decision(False, reason, "low", profile_name=names[0])
    corroborated = linked_from_owned_source or (website and website in known)
    if not corroborated:
        return _decision(False, "no_corroborating_link", "low", profile_name=matched[0])
    return _decision(True, "name_match_and_corroborating_link", "high", profile_name=matched[0])


def drop_duplicate_external_ids(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """If two people would share one external id, neither keeps it."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["namespace"], row["external_id"]), []).append(row)
    kept: list[dict] = []
    ambiguities: list[dict] = []
    for (namespace, external_id), group in groups.items():
        people = {row["person_id"] for row in group}
        if len(people) > 1:
            ambiguities.append(
                {
                    "kind": "duplicate_external_id",
                    "namespace": namespace,
                    "external_id": external_id,
                    "person_ids": sorted(people),
                    "reason": "the same external id was proposed for more than one person",
                }
            )
            continue
        kept.extend(group)
    return kept, ambiguities


def _partial_overlap(profile_names: list[str], person_names: list[str]) -> bool:
    profile_keys = [set(name_key(name)) for name in profile_names]
    person_keys = [set(name_key(name)) for name in person_names]
    for left in profile_keys:
        for right in person_keys:
            if left and right and left != right and (left & right):
                return True
    return False


def _decision(accepted: bool, reason: str, confidence: str, profile_name: str | None = None) -> dict:
    return {
        "accepted": accepted,
        "reason": reason,
        "confidence": confidence,
        "profile_name": profile_name,
        "review_state": "machine_validated" if accepted else "needs_review",
    }
