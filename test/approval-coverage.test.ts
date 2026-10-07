import { readFileSync } from "node:fs";
import { reviewCommandSchema, type CanonicalImport } from "@pdoom/contracts";
import { afterAll, beforeEach, describe, expect, it } from "vitest";
import { effectiveReviewStateSql } from "../packages/db/src/coverage";
import { importCanonical, resetDatabase, validateDocument } from "../packages/db/src/import";
import { createPool } from "../packages/db/src/pool";
import { applyReviewDecision, emptyConfirmations } from "../packages/db/src/review";

const pool = createPool(process.env.DATABASE_URL!);
const original = validateDocument(JSON.parse(readFileSync("data/fixtures/refresh/dataset.json", "utf8")));
original.forecasts[0].question_key = "ai_extinction_unconditional";
const slug = original.statements[0].slug;

function command(overrides: Record<string, unknown> = {}) {
  return reviewCommandSchema.parse({
    statement_slug: slug, decision: "approve", reviewer: "t02-test-operator",
    reviewed_at: "2026-10-06T12:00:00Z", note: null, rejection_reason: null,
    confirmations: emptyConfirmations(true), corrections: {}, relationship: null,
    source_content_hash: null, evidence_hash: null, content_version: null,
    ...overrides,
  });
}

async function state() {
  const result = await pool.query(`SELECT ${effectiveReviewStateSql("s")} AS effective,
    s.review_state AS stored, s.normalized_text, f.question_key, f.horizon_text, f.definition_text,
    e.text AS evidence_text, e.start_char, e.end_char
    FROM statements s LEFT JOIN forecasts f ON f.statement_id = s.id
    JOIN evidence_segments e ON e.id = s.evidence_segment_id WHERE s.slug = $1`, [slug]);
  return result.rows[0];
}

async function audit() {
  return (await pool.query(`SELECT to_jsonb(d) AS decision, to_jsonb(x) AS extraction
    FROM review_decisions d JOIN statements s ON s.id = d.statement_id
    JOIN statement_extractions x ON x.statement_id = s.id
    WHERE s.slug = $1 ORDER BY d.reviewed_at, d.decision_key`, [slug])).rows;
}

