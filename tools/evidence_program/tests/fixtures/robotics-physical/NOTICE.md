# BARN 2024 Table II attribution and fixture notice

`barn-2024-table-ii.json` is a manually curated, transformed excerpt of **Table II, Physical Results**, from:

**Autonomous Ground Navigation in Highly Constrained Spaces: Lessons learned from The 3rd BARN Challenge at ICRA 2024**, arXiv:2407.01862v1, submitted 2024-07-02 00:22:31 UTC.

Authors: Xuesu Xiao; Zifan Xu; Aniket Datar; Garrett Warnell; Peter Stone; Joshua Julian Damanik; Jaewon Jung; Chala Adane Deresa; Than Duc Huy; Chen Jinyu; Chen Yichen; Joshua Adrian Cahyono; Jingda Wu; Longfei Mo; Mingyang Lv; Bowen Lan; Qingyang Meng; Weizhi Tao; Li Cheng.

- Versioned source: https://arxiv.org/html/2407.01862v1
- Version and rights record: https://arxiv.org/abs/2407.01862v1
- Same-version PDF: https://arxiv.org/pdf/2407.01862v1 (Table II on PDF page 4, zero-based page 3)
- License: **Creative Commons Attribution 4.0 International (CC BY 4.0)**, https://creativecommons.org/licenses/by/4.0/
- License legal terms, including the disclaimer of warranties: https://creativecommons.org/licenses/by/4.0/legalcode.en

The version-specific HTML and abstract's license link were checked on 2026-10-08. This source-derived fixture and any source-derived Table II expected values reproduced in `../../test_robotics_barn.py` retain CC BY 4.0. They are **not** dedicated under the repository's `data/` CC0 dedication and are **not** relicensed by the repository's software license. The validator and test implementation remain repository software. Preserve source/author/license attribution and identify changes when redistributing the licensed excerpt. No author or organizer endorsement is implied. Source material is supplied as-is; the source license's warranty disclaimer applies.

## Transformation and verification

The slash-separated cells were manually transcribed into 60 entries with team, course number, one-based left-to-right reported position, and original numeric string or `X`. Published rank, success-total cells, parenthetical times, and course-average strings were retained separately. This implementation adds a bounded JSON schema identifier, one physical-event identifier, attribution/provenance metadata, and an explicit null manuscript hash. No outcome cell was changed. This is not a publisher artifact, raw log, HTML dump, or PDF copy.

All 60 outcome values and the publisher's summary cells were cross-checked against the versioned HTML and same-version PDF text extraction. PDF screenshots were unavailable; no visual PDF inspection is claimed. The JSON's `retrieved_at_utc` is the source-text observation time (2026-10-08 03:31:38 UTC), not the competition date or a run timestamp. The PDF text cross-check occurred at 03:32:19 UTC.

The pre-adapter curated transcription was 6,325 bytes with SHA-256 `2bf3c579cb2262719a0bf126b016ce48a4582fc5c65fb947ea3685e9186a203e`. It is not bundled separately. After the schema/event/null-hash additions and explicit transformation notice, the bundled UTF-8 file, including its final newline, is **6,584 bytes**, SHA-256:

`f79a2b58fa8771b766890627bf59e9f710acb5af1da397510dfdf4763cc8bd5e`

Both hashes identify **curated JSON bytes only**, never the complete HTML, PDF, paper, organizer website, trial log, or robot software. Full manuscript bytes were not saved or hashed; `manuscript_sha256` remains null. The reader separately reports an input-JSON hash and an order/deduplication-normalized curated-excerpt hash; neither is a manuscript hash.

## Interpretation limits

- There are 15 reported timed outcomes per team: three courses with five displayed positions. The four all-reported success counts are LiCS-KI 10, MLDA_EEE 5, AIMS 5, EIT-NUS 0. There are 20 numeric successes and 40 `X` failures in total.
- Published credited results are 6/9, 5/9, 5/9, and 0/9. Reconstructing up to three successful slots per course explains these counts; the organizer does not label individual credited run identities.
- LiCS-KI Course 2 has two 37-second entries tied at the third-fastest boundary. One of reported positions 1 and 2 could supply the remaining slot after positions 4 and 5. The reader retains that ambiguity; it does not choose an authoritative row.
- Displayed position is not an established chronological attempt number. There are no native run IDs or run timestamps. Keys are source-version coordinates. A later/reordered source version requires explicit trial reconciliation and is rejected by this v1-only reader.
- Published course averages remain independent publisher claims. LiCS-KI's 30 and 35 seconds are not the exact fastest-three means: those are 88/3 and 98/3 seconds. The reader does not recompute or replace the published averages. Published parenthetical team times 79 and 109 remain distinct from any later website decimals or calculations; those later-page values are not inputs here.
- `X` means reported failure with unknown time and cause, not a missing observation or zero-second completion. Reset counts, practice counts, checkpoints, hardware instance, interventions and time ordering are not established by this table. A protocol prohibition on intervention does not measure observed intervention counts.
- This is one staged physical-navigation competition excerpt. No simulation rows, cross-year pooling, continuous-deployment exposure, practical general-purpose autonomy, scoring, or catastrophe probability is established.

This notice does not establish reuse rights for the organizer website, videos, evaluated systems/checkpoints, underlying logs/course assets, or robot/evaluation-harness software. None of those artifacts are bundled or executed. Tests are offline and do not fetch sources. Structural validation and fixture-byte consistency are not independent scientific replication, legal approval, or canonical dataset admission.
