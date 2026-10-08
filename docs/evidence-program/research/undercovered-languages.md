# Undercovered languages and regions

Session 20, reviewed 8 October 2026 against main `82fd46330539bd484c80190c69868d71b2052f6e`. Source review is complete with explicit holds; operational admission remains pending. Publication progress is tracked in the [dated queue](research-session-review-queue.md). See the [separate JSON record](../../../data/evidence-program/research/undercovered-languages.json).

Retain eight scoped collections, with INE first, MERA ruEthics second and KoBBQ third. NIA needs an immediate denominator-revision warning. All remain research candidates; no corpus or live collector is admitted.

## ULR001 AnswerCarefully Japanese safety revision metadata

Public notice confirms the 24 December 2024 removal of two ACv1-test IDs that overlapped ACv2 development. ACv2, culturally annotated ACv2.2, borderline and ACv3 are separate populations. Native Japanese metadata adds split corrections and local adaptation context. Corpus contact-sharing/terms gate and purpose-limited no-redistribution license remain; no payloads acquired.

Overlap: GL020 is Japan AISI tooling/presets, not this originating NII collection. A future AISI evaluation using it shares the same stimulus provenance; do not count as independent coverage.

Next: Store the two-ID correction event and version/split relationships; leave corpus access and model-result ingestion closed.

