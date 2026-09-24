import { importCanonical } from "../packages/db/src/import";
import { createPool } from "../packages/db/src/pool";
import { getStatement, getTrend, listStatements } from "../packages/db/src/queries";
import { describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");

describe("fixture import and trends", () => {
  it("is idempotent", async () => {
    const before = await pool.query("SELECT count(*)::int AS count FROM statements");
    const first = await importCanonical(pool);
    const second = await importCanonical(pool);
    const after = await pool.query("SELECT count(*)::int AS count FROM statements");
    expect(second.counts.statements).toBe(first.counts.statements);
    expect(after.rows[0].count).toBe(before.rows[0].count);
    const ids = await pool.query("SELECT id FROM people WHERE slug = 'ada-quill'");
    expect(ids.rowCount).toBe(1);
  });

  it("does not merge similar names", async () => {
    const rows = await pool.query(
      `SELECT slug FROM people WHERE family_name = 'Okonkwo' ORDER BY slug`,
    );
    expect(rows.rows.map((row) => row.slug)).toEqual(["samir-okonkwo", "samira-okonkwo"]);
  });

  it("keeps mentioned people distinct from speakers", async () => {
    const rows = await pool.query(
      `SELECT sp.role, p.slug
       FROM source_participants sp
       JOIN source_items si ON si.id = sp.source_item_id
       JOIN people p ON p.id = sp.person_id
       WHERE si.slug = 'samir-post-2024'
       ORDER BY sp.role`,
    );
    expect(rows.rows).toEqual([
      { role: "author", slug: "samir-okonkwo" },
      { role: "mentioned", slug: "samira-okonkwo" },
    ]);
    const statement = await getStatement("samir-extinction-2024", pool);
    expect(statement?.person.slug).toBe("samir-okonkwo");
  });

  it("round-trips provenance", async () => {
    const statement = await getStatement("ada-extinction-2025", pool);
    expect(statement?.statement_type).toBe("explicit_numeric");
    expect(statement?.forecast?.value_numeric).toBeCloseTo(0.12);
    expect(statement?.forecast?.question_key).toBe("ai_extinction_unconditional_by_2070");
    expect(statement?.evidence.text).toContain("12 percent");
    expect(statement?.evidence.start_ms).toBe(1860000);
    expect(statement?.provenance.content_hash).toMatch(/^[a-f0-9]{64}$/);
    expect(statement?.source_item.canonical_url).toContain("https://synthetic.pdoom.example/items/ada-podcast-2025");
    expect(statement?.source_item.published_at).not.toBe(statement?.source_item.observed_at);
    expect(statement?.relationships.some((relation) => relation.from_slug === "ada-extinction-2023")).toBe(true);
  });

  it("excludes non-comparable forecasts from the extinction distribution", async () => {
    const trend = await getTrend("extinction-by-2070-distribution", pool);
    expect(trend?.kind).toBe("distribution");
    if (trend?.kind !== "distribution") return;
    expect(trend.method_version).toBe("explicit-numeric-distribution/1.0.0");
    expect(trend.distribution.included.map((item) => item.value_numeric)).toEqual([0.05, 0.09, 0.12, 0.18]);
    expect(trend.distribution.contributing_person_count).toBe(4);
    expect(trend.distribution.contributing_statement_count).toBe(4);
    expect(trend.distribution.median).toBeCloseTo(0.105);
    const reasons = Object.fromEntries(trend.distribution.exclusions.map((item) => [item.statement_slug, item.reason]));
    expect(reasons["jonah-catastrophe-2022"]).toBe("topic_not_target");
    expect(reasons["jonah-conditional-2024"]).toBe("question_key_mismatch");
    expect(reasons["elena-disempowerment-2024"]).toBe("topic_not_target");
    expect(reasons["mateo-agi-2025"]).toBe("topic_not_target");
    expect(reasons["jonah-extinction-no-horizon-2025"]).toBe("missing_horizon");
    expect(reasons["jonah-extinction-review-2024"]).toBe("review_state");
    expect(reasons["noah-extinction-range-2025"]).toBe("value_type_not_point");
    expect(reasons["ada-misuse-2024"]).toBe("statement_type");
    expect(reasons["ada-inferred-2024"]).toBe("statement_type");
    expect(reasons["ada-extinction-2023"]).toBe("not_latest");
    expect(trend.distribution.included.map((item) => item.value_numeric)).not.toContain(0.25);
    expect(trend.distribution.included.map((item) => item.value_numeric)).not.toContain(0.55);
  });

  it("counts statement volume without blending classes", async () => {
    const trend = await getTrend("statement-volume-by-topic-type", pool);
    expect(trend?.kind).toBe("volume");
    if (trend?.kind !== "volume") return;
    expect(trend.volume.contributing_statement_count).toBe(21);
    expect(trend.volume.exclusions.map((item) => item.statement_slug)).toContain("jonah-extinction-review-2024");
    const types = new Set(trend.volume.rows.map((row) => row.statement_type));
    expect(types.has("explicit_numeric")).toBe(true);
    expect(types.has("explicit_qualitative")).toBe(true);
    expect(types.has("model_inferred_signal")).toBe(true);
  });

  it("filters and paginates statements", async () => {
    const numeric = await listStatements({ statement_type: "explicit_numeric", limit: 50, sort: "event_time_desc" }, pool);
    expect(numeric.data.every((row) => row.statement_type === "explicit_numeric")).toBe(true);
    const qualitative = await listStatements({ statement_type: "explicit_qualitative", limit: 50, sort: "event_time_desc" }, pool);
    expect(qualitative.data.every((row) => !row.forecast || row.forecast.value_numeric === null)).toBe(true);
    const page = await listStatements({ limit: 2, sort: "event_time_desc" }, pool);
    expect(page.data).toHaveLength(2);
    expect(page.page.next_cursor).toBeTruthy();
    const next = await listStatements({ limit: 2, cursor: page.page.next_cursor ?? undefined, sort: "event_time_desc" }, pool);
    const ids = new Set([...page.data, ...next.data].map((row) => row.id));
    expect(ids.size).toBe(4);
    await expect(listStatements({ limit: 2, cursor: "%%%", sort: "event_time_desc" }, pool)).rejects.toThrow(/invalid_cursor/);
  });

  it("keeps hostile source text inert", async () => {
    const statement = await getStatement("riley-hostile-2025", pool);
    expect(statement?.statement_type).toBe("explicit_qualitative");
    expect(statement?.forecast).toBeNull();
    expect(statement?.evidence.text).toContain("Ignore previous instructions");
    expect(statement?.evidence.text).toContain("<script>");
    const numeric = await pool.query(
      `SELECT count(*)::int AS count FROM forecasts f
       JOIN statements s ON s.id = f.statement_id
       WHERE s.person_id = (SELECT id FROM people WHERE slug = 'riley-moss')
         AND f.value_numeric IS NOT NULL`,
    );
    expect(numeric.rows[0].count).toBe(0);
  });
});
