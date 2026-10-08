# Robotics and physical-world capability

## Follow-up qualification: 8 October 2026

For RP004 / RP-A6 / RP-P4 and RP002 / RP-A4 / RP-P2, the [physical-world and inference follow-up](followups/physical-inference-comparability.md) ([JSON](../../../data/evidence-program/research/followups/physical-inference-comparability.json)) records completed bounded selection/version, whitepaper and snapshot metadata checks. Complete cohort/metric reconciliation, exclusion application, scale and duration holds remain. The original catalog and review below remain historical.

Reviewed 8 October 2026 against [`ee3e0d2`](https://github.com/mishakgg/pdoom-live/commit/ee3e0d2fa2c5a594fec276f08f4c985147e9f130). This is the ninth separately logged sequential research review. Publication of this guide does not admit any source or enable a collector.

## Result and scope

Five new candidate source families complement one another. Physical contest attempts, policy preferences, progress labels, jobs/rewards, episode/item outcomes, recovery attempts and operating exposure remain separate measurements. No universal robot capability score or p(doom) conversion is supported.

The [machine-readable catalog](../../../data/evidence-program/research/robotics-physical.json) contains 35 artifact references, 19 qualified findings, seven corrections, eight next actions and six self-contained follow-up prompts. The frozen 64-family inventory, all eight earlier research catalogs, prior readers and canonical schemas are unchanged.

Implemented: one bounded offline **manually curated BARN 2024 Table II validator/normalizer**, preserving all 60 displayed results, 12 course summaries and four team summaries. It is **not an HTML scraper**, physical reproduction or operational collector. A separately licensed CC BY 4.0 table derivative is the only new source-derived fixture. The full report, videos, trajectories and other source datasets are not bundled.

## Top additions

| Rank | Collection | Why start here | Main hold |
| --- | --- | --- | --- |
| 1 | BARN 2024 | Versioned small physical table makes denominator fidelity testable | Display positions are not native run IDs; published averages and credit need separate meanings |
| 2 | RoboArena | Session metadata separates preferences, partial progress and binary success | Raw duration units, scale bridge and export exclusion membership unresolved |
| 3 | RRC2020 | Indexed historical physical jobs with explicit development/evaluation context | Noncommercial/share-alike compatibility and actual index schema/rows unverified |

PhAIL adds detailed episode/items but cohort and intervention definitions remain in conflict. STRANDS adds sustained operation with requested assistance explicitly allowed by its lifetime metric, while data/sheet reuse rights remain unknown. Ranking is readiness for bounded research, not robot performance or rights clearance.

## Baseline and overlap review

The [source priorities](../source_priorities.md) and [frozen inventory](../../../data/evidence-program/source_inventory.json) were read at the exact reviewed commit. All eight prior catalogs, 43 collections and 327 artifact references were compared in 40 candidate-by-catalog semantic cells. Family, artifact, underlying study and measurement relationships were considered separately. No same underlying study or exact artifact was established with these catalogs. This is a scoped negative finding, not proof of universal non-overlap or statistical independence.

| Prior catalog | Collections | Artifacts | Exact Git blob |
| --- | ---: | ---: | --- |
| [chinese-safety-evaluations](chinese-safety-evaluations.md) | 8 | 49 | `e205499dfaabf8769582c0a2b33859bb4564bf2f` |
| [adoption-productivity](adoption-productivity.md) | 5 | 41 | `fbd2337a06d86c04d3092ba1b63a2e815b3b7d1c` |
| [organizational-safety](organizational-safety.md) | 5 | 50 | `14e560889f729f14bd2e0c0290ac51bdcc32d1c6` |
| [open-model-diffusion](open-model-diffusion.md) | 5 | 37 | `686e7a69a3020215e21afd984e6b3a4e7eb2e399` |
| [concentration-dependencies](concentration-dependencies.md) | 5 | 28 | `e98df02f9c42060decf2d157f1b4fa7e7b18ad1c` |
| [historical-capability-backfills](historical-capability-backfills.md) | 5 | 46 | `41ed220a48e676acf2bd691e3309a9105ef834f9` |
| [scientific-progress](scientific-progress.md) | 5 | 46 | `fdce2e6cb61147704c32bb7e300b2b331e7b6c0e` |
| [persuasion-information](persuasion-information.md) | 5 | 30 | `d06a5acc63d629db60f83a3d0035d516d017e970` |

A-Lab in the scientific-progress review is adjacent physical automation, but materials-synthesis campaign/target/recipe denominators do not identify these navigation/manipulation runs. Historical IPC planning is an adjacent topic, not a duplicate robot contest. Hugging Face hosting, model-family names and frontend human preference labels do not turn robot trials into open-model metadata or persuasion experiments. The two earlier correction ledgers were also reviewed.

All five collections are proposed new families with `inventory_source_id=null`. GL016 is a contextual DeepMind model-card connection; GL034 is possible secondary re-reporting; GL039/GL040 support scholarly discovery and version provenance. None justifies assigning those existing family IDs to an independent robot dataset or counting a paper host as new experimental evidence.

## Five primary collections

### RP001 · BARN Challenge physical navigation

Regime: `staged_physical_contest`. Candidate remains unadmitted.

**Coverage and cadence**

- Family editions: 2022–2026 annual organizer collection
- Selected edition: 2024
- Event dates: ["2024-05-15", "2024-05-16"]
- Report published: 2024-07-02
- Report version: 2407.01862v1
- Date roles separate: Yes

Cadence: Annual events; selected v1 is a fixed historical report, not a live results feed.

Access/export: Public versioned HTML Table II. This integration transcribes and validates a bounded curated table; it does not implement an HTML scraper or run the simulation harness.

**Hardware, environment and human involvement**

- Platform: Clearpath Jackal
- Sensor: Hokuyo 270-degree 2D LiDAR
- Environment: Three obstacle courses made with cardboard boxes
- Hardware instance: Unknown / not established
- Regime: Physical contest, separate from Table I simulation
- Robots available: 2
- Success rule: Complete the course without collision or human intervention; neither prohibition supplies a measured intervention count.
- Setup window minutes: 20
- Timed window minutes: 20
- Reset count: Unknown / not established
- Reset duration s: Unknown / not established
- Practice attempt count: Unknown / not established
- Observed intervention count: Unknown / not established
- Exact checkpoint: Unknown / not established
- Unknown reason: The table reports timed outcomes, not comprehensive reset, practice, intervention or checkpoint telemetry.
- Window scope: Per team per course, covering setup then five timed runs collectively; not a 20-minute timeout per run.

**Observed examples and measurements**

- Observed table row: `{"team": "LiCS-KI", "course": 1, "reported_values": ["32", "31", "32", "27", "30"], "time_unit": "seconds"}`
  - Five displayed positions; chronological order unverified.
  - Locator: Table II, LiCS-KI, Course 1. References: `rp001_report`.
- Derived all reported attempts: `{"LiCS-KI": {"successes": 10, "denominator": 15}, "MLDA_EEE": {"successes": 5, "denominator": 15}, "AIMS": {"successes": 5, "denominator": 15}, "EIT-NUS": {"successes": 0, "denominator": 15}}`
  - Computed from all 60 published numeric/X cells; failures stay reported failed attempts, with null time and unknown cause.
  - Locator: Table II, all four teams and three courses. References: `rp001_report`.
- Reported credited contest results: `{"LiCS-KI": {"successes": 6, "denominator": 9}, "MLDA_EEE": {"successes": 5, "denominator": 9}, "AIMS": {"successes": 5, "denominator": 9}, "EIT-NUS": {"successes": 0, "denominator": 9}}`
  - Contest denominator is selected credit, not total attempts performed.
  - Locator: Table II, success-rate column and physical scoring rule. References: `rp001_report`.

**Verified findings and qualifications**

- Table II contains 60 displayed attempts: four teams × three courses × five positions. X denotes failure, not missingness, zero time or a diagnosed collision. References: `rp001_report`.
- LiCS-KI course-two values have a tie at 37 seconds around the third-fastest selection boundary. Credited success count is known; the exact displayed failed/successful row membership must not be invented. References: `rp001_report`.
- LiCS-KI published course averages are 30 and 35 seconds for courses one and two. These agree with rounded all-five means 30.4 and 35, not fastest-three means 88/3 and 98/3 seconds; preserve original averages separately. References: `rp001_report`.
- From printed integer times, MLDA_EEE and AIMS means are 78.6 and 108.6 seconds; paper rounded means are 79 and 109; later organizer page reports 78.8 and 108.8. Unreported precision or another cause is possible but unverified; preserve each assertion with edition/artifact identity. References: `rp001_report`, `rp001_organizer`.

**Limitations and duplicate evidence**

- Four participating teams and three selected courses are a small contest population; no field-fleet reliability inference.
- All 60 displayed results are not necessarily every attempt ever performed; practice and reset exposure are unmeasured.
- Displayed slash positions are not established chronological trial IDs. Exact failure causes and timestamps are unknown.
- Success-first/top-three contest credit differs from all reported attempts; tied times can leave credited row membership ambiguous.
- Published course means remain source assertions and are not overwritten by derived fastest-three means.
- Later editions change courses and timing/scoring rules; no cross-year pooling.
- Four physical finalists were selected from six simulation entrants; course-specific fine-tuning and travel selection limit generalization.
- Organizer ranking, paper and team reports may repeat the same event.
- Simulation Table I is a different regime, not extra physical attempts.
- A changed or reordered future table cannot be joined as identical trials solely by display position.

**Artifact access, version and rights**

- `rp001_report`: [BARN 2024 organizer report](https://arxiv.org/html/2407.01862v1). Version: 2407.01862v1. Access: primary documentation observed.
  - Rights: CC-BY-4.0. This exact v1 report is CC BY 4.0; attribution and derivative-table notice accompany the bounded fixture. This does not license website text, videos or other environment assets.
  - [Rights evidence](https://arxiv.org/abs/2407.01862v1).
- `rp001_organizer`: [Official annual collection](https://people.cs.gmu.edu/~xiao/Research/BARN_Challenge/BARN_Challenge26.html). Version: unversioned/unknown. Access: indexed primary text observed live page timeout.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp001_harness`: [Official simulation harness reference](https://github.com/Daffan/the-barn-challenge/tree/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83). Version: bf5a226f6088ec96bf0d2dbee3253a8ea6119b83. Access: primary documentation observed.
  - Rights: MIT. MIT software terms do not establish physical execution or license all linked assets.
  - [Rights evidence](https://github.com/Daffan/the-barn-challenge/blob/bf5a226f6088ec96bf0d2dbee3253a8ea6119b83/LICENSE).

### RP002 · RoboArena distributed physical evaluation

Regime: `episodic_physical_comparison`. Candidate remains unadmitted.

**Coverage and cadence**

- Paper first published: 2025-06
- Selected snapshot: 2026-07-17
- Earlier snapshot: 2026-02-03
- Sessions: 3883
- Policy episodes: 10783
- Videos: 27148
- Count units separate: Yes
- July dataset commit: 7931db81f3f6a48a3245427f7213a4c461f92ccc
- February dataset commit: 1e7e7d092bf21eadec5816cc6603476cbe1eee10
- Latest verified paper: 2506.18123v2
- Latest paper publication: 2025-11-29
- February release last modified: 2026-02-04T20:52:35Z

Cadence: Dated snapshots; fixed future publication schedule unverified.

Access/export: Read small public YAML manifest/session files and dataset-card metadata individually. No MP4, NPZ or trajectory archive downloaded; viewer processing failure is not an evidence count.

**Hardware, environment and human involvement**

- Platform: Franka Panda 7DoF with Robotiq 2F-85
- Environment: Distributed evaluator-selected scenes/tasks, closely matched within comparison
- Exact checkpoint: Unknown / not established
- Policy name is checkpoint: No
- Cameras: Wrist ZED Mini and external ZED 2 cameras
- Task selection: Human evaluators select task and scene
- Judgment: Preference and progress labels are evaluator judgments
- Scene preparation: Human setup/reset work occurs outside episode metadata
- Reset count: Unknown / not established
- Reset duration s: Unknown / not established
- Comprehensive intervention count: Unknown / not established

**Observed examples and measurements**

- Observed selected session: `{"session_date": "2025-10-17", "task": "Open the fridge door", "preference": "TIE", "policies": ["paligemma_fast_droid", "paligemma_fast_specialist_droid"], "binary_success": [0, 0], "partial_success_raw": [0.1, 0.1], "partial_success_scale": null, "duration_raw": [399, 399], "duration_unit": null, "exact_checkpoints": [null, null]}`
  - Personal evaluator information omitted. Partial scale and duration units unverified.
  - Locator: Session metadata: task, preference and policy outcome fields. References: `rp002_session`.

**Verified findings and qualifications**

- Manifest reports 3,883 sessions and 10,783 policy episodes; card reports 27,148 videos. Multiple views are not additional independent trials. References: `rp002_manifest`, `rp002_snapshot`.
- The exact selected session YAML is byte-identical across pinned February and July releases. The file has no copy marker; byte equality establishes one overlap without proving whole-release membership. References: `rp002_session`, `rp002_february`.
- A checked-in notice describes exclusions from 2 April 2026; current Home/Results source comments out the notice imports and rendering. Neither live display nor July-export filtering is established. Do not retain personal evaluator details. References: `rp002_integrity`, `rp002_home_source`, `rp002_results_source`.
- Paper v1/v2 describes progress on a 0–100 scale, while the current UI renders partial_success × 100 as percent. This supports fractional UI representation; linkage from archived YAML to current API schema remains unverified. Preserve raw 0.1; no normalized progress claim. References: `rp002_paper`, `rp002_paper_v2`, `rp002_progress_ui`.

**Limitations and duplicate evidence**

- Preference tie, partial progress and binary success are separate outcomes.
- Sample raw duration 399 has unverified units; do not label seconds or infer hours of operation.
- Paper progress scale and sampled 0.1 values require a documented scale bridge before normalization.
- Evaluator-selected tasks/scenes are not representative of all deployment work.
- Policies are named but exact model/checkpoint identity is not established by a name alone.
- The integrity component is checked in but its Home/Results imports and rendering are commented out at the pinned current revision. Live display and snapshot exclusion implementation are unverified.
- The exact sampled session YAML is byte-identical across the two pinned snapshots; it has no copy marker. This proves one overlapping record, not all-release membership.
- Deduplicate stable session/episode identities and retain revisions, never count views/videos as trials.
- Original paper, site leaderboard and snapshots may report overlapping evidence; exclusion state is version-specific.

**Artifact access, version and rights**

- `rp002_site`: [RoboArena project](https://robo-arena.github.io/). Version: unversioned/unknown. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp002_paper`: [Original paper v1](https://arxiv.org/html/2506.18123v1). Version: 2506.18123v1. Access: primary documentation observed.
  - Rights: CC-BY-4.0. Paper license only; neither model weights nor every hosted asset inherits it.
- `rp002_snapshot`: [July dataset snapshot](https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026/blob/7931db81f3f6a48a3245427f7213a4c461f92ccc/README.md). Version: 7931db81f3f6a48a3245427f7213a4c461f92ccc. Access: primary documentation observed.
  - Rights: MIT. Dataset card declares MIT for this release; privacy and exact checkpoint rights remain separate.
- `rp002_manifest`: [July global manifest](https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026/blob/7931db81f3f6a48a3245427f7213a4c461f92ccc/global_metadata.yaml). Version: 7931db81f3f6a48a3245427f7213a4c461f92ccc. Access: primary documentation observed.
  - Rights: MIT. Covered by dataset-card declaration, not a separately inspected license for model checkpoints.
  - [Rights evidence](https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026/blob/7931db81f3f6a48a3245427f7213a4c461f92ccc/README.md).
- `rp002_session`: [One public session metadata reference](https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026/blob/7931db81f3f6a48a3245427f7213a4c461f92ccc/evaluation_sessions/00008df3-4cb6-45ce-a6de-1d98a755146a/metadata.yaml). Version: 7931db81f3f6a48a3245427f7213a4c461f92ccc. Access: primary documentation observed.
  - Rights: MIT. Dataset-card declaration; only task/outcome fields are summarized, personal evaluator fields omitted.
  - [Rights evidence](https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026/blob/7931db81f3f6a48a3245427f7213a4c461f92ccc/README.md).
  - SHA-256 `5dc0139c38d945becdb1c6064525bbe00169d1048b3c2db52e48f758d347823f`; scope: Exact acquired UTF-8 source file bytes. Source bytes are not in this repository.
- `rp002_february`: [Earlier overlapping release](https://huggingface.co/datasets/RoboArena/DataDump_02-03-2026/blob/1e7e7d092bf21eadec5816cc6603476cbe1eee10/README.md). Version: 1e7e7d092bf21eadec5816cc6603476cbe1eee10. Access: primary documentation observed.
  - Rights: MIT. Earlier dataset-card declaration; independent model/media rights are not established.
- `rp002_integrity`: [Versioned benchmark integrity notice](https://github.com/robo-arena/robo-arena.github.io/blob/2ce29abe69424385d0ebc8d3222698d82a3008db/src/components/BenchmarkIntegrityNotice.jsx). Version: 2ce29abe69424385d0ebc8d3222698d82a3008db. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp002_paper_v2`: [Latest verified paper v2](https://arxiv.org/html/2506.18123v2). Version: 2506.18123v2. Access: primary documentation observed.
  - Rights: CC-BY-4.0. Version-specific paper license, separate from dataset/model rights.
- `rp002_home_source`: [Home source with notice commented out](https://github.com/robo-arena/robo-arena.github.io/blob/2ce29abe69424385d0ebc8d3222698d82a3008db/src/pages/Home.jsx#L10). Version: 2ce29abe69424385d0ebc8d3222698d82a3008db. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp002_results_source`: [Results source with notice commented out](https://github.com/robo-arena/robo-arena.github.io/blob/2ce29abe69424385d0ebc8d3222698d82a3008db/src/pages/ResultsPage.jsx#L192). Version: 2ce29abe69424385d0ebc8d3222698d82a3008db. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp002_progress_ui`: [Progress rendering source](https://github.com/robo-arena/robo-arena.github.io/blob/2ce29abe69424385d0ebc8d3222698d82a3008db/src/components/EvaluationCard.jsx#L128-L140). Version: 2ce29abe69424385d0ebc8d3222698d82a3008db. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.

### RP003 · TriFinger / Real Robot Challenge 2020

Regime: `physical_development_and_evaluation_jobs`. Candidate remains unadmitted.

**Coverage and cadence**

- Challenge period: 2020-08–2020-12
- Phase 2 cube jobs: 2856
- Phase 3 cuboid jobs: 7422
- Simulator qualification in archive: No
- Mixed development and weekly evaluation: Yes

Cadence: Fixed historical archive; later challenge years and later RL artifacts are distinct releases.

Access/export: Public SQLite index and documented query helper can filter jobs before trajectory acquisition. Documentation and endpoints reviewed; SQLite rows and trajectories not acquired, helper not executed.

**Hardware, environment and human involvement**

- Platform: TriFinger
- Fingers: 3
- Actuated joints: 9
- Cameras: 3
- Proprioception hz: 1000
- Camera hz: 10
- Cube edge mm: 65
- Cuboid mm: [20, 20, 80]
- Environment: Bounded laboratory workspace
- Standard evaluation duration s: 120
- Duration applies to every archived job: No
- Reset count: Unknown / not established
- Reset duration s: Unknown / not established
- Intervention count: Unknown / not established
- Unknown reason: Index documentation does not comprehensively establish resets or interventions.

**Observed examples and measurements**

- Observed documented schema: `{"fields": ["job_id", "start_time", "challenge_phase", "robot_name", "difficulty_level", "cumulative_reward", "baseline_reward", "initial_distance_to_goal", "min_distance_to_goal", "max_height"], "database_rows_inspected": false, "documented_max_height_unit": "metres"}`
  - Schema from documentation; no actual SQLite row or index checksum claimed.
  - Locator: Dataset documentation: index fields. References: `rp003_docs`.

**Verified findings and qualifications**

- Archive documentation lists 2,856 phase-two cube jobs and 7,422 phase-three cuboid jobs. Participants and weekly evaluations are mixed; neither count is a success-rate denominator. References: `rp003_docs`.
- The later TriFinger RL documentation warns about errors in certain files downloaded before 15 May 2023. Applies specifically to weak-n-expert, half-expert and trifinger-cube-lift-sim-expert-* files in the later RL collection; not a correction to RRC2020 or evidence of duplicate trajectories. References: `rp003_rl_correction`.

**Limitations and duplicate evidence**

- 2,856 and 7,422 are recorded-job counts including development and weekly evaluations, not standardized success denominators.
- Reward depends on initial goal distance; cube/cuboid and orientation objectives differ.
- Missing success, checkpoint, intervention and formal-evaluation fields remain unknown.
- Simulation qualification is excluded from selected physical archive; later RL simulation and physical variants cannot be merged.
- Noncommercial/share-alike dataset terms require separate compatibility review before redistribution or admission.
- Documentation supports max_height in metres (5 cm → 0.05); other distance units and timestamp timezone remain unverified.
- Helper-generated url_orig/url_zarr are not documented stored SQL columns. _10/_30 fields describe camera-observation order statistics, not independent trial counts.
- Documentation has a camera360 versus camera300 naming inconsistency; preserve it rather than silently pick a sensor schema.
- Original logs, converted logs and Zarr exports represent the same underlying jobs.
- Later TriFinger RL artifacts share the source family; underlying-run overlap with RRC2020 is unestablished. Their license/correction cannot be inherited by 2020.

**Artifact access, version and rights**

- `rp003_docs`: [RRC2020 dataset documentation](https://people.tuebingen.mpg.de/mpi-is-software/data/rrc2020/). Version: unversioned/unknown. Access: primary documentation observed.
  - Rights: CC-BY-NC-SA-4.0. Documented license for 2020 dataset/index/trajectories; not a blanket license for every paper or later release.
- `rp003_index`: [RRC2020 SQLite index reference](https://download.is.tue.mpg.de/rrc2020/rrc2020_dataset_index.db). Version: unversioned/unknown. Access: endpoint reference not downloaded.
  - Rights: CC-BY-NC-SA-4.0. 2020 dataset restrictions retained; no database bytes or rows acquired.
  - [Rights evidence](https://people.tuebingen.mpg.de/mpi-is-software/data/rrc2020/).
- `rp003_helper`: [Query helper reference](https://download.is.tue.mpg.de/rrc2020/rrc_dataset_query.py). Version: unversioned/unknown. Access: endpoint reference not executed.
  - Rights: unknown / no general reuse grant established. Helper-specific software license unverified; never executed.
- `rp003_paper`: [Real Robot Challenge paper v2](https://arxiv.org/html/2109.10957v2). Version: 2109.10957v2. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp003_rl_correction`: [Later TriFinger RL correction notice](https://webdav.tuebingen.mpg.de/trifinger-rl/docs/datasets/index.html). Version: unversioned/unknown. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.

### RP004 · PhAIL physical task reliability

Regime: `episodic_physical_laboratory`. Candidate remains unadmitted.

**Coverage and cadence**

- Release: v1.0
- Collection period: 2025-11–2026-05
- Dataset publication: 2026-05-06
- Collection is synthetic: No
- Cohorts reconciled: No
- Reported cohorts: {"hf_card": {"policy": 524, "human": 40, "training": 449}, "paper_v1": {"policy": 599, "human": 396, "training": 449}, "website_release": {"policy": 594, "human": null, "training": 352}}
- Dataset commit: 5bc590213c5d2615eefeb47bc23a700f8c57022a
- Paper repo commit: 18ce72d5703dcbbbb10a980336aa5a1622601fb4
- Paper publication: 2026-05-28
- Current website home updated: 2026-10-05

Cadence: Release-specific publication; no fixed update schedule verified. Website, paper and dataset dates/cohorts remain separate.

Access/export: Public JSON metadata/annotation sidecars and documentation can be reviewed individually. Parquet telemetry and MP4 recordings are not fetched. sample/ is a selected subset, not additional episodes.

**Hardware, environment and human involvement**

- Platform: Franka Research 3
- Gripper: Robotiq 2F-85
- Cameras: Wrist and external cameras
- Action frequency hz: 15
- Setting: Single-laboratory tote/item handling
- Serving topology: Model-dependent local notebook, local network or Cyprus–Finland remote link
- Preparation: Evaluator reloads tote and chooses camera/tote placement per episode
- Checkpoint selection: Blinded as described by release
- Stopping rule: Operator success stop, safety stop, or 30 seconds × initial item count
- Cap per item s: 30
- Reset count: Unknown / not established
- Reset duration s: Unknown / not established
- Outside episode recovery time s: Unknown / not established
- Intervention metric: Definition conflict: Table 2 caption says safety-stop episodes, but pinned table-build code uses Safety OR Stalled. Appendix F also claims an episode denominator with conflicting percentages. Separate fig_intervention_meta uses per-operation drops+safety.

**Observed examples and measurements**

- Observed selected episode: `{"model": "groot", "variant": "270226-ee_rot6d_rel:150000", "eval.object": "Wooden spoons", "eval.total_items": 8, "eval.successful_items": 8, "eval.outcome": "Success", "eval.duration": 193.2486054940091, "eval.cap_per_item": 30}`
  - Dotted keys are literal JSON keys; derived unit and episode-count annotations are separate from source fields. Eight items belong to one selected episode; sample/ contains existing episodes.
  - Locator: static.json: model/variant and eval.* fields. References: `rp004_sample`.
- Conflicting published intervention rates: `{"model": "SmolVLA", "table_2_percent": 18.6, "appendix_f_percent": 12.2, "reconciled": false}`
  - Table 2 caption and Appendix F both claim episode-based safety-stop percentages but conflict. Table 2 matches code-defined Safety OR Stalled aggregates. Separate fig_intervention_meta uses per-operation drops+safety and is not a replacement.
  - Locator: Table 2 versus Appendix F. References: `rp004_paper`, `rp004_builder`, `rp004_table_aggregate`, `rp004_operation_metric`.
Derived annotations (not source-native keys): `{"duration_unit": "seconds", "duration_unit_basis": "Dataset-card documentation; not a source JSON key", "independent_episode_count": 1}`.

**Verified findings and qualifications**

- Dataset-card, paper and release-page policy/human/training cohorts differ. Published counts are preserved per artifact; no membership bridge or pooled denominator established. References: `rp004_card`, `rp004_paper`, `rp004_release`.
- The sample records eight completed wooden spoons in one episode. Selected example does not estimate general robot reliability. References: `rp004_sample`.
- The paper caption defines intervention as safety stops, but its table-building code uses a Safety OR Stalled proxy. Static code and aggregate numerators 7/165,7/165,3/151,22/118 reproduce rounded Table 2 values. No code was executed. Caption/code and Table 2/Appendix F conflicts remain; separate per-operation metadata is a different measure. References: `rp004_paper`, `rp004_builder`, `rp004_table_aggregate`, `rp004_operation_metric`.
- A small aggregate audit reports 524 inference plus 142 legacy episodes; subtracting 72 fifth-object episodes yields 594. Arithmetic is a plausible website explanation, not a membership join. It does not reconcile paper 599, human 40 versus 396 or training 352 versus 449. References: `rp004_audit`, `rp004_card`, `rp004_paper`, `rp004_release`.
- The current explorer shows 1,043 episodes and a 120-second reliability display, while paper HRT/RMST uses 240 seconds. 1,043 equals 594+449 arithmetically but composition is unverified; UI and paper metrics remain separate. References: `rp004_explorer`, `rp004_paper`.
- Pinned table aggregate contains bare Infinity for SmolVLA median_T. Not valid strict JSON; no source aggregate fixture vendored, no nonfinite value coerced to zero or imported. References: `rp004_table_aggregate`.

**Limitations and duplicate evidence**

- One eight-item episode is not eight independent trials.
- Policy, human and training counts differ by artifact and membership is unreconciled.
- Table 2 and Appendix F both claim episode-based safety-stop metrics but disagree; inspected Table 2 code counts Safety OR Stalled. Separate per-operation metadata uses drops+safety, excluding stalls.
- Reset/preparation/recovery overhead outside episodes is not measured production-time exposure.
- Model serving topology differs; wall time and physical task success need distinct interpretation.
- Scene configurations are not replay-matched between policies. Current UI 120-second reliability must not inherit paper 240-second HRT/RMST semantics.
- HF files, paper and website overlap but cohorts cannot be equated without membership evidence.
- sample/ is selected from existing episodes.
- DROID hardware convention does not establish duplicated DROID trajectories.

**Artifact access, version and rights**

- `rp004_site`: [PhAIL project](https://phail.ai/). Version: unversioned/unknown. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp004_release`: [PhAIL release v1.0 protocol](https://phail.ai/releases/v1.0). Version: v1.0. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp004_card`: [PhAIL v1.0 dataset card](https://huggingface.co/datasets/phail-anon/phail-v1.0/blob/5bc590213c5d2615eefeb47bc23a700f8c57022a/README.md). Version: 5bc590213c5d2615eefeb47bc23a700f8c57022a. Access: primary documentation observed.
  - Rights: CC-BY-4.0. Dataset declaration only; website/paper treated separately.
  - [Rights evidence](https://huggingface.co/datasets/phail-anon/phail-v1.0/blob/5bc590213c5d2615eefeb47bc23a700f8c57022a/croissant.json).
- `rp004_croissant`: [PhAIL artifact metadata](https://huggingface.co/datasets/phail-anon/phail-v1.0/blob/5bc590213c5d2615eefeb47bc23a700f8c57022a/croissant.json). Version: 5bc590213c5d2615eefeb47bc23a700f8c57022a. Access: primary documentation observed.
  - Rights: CC-BY-4.0. Dataset declaration; no telemetry or videos redistributed.
- `rp004_sample`: [One selected episode sidecar reference](https://huggingface.co/datasets/phail-anon/phail-v1.0/blob/5bc590213c5d2615eefeb47bc23a700f8c57022a/sample/inference/000000000000/000000000000/static.json). Version: 5bc590213c5d2615eefeb47bc23a700f8c57022a. Access: primary documentation observed.
  - Rights: CC-BY-4.0. Dataset declaration; factual task/outcome fields only.
  - [Rights evidence](https://huggingface.co/datasets/phail-anon/phail-v1.0/blob/5bc590213c5d2615eefeb47bc23a700f8c57022a/croissant.json).
- `rp004_paper`: [PhAIL paper v1](https://arxiv.org/html/2605.29710v1). Version: 2605.29710v1. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. arXiv perpetual nonexclusive distribution license is not a general redistribution grant; separate from CC BY 4.0 dataset and Apache software.
- `rp004_builder`: [Pinned intervention table builder](https://github.com/Positronic-Robotics/phail-paper/blob/18ce72d5703dcbbbb10a980336aa5a1622601fb4/build/tab_leaderboard.py#L52-L75). Version: 18ce72d5703dcbbbb10a980336aa5a1622601fb4. Access: primary documentation observed.
  - Rights: Apache-2.0. Software license only; source read as inert text, never executed. Does not license the paper, website, model weights or all data.
  - [Rights evidence](https://github.com/Positronic-Robotics/phail-paper/blob/18ce72d5703dcbbbb10a980336aa5a1622601fb4/LICENSE).
- `rp004_table_aggregate`: [Pinned published table aggregate](https://github.com/Positronic-Robotics/phail-paper/blob/18ce72d5703dcbbbb10a980336aa5a1622601fb4/out/paper/tab_leaderboard.json). Version: 18ce72d5703dcbbbb10a980336aa5a1622601fb4. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. Aggregate-specific redistribution grant not separately established; limited factual metadata only.
- `rp004_audit`: [Pinned aggregate cohort audit](https://github.com/Positronic-Robotics/phail-paper/blob/18ce72d5703dcbbbb10a980336aa5a1622601fb4/out/data_audit/summary.json). Version: 18ce72d5703dcbbbb10a980336aa5a1622601fb4. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp004_operation_metric`: [Separate per-operation metric metadata](https://github.com/Positronic-Robotics/phail-paper/blob/18ce72d5703dcbbbb10a980336aa5a1622601fb4/out/paper/fig_intervention_meta.json). Version: 18ce72d5703dcbbbb10a980336aa5a1622601fb4. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp004_explorer`: [Current benchmark explorer](https://phail.ai/benchmark/pick-and-place-droid-v1.0). Version: unversioned/unknown. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.

### RP005 · STRANDS / LCAS long-term deployments

Regime: `sustained_physical_deployment`. Candidate remains unadmitted.

**Coverage and cadence**

- Later daily dataset: 2016-11–2017-04
- Earlier study: 2014–2015
- Earlier continuous runs: 43
- Recovery table period: 2015 deployments
- Separate deployment artifacts: Yes

Cadence: Historical releases. Daily observations do not imply ongoing publication or monitoring.

Access/export: Public daily report and archive listings reviewed; day ZIPs and ROS bag extracts not downloaded. No care-home occupants, personal records or evaluator identities retained.

**Hardware, environment and human involvement**

- Later platform: SCITOS-G5
- Earlier platform: SCITOS A5
- Later setting: Vienna care home
- Later sensors: Laser, odometry and localization outputs
- Hardware names not silently merged: Yes
- Requested assistance allowed in earlier lifetime metric: Yes
- Lifetime reset rule: Unrecoverable failure or unrequested expert assistance
- Recovery success rule: No subsequent failure within one minute or one metre
- Reset count: Unknown / not established
- Reset duration s: Unknown / not established
- Overall assistance count: Unknown / not established
- Service quality measured by lifetime: No

**Observed examples and measurements**

- Observed daily aggregate: `{"date": "2016-11-21", "Data": 0.5, "Data available": 1, "Robot active": 1, "Distance": 2017.15, "Distance_unit": null, "Hours": 9.99, "Data_fraction_definition": null}`
  - Inactive available days and missing observations are different; exact Distance unit and fractional Data definition are unverified.
  - Locator: Daily report, 21 November 2016 row and COL legend. References: `rp005_sheet`.
- Observed recovery aggregate: `{"period": "2015 deployments", "trigger": "bumper", "successful_attempts": 177, "unsuccessful_attempts": 148, "requested_human_help": true, "unit": "recovery_attempt", "independent_deployment_failures": null}`
  - Recovery attempts can repeat after one failure. Count is not an unattended-autonomy rate.
  - Locator: Recovery table and recovery-success definition. References: `rp005_paper`.

**Verified findings and qualifications**

- The earlier study reports 43 continuous runs over 2014–2015. Its bumper recovery 177/148 counts are specifically from 2015 deployments. References: `rp005_paper`.
- Lifetime resets after unrecoverable failure or unrequested expert assistance. Requested assistance can coexist with the lifetime metric; no service-quality score inferred. References: `rp005_paper`.
- Daily report distinguishes data availability and robot activity. Unknown field semantics remain null; COL is not recoded as collision count. References: `rp005_sheet`.

**Limitations and duplicate evidence**

- Older purpose-built systems and selected environments are not a current general-purpose robot capability estimate.
- 177 successful and 148 unsuccessful bumper-triggered recovery attempts concern 2015, not the whole 43-run period.
- Several unsuccessful recovery attempts can precede a success; attempts are not independent underlying failures.
- Requested human help can coexist with reported autonomy; lifetime is not unattended operation or service quality.
- Daily Data=0.5 meaning and Distance units remain unresolved.
- COL legend indicates human pushing, not a conventional collision statistic.
- Unknown archive/spreadsheet reuse rights remain held; citation request is not a license.
- An active available-data day has Data=0, so Data is not an availability or activity flag. Hours is a named source unit, but its calculation is unverified.
- Localization-event extracts overlap daily recordings and add no operating exposure.
- Earlier 2014–2015 study and later 2016–2017 daily archive are distinct deployments; do not transfer metric definitions automatically.

**Artifact access, version and rights**

- `rp005_docs`: [Long-term indoor dataset documentation](https://strands.readthedocs.io/en/latest/datasets/care_home.html). Version: unversioned/unknown. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp005_sheet`: [AAF navigation report](https://docs.google.com/spreadsheets/d/1SeyMyPDr4WoCeIf0-GxYsnGRLkYnFpTZcfQGw0nYSns/edit). Version: unversioned/unknown. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp005_archives`: [Daily archive listing](https://lcas.lincoln.ac.uk/nextcloud/shared/datasets/AAF_Y4/). Version: unversioned/unknown. Access: directory listing only archives not downloaded.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp005_glitches`: [Selected localization-event extracts listing](https://lcas.lincoln.ac.uk/nextcloud/shared/datasets/AAF_Y4/y4_glitches/). Version: unversioned/unknown. Access: directory listing only archives not downloaded.
  - Rights: unknown / no general reuse grant established. No artifact-specific redistribution grant verified; metadata and source links only.
- `rp005_paper`: [Earlier long-term autonomy study v2](https://arxiv.org/html/1604.04384v2). Version: 1604.04384v2. Access: primary documentation observed.
  - Rights: unknown / no general reuse grant established. arXiv perpetual nonexclusive distribution license is not a general reuse grant; no source body or table fixture redistributed.

## Implemented bounded BARN check

[Validator](../../../tools/evidence_program/validate_barn_table.py) · [licensed table derivative](../../../tools/evidence_program/tests/fixtures/robotics-physical/barn-2024-table-ii.json) · [attribution and transformation notice](../../../tools/evidence_program/tests/fixtures/robotics-physical/NOTICE.md) · [focused tests](../../../tools/evidence_program/tests/test_robotics_barn.py).

The selected exact source is arXiv `2407.01862v1`, Table II. The table was manually checked against versioned HTML and the same PDF text extraction. This does not claim visual PDF validation or acquired full-source bytes. Every `X` is one reported failed attempt, with null completion time and unknown cause. No simulation Table I, later editions, videos or practice outcomes enter the 60-cell denominator.

| Team | All displayed successes / results | Credited successes / contest slots |
| --- | ---: | ---: |
| LiCS-KI | 10/15 | 6/9 |
| MLDA_EEE | 5/15 | 5/9 |
| AIMS | 5/15 | 5/9 |
| EIT-NUS | 0/15 | 0/9 |

Credited counts are separate aggregates, with three credited slots per course. The exact selected displayed-row identities are not supplied; LiCS-KI course two has a 37-second tie at the third-fastest boundary. The validator never assigns an authoritative per-row credited boolean. Published averages remain original source assertions, alongside exact rational recomputations: LiCS-KI fastest-three means are 88/3 and 98/3 seconds, whereas published course averages are 30 and 35. A different published denominator is not an extraction error to silently repair.

Rows use source-version/team/course/reported-position observation keys. Reordering the JSON input preserves normalized identities; repeated identical coordinates are deduplicated, conflicting repeated coordinates rejected. These are display observations, not native run IDs. Unreviewed source versions are rejected; cross-version trial reconciliation is future work. A protocol ban on human intervention does not become a measured zero-intervention field. Reset counts/duration, practice counts, exact checkpoint/system version, timestamps and hardware-instance identity remain null.

Input file access is stdlib-only, POSIX descriptor-relative and no-symlink, regular-file-only; unsupported safe-open platforms fail closed. Limits: 64 KiB, nesting depth 12, 120 input rows allowing duplicate checks but exactly 60 unique coordinates, eight input summaries but four unique teams, 2,048-byte strings and bounded positive integer times. URLs, stdin, parent traversal, symlink components, special files, duplicate JSON keys, nonfinite values, booleans masquerading as numbers and unknown/invalid fields are rejected. The OS may mount a remote filesystem behind a regular path, so this does not prove filesystem locality. Strings are inert data; there are no network, subprocess or source-code calls.

```bash
python tools/evidence_program/validate_barn_table.py tools/evidence_program/tests/fixtures/robotics-physical/barn-2024-table-ii.json
python -m unittest discover -s tools/evidence_program/tests -p 'test_robotics*.py'
python tools/evidence_program/check.py
```

Fixture: 6584 bytes. SHA-256 `f79a2b58fa8771b766890627bf59e9f710acb5af1da397510dfdf4763cc8bd5e`. This identifies the transformed curated JSON only. The report/HTML/PDF hash remains null. Source URL versioning is not full-byte pinning. CC BY 4.0 applies to the source-derived fixture under `tools/`; the repository data dedication and software terms do not relicense it.

The [catalog checker](../../../tools/evidence_program/check_robotics_physical.py) and regression suite protect explicit sample values, source/rights provenance, 40 overlap cells, disabled controls/admission, source corrections and bounded future prompts. Passing is offline consistency, not empirical reproduction, rights approval, independent source-truth verification or canonical compatibility.

## Completed work, holds and next actions

### RP-A1 · completed

Review primary metadata and compare the frozen 64 and all eight prior catalogs.

Completion condition: Five new source families retained as unadmitted; full 40-cell semantic overlap review and exact base hashes recorded.

### RP-A2 · completed

Implement a bounded offline curated BARN 2024 Table II validator.

Completion condition: Preserve all 60 displayed results, 12 course and four team summaries; keep licensed fixture outside data/CC0; pass security, idempotency and denominator tests.

### RP-A3 · held

Resolve BARN average and identity semantics before broader extraction or cross-edition comparisons.

Completion condition: Document source precision and source-specific aggregate definitions; identify native run IDs or explicitly keep display observations artifact-scoped. No pooling or automatic cross-version trial merge.

### RP-A4 · held

Resolve RoboArena snapshot membership, score scale and integrity implementation.

Completion condition: Pin bounded metadata revisions, document session/episode overlap and exclusions, prove dump/UI scale linkage and duration units; omit personal evaluators.

### RP-A5 · held

Define license-compatible RRC2020 index use and fill documented-schema gaps.

Completion condition: Establish units, timezone, evaluation/development flags and use rights before any separate bounded index acquisition; no trajectories or helper execution.

### RP-A6 · held

Reconcile PhAIL cohorts, episode-based intervention claims and separate per-operation metric definitions.

Completion condition: Explain card/paper/website membership, Table 2 Safety OR Stalled versus safety-only caption, conflicting Appendix F episode rates and separate per-operation drops+safety measure; arithmetic is not record-membership proof.

### RP-A7 · held

Resolve STRANDS aggregate rights, field meanings and version identity.

Completion condition: Verify dataset/spreadsheet license, fractional Data, Distance unit, Hours computation and sheet revision; no raw care-home logs.

### RP-A8 · pending_separate_review

Map physical capability evidence to existing canonical contracts.

Completion condition: Preserve event/run/episode/item/recovery units, hardware, dates, exact source version, missingness and rights; no schema changes or admission in this review.

## Bounded standalone follow-up prompts

These prompts are prepared for later separate work, not dispatched collectors or active schedules. Each names its own scope and stopping boundary.

### RP-P1 · Resolve BARN table semantics

Review https://arxiv.org/html/2407.01862v1 Table II and https://people.cs.gmu.edu/~xiao/Research/BARN_Challenge/BARN_Challenge26.html historical 2024 rankings. Preserve all 60 reported positions (20 successes, 40 failures), selected 6/9,5/9,5/9,0/9 credit and unknown chronological/native-run identity. Determine whether published averages or additional public precision explains LiCS-KI 30/35, paper MLDA/AIMS 79/109 and later-site 78.8/108.8 versus printed-cell means 78.6/108.6. Do not choose a credited 37-second tied row or invent a correction. Return version/locator-qualified assertions and gaps, not a pooled cross-year series. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, robot control, source-script/notebook/model execution, video/NPZ/trajectory/ROS-bag acquisition, personal evaluator or care-home occupant data, or ongoing collection. Do not infer missing units, rights or membership. Stop at unavailable evidence and report the gap. No repository edits, canonical admission, universal capability score or p(doom) conversion.

### RP-P2 · Reconcile RoboArena snapshot semantics

Inspect only bounded public YAML/card metadata at https://huggingface.co/datasets/RoboArena/DataDump_07-17-2026 and https://huggingface.co/datasets/RoboArena/DataDump_02-03-2026 plus https://arxiv.org/html/2506.18123v1 and public RoboArena website source. Pin revisions and compare the already referenced session 00008df3-4cb6-45ce-a6de-1d98a755146a without retaining personal evaluator fields. Establish raw 399 duration units, partial 0.1 scale linkage, snapshot overlap and whether the checked-in April 2 integrity notice is displayed or applied to these exports. A commented-out component or frontend percentage rendering is not proof of dataset filtering/normalization. Return a bounded membership/version/measurement plan and explicit unknowns; no video or episode sweep. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, robot control, source-script/notebook/model execution, video/NPZ/trajectory/ROS-bag acquisition, personal evaluator or care-home occupant data, or ongoing collection. Do not infer missing units, rights or membership. Stop at unavailable evidence and report the gap. No repository edits, canonical admission, universal capability score or p(doom) conversion.

### RP-P3 · Clarify RRC index contract

Review https://people.tuebingen.mpg.de/mpi-is-software/data/rrc2020/, https://arxiv.org/html/2109.10957v2 and https://webdav.tuebingen.mpg.de/trifinger-rl/docs/datasets/index.html. Use documentation only to clarify index units/timezone, job identity, development versus evaluation, and CC BY-NC-SA 4.0 compatibility. Do not acquire the SQLite database in this follow-up. Record that 2856 cube plus 7422 cuboid are documented mixed jobs, not queried counts or successes. Keep the May 15, 2023 later-RL correction separate from 2020 and do not assume duplicated trajectories. Return a precise proposed read-only index test plus unresolved rights and metadata needs. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, robot control, source-script/notebook/model execution, video/NPZ/trajectory/ROS-bag acquisition, personal evaluator or care-home occupant data, or ongoing collection. Do not infer missing units, rights or membership. Stop at unavailable evidence and report the gap. No repository edits, canonical admission, universal capability score or p(doom) conversion.

### RP-P4 · Reconcile PhAIL aggregate definitions

Review https://huggingface.co/datasets/phail-anon/phail-v1.0, https://arxiv.org/html/2605.29710v1 and https://phail.ai/releases/v1.0 with small public aggregate build metadata only. Preserve card 524/40/449, paper 599/396/449 and website 594/unknown/352 policy/human/training cohorts. The plausible arithmetic 524+142−72=594 is not membership proof and does not reconcile 599. Inspect the table builder as inert text: Safety OR Stalled differs from the paper safety-stop-only caption; Appendix F also claims safety-stop episodes but differs numerically; separate fig_intervention_meta uses drops+safety per operation and is not a replacement. Return artifact-version-specific counts/definitions and unresolved discrepancies, without executing code or fetching raw episodes. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, robot control, source-script/notebook/model execution, video/NPZ/trajectory/ROS-bag acquisition, personal evaluator or care-home occupant data, or ongoing collection. Do not infer missing units, rights or membership. Stop at unavailable evidence and report the gap. No repository edits, canonical admission, universal capability score or p(doom) conversion.

### RP-P5 · Clarify STRANDS daily aggregates

Review https://strands.readthedocs.io/en/latest/datasets/care_home.html, https://docs.google.com/spreadsheets/d/1SeyMyPDr4WoCeIf0-GxYsnGRLkYnFpTZcfQGw0nYSns/edit and https://arxiv.org/html/1604.04384v2. Use only existing public documentation and selected aggregate cells to resolve dataset/sheet rights, fractional Data, Distance units, Hours computation and immutable sheet version. Keep inactive-but-available versus missing days separate. Earlier 43 runs cover 2014–2015 while 177/148 bumper recovery attempts concern 2015; requested help is compatible with lifetime. Keep A5/G5 deployment artifacts distinct. Return field/rights evidence or preserve holds; no daily ZIPs or localization extracts. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, robot control, source-script/notebook/model execution, video/NPZ/trajectory/ROS-bag acquisition, personal evaluator or care-home occupant data, or ongoing collection. Do not infer missing units, rights or membership. Stop at unavailable evidence and report the gap. No repository edits, canonical admission, universal capability score or p(doom) conversion.

### RP-P6 · Review physical evidence mapping

Inspect the current pdoom-live data/evidence-program/research/robotics-physical.json, docs/evidence-program/research/robotics-physical.md and frozen evidence-program contracts. Propose lossless mapping for displayed BARN attempts versus contest credit, RoboArena session/policy/preference/partial outcomes, RRC jobs/reward, PhAIL episode/items/intervention definitions and STRANDS recovery/operating exposure. Preserve physical/simulation/staged/sustained regimes, versioned rights, unknown reset/practice/checkpoint/unit fields, source and derived values, and duplicate evidence. Return a compatibility analysis and minimal acceptance examples, not a schema migration or importer. Read-only public-source research only. No login, outreach, bulk download, access-control bypass, robot control, source-script/notebook/model execution, video/NPZ/trajectory/ROS-bag acquisition, personal evaluator or care-home occupant data, or ongoing collection. Do not infer missing units, rights or membership. Stop at unavailable evidence and report the gap. No repository edits, canonical admission, universal capability score or p(doom) conversion.

## Verification limits

- Full manuscript byte hashes are not fabricated from extracted text. Metadata references can be version-pinned while full source bytes remain unacquired.
- BARN deterministic fixture tests and source-document review are separate. Source truth is not proven merely by matching a curated hash.
- RRC SQLite rows and trajectories were not queried; documented schema/counts are not an independent SQL reproduction.
- No robot controls, simulation harnesses, models, notebooks or downloaded source scripts ran. No personal evaluator details, care-home occupant records, raw trajectory/NPZ/video/ROS-bag archives or source private reports are included.
- Unknown rights remain held. A dataset license does not cover its paper, website, software, hardware assets or evaluated checkpoints by default.
- Canonical mapping, admission, deployment and any later acquisition require separate work. A source-review merge does not clear unresolved evidence holds.

## Strongest limitation

Different task populations, assistance rules, stopping conditions, cohort membership and denominators prevent a single comparable physical-world reliability score.

## Smallest testable implementation

A licensed manually curated BARN 2024 Table II excerpt and bounded offline validator, preserving 60 reported outcomes and separate contest credit.
