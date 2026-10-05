"""OpenAlex identity resolution.

A record is accepted only for an exact name match plus institution corroboration,
or for one exact match of a distinctive name. Similar names are never merged.
A different ORCID stays on its own name. Two people who share a display name
and carry different OpenReview profile ids stay separate. A missing ORCID or
OpenReview profile id does not match the nearest similar name. ORCID and
OpenReview ids are copied only from the accepted OpenAlex record.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from pdoom_pipeline.identity.names import name_key

_OPENREVIEW_PROFILE = re.compile(r"^~[A-Za-z0-9_-]{1,128}$")

AI_TOPIC_HINTS = ("machine learning", "artificial intelligence", "computer science", "neural", "language model")


def institution_matches(institution_name: str, keywords: list[str]) -> bool:
    inst_tokens = name_key(institution_name)
    if not inst_tokens:
        return False
    for keyword in keywords:
        kw_tokens = name_key(keyword)
        if len("".join(kw_tokens)) < 3:
            continue
        if _contains_sequence(inst_tokens, kw_tokens):
            return True
    return False


def _contains_sequence(haystack: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(haystack[index : index + width] == needle for index in range(len(haystack) - width + 1))


def _institution_names(record: dict) -> list[str]:
    names: list[str] = []
    for affiliation in record.get("affiliations") or []:
        institution = affiliation.get("institution") or {}
        if institution.get("display_name"):
            names.append(institution["display_name"])
    for institution in record.get("last_known_institutions") or []:
        if isinstance(institution, dict) and institution.get("display_name"):
            names.append(institution["display_name"])
    return names


def _compatible_name(person: dict, display_name: str) -> bool:
    candidates = [person["display_name"], *(person.get("name_variants") or [])]
    return any(_names_compatible(candidate, display_name) for candidate in candidates)


def _names_compatible(left: str, right: str) -> bool:
    left_tokens = normalize_tokens(left)
    right_tokens = normalize_tokens(right)
    left_key = tuple(token for token in left_tokens if len(token) > 1)
    right_key = tuple(token for token in right_tokens if len(token) > 1)
    if not left_key or left_key != right_key:
        return False
    left_initials = [token for token in left_tokens if len(token) == 1]
    right_initials = [token for token in right_tokens if len(token) == 1]
    if left_initials and right_initials and left_initials != right_initials:
        return False
    return True


def normalize_tokens(name: str) -> list[str]:
    return name_key_tokens(name)


def name_key_tokens(name: str) -> list[str]:
    from pdoom_pipeline.identity.names import normalize_name

    return normalize_name(name).split()


def _normalized_name_match(person: dict, display_name: str) -> bool:
    from pdoom_pipeline.identity.names import normalize_name

    target = normalize_name(display_name)
    if not target:
        return False
    candidates = [person.get("display_name") or "", *(person.get("name_variants") or [])]
    return any(normalize_name(candidate) == target for candidate in candidates if candidate)


def _exact_records(person: dict, results: list[dict]) -> list[dict]:
    """Exact names stay eligible. A similar name joins them only with the same ORCID.

    A missing ORCID never promotes the nearest similar name into a match.
    """
    strict: list[dict] = []
    similar: list[dict] = []
    for record in results:
        display_name = str(record.get("display_name") or "")
        if not _compatible_name(person, display_name):
            continue
        if _normalized_name_match(person, display_name):
            strict.append(record)
        elif _orcid(record):
            similar.append(record)
    if not strict:
        return similar
    orcids = {value for value in (_orcid(record) for record in strict) if value}
    if len(orcids) != 1 or any(_orcid(record) is None for record in strict):
        return strict
    only = next(iter(orcids))
    return strict + [record for record in similar if _orcid(record) == only]


def choose_openalex_author(person: dict, results: list[dict]) -> dict:
    exact = _exact_records(person, results)
    keywords = list(person.get("institution_keywords") or [])
    corroborated = []
    for record in exact:
        names = _institution_names(record)
        if any(institution_matches(name, keywords) for name in names):
            corroborated.append(record)
    if len(corroborated) == 1:
        return _accept(corroborated[0], _confidence_for(person, corroborated[0], "high"), "openalex_exact_name_and_institution", exact)
    if len(corroborated) > 1:
        distinct_orcids = {value for value in (_orcid(record) for record in corroborated) if value}
        if len(distinct_orcids) > 1:
            return _ambiguous("distinct_orcids", exact)
        distinct_profiles = {value for value in (_openreview_id(record) for record in corroborated) if value}
        if len(distinct_profiles) > 1:
            return _ambiguous("distinct_openreview_profiles", exact)
        dominant = _dominant_profile(person, corroborated)
        if dominant is not None:
            return _accept(dominant, "medium", "openalex_dominant_profile", exact)
        return _ambiguous("multiple_institution_matches", exact)
    distinctive = person.get("name_distinctiveness") == "high"
    if distinctive and len(exact) == 1 and int(exact[0].get("works_count") or 0) >= 3:
        return _accept(exact[0], "medium", "openalex_unique_exact_name", exact)
    if len(exact) > 1:
        return _ambiguous("multiple_exact_name_matches_without_unique_institution", exact)
    return {"status": "not_found", "candidates": [_candidate_summary(record) for record in exact]}


def _dominant_profile(person: dict, records: list[dict]) -> dict | None:
    """Pick a split OpenAlex profile only when one record clearly dominates."""
    if person.get("name_distinctiveness") != "high" or len(records) < 2:
        return None
    ordered = sorted(records, key=lambda record: int(record.get("works_count") or 0), reverse=True)
    top = int(ordered[0].get("works_count") or 0)
    second = int(ordered[1].get("works_count") or 0)
    if top < 25 or second * 3 > top:
        return None
    return ordered[0]


def _confidence_for(person: dict, record: dict, proposed: str) -> str:
    given = name_key(person.get("given_name") or "")
    family = name_key(person.get("family_name") or "")
    for institution in _institution_names(record):
        tokens = set(name_key(institution))
        if "university" in tokens and (set(given) & tokens or set(family) & tokens):
            return "medium"
    return proposed


def _accept(record: dict, confidence: str, method: str, exact: list[dict]) -> dict:
    orcid = _orcid(record)
    openalex_id = str(record.get("id") or "").rstrip("/").split("/")[-1]
    return {
        "status": "accepted",
        "confidence": confidence,
        "verification_method": method,
        "openalex_id": openalex_id,
        "orcid": orcid,
        "openreview_id": _openreview_id(record),
        "matched_name": record.get("display_name"),
        "matched_institutions": _institution_names(record),
        "works_count": record.get("works_count"),
        "cited_by_count": record.get("cited_by_count"),
        "candidate_count": len(exact),
        "rejected_candidate_count": max(len(exact) - 1, 0),
    }


def _ambiguous(reason: str, exact: list[dict]) -> dict:
    return {
        "status": "ambiguous",
        "reason": reason,
        "candidates": [_candidate_summary(record) for record in exact],
    }


def _candidate_summary(record: dict) -> dict:
    return {
        "openalex_id": str(record.get("id") or "").rstrip("/").split("/")[-1],
        "display_name": record.get("display_name"),
        "openreview_id": _openreview_id(record),
        "institutions": _institution_names(record),
        "works_count": record.get("works_count"),
    }


def _orcid(record: dict) -> str | None:
    raw = record.get("orcid") or (record.get("ids") or {}).get("orcid")
    if not raw:
        return None
    text = str(raw).rstrip("/").split("/")[-1]
    if not text or text.lower() == "none":
        return None
    return text


def _openreview_id(record: dict) -> str | None:
    """Profile ids look like ``~First_Last1``. A URL is reduced to that id."""
    raw = record.get("openreview_id") or record.get("openreview")
    if not raw:
        ids = record.get("ids")
        if isinstance(ids, dict):
            raw = ids.get("openreview")
    if not raw:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    if "://" in text or text.lower().startswith("openreview.net"):
        parsed = urlparse(text if "://" in text else f"https://{text}")
        query_id = parse_qs(parsed.query).get("id")
        text = query_id[0] if query_id else parsed.path.rstrip("/").split("/")[-1]
    text = unquote(text).strip()
    if not _OPENREVIEW_PROFILE.fullmatch(text):
        return None
    return text


def dedupe_openalex_ids(decisions: dict[str, dict]) -> tuple[dict[str, dict], list[dict]]:
    """If two people receive one OpenAlex id, neither keeps it."""
    owners: dict[str, list[str]] = {}
    for person_id, decision in decisions.items():
        if decision.get("status") == "accepted" and decision.get("openalex_id"):
            owners.setdefault(decision["openalex_id"], []).append(person_id)
    conflicts = []
    cleaned = {key: dict(value) for key, value in decisions.items()}
    for openalex_id, person_ids in owners.items():
        if len(person_ids) < 2:
            continue
        conflicts.append({"openalex_id": openalex_id, "person_ids": person_ids, "reason": "duplicate_external_id"})
        for person_id in person_ids:
            cleaned[person_id] = {
                "status": "ambiguous",
                "reason": "duplicate_external_id",
                "openalex_id": None,
                "candidates": [{"openalex_id": openalex_id, "person_ids": person_ids}],
            }
    return cleaned, conflicts
