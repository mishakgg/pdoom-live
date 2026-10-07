# Chinese language evidence preparation guide

English operational preparation for pdoom.live • 7 October 2026

## Purpose and limits

Build Chinese-language coverage through traceable sources, verified identities and faithful interpretation. Start with established datasets and their native records, then investigate evidence gaps. Keep beliefs, capability measurements, deployment events and governance context separate.

This package prepares an operational workflow, lookup aids and wholly synthetic semantic cases. It does not implement a collector or parser, run a crawl, call paid models, change production behavior, ingest new evidence or modify the frozen Step 3 contract. It does not establish human translation expertise, legal permission or complete Chinese coverage. The 24 Chinese source families remain candidates; their availability and rights caveats still apply.

Authoritative dependencies are the [dataset specification](dataset_spec.md), [frozen contract](../../tools/evidence_program/contracts/dataset.schema.json), and [24-record Chinese source inventory](../../data/evidence-program/chinese_sources.json). The [reference manifest](../../data/evidence-program/chinese/reference_manifest.json) identifies these repository-native paths and fingerprints. [Repository checks](../../tools/evidence_program/README.md) validate preparation-file consistency and partial schema-fragment shapes; they are not an extractor or a test of language understanding.

- [Alias lookup](../../data/evidence-program/chinese/aliases.json): primary-evidence-backed name mappings, non-equivalence warnings and unresolved names. A verified mapping is still subject to identity review.
- [Query lexicon](../../data/evidence-program/chinese/query_lexicon.json): 30 bilingual concepts and 14 proposed search templates. These are retrieval aids, not source quotations or an executed search campaign.
- [Synthetic test cases](../../data/evidence-program/chinese/test_cases.json): 25 invented semantic examples with expected decisions and partial contract-shaped fragments. These are not complete dataset records, real quotations or demonstrated extractor performance.

## Separate the questions before searching

Define the desired record family and outcome before selecting search words. Extinction, catastrophic harm, loss of control, an AGI milestone and success on a benchmark are different targets. An article containing a percentage and the word risk is not necessarily a probability forecast.

Use the contract's 13 record types without inventing language-specific replacements:

1. source_artifact holds an original or translated source, its language, provenance and access status.
2. actor represents a person, organization or defined collective. Model and product names do not create additional actor kinds.
3. statement retains an attributed original, normalized wording and explicit_numeric, explicit_qualitative or model_inferred_signal distinction.
4. model_version identifies the model actually evaluated, including uncertain or mutable provider labels.
5. release_event separates announcement, preview, API access, weights release, withdrawal and update.
6. benchmark_run holds protocol-specific capability results, including evaluator independence and contamination status.
7. resource_observation holds compute, cost, price, adoption and other explicitly defined measurements.
8. safety_evaluation holds a domain-specific test, limitations and thresholds. Test failure rates are not global catastrophe probabilities.
9. incident holds an alleged or observed event with verification and causation considered separately.
10. forecast_question defines the exact outcome, population, condition, horizon and resolution rule.
11. forecast supplies an attributed answer to that exact question revision.
12. resolution records evidence-backed adjudication. Silence or an unresolved question is not a negative outcome.
13. snapshot freezes exact revisions and their knowledge cutoff. It does not certify correctness or publishability.

Generic political, ethical or marketing language may be useful source context without supporting a forecast. A model announcing a probability in generated chat is not a statement by its developer. Chinese-language prose does not establish nationality; English prose from a China-based organization remains English.

## Source priorities and acquisition decisions

