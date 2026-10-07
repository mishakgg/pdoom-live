import { readFileSync } from "node:fs";
import { afterAll, beforeEach, describe, expect, it } from "vitest";
import { reviewCommandSchema, type CurrentReviewManifest } from "@pdoom/contracts";
import { createPool } from "../packages/db/src/pool";
import { importCanonical, resetDatabase, validateDocument } from "../packages/db/src/import";
import { applyReviewDecision, emptyConfirmations, exportReviewManifest, importReviewManifest, validateReviewManifest, validateReviewManifestInDatabase } from "../packages/db/src/review";
import { getStatement } from "../packages/db/src/queries";

const pool = createPool(process.env.DATABASE_URL!);
const original = validateDocument(JSON.parse(readFileSync("data/fixtures/refresh/dataset.json", "utf8")));
original.forecasts[0].question_key = "ai_extinction_unconditional";
const slug = original.statements[0].slug;
function command(overrides: Record<string, unknown> = {}) {
  return reviewCommandSchema.parse({
    statement_slug: slug, decision: "approve", reviewer: "manifest-test",
    reviewed_at: "2026-10-07T12:00:00Z", note: null, rejection_reason: null,
    confirmations: emptyConfirmations(true), corrections: {}, relationship: null,
    source_content_hash: null, evidence_hash: null, content_version: null, ...overrides,
  });
}
async function fresh(doc = original) {
  await resetDatabase(pool);
  await importCanonical(pool, doc);
}
async function countDecisions() {
  return Number((await pool.query("SELECT count(*) AS count FROM review_decisions")).rows[0].count);
}
function legacy(manifest: CurrentReviewManifest) {
  return { schema_version: "review-decisions/1.0.0", decisions: manifest.decisions.map((entry) => {
    const { machine_claim: _machine, accepted_claim: _accepted, ...decision } = entry;
    return decision;
  }) };
}

