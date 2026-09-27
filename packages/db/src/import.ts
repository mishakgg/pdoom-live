import { readFile } from "node:fs/promises";
import {
  canonicalImportSchema,
  parseExplicitProbability,
  type CanonicalImport,
} from "@pdoom/contracts";
import type pg from "pg";
import { deploymentMode } from "./env";
import { sha256, stableId } from "./ids";
import { migrationState } from "./migrate";
import { fixtureFile } from "./paths";
import { commitOrAbort, setActiveClient } from "./shutdown";

export type ImportResult = {
  dataset_id: string;
  dataset_kind: string;
  schema_version: string;
  cohort_slug: string | null;
  cohort_version: string | null;
  imported: Record<string, number>;
  counts: Record<string, number>;
};

export function assertFixtureLoadAllowed(): void {
  if (deploymentMode() === "production") {
    throw new Error("refusing to load synthetic fixtures in production");
  }
}

export function assertDatasetAllowed(doc: { dataset_kind: string }): void {
  if (deploymentMode() === "production" && doc.dataset_kind === "synthetic") {
    throw new Error("refusing to import a synthetic dataset in production");
  }
}

async function loadFixture(): Promise<CanonicalImport> {
  assertFixtureLoadAllowed();
  const raw = await readFile(fixtureFile(), "utf8");
  return canonicalImportSchema.parse(JSON.parse(raw));
}

function num(value: number | null): string | null {
  return value === null ? null : value.toString();
}

export function validateDocument(raw: unknown): CanonicalImport {
  const parsed = canonicalImportSchema.parse(raw);
  validateForecastBoundaries(parsed);
  validateDatasetKind(parsed);
  return parsed;
}

export async function importCanonical(pool: pg.Pool, document?: CanonicalImport | unknown): Promise<ImportResult> {
  if (document === undefined) assertFixtureLoadAllowed();
  const doc = document ?? (await loadFixture());
  const parsed = validateDocument(doc);
  assertDatasetAllowed(parsed);
  const state = await migrationState(pool);
  if (state !== "current") {
    throw new Error(`refusing to import because migrations are ${state}`);
  }

  const client = await pool.connect();
  const pid = await client.query<{ pid: number }>("SELECT pg_backend_pid() AS pid");
  const backendPid = pid.rows[0]?.pid;
  if (backendPid === undefined) {
    client.release();
    throw new Error("database connection did not return a backend pid");
  }
  setActiveClient(client, backendPid);
  try {
    await client.query("BEGIN");
    await upsertAll(client, parsed);
    await commitOrAbort(client);
  } catch (error) {
    await client.query("ROLLBACK").catch(() => undefined);
    throw error;
  } finally {
    setActiveClient(null, null);
    try {
      client.release();
    } catch {
      // Shutdown may already have released the client.
    }
  }

  const counts = await countTables(pool);
  const cohort = parsed.cohorts[0] ?? null;
  return {
    dataset_id: parsed.dataset_id,
    dataset_kind: parsed.dataset_kind,
    schema_version: parsed.schema_version,
    cohort_slug: cohort?.slug ?? null,
    cohort_version: cohort?.version ?? null,
    imported: documentCounts(parsed),
    counts,
  };
}

function documentCounts(doc: CanonicalImport): Record<string, number> {
  return {
    organizations: doc.organizations.length,
    people: doc.people.length,
    affiliations: doc.affiliations.length,
    external_identities: doc.external_identities.length,
    sources: doc.sources.length,
    source_items: doc.source_items.length,
    statements: doc.statements.length,
    cohorts: doc.cohorts.length,
  };
}

function validateDatasetKind(doc: CanonicalImport): void {
  if (doc.dataset_kind !== "live") return;
  const syntheticMarkers = [
    ...doc.external_identities.filter((row) => row.verification_method === "synthetic_fixture").map((row) => row.external_id),
    ...doc.participants.filter((row) => row.attribution_method === "synthetic_fixture").map((row) => row.source_item_slug),
    ...doc.sources.filter((row) => row.collection_method === "fixture").map((row) => row.slug),
  ];
  if (syntheticMarkers.length) {
    throw new Error("live dataset cannot use synthetic_fixture or fixture collection markers");
  }
}

