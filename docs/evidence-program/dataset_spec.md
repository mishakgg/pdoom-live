# AI evidence dataset specification

Proposed version 0.1.0 • 7 October 2026

## Purpose and status

Use one versioned evidence envelope to connect sources, attributed beliefs, model versions, empirical observations and resolvable questions. Keep each type independently inspectable. A benchmark result, an incident allegation and a probability forecast answer different questions; this contract preserves those differences rather than producing a single risk score.

This is a portable design and validation prototype for review. It is an additive bridge to pdoom.live, not its existing import format, a database migration or a production integration. This repository integration adds design documents, isolated fixtures and checks; it changes no production APIs, database tables or collection schedules. All example records are wholly fictional, marked synthetic and isolated from research data.

The completed coverage audit used repository commit f5274396885dbb654fc2861a78fa5be8f42fad38 and a bounded inventory of 64 candidate source families. Catalog entries and available collectors do not establish saved quantitative observations. The contract addresses the missing record types without suggesting that these sources have now been ingested or that the inventory covers all relevant AI evidence.

## Record types and relationships

Every record has a persistent identifier, an immutable revision and the shared envelope described below. References always name an exact revision.

- source_artifact: a particular original or translated paper, report, model card, dataset release, webpage, market snapshot or other source. Preserve its URL, title, language, publisher and authors when established. A content hash is optional when bytes have not been captured; metadata discovery must not imply possession of the source body.
- actor: a person, organization or explicitly defined collective. Retain verified identity mappings, names in their original scripts and dated affiliations. A collective represents anonymous survey respondents, a market community or a panel, with its population and anonymity stated. It is distinct from its publisher.
- statement: an attributed source statement, its original language, faithful normalized wording, topics and relationships to previous statements. Preserve explicit_numeric, explicit_qualitative and model_inferred_signal as separate kinds.
- model_version: a model family and version, developer, modalities, access and parent-model lineage. Identify whether the version is immutable, merely provider-labelled, inferred or unknown. A mutable product name is insufficient for a strong longitudinal comparison.
- release_event: an announcement, preview, API release, weights release, withdrawal or update tied to a model version. The availability scope and event time distinguish announcement from access.
- benchmark_run: a model version, benchmark revision and split, evaluator, protocol/configuration and measured or reported result. The record also states contamination status and the evaluator’s relationship to the developer.
- resource_observation: a compute, cost, price, energy, hardware, parameter, token, adoption or economic observation. State the subject, metric, denominator, time boundary and measurement method. Native currency and price basis are retained.
- safety_evaluation: a model version, risk domain, evaluator, protocol, result, optional threshold and limitations. A protocol result is not an estimate of global catastrophe probability.
- incident: an alleged or observed event, neutral description, verification state, causal-attribution status, severity rubric and curated event-cluster key. Association with an AI model is not proof of causation.
- forecast_question: exact wording, outcome definition, population, conditioning, horizon, answer domain and resolution rule. Extinction, catastrophe, loss of control, AGI and a particular benchmark milestone remain distinct event families.
- forecast: an answer to an exact question revision, an attributed forecaster or collective, forecast time, elicitation channel and optional source-statement reference. A source-published aggregate includes a separate aggregator, wave and sampling context.
- resolution: the adjudication of an exact question revision, with source evidence, rationale and status. Open, ambiguous and void cases cannot carry a fabricated outcome. Resolved binary event questions use boolean outcomes, not probabilities.
- snapshot: a closed manifest of exact record revisions and hashes at a declared knowledge cutoff. It records what could be known, not a claim that all included evidence is correct or publishable.

Source records, actors and their evidence may form a reference graph. Historical revision links form ordered chains. The prototype’s self-contained bundle includes all referenced revisions; a future external reference resolver would be a separately specified extension.

## Shared envelope and required evidence

