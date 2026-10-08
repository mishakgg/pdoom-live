# AlgoPerf v0.5 single-trial research fixture

Source: MLCommons AlgoPerf v0.5 result archive, external tuning, Team 21 Distributed Shampoo submission, study 0, fastMRI PyTorch, trial 1. Archive commit `834b09b27ed24d50cb7cbe07f0c83c7f7dc2076f`; execution-code commit `4b01ee64c30dec442dd111abe31d40d80820fc70` is a distinct identity. Experiment datetime is unknown.

[Official publisher and results](https://mlcommons.org/benchmarks/algorithms/) explicitly licenses submissions and training logs under Apache License 2.0. [Original archive](https://github.com/mlcommons/algorithms_results_v0.5/tree/834b09b27ed24d50cb7cbe07f0c83c7f7dc2076f) and exact [LICENSE.md](LICENSE.md) are the source and applicable license. Retain this attribution, source links, license and modification notice in redistributions. No upstream root NOTICE was found in the inspected archive tree; this is a locally authored provenance notice, not a claimed upstream notice.

Copyright and other notices in the retained Apache license are unchanged. These third-party fixtures remain Apache-2.0 and are outside the repository data/CC0 area. The original training datasets, images, models and executable submission source are not included or covered by this fixture grant.

## Files and modifications

- `eval_measurements.csv`, `hparams.json` and `LICENSE.md` retain exact upstream bytes.
- `meta_data_0.curated.json` retains workload definitions, host/software and GPU configuration, seed and execution revision; it omits incidental utilization, temperature, network and memory telemetry.
- `flags_0.curated.json` retains run/workload/tuning/framework/compile/checkpoint configuration and source-code path strings as inert provenance. It omits generic local storage paths, debug/help and incidental logging flags. The reader never follows any source path or URL.
- Retained JSON value lexemes are unchanged. Derivative filenames and hashes deliberately differ from upstream JSON identities. `manifest.json` enumerates every omitted key and both source and local byte/Git/SHA-256 identities. A derivative hash is never represented as the upstream hash.

## Interpretation

This is a local independent parsing analysis of one published trial, not an official MLCommons aggregate score, leaderboard claim, endorsement or new benchmark submission. It retains 74 checkpoint observations and derives one first observed validation-target crossing. Checkpoints are not independent trials. The CSV `score` column is a raw source field equal to submission time for this trace, not the official cross-workload score.

Retrospective scoring code uses inclusive `>=` for higher-is-better SSIM; runtime workload predicates use strict `>` for validation and test, and the runner can stop after both goals have previously been reached. Those semantics are distinct. The pilot selects by validation only and does not emulate runtime termination, interpolate between evaluations or infer exhausted budgets from truncated data. Submission, evaluation, logging and total duration clocks remain separate. No FLOPs, energy, full research cost, efficiency ratio, scaling law or p(doom) is inferred.
