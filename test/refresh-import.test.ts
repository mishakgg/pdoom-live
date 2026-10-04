import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { candidateKey, type CanonicalImport } from "@pdoom/contracts";
import { importCanonical, resetDatabase, validateDocument } from "../packages/db/src/import";
import { createPool } from "../packages/db/src/pool";
import { getPublicCatalog, getPublicSource } from "../packages/db/src/public-read";
import { getCoverage, getStatement } from "../packages/db/src/queries";
import { applyReviewDecision, emptyConfirmations } from "../packages/db/src/review";
import { afterAll, describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");
const manifest = JSON.parse(readFileSync("data/fixtures/refresh/manifest.json", "utf8")) as {
  numeric_slug: string;
  qualitative_slug: string;
  numeric_evidence_slug: string;
  source_item_slug: string;
  changed_evidence_slug: string;
  changed_source_item_slug: string;
};
const original = validateDocument(JSON.parse(readFileSync("data/fixtures/refresh/dataset.json", "utf8")));
const changed = validateDocument(JSON.parse(readFileSync("data/fixtures/refresh/dataset-changed.json", "utf8")));
const partial = validateDocument(JSON.parse(readFileSync("data/fixtures/refresh/dataset-partial.json", "utf8")));
const corrected = "Reviewed wording: the chance of human extinction from AI is 15% by 2070.";

function machineKey(doc: CanonicalImport, slug: string): string {
  const statement = doc.statements.find((row) => row.slug === slug);
  if (!statement) throw new Error(slug);
  const item = doc.source_items.find((row) => row.slug === statement.source_item_slug);
  const evidence = doc.evidence_segments.find((row) => row.slug === statement.evidence_slug);
  const forecast = doc.forecasts.find((row) => row.statement_slug === slug);
  if (!item?.content_hash || !evidence) throw new Error(`missing provenance for ${slug}`);
  return candidateKey({
    person_slug: statement.person_slug,
    source_content_hash: item.content_hash,
    evidence_hash: createHash("sha256").update(evidence.text, "utf8").digest("hex"),
    extractor_name: statement.extractor_version.split("/")[0] || statement.extractor_version,
    extractor_version: statement.extractor_version,
    statement_type: statement.statement_type,
    question_key: forecast?.question_key ?? null,
    horizon_text: forecast?.horizon_text ?? null,
    unit: forecast?.unit ?? null,
    value_type: forecast?.value_type ?? null,
    value_numeric: forecast?.value_numeric ?? null,
    value_min: forecast?.value_min ?? null,
    value_max: forecast?.value_max ?? null,
  });
}

describe("refresh import preserves review and freshness", () => {
  afterAll(async () => {
    await resetDatabase(pool);
    await pool.end();
  });

  it("imports the offline refresh, keeps review across an unchanged reimport, and downgrades a stale approval", async () => {
    await resetDatabase(pool);
    await importCanonical(pool, partial);
    const partialRun = await pool.query(
      `SELECT status, failed_count FROM ingestion_runs WHERE slug = 'belief-corpus-2026-09'`,
    );
    expect(partialRun.rows[0].status).toBe("partial");
    expect(partialRun.rows[0].failed_count).toBeGreaterThan(0);
    const broken = await pool.query(
      `SELECT last_checked_at IS NOT NULL AS checked, last_success_at IS NULL AS no_success
       FROM sources WHERE slug = 'refresh-ada-rss-broken'`,
    );
    expect(broken.rows[0]).toEqual({ checked: true, no_success: true });

    const first = await importCanonical(pool, original);
    const second = await importCanonical(pool, original);
    expect(second.counts.statements).toBe(first.counts.statements);
    const storedKey = await pool.query(`SELECT candidate_key FROM statements WHERE slug = $1`, [manifest.numeric_slug]);
    expect(storedKey.rows[0].candidate_key).toBe(machineKey(original, manifest.numeric_slug));

    const source = await getPublicSource("refresh-ada-html-page", "2026-10-04T00:00:00.000Z", pool);
    expect(source?.last_checked_at).toBe("2026-10-01T12:00:00.000Z");
    expect(source?.last_success_at).toBe("2026-10-01T12:00:00.000Z");
    expect(source?.freshness).toBe("current");
    const catalog = await getPublicCatalog(null, pool);
    expect(catalog.dataset?.source_generated_at).toBe("2026-10-01T12:05:00.000Z");
    expect(catalog.dataset?.imported_at).not.toBe(catalog.dataset?.source_generated_at);
    expect(catalog.latest_source_checked_at).toBe("2026-10-01T12:00:00.000Z");
    expect(catalog.latest_source_success_at).toBe("2026-10-01T12:00:00.000Z");
    const coverage = await getCoverage("2026-10-04T00:00:00.000Z", pool);
    expect(coverage.latest_source_checked_at).toBe("2026-10-01T12:00:00.000Z");

    const beforeText = await pool.query(`SELECT normalized_text FROM statements WHERE slug = $1`, [manifest.numeric_slug]);
    await applyReviewDecision(pool, {
      statement_slug: manifest.numeric_slug,
      decision: "approve",
      reviewer: "local-operator",
      reviewed_at: "2026-10-02T12:00:00.000Z",
      note: "Fixture approval of an explicit extinction probability.",
      rejection_reason: null,
      confirmations: emptyConfirmations(true),
      corrections: {
        normalized_text: corrected,
        question_key: "ai_extinction_unconditional",
        horizon_text: "by 2070",
      },
      relationship: null,
      source_content_hash: null,
      evidence_hash: null,
      content_version: null,
    });
    await applyReviewDecision(pool, {
      statement_slug: manifest.qualitative_slug,
      decision: "reject",
      reviewer: "local-operator",
      reviewed_at: "2026-10-02T12:05:00.000Z",
      note: null,
      rejection_reason: "not_a_forecast",
      confirmations: emptyConfirmations(false),
      corrections: {},
      relationship: null,
      source_content_hash: null,
      evidence_hash: null,
      content_version: null,
    });
    const extraction = await pool.query(
      `SELECT e.normalized_text FROM statement_extractions e JOIN statements s ON s.id = e.statement_id WHERE s.slug = $1`,
      [manifest.numeric_slug],
    );
    expect(extraction.rows[0].normalized_text).toBe(beforeText.rows[0].normalized_text);

    await importCanonical(pool, original);
    const kept = await getStatement(manifest.numeric_slug, pool);
    expect(kept?.review_state).toBe("human_verified");
    expect(kept?.normalized_text).toBe(corrected);
    expect(kept?.forecast?.question_key).toBe("ai_extinction_unconditional");
    expect(kept?.forecast?.horizon_text).toBe("by 2070");
    expect(await getStatement(manifest.qualitative_slug, pool)).toBeNull();
    const decisionsAfterReimport = await pool.query(`SELECT count(*)::int AS count FROM review_decisions`);
    expect(decisionsAfterReimport.rows[0].count).toBe(2);
    const extractionAfter = await pool.query(
      `SELECT e.normalized_text FROM statement_extractions e JOIN statements s ON s.id = e.statement_id WHERE s.slug = $1`,
      [manifest.numeric_slug],
    );
    expect(extractionAfter.rows[0].normalized_text).toBe(beforeText.rows[0].normalized_text);

    await importCanonical(pool, changed);
    const stale = await getStatement(manifest.numeric_slug, pool);
    expect(stale?.review_state).toBe("needs_review");
    expect(stale?.evidence.slug).toBe(manifest.changed_evidence_slug);
    expect(stale?.source_item.slug).toBe(manifest.changed_source_item_slug);
    const storedReview = await pool.query(`SELECT review_state FROM statements WHERE slug = $1`, [manifest.numeric_slug]);
    expect(storedReview.rows[0].review_state).toBe("human_verified");
    const versions = await pool.query(
      `SELECT slug, content_version, is_current FROM source_items WHERE canonical_url = 'https://refresh.example/notes' ORDER BY content_version`,
    );
    expect(versions.rows).toEqual([
      { slug: manifest.source_item_slug, content_version: 1, is_current: false },
      { slug: manifest.changed_source_item_slug, content_version: 2, is_current: true },
    ]);
    const oldEvidence = await pool.query(`SELECT slug FROM evidence_segments WHERE slug = $1`, [manifest.numeric_evidence_slug]);
    expect(oldEvidence.rowCount).toBe(1);
    expect((await pool.query(`SELECT count(*)::int AS count FROM review_decisions`)).rows[0].count).toBe(2);
    expect(await getStatement(manifest.qualitative_slug, pool)).toBeNull();
    const rejected = await pool.query(`SELECT review_state FROM statements WHERE slug = $1`, [manifest.qualitative_slug]);
    expect(rejected.rows[0].review_state).toBe("rejected");

    const statementCount = await pool.query(`SELECT count(*)::int AS count FROM statements`);
    await importCanonical(pool, changed);
    expect((await pool.query(`SELECT count(*)::int AS count FROM statements`)).rows[0].count).toBe(statementCount.rows[0].count);
    expect((await pool.query(`SELECT count(*)::int AS count FROM review_decisions`)).rows[0].count).toBe(2);

    await importCanonical(pool, original);
    const restored = await getStatement(manifest.numeric_slug, pool);
    expect(restored?.review_state).toBe("human_verified");
    expect(restored?.normalized_text).toBe(corrected);
    expect(restored?.forecast?.question_key).toBe("ai_extinction_unconditional");
    expect(restored?.evidence.slug).toBe(manifest.numeric_evidence_slug);
    expect(await getStatement(manifest.qualitative_slug, pool)).toBeNull();
  });
});
