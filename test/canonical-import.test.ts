import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { canonicalImportSchema, classifyFreshness } from "@pdoom/contracts";
import { validateDocument, importCanonical, resetDatabase } from "../packages/db/src/import";
import { createPool } from "../packages/db/src/pool";
import { getCoverage, getOverview, getPerson, getStatement, listStatements } from "../packages/db/src/queries";
import { describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");

function liveExport() {
  const raw = execFileSync("python", ["-c", "import json; from pdoom_pipeline.export.canonical import export_seed; print(json.dumps(export_seed()))"], {
    cwd: process.cwd(),
    env: { ...process.env, PYTHONPATH: "pipeline" },
    maxBuffer: 64 * 1024 * 1024,
  });
  return JSON.parse(raw.toString("utf8"));
}

describe("canonical dataset contract", () => {
  it("accepts the synthetic fixture and a live export", () => {
    const fixture = JSON.parse(readFileSync("data/fixtures/synthetic/dataset.json", "utf8"));
    expect(validateDocument(fixture).dataset_kind).toBe("synthetic");
    const live = validateDocument(liveExport());
    expect(live.dataset_kind).toBe("live");
    expect(live.statements).toHaveLength(0);
    expect(live.people.length).toBeGreaterThan(300);
    expect(live.sources.length).toBeGreaterThan(200);
  });

  it("rejects a live document that uses fixture markers", () => {
    const fixture = validateDocument(JSON.parse(readFileSync("data/fixtures/synthetic/dataset.json", "utf8")));
    expect(() => validateDocument({ ...fixture, dataset_kind: "live" })).toThrow(/synthetic_fixture|fixture/);
  });

  it("stores a precomputed hash and does not require a body", async () => {
    const hash = "a".repeat(64);
    const fixture = validateDocument(JSON.parse(readFileSync("data/fixtures/synthetic/dataset.json", "utf8")));
    const item = {
      ...fixture.source_items[0],
      slug: "hash-only-item",
      logical_key: "hash-only-item",
      content_hash: hash,
      content_hash_input: null,
      canonical_url: "https://synthetic.pdoom.example/items/hash-only-item",
    };
    const doc = {
      ...fixture,
      dataset_id: "hash-only",
      source_items: [item],
      participants: [],
      evidence_segments: [],
      statements: [],
      forecasts: [],
      relationships: [],
      extraction_runs: [],
    };
    await importCanonical(pool, doc);
    const stored = await pool.query("SELECT content_hash FROM source_items WHERE slug = 'hash-only-item'");
    expect(stored.rows[0].content_hash).toBe(hash);
    const columns = await pool.query(
      `SELECT column_name FROM information_schema.columns WHERE table_name = 'source_items' AND column_name = 'content_hash_input'`,
    );
    expect(columns.rowCount).toBe(0);
    await resetDatabase(pool);
  });

  it("imports the live seed idempotently without deleting the fixture people", async () => {
    const before = await pool.query("SELECT count(*)::int AS count FROM people WHERE slug = 'ada-quill'");
    const live = liveExport();
    const first = await importCanonical(pool, live);
    const second = await importCanonical(pool, live);
    expect(second.counts.people).toBe(first.counts.people);
    const ada = await pool.query("SELECT count(*)::int AS count FROM people WHERE slug = 'ada-quill'");
    expect(ada.rows[0].count).toBe(before.rows[0].count);
    const identity = await pool.query(
      `SELECT verification_method, verification_detail, confidence_level, review_state
       FROM external_identities WHERE verification_detail = 'openalex_exact_name_and_institution' LIMIT 1`,
    );
    expect(identity.rows[0]).toMatchObject({
      verification_method: "structured_academic_source",
      verification_detail: "openalex_exact_name_and_institution",
    });
    expect(["high", "medium", "low"]).toContain(identity.rows[0].confidence_level);
    const overview = await getOverview(pool);
    expect(overview.dataset.dataset_kind).toBe("live");
    expect(overview.trends).toEqual([]);
    const needsReview = await pool.query(
      `SELECT p.slug FROM external_identities e JOIN people p ON p.id = e.person_id WHERE e.review_state = 'needs_review' LIMIT 1`,
    );
    expect(needsReview.rowCount).toBeGreaterThan(0);
    const person = await getPerson(String(needsReview.rows[0].slug), pool);
    expect(person?.identities.some((row) => row.review_state === "needs_review" && row.settled === false)).toBe(true);
    await resetDatabase(pool);
  });

  it("rolls back a failed import", async () => {
    const before = await pool.query("SELECT count(*)::int AS count FROM statements");
    const fixture = validateDocument(JSON.parse(readFileSync("data/fixtures/synthetic/dataset.json", "utf8")));
    const broken = {
      ...fixture,
      dataset_id: "broken",
      statements: fixture.statements.map((statement, index) =>
        index === 0 ? { ...statement, evidence_slug: "missing-evidence" } : statement,
      ),
    };
    await expect(importCanonical(pool, broken)).rejects.toThrow();
    const after = await pool.query("SELECT count(*)::int AS count FROM statements");
    expect(after.rows[0].count).toBe(before.rows[0].count);
    const current = await pool.query("SELECT dataset_id FROM dataset_imports WHERE is_current");
    expect(current.rows[0].dataset_id).not.toBe("broken");
  });

  it("imports the published live corpus without collapsing distinct horizons", async () => {
    const live = validateDocument(JSON.parse(readFileSync("data/collections/cohort-v2026-09/canonical-live.json", "utf8")));
    expect(live.dataset_kind).toBe("live");
    try {
      await importCanonical(pool, live);
      const stored = await pool.query(
        `SELECT s.slug, s.candidate_key
         FROM statements s
         WHERE s.slug = ANY($1::text[])`,
        [live.statements.map((statement) => statement.slug)],
      );
      expect(stored.rowCount).toBe(live.statements.length);
      expect(new Set(stored.rows.map((row) => row.candidate_key)).size).toBe(stored.rowCount);
      const horizons = await pool.query(
        `SELECT f.horizon_text
         FROM forecasts f
         JOIN statements s ON s.id = f.statement_id
         JOIN people p ON p.id = s.person_id
         WHERE p.slug = 'holden-karnofsky' AND f.horizon_text IN ('by 2036', 'by 2060', 'by 2100')`,
      );
      expect(horizons.rowCount).toBe(6);
    } finally {
      await resetDatabase(pool);
    }
  });

  it("hides rejected statements and classifies freshness", async () => {
    await pool.query(
      `UPDATE statements SET review_state = 'rejected' WHERE slug = 'riley-hostile-2025'`,
    );
    const hidden = await getStatement("riley-hostile-2025", pool);
    expect(hidden).toBeNull();
    const listed = await listStatements({ review_state: "rejected", limit: 20 }, pool);
    expect(listed.data).toHaveLength(0);
    expect(listed.page.total).toBe(0);
    await pool.query(`UPDATE statements SET review_state = 'human_verified' WHERE slug = 'riley-hostile-2025'`);
    const coverage = await getCoverage("2025-08-15T00:00:00.000Z", pool);
    expect(coverage.cohort_size).toBe(8);
    expect(coverage.freshness.current).toBeGreaterThan(0);
    expect(classifyFreshness(null, "2025-08-15T00:00:00.000Z")).toBe("never_checked");
    expect(coverage.unavailable_or_failing_sources).toBeGreaterThan(0);
  });
});