The order below is a proposed work sequence for a later acquisition run. It does not change the source inventory or claim that the run has occurred. Verify the live page and its artifact-specific rights again when acquiring material. Source IDs such as [CN019](https://github.com/open-compass/opencompass) are inventory identifiers, not substitutes for contract source_artifact revision references.

### Comparable capability and progress evidence

- CN019 OpenCompass: prioritize versioned configurations, evaluator provenance and dated score snapshots. The repository is readable, but the interactive ranking returned no usable score rows during the inventory check. Do not claim a historical score export exists until inspected.
- [CN020](https://github.com/flageval-baai/FlagEval) FlagEval: prioritize the core toolkit and official report index, then inspect individual dated reports or snapshots. A repeat citation is not an independent run. Some platform and PDF reads failed; toolkit access alone does not establish leaderboard access.
- [CN021](https://github.com/hkust-nlp/ceval) C-Eval: preserve the benchmark release, native question/run IDs, split, prompting and scoring configuration. Its dataset is CC BY-NC-SA 4.0 while its code has a separate MIT license. Review the proposed use before copying or distributing question data.
- [CN022](https://github.com/haonan-li/CMMLU) CMMLU: preserve the same metadata and distinguish zero-shot from five-shot results. Dataset CC BY-NC-SA 4.0 does not establish a permissive license for every other artifact. The author-linked dataset URL redirected; retain that provenance and verify the actual data revision.

These sources can support measured-progress work once comparable observations are available. Do not splice C-Eval and CMMLU accuracies into one trajectory, turn a current ranking into a historical series, or extrapolate saturated benchmarks directly into an AGI arrival date. Preserve metric changes, inference budgets, tools, scoring models and model identities. A vendor table remains reported evidence unless the underlying measured run is actually available.

### Current releases and historical anchors

- [CN001](https://www.deepseek.com/news/) DeepSeek research index: identify dated release articles and papers; reconcile the existing catalog before adding duplicate entries.
- [CN024](https://api-docs.deepseek.com/) DeepSeek API documentation: record request names separately from documented serving models and retirement/alias changes. The same API string can refer to a different serving model over time.
- [CN002](https://github.com/deepseek-ai/DeepSeek-R1) DeepSeek R1: retain as a historical technical anchor and pair with CN001/CN024; it is not evidence of the newest model.
- [CN003](https://github.com/QwenLM/Qwen3) Qwen3: retain historical results and use the official documentation/redirected blog route to discover successors. The new blog body did not parse in the inventory check.
- [CN004](https://github.com/zai-org/GLM-4.5) GLM: pin the exact README/report/model version; the repository name and its current mixed-generation README are not an immutable checkpoint.
- [CN005](https://github.com/MoonshotAI/Kimi-K2) Kimi K2: use as a historical anchor and follow verified official company/product links for successors. Keep Kimi distinct from Moonshot AI as product versus organization.
- [CN006](https://github.com/MiniMax-AI/MiniMax-M1) MiniMax M1: preserve historical configurations; use verified official news/model links for successor discovery, while acknowledging that the news index body did not parse.
- [CN007](https://ernie.baidu.com/blog/posts/ernie4.5/) ERNIE 4.5: pair the release article with the verified official ERNIE blog index. Do not substitute an old Baidu research maintenance page for the original material.
- [CN008](https://seed.bytedance.com/zh/) ByteDance Seed: discover first-party releases and author papers. The site has explicit reuse restrictions; seek separately licensed artifacts rather than assuming website prose is open.

For each release distinguish publication, announcement, preview, actual availability and evaluation dates. A promised future API launch is an attributed plan, not completed access. If a provider labels a version without making it immutable, retain that uncertainty. Release frequency and administrative deployment counts do not themselves measure capability improvement.

### Qualitative risk and scientific context

- [CN009](https://idais-beijing.baai.ac.cn/?lang=zh) BAAI Beijing consensus: retain collective authorship and endorsement relationships. Repeated signature lists must be deduplicated; do not generate one numerical belief per signer.
- [CN011](https://air.tsinghua.edu.cn/info/1007/2532.htm) Tsinghua AIR: preserve the fact that the text is an official Chinese translation of an international statement and recover the matching original before cross-language deduplication.
- [CN018](https://ai45.shlab.org.cn/research/zh/posts/safework-f1/) AI45 SafeWork-F1: prioritize bilingual terminology review. Its Chinese introduction uses catastrophic risk where the English counterpart uses existential risk. That difference must remain visible, not be flattened into a universal synonym. The linked large PDF did not render in the inventory check.
- [CN010](https://www.shlab.org.cn/news/5444269) Shanghai AI Laboratory workshop report: separate institutional reporting, research questions and attributed quotations. A question posed at a workshop is not a participant's belief.
- [CN017](https://arxiv.org/abs/2310.19852) alignment review: survey means literature review here. Trace numerical claims to their original sources rather than attributing all cited forecasts to every coauthor.

### Policy and deployment metadata

- [CN012](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm) interim service measures and [CN013](https://www.most.gov.cn/kjbgz/202109/t20210926_177063.html) ethical norms: keep normative requirements in policy context. Current legal obligations require a separate current-status check; the source inventory is not legal advice.
- [CN023](https://www.cac.gov.cn/2024-04/02/c_1713729983803145.htm) CAC filing/registration series: distinguish the dated attachment, as-of date, index-page date and later updates. Its August 2026 attachment failed to download in the inventory check. Do not treat service filings, local application registrations and on-device notices as disjoint counts of unique frontier models.

### Public attitudes and survey evidence

- [CN014](https://kxxyj.magtechjournal.com/kxxyj/CN/abstract/abstract23402.shtml), [CN015](https://kxxyj.magtechjournal.com/kxxyj/CN/Y2025/V43/I10/2066) and [CN016](https://journals.sagepub.com/doi/abs/10.1177/0266666919893411) are original China-focused attitude studies. Seek the actual questionnaire, fieldwork dates, recruitment, weighting, nonresponse, wave identifiers and data-availability statement before comparisons. No reusable respondent microdata was verified in the inventory.
- A percentage of respondents endorsing a proposition is not the probability of the proposition. A source-published median probability is a different statistic and must be attributed to a wave-specific collective, with a separate aggregator.
- Do not infer national representativeness from a national online or quota sample. A review article, a risk-perception scale and a probability-elicitation survey are not interchangeable.

## Identity and alias handling

Use the alias file as a source-supported lookup aid, not an automatic merge table. Its verified entries mean that the specified primary evidence supports the stated name relation. They do not prove ownership of an unrelated account, current employment, citizenship, source authenticity for every future page or production eligibility.

Never flatten every names entry into actor.data.aliases. Only an evidence-supported name-equivalence relation is an alias candidate; operator, team, family, checkpoint and product relationships remain separate. Keep the exact relationship. An organization abbreviation can be a name variant; a team belonging to a company, a product made by it and a model family are different relationships. Kimi is not automatically Moonshot AI as an actor; GLM and ERNIE are not people. The preparatory field actor_type_representable expresses type compatibility only. It grants no review, rights or publication approval. All mappings require human review and automatic merging remains disabled.

For a person's bilingual name, require a first-party faculty, author or institutional page connecting the scripts. Common romanizations, initials, reordered given/family names and homophones are candidates, not identifiers. Keep unresolved forms out of actor.data.aliases until resolved. Do not infer that two occurrences of Zhang Peng, Yi Zeng or an abbreviated surname denote the same person without the contextual evidence.

Record a role or affiliation for the period supported by its source; do not project a current biography into a historical utterance. An original Chinese name, English publication name and external identifier can coexist. If no verified external identifier is available, leave the list empty rather than inventing one. Separate identity confidence from whether a particular quotation was accurately attributed.

## Retrieval and screening workflow

First ask whether the evidence already exists upstream. A dataset, survey release, benchmark report or source-native row may be linked instead of copied. Preserve upstream dataset ID, exact release, native record key, schema name/version and source reference. Record ordered versioned transformations such as script normalization for search, percent-to-probability conversion or relative-date resolution. The upstream record remains authoritative within its own scope.

Use the query lexicon to expand Chinese, traditional-script and English searches separately. Log the actual query, domain and match language. Search-result snippets and translated headlines establish discovery only; they do not substitute for the original text and surrounding context. Prefer primary institutional pages, author versions, original publishers and official repositories. Reposts can help find the original but do not automatically become independent evidence.

Screen each candidate for record family, relevant outcome, actual speaker, source language, source version, timestamp precision, acquisition method and rights. Preserve a reason for rejection or uncertainty. A failed search is an observed coverage gap, not evidence that a person assigns low risk or has no opinion. Do not bypass access denial, paywalls, login controls or rights restrictions. Do not contact authors, submit forms or upload model/data artifacts under this preparatory item.

## Preserve the original and its coordinates

Keep the permitted original text immutable. Store normalized, simplified-script, OCR-corrected and translated versions as derivatives. If original bytes were not captured, do not claim a content hash or possession of the full source. Source excerpts still require appropriate rights even when technically easy to copy.

Choose and explicitly name a coordinate system. The fixtures use zero-based Unicode code-point positions with an exclusive end, measured against input.original_text exactly as stored. An emoji can occupy one code point but two UTF-16 code units and several UTF-8 bytes. Fullwidth punctuation or decimal marks can change bytes under compatibility normalization. Combining marks and emoji sequences introduce additional distinctions between code points and visually perceived characters.

Never transfer offsets blindly between UTF-8 bytes, Unicode code points, UTF-16 code units, PDF extraction text and displayed characters. For a future pipeline, retain a transformation/alignment map from every derived span back to the immutable original, documenting inserted/deleted text, OCR corrections, whitespace and normalization. Recompute and verify the original substring before accepting an excerpt. A valid hash on the normalized text does not identify the original bytes.

The frozen v0.1 evidence.locator is a descriptive string, not a tested automatic span-mapping mechanism. A locator can state the paragraph/table cell or video timestamp plus the named coordinate convention. The fixture's quote_span object is preparatory test metadata, not an extra field to insert into the frozen evidence schema. ZH001 demonstrates the offset issue; no automatic alignment mapper has been implemented or validated here.

## Normalize numbers without changing meaning

Normalize only an interpretation copy. Preserve the raw form beside every accepted result and document the conversion. Exact empirical values and probabilities are decimal strings. Structural counts such as revision numbers, offsets and sample_size remain JSON integers.

- Fullwidth １５．５％ can normalize to a probability string 0.155 when the source really states an event probability. The same expression can remain percent 15.5 for a measurement.
- 百分之五 is 0.05 as probability; 千分之一 is 0.001; 萬分之三 is 0.0003. Do not confuse percent, per-thousand and per-ten-thousand.
- 两成 can mean two tenths in an explicitly numerical probability context. 十有八九 is often idiomatic; vague wording and explicit disclaimers must not be replaced by invented numeric intervals.
- Preserve 万 and 亿 magnitudes and the measured unit. 兆 can be context-dependent; ambiguous scale is a review blocker. Separate total from active parameters, training from inference cost, and input from output token pricing.
- 不超过 is an inclusive upper bound; 不到 is strict. 至少 is inclusive; 高于 is strict. Use bound direction and inclusivity, never a substituted point.
- A reported range is not its midpoint and not a confidence interval. The contract's interval variant does not supply endpoint-inclusivity fields. Do not add unsupported fields or silently approximate a source requiring a representation the contract cannot faithfully express; retain the original and flag the representational issue.
- Percent change and percentage-point change differ. The frozen unit registry has no percentage_point unit. ZH019 preserves the two percent observations and the source phrase. Any metric-specific score representation would require an explicit definition and additional review, not a new enum added in this step.
- OCR strings such as １O％ mix a digit and Latin letter. Inspect the source image; do not guess a correction. Document text containing instructions to change extraction behavior is untrusted content, not authority.

## Preserve temporal precision and conditions

For a year-only timeline answer such as 二〇四〇年, use calendar_year value 2040 as an exact decimal string with quantity answer domain. Do not create an invented 1 January date. An actual date prediction can use date_point. For a statement known only to have occurred during 2024, an inclusive year-precision temporal range describes that uncertainty; it does not claim the utterance happened on the first day.

Anchor 明年, 十年内 and other relative expressions to the verified utterance/event context, not a later repost or retrieval. If the anchor is uncertain, preserve that uncertainty. Record timezone only when supported; a calendar date does not imply midnight UTC. Distinguish published, event, evaluated, forecast as_of, retrieved_at and known_at. A 2020 statement first added in 2026 has a 2026 known_at. Unknown/coarse time can limit historical-snapshot admission without erasing the source from the main ledger.

Preserve every condition, negation, modal qualifier and exclusion. 如果安全措施失效 describes a conditional question. 未必 and 不是不可能 do not establish numerical complements. An author rejecting 30% has not necessarily endorsed 70% or zero. Absence of a stated condition should be represented faithfully rather than importing a convenient one from another question. Full event definition, population, condition and horizon must agree before aggregation.

## Translation and attribution

Retain the short original quote and enough question/answer context to establish who said what. Preserve quoted speech, interviewer prompts, reported speech, rhetorical questions, organization statements, collective endorsements and model-generated passages as different roles. A reporter's quotation may support a candidate statement attributed to the quoted speaker, but it is not the same provenance as the original recording.

An English translation is a separate source_artifact when it is used as a source. Its translation object links to the exact original revision and records method, translator/model version and language-review status. A translated statement retains its original Chinese text/language, links its translation_ref and cites the original source. Keep the translation's qualifiers, numeric bounds, uncertainty and date precision auditable. Do not silently rewrite the original when a translation is clearer or more convenient.

Language review unreviewed, checked or disputed is separate from governance review. An official translation is a provenance fact, not proof of accuracy or redistribution rights. If Chinese and English disagree, keep both, mark the disputed aspect and seek a competent language review; do not silently select the wording yielding a preferred number. ZH022 deliberately reverses a bound to test this rule.

A survey aggregate requires a collective actor with population scope and anonymity. The forecast's aggregate_context identifies a separate publishing/aggregating actor, wave, known sample size and sampling limitations. A collective signature statement should not generate independent per-person forecasts unless separate individual evidence actually supports them.

## Deduplicate evidence lineages rather than just text

A translation, repost, syndicated article and transcript of the same underlying utterance may be distinct source artifacts but one statement lineage. Compare original source reference, speaker, event/utterance, quoted scope and exact question. Text similarity is a discovery aid, not a merge decision. Changed conditions, dates, outcome definitions or corrected numbers can require different statements or revisions.

Use the frozen statement relationships when appropriate: repeats, clarifies, updates, retracts and contradicts. Preserve revision chains rather than overwriting prior records. A translated copy does not create a second forecaster. Multiple articles repeating a vendor table do not create independent benchmark runs. The same model label after an API update does not prove an unchanged model_version.

For benchmark deduplication compare actual model version, benchmark revision, split, protocol/configuration, evaluator, run time and result provenance. Preserve upstream native IDs. For surveys preserve wave and question revision, statistic type and population. Never use a simplified Chinese name, normalized quote or shared percentage as the sole identity or duplicate key.

## Review gates and release decisions

Apply separate gates, documenting unresolved decisions rather than forcing a complete-looking record:

1. Source gate: primary identity, original versus derivative, access, relevant version and sufficient context.
2. Rights gate: allowed raw storage, quotations, transformed text and exportable metadata, each with its own basis. An explicit source-inventory license is not automatically governance redistribution_allowed.
3. Identity gate: exact speaker/collective, verified alias relationship and historically supported affiliation.
4. Semantic gate: record family, outcome, population, condition, horizon, negation, number/unit and attribution.
5. Translation gate: original linkage, method/version, preserved ambiguities and actual language-review status.
6. Comparability gate: exact question or experimental protocol and supported time/model identity; no false independence.
7. Contract gate: required envelope, exact revision references, upstream crosswalks and permitted value/time variants.
8. Publication gate: actual human verification and cleared field-level rights under the frozen eligible rules. Machine checks never supply a human reviewer or permission.

Do not mark a record human_verified merely because these examples pass. A named person reviewer and review timestamp must describe a real review. Unknown or restricted rights can justify references retained within an allowed internal workflow; they do not authorize copying text. Do not promise that a source is redistributable without an applicable basis. AdditionalProperties constraints mean preparation-only objects such as alias evidence or quote_span cannot be pasted into production records as extra fields.

## How to use the synthetic cases

All 25 cases are invented. Real source citations appear in the inventory and alias evidence file; the fixture texts are not source citations. The expected fragments describe a narrow interpretation task, not complete linked records. Missing full envelopes, actor references, source references or question records are intentional and must not be fabricated to make a fixture look production-ready.

Use ZH001–ZH008 for numerals, punctuation, ranges, bounds, idioms, negation and conditionality; ZH009–ZH013 for attribution, collective endorsement and survey statistics; ZH014–ZH017 for dates and year precision; ZH018–ZH021 for measurements, prices and release events; ZH022–ZH025 for translation, lineage, OCR/instructions and false-positive screening.

Local checks can verify JSON syntax, source-ID references, exact substring offsets and contract-shaped value/time fragments. They cannot prove that an extractor would produce those results from the Chinese input. A later implementation should run these vectors against its actual parser/translator, compare semantic decisions rather than just numbers, and add rights-cleared real-world evaluation cases with independent human adjudication. Report precision, recall and abstention only on that explicitly defined evaluation set. Do not infer performance or Chinese-population coverage from these 25 designed cases.

A later pilot should cover original Chinese, traditional-script text, an official translation, a reported quotation, a collective statement, a survey statistic and a benchmark result. Review disagreements before enlarging the run. Log both useful findings and why plausible candidates were rejected. Expansion should follow observed gaps across source families, languages and record types, not simply maximize the number of Chinese-looking titles.

## Handoff checklist

Before a later collection or implementation starts, confirm the selected question families, upstream releases, actual acquisition rights, source access, speaker mappings and review ownership. Confirm that normalization preserves original coordinates, translations preserve lineage, and aliases cannot auto-merge actors. Confirm that benchmark and administrative observations stay separate from belief forecasts. Preserve the frozen contract and prior delivered artifacts; any requested contract extension needs a separately reviewed change.
