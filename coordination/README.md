# Coordination record

Agent 7 owns this directory. It is the repository-visible coordination record for the six implementation workstreams.

The six agents keep ownership of their implementations. This directory does not change forecast semantics, identity rules, review policy, schema, or UI.

## Files

| Path | Role |
| --- | --- |
| `checkpoint.json` | Restart point. Read this first on every review. |
| `dependency-map.json` | Shared contracts, dependency edges, and known conflicts. |
| `status/status-<review-id>.md` | Uniquely named human status for one review. |
| `manifests/manifest-<review-id>.json` | Uniquely named machine manifest for one review. |

`checkpoint.json` names the latest status and manifest. Older reviews stay in place.

## Review lock

The hourly timer runs only while this agent is idle. A review still records `run_lock` in `checkpoint.json` before it changes the integration branch, and clears that lock in the same checkpoint update. A lock younger than two hours means another review is in progress and must not start a second integration.

## Integration candidate

`manifests/manifest-<review-id>.json` is authoritative for the candidate it names. A later main or pull-request head does not change an older manifest. A new candidate gets a new manifest and a new integration commit.
