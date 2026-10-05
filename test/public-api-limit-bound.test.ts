import { beforeEach, describe, expect, it } from "vitest";
import { handlePublicApi } from "../apps/web/lib/public-api-handler";
import { resetPublicRepresentationCache } from "../apps/web/lib/representation-cache";
import { publicApiLimiter } from "../apps/web/lib/rate-limit";
import { resetFlights } from "../apps/web/lib/single-flight";

function get(path: string, headers?: HeadersInit) {
  return handlePublicApi(new Request(`http://localhost${path}`, { headers }));
}

async function expectRejectedLimit(path: string, forbiddenSlug: string) {
  const response = await get(path);
  expect(response.status, path).toBe(400);
  expect(response.headers.get("cache-control")).toBe("no-store");
  const body = await response.json();
  expect(body.error.code, path).toBe("invalid_query");
  expect(body.data, path).toBeUndefined();
  expect(body.page, path).toBeUndefined();
  expect(JSON.stringify(body), path).not.toContain(forbiddenSlug);
  return body;
}

describe("public API limit bounds", () => {
  beforeEach(() => {
    publicApiLimiter.reset();
    resetPublicRepresentationCache();
    resetFlights();
  });

  it("rejects a limit above the maximum, zero, or negative instead of the first page", async () => {
    const first = await get("/api/v1/statements?limit=2");
    expect(first.status).toBe(200);
    const etag = first.headers.get("etag");
    expect(etag).toBeTruthy();
    const firstBody = await first.json();
    const firstSlugs = firstBody.data.map((row: { slug: string }) => row.slug);
    expect(firstSlugs).toHaveLength(2);
    expect(firstBody.page.limit).toBe(2);
    expect(firstBody.page.next_cursor).toBeTruthy();

    const second = await get(`/api/v1/statements?limit=2&cursor=${encodeURIComponent(firstBody.page.next_cursor)}`);
    expect(second.status).toBe(200);
    const secondBody = await second.json();
    expect(secondBody.page.limit).toBe(2);
    expect(secondBody.data.map((row: { slug: string }) => row.slug)).not.toEqual(firstSlugs);

    const defaults = await get("/api/v1/statements");
    expect(defaults.status).toBe(200);
    const defaultBody = await defaults.json();
    expect(defaultBody.page.limit).toBe(20);
    expect(defaultBody.data.length).toBeGreaterThan(0);
    const defaultSlug = defaultBody.data[0].slug as string;

    const people = await get("/api/v1/people?limit=1");
    expect(people.status).toBe(200);
    const peopleBody = await people.json();
    expect(peopleBody.data).toHaveLength(1);
    expect(peopleBody.page.limit).toBe(1);
    expect(peopleBody.page.next_cursor).toBeTruthy();
    const peopleNext = await get(`/api/v1/people?limit=1&cursor=${encodeURIComponent(peopleBody.page.next_cursor)}`);
    expect(peopleNext.status).toBe(200);
    expect((await peopleNext.json()).data[0].slug).not.toBe(peopleBody.data[0].slug);

    const sources = await get("/api/v1/sources?limit=1");
    expect(sources.status).toBe(200);
    const sourcesBody = await sources.json();
    expect(sourcesBody.data).toHaveLength(1);
    expect(sourcesBody.page.limit).toBe(1);
    expect(sourcesBody.page.next_cursor).toBeTruthy();

    const rejected = ["0", "00", "0.0", "+0", "-0", "-1", "-5", "51", "500", "1.5", "1e2"];
    for (const limit of rejected) {
      const encoded = encodeURIComponent(limit);
      await expectRejectedLimit(`/api/v1/statements?limit=${encoded}`, defaultSlug);
      await expectRejectedLimit(
        `/api/v1/statements?limit=${encoded}&cursor=${encodeURIComponent(firstBody.page.next_cursor)}`,
        firstSlugs[0],
      );
      await expectRejectedLimit(`/api/v1/people?limit=${encoded}`, peopleBody.data[0].slug);
      await expectRejectedLimit(`/api/v1/sources?limit=${encoded}`, sourcesBody.data[0].slug);
    }

    const cachedFirst = await get("/api/v1/statements?limit=0", { "if-none-match": etag ?? "" });
    expect(cachedFirst.status).toBe(400);
    const cachedBody = await cachedFirst.json();
    expect(cachedBody.data).toBeUndefined();
    expect(JSON.stringify(cachedBody)).not.toContain(firstSlugs[0]);

    const overMaxCached = await get("/api/v1/statements?limit=500", { "if-none-match": etag ?? "" });
    expect(overMaxCached.status).toBe(400);
    expect((await overMaxCached.json()).page).toBeUndefined();

    const one = await get("/api/v1/statements?limit=1");
    expect(one.status).toBe(200);
    const oneBody = await one.json();
    expect(oneBody.data).toHaveLength(1);
    expect(oneBody.page.limit).toBe(1);
    expect(oneBody.page.next_cursor).toBeTruthy();
    const oneNext = await get(`/api/v1/statements?limit=1&cursor=${encodeURIComponent(oneBody.page.next_cursor)}`);
    expect(oneNext.status).toBe(200);
    expect((await oneNext.json()).data[0].slug).not.toBe(oneBody.data[0].slug);

    const max = await get("/api/v1/statements?limit=50");
    expect(max.status).toBe(200);
    const maxBody = await max.json();
    expect(maxBody.page.limit).toBe(50);
    expect(maxBody.data.map((row: { slug: string }) => row.slug)).toEqual(
      expect.arrayContaining(firstSlugs),
    );
  });
});
