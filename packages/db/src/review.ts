import {
  assertReviewTransition,
  candidateKey,
  decisionKey,
  evidenceSupportsNumbers,
  isKnownQuestionKey,
  normalizePrefixedId,
  resultingReviewState,
  reviewCommandSchema,
  reviewManifestSchema,
  reviewPriority,
  reviewWarnings,
  suggestQuestionKeys,
  type ReviewCommand,
  type ReviewManifest,
  type ReviewState,
  type StatementType,
} from "@pdoom/contracts";
import type pg from "pg";
import { effectiveReviewStateSql, staleApprovalSql } from "./coverage";
import { sha256, stableId } from "./ids";
import { getPool } from "./pool";

type StatementRow = {
  id: string;
  slug: string;
  statement_type: string;
  normalized_text: string;
  review_state: string;
  confidence: string | null;
  extraction_confidence_level: string | null;
  extractor_name: string;
  extractor_version: string;
  candidate_key: string;
  person_slug: string;
  display_name: string;
  source_slug: string;
  source_name: string;
  source_type: string;
  canonical_url: string;
  content_hash: string;
  content_version: number;
  published_at: Date | null;
  event_time: Date | null;
  evidence_id: string;
  evidence_slug: string;
  evidence_text: string;
  context_text: string | null;
  segment_hash: string;
  start_char: number | null;
  end_char: number | null;
  start_ms: number | null;
  end_ms: number | null;
  source_item_id: string;
  question_key: string | null;
  question_text: string | null;
  definition_text: string | null;
  condition_text: string | null;
  horizon_text: string | null;
  value_type: string | null;
  value_numeric: string | null;
  value_min: string | null;
  value_max: string | null;
  unit: string | null;
  forecast_review_state: string | null;
  topic_slugs: string[];
  proposed_topics: string[];
  last_success_at: Date | null;
};