function validateForecastBoundaries(doc: CanonicalImport): void {
  const statements = new Map(doc.statements.map((statement) => [statement.slug, statement]));
  for (const forecast of doc.forecasts) {
    const statement = statements.get(forecast.statement_slug);
    if (!statement) throw new Error(`forecast missing statement ${forecast.statement_slug}`);
    const numeric =
      forecast.value_numeric !== null ||
      forecast.value_min !== null ||
      forecast.value_max !== null ||
      forecast.distribution !== null;
    if (statement.statement_type !== "explicit_numeric" && numeric) {
      throw new Error(`refusing numeric values on ${statement.statement_type} forecast ${forecast.statement_slug}`);
    }
    if (statement.statement_type === "explicit_numeric" && forecast.value_type === "none") {
      throw new Error(`explicit_numeric forecast ${forecast.statement_slug} is missing a value`);
    }
    if (forecast.value_text) {
      const parsed = parseExplicitProbability(forecast.value_text);
      if (parsed === null || forecast.value_numeric === null || Math.abs(parsed - forecast.value_numeric) > 1e-9) {
        throw new Error(`value_text does not match value_numeric for ${forecast.statement_slug}`);
      }
    }
  }
}

async function upsertAll(client: pg.PoolClient, doc: CanonicalImport): Promise<void> {
  for (const org of doc.organizations) {
    await client.query(
      `INSERT INTO organizations (id, slug, name, organization_type, canonical_url)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (slug) DO UPDATE SET
         name = EXCLUDED.name,
         organization_type = EXCLUDED.organization_type,
         canonical_url = EXCLUDED.canonical_url,
         updated_at = now()`,
      [stableId(`organization:${org.slug}`), org.slug, org.name, org.organization_type, org.canonical_url],
    );
  }

  for (const person of doc.people) {
    await client.query(
      `INSERT INTO people (
         id, slug, display_name, given_name, family_name, bio_short, inclusion_reason, cohort_tags, status
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
       ON CONFLICT (slug) DO UPDATE SET
         display_name = EXCLUDED.display_name,
         given_name = EXCLUDED.given_name,
         family_name = EXCLUDED.family_name,
         bio_short = EXCLUDED.bio_short,
         inclusion_reason = EXCLUDED.inclusion_reason,
         cohort_tags = EXCLUDED.cohort_tags,
         status = EXCLUDED.status,
         updated_at = now()`,
      [
        stableId(`person:${person.slug}`),
        person.slug,
        person.display_name,
        person.given_name,
        person.family_name,
        person.bio_short,
        person.inclusion_reason,
        person.cohort_tags,
        person.status,
      ],
    );
  }

  for (const source of doc.sources) {
    await client.query(
      `INSERT INTO sources (
         id, slug, source_type, name, canonical_url, platform, owner_person_id, owner_organization_id,
         collection_method, collection_adapter, rights_notes, enabled, review_state, last_checked_at, last_success_at
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
       ON CONFLICT (slug) DO UPDATE SET
         source_type = EXCLUDED.source_type,
         name = EXCLUDED.name,
         canonical_url = EXCLUDED.canonical_url,
         platform = EXCLUDED.platform,
         owner_person_id = EXCLUDED.owner_person_id,
         owner_organization_id = EXCLUDED.owner_organization_id,
         collection_method = EXCLUDED.collection_method,
         collection_adapter = EXCLUDED.collection_adapter,
         rights_notes = EXCLUDED.rights_notes,
         enabled = EXCLUDED.enabled,
         review_state = EXCLUDED.review_state,
         last_checked_at = EXCLUDED.last_checked_at,
         last_success_at = EXCLUDED.last_success_at,
         updated_at = now()`,
      [
        stableId(`source:${source.slug}`),
        source.slug,
        source.source_type,
        source.name,
        source.canonical_url,
        source.platform,
        source.owner_person_slug ? stableId(`person:${source.owner_person_slug}`) : null,
        source.owner_organization_slug ? stableId(`organization:${source.owner_organization_slug}`) : null,
        source.collection_method,
        source.collection_adapter,
        source.rights_notes,
        source.enabled,
        source.review_state,
        source.last_checked_at,
        source.last_success_at,
      ],
    );
  }

  for (const affiliation of doc.affiliations) {
    const id = stableId(
      `affiliation:${affiliation.person_slug}:${affiliation.organization_slug}:${affiliation.role ?? ""}:${affiliation.start_date ?? ""}`,
    );
    await client.query(
      `INSERT INTO affiliations (
         id, person_id, organization_id, role, start_date, end_date, source_id, confidence_level, verification_detail, review_state
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
       ON CONFLICT (person_id, organization_id, role, start_date) DO UPDATE SET
         end_date = EXCLUDED.end_date,
         source_id = EXCLUDED.source_id,
         confidence_level = EXCLUDED.confidence_level,
         verification_detail = EXCLUDED.verification_detail,
         review_state = EXCLUDED.review_state`,
      [
        id,
        stableId(`person:${affiliation.person_slug}`),
        stableId(`organization:${affiliation.organization_slug}`),
        affiliation.role,
        affiliation.start_date,
        affiliation.end_date,
        affiliation.source_slug ? stableId(`source:${affiliation.source_slug}`) : null,
        affiliation.confidence_level,
        affiliation.verification_detail,
        affiliation.review_state,
      ],
    );
    if (affiliation.is_current) {
      await client.query("UPDATE people SET current_affiliation_id = $1 WHERE id = $2", [
        id,
        stableId(`person:${affiliation.person_slug}`),
      ]);
    }
  }

  for (const identity of doc.external_identities) {
    await client.query(
      `INSERT INTO external_identities (
         id, person_id, namespace, external_id, canonical_url, handle, verification_method, verification_detail,
         confidence_level, review_state, verified_at, source_id
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
       ON CONFLICT (namespace, external_id) DO UPDATE SET
         person_id = EXCLUDED.person_id,
         canonical_url = EXCLUDED.canonical_url,
         handle = EXCLUDED.handle,
         verification_method = EXCLUDED.verification_method,
         verification_detail = EXCLUDED.verification_detail,
         confidence_level = EXCLUDED.confidence_level,
         review_state = EXCLUDED.review_state,
         verified_at = EXCLUDED.verified_at,
         source_id = EXCLUDED.source_id`,
      [
        stableId(`identity:${identity.namespace}:${identity.external_id}`),
        stableId(`person:${identity.person_slug}`),
        identity.namespace,
        identity.external_id,
        identity.canonical_url,
        identity.handle,
        identity.verification_method,
        identity.verification_detail,
        identity.confidence_level,
        identity.review_state,
        identity.verified_at,
        identity.source_slug ? stableId(`source:${identity.source_slug}`) : null,
      ],
    );
  }

  for (const run of doc.ingestion_runs) {
    await client.query(
      `INSERT INTO ingestion_runs (
         id, slug, collector, source_id, started_at, completed_at, status, cursor_before, cursor_after,
         observed_count, new_count, changed_count, error_summary
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
       ON CONFLICT (slug) DO UPDATE SET
         collector = EXCLUDED.collector,
         source_id = EXCLUDED.source_id,
         started_at = EXCLUDED.started_at,
         completed_at = EXCLUDED.completed_at,
         status = EXCLUDED.status,
         cursor_before = EXCLUDED.cursor_before,
         cursor_after = EXCLUDED.cursor_after,
         observed_count = EXCLUDED.observed_count,
         new_count = EXCLUDED.new_count,
         changed_count = EXCLUDED.changed_count,
         error_summary = EXCLUDED.error_summary`,
      [
        stableId(`ingestion:${run.slug}`),
        run.slug,
        run.collector,
        run.source_slug ? stableId(`source:${run.source_slug}`) : null,
        run.started_at,
        run.completed_at,
        run.status,
        run.cursor_before,
        run.cursor_after,
        run.observed_count,
        run.new_count,
        run.changed_count,
        run.error_summary,
      ],
    );
  }

  for (const item of doc.source_items) {
    const contentHash = resolveContentHash(item);
    await client.query(
      `INSERT INTO source_items (
         id, slug, source_id, upstream_id, logical_key, canonical_url, title, published_at, published_timezone,
         observed_at, updated_at_source, language, content_hash, content_version, content_reference, metadata_json,
         collection_status, availability, is_current, ingestion_run_id
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16::jsonb,$17,$18,$19,$20)
       ON CONFLICT (slug) DO UPDATE SET
         source_id = EXCLUDED.source_id,
         upstream_id = EXCLUDED.upstream_id,
         logical_key = EXCLUDED.logical_key,
         canonical_url = EXCLUDED.canonical_url,
         title = EXCLUDED.title,
         published_at = EXCLUDED.published_at,
         published_timezone = EXCLUDED.published_timezone,
         observed_at = EXCLUDED.observed_at,
         updated_at_source = EXCLUDED.updated_at_source,
         language = EXCLUDED.language,
         content_hash = EXCLUDED.content_hash,
         content_version = EXCLUDED.content_version,
         content_reference = EXCLUDED.content_reference,
         metadata_json = EXCLUDED.metadata_json,
         collection_status = EXCLUDED.collection_status,
         availability = EXCLUDED.availability,
         is_current = EXCLUDED.is_current,
         ingestion_run_id = EXCLUDED.ingestion_run_id`,
      [
        stableId(`source-item:${item.slug}`),
        item.slug,
        stableId(`source:${item.source_slug}`),
        item.upstream_id,
        item.logical_key,
        item.canonical_url,
        item.title,
        item.published_at,
        item.published_timezone,
        item.observed_at,
        item.updated_at_source,
        item.language,
        contentHash,
        item.content_version,
        item.content_reference,
        JSON.stringify(item.metadata),
        item.collection_status,
        item.availability,
        item.is_current,
        item.ingestion_run_slug ? stableId(`ingestion:${item.ingestion_run_slug}`) : null,
      ],
    );
  }

  for (const participant of doc.participants) {
    await client.query(
      `INSERT INTO source_participants (
         id, source_item_id, person_id, organization_id, role, attribution_method, attribution_detail, confidence_level
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
       ON CONFLICT (source_item_id, person_id, organization_id, role) DO UPDATE SET
         attribution_method = EXCLUDED.attribution_method,
         attribution_detail = EXCLUDED.attribution_detail,
         confidence_level = EXCLUDED.confidence_level`,
      [
        stableId(
          `participant:${participant.source_item_slug}:${participant.person_slug ?? ""}:${participant.organization_slug ?? ""}:${participant.role}`,
        ),
        stableId(`source-item:${participant.source_item_slug}`),
        participant.person_slug ? stableId(`person:${participant.person_slug}`) : null,
        participant.organization_slug ? stableId(`organization:${participant.organization_slug}`) : null,
        participant.role,
        participant.attribution_method,
        participant.attribution_detail,
        participant.confidence_level,
      ],
    );
  }

  for (const segment of doc.evidence_segments) {
    await client.query(
      `INSERT INTO evidence_segments (
         id, slug, source_item_id, segment_kind, sequence, start_char, end_char, start_ms, end_ms, text, context_text, segment_hash
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
       ON CONFLICT (slug) DO UPDATE SET
         source_item_id = EXCLUDED.source_item_id,
         segment_kind = EXCLUDED.segment_kind,
         sequence = EXCLUDED.sequence,
         start_char = EXCLUDED.start_char,
         end_char = EXCLUDED.end_char,
         start_ms = EXCLUDED.start_ms,
         end_ms = EXCLUDED.end_ms,
         text = EXCLUDED.text,
         context_text = EXCLUDED.context_text,
         segment_hash = EXCLUDED.segment_hash`,
      [
        stableId(`evidence:${segment.slug}`),
        segment.slug,
        stableId(`source-item:${segment.source_item_slug}`),
        segment.segment_kind,
        segment.sequence,
        segment.start_char,
        segment.end_char,
        segment.start_ms,
        segment.end_ms,
        segment.text,
        segment.context_text,
        sha256(segment.text),
      ],
    );
  }

  const topics = [...doc.topics].sort((a, b) => Number(Boolean(a.parent_slug)) - Number(Boolean(b.parent_slug)));
  for (const topic of topics) {
    await client.query(
      `INSERT INTO topics (id, slug, name, definition, parent_topic_id, version)
       VALUES ($1,$2,$3,$4,$5,$6)
       ON CONFLICT (slug) DO UPDATE SET
         name = EXCLUDED.name,
         definition = EXCLUDED.definition,
         parent_topic_id = EXCLUDED.parent_topic_id,
         version = EXCLUDED.version,
         updated_at = now()`,
      [
        stableId(`topic:${topic.slug}`),
        topic.slug,
        topic.name,
        topic.definition,
        topic.parent_slug ? stableId(`topic:${topic.parent_slug}`) : null,
        topic.version,
      ],
    );
  }

  for (const run of doc.extraction_runs) {
    await client.query(
      `INSERT INTO extraction_runs (
         id, slug, source_item_id, extractor_name, extractor_version, model_provider, model_name,
         prompt_contract_version, started_at, completed_at, status, input_hash, output_hash
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
       ON CONFLICT (slug) DO UPDATE SET
         source_item_id = EXCLUDED.source_item_id,
         extractor_name = EXCLUDED.extractor_name,
         extractor_version = EXCLUDED.extractor_version,
         model_provider = EXCLUDED.model_provider,
         model_name = EXCLUDED.model_name,
         prompt_contract_version = EXCLUDED.prompt_contract_version,
         started_at = EXCLUDED.started_at,
         completed_at = EXCLUDED.completed_at,
         status = EXCLUDED.status,
         input_hash = EXCLUDED.input_hash,
         output_hash = EXCLUDED.output_hash`,
      [
        stableId(`extraction:${run.slug}`),
        run.slug,
        stableId(`source-item:${run.source_item_slug}`),
        run.extractor_name,
        run.extractor_version,
        run.model_provider,
        run.model_name,
        run.prompt_contract_version,
        run.started_at,
        run.completed_at,
        run.status,
        run.input_hash,
        run.output_hash,
      ],
    );
  }

  for (const statement of doc.statements) {
    await client.query(
      `INSERT INTO statements (
         id, slug, person_id, source_item_id, statement_type, normalized_text, event_time,
         evidence_segment_id, extractor_version, confidence, review_state, extraction_run_id
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
       ON CONFLICT (slug) DO UPDATE SET
         person_id = EXCLUDED.person_id,
         source_item_id = EXCLUDED.source_item_id,
         statement_type = EXCLUDED.statement_type,
         normalized_text = EXCLUDED.normalized_text,
         event_time = EXCLUDED.event_time,
         evidence_segment_id = EXCLUDED.evidence_segment_id,
         extractor_version = EXCLUDED.extractor_version,
         confidence = EXCLUDED.confidence,
         review_state = EXCLUDED.review_state,
         extraction_run_id = EXCLUDED.extraction_run_id`,
      [
        stableId(`statement:${statement.slug}`),
        statement.slug,
        stableId(`person:${statement.person_slug}`),
        stableId(`source-item:${statement.source_item_slug}`),
        statement.statement_type,
        statement.normalized_text,
        statement.event_time,
        stableId(`evidence:${statement.evidence_slug}`),
        statement.extractor_version,
        statement.confidence,
        statement.review_state,
        statement.extraction_run_slug ? stableId(`extraction:${statement.extraction_run_slug}`) : null,
      ],
    );
    for (const topicSlug of statement.topic_slugs) {
      await client.query(
        `INSERT INTO statement_topics (statement_id, topic_id, confidence, method)
         VALUES ($1,$2,$3,$4)
         ON CONFLICT (statement_id, topic_id) DO UPDATE SET
           confidence = EXCLUDED.confidence,
           method = EXCLUDED.method`,
        [
          stableId(`statement:${statement.slug}`),
          stableId(`topic:${topicSlug}`),
          statement.topic_confidence,
          statement.topic_method,
        ],
      );
    }
  }

  for (const forecast of doc.forecasts) {
    await client.query(
      `INSERT INTO forecasts (
         id, statement_id, forecast_kind, question_key, question_text, definition_text, condition_text,
         target_date_start, target_date_end, horizon_text, value_type, value_numeric, value_min, value_max,
         unit, distribution_json, resolution_criteria, review_state
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16::jsonb,$17,$18)
       ON CONFLICT (statement_id) DO UPDATE SET
         forecast_kind = EXCLUDED.forecast_kind,
         question_key = EXCLUDED.question_key,
         question_text = EXCLUDED.question_text,
         definition_text = EXCLUDED.definition_text,
         condition_text = EXCLUDED.condition_text,
         target_date_start = EXCLUDED.target_date_start,
         target_date_end = EXCLUDED.target_date_end,
         horizon_text = EXCLUDED.horizon_text,
         value_type = EXCLUDED.value_type,
         value_numeric = EXCLUDED.value_numeric,
         value_min = EXCLUDED.value_min,
         value_max = EXCLUDED.value_max,
         unit = EXCLUDED.unit,
         distribution_json = EXCLUDED.distribution_json,
         resolution_criteria = EXCLUDED.resolution_criteria,
         review_state = EXCLUDED.review_state`,
      [
        stableId(`forecast:${forecast.statement_slug}`),
        stableId(`statement:${forecast.statement_slug}`),
        forecast.forecast_kind,
        forecast.question_key,
        forecast.question_text,
        forecast.definition_text,
        forecast.condition_text,
        forecast.target_date_start,
        forecast.target_date_end,
        forecast.horizon_text,
        forecast.value_type,
        num(forecast.value_numeric),
        num(forecast.value_min),
        num(forecast.value_max),
        forecast.unit,
        forecast.distribution ? JSON.stringify(forecast.distribution) : null,
        forecast.resolution_criteria,
        forecast.review_state,
      ],
    );
  }

  for (const relationship of doc.relationships) {
    await client.query(
      `INSERT INTO statement_relationships (
         id, from_statement_id, to_statement_id, relationship_type, method, confidence, review_state
       ) VALUES ($1,$2,$3,$4,$5,$6,$7)
       ON CONFLICT (from_statement_id, to_statement_id, relationship_type) DO UPDATE SET
         method = EXCLUDED.method,
         confidence = EXCLUDED.confidence,
         review_state = EXCLUDED.review_state`,
      [
        stableId(
          `relationship:${relationship.from_statement_slug}:${relationship.to_statement_slug}:${relationship.relationship_type}`,
        ),
        stableId(`statement:${relationship.from_statement_slug}`),
        stableId(`statement:${relationship.to_statement_slug}`),
        relationship.relationship_type,
        relationship.method,
        relationship.confidence,
        relationship.review_state,
      ],
    );
  }

  for (const cohort of doc.cohorts) {
    const cohortId = stableId(`cohort:${cohort.slug}:${cohort.version}`);
    await client.query(
      `INSERT INTO cohorts (id, slug, version, name, definition)
       VALUES ($1,$2,$3,$4,$5)
       ON CONFLICT (slug, version) DO UPDATE SET
         name = EXCLUDED.name,
         definition = EXCLUDED.definition`,
      [cohortId, cohort.slug, cohort.version, cohort.name, cohort.definition],
    );
    for (const member of cohort.member_slugs) {
      const person = doc.people.find((item) => item.slug === member);
      await client.query(
        `INSERT INTO cohort_memberships (cohort_id, person_id, inclusion_reason)
         VALUES ($1,$2,$3)
         ON CONFLICT (cohort_id, person_id) DO UPDATE SET inclusion_reason = EXCLUDED.inclusion_reason`,
        [cohortId, stableId(`person:${member}`), person?.inclusion_reason ?? "cohort member"],
      );
    }
  }

  for (const trend of doc.trend_definitions) {
    await client.query(
      `INSERT INTO trend_definitions (
         id, slug, name, topic_id, method_version, cohort_id, cohort_definition_json, aggregation_definition_json, published
       ) VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9)
       ON CONFLICT (slug) DO UPDATE SET
         name = EXCLUDED.name,
         topic_id = EXCLUDED.topic_id,
         method_version = EXCLUDED.method_version,
         cohort_id = EXCLUDED.cohort_id,
         cohort_definition_json = EXCLUDED.cohort_definition_json,
         aggregation_definition_json = EXCLUDED.aggregation_definition_json,
         published = EXCLUDED.published`,
      [
        stableId(`trend:${trend.slug}`),
        trend.slug,
        trend.name,
        trend.topic_slug ? stableId(`topic:${trend.topic_slug}`) : null,
        trend.method_version,
        stableId(`cohort:${trend.cohort_slug}:${trend.cohort_version}`),
        JSON.stringify({
          cohort_slug: trend.cohort_slug,
          cohort_version: trend.cohort_version,
          description: trend.cohort_definition,
        }),
        JSON.stringify(trend.aggregation),
        trend.published,
      ],
    );
  }

  const cohort = doc.cohorts[0] ?? null;
  await client.query("UPDATE dataset_imports SET is_current = false WHERE is_current");
  await client.query(
    `INSERT INTO dataset_imports (
       schema_version, dataset_id, dataset_kind, generated_at, notice, producer_name, producer_version,
       cohort_slug, cohort_version, is_current
     ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,true)`,
    [
      doc.schema_version,
      doc.dataset_id,
      doc.dataset_kind,
      doc.generated_at,
      doc.notice,
      doc.producer?.name ?? null,
      doc.producer?.version ?? null,
      cohort?.slug ?? null,
      cohort?.version ?? null,
    ],
  );
}

