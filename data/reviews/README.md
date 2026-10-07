# Review decisions

Store `review-decisions/2.0.0` manifests here. Each entry includes its stored machine-input and accepted-claim snapshots. Legacy `1.0.0` files remain inspectable but cannot grant fresh human verification without re-review. A manifest is the append-only record of operator approvals, rejections, and corrections. Import atomically reconstructs review state only when the extracted statements and correction history match the bound snapshots. Keep the complete decision history.

Do not put credentials, session tokens, or private notes that are not meant for the repository in these files. Operator identifiers in a manifest are the reviewer labels recorded with each decision.

See `docs/CURATION.md`.
