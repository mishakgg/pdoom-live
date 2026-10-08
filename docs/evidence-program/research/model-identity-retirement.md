# Model identity and retirement histories

Session 19, reviewed 8 October 2026 against main `82fd46330539bd484c80190c69868d71b2052f6e`. Source review is complete with explicit holds; operational admission remains pending. Publication progress is tracked in the dated queue. See the [separate JSON record](../../../data/evidence-program/research/model-identity-retirement.json) and [dated queue](research-session-review-queue.md).

All seven collections remain unadmitted research metadata. No adapter, validator, entity registry, model calls, weight downloads, live collector or source execution was added. Exact routing, execution and artifact identity require separate evidence.

## Decision

Retain the top three priorities: **Google lifecycle/routing**, **Azure hosting lifecycle**, then **publisher-owned checkpoint metadata**. Each addresses a different identity boundary. The JSON record contains the seven sample records, rights/access/coverage decisions and source locators.

### Changes that matter

- **Dated IDs can redirect.** Google's May 6, 2025 notice announces a preview-ID change; its June 26 entry reports both March and May preview IDs redirecting to the stable model. These are publisher assertions with different temporal strength, not observed requests. [Gemini changelog](https://ai.google.dev/gemini-api/docs/changelog)
- **Azure conflicts remain unresolved.** The included table has two retirement dates for each of two `gpt-realtime-mini` versions. Keep all four assertions: version 2025-10-06 has 2027-04-06 versus 2026-09-21; version 2025-12-15 has 2027-06-15 versus 2026-12-15. Docs/API lifecycle vocabulary differs, and deployment type, region and upgrade policy matter. [Included table](https://github.com/MicrosoftDocs/azure-ai-docs/blob/main/articles/foundry/openai/includes/concepts-model-retirement-schedule-content.md), [policy](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirements)
- **A revision is not a complete checkpoint.** The DeepSeek-R1 sample establishes a publisher-declared shard OID and size. A separate February 9 commit changes only tokenizer configuration. Neither proves an evaluation loaded a full identified artifact set. [Weight-upload commit](https://huggingface.co/deepseek-ai/DeepSeek-R1/commit/abf9bba58b8180037a228a50ed7ac547905e415d), [tokenizer commit](https://huggingface.co/deepseek-ai/DeepSeek-R1/commit/8a58a132790c9935686eb97f042afa8013451c9f)
- **DeepSeek evidence remains indexed-primary only.** Official indexed English/Chinese text supports the central alias/mode changes; no present page-body snapshot or API behavior was verified. The January 20, 2025 English entry also contradicts itself about R1/V3. Retain that conflict without overriding the separately sourced R1 tariff in IPP004. [English changelog](https://api-docs.deepseek.com/updates/), [Chinese changelog](https://api-docs.deepseek.com/zh-cn/updates/)
- **Anthropic's rule has a precise scope.** Canonical generation-4.6-and-later dateless IDs are publisher-assured fixed snapshots; earlier convenience aliases are excluded. Serving infrastructure can change independently. [ID semantics](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)
- **OpenAI product and API evidence stay separate.** The April 2025 GPT-4o rollback describes ChatGPT, not every API snapshot. [Rollback explanation](https://openai.com/index/sycophancy-in-gpt-4o/), [snapshot documentation](https://developers.openai.com/api/docs/models/gpt-4o)
- **Correct the AWS archive/Region claims.** The live legacy page retains a separate past-EOL table. Listed Regions scope the announced EOL and are not necessarily exhaustive availability. October 8, 2026 is Opus 4.1's published extended-access start, not an observed transition instant or EOL. [Bedrock lifecycle](https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle-legacy.html)

## Meaningful overlap

- OM001 supplies Hub metadata history; MIR003 adds publisher-owned artifact revisions. OM004's native/converted checkpoint distinction remains intact.
- IPP001/IPP002 cost and energy rows keep unresolved immutable-model identity. IPP003 analytical label substitutions do not become identity equivalence.
- IPP004 tariff and MIR004 alias observations reuse the same provider events. Link event/service/alias/mode/time rather than duplicate measurements.
- CRP002 distinguishes reported model revision, evaluator revision and result deposit. This review does not resolve its missing evaluator or executed-weight/configuration chain.
- GL014–GL016 developer cards receive lifecycle context; Azure and Bedrock remain distinct hosts. CN002 is the inspected Hub seed; CN003–CN006 expansion is unverified.

## Rights and access

Google documentation: CC BY 4.0, code Apache 2.0. MicrosoftDocs documentation: CC BY 4.0, code MIT. The inspected DeepSeek-R1 release declares MIT for code and weights with derivative qualifications. AWS documentation: CC BY-SA 4.0, embedded code MIT-0. These are artifact-scoped grants. Anthropic/OpenAI/DeepSeek website-text rights and a blanket Hub metadata grant remain unknown. No weight, gated data, subscription API or inference was accessed.

## Bounded crosswalk specification

The proposed chain is result → evaluation run → invocation/deployment → service version or local artifact manifest, with separately evidenced edges. Retain exact names, platform/region/mode, execution interval, benchmark/harness revision, configuration and weight-manifest identity, source locator and date type.

Use only the three verified Gemini IDs in the May 6–June 26, 2025 window as a future manual fixture: one source page, 2 MiB, at most 15 assertions. Test future-versus-active language, exact IDs, host separation, conflicting dates, incomplete manifests and unresolved runs. Response-schema metadata can strengthen a link only when the original evaluation recorded it. No adapter, validator or entity registry was implemented.

## Stop condition and holds

Critical factual checks are complete. Leave exact historical routing, private deployment histories, full checkpoint/configuration manifests, executed bytes, contradictory schedules and unestablished redistribution rights explicit. Do not chase hidden execution history or infer missing identities from similar names. Seven bounded next-action prompts follow; none was started.

## Next actions and copy-ready prompts

### MIR-A01 / MIR-P01: Record Gemini identity assertions

P0; source MIR001; status `bounded_follow_up_not_started`.

Using only https://ai.google.dev/gemini-api/docs/changelog and its already verified May 6–June 26, 2025 sections, prepare a manual factual crosswalk for gemini-2.5-pro-preview-03-25, gemini-2.5-pro-preview-05-06 and gemini-2.5-pro. Limit to one page, 2 MiB and 15 assertions. Keep future announcements, planned dates and publisher-reported active mappings separate; no exact activation instant, continuous interval or Cloud-hosted identity may be inferred. Include source locators and CC BY 4.0 attribution. No code/adapter, model calls, authentication or linked artifact downloads. Stop with the bounded crosswalk and unresolved run links.

### MIR-A02 / MIR-P02: Preserve Azure lifecycle conflicts

P1; source MIR002; status `bounded_follow_up_not_started`.

Inspect only https://github.com/MicrosoftDocs/azure-ai-docs/blob/main/articles/foundry/openai/includes/concepts-model-retirement-schedule-content.md and at most one directly linked Microsoft clarification for gpt-realtime-mini versions 2025-10-06 and 2025-12-15. The reviewed table publishes two dates for each pair. Preserve the exact versions, raw lifecycle values, each date, source revision if available, region/deployment/capability scope and any supersession evidence. Do not pick a row by order or infer actual retirement from elapsed time. Do not query a subscription, sign in, contact Microsoft or modify a deployment/repository. If no official disambiguation exists, return the two unresolved pairs and stop.

### MIR-A03 / MIR-P03: Specify checkpoint manifest evidence

P1; source MIR003; status `bounded_follow_up_not_started`.

Use the already inspected https://huggingface.co/deepseek-ai/DeepSeek-R1 repository metadata, one shard pointer at abf9bba58b8180037a228a50ed7ac547905e415d and tokenizer-only commit 8a58a132790c9935686eb97f042afa8013451c9f. Specify the evidence required to distinguish repository state, weight object set, tokenizer/chat template, generation configuration and runtime. Relate this to OM001/OM004 and CRP002 without asserting execution or equating native and converted checkpoints. Do not fetch weights, sweep manifests, run code/models, resolve private logs or create an entity registry. Keep complete manifest and executed-artifact linkage unresolved and stop after the specification.

### MIR-A04 / MIR-P04: Verify DeepSeek event snapshot

P1; source MIR004; status `bounded_follow_up_not_started`.

If separately authorized, make one bounded public read of https://api-docs.deepseek.com/updates/ and the Chinese counterpart only if needed. Preserve the verified indexed 2025-05-28, 2025-08-21 and 2026-09-10 alias/mode relationships and January 20, 2025 R1/V3 contradictory wording. Cross-link the corresponding IPP004 tariff event rather than duplicating it. A successful read can establish a present snapshot, never observed API behavior or historical wording availability. No login, paid inference, weights, outreach or source-body publication. If the page is unavailable, retain indexed-primary status and stop.

### MIR-A05 / MIR-P05: Scope Anthropic identity rules

P1; source MIR005; status `bounded_follow_up_not_started`.

For a supplied evaluation record only, match its exact ID and platform to https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions and https://platform.claude.com/docs/en/about-claude/model-deprecations. Distinguish canonical generation-4.6-and-later pinned IDs from earlier convenience aliases; distinguish Anthropic-operated schedules from partner schedules. Use a relevant postmortem window only as possible serving-infrastructure exposure. Do not search hidden execution logs, infer weights from response style, run inference, contact anyone or publish unlicensed page bodies. If the evaluation lacks platform/time/version metadata, leave the relationship unresolved and stop. If no evaluation record is supplied, return the required fields and stop.

### MIR-A06 / MIR-P06: Separate OpenAI product identities

P1; source MIR006; status `bounded_follow_up_not_started`.

For a supplied result only, record exact requested/returned identifier, execution interval and whether the surface was OpenAI API, ChatGPT or a hosted partner. Check only the relevant entry at https://developers.openai.com/api/docs/models/gpt-4o or https://developers.openai.com/api/docs/deprecations. The April 25–29, 2025 GPT-4o product update/rollback applies to ChatGPT evidence; do not propagate it to API snapshots. Do not treat IPP003 label substitutions or system_fingerprint as checkpoint equivalence. No inference, credentials, private log searches or repository changes. Return the strongest evidenced link and explicit missing fields, then stop. If no result record is supplied, return the required fields and stop.

### MIR-A07 / MIR-P07: Scope Bedrock lifecycle dates

P1; source MIR007; status `bounded_follow_up_not_started`.

For anthropic.claude-opus-4-1-20250805-v1:0, use only https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-1.html, https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle-legacy.html and https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html. Preserve the pre-September-7-2026 launch regime; label the listed us-east-1/us-east-2/us-west-2 Regions as announced-EOL scope; retain October 8, 2026 extended-access start separately from January 8, 2027 EOL. The live page now retains past-EOL entries. Do not infer a transition instant, price change, customer endpoint state or universal availability. No regional API query, authentication, migration or inference. Stop after the bounded documentary record.
