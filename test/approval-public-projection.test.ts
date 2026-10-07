import { readFileSync } from "node:fs";
import { reviewCommandSchema, searchQuerySchema } from "@pdoom/contracts";
import { afterAll, describe, expect, it } from "vitest";
import { importCanonical, resetDatabase, validateDocument } from "../packages/db/src/import";
import { createPool } from "../packages/db/src/pool";
import { getStatement, listStatements } from "../packages/db/src/queries";
import { applyReviewDecision, emptyConfirmations } from "../packages/db/src/review";
import { searchPublic } from "../packages/db/src/search";

const pool = createPool(process.env.DATABASE_URL!);

// Integration regression for T01's nested public visibility policy together
// with T02's exact approval coverage. Run against the combined implementation.
describe("changed interpretation cannot retain an approved public forecast", () => {
  afterAll(async () => {
    await resetDatabase(pool);
    await pool.end();
  });
  it("keeps a needs_review statement visible while omitting its unreviewed forecast", async () => {
    await resetDatabase(pool);
    const original = validateDocument(JSON.parse(readFileSync("data/fixtures/refresh/dataset.json", "utf8")));
    original.forecasts[0].question_key = "ai_extinction_unconditional";
    await importCanonical(pool, original);
    const slug = original.statements[0].slug;
    await applyReviewDecision(pool, reviewCommandSchema.parse({
      statement_slug: slug, decision: "approve", reviewer: "t02-combined-test",
      reviewed_at: "2026-10-06T12:00:00Z", note: null, rejection_reason: null,
      confirmations: emptyConfirmations(true), corrections: {}, relationship: null,
      source_content_hash: null, evidence_hash: null, content_version: null,
    }));
    expect((await getStatement(slug, pool))?.forecast).toBeTruthy();
    const changed = structuredClone(original);
    changed.forecasts[0].condition_text = "if AGI is built";
    changed.forecasts[0].review_state = "unreviewed";
    await importCanonical(pool, changed);
    const stored = await pool.query(`SELECT review_state FROM forecasts
      WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    expect(stored.rows[0].review_state).toBe("unreviewed");
    const detail = await getStatement(slug, pool);
    expect(detail?.review_state).toBe("needs_review");
    expect(detail?.forecast).toBeNull();
    const listed = (await listStatements({ person: "refresh-ada", limit: 20 }, pool)).data.find((row) => row.slug === slug);
    expect(listed?.review_state).toBe("needs_review");
    expect(listed?.forecast).toBeNull();
    const found = (await searchPublic(searchQuerySchema.parse({
      q: "human extinction", type: "statement", person: "refresh-ada", limit: 20,
    }), pool)).groups.statement.data.find((row) => row.slug === slug);
    expect(found?.review_state).toBe("needs_review");
    expect(found?.forecast).toBeNull();
  });
});
