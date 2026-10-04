import { writeFile } from "node:fs/promises";
import { createPool } from "../packages/db/src/pool";
import { stableId } from "../packages/db/src/ids";
import { effectiveReviewStateSql } from "../packages/db/src/coverage";
import { getOverview, getPerson, getTrend, listPeople, listStatements, listTopics } from "../packages/db/src/queries";
import { getPublicPerson, listPublicStatements } from "../packages/db/src/public-read";
import { searchPublic } from "../packages/db/src/search";
import type { PublicTrend } from "../packages/db/src/trend-query";
import { counterSnapshot, resetMetrics } from "@pdoom/observability";
import { afterAll, describe, expect, it } from "vitest";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");
const PEOPLE = 400;
const SOURCES = 1200;
const ITEMS = 3000;
const REPORT_PATH = "/tmp/pdoom-public-read-scale.json";

function dbQueries() {
  return counterSnapshot()
    .filter((row) => row.name === "pdoom_db_queries_total")
    .reduce((sum, row) => sum + row.value, 0);
}

function distribution(samples: number[]) {
  const sorted = [...samples].sort((left, right) => left - right);
  const at = (percentile: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.ceil((percentile / 100) * sorted.length) - 1))] ?? 0;
  return { min: sorted[0] ?? 0, p50: at(50), p95: at(95), max: sorted[sorted.length - 1] ?? 0, n: sorted.length };
}

async function measure<T>(label: string, fn: () => Promise<T>) {
  const before = dbQueries();
  const heapBefore = process.memoryUsage();
  const started = performance.now();
  const value = await fn();
  const ms = performance.now() - started;
  return {
    label,
    ms: Math.round(ms * 10) / 10,
    queries: dbQueries() - before,
    bytes: Buffer.byteLength(JSON.stringify(value)),
    heap_delta: process.memoryUsage().heapUsed - heapBefore.heapUsed,
    rss: process.memoryUsage().rss,
    value,
  };
}

function exclusions(trend: PublicTrend) {
  if (trend.kind === "volume") return trend.volume.exclusions;
  if (trend.kind === "distribution") return trend.distribution.exclusions;
  if (trend.kind === "timeline") return trend.timeline.exclusions;
  if (trend.kind === "quantity") return trend.quantity.exclusions;
  return trend.revision.exclusions;
}

