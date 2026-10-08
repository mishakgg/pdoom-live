# Human reliance and decision quality

Reviewed 8 October 2026 against [main 33fef790](https://github.com/mishakgg/pdoom-live/commit/33fef7908a6e449c8acd38f15b8d50d65a4923a3). Original research used 6c2a4aa; this review rechecks the frozen 64-source register and all ten earlier catalogs. [Machine-readable catalog](../../../data/evidence-program/research/human-reliance.json) · [review queue](research-session-review-queue.md).

Five candidate experimental families remain unadmitted. This is a documentary review plus an implemented manual paper-aggregate validator and a provisional synthetic-only five-bit decoder. No workbook reader or real-data acceptance is complete. No participant CSV/workbook bytes were acquired in this review. No minors records, clinical records/images, names or demographic rows are retained.

## Recommendations and implementation boundary

1. Bastani: immediate subsequent unaided learning, with minors rows excluded and data reuse rights unknown.
2. Bansal: observed human–AI team performance, retaining the separate unaided condition.
3. Okamura–Yamada: a compact explicitly licensed dataset candidate; privacy/schema acquisition remains held. Useful current code validates manually transcribed paper counts and synthetic arithmetic only.

Gaube adds professional expertise and operational recommendation scoring. Glickman–Sharot adds independent perceptual judgments after prior exposure. None establishes months-long professional deskilling. Immediate assisted performance, immediate unaided learning, within-session bias changes and delayed retention are different measurements.

## Current verification versus inherited evidence

- Current primary publications, static documentation/source text, dictionaries and repository/OSF/Figshare metadata establish scoped documentary claims. A paper count can be verified even when participant data are not acquired.
- Bastani and Bansal outcome-file identities are metadata-only; actual row snippets and header order from earlier research are not re-published or reverified.
- Okamura dataset license, file size/version/metadata MD5 and published aggregate totals are currently verified. Its inherited SHA-256, workbook sheets/dictionary, bit order, recruit-group counts and NoTCC cue-flag observation are not currently reverified. A public download link is not completed acquisition.
- Paper metadata, an indexed correction, an opened primary document, a dictionary and an inherited schema have explicit different access/verification labels in the catalog.
- Four families retain unknown data-specific reuse rights. Dataset CC BY4.0 for Okamura does not settle participant privacy/schema permission or license simulator images. No article license is propagated to separate CSVs or radiographs.

## HR001 Bastani et al. — Generative AI without guardrails can harm learning

Family `bastani-genai-learning`; new experimental family relative to this register, inventory source ID null. It has no operational collector or canonical admission.

- Task: High-school mathematics practice followed by unaided examination
- Stakes: Classroom work contributed to grades
- Expertise: Students at one Turkish high school; minors may be represented
- Adviser kind: GPT-4-based tutoring variants
- Model identity basis: Paper appendix specification; no model execution
- Baseline: Prior GPA and randomized control; practice and immediate unaided examination are distinct phases
- Followup kind: immediate_unaided_examination
- Conditions: Ordinary resources/control; GPT Base; GPT Tutor with teacher-informed safeguards
- Specified checkpoint: GPT-4-0613

Coverage: collection period: Fall 2023; publication date: 2025-06-25; publication precision: day; correction date: 2025-08-20; artifact revision: 2f63dae1a01d51453826fe07ef5cf6678e339588; update frequency: Fixed study deposit; no scheduled refresh verified; artifact revision time: 2025-06-25T16:50:04Z; first outcome file commit date: 2025-06-13T00:25:26Z.

### Source-backed findings

- GPT Base examination performance was reported 17% lower relative to control; this is not a 17-percentage-point decrease. An immediate unaided mathematics exam at one school does not establish durable professional deskilling. Verification: `current_documentary_verification`. [Primary paper](https://doi.org/10.1073/pnas.2422633122), [Author-hosted paper and appendix](https://hamsabastani.github.io/education_llm.pdf)
- The two final_data.csv paths have the same Git blob identity. One dataset in two folders, not two independent cohorts; metadata equality does not require reading minors rows. Verification: `current_documentary_verification`. [Outcome-file identity only; minors rows excluded](https://github.com/obastani/GenAICanHarmLearning/blob/2f63dae1a01d51453826fe07ef5cf6678e339588/main_regressions/final_data.csv), [Duplicate outcome-file identity only](https://github.com/obastani/GenAICanHarmLearning/blob/2f63dae1a01d51453826fe07ef5cf6678e339588/additional_results/final_data.csv)
- The correction changes an author affiliation. No outcome/data correction is established by this notice. Verification: `indexed_primary_direct_access_blocked`. [Affiliation correction](https://doi.org/10.1073/pnas.2518204122)
- Table 3 (appendix p33) reports 839 main-survey participants and 943 including honors; Table 1 (p10) has 2,848 student-session regression observations. Different populations/units. Unique main-regression students remain unknown; do not infer all 839 supplied regression observations. Verification: `current_documentary_verification`. [Author-hosted paper and appendix](https://hamsabastani.github.io/education_llm.pdf)
- GPT Base exam coefficient is−0.054 on normalized 0–1 score and control mean 0.321, approximately−16.8% relative. −5.4 normalized-score percentage points is not 17 percentage points or a percentage of students failing. Tutor nonsignificance is not equivalence. Verification: `current_documentary_verification`. [Author-hosted paper and appendix](https://hamsabastani.github.io/education_llm.pdf)

Aggregate denominator ledger (documentary facts, not recomputed participant data):

- main survey participants: 839
- survey including honors: 943
- main regression student session observations: 2848
- noncomplier exclusion regression observations: 2805
- problem level practice observations: 13484
- problem level exam observations: 11392
- unique main regression students: null
- analysis exclusions: ["Baseline-survey nonresponse", "Honors classrooms"]
- noncompliance: "Five classroom-sessions retained in main intention-to-treat analysis"
- source locator: "Experimental Design pp6–9; Table1 p10; AppendixA.1 p25; Table3 p33; Tables7–8 pp36–37"

### Artifact references and rights

- [hr001_paper](https://doi.org/10.1073/pnas.2422633122): Primary paper. Access `bibliographic_metadata_verified_author_paper_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr001_appendix](https://hamsabastani.github.io/education_llm.pdf): Author-hosted paper and appendix. Access `public_primary_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr001_readme](https://github.com/obastani/GenAICanHarmLearning/blob/2f63dae1a01d51453826fe07ef5cf6678e339588/README.md): Dictionary and repository documentation. Access `public_primary_read`; rights `unknown`; Git blob `bc793475478e20d0046020e77b202836dbd44158`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr001_outcomes](https://github.com/obastani/GenAICanHarmLearning/blob/2f63dae1a01d51453826fe07ef5cf6678e339588/main_regressions/final_data.csv): Outcome-file identity only; minors rows excluded. Access `metadata_only_no_rows_acquired`; rights `unknown`; Git blob `b6b9babbfafc2fe5f140498cb1ed96ea00890919`; 470993 bytes. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr001_duplicate](https://github.com/obastani/GenAICanHarmLearning/blob/2f63dae1a01d51453826fe07ef5cf6678e339588/additional_results/final_data.csv): Duplicate outcome-file identity only. Access `metadata_only_no_rows_acquired`; rights `unknown`; Git blob `b6b9babbfafc2fe5f140498cb1ed96ea00890919`; 470993 bytes. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr001_correction](https://doi.org/10.1073/pnas.2518204122): Affiliation correction. Access `indexed_primary_correction_direct_access_blocked`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.

Schema example: documentation_schema_only_no_participant_record; status `current_dictionary_only_actual_csv_header_aliases_inherited`. Field names only: `Year`, `Session`, `Part2Tot`, `Part3Tot`, `GPTBase`, `GPTTutor`, `Treatment_arm`. No original participant sample row is included.

### Limitations and evidence identity

- Minors individual rows, student IDs, grades/GPA and classroom identifiers must not be acquired or published for this review. Paper aggregates and repository metadata only.
- One school/subject and author exclusions limit external validity; repeated student-session and classroom dependence remain study-level context.
- README calls Year academic year; calendar-year semantics not established. Student ID/Student_ID and Treatment arm/Treatment_arm actual-header aliases remain inherited; CSV bodies not read.
- Data artifact reuse rights unknown; public availability and citation requests do not establish a redistribution license.
- Two outcome CSV locations are byte-identical according to Git metadata.
- Paper, appendix and correction are one evidence chain; no extra cohort.

## HR002 Bansal et al. — Does the Whole Exceed Its Parts?

Family `bansal-complementary-performance`; new experimental family relative to this register, inventory source ID null. It has no operational collector or canonical admission.

- Task: Beer/book sentiment and LSAT reasoning
- Stakes: MTurk task with monetary performance bonuses
- Expertise: Screened US MTurk participants; not a professional workforce sample
- Adviser kind: Fine-tuned RoBERTa classifiers
- Model identity basis: Final advisers: RoBERTa (AllenNLP sentiment; ReClor LSAT); exact checkpoints unknown. Separate Beer explanation pilot used logistic regression.
- Baseline: Unaided human condition is separate; no per-person pre-advice decision in inherited schema
- Followup kind: immediate_task_decisions
- Conditions: Separate unaided condition; Recommendation with confidence; Explanation strategies

Coverage: collection period: unknown; publication date: 2021; publication precision: year; artifact revision: 6cebab4ffd2b332ebec5e27e7632e7bf1c36ba5f; repository revision date: 2025-09-20; update frequency: Fixed experiment with documentation correction; not a new cohort.

### Source-backed findings

- The study reports complementary team performance but no significant additional performance benefit of explanations over confidence alone. Task and condition-specific inference; does not mean every individual benefits. Verification: `current_documentary_verification`. [Author paper version](https://arxiv.org/html/2006.14779v3)
- Separate unaided responses and final assisted choices do not identify individual switching from a correct answer. Agreement with an incorrect recommendation is not an observed correct-to-incorrect switch. Verification: `current_documentary_verification`. [Author paper version](https://arxiv.org/html/2006.14779v3), [Dictionary and correction context](https://github.com/uw-hai/Complementary-Performance/blob/6cebab4ffd2b332ebec5e27e7632e7bf1c36ba5f/README.md)
- The pinned README correction swaps pred 2/conf 2 descriptions, but pred 2 still contains an unresolved binary 1-conf clause. Documentation correction only; actual field types and mapping are held. The revision did not change outcome files or create a cohort. Verification: `current_documentary_verification`. [Dictionary and correction context](https://github.com/uw-hai/Complementary-Performance/blob/6cebab4ffd2b332ebec5e27e7632e7bf1c36ba5f/README.md)
- The paper reports incompatible LSAT recruitment/retention and condition-size quantities. 508 ×0.35=177.8 cannot reconcile 100 people in each of several conditions; true retained total remains unknown. Verification: `current_documentary_verification`. [Author paper version](https://arxiv.org/html/2006.14779v3)

Aggregate denominator ledger (documentary facts, not recomputed participant data):

- recruits reported: {"Beer": 566, "Amzbook": 552, "LSAT": 508}
- retained proportions reported: {"sentiment": "0.84", "LSAT": "0.35"}
- per condition reported: {"sentiment": "93–101", "LSAT": 100}
- retained unique people: null
- decision row count: null
- quality flag: "UNRESOLVED_PUBLICATION_ARITHMETIC"
- trials per person: {"Beer": 50, "Amzbook": 50, "LSAT": 20}
- source locator: "Sections3.2,4.2,4.3,5.1,6.3; PDF p7 LSAT denominator statement"

### Artifact references and rights

- [hr002_paper](https://arxiv.org/html/2006.14779v3): Author paper version. Access `public_primary_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr002_doi](https://doi.org/10.1145/3411764.3445717): CHI publication identity. Access `publication_identity_verified_publisher_direct_access_failed`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr002_readme](https://github.com/uw-hai/Complementary-Performance/blob/6cebab4ffd2b332ebec5e27e7632e7bf1c36ba5f/README.md): Dictionary and correction context. Access `public_primary_read`; rights `unknown`; Git blob `0683f4e96dec80720973546d129315d7762d7128`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr002_filtered](https://github.com/uw-hai/Complementary-Performance/blob/6cebab4ffd2b332ebec5e27e7632e7bf1c36ba5f/experiment-data/decision-result-filter.csv): Filtered outcome artifact identity. Access `metadata_only_no_rows_acquired`; rights `unknown`; Git blob `8e0ffa27b01970004240cddbff40269f1bfbca59`; 5019995 bytes. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr002_prefilter](https://github.com/uw-hai/Complementary-Performance/blob/6cebab4ffd2b332ebec5e27e7632e7bf1c36ba5f/experiment-data/decision-result-prefilter.csv): Prefilter processing version; metadata only. Access `metadata_only_no_rows_acquired`; rights `unknown`; Git blob `b5788855beab341acf54a4d06c8ad2ec50ef56ad`; 5224636 bytes. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.

Schema example: documentation_schema_only_no_participant_record; status `current_dictionary_only_actual_csv_header_order_and_types_inherited`. Field names only: `questionId`, `task`, `condition`, `time`, `choice`, `y`, `pred`, `conf`, `conf2`, `pred2`. No original participant sample row is included.

### Limitations and evidence identity

- Curated item difficulty and fixed order constrain generalization; paper adviser accuracy was 84% sentiment and 65% LSAT.
- Do not treat multiple task conditions or filtered/prefilter exports as independent participant cohorts without design evidence.
- Exact checkpoints and artifact-specific data rights unknown; review text and LSAT materials have separate rights.
- Participant/assignment IDs and individual responses are not acquired or published here.
- Publication arithmetic unresolved: LSAT 508 recruits ×35% retained is 177.8, incompatible with 100 retained per several conditions. Do not silently change any figure or claim an exact retained total or decision-row count.
- Filtered and prefilter exports are processing versions of the same experiments, not independent replications.

## HR003 Okamura–Yamada — Adaptive trust calibration

Family `okamura-yamada-trust-calibration`; new experimental family relative to this register, inventory source ID null. It has no operational collector or canonical admission.

- Task: Simulated drone pothole inspection; manual versus automatic choice
- Stakes: Brief experimental task, not an operational drone deployment; compensation not established in reviewed paper.
- Expertise: Adult online recruits aged 20–69; not professional operators
- Adviser kind: Configured reliability simulation
- Model identity basis: Not applicable: no learned-model checkpoint
- Baseline: All groups receive continuous reliability information; NoTCC has no additional calibration cue
- Followup kind: within_session
- Conditions: NoTCC; Visual; Audio; Verbal; Anthro.

Coverage: collection period: unknown; publication date: 2020-02-21; publication precision: day; artifact published at: 2020-01-07T17:55:29Z; artifact version: 1; update frequency: Static versioned Figshare deposit.

### Source-backed findings

- The paper reports 194 recruits, 116 completers of the first 15 checkpoints and 78 excluded recruits. Recruitment, author-analysis population and repeated decision denominators stay separate. Verification: `current_documentary_verification`. [Primary paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0229132)
- The paper reports 1,740 decisions, 1,282 correct, 1,236 automatic and 504 manual decisions. Manual aggregate transcription; not a workbook recomputation or decoder acceptance pass. Verification: `current_documentary_verification`. [Primary paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0229132)
- Completer groups are NoTCC 28, Visual 18, Audio 22, Verbal 29 and Anthro. 19. Counts sum to 116; no individual rows or identifiers retained. Verification: `current_documentary_verification`. [Primary paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0229132)
- Dataset metadata identifies version 1 and one 28,147-byte CC BY 4.0 workbook. Rights do not establish deidentification/schema consent or current byte integrity. Verification: `current_documentary_verification`. [File manifest, version and dataset license](https://api.figshare.com/v2/articles/11538792), [Versioned dataset identity](https://doi.org/10.6084/m9.figshare.11538792.v1)
- Provisional decoder convention uses bit weights 16/8/4/2/1 for automatic/judgment/truth/operational over-trust/cue flags; code19 follows the inherited example. Full mapping is inferred from intake field order and code19, not an independently read dictionary. Current dictionary not acquired; no real-data acceptance. Verification: `inherited_intake_not_currently_recomputed`. [Candidate workbook; acquisition held](https://ndownloader.figshare.com/files/20725707)
- Inherited NoTCC records may carry the cue bit; keep tcc_flag_raw as an operational code. A raw flag is not proof a cue was presented, and overtrust_flag_raw is not a measured mental state. Verification: `inherited_intake_not_currently_recomputed`. [Candidate workbook; acquisition held](https://ndownloader.figshare.com/files/20725707)

### Artifact references and rights

- [hr003_paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0229132): Primary paper. Access `public_primary_read`; rights `declared_license` (CC-BY-4.0). PLOS article copyright explicitly links CC BY4.0; separate dataset/privacy and third-party asset scope remain qualified.
- [hr003_dataset](https://doi.org/10.6084/m9.figshare.11538792.v1): Versioned dataset identity. Access `public_metadata_read`; rights `declared_license` (CC-BY-4.0). Dataset license explicitly attached to Figshare article; not simulator images or other studies.
- [hr003_metadata](https://api.figshare.com/v2/articles/11538792): File manifest, version and dataset license. Access `public_metadata_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr003_workbook](https://ndownloader.figshare.com/files/20725707): Candidate workbook; acquisition held. Access `not_acquired_current_review`; rights `declared_license` (CC-BY-4.0); 28147 bytes. Dataset CC BY4.0 is established; participant/privacy and schema gates remain separate.

Schema example: inherited_schema_proposal_not_source_acceptance; status `inherited_unverified_source_schema`. Field names only: `ID`, `Group`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, `11`, `12`, `13`, `14`, `15`. No original participant sample row is included.

### Limitations and evidence identity

- 78/194 recruitment attrition is substantial. Within-session checkpoint differences are not delayed retention.
- Paper reports verbal-cue discrimination improvement without statistically significant between-group accuracy differences.
- Workbook acquisition and exact schema verification remain held; no current workbook bytes, row processing or participant-key retention.
- The inherited all-recruit group counts 41/33/32/44/44 and workbook hash are not independently reverified; only paper completer totals are in the manual aggregate ledger.
- Privacy review requires adult deidentified task-only scope, no identifying/demographic/sensitive fields, no cross-study linkage, aggregate outputs only.
- Paper supplementary link and Figshare file identify one workbook/evidence chain, not two cohorts.

## HR004 Gaube et al. — Do as AI say

Family `gaube-ai-label-advice`; new experimental family relative to this register, inventory source ID null. It has no operational collector or canonical admission.

- Task: Eight chest-X-ray vignettes with recommendations
- Stakes: Simulated clinical judgment, no patient-care outcome
- Expertise: 138 radiologists and127 internal/emergency-medicine physicians, including residents, practicing in US/Canada
- Adviser kind: Human expert-authored recommendations labeled as AI or human
- Model identity basis: Not applicable: CHEST-AI label did not identify an actual AI model
- Baseline: No unaided condition
- Followup kind: immediate_vignette_decisions
- Conditions: Advice source label between participants; Six accurate and two inaccurate recommendations within each participant

Coverage: collection period: unknown; publication date: 2021-02-19; publication precision: day; artifact modified at: 2020-05-26; update frequency: Static OSF experiment deposit; revisions are not new cohorts.

### Source-backed findings

- All advice was human-authored, including the CHEST-AI-labeled condition. Label effects cannot be represented as a tested AI model checkpoint or actual clinical system effectiveness. Verification: `indexed_primary_direct_access_blocked`. [Primary paper](https://www.nature.com/articles/s41746-021-00385-9), [Full-text author paper mirror](https://pmc.ncbi.nlm.nih.gov/articles/PMC7896064/)
- Rejecting an inaccurate recommendation receives correct-final-diagnosis credit under the study rule. The alternative diagnosis is not thereby independently shown correct; retain acceptance/rejection operational scoring. Verification: `indexed_primary_direct_access_blocked`. [Full-text author paper mirror](https://pmc.ncbi.nlm.nih.gov/articles/PMC7896064/)
- The study has 138 radiologists and 127 other physicians reviewing eight vignettes each; no unaided arm. Repeated vignette judgments do not become independent people or patient-care outcomes. Verification: `indexed_primary_direct_access_blocked`. [Full-text author paper mirror](https://pmc.ncbi.nlm.nih.gov/articles/PMC7896064/)
- Methods imply 265 participants, while Table 3 reports total 264. No row-level reconciliation performed; do not silently choose one participant total. Verification: `indexed_primary_direct_access_blocked`. [Full-text author paper mirror](https://pmc.ncbi.nlm.nih.gov/articles/PMC7896064/)

Aggregate denominator ledger (documentary facts, not recomputed participant data):

- methods radiologists: 138
- methods internal emergency medicine: 127
- methods sum: 265
- table3 total: 264
- reconciled unique participants: null
- vignettes per participant: 8
- correct recommendations: 6
- incorrect recommendations: 2
- initial recruit count: null
- exclusion count: null

### Artifact references and rights

- [hr004_paper](https://www.nature.com/articles/s41746-021-00385-9): Primary paper. Access `indexed_primary_methods_and_aggregates_direct_html_blocked`; rights `declared_license` (CC-BY-4.0). Article-specific CC BY4.0 with third-party credit-line caveats; does not license separate CSVs, radiographs or stimulus images.
- [hr004_pmc](https://pmc.ncbi.nlm.nih.gov/articles/PMC7896064/): Full-text author paper mirror. Access `indexed_primary_methods_and_aggregates_direct_html_blocked`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr004_project](https://osf.io/rjfqx/): Author project. Access `public_metadata_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr004_manifest](https://api.osf.io/v2/nodes/rjfqx/files/osfstorage/5ec79b16c7568600952d07a9/): Data-file manifest only. Access `public_metadata_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr004_outcomes](https://osf.io/rjfqx/files/osfstorage/5eccd338aeeb6d019708665e): Combined long CSV reference, not acquired. Access `metadata_only_no_rows_acquired`; rights `unknown`; 238730 bytes. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.

Schema example: inherited_header_reference_only; status `complete_decoder_unverified`. Field names only: `ORDER OF PATIENTS`, `Q1`, `Q2`, `Q3`, `Q4`, `Q5`, `Q6`, `Rec_Typ`, `Q3n`, `Condition`. No original participant sample row is included.

### Limitations and evidence identity

- No clinical decision tool, patient records, image acquisition, medical-data CSV processing or individual physician profiles are within scope.
- Complete Q 1–Q 6 codebook mappings not established; do not infer code meanings.
- OSF data reuse rights remain unknown; article CC BY does not license separate CSV or radiographs.
- Collection dates unknown; file/project timestamps are administrative artifact history.
- Methods counts 138+127=265 conflict with Table 3 total 264; preserve both and keep reconciled unique-person count unknown.
- Always/never acceptance classifications use only two inaccurate-advice cases per physician; not a stable trait or long-term clinical error rate. Unknown exclusions are not zero.
- Combined long, specialty-specific long and wide files are alternate representations of the same experiment. Exact row correspondence unverified; never add as independent samples.

## HR005 Glickman–Sharot — Human–AI feedback loops

Family `glickman-sharot-biased-human-ai`; new experimental family relative to this register, inventory source ID null. It has no operational collector or canonical admission.

- Task: Experiment2 moving-dot numerical estimation
- Stakes: Prolific laboratory-style online task with performance bonuses
- Expertise: General online adult participant pool; professional expertise not established
- Adviser kind: Hard-coded accurate/biased/noisy algorithms in Experiment2 only
- Model identity basis: No commercial model release identified for Experiment2
- Baseline: Main:30 baseline trials then three 30-trial algorithm blocks in Latin-square counterbalanced order. Each extension:30 baseline trials then five 30-trial exposure blocks, coded 1 baseline and 2–6 exposure.
- Followup kind: within_session
- Conditions: Main Experiment2: accurate, biased and noisy; Separate repeated-accurate extension; Separate repeated-biased extension
- Family scope: Experiment 1 includes CNN; Experiment 3 includes Stable Diffusion 2.1. Configured-algorithm/no-commercial-checkpoint description applies only to Experiment 2.

Coverage: collection period: April2021–March2024; online publication date: 2024-12-18; journal issue: 2025-02; artifact revision: ed7b66035135c39c910a3ba4ddcce4b5dafc3b78; update frequency: Fixed experiment release; no scheduled refresh verified; collection period scope: Family-wide reporting summary, not independently established Experiment2-specific dates..

### Source-backed findings

- Main Experiment 2 has 120 participants; accurate and biased extensions have 50 participants each. Preserve three distinct cohort/subexperiment identities within one family; extensions are not duplicate exports. Verification: `current_documentary_verification`. [Primary paper PDF with appended reporting summary](https://www.nature.com/articles/s41562-024-02077-2.pdf), [Collection and experiment identities](https://github.com/affective-brain-lab/BiasedHumanAI/blob/ed7b66035135c39c910a3ba4ddcce4b5dafc3b78/README.md)
- Independent estimates after previous algorithm exposure permit within-session bias/error comparisons. Current pre-advice judgments can reflect prior exposure; not delayed retention or months-long deskilling. Verification: `current_documentary_verification`. [Primary paper PDF with appended reporting summary](https://www.nature.com/articles/s41562-024-02077-2.pdf)
- Signed error is response minus evidence; absolute error is the absolute difference. Opposite signed errors may cancel despite substantial absolute error; preserve different estimands. Verification: `current_documentary_verification`. [Primary paper PDF with appended reporting summary](https://www.nature.com/articles/s41562-024-02077-2.pdf), [Measure definitions in static text, never executed](https://github.com/affective-brain-lab/BiasedHumanAI/blob/ed7b66035135c39c910a3ba4ddcce4b5dafc3b78/Exp2/Analysis/analysisExp2B.m)
- Main biased/noisy conditions did not show significant absolute-error change against baseline (all P>0.14), although directional signed bias changed. Different estimands: bias increase is not established general accuracy worsening or durable skill loss. Paper pp 6,8; no participant recomputation. Verification: `current_documentary_verification`. [Primary paper PDF with appended reporting summary](https://www.nature.com/articles/s41562-024-02077-2.pdf)

Cohorts: main-exp2 (120 analyzed); accurate-extension (50 analyzed); biased-extension (50 analyzed).

### Artifact references and rights

- [hr005_paper](https://www.nature.com/articles/s41562-024-02077-2.pdf): Primary paper PDF with appended reporting summary. Access `public_primary_read`; rights `declared_license` (CC-BY-4.0). Article-specific CC BY4.0 with third-party credit-line caveats; does not license separate CSVs, radiographs or stimulus images.
- [hr005_readme](https://github.com/affective-brain-lab/BiasedHumanAI/blob/ed7b66035135c39c910a3ba4ddcce4b5dafc3b78/README.md): Collection and experiment identities. Access `public_primary_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr005_biased](https://github.com/affective-brain-lab/BiasedHumanAI/blob/ed7b66035135c39c910a3ba4ddcce4b5dafc3b78/Exp2/Data/Exp2-Biased.csv): Biased extension artifact identity only. Access `metadata_only_no_rows_acquired`; rights `unknown`; Git blob `f9508490b19dfe0ed06dde1a673121af23319210`; 205193 bytes. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr005_tree](https://github.com/affective-brain-lab/BiasedHumanAI/tree/ed7b66035135c39c910a3ba4ddcce4b5dafc3b78/Exp2): Experiment2 directory metadata. Access `public_metadata_read`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.
- [hr005_analysis](https://github.com/affective-brain-lab/BiasedHumanAI/blob/ed7b66035135c39c910a3ba4ddcce4b5dafc3b78/Exp2/Analysis/analysisExp2B.m): Measure definitions in static text, never executed. Access `static_source_text_read_not_executed`; rights `unknown`. No artifact-specific redistribution license independently established; article and code rights do not propagate to data.

Schema example: inherited_header_reference_only; status `inherited_not_current_data_read`. Field names only: `evidence`, `response`, `responseAI`, `block`. No original participant sample row is included.

### Limitations and evidence identity

- Artificial perceptual task and short exposure constrain real-world/professional generalization.
- CSV header/prefix remains inherited. Four expected fields and measure definitions are verified through one static MATLAB source read, not data parsing or script execution; responseAI header claim remains inherited.
- Unknown CSV reuse rights remain distinct from the article CC BY statement.
- No participant IDs, row-level responses or cross-study linkage.
- Reported analyzed cohort Ns sum to 1,401; this is not all recruited people. Exp 1 human–human level 2 excludes 14 of 64, and a separate 30-person image-rating panel has unresolved relation to that sum.
- Do not infer a family-wide single adviser/model identity from the deliberately bounded Experiment 2 focus.
- Exp2.csv, Exp2-Accurate.csv and Exp2-Biased.csv belong to one family but distinct cohorts/subexperiments.
- Paper figures, repository data and analysis descriptions represent the same underlying experiment; no added independent evidence from republishing.
- Main Experiment 2 uses three within-person adviser blocks, not 360 independent people.
- Experiment 1 reuses level 1 source human judgments across four network conditions; baseline/interaction phases use the same level 3 people. These are contextual family dependencies, not extra Experiment 2 observations.

## Offline implementation and acceptance separation

[Paper ledger](../../../data/evidence-program/research/okamura-aggregate-ledger.json) is a manually curated aggregate factual summary. [Validator](../../../tools/evidence_program/validate_okamura_summary.py) checks one study, seven count assertions, five group counts, exact documentary profile, nonnegative bounded integers and denominator identities. It cannot extract a paper or verify a workbook. The paper source-byte SHA-256 is null.

- 194 recruits = 116 completers + 78 excluded.
- 116 × 15 = 1,740 repeated checkpoint decisions.
- 1,236 automatic + 504 manual = 1,740. Correct 1,282 is a published aggregate, with 458 incorrect derived arithmetically.
- Completers by group: NoTCC 28, Visual 18, Audio 22, Verbal 29, Anthro. 19. Recruits per group from the earlier workbook review are deliberately excluded from this paper ledger.

[Provisional decoder](../../../tools/evidence_program/decode_okamura_decisions.py) accepts only the explicitly synthetic fixed study in memory. It is not an XLSX reader. It uses provisional bit weights 16/8/4/2/1 inferred from the earlier field order and code19 example, not an independently verified dictionary: for automatic, judgment, ground truth, operational over-trust flag and cue flag. Code 19 is a synthetic regression example: automatic, negative judgment and truth, both raw flags. That test cannot establish the actual source mapping.

- Zero is a valid code; None/blank is missing. Booleans, numeric strings, noninteger numbers, nonfinite values and values outside 0–31 fail.
- Synthetic inputs have exactly 15 checkpoints and fixed group labels, bounded row keys and explicit completer/excluded status. Only declared completers contribute to simulated author-analysis summaries; excluded cells remain separately counted.
- At most 512 synthetic rows, depth 6, 40,000 nodes and 128-byte text fields. No file I/O, network, execution, fitting, credentials or arbitrary field passthrough. Unknown fields and duplicate row keys fail. No identifiers leave aggregate output.
- Baseline checkpoints 1–6, transition 7–9 and later 10–15 are within-session. NoTCC receives reliability information; it is not an uninformed baseline.
- Raw over-trust/cue bits remain operational codes, not observed beliefs or proof of visible cue delivery. The inherited NoTCC ambiguity stays unresolved.
- Public tests are self-authored synthetic inputs plus the curated aggregate facts. No source rows or workbook fixtures are shipped.

### Proposed real-workbook acceptance, held

The proposed scope is Figshare article 11538792/v1, file 20725707 only, expected 28,147 bytes, hard acquisition cap 65,536 bytes. The earlier SHA-256 claim `5d57d46fb768c1782ada806e70250d37494db6e1a3354ca56b15b773d249bda7` is inherited, not a current integrity result. No network path is implemented.

Before any future acquisition, establish permission and adult deidentified task-only scope from allowed documentation. If that gate cannot be established, stop. A separately authorized inspection would then verify exact schema/dictionary and bytes, retain blank/zero semantics, reproduce 194/116/1,740/1,282 and mode/group totals, and document any discrepancy without changing targets. Only ephemeral within-study keys may preserve repeated-observation dependence; never publish identifiers or link people across studies. No simulator imagery or source scripts/notebooks are part of this proposal.

## Comparison with frozen 64 and ten earlier catalogs

All 64 source IDs and ten catalog files were compared at exact current-base Git blobs: 53 earlier collections, 404 artifact references and 50 candidate-by-catalog comparison cells. No matching experimental family, paper/dataset DOI, repository artifact or shared cohort was established. This limited novelty statement is not proof that participant overlap is impossible. No cross-study person matching was attempted.

- [adoption-productivity](../../../data/evidence-program/research/adoption-productivity.json): 5 collections; 41 artifact references. Workplace/customer-support productivity and learning evidence is conceptually adjacent, but the school, MTurk, drone, physician and perceptual cohorts here have no established shared study, artifact or participant linkage. AP003 learning is not the Bastani school experiment.
- [chinese-safety-evaluations](../../../data/evidence-program/research/chinese-safety-evaluations.json): 8 collections; 49 artifact references. Model safety question/response evaluations are distinct from human participant decisions and trust calibration; shared AI terminology supplies no family or cohort identity.
- [concentration-dependencies](../../../data/evidence-program/research/concentration-dependencies.json): 5 collections; 28 artifact references. Ownership, operational dependencies and institution surveys do not identify these experimental human cohorts or measurements.
- [historical-capability-backfills](../../../data/evidence-program/research/historical-capability-backfills.json): 5 collections; 46 artifact references. Historical machine benchmark archives have different task/observation units; human evaluation within WMT does not identify any present experimental cohort.
- [open-model-diffusion](../../../data/evidence-program/research/open-model-diffusion.json): 5 collections; 37 artifact references. Access/weight licensing and ecosystem metadata do not identify the experimental adviser versions or human cohorts here.
- [organizational-safety](../../../data/evidence-program/research/organizational-safety.json): 5 collections; 50 artifact references. Organization safety reports may discuss human oversight but do not establish these independent experiments as developer-card data or institutional practice effects.
- [persuasion-information](../../../data/evidence-program/research/persuasion-information.json): 5 collections; 30 artifact references. Information judgments and persuasion are conceptually adjacent to Gaube/Glickman decision outcomes; distinct authors, tasks and cohorts. No shared underlying study established; belief change is not substituted for objective accuracy.
- [robotics-physical](../../../data/evidence-program/research/robotics-physical.json): 5 collections; 35 artifact references. Okamura uses simulated drone decisions by humans, not BARN/RoboArena/PhAIL physical robot performance. Distinct studies, units and cohorts.
- [scientific-progress](../../../data/evidence-program/research/scientific-progress.json): 5 collections; 46 artifact references. I4R team comparisons and RE-Bench human/AI baselines are adjacent concepts but distinct tasks/cohorts; no shared participants/artifact established.
- [training-data-feedback](../../../data/evidence-program/research/training-data-feedback.json): 5 collections; 42 artifact references. Human judgments after algorithm exposure differ from recursive model-training feedback and corpus availability. Shared feedback terminology establishes no dataset/study identity.

Frozen inventory links are contextual: GL034 may summarize a study, GL039/GL040 locate manuscript metadata, GL014–GL016 are developer-card families, CN014/CN015 concern trust/risk-perception attitudes and GL037 provides taxonomy. None substitutes for these independent experimental evidence chains.

Within-family dedupe preserves byte-identical Bastani CSVs, Bansal processing versions, Figshare/PLOS references and Gaube layout variants. Glickman main/extension cohorts remain distinct within one family; alternate exports are not silently treated as replications.

## Corrections and qualifications

- Baseline advanced from original research commit to 33fef 790; frozen 64 plus all ten earlier catalogs compared anew.
- Earlier participant-row snippets are omitted; schemas/metadata and paper aggregates replace row examples.
- Okamura CC BY4.0 and published counts are independently documentary verified, but current workbook bytes, header/dictionary and decoder acceptance are not.
- Inherited workbook hash, bit mapping, all-recruit group counts and NoTCC raw flags remain explicitly inherited; synthetic tests cannot confirm them.
- Bastani relative 17% exam result is not a percentage-point change or delayed retention; duplicate files are one cohort.
- Bansal final choice versus AI agreement does not establish an individual correct-to-wrong switch.
- Gaube advice was human-authored and scored by restrictive acceptance/rejection rules; no clinical system or unrestricted diagnostic accuracy.
- Glickman main and extensions retain distinct cohorts; signed bias and absolute error differ; within-session exposure is not durable deskilling.
- Bastani 839/943 survey populations and 2848 student-session observations are distinct; main unique regression students unknown.
- Bansal LSAT508×35% versus 100 per condition is an unresolved publication arithmetic conflict; pred 2 retains a problematic 1-conf clause.
- Gaube Methods 265 versus Table 3 264 participant count conflict remains explicit.
- Glickman family-wide Apr 2021–Mar 2024 dates and analyzed 1401 sum are not exact Exp 2 collection dates or all recruits; adviser identity varies across family experiments.
- Glickman directional bias and absolute-error accuracy are separate; main biased/noisy absolute-error comparisons are nonsignificant P>0.14. Main three-block and extension five-block designs cannot share a generic block2–6 mapping.

## Next actions

- HR-A01 (`completed_bounded_review`): Compare five candidate families against frozen 64 and all ten earlier research catalogs. 53 earlier collections, 404 artifact references and 50 candidate-by-catalog cells; no established same experimental family or participant cohort.
- HR-A02 (`implemented_offline`): Validate manually curated Okamura paper aggregates and synthetic inherited decoder behavior. Separate paper ledger and provisional synthetic-only decoder; no workbook reader or real-data acceptance.
- HR-A03 (`blocked_source_acceptance`): Resolve Okamura participant/privacy/schema permission before any workbook acquisition. Explicitly establish adult deidentified task-only scope and permitted bounded read; stop if unestablished. Independently verify dictionary/header, exact bytes, flags and all 194/116/1740/1282 targets only after that gate.
- HR-A04 (`open_documentary_only`): Clarify Bastani data rights and aggregate denominator/exclusion lineage without minors rows. Data reuse rights remain unknown. Preserve verified 839/943 survey populations,2848 student-session observations and unique-regression-student unknown; maintain baseline-survey/honors exclusion lineage with no minors rows.
- HR-A05 (`open_documentary_only`): Resolve Bansal dictionary correction, exact model provenance and data rights. Resolve conflicting 508×35% and 100-per-condition quantities, unresolved pred 2 1-conf clause, unknown exact checkpoint and data/content rights using public documentation only; no individual switching claim.
- HR-A06 (`open_documentary_only`): Resolve Gaube codebook and export identities/rights without clinical records. Resolve Methods 265 versus Table 3 264 and codebook/alternate-export identities through public aggregate documentation; retain human-authored advice and restrictive scoring, unknown data rights; no clinical or participant records.
- HR-A07 (`open_documentary_only`): Resolve Glickman Experiment 2 cohort/version identity and CSV rights. Retain main 120 and extension 50+50 identities, family-wide Apr 2021–Mar 2024 versus unknown specific-cohort dates, analyzed 1401 versus recruits and unresolved 30-person panel; establish CSV rights without participant data/scripts. Distinguish independent/joint decisions, main3 versus extension5 exposure blocks, signed bias versus absolute error and nonsignificant main accuracy comparisons.
- HR-A08 (`held_separate_review`): Design lossless proposed-contract mapping. Preserve study/cohort/condition/outcome and baseline/followup identities, clustering, raw flags, exclusions, rights and evidence strength; no schema change or canonical import without separate review.

## Standalone bounded follow-up prompts

Each prompt is complete on its own. These are proposed tasks, not active collection or authorization for participant-data access.

### HR-P01 Okamura permission and dictionary gate

Read-only public-source research only. For Okamura and Yamada, https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0229132 and Figshare https://api.figshare.com/v2/articles/11538792 (DOI 10.6084/m9.figshare.11538792.v1, file 20725707), inspect public paper and metadata only, at most 3 documents and 256KiB per metadata response. Establish whether explicit consent/deidentification documentation permits a bounded adult task-only workbook inspection. Current review acquired no workbook; CC BY4.0 does not settle privacy/schema permission. Do not fetch the XLSX. Return a proposed minimum dictionary/header-only scope or a clear hold. Separate paper totals 194/116/1740/1282 from unperformed workbook reconciliation and preserve NoTCC cue ambiguity. No login, outreach, bulk download, access-control bypass, source-script/notebook execution, simulator or model execution, participant-row acquisition, minors data, medical records, names or demographic data. No repository edits, canonical admission or deployment. Return source URLs, exact evidence locators, artifact-specific rights, verified versus unknown facts and a bounded stopping condition. Stop and report any access or permission gate; do not retry through another route.

### HR-P02 Bastani aggregates and rights

Read-only public-source research only. For Bastani et al., DOI 10.1073/pnas.2422633122, correction DOI 10.1073/pnas.2518204122 and https://github.com/obastani/GenAICanHarmLearning at 2f63dae1a01d51453826fe07ef5cf6678e339588, inspect at most paper/appendix,README and file-tree metadata. Never fetch outcome CSVs because they concern minors. Resolve artifact-specific rights and published aggregate denominators/exclusions; preserve relative 17% exam effect, immediate unaided phase, GPT-4-0613 and duplicate Git blob b6b9babbfafc2fe5f140498cb1ed96ea00890919. Public snippets containing individual rows must be skipped. No login, outreach, bulk download, access-control bypass, source-script/notebook execution, simulator or model execution, participant-row acquisition, minors data, medical records, names or demographic data. No repository edits, canonical admission or deployment. Return source URLs, exact evidence locators, artifact-specific rights, verified versus unknown facts and a bounded stopping condition. Stop and report any access or permission gate; do not retry through another route.

### HR-P03 Bansal schema and model provenance

Read-only public-source research only. For https://arxiv.org/html/2006.14779v3 and https://github.com/uw-hai/Complementary-Performance at 6cebab4ffd2b332ebec5e27e7632e7bf1c36ba5f, inspect paper,README and at most one documentation diff, no CSV bodies. Resolve conflicting LSAT 508 recruits/35% retention/100-per-condition quantities without inventing a reconciled total, and resolve pred2/conf2 dictionary correction, exact checkpoint documentation and data versus review/LSAT-content rights. Preserve separate unaided arm and absence of individual pre-advice switching evidence. Return documentary mappings or unknowns. No login, outreach, bulk download, access-control bypass, source-script/notebook execution, simulator or model execution, participant-row acquisition, minors data, medical records, names or demographic data. No repository edits, canonical admission or deployment. Return source URLs, exact evidence locators, artifact-specific rights, verified versus unknown facts and a bounded stopping condition. Stop and report any access or permission gate; do not retry through another route.

### HR-P04 Gaube scoring and rights

Read-only public-source research only. For Gaube et al., https://pmc.ncbi.nlm.nih.gov/articles/PMC7896064/ and https://osf.io/rjfqx/, inspect paper and at most 2 project/file-manifest metadata responses. No outcome CSV, clinical image or participant/medical data. Preserve Methods 265 versus Table3 264 as unresolved. Establish published acceptance/rejection scoring, whether codebook metadata resolves Q3/Q3n, and artifact-specific rights. Preserve human-authored AI-labeled advice, no unaided arm, 138+127 physicians, eight vignettes, and alternate long/wide exports as one experiment unless documented otherwise. No login, outreach, bulk download, access-control bypass, source-script/notebook execution, simulator or model execution, participant-row acquisition, minors data, medical records, names or demographic data. No repository edits, canonical admission or deployment. Return source URLs, exact evidence locators, artifact-specific rights, verified versus unknown facts and a bounded stopping condition. Stop and report any access or permission gate; do not retry through another route.

### HR-P05 Glickman cohort and outcome metadata

Read-only public-source research only. For https://www.nature.com/articles/s41562-024-02077-2 and https://github.com/affective-brain-lab/BiasedHumanAI at ed7b66035135c39c910a3ba4ddcce4b5dafc3b78, inspect paper,README and Exp2 tree metadata only, at most 3 documents. No participant CSV bodies or analysis scripts/notebooks. Separate family-wide Apr 2021–Mar 2024 reporting dates, analyzed 1401 versus recruitment, and the unlinked 30-person image panel. Verify Experiment 2 main 120 versus accurate/biased extension 50+50 cohort identities, baseline/exposure chronology, signed versus absolute error and data-specific rights. Keep within-session change separate from delayed skill retention. No login, outreach, bulk download, access-control bypass, source-script/notebook execution, simulator or model execution, participant-row acquisition, minors data, medical records, names or demographic data. No repository edits, canonical admission or deployment. Return source URLs, exact evidence locators, artifact-specific rights, verified versus unknown facts and a bounded stopping condition. Stop and report any access or permission gate; do not retry through another route.

### HR-P06 Human-reliance lossless mapping

Read-only public-source research only. Read mishakgg/pdoom-live at 33fef7908a6e449c8acd38f15b8d50d65a4923a3 and the later human-reliance research catalog/guide if present; record both inspected versions. Compare existing frozen proposed contract fields with study/cohort/condition/outcome, missingness, participant dependence, operational flags, immediate versus delayed followup, artifact-rights and verification-level needs. Inspect only those docs and contracts, at most 20 small files; no source-data fetch. Produce a gap table with examples using synthetic values. Do not assert a schema change is needed until a lossless mapping has been ruled out. No login, outreach, bulk download, access-control bypass, source-script/notebook execution, simulator or model execution, participant-row acquisition, minors data, medical records, names or demographic data. No repository edits, canonical admission or deployment. Return source URLs, exact evidence locators, artifact-specific rights, verified versus unknown facts and a bounded stopping condition. Stop and report any access or permission gate; do not retry through another route.

## Run and verify

From the repository root:

```bash
python tools/evidence_program/check.py
python -m unittest discover -s tools/evidence_program/tests -p "test_human_reliance*.py" -v
```

The aggregate check validates catalog provenance/rights, earlier-catalog exact identities, semantic holds, paper-ledger facts and synthetic negative tests. Existing frozen contracts, inventory, readers and catalogs remain unchanged. This does not replace web/database/pipeline suites or establish real-source extraction accuracy.

Top additions: Bastani for immediate unaided learning; Bansal for team decisions; Okamura for an explicitly licensed task-data candidate. Strongest limitation: no durable deskilling evidence, four unknown data licenses, unresolved denominators and an unopened workbook. Smallest implemented addition: manual Okamura aggregate checks and explicitly provisional synthetic five-bit arithmetic.
