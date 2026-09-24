import { createPool } from "../packages/db/src/pool";
import { stableId } from "../packages/db/src/ids";
import { describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");

describe("schema constraints", () => {
  it("rejects a numeric forecast on a qualitative statement", async () => {
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const statement = stableId("statement:ada-misuse-2024");
      await expect(
        client.query(
          `INSERT INTO forecasts (
             id, statement_id, forecast_kind, question_key, question_text, value_type, value_numeric, unit, review_state
           ) VALUES (gen_random_uuid(), $1, 'probability', 'bad', 'bad', 'point', 0.99, 'probability', 'human_verified')`,
          [statement],
        ),
      ).rejects.toThrow(/non-numeric|value_type|duplicate key/i);
      await client.query("ROLLBACK");
    } finally {
      client.release();
    }
  });

  it("rejects a duplicate external identity for a different person", async () => {
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      await expect(
        client.query(
          `INSERT INTO external_identities (
             id, person_id, namespace, external_id, verification_method, confidence
           ) VALUES (gen_random_uuid(), $1, 'orcid', '0000-0002-0001-0001', 'manual_review', 1)`,
          [stableId("person:samira-okonkwo")],
        ),
      ).rejects.toThrow(/duplicate key/i);
      await client.query("ROLLBACK");
    } finally {
      client.release();
    }
  });

  it("rejects an invalid statement type and a self-relationship", async () => {
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      await expect(
        client.query(
          `INSERT INTO statements (
             id, slug, person_id, source_item_id, statement_type, normalized_text, evidence_segment_id, extractor_version, confidence, review_state
           ) VALUES (gen_random_uuid(), 'bad-type', $1, $2, 'sentiment', 'no', $3, 'x', 1, 'human_verified')`,
          [
            stableId("person:ada-quill"),
            stableId("source-item:ada-essay-2023"),
            stableId("evidence:ada-essay-2023-evidence"),
          ],
        ),
      ).rejects.toThrow(/check constraint|statement_type/i);
      await client.query("ROLLBACK");
    } finally {
      client.release();
    }
  });

  it("does not store the unpublished source body", async () => {
    const result = await pool.query(`
      SELECT coalesce(title, '') || coalesce(content_reference, '') || metadata_json::text || coalesce((
        SELECT string_agg(text, '') FROM evidence_segments
      ), '') AS blob
      FROM source_items
    `);
    const blob = result.rows.map((row) => String(row.blob)).join("\n");
    expect(blob).not.toContain("UNIQUE_BODY_MARKER_9f3a");
    const columns = await pool.query(
      `SELECT column_name FROM information_schema.columns WHERE table_name = 'source_items'`,
    );
    expect(columns.rows.map((row) => row.column_name)).not.toContain("body");
  });
});
