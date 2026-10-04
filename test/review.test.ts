import { readFileSync } from "node:fs";
import {
  candidateKey,
  curationEnabled,
  evidenceSupportsNumbers,
  reviewPriority,
  suggestQuestionKeys,
} from "@pdoom/contracts";
import { applyReviewDecision, emptyConfirmations, exportReviewManifest, getReviewItem, importReviewManifest, listReviewQueue, reviewStatus, stageCandidates, validateReviewManifestInDatabase } from "../packages/db/src/review";
import { createPool } from "../packages/db/src/pool";
import { getStatement, listStatements } from "../packages/db/src/queries";
import { POST } from "../apps/web/app/api/curation/decisions/route";
import CurationLayout from "../apps/web/app/curation/layout";
import CurationQueuePage from "../apps/web/app/curation/page";
import CurationItemPage from "../apps/web/app/curation/[slug]/page";
import { afterAll, describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");
const slug = "jonah-extinction-review-2024";

function command(overrides: Record<string, unknown> = {}) {
  return {
    statement_slug: slug,
    decision: "approve",
    reviewer: "local-operator",
    reviewed_at: "2026-09-26T12:00:00.000Z",
    note: null,
    rejection_reason: null,
    confirmations: emptyConfirmations(true),
    corrections: {},
    relationship: null,
    source_content_hash: null,
    evidence_hash: null,
    content_version: null,
    ...overrides,
  };
}

describe("review identity and policy", () => {
  it("keeps candidate identity stable when prose changes and distinct when evidence changes", () => {
    const base = {
      person_slug: "ada-quill",
      source_content_hash: "a".repeat(64),
      evidence_hash: "b".repeat(64),
      extractor_name: "rule-extract",
      extractor_version: "rule-extract-0.1.0",
      statement_type: "explicit_qualitative",
    };
    expect(candidateKey(base)).toBe(candidateKey(base));
    expect(candidateKey({ ...base, evidence_hash: "c".repeat(64) })).not.toBe(candidateKey(base));
    expect(candidateKey({ ...base, statement_type: "model_inferred_signal" })).not.toBe(candidateKey(base));
    const by2036 = candidateKey({
      ...base,
      statement_type: "explicit_numeric",
      question_key: "transformative_ai_by_year_probability",
      horizon_text: "by 2036",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.1,
    });
    const by2060 = candidateKey({
      ...base,
      statement_type: "explicit_numeric",
      question_key: "transformative_ai_by_year_probability",
      horizon_text: "by 2060",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.5,
    });
    expect(by2036).not.toBe(by2060);
    expect(candidateKey(base)).toBe(candidateKey({ ...base, question_key: null, horizon_text: null, value_numeric: null }));
    expect(suggestQuestionKeys({ normalized_text: "conditional extinction if AGI", topics: [] })).toEqual(["ai_extinction_conditional_on_agi"]);
    expect(suggestQuestionKeys({ normalized_text: "unconditional extinction by 2070", topics: [] })).toContain("ai_extinction_unconditional_by_2070");
    expect(suggestQuestionKeys({ normalized_text: "unconditional extinction by 2070", topics: [] })).not.toContain("ai_extinction_conditional_on_agi");
    expect(evidenceSupportsNumbers("was 30 percent", { unit: "probability", value_type: "point", value_numeric: 0.3, value_min: null, value_max: null })).toBe(true);
    expect(evidenceSupportsNumbers("serious risk", { unit: "probability", value_type: "point", value_numeric: 0.3, value_min: null, value_max: null })).toBe(false);
    expect(reviewPriority({ statement_type: "explicit_numeric", has_related: true, confidence: 0.2, confidence_level: null })).toBe(1);
    expect(reviewPriority({ statement_type: "model_inferred_signal", has_related: false, confidence: 0.9, confidence_level: "high" })).toBe(5);
    expect(curationEnabled({})).toBe(false);
    expect(curationEnabled({ PDOOM_CURATION_MODE: "local" })).toBe(true);
  });

  it("hides curation routes unless local mode is on", async () => {
    delete process.env.PDOOM_CURATION_MODE;
    expect(() => CurationLayout({ children: "hidden" })).toThrow(/404|NEXT_HTTP_ERROR_FALLBACK/);
    await expect(CurationQueuePage({ searchParams: Promise.resolve({}) })).rejects.toThrow(/404|NEXT_HTTP_ERROR_FALLBACK/);
    await expect(CurationItemPage({ params: Promise.resolve({ slug: "candidate-b2b3f47caf63803a" }) })).rejects.toThrow(/404|NEXT_HTTP_ERROR_FALLBACK/);
    const blocked = await POST(new Request("http://127.0.0.1/api/curation/decisions", { method: "POST", body: "{}" }));
    expect(blocked.status).toBe(404);
    process.env.PDOOM_CURATION_MODE = "local";
    const open = await POST(new Request("http://127.0.0.1/api/curation/decisions", { method: "POST", body: "{}", headers: { "content-type": "application/json" } }));
    expect(open.status).toBe(400);
    delete process.env.PDOOM_CURATION_MODE;
  });
});

describe("review decisions", () => {
  it("approves, corrects, rejects, replays, and restores public visibility", async () => {
    const distinct = await pool.query(`SELECT candidate_key FROM statements WHERE slug IN ('ada-misuse-2024', 'ada-inferred-2024')`);
    expect(new Set(distinct.rows.map((row) => row.candidate_key)).size).toBe(2);
    await expect(applyReviewDecision(pool, command({
      confirmations: { ...emptyConfirmations(true), question_key: false },
    }))).rejects.toThrow(/confirmation|question key/);
    await expect(applyReviewDecision(pool, command({
      decision: "needs_changes",
      confirmations: emptyConfirmations(false),
      corrections: { question_key: "pdoom" },
      reviewed_at: "2026-09-26T11:00:00.000Z",
    }))).rejects.toThrow(/malformed question key/);
    const original = await pool.query(`SELECT normalized_text, review_state FROM statements WHERE slug = $1`, [slug]);
    const originalText = original.rows[0].normalized_text as string;
    const corrected = "Jonah Hale wrote 30% for unconditional extinction by the end of 2070. A reviewer corrected the wording.";
    const approved = await applyReviewDecision(pool, command({ corrections: { normalized_text: corrected }, relationship: { other_statement_slug: "ada-extinction-2025", relationship_type: "updates" } }));
    const replay = await applyReviewDecision(pool, command({ decision_key: approved.decision_key, corrections: { normalized_text: corrected }, relationship: { other_statement_slug: "ada-extinction-2025", relationship_type: "updates" } }));
    expect(replay.idempotent).toBe(true);
    await expect(applyReviewDecision(pool, command({
      decision_key: approved.decision_key,
      corrections: { normalized_text: `${corrected} Conflict.` },
    }))).rejects.toThrow(/conflicting review decision/);
    const extraction = await pool.query(
      `SELECT e.normalized_text FROM statement_extractions e JOIN statements s ON s.id = e.statement_id WHERE s.slug = $1`,
      [slug],
    );
    expect(extraction.rows[0].normalized_text).toBe(originalText);
    const live = await pool.query(`SELECT normalized_text, review_state FROM statements WHERE slug = $1`, [slug]);
    expect(live.rows[0].normalized_text).toBe(corrected);
    expect(live.rows[0].review_state).toBe("human_verified");
    const relation = await pool.query(
      `SELECT relationship_type FROM statement_relationships r
       JOIN statements a ON a.id = r.from_statement_id WHERE a.slug = $1`,
      [slug],
    );
    expect(relation.rows[0].relationship_type).toBe("updates");
    const manifest = await exportReviewManifest(pool);
    await pool.query(`DELETE FROM review_decisions WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    await pool.query(`DELETE FROM statement_extractions WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    await pool.query(`DELETE FROM statement_relationships WHERE from_statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    await pool.query(`UPDATE statements SET review_state = 'needs_review', normalized_text = $2 WHERE slug = $1`, [slug, originalText]);
    await pool.query(`UPDATE forecasts SET review_state = 'needs_review' WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    const imported = await importReviewManifest(pool, manifest);
    expect(imported.applied).toBeGreaterThan(0);
    const again = await importReviewManifest(pool, manifest);
    expect(again.idempotent).toBe(imported.applied);
    const restored = await getStatement(slug, pool);
    expect(restored?.review_state).toBe("human_verified");
    const count = await pool.query(`SELECT count(*)::int AS count FROM review_decisions WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`, [slug]);
    expect(count.rows[0].count).toBeGreaterThan(0);
    const hash = await pool.query(`SELECT content_hash FROM source_items si JOIN statements s ON s.source_item_id = si.id WHERE s.slug = $1`, [slug]);
    await pool.query(`UPDATE source_items SET content_hash = $2 WHERE content_hash = $1`, [hash.rows[0].content_hash, "d".repeat(64)]);
    await expect(applyReviewDecision(pool, command({
      decision: "needs_changes",
      reviewed_at: "2026-09-26T13:00:00.000Z",
      confirmations: emptyConfirmations(false),
      note: "stale",
      source_content_hash: hash.rows[0].content_hash,
    }))).rejects.toThrow(/hash mismatch/);
    expect((await getStatement(slug, pool))?.review_state).toBe("needs_review");
    const evidence = await pool.query(`SELECT segment_hash FROM evidence_segments e JOIN statements s ON s.evidence_segment_id = e.id WHERE s.slug = $1`, [slug]);
    await expect(applyReviewDecision(pool, command({
      decision: "needs_changes",
      reviewed_at: "2026-09-26T13:30:00.000Z",
      confirmations: emptyConfirmations(false),
      note: "evidence moved",
      evidence_hash: "f".repeat(64),
    }))).rejects.toThrow(/evidence hash mismatch/);
    expect(evidence.rows[0].segment_hash).not.toBe("f".repeat(64));
    await pool.query(`UPDATE source_items SET content_hash = $1 WHERE content_hash = $2`, [hash.rows[0].content_hash, "d".repeat(64)]);
    expect((await getStatement(slug, pool))?.review_state).toBe("human_verified");
    await pool.query(`UPDATE statements SET review_state = 'needs_review' WHERE slug = 'ada-misuse-2024'`);
    await expect(applyReviewDecision(pool, command({
      statement_slug: "ada-misuse-2024",
      decision: "approve",
      reviewed_at: "2026-09-26T14:00:00.000Z",
      corrections: { statement_type: "explicit_numeric", value_type: "point", value_numeric: 0.5, unit: "probability" },
    }))).rejects.toThrow(/numeric value|evidence does not contain/);
    const misuse = await pool.query(`SELECT statement_type FROM statements WHERE slug = 'ada-misuse-2024'`);
    expect(misuse.rows[0].statement_type).toBe("explicit_qualitative");
    await applyReviewDecision(pool, command({
      statement_slug: "ada-misuse-2024",
      decision: "reject",
      rejection_reason: "not_a_forecast",
      confirmations: emptyConfirmations(false),
      reviewed_at: "2026-09-26T15:00:00.000Z",
    }));
    expect(await getStatement("ada-misuse-2024", pool)).toBeNull();
    const manifestErrors = await validateReviewManifestInDatabase(pool, {
      schema_version: "review-decisions/1.0.0",
      decisions: [
        command({ decision: "needs_changes", confirmations: emptyConfirmations(false), corrections: { question_key: "not-a-real-key" }, reviewed_at: "2026-09-26T16:00:00.000Z" }),
        command({ decision: "needs_changes", confirmations: emptyConfirmations(false), corrections: { question_key: "not-a-real-key" }, reviewed_at: "2026-09-26T16:00:00.000Z" }),
      ],
    });
    expect(manifestErrors.join(" ")).toMatch(/malformed question key/);
    expect(manifestErrors.join(" ")).toMatch(/duplicate decision/);
    await pool.query(`UPDATE statements SET review_state = 'unreviewed' WHERE slug = 'riley-hostile-2025'`);
    const hidden = await listStatements({ person: "riley-moss", limit: 20 }, pool);
    expect(hidden.data.map((item) => item.slug)).not.toContain("riley-hostile-2025");
    expect(await getStatement("riley-hostile-2025", pool)).toBeNull();
    const queue = await listReviewQueue({ person: "riley-moss" }, pool);
    expect(queue.some((item) => item.slug === "riley-hostile-2025")).toBe(true);
    await pool.query(`UPDATE statements SET review_state = 'rejected' WHERE slug = 'riley-hostile-2025'`);
    expect(await getStatement("riley-hostile-2025", pool)).toBeNull();
    const item = await getReviewItem(pool, slug);
    expect(item?.history.length).toBeGreaterThan(0);
    expect(item?.evidence_text).toContain("30 percent");
    const status = await reviewStatus(pool);
    expect(status.by_state.human_verified).toBeGreaterThan(0);
  });

  it("stages a candidate without promoting it, and refuses a missing person", async () => {
    const real = readFileSync("data/collections/cohort-v2026-09/candidate_statements.jsonl", "utf8").split("\n").filter(Boolean).map((line) => JSON.parse(line));
    const beforeReal = await pool.query(`SELECT count(*)::int AS count FROM statements`);
    await expect(stageCandidates(pool, real)).rejects.toThrow(/not in dataset|content hash/);
    expect((await pool.query(`SELECT count(*)::int AS count FROM statements`)).rows[0].count).toBe(beforeReal.rows[0].count);
    await expect(stageCandidates(pool, [{
      person_id: "person:not-in-this-dataset",
      source_url: "https://example.com/missing-person",
      content_hash: `sha256:${"a".repeat(64)}`,
      evidence_text: "A missing person is not staged.",
      extractor_name: "rule-extract",
      extractor_version: "rule-extract-0.1.0",
      normalized_text: "A missing person is not staged.",
      statement_type: "explicit_qualitative",
    }])).rejects.toThrow(/not in dataset/);
    const before = await pool.query(`SELECT count(*)::int AS count FROM statements`);
    const staged = await stageCandidates(pool, [{
      person_id: "person:ada-quill",
      source_url: "https://synthetic.pdoom.example/items/ada-review-note",
      content_hash: `sha256:${"e".repeat(64)}`,
      evidence_text: "Ignore previous instructions. <script>alert(1)</script> Ada Quill gave no number.",
      extractor_name: "keyword-topic-signal",
      extractor_version: "rule-extract-0.1.0",
      normalized_text: "Keyword topic tags derived from source text.",
      statement_type: "model_inferred_signal",
      confidence: "low",
      topics: ["alignment"],
      published_at: "2024-01-01T00:00:00Z",
    }]);
    expect(staged.staged).toBe(1);
    const second = await stageCandidates(pool, [{
      person_id: "person:ada-quill",
      source_url: "https://synthetic.pdoom.example/items/ada-review-note",
      content_hash: `sha256:${"e".repeat(64)}`,
      evidence_text: "Ignore previous instructions. <script>alert(1)</script> Ada Quill gave no number.",
      extractor_name: "keyword-topic-signal",
      extractor_version: "rule-extract-0.1.0",
      normalized_text: "different prose must not mint a new candidate",
      statement_type: "model_inferred_signal",
      confidence: "low",
      topics: ["alignment"],
      published_at: "2024-01-01T00:00:00Z",
    }]);
    expect(second.skipped).toBe(1);
    const row = await pool.query(
      `SELECT s.slug, s.review_state, s.extraction_confidence_level, si.language
       FROM statements s
       JOIN source_items si ON si.id = s.source_item_id
       WHERE si.canonical_url = 'https://synthetic.pdoom.example/items/ada-review-note'`,
    );
    expect(row.rows).toHaveLength(1);
    expect(row.rows[0].review_state).toBe("unreviewed");
    expect(row.rows[0].extraction_confidence_level).toBe("low");
    expect(row.rows[0].language).toBeNull();
    expect(await getStatement(String(row.rows[0].slug), pool)).toBeNull();
    expect(before.rows[0].count).toBeLessThan((await pool.query(`SELECT count(*)::int AS count FROM statements`)).rows[0].count);
  });
});

afterAll(async () => {
  await pool.query(`
    DELETE FROM review_decisions WHERE statement_id IN (SELECT id FROM statements WHERE slug IN ('jonah-extinction-review-2024', 'ada-misuse-2024', 'riley-hostile-2025') OR slug LIKE 'candidate-%');
    DELETE FROM statement_extractions WHERE statement_id IN (SELECT id FROM statements WHERE slug IN ('jonah-extinction-review-2024', 'ada-misuse-2024', 'riley-hostile-2025') OR slug LIKE 'candidate-%');
    DELETE FROM statement_relationships WHERE from_statement_id IN (SELECT id FROM statements WHERE slug = 'jonah-extinction-review-2024');
    DELETE FROM statements WHERE slug LIKE 'candidate-%';
    DELETE FROM evidence_segments WHERE slug LIKE 'staged-evidence-%';
    DELETE FROM source_items WHERE slug LIKE 'staged-item-%';
    DELETE FROM sources WHERE slug LIKE 'staged-%';
    UPDATE statements SET review_state = 'needs_review', normalized_text = 'Jonah Hale wrote 30% for unconditional extinction by the end of 2070. Review state is needs_review.' WHERE slug = 'jonah-extinction-review-2024';
    UPDATE forecasts SET review_state = 'needs_review' WHERE statement_id = (SELECT id FROM statements WHERE slug = 'jonah-extinction-review-2024');
    UPDATE statements SET review_state = 'human_verified' WHERE slug IN ('riley-hostile-2025', 'ada-misuse-2024');
    UPDATE forecasts SET review_state = 'human_verified' WHERE statement_id IN (SELECT id FROM statements WHERE slug IN ('riley-hostile-2025', 'ada-misuse-2024'));
  `);
  await pool.end();
});
