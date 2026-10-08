# Claim-to-result provenance

Session 18, reviewed 8 October 2026 against main `82fd46330539bd484c80190c69868d71b2052f6e`. Source review is complete with explicit holds; operational admission remains pending. Publication progress is tracked in the dated queue. See the [separate JSON record](../../../data/evidence-program/research/claim-result-provenance.json) and [dated queue](research-session-review-queue.md).

Documentation and original factual research metadata only. No new adapter, source corpus, full source-response receipts, model execution, live collector or canonical import. Linked artifacts keep their own rights.

## Decision

Keep **seven collections: five new collection/infrastructure families and two enrichments**. Best three: **ReScience C, archived HF Open LLM Leaderboard, Crossref/Crossmark with Retraction Watch attribution**. This ranks provenance value, not redistribution clearance.

1. **CRP001: ReScience C, new.** The [Ashok–Aekula entry](https://rescience.github.io/bibliography/Ashok_2022.html) links article DOI `10.5281/zenodo.6574629`, code DOI `10.5281/zenodo.6508499` and public review; data DOI is missing. The [CC BY 4.0 paper](https://ashok-arjun.github.io/papers/AshokRescienceC.pdf) confirms four miniImageNet values: Table 1, ResNet-18/224, 74.07 ± 0.71 and 77.29 ± 0.73; Table 9, Conv-4-64/84, 66.78 ± 0.84 and 64.94 ± 0.75. Keep two 5-way/5-shot protocols, 600 evaluation episodes and the stated 95% intervals. These are published replication findings, not experiments rerun here. The PDF declares the SWHID; Git-tag/tree equality and SWH retrieval remain unverified. Code rights are `other-open`, not a resolved grant; bibliography CC BY-SA licensing is unverified. No checkpoints or run outputs fetched.

2. **CRP002: HF leaderboard archives, new collection on a known host.** The [pinned result](https://huggingface.co/datasets/open-llm-leaderboard/results/blob/79baa2ab316ba40c29cd558444361394b7cf48e3/meta-llama/Llama-3.1-8B-Instruct/results_2025-02-06T09-49-35.437423.json) confirms Llama-3.1-8B-Instruct revision `0e9e39f249a16976918f6564b8830bc894c89659`, float16, IFEval task 2.0, 541 prompts, strict prompt accuracy 0.4195933456561922 and reported stderr 0.021236532548855144. Preserve null chat template and unresolved evaluator hash `a781a6b`. Repeated aggregate fields inside the JSON are not independent results. Model revision is not a weight digest or execution proof. V1 was archived June 2024; [retirement was announced March 13, 2025](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/1135). Recent request activity does not demonstrate new evaluations. Requests declare Apache-2.0; aggregate-result rights remain unresolved, and detailed-output gates were not entered. The submitted Meta 80.4 comparison remains unverified here.

3. **CRP006: Crossref/Crossmark + Retraction Watch, new.** [The Nature notice](https://www.nature.com/articles/s41586-025-08905-3) corrects a theoretical assumption, not a reported numerical result. Its code DOI is a Crossref reference, not a typed code relationship. DOI `10.1155/2022/1779131` has two assertions to retraction notice `10.1155/2023/9761643`, both September 14, 2023: publisher and Retraction Watch record 47559. Preserve **one notice and two assertions**, including reverse edges. Production metadata, notice scope and dates are checked. The database is CC0, with working-day updates; full text and abstracts have separate rights. [New Labs update annotations stopped May 29, 2026](https://community.crossref.org/t/deprecating-retraction-watch-annotations-in-the-labs-api/15884); existing annotations remain. Missing updates mean “none observed.” No author-level accusation follows from a work-level notice.

4. **CRP005: Zenodo/DataCite, new infrastructure family.** Selected metadata verifies article→supplementary-code and article→concept-DOI relations. Article, code, their concept DOIs and SWH identifiers remain distinct. The code ZIP’s 4,419,478-byte size and MD5 are provider-reported; the ZIP was not downloaded. Zenodo modification and DataCite update times differ and both survive. [Zenodo metadata is CC0 except email addresses](https://about.zenodo.org/policies/); files keep their licenses. This is the same ReScience package, not another replication. Prior OM002/PI005 already contain Zenodo-hosted artifacts.

5. **CRP003: SWE-bench, GL007 enrichment.** Pinned metadata and results link SWE-agent/GPT-4-1106-preview, paper arXiv:2405.15793 and 54 resolved-list entries, including `psf__requests-2317`. Preserve `checked:true` as the registry’s assertion. Exact scaffold/harness revision, execution date and artifact rights remain unresolved. The reported 18/17 `no_generation` duplicate count remains unverified. No logs or trajectories acquired.

6. **CRP004: OpenML, new.** [Provider-rendered historical output](https://blog.openml.org/openml/2019/10/26/OpenML-Machine-Learning-as-a-community.html) verifies run 523926→task 59→Iris 61→flow 2629 v8→setup 3526, accuracy 0.966667 and one repeat of ten stratified folds. This is not a successful current run-API check. The Feurer reconstruction explicitly includes deactivated tasks and chooses oldest IDs heuristically; it does not prove original split identity. Artifact licenses govern reuse.

7. **CRP007: arXiv, GL040 enrichment.** Versioned pages confirm `2509.00072`: v1 August 26, 2025; withdrawn v2 October 6, 2025; available latest v4 May 13, 2026, with changed title/authors. Keep withdrawal and licensing version-local: nonexclusive distribution permission, withdrawn-version no-license statement, then CC BY 4.0. Do not mark v4 withdrawn or apply its rights backwards. Atom exact-version behavior was not tested.

## Meaningful overlap and bounded crosswalk

GL039/GL040 supply discovery identifiers, not a second measurement. OM001/OM004 inform model/artifact identity; SP001 replication and SP002 A-Lab corrections are distinct studies. PI005, TD003 and item 17’s price, identity and throughput-correction records supply related provenance patterns without proving identical underlying measurements. In particular, the Nature model-collapse paper and TD003 are different studies.

Propose four record types only: artifact version, evaluation specification, observation, attributed relationship. Track declared links, verified identifiers, retrieved bytes, provider execution reports and independently recomputed results separately. No single “reproducible” boolean. Keep contradictory observations and explicit correction edges, clocks, denominators, uncertainty and rights.

The bounded first mapping reuses one ReScience package: four observations, two protocols, one study, with unresolved code identity and execution provenance. No new adapter, validator or framework. No metric pooling, interval conversion, fixed entity matches without evidence or p(doom) conversion.

## Review limits

Acquisition was partial. Selected journal, result and registry metadata support the facts above; this is not a complete archival audit. No code ZIP, weights, dataset corpus or evaluation traces were acquired or executed. Git/SWH equality, collection-wide historical bounds, SWE-bench duplicate recount and current OpenML API access remain explicit holds. Additional acquisition requires separate authorization.

## Next actions and copy-ready prompts

All seven actions are unstarted. These are bounded documentary or mapping tasks; implementation, further held acquisition and source admission remain separate decisions.

### CRP-A01 / CRP-P01: Resolve replication package identity

P0; source CRP001; status `bounded_follow_up_not_started`.

Review only Ashok:2022, article DOI 10.5281/zenodo.6574629 and code DOI 10.5281/zenodo.6508499. Reuse the four checked aggregate observations and Zenodo metadata summarized in this review. Resolve the declared v1 tag/commit/SWH directory relationship and exact code rights only after separate authorization for additional acquisition. Do not fetch additional artifacts under this mapping task. If not authorized, retain explicit unverified identity/license fields. No archive, checkpoint, dataset, code execution or external contact. Return a compact evidence map, not an adapter.

### CRP-A02 / CRP-P02: Clarify leaderboard provenance rights

P0; source CRP002; status `bounded_follow_up_not_started`.

Review only the checked HF result for meta-llama/Llama-3.1-8B-Instruct dated 2025-02-06 at result repository revision 79baa2ab316ba40c29cd558444361394b7cf48e3. Determine from public small documentation whether an explicit grant covers aggregate results and whether evaluator git_hash a781a6b has a documented repository. Preserve 541 prompts, task version 2.0 and model revision 0e9e39f249a16976918f6564b8830bc894c89659. No weights, gated details, execution, login or permission bypass. Stop with precise holds if unresolved; no new collector.

### CRP-A03 / CRP-P03: Clarify submission artifact claims

P1; source CRP003; status `bounded_follow_up_not_started`.

Review only SWE-bench experiments revision 40f164d5b8f1d249bf95a6df8b74b577fd8e519d, evaluation/lite/20240402_sweagent_gpt4. Use already-read metadata and results; any new artifact acquisition requires separate authorization. Check outcome-list duplication and exact rights/scaffold/harness/date claims from small public metadata only. Preserve checked as registry assertion, not independent execution. No trajectories, patches archive, tests, models or repo changes. Return unresolved fields when evidence is absent.

### CRP-A04 / CRP-P04: Verify one OpenML chain

P1; source CRP004; status `bounded_follow_up_not_started`.

Review the provider-rendered OpenML run 523926, task 59, dataset 61, flow 2629 version 8 and setup 3526. Current run-API retrieval remains unverified and remains held; do not retrieve additional API data without separate authorization. Map existing historical output and the documented deactivation/reconstruction caveat now. If later authorized, inspect only small metadata for that chain; no predictions, data files or execution. Do not infer original task from oldest-ID heuristic. Stop after one chain.

### CRP-A05 / CRP-P05: Map deposit relationship evidence

P1; source CRP005; status `bounded_follow_up_not_started`.

Using only the checked Zenodo 6508499/6574629 and DataCite 10.5281/zenodo.6574629 metadata, map version/concept DOIs, supplementary-code relations and distinct source timestamps. Keep the 4,419,478-byte ZIP checksum provider-reported and other-open unresolved. Reuse CRP001 study/artifact identities. No new downloads, code execution, permission changes or general adapter. Return one compact crosswalk with explicit gaps.

### CRP-A06 / CRP-P06: Map attributed correction notices

P0; source CRP006; status `bounded_follow_up_not_started`.

Using already checked production Crossref records, map 10.1038/s41586-024-07566-y→10.1038/s41586-025-08905-3 and 10.1155/2022/1779131→10.1155/2023/9761643. Preserve the Nature theory-only scope and one retraction notice with publisher and Retraction Watch 47559 assertions dated 2023-09-14. Do not infer author misconduct, numerical changes or independent reproduction. Retain notice/source/date and reverse-edge provenance; do not use retired Labs updates. No bulk CSV or code implementation. Stop after these two chains.

### CRP-A07 / CRP-P07: Map version-local arXiv status

P1; source CRP007; status `bounded_follow_up_not_started`.

Use the checked HTML metadata for arXiv 2509.00072v1, v2, v4. Preserve v2 withdrawal, available v4, changed title/author list and each version’s license. Do not propagate latest status or rights backwards or infer that a declared code URL identifies executed code. No manuscript bulk download, Atom harvesting or execution. Return a compact version map with unresolved underlying-measurement relationships; no new adapter.
