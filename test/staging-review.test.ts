import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { candidateKey } from "@pdoom/contracts";
import { candidateKeyForCanonicalStatement } from "../packages/db/src/import";
import { restoreCoveredDecisions } from "../packages/db/src/coverage";
import { sha256 } from "../packages/db/src/ids";
import { createPool } from "../packages/db/src/pool";
import { getStatement } from "../packages/db/src/queries";
import { applyReviewDecision, emptyConfirmations, stageCandidates } from "../packages/db/src/review";
import { afterAll, describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");
const fixture = JSON.parse(readFileSync("data/fixtures/review/staging-identity.json", "utf8"));
const prefix = "https://synthetic.pdoom.example/staging-review/";

function identityOf(row: {
  evidence_text: string;
  content_hash: string;
  extractor_name: string;
  extractor_version: string;
  statement_type: string;
  question_key?: string | null;
  horizon_text?: string | null;
  unit?: string | null;
  value_type?: string | null;
  value_numeric?: number | null;
  value_min?: number | null;
  value_max?: number | null;
}) {
  return {
    person_slug: "ada-quill",
    source_content_hash: row.content_hash.replace(/^sha256:/, ""),
    evidence_hash: sha256(row.evidence_text.slice(0, 2000)),
    extractor_name: row.extractor_name,
    extractor_version: row.extractor_version,
    statement_type: row.statement_type,
    question_key: row.question_key ?? null,
    horizon_text: row.horizon_text ?? null,
    unit: row.unit ?? null,
    value_type: row.value_type ?? null,
    value_numeric: row.value_numeric ?? null,
    value_min: row.value_min ?? null,
    value_max: row.value_max ?? null,
  };
}

function pythonCandidates() {
  const raw = execFileSync("python3", ["data/fixtures/review/roundtrip.py"], {
    cwd: process.cwd(),
    env: { ...process.env, PYTHONPATH: "pipeline" },
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(raw) as {
    essay: Array<Record<string, unknown>>;
    podcast: Array<Record<string, unknown>>;
    podcast_observations: Array<Record<string, unknown>>;
  };
}

describe("staging identity and review continuity", () => {
  it("agrees with canonical import identity and keeps distinct claims", async () => {
    const primaryKey = candidateKey(identityOf(fixture.candidate));
    const siblingKey = candidateKey(identityOf(fixture.sibling));
    expect(primaryKey).not.toBe(siblingKey);
    expect(candidateKeyForCanonicalStatement(fixture.canonical, fixture.canonical.statement)).toBe(primaryKey);
    const staged = await stageCandidates(pool, [fixture.candidate, fixture.sibling]);
    expect(staged.staged).toBe(2);
    const again = await stageCandidates(pool, [fixture.candidate, fixture.sibling]);
    expect(again.skipped).toBe(2);
    const rows = await pool.query(
      `SELECT s.candidate_key, s.review_state, f.question_key, f.horizon_text, f.value_numeric, to_char(f.target_date_end, 'YYYY-MM-DD') AS target_date_end,
              f.condition_text, f.resolution_criteria, f.review_state AS forecast_state, si.published_timezone, si.language
       FROM statements s
       JOIN forecasts f ON f.statement_id = s.id
       JOIN source_items si ON si.id = s.source_item_id
       WHERE si.canonical_url = $1
       ORDER BY f.horizon_text`,
      [fixture.candidate.source_url],
    );
    expect(rows.rows.map((row) => row.candidate_key).sort()).toEqual([primaryKey, siblingKey].sort());
    expect(rows.rows.every((row) => row.review_state === "unreviewed")).toBe(true);
    expect(rows.rows.every((row) => row.forecast_state === "unreviewed")).toBe(true);
    const by2040 = rows.rows.find((row) => row.horizon_text === "by 2040");
    expect(by2040?.question_key).toBe("extinction_unconditional");
    expect(Number(by2040?.value_numeric)).toBeCloseTo(0.1);
    expect(by2040?.target_date_end).toBe("2040-12-31");
    expect(by2040?.resolution_criteria).toContain("2040");
    expect(by2040?.published_timezone).toBe("-05:00");
    expect(await getStatement(String((await pool.query(`SELECT slug FROM statements WHERE candidate_key = $1`, [primaryKey])).rows[0].slug), pool)).toBeNull();
  });

  it("restores covered decisions and refuses stale approval", async () => {
    const primary = await pool.query(
      `SELECT s.slug, s.normalized_text FROM statements s
       JOIN forecasts f ON f.statement_id = s.id
       JOIN source_items si ON si.id = s.source_item_id
       WHERE si.canonical_url = $1 AND f.horizon_text = 'by 2040'`,
      [fixture.candidate.source_url],
    );
    const sibling = await pool.query(
      `SELECT s.slug FROM statements s
       JOIN forecasts f ON f.statement_id = s.id
       JOIN source_items si ON si.id = s.source_item_id
       WHERE si.canonical_url = $1 AND f.horizon_text = 'by 2060'`,
      [fixture.candidate.source_url],
    );
    const slug = String(primary.rows[0].slug);
    const siblingSlug = String(sibling.rows[0].slug);
    const original = String(primary.rows[0].normalized_text);
    const corrected = "Ada Quill stated a 10% extinction probability by 2040. Reviewer wording.";
    await expect(applyReviewDecision(pool, {
      statement_slug: slug,
      decision: "approve",
      reviewer: "local-operator",
      reviewed_at: "2026-10-04T12:00:00.000Z",
      note: null,
      rejection_reason: null,
      confirmations: emptyConfirmations(true),
      corrections: {},
      relationship: null,
      source_content_hash: null,
      evidence_hash: null,
      content_version: null,
    })).rejects.toThrow(/known question key/);
    await applyReviewDecision(pool, {
      statement_slug: slug,
      decision: "approve",
      reviewer: "local-operator",
      reviewed_at: "2026-10-04T12:05:00.000Z",
      note: "mapped to the registry key",
      rejection_reason: null,
      confirmations: emptyConfirmations(true),
      corrections: { normalized_text: corrected, question_key: "ai_extinction_unconditional" },
      relationship: { other_statement_slug: siblingSlug, relationship_type: "updates" },
      source_content_hash: null,
      evidence_hash: null,
      content_version: null,
    });
    await pool.query(
      `INSERT INTO statement_relationships (
         id, from_statement_id, to_statement_id, relationship_type, method, confidence, review_state
       ) VALUES (
         gen_random_uuid(),
         (SELECT id FROM statements WHERE slug = $1),
         (SELECT id FROM statements WHERE slug = 'ada-extinction-2025'),
         'repeats', 'revision-language-0.1', 0.4, 'unreviewed'
       )`,
      [siblingSlug],
    );
    await pool.query(`UPDATE statements SET review_state = 'unreviewed', normalized_text = $2 WHERE slug = $1`, [slug, original]);
    await pool.query(
      `UPDATE forecasts SET review_state = 'unreviewed', question_key = 'extinction_unconditional'
       WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`,
      [slug],
    );
    await pool.query(
      `UPDATE statement_relationships SET method = 'revision-language-0.1', review_state = 'unreviewed'
       WHERE from_statement_id = (SELECT id FROM statements WHERE slug = $1) AND relationship_type = 'updates'`,
      [slug],
    );
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      await restoreCoveredDecisions(client);
      await client.query("COMMIT");
    } finally {
      client.release();
    }
    const restored = await pool.query(`SELECT normalized_text, review_state FROM statements WHERE slug = $1`, [slug]);
    expect(restored.rows[0].review_state).toBe("human_verified");
    expect(restored.rows[0].normalized_text).toBe(corrected);
    const forecast = await pool.query(
      `SELECT question_key, review_state FROM forecasts WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`,
      [slug],
    );
    expect(forecast.rows[0].question_key).toBe("ai_extinction_unconditional");
    expect(forecast.rows[0].review_state).toBe("human_verified");
    const curator = await pool.query(
      `SELECT method, review_state FROM statement_relationships
       WHERE from_statement_id = (SELECT id FROM statements WHERE slug = $1) AND relationship_type = 'updates'`,
      [slug],
    );
    expect(curator.rows[0].method).toBe("curator_review");
    expect(curator.rows[0].review_state).toBe("human_verified");
    const machine = await pool.query(
      `SELECT method, review_state FROM statement_relationships
       WHERE from_statement_id = (SELECT id FROM statements WHERE slug = $1) AND relationship_type = 'repeats'`,
      [siblingSlug],
    );
    expect(machine.rows[0].method).toBe("revision-language-0.1");
    expect(machine.rows[0].review_state).toBe("unreviewed");

    const qualitative = await stageCandidates(pool, [{
      person_id: "person:ada-quill",
      source_url: `${prefix}qualitative`,
      content_hash: "cd".repeat(32),
      evidence_text: "Extinction from AI is unlikely.",
      extractor_name: "rule-extract",
      extractor_version: "rule-extract/0.4.0",
      normalized_text: "Extinction from AI is unlikely.",
      statement_type: "explicit_qualitative",
      role: "author",
      ownership: "owned",
      source_type: "blog",
      attribution_method: "byline",
    }]);
    expect(qualitative.staged).toBe(1);
    const qual = await pool.query(
      `SELECT s.slug, s.id, si.language, e.segment_hash
       FROM statements s
       JOIN source_items si ON si.id = s.source_item_id
       JOIN evidence_segments e ON e.id = s.evidence_segment_id
       WHERE si.canonical_url = $1`,
      [`${prefix}qualitative`],
    );
    expect(qual.rows[0].language).toBeNull();
    const qualSlug = String(qual.rows[0].slug);
    await applyReviewDecision(pool, {
      statement_slug: qualSlug,
      decision: "approve",
      reviewer: "local-operator",
      reviewed_at: "2026-10-04T13:00:00.000Z",
      note: null,
      rejection_reason: null,
      confirmations: emptyConfirmations(false),
      corrections: { normalized_text: "A reviewer kept this qualitative." },
      relationship: null,
      source_content_hash: null,
      evidence_hash: null,
      content_version: null,
    });
    await pool.query(
      `UPDATE evidence_segments SET text = 'Changed evidence that is not the approved span.', segment_hash = $2 WHERE id = (
         SELECT evidence_segment_id FROM statements WHERE slug = $1
       )`,
      [qualSlug, "ef".repeat(32)],
    );
    expect((await getStatement(qualSlug, pool))?.review_state).toBe("needs_review");
    await pool.query(
      `UPDATE statements SET review_state = 'unreviewed', normalized_text = 'Extinction from AI is unlikely.' WHERE slug = $1`,
      [qualSlug],
    );
    const restoreClient = await pool.connect();
    try {
      await restoreClient.query("BEGIN");
      await restoreCoveredDecisions(restoreClient);
      await restoreClient.query("COMMIT");
    } finally {
      restoreClient.release();
    }
    const stale = await pool.query(`SELECT review_state, normalized_text FROM statements WHERE slug = $1`, [qualSlug]);
    expect(stale.rows[0].review_state).toBe("unreviewed");
    expect(stale.rows[0].normalized_text).toBe("Extinction from AI is unlikely.");
    expect(await getStatement(qualSlug, pool)).toBeNull();
  });

  it("stages real pipeline candidates without publishing them", async () => {
    const produced = pythonCandidates();
    expect(produced.essay.length).toBeGreaterThan(0);
    expect(produced.essay.every((row) => row.review_state !== "human_verified")).toBe(true);
    expect(produced.essay.some((row) => row.value_numeric === 0.99)).toBe(false);
    expect(produced.podcast_observations[0]?.source_type).toBe("podcast");
    expect(produced.podcast_observations[0]?.ownership).toBe("appearance");
    expect(produced.podcast_observations[0]?.role).toBe("guest");
    const roles = (produced.podcast_observations[0]?.participants as Array<{ role: string }>).map((row) => row.role);
    expect(roles).toContain("guest");
    expect(roles).toContain("host");
    const staged = await stageCandidates(pool, [...produced.essay, ...produced.podcast]);
    expect(staged.staged).toBe(produced.essay.length + produced.podcast.length);
    const repeat = await stageCandidates(pool, [...produced.essay, ...produced.podcast]);
    expect(repeat.skipped).toBe(staged.staged);
    const essay = await pool.query(
      `SELECT s.review_state, s.slug, f.question_key, f.condition_text, f.horizon_text, f.value_numeric, to_char(f.target_date_end, 'YYYY-MM-DD') AS target_date_end,
              f.review_state AS forecast_state, si.published_timezone, si.language, src.source_type, src.owner_person_id, src.review_state AS source_state
       FROM statements s
       JOIN source_items si ON si.id = s.source_item_id
       JOIN sources src ON src.id = si.source_id
       LEFT JOIN forecasts f ON f.statement_id = s.id
       WHERE si.canonical_url = $1`,
      [produced.essay[0]?.source_url],
    );
    expect(essay.rows.every((row) => row.review_state === "unreviewed")).toBe(true);
    expect(essay.rows.every((row) => row.forecast_state === "unreviewed")).toBe(true);
    expect(essay.rows.every((row) => row.source_state === "unreviewed")).toBe(true);
    expect(essay.rows[0].published_timezone).toBe("-05:00");
    expect(essay.rows[0].language).toBe("en");
    expect(essay.rows[0].source_type).toBe("blog");
    expect(essay.rows[0].owner_person_id).toBeTruthy();
    const conditional = essay.rows.find((row) => row.question_key === "extinction_conditional_agi");
    expect(conditional?.condition_text).toContain("if we build AGI");
    expect(Number(conditional?.value_numeric)).toBeCloseTo(0.1);
    expect(conditional?.target_date_end).toBe("2040-12-31");
    for (const row of essay.rows) expect(await getStatement(String(row.slug), pool)).toBeNull();
    const podcast = await pool.query(
      `SELECT s.slug, e.start_ms, src.source_type, src.owner_person_id, sp.role
       FROM statements s
       JOIN evidence_segments e ON e.id = s.evidence_segment_id
       JOIN source_items si ON si.id = s.source_item_id
       JOIN sources src ON src.id = si.source_id
       LEFT JOIN source_participants sp ON sp.source_item_id = si.id AND sp.role = 'guest'
       WHERE si.canonical_url = $1
       ORDER BY e.start_ms`,
      [produced.podcast[0]?.source_url],
    );
    expect(podcast.rows.map((row) => row.start_ms)).toEqual([62000, 910000]);
    expect(podcast.rows.every((row) => row.source_type === "podcast")).toBe(true);
    expect(podcast.rows.every((row) => row.owner_person_id === null)).toBe(true);
    expect(podcast.rows.every((row) => row.role === "guest")).toBe(true);
    const metadata = await pool.query(
      `SELECT metadata_json->'participants' AS participants FROM source_items WHERE canonical_url = $1 LIMIT 1`,
      [produced.podcast[0]?.source_url],
    );
    const names = (metadata.rows[0].participants as Array<{ role: string }>).map((row) => row.role);
    expect(names).toContain("host");
    await applyReviewDecision(pool, {
      statement_slug: String(essay.rows[0].slug),
      decision: "reject",
      reviewer: "local-operator",
      reviewed_at: "2026-10-04T14:00:00.000Z",
      note: null,
      rejection_reason: "not_a_forecast",
      confirmations: emptyConfirmations(false),
      corrections: {},
      relationship: null,
      source_content_hash: null,
      evidence_hash: null,
      content_version: null,
    });
    expect(await getStatement(String(essay.rows[0].slug), pool)).toBeNull();
    const rejected = await pool.query(`SELECT review_state FROM statements WHERE slug = $1`, [essay.rows[0].slug]);
    expect(rejected.rows[0].review_state).toBe("rejected");
  });
});

afterAll(async () => {
  await pool.query(
    `DELETE FROM statement_relationships WHERE from_statement_id IN (
       SELECT s.id FROM statements s JOIN source_items si ON si.id = s.source_item_id WHERE si.canonical_url LIKE $1
     ) OR to_statement_id IN (
       SELECT s.id FROM statements s JOIN source_items si ON si.id = s.source_item_id WHERE si.canonical_url LIKE $1
     )`,
    [`${prefix}%`],
  );
  await pool.query(
    `DELETE FROM review_decisions WHERE statement_id IN (
       SELECT s.id FROM statements s JOIN source_items si ON si.id = s.source_item_id WHERE si.canonical_url LIKE $1
     )`,
    [`${prefix}%`],
  );
  await pool.query(
    `DELETE FROM statement_extractions WHERE statement_id IN (
       SELECT s.id FROM statements s JOIN source_items si ON si.id = s.source_item_id WHERE si.canonical_url LIKE $1
     )`,
    [`${prefix}%`],
  );
  await pool.query(
    `DELETE FROM forecasts WHERE statement_id IN (
       SELECT s.id FROM statements s JOIN source_items si ON si.id = s.source_item_id WHERE si.canonical_url LIKE $1
     )`,
    [`${prefix}%`],
  );
  await pool.query(
    `DELETE FROM source_participants WHERE source_item_id IN (
       SELECT id FROM source_items WHERE canonical_url LIKE $1
     )`,
    [`${prefix}%`],
  );
  await pool.query(
    `DELETE FROM statements WHERE source_item_id IN (SELECT id FROM source_items WHERE canonical_url LIKE $1)`,
    [`${prefix}%`],
  );
  await pool.query(`DELETE FROM evidence_segments WHERE source_item_id IN (SELECT id FROM source_items WHERE canonical_url LIKE $1)`, [`${prefix}%`]);
  await pool.query(`DELETE FROM source_items WHERE canonical_url LIKE $1`, [`${prefix}%`]);
  await pool.query(`DELETE FROM sources WHERE canonical_url LIKE $1`, [`${prefix}%`]);
  await pool.end();
});