describe("approval covers the accepted claim and survives canonical replay", () => {
  beforeEach(async () => {
    await resetDatabase(pool);
    await importCanonical(pool, original);
  });
  afterAll(async () => {
    await resetDatabase(pool);
    await pool.end();
  });

  const changes: Array<[string, (doc: CanonicalImport) => void]> = [
    ["person", (doc) => {
      doc.people.push({ ...doc.people[0], slug: "refresh-other", display_name: "Refresh Other" });
      doc.statements[0].person_slug = "refresh-other";
    }],
    ["question", (doc) => { doc.forecasts[0].question_key = "ai_extinction_conditional_on_agi"; }],
    ["value", (doc) => { doc.forecasts[0].value_numeric = 0.2; doc.forecasts[0].value_text = "20%"; }],
    ["value shape", (doc) => {
      Object.assign(doc.forecasts[0], { value_type: "range", value_numeric: null, value_text: null, value_min: 0.1, value_max: 0.2 });
    }],
    ["distribution", (doc) => {
      Object.assign(doc.forecasts[0], { value_type: "distribution", value_numeric: null, value_text: null, distribution: { p10: 0.1, p90: 0.2 } });
    }],
    ["horizon", (doc) => { doc.forecasts[0].horizon_text = "by 2100"; }],
    ["type", (doc) => {
      doc.statements[0].statement_type = "model_inferred_signal";
      Object.assign(doc.forecasts[0], { forecast_kind: "classification", value_type: "none", value_numeric: null, value_text: null });
    }],
    ["extractor", (doc) => { doc.statements[0].extractor_version = "new-extractor/2.0"; }],
    ["normalized claim", (doc) => { doc.statements[0].normalized_text = "A different interpretation of the same evidence."; }],
    ["definition", (doc) => { doc.forecasts[0].definition_text = "catastrophic harm"; }],
    ["conditionality", (doc) => { doc.forecasts[0].condition_text = "conditional on AGI"; }],
    ["question wording", (doc) => { doc.forecasts[0].question_text = "Will AGI arrive?"; }],
    ["target date", (doc) => { doc.forecasts[0].target_date_end = "2100-12-31"; }],
    ["unit", (doc) => { doc.forecasts[0].unit = "share"; }],
    ["forecast kind", (doc) => { doc.forecasts[0].forecast_kind = "quantity"; }],
    ["resolution", (doc) => { doc.forecasts[0].resolution_criteria = "A different resolution rule"; }],
    ["evidence locator", (doc) => { doc.evidence_segments[0].start_ms = 1000; }],
    ["topics", (doc) => { doc.statements[0].topic_slugs = ["ai-disempowerment"]; }],
    ["removed forecast", (doc) => { doc.forecasts.splice(0, 1); }],
  ];

  it.each(changes)("requires review after re-extraction changes %s over the same bytes", async (_name, change) => {
    await applyReviewDecision(pool, command());
    const before = await audit();
    const changed = structuredClone(original);
    change(changed);
    await importCanonical(pool, changed);
    expect((await state()).effective).toBe("needs_review");
    expect(await audit()).toEqual(before);
    await importCanonical(pool, original);
    expect((await state()).effective).toBe("human_verified");
  });

  it("detects live semantic drift even when candidate key and evidence bytes are unchanged", async () => {
    await applyReviewDecision(pool, command());
    await pool.query(`UPDATE forecasts SET condition_text = 'if AGI is built'
      WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    expect((await state()).effective).toBe("needs_review");
  });

  it("normalizes topic order, timestamp offsets and JSON object serialization", async () => {
    const input = structuredClone(original);
    input.statements[0].topic_slugs = ["ai-extinction", "ai-disempowerment"];
    await importCanonical(pool, input);
    await applyReviewDecision(pool, command());
    const same = structuredClone(input);
    same.statements[0].topic_slugs.reverse();
    same.statements[0].event_time = "2024-06-01T02:00:00+02:00";
    await importCanonical(pool, JSON.parse(JSON.stringify(same)));
    expect((await state()).effective).toBe("human_verified");
  });

  it("retains cumulative corrections through needs_changes and empty-delta reapproval", async () => {
    const evidence = original.evidence_segments.find((row) => row.slug === original.statements[0].evidence_slug)!;
    const span = evidence.text.slice(evidence.text.indexOf("15%"));
    await applyReviewDecision(pool, command({ corrections: {
      normalized_text: "Accepted wording: a 15% chance of extinction by 2070.",
      horizon_text: "by the end of 2070", evidence_text: span, start_char: 5, end_char: 5 + span.length,
    } }));
    await applyReviewDecision(pool, command({ decision: "needs_changes", reviewed_at: "2026-10-06T13:00:00Z",
      corrections: { definition_text: "Human extinction from AI, unconditional." } }));
    await applyReviewDecision(pool, command({ reviewed_at: "2026-10-06T14:00:00Z" }));
    const accepted = await state();
    const before = await audit();
    expect(before.at(-1)?.decision.corrections_json).toEqual({});
    await importCanonical(pool, original);
    expect(await state()).toEqual(accepted);
    expect(await audit()).toEqual(before);

    // A canonical replay of the already accepted span is covered too, even
    // though its candidate key differs from the original machine span.
    const corrected = structuredClone(original);
    corrected.statements[0].normalized_text = accepted.normalized_text;
    corrected.forecasts[0].horizon_text = accepted.horizon_text;
    corrected.forecasts[0].definition_text = accepted.definition_text;
    Object.assign(corrected.evidence_segments.find((row) => row.slug === evidence.slug)!, {
      text: accepted.evidence_text, start_char: accepted.start_char, end_char: accepted.end_char,
    });
    await importCanonical(pool, corrected);
    expect(await state()).toEqual(accepted);
    await importCanonical(pool, original);
    expect(await state()).toEqual(accepted);
    expect(await audit()).toEqual(before);
  });

  it("retains corrections on exact unchanged reimport and can approve a changed interpretation", async () => {
    await applyReviewDecision(pool, command({ corrections: { normalized_text: "Accepted 15% extinction probability." } }));
    await importCanonical(pool, original);
    expect((await state()).normalized_text).toBe("Accepted 15% extinction probability.");
    expect((await state()).effective).toBe("human_verified");
    const changed = structuredClone(original);
    changed.forecasts[0].horizon_text = "by 2100";
    await importCanonical(pool, changed);
    expect((await state()).effective).toBe("needs_review");
    await applyReviewDecision(pool, command({ reviewed_at: "2026-10-06T15:00:00Z" }));
    await importCanonical(pool, changed);
    expect((await state()).effective).toBe("human_verified");
    await importCanonical(pool, original);
    expect((await state()).effective).toBe("needs_review");
  });

  it("fails closed on legacy approvals, preserves their cumulative deltas, and allows explicit reapproval", async () => {
    await applyReviewDecision(pool, command({ corrections: { normalized_text: "Legacy accepted correction." } }));
    await applyReviewDecision(pool, command({ decision: "needs_changes", reviewed_at: "2026-10-06T13:00:00Z" }));
    await applyReviewDecision(pool, command({ reviewed_at: "2026-10-06T14:00:00Z" }));
    // Simulate the additive migration's NULL columns on pre-migration audit rows.
    await pool.query(`UPDATE review_decisions SET machine_claim_json = NULL, accepted_claim_json = NULL
      WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    const before = await audit();
    expect((await state()).effective).toBe("needs_review");
    await importCanonical(pool, original);
    expect((await state()).normalized_text).toBe("Legacy accepted correction.");
    expect((await state()).effective).toBe("needs_review");
    expect(await audit()).toEqual(before);
    await applyReviewDecision(pool, command({ reviewed_at: "2026-10-06T15:00:00Z" }));
    expect((await state()).effective).toBe("human_verified");
  });
});