Sources: [NII release notice](https://llmc.nii.ac.jp/answercarefully-dataset/) · [Dataset card and gate](https://huggingface.co/datasets/llm-jp/AnswerCarefully) · [Corpus terms](https://huggingface.co/datasets/llm-jp/AnswerCarefully/blob/main/LICENSE)

## ULR002 NIA Korean Internet Usage Survey correction lineage

Figure 93 was revised from 7.9% to 17.8% on 26 May 2026 because its base changed. Both exact denominator definitions remain unverified, explicitly null and held. The corrected PDF content and base labels remain unverified. Preserve publication date (31 March), filename token 260512, correction date, earlier headline and revision reason. XLSX catalog is KOGL Type 2; PDF rights remain unresolved.

Overlap: Same originating MSIT/NIA survey as GL026; Korean/English releases, tables, XLSX and press coverage are representations of a wave, not independent adoption observations.

Next: Keep GL026 subscription comparisons held; use only an authorized supplied original/revised figure-93 base-label excerpt and artifact-rights evidence to resolve the hold. Do not circumvent access restrictions.

Sources: [Report correction](https://nia.or.kr/site/nia_kor/ex/bbs/View.do?bcIdx=29198&cbIdx=99870&parentSeq=29198) · [Table correction](https://www.nia.or.kr/site/nia_kor/ex/bbs/View.do?bcIdx=29199&cbIdx=99870) · [XLSX catalog](https://www.data.go.kr/data/15086936/fileData.do) · [Unverified corrected PDF target](https://www.nia.or.kr/common/board/Download.do?bcIdx=29198&cbIdx=99870&fileNo=3)

## ULR003 KoBBQ Korean cultural-validation metadata

Metadata confirms 1,600 validation participants, adaptation codes and questions about perceived societal stereotypes rather than personal endorsement. The card says 268 templates/76,048 samples; viewer says 81.1k. Keep this version/count mismatch open. Actual survey filename is .json, despite README .jsonl. Dataset MIT and the separate ethical-use statement must both survive; no stereotype payloads retained.

Overlap: Existing naver_ai_pages is NAVER Labs HTML title/date/URL metadata with runner_wired=false, not NAVER AI/Cloud KoBBQ data. Organization-name affinity does not establish existing benchmark coverage. Retain BBQ upstream relation and deduplicate HF/GitHub representations.

Next: Prepare a metadata reconciliation of pinned card, viewer and directory revision; record counts separately and use .json manifest filename.

Sources: [Dataset card](https://huggingface.co/datasets/naver-ai/kobbq/blob/main/README.md) · [Validation documentation](https://github.com/naver-ai/KoBBQ/blob/main/data/README.md) · [Viewer metadata](https://huggingface.co/datasets/naver-ai/kobbq) · [Directory manifest](https://api.github.com/repos/naver-ai/KoBBQ/contents/data) · [MIT notice](https://github.com/naver-ai/KoBBQ/blob/main/LICENSE)

## ULR004 AraSafe Arabic natural/synthetic safety classification

Natural cohort 12,141 and GPT-4o synthetic cohort 12,264 are distinct, as are 12K ArabicQA safe additions. Table 7 reports Fanar-1-9B macro-F1 78.9%, accuracy 90.4% for natural-prompt binary classification. Table 2 dialect counts sum to 12,104, leaving a count mismatch. Dataset academic/noncommercial restriction does not establish redistribution terms; paper CC BY is separate.

Overlap: New originating collection. Future HELM/leaderboard or paper restatements would share source-result lineage; native Arabic does not establish population representativeness.

Next: Retain one Table-7 result with natural-cohort label and an unresolved count/rights issue; later review only explicit public clarification or metadata, not corpora.

Sources: [Repository metadata](https://github.com/qcri/AraSafe-benchmark) · [Paper](https://aclanthology.org/2025.findings-emnlp.529.pdf) · [Publication page](https://aclanthology.org/2025.findings-emnlp.529/)

## ULR005 ArabicMMLU native examination provenance

Published 14,575 questions/40 tasks cover eight named countries plus 3,014 Other questions. Safe test metadata ID 7183 confirms Egypt/Accounting/Univ, answer A; no model prediction. ID 7214 appears in both All/dev and Accounting/dev, demonstrating representation overlap, not dev/test leakage. GitHub CC BY-NC-SA versus HF CC BY-NC remains unresolved, alongside underlying examination rights.

Overlap: New originating collection; deduplicate by pinned release and source ID across All/subject configurations and downstream benchmark reports. Verified All/dev overlap does not establish split leakage.

Next: Keep both rights assertions with pinned card/packaging identifiers and safe ID 7183/7214 provenance; no commercial or general corpus admission until resolved.

Sources: [Repository](https://github.com/mbzuai-nlp/ArabicMMLU) · [Dataset card](https://huggingface.co/datasets/MBZUAI/ArabicMMLU/blob/main/README.md) · [Viewer metadata](https://huggingface.co/datasets/MBZUAI/ArabicMMLU) · [Paper](https://aclanthology.org/2024.findings-acl.334.pdf) · [All/dev metadata](https://huggingface.co/datasets/MBZUAI/ArabicMMLU/blob/main/All/dev.csv) · [Packaging revision](https://huggingface.co/datasets/MBZUAI/ArabicMMLU/commit/9ea4eb3da8b230ee33c0ad6deb996b5e7a7d7d41)

## ULR006 MERA original-text ruEthics Russian diagnostic

The original-text diagnostic has 645 text–ordered-actor-pair cases and 1,935 rows across three framings. Human criterion labels differ from model responses. Evaluation yields three sets of five MCC correlations and is excluded from aggregate ranking. Task-specific MIT is verified; upstream text provenance, original/v2 distinction and private submitted-response restrictions remain. No population-belief inference.

Overlap: GL006 framework coverage does not supply these original tasks. TAPE is upstream; repeated framings, mirrors and future aggregator results share provenance.

Next: Specify a case/framing-aware metadata fixture retaining all 15 metric slots; keep actual result values and public trace access null.

Sources: [Task documentation](https://mera.a-ai.ru/ru/text/tasks/4) · [Dataset card](https://huggingface.co/datasets/MERA-evaluation/MERA/blob/main/README.md) · [Task license](https://github.com/MERA-Evaluation/MERA/blob/release/benchmark_tasks/ruethics/README.md) · [FAQ](https://mera.a-ai.ru/ru/text/about)

## ULR007 Dutch Algorithm Register deployment declarations

IDA/ICTU declares In gebruik (translation: in use), start 2026-09, modified 6 October 2026 at 08:49, standard 1.0. Impact assessment is unfilled, not zero risk. The record’s risks and mitigations are operator declarations. Publisher permits scoped text reuse, with separate images/attachments and no-endorsement conditions; download payload/API not tested.

Overlap: Complementary to GL033 policy material and CD001 UK ATRS/CD004 OMB disclosures. Different jurisdictions and units; same product across agencies is not duplicate deployment, nor independent proof of supplier safety. No spend/workload/concentration denominator.

Next: Create one allowlisted IDA metadata record preserving native status and null assessment; later export inspection is optional and separate.

Sources: [IDA declaration](https://algoritmes.overheid.nl/nl/algoritme/27198742/85273997/ida) · [Text reuse conditions](https://algoritmes.overheid.nl/nl/footer/copyright) · [Archive documentation](https://algoritmes.overheid.nl/nl/footer/archief)

## ULR008 INE Spanish microenterprise AI adoption aggregates

The final release dated 22 October 2025 reports 7.5% for Q1 2024 and 13.4% for Q1 2025 among internet-connected enterprises with fewer than ten employees. These are two reference periods in one publication vintage. Native Spanish footnote, sector scope and statistical-enterprise definition are retained. INE-origin statistics have scoped commercial/noncommercial reuse; respondent counts and uncertainty remain unknown.

Overlap: GL022 shares European survey lineage but standard population is 10+ employed persons; under-ten series must not merge with it. Larger-enterprise overlaps require cell-level deduplication. LM003 ICT training shares infrastructure but differs in construct/reference period; no same-enterprise causal link.

Next: Use a two-row hand-curated specification; later authorize one bounded extractor through existing contracts only, with denominator/date tests below. No implementation in this review.

Sources: [Final release](https://www.ine.es/dyngs/Prensa/ETICCE20241T2025.htm) · [Methodology](https://www.ine.es/dynt3/metadatos/es/RespuestaDatos.html?oe=30169) · [Reuse notice](https://www.ine.es/ss/Satellite?L=0&c=Page&cid=1254735849170&p=1254735849170&pagename=Ayuda/INELayout) · [JAXI scope](https://www.ine.es/jaxi/Tabla.htm?L=0&tpx=76397)

## Bounded implementation specification

Use only the INE final-release HTML, methodology and reuse notice: at most three reads, 2 MiB each, no traversal. Produce exactly two proposed adoption records. No adapter, validator or new framework was built.

Acceptance requires:
- Exactly 7.5 and 13.4 with Q1 2024/Q1 2025 references and the same 2025 publication vintage
- Unchanged Spanish indicator/footnote plus separately marked translations; under-ten, internet-connected and sector scope intact
- Null achieved denominator, numerator and errors; no counts reconstructed from rounded percentages
- Stable observation identities separate from snapshot/version identities; changed denominators prevent automatic comparable-series joins
- No pooling with Eurostat 10+ or ICT-training indicators; mirrors add provenance
- Scoped INE rights, bounded fetches and no conversion into capability, national traits or p(doom)

The JSON contains coverage, update, access and rights fields, safe sample metadata and source locators. No exact upstream HTTP-byte identity is claimed. Eight standalone bounded prompts follow.

## Next actions and copy-ready prompts

All eight actions are unstarted. Public metadata does not clear corpus acquisition or redistribution; implementation remains deferred.

### ULR001-A01 / ULR001-P01: Record Japanese split corrections

P1; source ULR001; status `bounded_follow_up_not_started`.

Review only the public notice https://llmc.nii.ac.jp/answercarefully-dataset/, card https://huggingface.co/datasets/llm-jp/AnswerCarefully, and terms https://huggingface.co/datasets/llm-jp/AnswerCarefully/blob/main/LICENSE. Produce a metadata-only release/correction manifest for the two ACv1 IDs removed on 2024-12-24, preserving original Japanese labels and separately marked translations. Separate ACv2, ACv2.2, borderline and ACv3 populations, split relations and rights. Do not log in, accept terms, share contacts, acquire corpus files, reproduce harmful payloads or run evaluations. Stop at any gate; leave rights and score-comparability gaps explicit.

### ULR002-A01 / ULR002-P01: Preserve Korean denominator revision

P0; source ULR002; status `bounded_follow_up_not_started`.

For GL026, use https://nia.or.kr/site/nia_kor/ex/bbs/View.do?bcIdx=29198&cbIdx=99870&parentSeq=29198, https://www.nia.or.kr/site/nia_kor/ex/bbs/View.do?bcIdx=29199&cbIdx=99870, and https://www.data.go.kr/data/15086936/fileData.do to preserve the dated 2026-05-26 figure-93 revision, 7.9 and 17.8, Korean labels, filename token, and separate old/new denominator-definition fields. Both definitions remain unverified; do not infer them. Corrected PDF content is unverified and remains an access hold; do not attempt another route to bypass restrictions. If the user supplies an authorized original/revised excerpt, verify its base labels and artifact rights; otherwise finish with a correction-only record and comparison hold. No respondents, workbook bulk download, login or outreach.

### ULR003-A01 / ULR003-P01: Reconcile KoBBQ counts

P1; source ULR003; status `bounded_follow_up_not_started`.

Inspect only https://huggingface.co/datasets/naver-ai/kobbq/blob/main/README.md, https://github.com/naver-ai/KoBBQ/blob/main/data/README.md, https://api.github.com/repos/naver-ai/KoBBQ/contents/data, and https://github.com/naver-ai/KoBBQ/blob/main/LICENSE, plus the viewer count label. Reconcile documented 268 templates/76,048 samples with the displayed 81.1k test rows without downloading full samples. Record 1,600 validation participants, adaptation codes, questionnaire-perception caveat, original Korean short label and marked English gloss. Keep MIT notice and separate ethical-use statement; use actual .json manifest filename. Do not reproduce stereotypes, fetch respondents or run models. Leave score comparability held if version counts cannot be resolved from metadata.

### ULR004-A01 / ULR004-P01: Reconcile AraSafe cohort counts

P1; source ULR004; status `bounded_follow_up_not_started`.

Review only https://github.com/qcri/AraSafe-benchmark root/README and directory metadata plus https://aclanthology.org/2025.findings-emnlp.529.pdf. Preserve separate paper cohorts of 12,141 natural and 12,264 GPT-4o synthetic prompts and 12K ArabicQA safe additions. Record only Fanar Table-7 macro-F1 78.9 and accuracy 90.4 for natural binary classification, including model-label variation and author relationship. Keep the Table-2 dialect total 12,104 discrepancy open unless public documentation resolves it. Check explicit dataset terms separately from paper CC BY. No JSONL bulk acquisition, harmful prompts, attack instructions, model/source execution, login or outreach.

### ULR005-A01 / ULR005-P01: Resolve ArabicMMLU rights

P1; source ULR005; status `bounded_follow_up_not_started`.

Inspect https://github.com/mbzuai-nlp/ArabicMMLU, https://huggingface.co/datasets/MBZUAI/ArabicMMLU/blob/main/README.md, public manifests and https://aclanthology.org/2024.findings-acl.334.pdf. Preserve CC BY-NC-SA 4.0 versus CC BY-NC 4.0 as conflicting assertions; do not infer upstream examination clearance. Record 14,575 questions/40 tasks, eight named countries plus 3,014 Other, question versus instruction language and answer-label script. Verify at most five benign IDs across All and one task using metadata only; retain ID, country, subject, level, split and source URL. All/dev duplication is not dev/test leakage. No full CSV/Parquet, question text, source/model execution, login or outreach.

### ULR006-A01 / ULR006-P01: Map Russian diagnostic protocol

P1; source ULR006; status `bounded_follow_up_not_started`.

Use https://mera.a-ai.ru/ru/text/tasks/4, https://huggingface.co/datasets/MERA-evaluation/MERA/blob/main/README.md, https://github.com/MERA-Evaluation/MERA/blob/release/benchmark_tasks/ruethics/README.md, and https://mera.a-ai.ru/ru/text/about for a metadata-only ruEthics protocol record. Preserve 645 ordered-actor-pair cases versus 1,935 rows, three Russian framings with marked translations, human criteria and three sets of five MCC values. Keep original-text lineage distinct from v2.0, disclose selection/filtering and diagnostic exclusion. Confirm task MIT scope, retaining TAPE text provenance. Do not acquire full situations, private submissions, model traces or execute models; use only sample 1289 metadata and leave missing results null.

### ULR007-A01 / ULR007-P01: Map Dutch deployment declaration

P1; source ULR007; status `bounded_follow_up_not_started`.

Read only IDA https://algoritmes.overheid.nl/nl/algoritme/27198742/85273997/ida, rights https://algoritmes.overheid.nl/nl/footer/copyright, and archive documentation https://algoritmes.overheid.nl/nl/footer/archief. Extract one deployment declaration with organization, status, declared start, modification display, publication standard and missing impact-assessment field. Preserve Dutch labels and separately marked translations. Classify hallucination and mitigation descriptions as operator claims, never audited safety or risk scores. Keep CD001/CD004 methodological overlap and jurisdiction differences; no aggregate adoption/concentration share. Do not crawl the whole register, invoke the chatbot, download attachments or assume export/API stability.

### ULR008-A01 / ULR008-P01: Specify Spanish AI adoption

P0; source ULR008; status `bounded_follow_up_not_started`.

For INE, inspect only https://www.ine.es/dyngs/Prensa/ETICCE20241T2025.htm, https://www.ine.es/dynt3/metadatos/es/RespuestaDatos.html?oe=30169, and https://www.ine.es/ss/Satellite?L=0&c=Page&cid=1254735849170&p=1254735849170&pagename=Ayuda/INELayout, at most one HTML document each, 2 MiB each. Prepare exactly two AI observations from the under-ten section: Q1 2024=7.5 and Q1 2025=13.4, both reproduced in the 2025-10-22 final publication. Preserve Spanish label and footnote plus marked English glosses, internet-connected base, sector scope, statistical-enterprise unit, survey year, reference quarter and publication vintage. Keep counts and errors null. Link GL022/LM003 without pooling populations/indicators. No respondents, archive traversal, JAXI expansion, adapter code or p(doom) conversion.