The required envelope fields are schema_version, record_type, id, revision, synthetic, times, governance, evidence and data. Identifiers use urn:pdataset:TYPE:SLUG. Revision 1 starts a record; each subsequent revision must point to the immediately preceding revision of the same identifier through supersedes, with a strictly later known_at. Correcting an allegation, attribution or value creates another revision rather than overwriting history.

Every record except a source artifact or snapshot requires at least one source evidence link. Each link supplies the exact source revision, an evidence locator, its relation to the record, extraction method and extractor version. Locators may identify a page, table, paragraph, timestamp or other stable selector. An optional short excerpt requires appropriate content rights. A machine-extracted claim remains distinguishable from the measurement procedure and human review.

Integrate established datasets before collecting genuinely missing evidence. Optional upstream_refs form a crosswalk to an upstream dataset, exact release, native record key and original schema name/version, with an evidence source reference and an ordered list of versioned transformations. Preserve the native record and upstream authority; this envelope can index a source record without copying all of its raw content or replacing the upstream database. The fictional survey example keeps its native wave/question/median key and explicitly records percent-to-probability conversion. Verify licensing, identifiers, versions and meaning before reuse, then use the coverage audit to identify what still requires new collection. Transformation rules are documented here, not implemented as an ingestion engine.

Optional legacy_refs retain the existing pdoom-live entity name, exact key and repository commit. They do not pretend that the new and old schemas are interchangeable. The complete machine-readable field dictionary is [field dictionary](../../tools/evidence_program/contracts/field_dictionary.json); the JSON schemas are authoritative for field shape and the validator for the additional implemented invariants.

## Numbers units and uncertainty

Store empirical numbers and probabilities as exact base-10 strings, such as "0.20" or "1200000000000000000000000". Do not serialize these values through binary floating-point JSON numbers. Exponents, NaN, infinity and thousands separators are rejected. Counts used only for structure, such as revision and sample_size, are JSON integers.

The tagged value union supports points, intervals, lower bounds, upper bounds, quantile sets, exact dates, date quantiles, categories, booleans and explicit missingness. Bound direction and inclusivity are mandatory. Intervals distinguish a reported range from a confidence, credible or measurement interval; confidence and credible intervals require a coverage level. Quantile probabilities must be strictly increasing and their values nondecreasing. Sparse quantiles do not define the distribution between them or a probability of the event never occurring.

Use probability for a fraction from 0 to 1, percent for a bounded proportion from 0 to 100 and percent_change for a signed change that can exceed 100. Generic scores and ratios require a metric definition and any known scale limits. Currency values may be signed for net flows or changes; a genuine cost or price should declare a nonnegative metric minimum. Means and estimates of counts or tokens can be fractional when the metric says so. Literal discrete-count validity remains a metric-specific check.

For currency_nominal and currency_constant, preserve the original three-letter currency code and the conversion method, including the explicit absence of conversion. Constant-price values also require a base year. Do not silently turn a CNY-denominated observation into USD. Price denominators, hardware identity, precision conventions, nominal versus effective FLOPs and included cost boundaries belong in the metric definition and scope.

Year-only timeline forecasts use integer calendar_year values, including intervals, bounds and quantiles. Actual date forecasts use date_point or date_quantiles. Do not convert “2040” to an invented 1 January 2040. Qualitative source language stays categorical; it cannot be converted into an invented numerical probability.

## Observation and evaluation context

Every numerical measurement distinguishes reported, measured and estimated. Reported means a party asserts the result; measured means an identifiable evaluator ran the procedure; estimated means assumptions or a calculation produced it. Record the method and relevant uncertainty either way. A developer’s quoted benchmark result is reported evidence unless the collection actually includes the evaluator’s measured run.

A benchmark comparison requires the same task definition, benchmark version, split, metric/unit and interpretation of the protocol. Preserve harness version, prompt or scaffold, tools, sampling settings, inference budget and scoring conditions in protocol configuration. Unknown or unavailable details must be disclosed; a fully populated shape alone does not make two runs comparable. Full reproducibility is an assertion that requires supporting artifacts and independent checks beyond this prototype.