function num(value: string | number | null): number | null {
  if (value === null || value === undefined) return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

async function loadStatement(client: pg.PoolClient, slug: string): Promise<StatementRow | null> {
  const result = await client.query(
    `SELECT s.id, s.slug, s.statement_type, s.normalized_text, s.review_state, s.confidence,
            s.extraction_confidence_level, s.extractor_name, s.extractor_version, s.candidate_key,
            s.proposed_topics, s.event_time,
            p.slug AS person_slug, p.display_name,
            src.slug AS source_slug, src.name AS source_name, src.source_type, src.last_success_at,
            si.id AS source_item_id, si.canonical_url, si.content_hash, si.content_version, si.published_at,
            e.id AS evidence_id, e.slug AS evidence_slug, e.text AS evidence_text, e.context_text, e.segment_hash,
            e.start_char, e.end_char, e.start_ms, e.end_ms,
            f.question_key, f.question_text, f.definition_text, f.condition_text, f.horizon_text,
            f.value_type, f.value_numeric, f.value_min, f.value_max, f.unit, f.review_state AS forecast_review_state,
            COALESCE(array_agg(DISTINCT t.slug) FILTER (WHERE t.slug IS NOT NULL), '{}') AS topic_slugs
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     JOIN evidence_segments e ON e.id = s.evidence_segment_id
     LEFT JOIN forecasts f ON f.statement_id = s.id
     LEFT JOIN statement_topics st ON st.statement_id = s.id
     LEFT JOIN topics t ON t.id = st.topic_id
     WHERE s.slug = $1
     GROUP BY s.id, p.slug, p.display_name, src.slug, src.name, src.source_type, src.last_success_at,
              si.id, e.id, f.question_key, f.question_text, f.definition_text, f.condition_text, f.horizon_text,
              f.value_type, f.value_numeric, f.value_min, f.value_max, f.unit, f.review_state`,
    [slug],
  );
  return (result.rows[0] as StatementRow | undefined) ?? null;
}

function snapshot(row: StatementRow) {
  return {
    statement_type: row.statement_type,
    normalized_text: row.normalized_text,
    confidence: num(row.confidence),
    extraction_confidence_level: row.extraction_confidence_level,
    extractor_name: row.extractor_name,
    extractor_version: row.extractor_version,
    evidence_text: row.evidence_text,
    evidence_hash: row.segment_hash,
    source_content_hash: row.content_hash,
    content_version: row.content_version,
    topic_slugs: row.topic_slugs,
    proposed_topics: row.proposed_topics,
    forecast: row.question_key
      ? {
          question_key: row.question_key,
          question_text: row.question_text,
          definition_text: row.definition_text,
          condition_text: row.condition_text,
          horizon_text: row.horizon_text,
          value_type: row.value_type,
          value_numeric: num(row.value_numeric),
          value_min: num(row.value_min),
          value_max: num(row.value_max),
          unit: row.unit,
        }
      : null,
  };
}

async function ensureExtraction(client: pg.PoolClient, row: StatementRow): Promise<void> {
  await client.query(
    `INSERT INTO statement_extractions (
       statement_id, candidate_key, statement_type, normalized_text, confidence, extraction_confidence_level,
       extractor_name, extractor_version, evidence_text, evidence_hash, source_content_hash, content_version,
       forecast_json, topic_slugs
     ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,$14)
     ON CONFLICT (statement_id) DO NOTHING`,
    [
      row.id,
      row.candidate_key,
      row.statement_type,
      row.normalized_text,
      num(row.confidence),
      row.extraction_confidence_level,
      row.extractor_name,
      row.extractor_version,
      row.evidence_text,
      row.segment_hash,
      row.content_hash,
      row.content_version,
      JSON.stringify(snapshot(row).forecast),
      row.topic_slugs,
    ],
  );
}

export async function applyReviewDecision(pool: pg.Pool, raw: ReviewCommand): Promise<{ decision_key: string; idempotent: boolean }> {
  const command = reviewCommandSchema.parse(raw);
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const key = command.decision_key ?? decisionKey({ ...command, decision_key: null });
    const existing = await client.query(
      `SELECT decision FROM review_decisions WHERE decision_key = $1 AND corrections_json = $2::jsonb`,
      [key, JSON.stringify(command.corrections)],
    );
    if (existing.rowCount) {
      await client.query("COMMIT");
      return { decision_key: key, idempotent: true };
    }
    const conflict = await client.query(`SELECT 1 FROM review_decisions WHERE decision_key = $1`, [key]);
    if (conflict.rowCount) throw new Error("conflicting review decision");
    const row = await loadStatement(client, command.statement_slug);
    if (!row) throw new Error(`review refers to nonexistent statement ${command.statement_slug}`);
    if (command.source_content_hash && command.source_content_hash !== row.content_hash) {
      throw new Error("source content hash mismatch; the reviewed source version changed");
    }
    if (command.evidence_hash && command.evidence_hash !== row.segment_hash) {
      const original = await client.query(`SELECT evidence_hash FROM statement_extractions WHERE statement_id = $1`, [row.id]);
      const originalHash = original.rows[0]?.evidence_hash as string | undefined;
      if (command.evidence_hash !== originalHash) {
        throw new Error("evidence hash mismatch; the reviewed evidence changed");
      }
    }
    if (command.content_version && command.content_version !== row.content_version) {
      throw new Error("source content version mismatch; the reviewed source version changed");
    }
    assertReviewTransition(row.review_state as ReviewState, command.decision);
    if (command.decision === "reject" && !command.rejection_reason) throw new Error("rejection requires a reason");
    if (command.rejection_reason === "other" && !command.note) throw new Error("rejection reason other requires a note");
    const nextType = command.corrections.statement_type ?? row.statement_type;
    const evidenceText = command.corrections.evidence_text ?? row.evidence_text;
    const evidenceChanged = Boolean(command.corrections.evidence_text) || command.corrections.start_char !== undefined || command.corrections.end_char !== undefined;
    const acceptedEvidenceHash = evidenceChanged ? sha256(evidenceText) : row.segment_hash;
    if (command.corrections.evidence_text && !row.evidence_text.includes(command.corrections.evidence_text)) {
      throw new Error("corrected evidence must be an exact span of the stored evidence");
    }
    const valueNumeric = command.corrections.value_numeric !== undefined ? command.corrections.value_numeric : num(row.value_numeric);
    const valueMin = command.corrections.value_min !== undefined ? command.corrections.value_min : num(row.value_min);
    const valueMax = command.corrections.value_max !== undefined ? command.corrections.value_max : num(row.value_max);
    const valueType = command.corrections.value_type ?? row.value_type ?? "none";
    const unit = command.corrections.unit !== undefined ? command.corrections.unit : row.unit;
    const numericFilled = valueNumeric !== null || valueMin !== null || valueMax !== null;
    if (nextType !== "explicit_numeric" && numericFilled) {
      throw new Error("a qualitative or inferred statement cannot gain a numeric value");
    }
    if (nextType === "explicit_numeric" && !evidenceSupportsNumbers(evidenceText, { unit, value_type: valueType, value_numeric: valueNumeric, value_min: valueMin, value_max: valueMax })) {
      throw new Error("evidence does not contain the numeric value");
    }
    const questionKey = command.corrections.question_key ?? row.question_key;
    if (command.decision === "approve" && nextType === "explicit_numeric") {
      const confirms = command.confirmations;
      if (!Object.values(confirms).every(Boolean)) throw new Error("explicit numeric approval requires every confirmation");
      if (!questionKey || !isKnownQuestionKey(questionKey)) throw new Error("explicit numeric approval requires a known question key");
      if (!command.confirmations.question_key) throw new Error("question key must be confirmed by the operator");
    }
    if (questionKey && command.corrections.question_key && !isKnownQuestionKey(questionKey)) {
      throw new Error(`malformed question key: ${questionKey}`);
    }
    await ensureExtraction(client, row);
    if (command.corrections.normalized_text || command.corrections.statement_type) {
      await client.query(
        `UPDATE statements SET normalized_text = $2, statement_type = $3 WHERE id = $1`,
        [row.id, command.corrections.normalized_text ?? row.normalized_text, nextType],
      );
    }
    if (command.corrections.evidence_text || command.corrections.start_char !== undefined || command.corrections.end_char !== undefined) {
      await client.query(
        `UPDATE evidence_segments
         SET text = $2, start_char = $3, end_char = $4, segment_hash = $5
         WHERE id = $1`,
        [
          row.evidence_id,
          evidenceText,
          command.corrections.start_char !== undefined ? command.corrections.start_char : row.start_char,
          command.corrections.end_char !== undefined ? command.corrections.end_char : row.end_char,
          acceptedEvidenceHash,
        ],
      );
    }
    if (command.corrections.topic_slugs) {
      await client.query(`DELETE FROM statement_topics WHERE statement_id = $1`, [row.id]);
      for (const topicSlug of command.corrections.topic_slugs) {
        const topic = await client.query(`SELECT id FROM topics WHERE slug = $1`, [topicSlug]);
        if (!topic.rowCount) throw new Error(`unknown topic ${topicSlug}`);
        await client.query(
          `INSERT INTO statement_topics (statement_id, topic_id, confidence, method) VALUES ($1,$2,$3,$4)`,
          [row.id, topic.rows[0].id, num(row.confidence) ?? 1, "curator_review"],
        );
      }
    }
    const resulting = resultingReviewState(command.decision);
    if (nextType === "explicit_numeric" && (command.corrections.question_key || row.question_key)) {
      await client.query(
        `INSERT INTO forecasts (
           id, statement_id, forecast_kind, question_key, question_text, definition_text, condition_text,
           horizon_text, value_type, value_numeric, value_min, value_max, unit, review_state
         ) VALUES ($1,$2,'probability',$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
         ON CONFLICT (statement_id) DO UPDATE SET
           question_key = EXCLUDED.question_key,
           question_text = EXCLUDED.question_text,
           definition_text = EXCLUDED.definition_text,
           condition_text = EXCLUDED.condition_text,
           horizon_text = EXCLUDED.horizon_text,
           value_type = EXCLUDED.value_type,
           value_numeric = EXCLUDED.value_numeric,
           value_min = EXCLUDED.value_min,
           value_max = EXCLUDED.value_max,
           unit = EXCLUDED.unit,
           review_state = EXCLUDED.review_state`,
        [
          stableId(`forecast:${row.slug}`),
          row.id,
          questionKey,
          command.corrections.question_text ?? row.question_text ?? questionKey,
          command.corrections.definition_text !== undefined ? command.corrections.definition_text : row.definition_text,
          command.corrections.condition_text !== undefined ? command.corrections.condition_text : row.condition_text,
          command.corrections.horizon_text !== undefined ? command.corrections.horizon_text : row.horizon_text,
          valueType,
          valueNumeric,
          valueMin,
          valueMax,
          unit,
          resulting,
        ],
      );
    } else if (row.question_key) {
      await client.query(`UPDATE forecasts SET review_state = $2 WHERE statement_id = $1`, [row.id, resulting]);
    }
    await client.query(`UPDATE statements SET review_state = $2 WHERE id = $1`, [row.id, resulting]);
    if (command.relationship) {
      const other = await client.query(`SELECT id FROM statements WHERE slug = $1`, [command.relationship.other_statement_slug]);
      if (!other.rowCount) throw new Error(`relationship target ${command.relationship.other_statement_slug} does not exist`);
      await client.query(
        `INSERT INTO statement_relationships (
           id, from_statement_id, to_statement_id, relationship_type, method, confidence, review_state
         ) VALUES ($1,$2,$3,$4,'curator_review',1,$5)
         ON CONFLICT (from_statement_id, to_statement_id, relationship_type) DO UPDATE SET
           method = EXCLUDED.method,
           review_state = EXCLUDED.review_state`,
        [
          stableId(`relationship:${row.slug}:${command.relationship.other_statement_slug}:${command.relationship.relationship_type}`),
          row.id,
          other.rows[0].id,
          command.relationship.relationship_type,
          resulting,
        ],
      );
    }
    await client.query(
      `INSERT INTO review_decisions (
         id, decision_key, statement_id, candidate_key, decision, rejection_reason, previous_review_state,
         resulting_review_state, reviewed_at, reviewer, note, extractor_name, extractor_version,
         source_item_id, evidence_segment_id, source_content_hash, evidence_hash, content_version,
         corrections_json, original_extraction_json, relationship_json
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19::jsonb,$20::jsonb,$21::jsonb)`,
      [
        stableId(`review:${key}`),
        key,
        row.id,
        row.candidate_key,
        command.decision,
        command.rejection_reason,
        row.review_state,
        resulting,
        command.reviewed_at,
        command.reviewer,
        command.note,
        row.extractor_name,
        row.extractor_version,
        row.source_item_id,
        row.evidence_id,
        row.content_hash,
        acceptedEvidenceHash,
        row.content_version,
        JSON.stringify(command.corrections),
        JSON.stringify(snapshot(row)),
        command.relationship ? JSON.stringify(command.relationship) : null,
      ],
    );
    await client.query("COMMIT");
    return { decision_key: key, idempotent: false };
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function reviewStatus(pool = getPool()) {
  const states = await pool.query(
    `SELECT ${effectiveReviewStateSql("s")} AS review_state, count(*)::int AS count
     FROM statements s
     GROUP BY 1
     ORDER BY 1`,
  );
  const numeric = await pool.query(
    `SELECT count(*)::int AS count FROM statements s
     WHERE s.statement_type = 'explicit_numeric'
       AND ${effectiveReviewStateSql("s")} IN ('unreviewed', 'needs_review', 'machine_validated')`,
  );
  const missing = await pool.query(
    `SELECT
       count(*) FILTER (WHERE f.horizon_text IS NULL)::int AS missing_horizon,
       count(*) FILTER (WHERE f.definition_text IS NULL)::int AS missing_definition
     FROM statements s
     LEFT JOIN forecasts f ON f.statement_id = s.id
     WHERE ${effectiveReviewStateSql("s")} IN ('unreviewed', 'needs_review', 'machine_validated')`,
  );
  return {
    by_state: Object.fromEntries(states.rows.map((row) => [row.review_state, row.count])),
    explicit_numeric_awaiting_review: numeric.rows[0].count as number,
    missing_horizon: missing.rows[0].missing_horizon as number,
    missing_definition: missing.rows[0].missing_definition as number,
  };
}

export async function listReviewQueue(
  filters: {
    statement_type?: string;
    person?: string;
    topic?: string;
    source_type?: string;
    extractor?: string;
    review_state?: string;
    missing_horizon?: boolean;
    missing_definition?: boolean;
    published_from?: string;
    published_to?: string;
  } = {},
  pool = getPool(),
) {
  const values: unknown[] = [];
  const clauses = [`(
    s.review_state IN ('unreviewed', 'needs_review', 'machine_validated')
    OR (s.review_state = 'human_verified' AND ${staleApprovalSql("s")})
  )`];
  if (filters.statement_type) {
    values.push(filters.statement_type);
    clauses.push(`s.statement_type = $${values.length}`);
  }
  if (filters.person) {
    values.push(filters.person);
    clauses.push(`p.slug = $${values.length}`);
  }
  if (filters.topic) {
    values.push(filters.topic);
    clauses.push(`($${values.length} = ANY(s.proposed_topics) OR EXISTS (
      SELECT 1 FROM statement_topics st JOIN topics t ON t.id = st.topic_id
      WHERE st.statement_id = s.id AND t.slug = $${values.length}
    ))`);
  }
  if (filters.source_type) {
    values.push(filters.source_type);
    clauses.push(`src.source_type = $${values.length}`);
  }
  if (filters.extractor) {
    values.push(filters.extractor);
    clauses.push(`s.extractor_name = $${values.length}`);
  }
  if (filters.review_state) {
    values.push(filters.review_state);
    clauses.push(`${effectiveReviewStateSql("s")} = $${values.length}`);
  }
  if (filters.missing_horizon) clauses.push(`(f.horizon_text IS NULL OR f.horizon_text = '')`);
  if (filters.missing_definition) clauses.push(`(f.definition_text IS NULL OR f.definition_text = '')`);
  if (filters.published_from) {
    values.push(filters.published_from);
    clauses.push(`COALESCE(s.event_time, si.published_at) >= $${values.length}::timestamptz`);
  }
  if (filters.published_to) {
    values.push(filters.published_to);
    clauses.push(`COALESCE(s.event_time, si.published_at) <= $${values.length}::timestamptz`);
  }
  const result = await pool.query(
    `SELECT s.slug, s.statement_type, s.normalized_text, ${effectiveReviewStateSql("s")} AS review_state, s.confidence, s.extraction_confidence_level,
            s.extractor_name, s.extractor_version, s.event_time, p.slug AS person_slug, p.display_name,
            src.source_type, src.name AS source_name, si.canonical_url, si.published_at, src.last_success_at,
            f.question_key, f.horizon_text, f.definition_text, e.text AS evidence_text,
            COALESCE(array_agg(DISTINCT t.slug) FILTER (WHERE t.slug IS NOT NULL), '{}') AS topic_slugs
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     JOIN evidence_segments e ON e.id = s.evidence_segment_id
     LEFT JOIN forecasts f ON f.statement_id = s.id
     LEFT JOIN statement_topics st ON st.statement_id = s.id
     LEFT JOIN topics t ON t.id = st.topic_id
     WHERE ${clauses.join(" AND ")}
     GROUP BY s.id, p.slug, p.display_name, src.source_type, src.name, si.canonical_url, si.published_at, src.last_success_at,
              f.question_key, f.horizon_text, f.definition_text, e.text
     LIMIT 200`,
    values,
  );
  const related = await pool.query(
    `SELECT p.slug AS person_slug, f.question_key, count(*)::int AS count
     FROM statements s
     JOIN people p ON p.id = s.person_id
     JOIN forecasts f ON f.statement_id = s.id
     GROUP BY p.slug, f.question_key
     HAVING count(*) > 1`,
  );
  const relatedKeys = new Set(related.rows.map((item) => `${item.person_slug}:${item.question_key}`));
  const items = result.rows.map((row) => {
    const hasRelated = relatedKeys.has(`${row.person_slug}:${row.question_key}`);
    return {
      slug: String(row.slug),
      statement_type: row.statement_type as StatementType,
      normalized_text: String(row.normalized_text),
      review_state: String(row.review_state),
      person_slug: String(row.person_slug),
      display_name: String(row.display_name),
      source_type: String(row.source_type),
      source_name: String(row.source_name),
      canonical_url: String(row.canonical_url),
      published_at: row.published_at ? new Date(row.published_at).toISOString() : null,
      event_time: row.event_time ? new Date(row.event_time).toISOString() : null,
      question_key: row.question_key ? String(row.question_key) : null,
      horizon_text: row.horizon_text ? String(row.horizon_text) : null,
      extractor_name: String(row.extractor_name),
      priority: reviewPriority({
        statement_type: row.statement_type,
        has_related: hasRelated,
        confidence: num(row.confidence),
        confidence_level: row.extraction_confidence_level,
      }),
      why: whyReview(String(row.review_state), row.horizon_text, row.definition_text),
    };
  });
  items.sort((a, b) => a.priority - b.priority || (b.published_at ?? "").localeCompare(a.published_at ?? ""));
  return items;
}

function whyReview(state: string, horizon: string | null, definition: string | null): string {
  const parts = [
    state === "unreviewed" ? "No human review is recorded." : "",
    state === "needs_review" ? "Marked for another look. This is not a verified claim." : "",
    state === "machine_validated" ? "Machine validation is not a human review." : "",
    horizon ? "" : "Horizon is missing.",
    definition ? "" : "Definition is missing.",
  ].filter(Boolean);
  return parts.join(" ");
}

export async function getReviewItem(pool: pg.Pool, slug: string) {
  const client = await pool.connect();
  try {
    const row = await loadStatement(client, slug);
    if (!row) return null;
    const history = await client.query(
      `SELECT decision, previous_review_state, resulting_review_state, reviewed_at, reviewer, note, rejection_reason, corrections_json
       FROM review_decisions WHERE statement_id = $1 ORDER BY reviewed_at, decision_key`,
      [row.id],
    );
    const related = row.question_key
      ? await client.query(
          `SELECT s.slug, s.normalized_text, s.review_state, s.event_time, f.value_numeric, f.horizon_text
           FROM statements s
           JOIN forecasts f ON f.statement_id = s.id
           WHERE s.person_id = (SELECT id FROM people WHERE slug = $1)
             AND f.question_key = $2
             AND s.slug <> $3
           ORDER BY s.event_time DESC NULLS LAST`,
          [row.person_slug, row.question_key, row.slug],
        )
      : { rows: [] };
    const extraction = snapshot(row);
    const latest = await client.query(
      `SELECT source_content_hash, evidence_hash, content_version, resulting_review_state
       FROM review_decisions WHERE statement_id = $1
       ORDER BY reviewed_at DESC, decision_key DESC LIMIT 1`,
      [row.id],
    );
    const covered = latest.rows[0];
    const stale = Boolean(
      covered &&
      row.review_state === "human_verified" &&
      (covered.resulting_review_state !== "human_verified" ||
        covered.source_content_hash !== row.content_hash ||
        covered.evidence_hash !== row.segment_hash ||
        covered.content_version !== row.content_version),
    );
    return {
      ...extraction,
      slug: row.slug,
      review_state: row.review_state,
      why: whyReview(row.review_state, row.horizon_text, row.definition_text),
      display_name: row.display_name,
      person_slug: row.person_slug,
      source_name: row.source_name,
      source_slug: row.source_slug,
      source_type: row.source_type,
      canonical_url: row.canonical_url,
      published_at: row.published_at ? new Date(row.published_at).toISOString() : null,
      event_time: row.event_time ? new Date(row.event_time).toISOString() : null,
      observed_context: row.context_text,
      start_char: row.start_char,
      end_char: row.end_char,
      start_ms: row.start_ms,
      end_ms: row.end_ms,
      content_hash: row.content_hash,
      content_version: row.content_version,
      evidence_hash: row.segment_hash,
      candidate_key: row.candidate_key,
      suggestions: suggestQuestionKeys({ normalized_text: row.normalized_text, topics: [...row.topic_slugs, ...row.proposed_topics] }),
      warnings: [
        ...(stale ? [{
          code: "stale_review",
          message: "The source or evidence changed after the last approval. It needs review again.",
        }] : []),
        ...reviewWarnings({
          statement_type: row.statement_type as StatementType,
          horizon_text: row.horizon_text,
          definition_text: row.definition_text,
          condition_text: row.condition_text,
          question_key: row.question_key,
          value_type: row.value_type,
          unit: row.unit,
          value_numeric: num(row.value_numeric),
          value_min: num(row.value_min),
          value_max: num(row.value_max),
          source_type: row.source_type,
          evidence_text: row.evidence_text,
        }),
      ],
      history: history.rows,
      related: related.rows,
      forecast: extraction.forecast,
    };
  } finally {
    client.release();
  }
}

export function validateReviewManifest(raw: unknown): ReviewManifest {
  return reviewManifestSchema.parse(raw);
}

export async function validateReviewManifestInDatabase(pool: pg.Pool, raw: unknown): Promise<string[]> {
  const manifest = validateReviewManifest(raw);
  const errors: string[] = [];
  const seen = new Set<string>();
  const client = await pool.connect();
  try {
    const states = new Map<string, ReviewState>();
    for (const decision of manifest.decisions) {
      const key = decision.decision_key ?? decisionKey({ ...decision, decision_key: null });
      if (seen.has(key)) {
        errors.push(`duplicate decision ${key}`);
        continue;
      }
      seen.add(key);
      const stored = await client.query(
        `SELECT 1 FROM review_decisions WHERE decision_key = $1 AND corrections_json = $2::jsonb`,
        [key, JSON.stringify(decision.corrections)],
      );
      const conflict = await client.query(`SELECT 1 FROM review_decisions WHERE decision_key = $1`, [key]);
      if (conflict.rowCount && !stored.rowCount) errors.push(`conflicting review decision ${key}`);
      if (stored.rowCount) continue;
      const row = await loadStatement(client, decision.statement_slug);
      if (!row) {
        errors.push(`missing statement ${decision.statement_slug}`);
        continue;
      }
      if (decision.source_content_hash && decision.source_content_hash !== row.content_hash) {
        errors.push(`source hash mismatch for ${decision.statement_slug}`);
      }
      if (decision.evidence_hash && decision.evidence_hash !== row.segment_hash) {
        const original = await client.query(`SELECT evidence_hash FROM statement_extractions WHERE statement_id = $1`, [row.id]);
        if (decision.evidence_hash !== original.rows[0]?.evidence_hash) {
          errors.push(`evidence hash mismatch for ${decision.statement_slug}`);
        }
      }
      if (decision.content_version && decision.content_version !== row.content_version) {
        errors.push(`content version mismatch for ${decision.statement_slug}`);
      }
      if (decision.corrections.question_key && !isKnownQuestionKey(decision.corrections.question_key)) {
        errors.push(`malformed question key ${decision.corrections.question_key}`);
      }
      const nextType = decision.corrections.statement_type ?? row.statement_type;
      const numeric = [decision.corrections.value_numeric, decision.corrections.value_min, decision.corrections.value_max].some((value) => value !== null && value !== undefined);
      if (nextType !== "explicit_numeric" && numeric) errors.push(`numeric value on non-numeric statement ${decision.statement_slug}`);
      const previous = states.get(decision.statement_slug) ?? (row.review_state as ReviewState);
      try {
        assertReviewTransition(previous, decision.decision);
      } catch (error) {
        errors.push(error instanceof Error ? error.message : "invalid transition");
      }
      states.set(decision.statement_slug, resultingReviewState(decision.decision));
      if (decision.decision === "reject" && !decision.rejection_reason) errors.push(`missing rejection reason for ${decision.statement_slug}`);
    }
  } finally {
    client.release();
  }
  return errors;
}

export async function importReviewManifest(pool: pg.Pool, raw: unknown): Promise<{ applied: number; idempotent: number }> {
  const manifest = validateReviewManifest(raw);
  let applied = 0;
  let idempotent = 0;
  for (const decision of manifest.decisions) {
    const result = await applyReviewDecision(pool, decision);
    if (result.idempotent) idempotent += 1;
    else applied += 1;
  }
  return { applied, idempotent };
}

export async function exportReviewManifest(pool: pg.Pool): Promise<ReviewManifest> {
  const result = await pool.query(
    `SELECT corrections_json, relationship_json, reviewer, reviewed_at, note, rejection_reason, decision,
            source_content_hash, evidence_hash, content_version, d.decision_key, s.slug AS statement_slug
     FROM review_decisions d
     JOIN statements s ON s.id = d.statement_id
     ORDER BY d.reviewed_at, d.decision_key`,
  );
    const decisions = result.rows.map((row) =>
    reviewCommandSchema.parse({
      decision_key: row.decision_key,
      statement_slug: row.statement_slug,
      decision: row.decision,
      reviewer: row.reviewer,
      reviewed_at: new Date(row.reviewed_at).toISOString(),
      note: row.note,
      rejection_reason: row.rejection_reason,
      confirmations: row.decision === "approve"
        ? { person: true, evidence: true, value: true, units: true, definition: true, conditionality: true, horizon: true, question_key: true }
        : { person: false, evidence: false, value: false, units: false, definition: false, conditionality: false, horizon: false, question_key: false },
      corrections: row.corrections_json,
      relationship: row.relationship_json,
      source_content_hash: row.source_content_hash,
      evidence_hash: row.evidence_hash,
      content_version: row.content_version,
    }),
  );
  decisions.sort((a, b) => a.reviewed_at.localeCompare(b.reviewed_at) || (a.decision_key ?? "").localeCompare(b.decision_key ?? ""));
  return { schema_version: "review-decisions/1.0.0", decisions };
}

type CandidateRow = {
  person_id: string;
  source_url: string;
  content_hash: string;
  evidence_text: string;
  extractor_name: string;
  extractor_version: string;
  normalized_text: string;
  statement_type: string;
  review_state?: string;
  published_at?: string | null;
  observed_at?: string | null;
  topics?: string[];
  confidence?: string | number | null;
  value_numeric?: number | null;
};

export async function stageCandidates(pool: pg.Pool, rows: CandidateRow[]): Promise<{ staged: number; skipped: number }> {
  let staged = 0;
  let skipped = 0;
  for (const row of rows) {
    if (row.review_state === "human_verified" || row.statement_type === "human_verified") {
      throw new Error("staging cannot mark a candidate human_verified");
    }
    const personSlug = normalizePrefixedId(row.person_id, "person");
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const person = await client.query(`SELECT id FROM people WHERE slug = $1`, [personSlug]);
      if (!person.rowCount) throw new Error(`candidate person not in dataset: ${personSlug}`);
      if (typeof row.content_hash !== "string") throw new Error("candidate content hash must be SHA-256");
      const hash = row.content_hash.replace(/^sha256:/, "");
      if (!/^[a-f0-9]{64}$/.test(hash)) throw new Error("candidate content hash must be SHA-256");
      const evidenceText = row.evidence_text.slice(0, 2000);
      const evidenceHash = sha256(evidenceText);
      const key = candidateKey({
        person_slug: personSlug,
        source_content_hash: hash,
        evidence_hash: evidenceHash,
        extractor_name: row.extractor_name,
        extractor_version: row.extractor_version,
        statement_type: row.statement_type,
      });
      const existing = await client.query(`SELECT 1 FROM statements WHERE candidate_key = $1`, [key]);
      if (existing.rowCount) {
        await client.query("COMMIT");
        skipped += 1;
        continue;
      }
      const sourceSlug = `staged-${personSlug}-pages`.slice(0, 80);
      await client.query(
        `INSERT INTO sources (
           id, slug, source_type, name, canonical_url, platform, owner_person_id, collection_method,
           collection_adapter, rights_notes, enabled, review_state
         ) VALUES ($1,$2,'blog',$3,$4,'blog',$5,'manual','candidate_stage','Staged excerpt for review. Not a human verification.',true,'needs_review')
         ON CONFLICT (slug) DO NOTHING`,
        [stableId(`source:${sourceSlug}`), sourceSlug, `Staged pages for ${personSlug}`, row.source_url, person.rows[0].id],
      );
      const itemSlug = `staged-item-${key.slice(0, 16)}`;
      await client.query(
        `INSERT INTO source_items (
           id, slug, source_id, logical_key, canonical_url, title, published_at, observed_at, language,
           content_hash, content_version, content_reference, metadata_json, collection_status, availability, is_current
         ) VALUES ($1,$2,(SELECT id FROM sources WHERE slug = $3),$4,$5,$6,$7,$8,'en',$9,1,$10,'{}'::jsonb,'collected','available',true)
         ON CONFLICT (slug) DO NOTHING`,
        [
          stableId(`source-item:${itemSlug}`),
          itemSlug,
          sourceSlug,
          itemSlug,
          row.source_url,
          row.source_url,
          row.published_at ?? null,
          row.observed_at ?? new Date().toISOString(),
          hash,
          `candidate://${key}`,
        ],
      );
      const evidenceSlug = `staged-evidence-${key.slice(0, 16)}`;
      await client.query(
        `INSERT INTO evidence_segments (id, slug, source_item_id, segment_kind, sequence, text, segment_hash)
         VALUES ($1,$2,(SELECT id FROM source_items WHERE slug = $3),'text',1,$4,$5)
         ON CONFLICT (slug) DO NOTHING`,
        [stableId(`evidence:${evidenceSlug}`), evidenceSlug, itemSlug, evidenceText, evidenceHash],
      );
      const level = typeof row.confidence === "string" ? row.confidence : null;
      await client.query(
        `INSERT INTO statements (
           id, slug, person_id, source_item_id, statement_type, normalized_text, event_time, evidence_segment_id,
           extractor_name, extractor_version, candidate_key, confidence, extraction_confidence_level, review_state, proposed_topics
         ) VALUES (
           $1,$2,$3,(SELECT id FROM source_items WHERE slug = $4),$5,$6,$7,(SELECT id FROM evidence_segments WHERE slug = $8),
           $9,$10,$11,NULL,$12,'unreviewed',$13
         )`,
        [
          stableId(`statement:candidate-${key.slice(0, 16)}`),
          `candidate-${key.slice(0, 16)}`,
          person.rows[0].id,
          itemSlug,
          row.statement_type,
          row.normalized_text.slice(0, 600),
          row.published_at ?? null,
          evidenceSlug,
          row.extractor_name,
          row.extractor_version,
          key,
          level,
          row.topics ?? [],
        ],
      );
      await client.query("COMMIT");
      staged += 1;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }
  return { staged, skipped };
}

export function emptyConfirmations(on: boolean) {
  return {
    person: on,
    evidence: on,
    value: on,
    units: on,
    definition: on,
    conditionality: on,
    horizon: on,
    question_key: on,
  };
}
