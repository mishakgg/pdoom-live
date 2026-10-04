"""Collection order for cohort 2026.09.0.

The score is a fetch budget. It is not a ranking of researchers or of their importance.
"""

from __future__ import annotations

PRIORITY_LIMIT = 120


def priority_rows(people: list[dict], *, lead_slugs: set[str], covered_slugs: set[str]) -> list[dict]:
    ranked = []
    for person in people:
        reasons = set(person.get("inclusion_reasons") or [person.get("inclusion_reason")])
        focus = person.get("focus") or ""
        score = 0
        if reasons & {"frontier_safety_eval", "academic_forecasting", "former_frontier_researcher"}:
            score += 3
        elif person.get("inclusion_reason") == "frontier_lab_researcher":
            score += 2
        elif person.get("inclusion_reason") == "frontier_model_author":
            score += 1
        if focus in {"safety", "governance", "economics"}:
            score += 2
        if person.get("name_distinctiveness") == "high":
            score += 1
        if person["slug"] not in covered_slugs:
            score += 1
        if person["slug"] in lead_slugs:
            score += 2
        ranked.append(
            {
                "person_slug": person["slug"],
                "collection_score": score,
                "forced_by_known_longform_lead": person["slug"] in lead_slugs,
                "note": "Collection priority only. Not a public ranking of importance.",
            }
        )
    ranked.sort(key=lambda row: (-row["collection_score"], row["person_slug"]))
    chosen = [row for row in ranked if row["forced_by_known_longform_lead"]]
    seen = {row["person_slug"] for row in chosen}
    for row in ranked:
        if row["person_slug"] in seen:
            continue
        if len(chosen) >= PRIORITY_LIMIT:
            break
        chosen.append(row)
        seen.add(row["person_slug"])
    chosen.sort(key=lambda row: (-row["collection_score"], row["person_slug"]))
    return chosen[:PRIORITY_LIMIT]


def priority_table(
    people: list[dict],
    *,
    lead_slugs: set[str],
    covered_slugs: set[str],
    missing_nonacademic_slugs: set[str] | None = None,
    limit: int = PRIORITY_LIMIT,
) -> list[dict]:
    """Score every person for a fetch budget.

    The score is not a ranking of people. `in_fetch_budget` marks who would be
    fetched first. Everyone else stays visible as not selected.
    """
    missing = missing_nonacademic_slugs or set()
    rows = []
    for person in people:
        reasons = set(person.get("inclusion_reasons") or [person.get("inclusion_reason")])
        focus = person.get("focus") or ""
        score = 0
        if reasons & {"frontier_safety_eval", "academic_forecasting", "former_frontier_researcher"}:
            score += 3
        elif person.get("inclusion_reason") == "frontier_lab_researcher":
            score += 2
        elif person.get("inclusion_reason") == "frontier_model_author":
            score += 1
        if focus in {"safety", "governance", "economics"}:
            score += 2
        if person.get("name_distinctiveness") == "high":
            score += 1
        if person["slug"] not in covered_slugs:
            score += 1
        if person["slug"] in lead_slugs:
            score += 2
        if person["slug"] in missing:
            score += 2
        rows.append(
            {
                "person_slug": person["slug"],
                "collection_score": score,
                "forced_by_known_longform_lead": person["slug"] in lead_slugs,
                "missing_nonacademic_source": person["slug"] in missing,
                "ordering_kind": "fetch_budget",
                "note": "Collection priority only. Not a public ranking of importance.",
            }
        )
    rows.sort(key=lambda row: (-row["collection_score"], row["person_slug"]))
    for index, row in enumerate(rows):
        row["in_fetch_budget"] = index < limit
        row["fetch_budget_rank"] = index + 1
    return rows
