import { createPool } from "../packages/db/src/pool";
import { stableId } from "../packages/db/src/ids";
import { getOverview, getPerson, getTrend, listPeople, listStatements, listTopics, searchAll } from "../packages/db/src/queries";
import { afterAll, describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");
const PEOPLE = 400;
const SOURCES = 1200;
const ITEMS = 3000;

async function seedScale() {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query(
      `INSERT INTO organizations (id, slug, name, organization_type)
       VALUES ($1, 'scale-org', 'Scale Org', 'research_lab')
       ON CONFLICT (slug) DO NOTHING`,
      [stableId("organization:scale-org")],
    );
    await client.query(
      `INSERT INTO people (id, slug, display_name, bio_short, inclusion_reason, status)
       SELECT
         ('00000000-0000-5000-8000-' || lpad(to_hex(n), 12, '0'))::uuid,
         'scale-person-' || n,
         'Scale Person ' || n,
         'Scale bio ' || n,
         'scale coverage check',
         'active'
       FROM generate_series(1, $1) AS n
       ON CONFLICT (slug) DO NOTHING`,
      [PEOPLE],
    );
    await client.query(
      `INSERT INTO sources (id, slug, source_type, name, canonical_url, collection_method, owner_person_id, review_state, last_success_at)
       SELECT
         ('10000000-0000-5000-8000-' || lpad(to_hex(n), 12, '0'))::uuid,
         'scale-source-' || n,
         CASE WHEN n % 5 = 0 THEN 'blog' ELSE 'academic_works' END,
         'Scale source ' || n,
         'https://synthetic.pdoom.example/scale/' || n,
         'api',
         (SELECT id FROM people WHERE slug = 'scale-person-' || ((n % $2) + 1)),
         'machine_validated',
         CASE WHEN n % 17 = 0 THEN NULL ELSE now() - ((n % 120) || ' days')::interval END
       FROM generate_series(1, $1) AS n
       ON CONFLICT (slug) DO NOTHING`,
      [SOURCES, PEOPLE],
    );
    await client.query(
      `INSERT INTO source_items (
         id, slug, source_id, logical_key, canonical_url, title, observed_at, content_hash, content_version, collection_status, availability
       )
       SELECT
         ('20000000-0000-5000-8000-' || lpad(to_hex(n), 12, '0'))::uuid,
         'scale-item-' || n,
         (SELECT id FROM sources WHERE slug = 'scale-source-' || ((n % $2) + 1)),
         'scale-item-' || n,
         'https://synthetic.pdoom.example/scale/items/' || n,
         'Scale item ' || n,
         now(),
         repeat(substr(md5(n::text), 1, 32), 2),
         1,
         'collected',
         'available'
       FROM generate_series(1, $1) AS n
       ON CONFLICT (slug) DO NOTHING`,
      [ITEMS, SOURCES],
    );
    await client.query(
      `INSERT INTO evidence_segments (id, slug, source_item_id, segment_kind, sequence, text, segment_hash)
       SELECT
         ('30000000-0000-5000-8000-' || lpad(to_hex(n), 12, '0'))::uuid,
         'scale-evidence-' || n,
         (SELECT id FROM source_items WHERE slug = 'scale-item-' || n),
         'text',
         1,
         'Scale excerpt ' || n,
         repeat('b', 64)
       FROM generate_series(1, $1) AS n
       ON CONFLICT (slug) DO NOTHING`,
      [ITEMS],
    );
    await client.query(
      `INSERT INTO statements (
         id, slug, person_id, source_item_id, statement_type, normalized_text, evidence_segment_id,
         extractor_name, extractor_version, confidence, review_state
       )
       SELECT
         ('40000000-0000-5000-8000-' || lpad(to_hex(n), 12, '0'))::uuid,
         'scale-statement-' || n,
         (SELECT id FROM people WHERE slug = 'scale-person-' || ((n % $2) + 1)),
         (SELECT id FROM source_items WHERE slug = 'scale-item-' || n),
         'explicit_qualitative',
         'Scale statement ' || n,
         (SELECT id FROM evidence_segments WHERE slug = 'scale-evidence-' || n),
         'scale',
         'scale',
         0.5,
         'human_verified'
       FROM generate_series(1, $1) AS n
       ON CONFLICT (slug) DO NOTHING`,
      [ITEMS, PEOPLE],
    );
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

async function timed<T>(label: string, fn: () => Promise<T>): Promise<T> {
  const started = Date.now();
  const value = await fn();
  const elapsed = Date.now() - started;
  expect(elapsed, label).toBeLessThan(2000);
  return value;
}

describe("scaled query behavior", () => {
  it("answers overview, lists, detail, search, topics, and trends without a full scan per row", async () => {
    await seedScale();
    const overview = await timed("overview", () => getOverview(pool));
    expect(overview.dataset.person_count).toBeGreaterThan(PEOPLE);
    const people = await timed("people", () => listPeople({ limit: 20 }, pool));
    expect(people.data).toHaveLength(20);
    const person = await timed("person", () => getPerson("scale-person-1", pool));
    expect(person?.sources.length).toBeGreaterThan(0);
    const statements = await timed("statements", () => listStatements({ limit: 20, q: "Scale statement 12" }, pool));
    expect(statements.data.length).toBeGreaterThan(0);
    expect(JSON.stringify(statements.data)).not.toContain("content_hash_input");
    await timed("search", () => searchAll("Scale Person 3", pool));
    await timed("topics", () => listTopics(pool));
    await timed("trend", () => getTrend("extinction-by-2070-distribution", pool));
  });
});

afterAll(async () => {
  await pool.query(`
    DELETE FROM statements WHERE slug LIKE 'scale-statement-%';
    DELETE FROM evidence_segments WHERE slug LIKE 'scale-evidence-%';
    DELETE FROM source_items WHERE slug LIKE 'scale-item-%';
    DELETE FROM sources WHERE slug LIKE 'scale-source-%';
    DELETE FROM people WHERE slug LIKE 'scale-person-%';
    DELETE FROM organizations WHERE slug = 'scale-org';
  `);
  await pool.end();
});
