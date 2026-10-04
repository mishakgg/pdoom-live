import { beforeEach, describe, expect, it } from "vitest";
import { getPool, stableId } from "@pdoom/db";
import { counterSnapshot } from "@pdoom/observability";
import { GET as listSiteStatements } from "../apps/web/app/api/statements/route";
import { handlePublicApi } from "../apps/web/lib/public-api-handler";
import { publicOriginCounters, resetPublicRepresentationCache } from "../apps/web/lib/representation-cache";
import { createRateLimiter, publicApiLimiter, publicClientKey } from "../apps/web/lib/rate-limit";

function get(path: string, headers?: HeadersInit) {
  return handlePublicApi(new Request(`http://localhost${path}`, { headers }));
}

function dbQueryCount() {
  return counterSnapshot()
    .filter((row) => row.name === "pdoom_db_queries_total")
    .reduce((sum, row) => sum + row.value, 0);
}

describe("public API v1", () => {
  beforeEach(() => {
    publicApiLimiter.reset();
    resetPublicRepresentationCache();
  });

  it("uses the versioned envelope and hides non-public review states", async () => {
    const response = await get("/api/v1/statements?limit=50");
    expect(response.status).toBe(200);
    expect(response.headers.get("etag")).toMatch(/^"[a-f0-9]{64}"$/);
    expect(response.headers.get("cache-control")).toContain("public");
    expect(response.headers.get("last-modified")).toBeNull();
    expect(response.headers.get("x-api-version")).toBe("v1");
    const body = await response.json();
    expect(body.api_version).toBe("v1");
    expect(body.export_schema_version).toBe("1.0.0");
    expect(body.page.limit).toBe(50);
    const slugs = body.data.map((row: { slug: string }) => row.slug);
    expect(slugs).not.toContain("jonah-extinction-review-2024");
    expect(JSON.stringify(body)).not.toContain("extractor_version");
    expect(JSON.stringify(body)).not.toContain("verification_detail");
    const inferred = body.data.find((row: { slug: string }) => row.slug === "ada-inferred-2024");
    expect(inferred).toMatchObject({ verified: false, machine_labeled: true, statement_type: "model_inferred_signal" });
    const numeric = body.data.find((row: { slug: string }) => row.slug === "ada-extinction-2025");
    expect(numeric.forecast.question_key).toBeTruthy();
    expect(numeric.forecast.horizon_text).toBeTruthy();
    expect(numeric.forecast.unit).toBe("probability");
    expect(numeric.evidence_ref.segment_hash).toMatch(/^[a-f0-9]{64}$/);
    expect(numeric.evidence).toBeUndefined();

    const detail = await get("/api/v1/statements/ada-extinction-2025");
    const detailBody = await detail.json();
    expect(detailBody.data.evidence.text.length).toBeGreaterThan(0);
    expect(detailBody.data.source_item.canonical_url).toBe(numeric.source_item.canonical_url);
    expect(detailBody.data.person.slug).toBe(numeric.person.slug);

    const hidden = await get("/api/v1/statements/jonah-extinction-review-2024");
    expect(hidden.status).toBe(404);
    const hiddenItem = await get("/api/v1/source-items/jonah-review-2024");
    expect(hiddenItem.status).toBe(404);

    const site = await listSiteStatements(new Request("http://localhost/api/statements?person=jonah-hale&limit=50"));
    const siteBody = await site.json();
    expect(siteBody.data.some((row: { slug: string }) => row.slug === "jonah-extinction-review-2024")).toBe(true);

    const trends = await get("/api/v1/trends");
    const trendList = await trends.json();
    expect(trendList.data.some((row: { slug: string }) => row.slug === "extinction-by-2070-distribution")).toBe(true);
    const trend = await get("/api/v1/trends/extinction-by-2070-distribution");
    const trendText = JSON.stringify(await trend.json());
    expect(trendText).not.toContain("jonah-extinction-review-2024");
    expect(trendText).toContain("ada-extinction-2025");
  });

  it("pages with cursors and rejects abusive queries", async () => {
    const first = await get("/api/v1/statements?limit=2");
    const firstBody = await first.json();
    expect(firstBody.data).toHaveLength(2);
    expect(firstBody.page.next_cursor).toBeTruthy();
    const second = await get(`/api/v1/statements?limit=2&cursor=${encodeURIComponent(firstBody.page.next_cursor)}`);
    const secondBody = await second.json();
    expect(secondBody.data).toHaveLength(2);
    expect(secondBody.data[0].slug).not.toBe(firstBody.data[0].slug);
    const back = await get(`/api/v1/statements?limit=2&cursor=${encodeURIComponent(secondBody.page.prev_cursor)}`);
    const backBody = await back.json();
    expect(backBody.data.map((row: { slug: string }) => row.slug)).toEqual(
      firstBody.data.map((row: { slug: string }) => row.slug),
    );

    const full = await get("/api/v1/statements?limit=50");
    const fullBody = await full.json();
    const walked: string[] = [];
    let cursor: string | null = null;
    for (let page = 0; page < 40; page += 1) {
      const path = cursor
        ? `/api/v1/statements?limit=2&cursor=${encodeURIComponent(cursor)}`
        : "/api/v1/statements?limit=2";
      const response = await get(path);
      const body = await response.json();
      walked.push(...body.data.map((row: { slug: string }) => row.slug));
      cursor = body.page.next_cursor;
      if (!cursor) break;
    }
    expect(walked).toEqual(fullBody.data.map((row: { slug: string }) => row.slug));

    expect((await get("/api/v1/statements?limit=500")).status).toBe(400);
    expect((await get("/api/v1/statements?review_state=needs_review")).status).toBe(400);
    expect((await get("/api/v1/statements?review_state=rejected")).status).toBe(400);
    expect((await get("/api/v1/statements?review_state=unreviewed")).status).toBe(400);
    expect((await get(`/api/v1/search?q=${"a".repeat(121)}`)).status).toBe(400);
    expect((await get("/api/v1/search?q=%25%25")).status).toBe(400);
    expect((await get("/api/v1/search?q=a")).status).toBe(400);
    expect((await get("/api/v1/statements?from=2025-02-01&to=2024-01-01")).status).toBe(400);
    expect((await get(`/api/v1/statements?q=${"a".repeat(3000)}`)).status).toBe(400);
    expect((await get("/api/v1/statements?cursor=not-a-cursor")).status).toBe(400);
    expect((await get("/api/v1/people/NOT-A-SLUG")).status).toBe(400);
    const bad = await get("/api/v1/statements?limit=500");
    expect(bad.headers.get("cache-control")).toBe("no-store");
  });

  it("returns 304 for a matching ETag and ignores If-Modified-Since", async () => {
    const before = dbQueryCount();
    const first = await get("/api/v1/dataset");
    const coldQueries = dbQueryCount() - before;
    const etag = first.headers.get("etag");
    expect(etag).toBeTruthy();
    expect(first.headers.get("last-modified")).toBeNull();
    const cached = await get("/api/v1/dataset", { "if-none-match": etag ?? "" });
    expect(cached.status).toBe(304);
    expect(cached.headers.get("etag")).toBe(etag);
    const stale = await get("/api/v1/dataset", { "if-modified-since": "Tue, 01 Jan 1980 00:00:00 GMT" });
    expect(stale.status).toBe(200);
    const echoed = await get("/api/v1/dataset", { "if-modified-since": new Date().toUTCString() });
    expect(echoed.status).toBe(200);
    const mismatched = await get("/api/v1/dataset", {
      "if-none-match": '"deadbeef"',
      "if-modified-since": new Date(Date.now() + 86_400_000).toUTCString(),
    });
    expect(mismatched.status).toBe(200);
    const both = await get("/api/v1/dataset", {
      "if-none-match": etag ?? "",
      "if-modified-since": "Tue, 01 Jan 1980 00:00:00 GMT",
    });
    expect(both.status).toBe(304);
    const weak = await get("/api/v1/dataset", { "if-none-match": `W/${etag}` });
    expect(weak.status).toBe(304);
    const star = await get("/api/v1/dataset", { "if-none-match": "*" });
    expect(star.status).toBe(304);
    const hotBefore = dbQueryCount();
    const again = await get("/api/v1/dataset", { "if-none-match": etag ?? "" });
    const hotQueries = dbQueryCount() - hotBefore;
    expect(again.status).toBe(304);
    expect(again.headers.get("etag")).toBe(etag);
    expect(hotQueries).toBeLessThan(coldQueries);
    expect(hotQueries).toBeLessThanOrEqual(2);
    expect(publicOriginCounters().reused).toBeGreaterThan(0);
    expect(publicOriginCounters().heavy).toBe(1);
    const body = await first.json();
    expect(body.data.dataset.dataset_kind).toBe("synthetic");
    expect(body.data.publication.included_review_states).toEqual(["human_verified", "machine_validated"]);
    expect(body.data.license.status).toBe("cc0-1.0");
    expect(body.data.publication.excluded_review_states).toContain("needs_review");
    expect(body.data.counts.statements).toBeGreaterThan(0);
  });

  it("omits a stale human_verified approval from the research export", async () => {
    const pool = getPool();
    const slug = "ada-extinction-2025";
    expect((await get(`/api/v1/statements/${slug}`)).status).toBe(200);
    const row = await pool.query(
      `SELECT s.id, s.candidate_key, si.id AS source_item_id, e.id AS evidence_id, si.content_version
       FROM statements s
       JOIN source_items si ON si.id = s.source_item_id
       JOIN evidence_segments e ON e.id = s.evidence_segment_id
       WHERE s.slug = $1`,
      [slug],
    );
    const found = row.rows[0];
    const key = "stale-research-export-test";
    await pool.query(
      `INSERT INTO review_decisions (
         id, decision_key, statement_id, candidate_key, decision, previous_review_state,
         resulting_review_state, reviewed_at, reviewer, source_item_id, evidence_segment_id,
         source_content_hash, evidence_hash, content_version, corrections_json, original_extraction_json
       ) VALUES ($1,$2,$3,$4,'approve','needs_review','human_verified',$5,'test',$6,$7,$8,$9,$10,'{}'::jsonb,'{}'::jsonb)`,
      [
        stableId(`review:${key}`),
        key,
        found.id,
        found.candidate_key,
        "2026-09-27T00:00:00.000Z",
        found.source_item_id,
        found.evidence_id,
        "a".repeat(64),
        "b".repeat(64),
        found.content_version,
      ],
    );
    try {
      expect((await get(`/api/v1/statements/${slug}`)).status).toBe(404);
      const listed = await get("/api/v1/statements?limit=50&person=ada-quill");
      const body = await listed.json();
      expect(body.data.map((item: { slug: string }) => item.slug)).not.toContain(slug);
      const trend = await get("/api/v1/trends/extinction-by-2070-distribution");
      expect(trend.status).toBe(200);
      const trendBody = await trend.json();
      expect(JSON.stringify(trendBody)).not.toContain(slug);
      expect(trendBody.data.method_version).toBe("explicit-numeric-distribution/1.1.0");
      expect(trendBody.data.omitted_non_research_count).toBeGreaterThan(0);
      const site = await listSiteStatements(new Request("http://localhost/api/statements?person=ada-quill&limit=50"));
      const siteBody = await site.json();
      const visible = siteBody.data.find((item: { slug: string; review_state: string }) => item.slug === slug);
      expect(visible?.review_state).toBe("needs_review");
    } finally {
      await pool.query(`DELETE FROM review_decisions WHERE decision_key = $1`, [key]);
    }
    expect((await get(`/api/v1/statements/${slug}`)).status).toBe(200);
  });

  it("does not treat import time as a validator when a review changes the payload in one second", async () => {
    const pool = getPool();
    const slug = "ada-extinction-2025";
    const paths = [
      "/api/v1/dataset",
      "/api/v1/statements?limit=50",
      `/api/v1/statements/${slug}`,
      "/api/v1/topics",
      "/api/v1/trends",
      "/api/v1/trends/extinction-by-2070-distribution",
    ];
    const before = new Map<string, { status: number; etag: string | null; text: string }>();
    for (const path of paths) {
      const response = await get(path);
      before.set(path, {
        status: response.status,
        etag: response.headers.get("etag"),
        text: await response.text(),
      });
    }
    expect(before.get(`/api/v1/statements/${slug}`)?.status).toBe(200);
    const stamp = await pool.query(
      `SELECT imported_at FROM dataset_imports WHERE is_current ORDER BY imported_at DESC LIMIT 1`,
    );
    const importedAt = new Date(stamp.rows[0].imported_at as Date).toISOString();
    const importHttpDate = new Date(importedAt).toUTCString();
    const firstInstant = "2026-10-04T12:00:00.100Z";
    const secondInstant = "2026-10-04T12:00:00.900Z";
    expect(new Date(firstInstant).toUTCString()).toBe(new Date(secondInstant).toUTCString());
    const row = await pool.query(
      `SELECT s.id, s.candidate_key, si.id AS source_item_id, e.id AS evidence_id, si.content_version,
              si.content_hash, e.segment_hash
       FROM statements s
       JOIN source_items si ON si.id = s.source_item_id
       JOIN evidence_segments e ON e.id = s.evidence_segment_id
       WHERE s.slug = $1`,
      [slug],
    );
    const found = row.rows[0];
    const keys = ["same-second-review-a", "same-second-review-b"];
    async function insertDecision(key: string, reviewedAt: string, sourceHash: string, evidenceHash: string) {
      await pool.query(
        `INSERT INTO review_decisions (
           id, decision_key, statement_id, candidate_key, decision, previous_review_state,
           resulting_review_state, reviewed_at, reviewer, source_item_id, evidence_segment_id,
           source_content_hash, evidence_hash, content_version, corrections_json, original_extraction_json
         ) VALUES ($1,$2,$3,$4,'approve','needs_review','human_verified',$5,'test',$6,$7,$8,$9,$10,'{}'::jsonb,'{}'::jsonb)`,
        [
          stableId(`review:${key}`),
          key,
          found.id,
          found.candidate_key ?? slug,
          reviewedAt,
          found.source_item_id,
          found.evidence_id,
          sourceHash,
          evidenceHash,
          found.content_version,
        ],
      );
    }
    try {
      const datasetPath = "/api/v1/dataset";
      const listPath = "/api/v1/statements?limit=50";
      const trendPath = "/api/v1/trends/extinction-by-2070-distribution";
      const trendsPath = "/api/v1/trends";
      const topicsPath = "/api/v1/topics";
      const changedPaths = [datasetPath, listPath, trendPath, trendsPath, topicsPath];
      const beforeCount = JSON.parse(before.get(datasetPath)?.text ?? "{}").data.counts.statements as number;
      await insertDecision(keys[0], firstInstant, "c".repeat(64), "d".repeat(64));
      const hidden = await get(`/api/v1/statements/${slug}`, {
        "if-none-match": before.get(`/api/v1/statements/${slug}`)?.etag ?? "",
        "if-modified-since": importHttpDate,
      });
      expect(hidden.status).toBe(404);
      expect(hidden.headers.get("last-modified")).toBeNull();
      const mid = new Map<string, string>();
      for (const path of changedPaths) {
        const response = await get(path, {
          "if-none-match": before.get(path)?.etag ?? "",
          "if-modified-since": importHttpDate,
        });
        expect(response.status, path).toBe(200);
        expect(response.headers.get("last-modified")).toBeNull();
        const etag = response.headers.get("etag");
        expect(etag, path).toBeTruthy();
        expect(etag).not.toBe(before.get(path)?.etag);
        mid.set(path, etag ?? "");
        const text = await response.text();
        if (path === datasetPath) expect(JSON.parse(text).data.counts.statements).toBe(beforeCount - 1);
        if (path === listPath || path === trendPath) expect(text).not.toContain(slug);
      }
      await insertDecision(keys[1], secondInstant, String(found.content_hash), String(found.segment_hash));
      const sameSecond = new Date(firstInstant).toUTCString();
      for (const path of changedPaths) {
        const response = await get(path, {
          "if-none-match": mid.get(path) ?? "",
          "if-modified-since": sameSecond,
        });
        expect(response.status, path).toBe(200);
        const etag = response.headers.get("etag");
        expect(etag).toBeTruthy();
        expect(etag).not.toBe(mid.get(path));
        const text = await response.text();
        if (path === datasetPath) expect(JSON.parse(text).data.counts.statements).toBe(beforeCount);
        if (path === listPath || path === trendPath) expect(text).toContain(slug);
        const cached = await get(path, { "if-none-match": etag ?? "", "if-modified-since": importHttpDate });
        expect(cached.status, path).toBe(304);
        expect(cached.headers.get("etag")).toBe(etag);
      }
      const restored = await get(`/api/v1/statements/${slug}`, { "if-modified-since": importHttpDate });
      expect(restored.status).toBe(200);
      expect(restored.headers.get("last-modified")).toBeNull();
      const stampAfter = await pool.query(
        `SELECT imported_at FROM dataset_imports WHERE is_current ORDER BY imported_at DESC LIMIT 1`,
      );
      expect(new Date(stampAfter.rows[0].imported_at as Date).toISOString()).toBe(importedAt);
    } finally {
      await pool.query(`DELETE FROM review_decisions WHERE decision_key = ANY($1::text[])`, [keys]);
    }
  });

  it("changes detail and list validators when statement text changes and the import time does not", async () => {
    const pool = getPool();
    const slug = "ada-extinction-2025";
    const original = await pool.query(`SELECT normalized_text FROM statements WHERE slug = $1`, [slug]);
    const text = String(original.rows[0].normalized_text);
    const stamp = await pool.query(`SELECT imported_at FROM dataset_imports WHERE is_current ORDER BY imported_at DESC LIMIT 1`);
    const importHttpDate = new Date(stamp.rows[0].imported_at as Date).toUTCString();
    const detailPath = `/api/v1/statements/${slug}`;
    const listPath = "/api/v1/statements?limit=50&person=ada-quill";
    const detail = await get(detailPath);
    const list = await get(listPath);
    const detailEtag = detail.headers.get("etag");
    const listEtag = list.headers.get("etag");
    expect(detailEtag).toBeTruthy();
    expect(listEtag).toBeTruthy();
    try {
      await pool.query(`UPDATE statements SET normalized_text = $2 WHERE slug = $1`, [slug, `${text} (corrected)`]);
      const changedDetail = await get(detailPath, {
        "if-none-match": detailEtag ?? "",
        "if-modified-since": importHttpDate,
      });
      expect(changedDetail.status).toBe(200);
      expect(changedDetail.headers.get("etag")).not.toBe(detailEtag);
      expect(changedDetail.headers.get("last-modified")).toBeNull();
      const changedBody = await changedDetail.json();
      expect(changedBody.data.normalized_text).toContain("(corrected)");
      const changedList = await get(listPath, {
        "if-none-match": listEtag ?? "",
        "if-modified-since": importHttpDate,
      });
      expect(changedList.status).toBe(200);
      expect(changedList.headers.get("etag")).not.toBe(listEtag);
      const fresh = changedDetail.headers.get("etag");
      expect((await get(detailPath, { "if-none-match": fresh ?? "" })).status).toBe(304);
    } finally {
      await pool.query(`UPDATE statements SET normalized_text = $2 WHERE slug = $1`, [slug, text]);
    }
  });

  it("changes the detail validator when the source version changes and the import time does not", async () => {
    const pool = getPool();
    const slug = "ada-extinction-2025";
    const original = await pool.query(
      `SELECT si.id, si.content_hash, si.content_version
       FROM source_items si
       JOIN statements s ON s.source_item_id = si.id
       WHERE s.slug = $1`,
      [slug],
    );
    const item = original.rows[0];
    const stamp = await pool.query(`SELECT imported_at FROM dataset_imports WHERE is_current ORDER BY imported_at DESC LIMIT 1`);
    const importHttpDate = new Date(stamp.rows[0].imported_at as Date).toUTCString();
    const path = `/api/v1/statements/${slug}`;
    const first = await get(path);
    const etag = first.headers.get("etag");
    try {
      await pool.query(`UPDATE source_items SET content_hash = $2, content_version = content_version + 1 WHERE id = $1`, [
        item.id,
        "e".repeat(64),
      ]);
      const changed = await get(path, { "if-none-match": etag ?? "", "if-modified-since": importHttpDate });
      expect(changed.status).toBe(200);
      expect(changed.headers.get("etag")).not.toBe(etag);
      expect(changed.headers.get("last-modified")).toBeNull();
      const body = await changed.json();
      expect(body.data.source_item.content_hash).toBe("e".repeat(64));
      const fresh = changed.headers.get("etag");
      expect((await get(path, { "if-none-match": fresh ?? "", "if-modified-since": importHttpDate })).status).toBe(304);
    } finally {
      await pool.query(`UPDATE source_items SET content_hash = $2, content_version = $3 WHERE id = $1`, [
        item.id,
        item.content_hash,
        item.content_version,
      ]);
    }
  });

  it("pages statements with tied and null event times in a stable order", async () => {
    const pool = getPool();
    const listed = await get("/api/v1/statements?limit=50");
    const listedBody = await listed.json();
    const slugs = (listedBody.data as Array<{ slug: string }>).map((row) => row.slug).sort();
    expect(slugs.length).toBeGreaterThanOrEqual(3);
    const [tieA, tieB, blank] = slugs;
    const original = await pool.query(`SELECT slug, event_time FROM statements WHERE slug = ANY($1::text[])`, [[tieA, tieB, blank]]);
    try {
      await pool.query(`UPDATE statements SET event_time = $2 WHERE slug = ANY($1::text[])`, [[tieA, tieB], "2024-06-01T12:00:00.000Z"]);
      await pool.query(`UPDATE statements SET event_time = NULL WHERE slug = $1`, [blank]);
      resetPublicRepresentationCache();
      async function walk() {
        const rows: Array<{ slug: string; event_time: string | null }> = [];
        let cursor: string | null = null;
        for (let page = 0; page < 100; page += 1) {
          const path = cursor
            ? `/api/v1/statements?limit=2&cursor=${encodeURIComponent(cursor)}`
            : "/api/v1/statements?limit=2";
          const response = await get(path);
          expect(response.status).toBe(200);
          const body = await response.json();
          rows.push(...body.data);
          cursor = body.page.next_cursor;
          if (!cursor) break;
        }
        expect(cursor).toBeNull();
        return rows;
      }
      const first = await walk();
      const second = await walk();
      expect(second.map((row) => row.slug)).toEqual(first.map((row) => row.slug));
      expect(new Set(first.map((row) => row.slug)).size).toBe(first.length);
      const blankIndex = first.findIndex((row) => row.slug === blank);
      expect(blankIndex).toBeGreaterThanOrEqual(0);
      expect(first.slice(blankIndex).every((row) => row.event_time === null)).toBe(true);
      const tied = first.filter((row) => row.slug === tieA || row.slug === tieB);
      expect(tied.map((row) => row.event_time)).toEqual([tied[0]?.event_time, tied[0]?.event_time]);
      expect(first.findIndex((row) => row.slug === tieA) < first.findIndex((row) => row.slug === tieB)).toBe(tieA > tieB);
      for (let index = 1; index < first.length; index += 1) {
        const previous = first[index - 1];
        const current = first[index];
        if (previous?.event_time === null) expect(current?.event_time).toBeNull();
        else if (previous?.event_time && current?.event_time === previous.event_time) {
          expect((previous.slug > current.slug)).toBe(true);
        }
      }
    } finally {
      for (const row of original.rows) {
        await pool.query(`UPDATE statements SET event_time = $2 WHERE slug = $1`, [row.slug, row.event_time]);
      }
      resetPublicRepresentationCache();
    }
  });

  it("rate-limits the public route without changing the response shape of a normal call", async () => {
    process.env.PDOOM_PUBLIC_RATE_LIMIT = "2";
    process.env.PDOOM_PUBLIC_PROCESS_RATE_LIMIT = "100";
    publicApiLimiter.reset();
    try {
      expect((await get("/api/v1/topics")).status).toBe(200);
      expect((await get("/api/v1/topics")).status).toBe(200);
      const limited = await get("/api/v1/topics");
      expect(limited.status).toBe(429);
      expect(limited.headers.get("retry-after")).toBeTruthy();
      const body = await limited.json();
      expect(body.error.code).toBe("rate_limited");
    } finally {
      delete process.env.PDOOM_PUBLIC_RATE_LIMIT;
      delete process.env.PDOOM_PUBLIC_PROCESS_RATE_LIMIT;
      publicApiLimiter.reset();
    }
  });

  it("ignores a caller-supplied forwarding header unless the proxy hop count is configured", async () => {
    const previous = process.env.PDOOM_TRUSTED_PROXY_HOPS;
    delete process.env.PDOOM_TRUSTED_PROXY_HOPS;
    try {
      const spoofed = new Request("http://localhost/api/v1/topics", { headers: { "x-forwarded-for": "1.2.3.4" } });
      const other = new Request("http://localhost/api/v1/topics", { headers: { "x-forwarded-for": "203.0.113.9" } });
      expect(publicClientKey(spoofed)).toBe("direct");
      expect(publicClientKey(other)).toBe("direct");
      process.env.PDOOM_PUBLIC_RATE_LIMIT = "2";
      process.env.PDOOM_PUBLIC_PROCESS_RATE_LIMIT = "100";
      publicApiLimiter.reset();
      expect((await get("/api/v1/topics", { "x-forwarded-for": "1.2.3.4" })).status).toBe(200);
      expect((await get("/api/v1/topics", { "x-forwarded-for": "203.0.113.8" })).status).toBe(200);
      expect((await get("/api/v1/topics", { "x-forwarded-for": "198.51.100.2" })).status).toBe(429);
      process.env.PDOOM_TRUSTED_PROXY_HOPS = "1";
      publicApiLimiter.reset();
      const forwarded = "1.2.3.4, 203.0.113.9";
      expect(publicClientKey(new Request("http://localhost/api/v1/topics", { headers: { "x-forwarded-for": forwarded } }))).toBe(
        "xff:203.0.113.9",
      );
      expect(publicClientKey(new Request("http://localhost/api/v1/topics", { headers: { "x-forwarded-for": "not-an-ip" } }))).toBe(
        "direct",
      );
      expect((await get("/api/v1/topics", { "x-forwarded-for": forwarded })).status).toBe(200);
      expect((await get("/api/v1/topics", { "x-forwarded-for": "8.8.8.8, 203.0.113.9" })).status).toBe(200);
      expect((await get("/api/v1/topics", { "x-forwarded-for": "9.9.9.9, 203.0.113.9" })).status).toBe(429);
      expect((await get("/api/v1/topics", { "x-forwarded-for": "198.51.100.20" })).status).toBe(200);
      process.env.PDOOM_TRUSTED_PROXY_HOPS = "2";
      expect(publicClientKey(new Request("http://localhost/api/v1/topics", { headers: { "x-forwarded-for": forwarded } }))).toBe(
        "xff:1.2.3.4",
      );
      const limiter = createRateLimiter();
      process.env.PDOOM_PUBLIC_RATE_LIMIT = "1";
      process.env.PDOOM_PUBLIC_PROCESS_RATE_LIMIT = "100000";
      for (let octet = 1; octet <= 1024; octet += 1) {
        const decision = limiter.consume(`xff:10.1.${octet >> 8}.${octet & 255}`);
        expect(decision.ok).toBe(true);
      }
      expect(limiter.consume("xff:192.0.2.9").ok).toBe(true);
      expect(limiter.consume("xff:192.0.2.10").ok).toBe(false);
    } finally {
      if (previous === undefined) delete process.env.PDOOM_TRUSTED_PROXY_HOPS;
      else process.env.PDOOM_TRUSTED_PROXY_HOPS = previous;
      delete process.env.PDOOM_PUBLIC_RATE_LIMIT;
      delete process.env.PDOOM_PUBLIC_PROCESS_RATE_LIMIT;
      publicApiLimiter.reset();
    }
  });
});
