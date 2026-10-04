# Cohort methodology — 2026.09.0

This document defines who can be included in pdoom.live cohort `cohort_2026_09`. It is a purposive, reviewed seed. It is not a census of AI researchers, not a random sample, and not a measure of what "the field" believes.

## Inclusion

A person needs one primary reason:

- `frontier_lab_researcher` — current or recent researcher or research leader at an organization that trains or steers frontier models.
- `frontier_model_author` — author of research that materially shaped frontier models, even if their current job is elsewhere.
- `frontier_safety_eval` — advanced-AI safety or evaluation researcher whose work is tied to frontier systems.
- `academic_forecasting` — academic or independent researcher whose published work materially affects public forecasting of frontier AI, including labor and governance scholars when that link is direct.
- `former_frontier_researcher` — former frontier-lab researcher who still publishes research or forecasts in public.

Research-organization leaders who are the public technical voice of a frontier lab can be included under `frontier_lab_researcher`. A general corporate executive title, by itself, is not enough.

## Exclusion

The following do not qualify:

- authorship of an arbitrary machine-learning paper;
- a name match in OpenAlex, Semantic Scholar, or OpenReview;
- employment in an AI-related company without a research, evaluation, or forecasting role;
- social-media audience size.

People can have more than one reason. The primary reason is the one stored on the person record.

## Identity rules

External identifiers are not typed in by the curator.

An OpenAlex author id is attached only when `pipeline/pdoom_pipeline/identity/resolve.py` accepts it:

- the display name matches exactly after accent-folding, punctuation stripping, and dropping of single-letter initials;
- and either one institution string matches a curator-supplied keyword, or the name is marked distinctive and there is exactly one exact-name candidate with at least three works.

`John Schulman` does not match `Jonathan Schulman`. Middle initials block a match when both names have one and they differ. A common name with two institution-matching records is left ambiguous. A distinctive name with several institution-matching OpenAlex profiles is accepted only when one profile has at least 25 works and at least three times the works of the next profile; that acceptance is medium confidence (`openalex_dominant_profile`), because split profiles are common and the smaller profiles are not merged into it. If two people would receive the same external id, neither keeps it. A profile whose institutions include a university named after the person (for example "Elon University") is not given high confidence.

ORCID is copied only from the accepted OpenAlex record. It is not searched by name.

OpenReview, Semantic Scholar, GitHub, Hugging Face, Bluesky, Mastodon, X, YouTube, and podcast identifiers stay empty unless a later collector confirms them from a structured field or a page already linked to the accepted identity. Unknown is the recorded state until then.

Claimed personal sites in the roster are leads. They are not external identities until a fetch confirms them.

## Roles and time

Affiliation roles are curator-reviewed and carry their own confidence. Titles move quickly. A medium or low role confidence means the person belongs in the cohort and the exact current title should not be displayed as certain.

Organization headquarters country is a property of the organization. It is not the person's nationality.

## Versioning

Cohort version `2026.09.0` is the reviewed roster in `pipeline/pdoom_pipeline/seed/` and `data/seed/cohort/v2026-09/`. Historical trends that use this cohort must cite that version. Adding or removing a person requires a new cohort version rather than a silent edit.

Cohort `2026.10.0` is that next version. It copies this membership and records additions in `data/seed/cohort/v2026-10/membership_diff.json`. The rules for the additions are in [cohort 2026.10.0](./COHORT_2026_10.md). Files in `v2026-09/` stay the historical roster.

## What this seed is for

The seed is the starting graph for source collection. Coverage expands by reviewed rules: new organization pages, coauthor links from already accepted OpenAlex ids, and confirmed profile links. It does not expand by scraping the web for similar names.
