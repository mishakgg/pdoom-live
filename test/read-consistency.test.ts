import { beforeEach, describe, expect, it } from "vitest";
import { counterSnapshot, resetMetrics } from "@pdoom/observability";
import {
  getOverview,
  getPerson,
  getPool,
  getSource,
  getTopic,
  withConsistentRead,
  type ReadinessReport,
} from "@pdoom/db";
import type { QualityReport } from "@pdoom/observability";
import { GET as listSiteStatements } from "../apps/web/app/api/statements/route";
import { readinessResponse } from "../apps/web/lib/readiness-response";
import { handlePublicApi } from "../apps/web/lib/public-api-handler";
import { representPublicJson } from "../apps/web/lib/public-http";
import { loadPublicRepresentation, publicOriginCounters, resetPublicRepresentationCache } from "../apps/web/lib/representation-cache";
import { operationalReport, resetOperationalCache } from "../apps/web/lib/operational";
import { applicationReady, clearReadinessCache } from "../apps/web/lib/ready-cache";
import { FlightLimitError, resetFlights, singleFlight } from "../apps/web/lib/single-flight";

function dbQueryCount() {
  return counterSnapshot()
    .filter((row) => row.name === "pdoom_db_queries_total")
    .reduce((sum, row) => sum + row.value, 0);
}