describe("bound review manifest recovery", () => {
  beforeEach(() => fresh());
  afterAll(async () => { await resetDatabase(pool); await pool.end(); });

  it("rejects an exported approval against changed interpretation on identical source bytes", async () => {
    await applyReviewDecision(pool, command());
    const manifest = await exportReviewManifest(pool);
    expect(manifest.schema_version).toBe("review-decisions/2.0.0");
    expect(manifest.decisions[0].machine_claim?.version).toBe(1);
    expect(manifest.decisions[0].accepted_claim?.forecast?.condition_text).toBeNull();
    const changed = structuredClone(original);
    changed.forecasts[0].condition_text = "A different unreviewed conditioning event";
    await fresh(changed);
    expect(await validateReviewManifestInDatabase(pool, manifest)).toEqual([expect.stringMatching(/does not cover the current claim/)]);
    await expect(importReviewManifest(pool, manifest)).rejects.toThrow(/does not cover the current claim/);
    expect(await countDecisions()).toBe(0);
    expect((await getStatement(slug, pool))?.review_state).toBe("machine_validated");
  });

  it("keeps legacy manifests inspectable but cannot mint a fresh approval from them", async () => {
    await applyReviewDecision(pool, command());
    const manifest = legacy(await exportReviewManifest(pool));
    expect(validateReviewManifest(manifest).schema_version).toBe("review-decisions/1.0.0");
    await fresh();
    expect((await validateReviewManifestInDatabase(pool, manifest)).join(" ")).toMatch(/requires bound.*snapshots/);
    await expect(importReviewManifest(pool, manifest)).rejects.toThrow(/requires bound.*snapshots/);
    expect(await countDecisions()).toBe(0);
  });

  it("recovers exact cumulative corrections in deterministic order and remains idempotent", async () => {
    const corrections = { normalized_text: "A reviewed interpretation.", condition_text: "Unconditional" };
    await applyReviewDecision(pool, command({ corrections }));
    await applyReviewDecision(pool, command({ decision: "needs_changes", reviewed_at: "2026-10-07T13:00:00Z" }));
    await applyReviewDecision(pool, command({ reviewed_at: "2026-10-07T14:00:00Z" }));
    const manifest = await exportReviewManifest(pool);
    const expectedSnapshots = manifest.decisions.map((entry) => [entry.machine_claim, entry.accepted_claim]);
    manifest.decisions.reverse();
    await fresh();
    expect(await validateReviewManifestInDatabase(pool, manifest)).toEqual([]);
    expect(await countDecisions()).toBe(0);
    expect((await getStatement(slug, pool))?.normalized_text).toBe(original.statements[0].normalized_text);
    expect(await importReviewManifest(pool, manifest)).toEqual({ applied: 3, idempotent: 0 });
    expect(await importReviewManifest(pool, manifest)).toEqual({ applied: 0, idempotent: 3 });
    expect((await exportReviewManifest(pool)).decisions.map((entry) => [entry.machine_claim, entry.accepted_claim])).toEqual(expectedSnapshots);
    await importCanonical(pool, original);
    expect(await getStatement(slug, pool)).toMatchObject({ review_state: "human_verified", normalized_text: corrections.normalized_text, forecast: { condition_text: corrections.condition_text } });
  });

  it("restores a corrected evidence span without trusting only its hash", async () => {
    const evidence = "the chance of human extinction from AI is 15% by 2070.";
    await applyReviewDecision(pool, command({ corrections: { evidence_text: evidence } }));
    const manifest = await exportReviewManifest(pool);
    expect(manifest.decisions[0].accepted_claim?.evidence.hash).not.toBe(manifest.decisions[0].machine_claim?.evidence.hash);
    await fresh();
    expect(await validateReviewManifestInDatabase(pool, manifest)).toEqual([]);
    await importReviewManifest(pool, manifest);
    expect((await getStatement(slug, pool))?.evidence.text).toBe(evidence);
    await importCanonical(pool, original);
    expect((await getStatement(slug, pool))?.review_state).toBe("human_verified");
    expect((await getStatement(slug, pool))?.evidence.text).toBe(evidence);
  });

  it("rolls back earlier decisions when a later entry cannot reconstruct its accepted claim", async () => {
    await applyReviewDecision(pool, command({ corrections: { normalized_text: "First correction" } }));
    await applyReviewDecision(pool, command({ decision: "needs_changes", reviewed_at: "2026-10-07T13:00:00Z" }));
    const manifest = await exportReviewManifest(pool);
    manifest.decisions[1].accepted_claim!.normalized_text = "Not produced by the recorded correction";
    await fresh();
    expect((await validateReviewManifestInDatabase(pool, manifest)).join(" ")).toMatch(/do not reconstruct the accepted claim/);
    await expect(importReviewManifest(pool, manifest)).rejects.toThrow(/do not reconstruct the accepted claim/);
    expect(await countDecisions()).toBe(0);
    expect((await getStatement(slug, pool))?.normalized_text).toBe(original.statements[0].normalized_text);
  });

  it("rejects incompatible snapshot versions and reused keys with a changed action or snapshot", async () => {
    await applyReviewDecision(pool, command());
    const manifest = await exportReviewManifest(pool);
    const unsupported = structuredClone(manifest);
    (unsupported.decisions[0].machine_claim as unknown as { version: number }).version = 2;
    expect(() => validateReviewManifest(unsupported)).toThrow();
    const mismatched = structuredClone(manifest);
    mismatched.decisions[0].decision = "needs_changes";
    await expect(importReviewManifest(pool, mismatched)).rejects.toThrow(/conflicting review decision/);
    const drifted = structuredClone(manifest);
    drifted.decisions[0].accepted_claim!.normalized_text = "Different snapshot for an existing key";
    await expect(importReviewManifest(pool, drifted)).rejects.toThrow(/conflicting review decision/);
  });

  it("keeps exact original retries idempotent after a corrected evidence hash", async () => {
    const evidenceHash = (await pool.query(`SELECT e.segment_hash FROM evidence_segments e
      JOIN statements s ON s.evidence_segment_id = e.id WHERE s.slug = $1`, [slug])).rows[0].segment_hash;
    const correction = command({ evidence_hash: evidenceHash, corrections: {
      evidence_text: "the chance of human extinction from AI is 15% by 2070.",
    } });
    const first = await applyReviewDecision(pool, correction);
    expect(await applyReviewDecision(pool, correction)).toEqual({ decision_key: first.decision_key, idempotent: true });
    const manifest = await exportReviewManifest(pool);
    expect(await importReviewManifest(pool, manifest)).toEqual({ applied: 0, idempotent: 1 });
  });

  it("can replay a legacy rejection while retaining unknown snapshot coverage", async () => {
    const manifest = { schema_version: "review-decisions/1.0.0", decisions: [command({
      decision: "reject", rejection_reason: "extraction_error", confirmations: emptyConfirmations(false),
    })] };
    expect(await validateReviewManifestInDatabase(pool, manifest)).toEqual([]);
    expect(await countDecisions()).toBe(0);
    await importReviewManifest(pool, manifest);
    const restored = await exportReviewManifest(pool);
    expect(restored.decisions[0].machine_claim).toBeNull();
    expect(restored.decisions[0].accepted_claim).toBeNull();
    expect(await getStatement(slug, pool)).toBeNull();
    expect(await importReviewManifest(pool, manifest)).toEqual({ applied: 0, idempotent: 1 });
  });

  it("exports legacy null snapshots without filling them from mutable current rows", async () => {
    await applyReviewDecision(pool, command());
    await pool.query("UPDATE review_decisions SET machine_claim_json = NULL, accepted_claim_json = NULL");
    const manifest = await exportReviewManifest(pool);
    expect(manifest.decisions[0].machine_claim).toBeNull();
    expect(manifest.decisions[0].accepted_claim).toBeNull();
    await fresh();
    await expect(importReviewManifest(pool, manifest)).rejects.toThrow(/requires bound.*snapshots/);
  });
});
