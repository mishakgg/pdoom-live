import { beforeEach, describe, expect, it } from "vitest";
import { GET as listSiteStatements } from "../apps/web/app/api/statements/route";
import { handlePublicApi } from "../apps/web/lib/public-api-handler";
import { publicApiLimiter } from "../apps/web/lib/rate-limit";

function get(path: string, headers?: HeadersInit) {
  return handlePublicApi(new Request(`http://localhost${path}`, { headers }));
}

describe("public API v1", () => {
  beforeEach(() => {
    publicApiLimiter.reset();
  });

  it("uses the versioned envelope and hides non-public review states", async () => {
    const response = await get("/api/v1/statements?limit=50");
    expect(response.status).toBe(200);
    expect(response.headers.get("etag")).toMatch(/^"[a-f0-9]{64}"$/);
    expect(response.headers.get("cache-control")).toContain("public");
    expect(response.headers.get("last-modified")).toBeTruthy();
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

  it("returns 304 for a matching validator and keeps dataset metadata", async () => {
    const first = await get("/api/v1/dataset");
    const etag = first.headers.get("etag");
    const modified = first.headers.get("last-modified");
    expect(etag).toBeTruthy();
    expect(modified).toBeTruthy();
    const cached = await get("/api/v1/dataset", { "if-none-match": etag ?? "" });
    expect(cached.status).toBe(304);
    const stale = await get("/api/v1/dataset", { "if-modified-since": "Tue, 01 Jan 1980 00:00:00 GMT" });
    expect(stale.status).toBe(200);
    const fresh = await get("/api/v1/dataset", { "if-modified-since": modified ?? "" });
    expect(fresh.status).toBe(304);
    const again = await get("/api/v1/dataset");
    expect(again.headers.get("etag")).toBe(etag);
    const body = await first.json();
    expect(body.data.dataset.dataset_kind).toBe("synthetic");
    expect(body.data.publication.included_review_states).toEqual(["human_verified", "machine_validated"]);
    expect(body.data.license.status).toBe("cc0-1.0");
    expect(body.data.publication.excluded_review_states).toContain("needs_review");
    expect(body.data.counts.statements).toBeGreaterThan(0);
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
});