function defer() {
  let resolve: () => void = () => undefined;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

describe("public read consistency and in-flight caches", () => {
  beforeEach(() => {
    resetFlights();
    clearReadinessCache();
    resetOperationalCache();
    resetPublicRepresentationCache();
  });

  it("shares one in-flight load and does not remember a rejection", async () => {
    let calls = 0;
    const shared = () =>
      singleFlight("shared", async () => {
        calls += 1;
        await new Promise((resolve) => setTimeout(resolve, 20));
        return "ok";
      });
    await expect(Promise.all([shared(), shared(), shared()])).resolves.toEqual(["ok", "ok", "ok"]);
    expect(calls).toBe(1);

    await expect(
      singleFlight("bad", async () => {
        throw new Error("no");
      }),
    ).rejects.toThrow("no");
    await expect(singleFlight("bad", async () => "yes")).resolves.toBe("yes");
    await expect(
      singleFlight("sync", () => {
        throw new Error("sync");
      }),
    ).rejects.toThrow("sync");
    await expect(singleFlight("sync", async () => "recovered")).resolves.toBe("recovered");
  });

  it("rejects a new key once the in-flight map is full and accepts it after a slot frees", async () => {
    const gates: Array<(value: number) => void> = [];
    const pending = Array.from({ length: 64 }, (_, index) =>
      singleFlight(`held-${index}`, () => new Promise<number>((resolve) => gates.push(resolve))),
    );
    await Promise.resolve();
    expect(gates).toHaveLength(64);
    await expect(singleFlight("overflow", async () => 1)).rejects.toBeInstanceOf(FlightLimitError);
    gates.forEach((resolve, index) => resolve(index));
    await Promise.all(pending);
    await expect(singleFlight("overflow", async () => 1)).resolves.toBe(1);
  });

  it("coalesces readiness and operational loads and retries after a rejection", async () => {
    let readyCalls = 0;
    const readyReport: ReadinessReport = {
      status: "ready",
      checks: { process: "live", database: "ok", migrations: "current" },
    };
    const loadReady = async () => {
      readyCalls += 1;
      await new Promise((resolve) => setTimeout(resolve, 20));
      if (readyCalls === 1) throw new Error("ready-failed");
      return readyReport;
    };
    await expect(Promise.all([applicationReady(loadReady), applicationReady(loadReady)])).rejects.toThrow("ready-failed");
    expect(readyCalls).toBe(1);
    await expect(applicationReady(loadReady)).resolves.toBe(true);
    expect(readyCalls).toBe(2);
    await expect(applicationReady(loadReady)).resolves.toBe(true);
    expect(readyCalls).toBe(2);

    resetFlights();
    resetOperationalCache();
    let opsCalls = 0;
    const loadOps = async () => {
      opsCalls += 1;
      await new Promise((resolve) => setTimeout(resolve, 20));
      if (opsCalls === 1) throw new Error("ops-failed");
      return { marker: opsCalls } as QualityReport;
    };
    await expect(Promise.all([operationalReport(loadOps), operationalReport(loadOps)])).rejects.toThrow("ops-failed");
    const report = await operationalReport(loadOps);
    expect(opsCalls).toBe(2);
    await expect(operationalReport(loadOps)).resolves.toBe(report);
    expect(opsCalls).toBe(2);
  });

  it("rebuilds a public representation after a rejected load and then reuses it", async () => {
    const pool = getPool();
    let calls = 0;
    await expect(
      loadPublicRepresentation("representation-recovery", pool, async () => {
        calls += 1;
        throw new Error("representation-failed");
      }),
    ).rejects.toThrow("representation-failed");
    const produced = await loadPublicRepresentation("representation-recovery", pool, async () => representPublicJson({ ok: true }));
    expect(calls).toBe(1);
    expect(produced?.body).toContain("ok");
    const again = await loadPublicRepresentation("representation-recovery", pool, async () => {
      throw new Error("should-not-run");
    });
    expect(again?.body).toContain("ok");
    expect(publicOriginCounters().reused).toBeGreaterThan(0);
  });

  it("serves concurrent misses for one public URL from a single heavy read", async () => {
    const responses = await Promise.all(
      [0, 1, 2].map(() => handlePublicApi(new Request("http://localhost/api/v1/topics"))),
    );
    expect(responses.every((response) => response.status === 200)).toBe(true);
    expect(new Set(responses.map((response) => response.headers.get("etag"))).size).toBe(1);
    expect(publicOriginCounters().heavy).toBe(1);
  });

  it("answers readiness while snapshot slots are full and recovers after they release", async () => {
    const pool = getPool();
    const release = defer();
    const entered = [defer(), defer(), defer()];
    const holders = entered.map((gate) =>
      withConsistentRead(pool, async () => {
        gate.resolve();
        await release.promise;
      }),
    );
    await Promise.all(entered.map((gate) => gate.promise));
    try {
      expect((await readinessResponse()).status).toBe(200);
      const site = await listSiteStatements(new Request("http://localhost/api/statements?limit=1"));
      expect(site.status).toBe(429);
      expect(site.headers.get("retry-after")).toBe("1");
      expect((await site.json()).error.code).toBe("rate_limited");
      const pub = await handlePublicApi(new Request("http://localhost/api/v1/people?limit=1"));
      expect(pub.status).toBe(429);
      expect(pub.headers.get("retry-after")).toBe("1");
    } finally {
      release.resolve();
      await Promise.all(holders);
    }
    expect((await listSiteStatements(new Request("http://localhost/api/statements?limit=1"))).status).toBe(200);
  });

  it("does not let a committed review change counts inside an open repeatable read", async () => {
    const pool = getPool();
    const slug = "ada-extinction-2025";
    const original = await pool.query(`SELECT review_state, normalized_text FROM statements WHERE slug = $1`, [slug]);
    const reviewState = String(original.rows[0].review_state);
    const text = String(original.rows[0].normalized_text);
    const client = await pool.connect();
    try {
      await client.query("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY");
      const first = await getOverview(client);
      await pool.query(`UPDATE statements SET normalized_text = $2, review_state = 'rejected' WHERE slug = $1`, [
        slug,
        `${text} race`,
      ]);
      const second = await getOverview(client);
      expect(second.dataset.statement_count).toBe(first.dataset.statement_count);
      expect(second.dataset.human_verified_statement_count).toBe(first.dataset.human_verified_statement_count);
      expect(second.trends.map((trend) => [trend.slug, trend.contributing_statement_count, trend.cohort_size])).toEqual(
        first.trends.map((trend) => [trend.slug, trend.contributing_statement_count, trend.cohort_size]),
      );
      const during = await client.query(`SELECT normalized_text FROM statements WHERE slug = $1`, [slug]);
      expect(during.rows[0].normalized_text).toBe(text);
      await client.query("ROLLBACK");
    } catch (error) {
      await client.query("ROLLBACK").catch(() => undefined);
      throw error;
    } finally {
      client.release();
      await pool.query(`UPDATE statements SET normalized_text = $2, review_state = $3 WHERE slug = $1`, [slug, text, reviewState]);
    }
    const restored = await pool.query(`SELECT normalized_text, review_state FROM statements WHERE slug = $1`, [slug]);
    expect(restored.rows[0].normalized_text).toBe(text);
    expect(restored.rows[0].review_state).toBe(reviewState);
    const visible = await withConsistentRead(pool, (db) => db.query(`SELECT normalized_text FROM statements WHERE slug = $1`, [slug]));
    expect(visible.rows[0].normalized_text).toBe(text);
  });

  it("loads one person, topic, and source without scanning their full collections", async () => {
    const pool = getPool();
    resetMetrics();
    const personBefore = dbQueryCount();
    const person = await getPerson("ada-quill");
    const personQueries = dbQueryCount() - personBefore;
    expect(person?.slug).toBe("ada-quill");
    expect(personQueries).toBeGreaterThan(0);
    expect(personQueries).toBeLessThan(15);

    const topicBefore = dbQueryCount();
    const topic = await getTopic("ai-extinction");
    const topicQueries = dbQueryCount() - topicBefore;
    expect(topic?.slug).toBe("ai-extinction");
    expect(topicQueries).toBeLessThan(10);

    const sourceRow = await pool.query(`SELECT slug FROM sources ORDER BY slug LIMIT 1`);
    const sourceSlug = String(sourceRow.rows[0].slug);
    const sourceBefore = dbQueryCount();
    const source = await getSource(sourceSlug);
    const sourceQueries = dbQueryCount() - sourceBefore;
    expect(source?.slug).toBe(sourceSlug);
    expect(sourceQueries).toBeLessThan(10);
    console.info(
      JSON.stringify({
        detail_query_counts: { person: personQueries, topic: topicQueries, source: sourceQueries },
      }),
    );
  });
});