function resolveContentHash(item: CanonicalImport["source_items"][number]): string {
  if (item.content_hash_input) {
    const computed = sha256(item.content_hash_input);
    if (item.content_hash && item.content_hash !== computed) {
      throw new Error(`content_hash does not match content_hash_input for ${item.slug}`);
    }
    return computed;
  }
  if (!item.content_hash) throw new Error(`source item ${item.slug} is missing a content hash`);
  return item.content_hash;
}

async function countTables(pool: pg.Pool): Promise<Record<string, number>> {
  const tables = [
    "organizations",
    "people",
    "affiliations",
    "external_identities",
    "sources",
    "source_items",
    "source_participants",
    "evidence_segments",
    "topics",
    "statements",
    "forecasts",
    "statement_topics",
    "statement_relationships",
    "cohorts",
    "cohort_memberships",
    "ingestion_runs",
    "extraction_runs",
    "trend_definitions",
  ];
  const counts: Record<string, number> = {};
  for (const table of tables) {
    const result = await pool.query(`SELECT count(*)::int AS count FROM ${table}`);
    counts[table] = result.rows[0].count;
  }
  return counts;
}

export async function resetDatabase(pool: pg.Pool): Promise<ImportResult> {
  if (deploymentMode() === "production") {
    throw new Error("refusing to reset data in production");
  }
  await pool.query(`
    TRUNCATE
      trend_observations,
      trend_definitions,
      cohort_memberships,
      cohorts,
      statement_relationships,
      statement_topics,
      forecasts,
      statements,
      extraction_runs,
      evidence_segments,
      source_participants,
      source_items,
      ingestion_runs,
      external_identities,
      topics,
      sources,
      affiliations,
      people,
      organizations,
      dataset_imports
    RESTART IDENTITY CASCADE
  `);
  return importCanonical(pool);
}
