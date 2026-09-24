"""Author/speaker attribution is separate from a name that only appears in text."""

from __future__ import annotations

import re

from pdoom_pipeline.identity.names import name_key


def assign_participants(author_names: list[str], body_text: str, people: list[dict]) -> list[dict]:
    participants: list[dict] = []
    author_ids: set[str] = set()
    for name in author_names:
        person_id = unique_person_id(name, people)
        if person_id:
            author_ids.add(person_id)
        participants.append(
            {
                "name": name,
                "person_id": person_id,
                "role": "author",
                "attribution_method": "source_author_field",
                "confidence": "high" if person_id else "medium",
            }
        )
    for person in people:
        if person["id"] in author_ids:
            continue
        if mentioned(body_text, person["display_name"]):
            participants.append(
                {
                    "name": person["display_name"],
                    "person_id": person["id"],
                    "role": "mentioned",
                    "attribution_method": "name_occurrence_in_body",
                    "confidence": "low",
                }
            )
    return participants


def unique_person_id(name: str, people: list[dict]) -> str | None:
    key = name_key(name)
    if not key:
        return None
    matches = []
    for person in people:
        keys = [name_key(person["display_name"])]
        keys.extend(name_key(variant) for variant in person.get("name_variants") or [])
        if key in keys:
            matches.append(person["id"])
    if len(matches) == 1:
        return matches[0]
    return None


def mentioned(body_text: str, display_name: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(display_name) + r"(?!\w)"
    return re.search(pattern, body_text or "", flags=re.IGNORECASE) is not None