Safety evaluations retain domain-specific thresholds and limitations. Incident verification is separate from causal attribution and severity. Resource observations retain estimation assumptions and measurement boundaries. None of these records is automatically converted to p(doom), AGI probability or a forecast calibration score.

## Times historical snapshots and leakage

known_at is when this revision first became available to the dataset. retrieved_at is when its supporting material was captured. These are system timestamps in UTC with at most six fractional-second digits, not inferred historical publication dates. A late-discovered 2020 statement collected in 2026 has a 2026 known_at. Its event time may still be 2020.

Published, event and evaluated times use an instant, a date, an inclusive date range with precision, or unknown with a reason. The forecast’s as_of uses the same precision-aware representation. This avoids inventing exact timestamps for source statements, survey waves or uncertain event dates. The earliest possible forecast time cannot be wholly after known_at. Event, publication and evaluation times are not forced into one universal ordering because embargoes, retrospective reports and announcements differ.

An as_known snapshot checks that every member was known by the cutoff and that any represented review had occurred by then. For a forecast’s uncertain as_of, its latest possible time must also precede the cutoff; an unknown time is not admitted to this historical snapshot. This is conservative eligibility, not a reason to discard an otherwise useful source record from the main ledger. Closed snapshots include all dependencies and prior revisions, so consumers must select revisions explicitly rather than count each historical correction as a new independent event.

Manifest hashes use the named project rule python-json-sort-utf8-v1: JSON keys sorted, UTF-8, no extra whitespace, exact strings preserved, no non-finite JSON values, followed by SHA-256. This is not a claim of RFC 8785 compatibility. The supplied script is the reference encoder; another language needs a byte-for-byte conformance test before generating compatible hashes.

## Languages institutions and translations

Source language, actor location, institutional affiliation and jurisdiction are separate fields. English work from a China-based institution is not Chinese-language prose; Chinese-language prose does not establish the author’s nationality. Jurisdiction entries name the relationship, such as based_in or registered_in, and its supported time period. Unknown affiliation or language remains unknown.

A translation links directly to the exact original source revision and records its method, translator/model identity and language-review status. A translated statement must cite that original source. Preserve original script, qualifiers, numeric expressions and date precision. A translation and its original are one evidence lineage, not two independent beliefs or measurements. Schema syntax accepts BCP47-style language tags but does not check the full IANA registry or judge translation quality.

## Review rights and release gates

Review state, rights state and publication state answer different questions. Review states reuse the existing vocabulary: unreviewed, machine_validated, human_verified, needs_review and rejected. Machine validation is not human approval. A human_verified assertion requires a named person reviewer and a review timestamp; the validator cannot verify that the person actually reviewed the record.

Rights states distinguish unknown, link_only, metadata_only, redistribution_allowed and restricted, with a recorded basis. Do not inherit permission to redistribute an upstream paper or transcript from the website’s software license or the dataset’s own license. The presence of a URL is not permission to copy its contents. Raw storage, quoted evidence and exportable metadata may have different permissions.

The proposal’s optional publication_state eligible tier is intentionally conservative: it requires human verification and cleared metadata or content rights. Statement text and excerpts also require content redistribution clearance. This proposed tier does not change the current website’s broader public-review rules or automatically publish anything. Internal records with unknown or restricted rights can still retain allowed references for review; public export needs a separate reviewed policy and field-level check.

## Forecast comparability and source aggregates

A common topic or similar headline is insufficient for aggregation. Exact question revision, population, condition, outcome definition, horizon and units must agree. “AI causes human extinction by 2100” cannot be pooled with “AI causes a major disaster,” “loss of control conditional on AGI,” or “AGI by 2035.” Numerical normalization is not permission to merge outcomes.