async function cleanupScale() {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query("SET LOCAL statement_timeout = '120s'");
    await client.query(`DELETE FROM review_decisions WHERE decision_key LIKE 'scale-stale-%'`);
    await client.query(
      `DELETE FROM statement_relationships r
       USING statements s
       WHERE s.slug LIKE 'scale-statement-%'
         AND (r.from_statement_id = s.id OR r.to_statement_id = s.id)`,
    );
    await client.query(
      `DELETE FROM forecasts f
       USING statements s
       WHERE s.slug LIKE 'scale-statement-%' AND f.statement_id = s.id`,
    );
    await client.query(
      `DELETE FROM cohort_memberships cm
       USING people p
       WHERE p.slug LIKE 'scale-person-%' AND cm.person_id = p.id`,
    );
    await client.query(`DELETE FROM statements WHERE slug LIKE 'scale-statement-%'`);
    await client.query(`DELETE FROM evidence_segments WHERE slug LIKE 'scale-evidence-%'`);
    await client.query(`DELETE FROM source_items WHERE slug LIKE 'scale-item-%'`);
    await client.query(`DELETE FROM sources WHERE slug LIKE 'scale-source-%'`);
    await client.query(`DELETE FROM people WHERE slug LIKE 'scale-person-%'`);
    await client.query(`DELETE FROM organizations WHERE slug = 'scale-org'`);
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

async function seedScale() {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query("SET LOCAL statement_timeout = '120s'");
    await client.query(`DELETE FROM review_decisions WHERE decision_key LIKE 'scale-stale-%'`);
    await client.query(
      `DELETE FROM statement_relationships r
       USING statements s
       WHERE s.slug LIKE 'scale-statement-%'
         AND (r.from_statement_id = s.id OR r.to_statement_id = s.id)`,
    );
    await client.query(
      `DELETE FROM forecasts f
       USING statements s
       WHERE s.slug LIKE 'scale-statement-%' AND f.statement_id = s.id`,
    );
    await client.query(
      `DELETE FROM cohort_memberships cm
       USING people p
       WHERE p.slug LIKE 'scale-person-%' AND cm.person_id = p.id`,
    );
    await client.query(`DELETE FROM statements WHERE slug LIKE 'scale-statement-%'`);
    await client.query(`DELETE FROM evidence_segments WHERE slug LIKE 'scale-evidence-%'`);
    await client.query(`DELETE FROM source_items WHERE slug LIKE 'scale-item-%'`);
    await client.query(`DELETE FROM sources WHERE slug LIKE 'scale-source-%'`);
    await client.query(`DELETE FROM people WHERE slug LIKE 'scale-person-%'`);
    await client.query(`DELETE FROM organizations WHERE slug = 'scale-org'`);
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
         extractor_name, extractor_version, confidence, review_state, event_time
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
         'human_verified',
         CASE
           WHEN n % 17 = 0 THEN NULL
           ELSE timestamptz '2024-01-01T00:00:00Z' + ((n % 11) || ' hours')::interval
         END
       FROM generate_series(1, $1) AS n
       ON CONFLICT (slug) DO NOTHING`,
      [ITEMS, PEOPLE],
    );
    await client.query(
      `UPDATE people
       SET status = 'review'
       WHERE slug LIKE 'scale-person-%'
         AND substring(slug FROM '([0-9]+)$')::int % 20 = 0`,
    );
    await client.query(
      `UPDATE statements AS s
       SET review_state = 'unreviewed', statement_type = 'explicit_qualitative'
       FROM people AS p
       WHERE s.person_id = p.id
         AND p.slug LIKE 'scale-person-%'
         AND p.status = 'review'
         AND s.slug LIKE 'scale-statement-%'`,
    );
    await client.query(
      `UPDATE statements AS s
       SET statement_type = 'explicit_numeric',
           candidate_key = 'scale-candidate-' || n.n,
           review_state = CASE
             WHEN n.n % 50 = 3 THEN 'needs_review'
             WHEN n.n % 50 = 4 THEN 'rejected'
             ELSE s.review_state
           END
       FROM generate_series(1, $1) AS n(n)
       WHERE s.slug = 'scale-statement-' || n.n
         AND s.review_state = 'human_verified'
         AND n.n % 50 BETWEEN 0 AND 6`,
      [ITEMS],
    );
    await client.query(
      `INSERT INTO forecasts (
         id, statement_id, forecast_kind, question_key, question_text, definition_text,
         condition_text, horizon_text, value_type, value_numeric, value_min, value_max, unit, review_state
       )
       SELECT
         ('70000000-0000-5000-8000-' || lpad(to_hex(n.n), 12, '0'))::uuid,
         s.id,
         CASE WHEN n.n % 50 = 2 THEN 'quantity' ELSE 'probability' END,
         CASE
           WHEN n.n % 50 = 1 THEN 'ai_extinction_conditional_on_agi'
           WHEN n.n % 50 = 2 THEN 'gdp_growth_pp_by_2035'
           ELSE 'ai_extinction_unconditional_by_2070'
         END,
         CASE
           WHEN n.n % 50 = 1 THEN 'Probability of human extinction from AI, conditional on AGI being built.'
           WHEN n.n % 50 = 2 THEN 'Annual GDP growth by 2035, in percentage points.'
           ELSE 'Unconditional probability of literal human extinction caused by advanced AI by the end of 2070.'
         END,
         'Scale fixture forecast. It is not a sourced claim.',
         CASE WHEN n.n % 50 = 1 THEN 'conditional on AGI being built' ELSE NULL END,
         CASE WHEN n.n % 50 = 2 THEN 'by 2035' ELSE 'by 2070' END,
         CASE WHEN n.n % 50 IN (2, 6) THEN 'range' ELSE 'point' END,
         CASE WHEN n.n % 50 IN (2, 6) THEN NULL ELSE ((n.n % 97)::numeric / 100) END,
         CASE WHEN n.n % 50 = 2 THEN 1 WHEN n.n % 50 = 6 THEN 0.10 ELSE NULL END,
         CASE WHEN n.n % 50 = 2 THEN 3 WHEN n.n % 50 = 6 THEN 0.40 ELSE NULL END,
         CASE WHEN n.n % 50 = 2 THEN 'percentage_points' ELSE 'probability' END,
         s.review_state
       FROM generate_series(1, $1) AS n(n)
       JOIN statements s ON s.slug = 'scale-statement-' || n.n
       WHERE s.statement_type = 'explicit_numeric'`,
      [ITEMS],
    );
    await client.query(
      `INSERT INTO review_decisions (
         id, decision_key, statement_id, candidate_key, decision, previous_review_state,
         resulting_review_state, reviewed_at, reviewer, source_item_id, evidence_segment_id,
         source_content_hash, evidence_hash, content_version, corrections_json, original_extraction_json
       )
       SELECT
         ('50000000-0000-5000-8000-' || lpad(to_hex(n.n), 12, '0'))::uuid,
         'scale-stale-' || n.n,
         s.id,
         s.candidate_key,
         'approve',
         'needs_review',
         'human_verified',
         timestamptz '2026-01-01T00:00:00Z',
         'scale',
         s.source_item_id,
         s.evidence_segment_id,
         repeat('c', 64),
         repeat('b', 64),
         1,
         '{}'::jsonb,
         '{}'::jsonb
       FROM generate_series(1, $1) AS n(n)
       JOIN statements s ON s.slug = 'scale-statement-' || n.n
       WHERE n.n % 50 = 5
         AND s.statement_type = 'explicit_numeric'`,
      [ITEMS],
    );
    await client.query(
      `INSERT INTO statement_relationships (
         id, from_statement_id, to_statement_id, relationship_type, method, confidence, review_state
       )
       SELECT
         ('60000000-0000-5000-8000-' || lpad(to_hex(n.n), 12, '0'))::uuid,
         fs.id,
         ts.id,
         CASE WHEN n.n % 800 = 0 THEN 'retracts' ELSE 'updates' END,
         'scale',
         1,
         'human_verified'
       FROM generate_series(1, $1) AS n(n)
       JOIN statements fs ON fs.slug = 'scale-statement-' || n.n
       JOIN statements ts ON ts.slug = 'scale-statement-' || (n.n - 400)
       WHERE n.n % 400 = 0
         AND n.n > 400
         AND fs.statement_type = 'explicit_numeric'
         AND ts.statement_type = 'explicit_numeric'`,
      [ITEMS],
    );
    const membership = await client.query(
      `INSERT INTO cohort_memberships (cohort_id, person_id, inclusion_reason)
       SELECT c.id, p.id, 'scale coverage check'
       FROM people p
       JOIN cohorts c ON (c.slug, c.version) = (
         SELECT cohort_slug, cohort_version
         FROM dataset_imports
         WHERE is_current
         ORDER BY imported_at DESC
         LIMIT 1
       )
       WHERE p.slug LIKE 'scale-person-%'
       ON CONFLICT DO NOTHING`,
    );
    if (membership.rowCount !== PEOPLE) {
      throw new Error(`scale cohort membership inserted ${membership.rowCount}, expected ${PEOPLE}`);
    }
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

describe("scaled query behavior", () => {
  it("measures a cohort that includes the extra people, forecasts, and review exclusions", async () => {
    await seedScale();
    const version = await pool.query(`SELECT version() AS version, current_setting('server_version') AS server_version`);
    const fixture = await pool.query(
      `SELECT
         (SELECT count(*)::int FROM people WHERE slug LIKE 'scale-person-%') AS people,
         (SELECT count(*)::int FROM people WHERE slug LIKE 'scale-person-%' AND status = 'review') AS private_people,
         (SELECT count(*)::int FROM sources WHERE slug LIKE 'scale-source-%') AS sources,
         (SELECT count(*)::int FROM statements WHERE slug LIKE 'scale-statement-%') AS statements,
         (SELECT count(*)::int FROM forecasts f JOIN statements s ON s.id = f.statement_id WHERE s.slug LIKE 'scale-statement-%') AS forecasts,
         (SELECT count(*)::int FROM forecasts f JOIN statements s ON s.id = f.statement_id
            WHERE s.slug LIKE 'scale-statement-%' AND f.question_key = 'ai_extinction_unconditional_by_2070' AND f.value_type = 'point' AND s.review_state = 'human_verified') AS extinction_points,
         (SELECT count(*)::int FROM forecasts f JOIN statements s ON s.id = f.statement_id
            WHERE s.slug LIKE 'scale-statement-%' AND f.question_key = 'ai_extinction_conditional_on_agi') AS conditional_forecasts,
         (SELECT count(*)::int FROM forecasts f JOIN statements s ON s.id = f.statement_id
            WHERE s.slug LIKE 'scale-statement-%' AND f.question_key = 'gdp_growth_pp_by_2035' AND f.value_type = 'range') AS gdp_ranges,
         (SELECT count(*)::int FROM forecasts f JOIN statements s ON s.id = f.statement_id
            WHERE s.slug LIKE 'scale-statement-%' AND f.question_key = 'ai_extinction_unconditional_by_2070' AND f.value_type = 'range') AS extinction_ranges,
         (SELECT count(*)::int FROM statements WHERE slug LIKE 'scale-statement-%' AND review_state = 'needs_review') AS needs_review,
         (SELECT count(*)::int FROM statements WHERE slug LIKE 'scale-statement-%' AND review_state = 'rejected') AS rejected,
         (SELECT count(*)::int FROM review_decisions WHERE decision_key LIKE 'scale-stale-%') AS stale_reviews,
         (SELECT count(*)::int FROM statement_relationships r JOIN statements s ON s.id = r.from_statement_id WHERE s.slug LIKE 'scale-statement-%') AS revisions,
         (SELECT count(*)::int FROM cohort_memberships cm JOIN people p ON p.id = cm.person_id WHERE p.slug LIKE 'scale-person-%') AS memberships`,
    );
    const counts = fixture.rows[0];
    expect(counts.people).toBe(PEOPLE);
    expect(counts.memberships).toBe(PEOPLE);
    expect(counts.private_people).toBeGreaterThan(0);
    expect(counts.extinction_points).toBeGreaterThan(0);
    expect(counts.conditional_forecasts).toBeGreaterThan(0);
    expect(counts.gdp_ranges).toBeGreaterThan(0);
    expect(counts.extinction_ranges).toBeGreaterThan(0);
    expect(counts.needs_review).toBeGreaterThan(0);
    expect(counts.rejected).toBeGreaterThan(0);
    expect(counts.stale_reviews).toBeGreaterThan(0);
    expect(counts.revisions).toBeGreaterThan(0);
    const stale = await pool.query(
      `SELECT ${effectiveReviewStateSql("s")} AS review_state
       FROM statements s
       WHERE s.slug = 'scale-statement-5'`,
    );
    expect(stale.rows[0].review_state).toBe("needs_review");
    const hidden = await getPublicPerson("scale-person-20", pool);
    expect(hidden).toBeNull();
    const member = await getPublicPerson("scale-person-1", pool);
    expect(member?.in_current_cohort).toBe(true);

    resetMetrics();
    const samples = [];
    const personCold = await measure("person-cold", () => getPerson("scale-person-1", pool));
    samples.push(personCold);
    expect(personCold.value?.sources.length).toBeGreaterThan(0);
    expect(personCold.ms).toBeLessThan(2000);
    expect(personCold.queries).toBeLessThan(15);
    const personHot = await measure("person-hot", () => getPerson("scale-person-1", pool));
    samples.push(personHot);
    expect(personHot.ms).toBeLessThan(2000);

    const peopleCold = await measure("people-cold", () => listPeople({ limit: 20 }, pool));
    samples.push(peopleCold);
    expect(peopleCold.value.data).toHaveLength(20);
    expect(peopleCold.ms).toBeLessThan(2000);
    const peopleHot = await measure("people-hot", () => listPeople({ limit: 20 }, pool));
    samples.push(peopleHot);
    expect(peopleHot.ms).toBeLessThan(2000);

    const statementsCold = await measure("statements-cold", () => listStatements({ limit: 20, q: "Scale statement 12" }, pool));
    samples.push(statementsCold);
    expect(statementsCold.value.data.length).toBeGreaterThan(0);
    expect(JSON.stringify(statementsCold.value.data)).not.toContain("content_hash_input");
    expect(statementsCold.ms).toBeLessThan(2000);
    const statementsHot = await measure("statements-hot", () => listStatements({ limit: 20, q: "Scale statement 12" }, pool));
    samples.push(statementsHot);
    expect(statementsHot.ms).toBeLessThan(2000);

    const walked = await listPublicStatements({ person: "scale-person-1", limit: 50, sort: "event_time_desc" }, pool);
    const again = await listPublicStatements({ person: "scale-person-1", limit: 50, sort: "event_time_desc" }, pool);
    expect(again.data.map((row) => row.slug)).toEqual(walked.data.map((row) => row.slug));
    for (let index = 1; index < walked.data.length; index += 1) {
      const previous = walked.data[index - 1];
      const current = walked.data[index];
      if (!previous || !current) continue;
      if (previous.event_time === null) expect(current.event_time).toBeNull();
      else if (current.event_time && previous.event_time === current.event_time) expect(previous.slug > current.slug).toBe(true);
    }

    const searchSamples: Array<[string, () => Promise<unknown>]> = [
      ["search-person", () => searchPublic({ q: "Scale Person 3", limit: 5 }, pool)],
      ["search-statement", () => searchPublic({ q: "Scale statement 12", type: "statement", limit: 5 }, pool)],
      ["search-title", () => searchPublic({ q: "Scale item 12", type: "source_item", limit: 5 }, pool)],
      ["search-broad", () => searchPublic({ q: "Scale", limit: 8 }, pool)],
    ];
    for (const [label, fn] of searchSamples) {
      const sample = await measure(label, fn);
      samples.push(sample);
      expect(sample.ms, label).toBeLessThan(label === "search-broad" ? 2000 : 500);
      if (label === "search-person") {
        const person = sample.value as Awaited<ReturnType<typeof searchPublic>>;
        expect(person.groups.person.data[0]?.slug).toBe("scale-person-3");
        expect(person.groups.person.data[0]?.match).toBe("exact_name");
      }
      if (label === "search-statement") {
        const statement = sample.value as Awaited<ReturnType<typeof searchPublic>>;
        expect(statement.groups.statement.data[0]?.slug).toBe("scale-statement-12");
        expect(statement.groups.statement.data[0]?.match).toBe("exact_text");
      }
      if (label === "search-title") {
        const title = sample.value as Awaited<ReturnType<typeof searchPublic>>;
        expect(title.groups.source_item.data[0]?.slug).toBe("scale-item-12");
      }
      const hot = await measure(`${label}-hot`, fn);
      samples.push(hot);
    }

    const topics = await measure("topics", () => listTopics(pool));
    samples.push(topics);
    expect(topics.ms).toBeLessThan(2000);

    const trendCold = await measure("trend-cold", () => getTrend("extinction-by-2070-distribution", pool));
    samples.push(trendCold);
    const trendHot = await measure("trend-hot", () => getTrend("extinction-by-2070-distribution", pool));
    samples.push(trendHot);
    const extinction = trendCold.value;
    expect(extinction?.cohort_size).toBeGreaterThanOrEqual(PEOPLE);
    expect(extinction && exclusions(extinction).some((item) => item.reason === "value_type_not_point" && item.statement_slug.startsWith("scale-"))).toBe(true);
    expect(extinction && exclusions(extinction).some((item) => item.reason === "review_state" && item.statement_slug.startsWith("scale-"))).toBe(true);
    expect(extinction?.contributing_statement_count).toBeGreaterThan(0);
    const conditional = await getTrend("conditional-extinction-given-agi", pool);
    const gdp = await getTrend("gdp-growth-by-2035", pool);
    const revisions = await getTrend("extinction-by-2070-revisions", pool);
    expect(conditional?.contributing_statement_count).toBeGreaterThan(0);
    expect(gdp?.contributing_statement_count).toBeGreaterThan(0);
    expect(revisions?.contributing_statement_count).toBeGreaterThan(0);
    expect(trendCold.ms).toBeLessThan(15_000);
    expect(trendHot.ms).toBeLessThan(15_000);

    const overviewCold = await measure("overview-cold", () => getOverview(pool));
    samples.push(overviewCold);
    const overviewHot = await measure("overview-hot", () => getOverview(pool));
    samples.push(overviewHot);
    expect(overviewCold.value.dataset.person_count).toBeGreaterThan(PEOPLE);
    expect(overviewCold.ms).toBeLessThan(15_000);
    expect(overviewHot.ms).toBeLessThan(15_000);

    const concurrentStarted = performance.now();
    const concurrent = await Promise.all(
      Array.from({ length: 12 }, async () => {
        const started = performance.now();
        try {
          const page = await listStatements({ limit: 20 }, pool);
          return { ok: true, ms: performance.now() - started, bytes: Buffer.byteLength(JSON.stringify(page)) };
        } catch (error) {
          const name = error instanceof Error ? error.name : "unknown";
          if (name !== "AdmissionError") throw error;
          return { ok: false, ms: performance.now() - started, bytes: 0 };
        }
      }),
    );
    const concurrentMs = performance.now() - concurrentStarted;
    expect(concurrentMs).toBeLessThan(15_000);
    expect(concurrent.some((row) => row.ok)).toBe(true);

    const searchBurstStarted = performance.now();
    const searchBurst = await Promise.all(
      Array.from({ length: 8 }, async () => {
        const started = performance.now();
        try {
          await searchPublic({ q: "Scale statement", limit: 5 }, pool);
          return { ok: true, ms: performance.now() - started };
        } catch (error) {
          const name = error instanceof Error ? error.name : "unknown";
          if (name !== "AdmissionError" && name !== "SearchTimeoutError") throw error;
          return { ok: false, ms: performance.now() - started, name };
        }
      }),
    );
    const searchBurstMs = performance.now() - searchBurstStarted;
    expect(searchBurstMs).toBeLessThan(15_000);
    expect(searchBurst.some((row) => row.ok)).toBe(true);

    const report = {
      environment: {
        node: process.version,
        platform: process.platform,
        arch: process.arch,
        postgres: String(version.rows[0].server_version),
        postgres_version: String(version.rows[0].version),
        pool_max: 5,
        admission_limit: 3,
        statement_timeout_ms: 15_000,
      },
      fixture: counts,
      samples: samples.map(({ value: _value, ...sample }) => sample),
      trend: {
        cold_ms: trendCold.ms,
        hot_ms: trendHot.ms,
        cold_queries: trendCold.queries,
        hot_queries: trendHot.queries,
        cold_bytes: trendCold.bytes,
        cohort_size: extinction?.cohort_size ?? null,
        contributing_statement_count: extinction?.contributing_statement_count ?? null,
        conditional_contributing: conditional?.contributing_statement_count ?? null,
        gdp_contributing: gdp?.contributing_statement_count ?? null,
        revision_contributing: revisions?.contributing_statement_count ?? null,
      },
      overview: { cold_ms: overviewCold.ms, hot_ms: overviewHot.ms, cold_queries: overviewCold.queries, hot_queries: overviewHot.queries, cold_bytes: overviewCold.bytes },
      concurrent_lists: {
        elapsed_ms: Math.round(concurrentMs * 10) / 10,
        successes: concurrent.filter((row) => row.ok).length,
        admitted_out: concurrent.filter((row) => !row.ok).length,
        latency_ms: distribution(concurrent.map((row) => row.ms)),
      },
      concurrent_search: {
        elapsed_ms: Math.round(searchBurstMs * 10) / 10,
        successes: searchBurst.filter((row) => row.ok).length,
        limited: searchBurst.filter((row) => !row.ok).length,
        latency_ms: distribution(searchBurst.map((row) => row.ms)),
      },
      memory: process.memoryUsage(),
    };
    await writeFile(REPORT_PATH, JSON.stringify(report, null, 2));
    console.info(`scale-report ${JSON.stringify(report)}`);
  }, 120_000);
});

afterAll(async () => {
  await cleanupScale();
  await pool.end();
});