Individual source-derived forecasts must retain their actual statement speaker. A source-published survey or market aggregate instead attributes an explicit collective, while aggregate_context identifies the separate publisher/aggregator, survey wave or snapshot, sample size when known and sampling limitations. The synthetic survey example is a median of a fictional volunteer panel, not a probability asserted by the fictional publishing lab. A source’s reported aggregate is retained with its method; no analyst-created cross-question average is computed by this package.

Resolutions attach to exact questions, with adjudication evidence and human review required for resolved status. They do not implement forecast scoring or establish a sufficient calibration corpus. Unresolved extinction forecasts are not negative outcomes; speaker counts and repeated forecasts are not independent samples or confidence intervals.

## Compatibility with the current repository

The existing canonical ledger already represents organizations, people, affiliations, sources, source items, participants, evidence, statements and forecasts. Its contracts preserve numeric versus qualitative statements, question definitions, conditions, horizons, review states and revision relationships. Existing history helpers distinguish event time from knowledge and review cutoffs, and comparability helpers constrain question semantics. These are foundations to preserve, not missing functionality. See the pinned [canonical contracts](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/contracts/src/schemas.ts), [history helpers](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/contracts/src/history.ts) and [forecast comparability](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/docs/FORECAST_COMPARABILITY.md).

The bridge would map source artifacts to source items, actors to existing person/organization identities where applicable, and original evidence/statements to their current records. Collective respondents must not be forced into a fictitious person or attributed to a publisher. Model versions, runs, measurements, safety evaluations and incident records need additive staging and explicit adapters. This package supplies no adapter or migration.

The legacy forecast contract uses JavaScript numbers, numeric fields and an untyped distribution object; the initial SQL numeric storage has finite precision. Exact decimals, bounds and typed distributions in this proposal are not automatically round-trippable. Any future adapter must preserve raw values and reject or quarantine unrepresentable records rather than round, truncate or invent an identity. See the pinned [initial SQL schema](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/db/migrations/001_init.sql).

The repository already has bounded storage, rights/retention controls, private handoff checks, quota/owner/checksum gates and manifest-before-cleanup ordering. Preserve those protections in any later implementation. Their existence does not prove that storage credentials, an operational importer or the new data collection is ready. Public scoring is deliberately disabled in the existing resolution contract and remains outside this package. See [collection storage](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/docs/COLLECTION_STORAGE.md) and [forecast resolution](https://github.com/mishakgg/pdoom-live/blob/f5274396885dbb654fc2861a78fa5be8f42fad38/packages/contracts/src/forecast-resolution.ts).

## Validation and what passing means

Run from the repository root:

    python tools/evidence_program/validate_dataset.py tools/evidence_program/examples/synthetic_dataset.json
    python -m unittest discover -s tools/evidence_program/tests -p test_contract.py -v

Python 3.10 or newer and an installed jsonschema package with Draft 2020-12 support are required. The supplied package was tested with jsonschema 4.26.0. The validator does not install dependencies, fetch schema URLs, contact sources or modify the repository. The .invalid schema identifiers are offline namespaces, not deployed endpoints.

JSON Schema checks required fields, permitted variants, types, formats and basic identifier shape. The companion validator checks references and target types, revision chains, exact-decimal ranges, quantile ordering, metric/unit consistency, synthetic isolation, coarse-time admissibility, translation lineage, collective attribution, review/publication prerequisites and snapshot closure/hashes. The completed check validates 21 fictional records across all 13 types, loads all 14 schemas and passes 71 regression tests, including deliberate failures. Standalone per-type schemas are checked through an offline registry.

Passing establishes that the example is structurally consistent with this proposal and satisfies those coded checks. It does not establish factual accuracy, complete coverage, statistical independence, sound causal inference, verified legal rights, valid translations, source authenticity, reproducible experiments or scientifically defensible pooling. Identity resolution, semantic duplicate detection, benchmark equivalence, survey nonresponse, disputed adjudications, operational security and legal/publication review remain separate requirements. No production database constraints, importer, access controls, storage execution, complete unit ontology or calibration implementation are supplied.
