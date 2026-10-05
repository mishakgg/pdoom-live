import { beforeEach, describe, expect, it } from "vitest";
import { createRequestGate } from "@pdoom/contracts";
import { getPool } from "@pdoom/db";
import { handlePublicApi } from "../apps/web/lib/public-api-handler";
import { representPublicJson } from "../apps/web/lib/public-http";
import { loadPublicRepresentation, representationKey, resetPublicRepresentationCache } from "../apps/web/lib/representation-cache";
import { publicApiLimiter } from "../apps/web/lib/rate-limit";
import { resetFlights } from "../apps/web/lib/single-flight";

function get(path: string) {
  return handlePublicApi(new Request(`http://localhost${path}`));
}

function opaque(payload: unknown) {
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

async function expectInvalidCursor(path: string) {
  const response = await get(path);
  expect(response.status).toBe(400);
  expect(response.headers.get("cache-control")).toBe("no-store");
  const body = await response.json();
  expect(body.error.code).toBe("invalid_cursor");
  expect(body.data).toBeUndefined();
  expect(body.page).toBeUndefined();
}

describe("public API cursor order", () => {
  beforeEach(() => {
    publicApiLimiter.reset();
    resetPublicRepresentationCache();
    resetFlights();
  });

  it("rejects an expired or malformed opaque cursor instead of another page", async () => {
    const first = await get("/api/v1/statements?limit=2");
    expect(first.status).toBe(200);
    const firstBody = await first.json();
    const firstSlugs = firstBody.data.map((row: { slug: string }) => row.slug);
    expect(firstSlugs).toHaveLength(2);
    expect(firstBody.page.next_cursor).toBeTruthy();

    const cachedCursor = firstBody.page.next_cursor as string;
    const second = await get(`/api/v1/statements?limit=2&cursor=${encodeURIComponent(cachedCursor)}`);
    expect(second.status).toBe(200);
    const secondBody = await second.json();
    expect(secondBody.data.map((row: { slug: string }) => row.slug)).not.toEqual(firstSlugs);

    const malformed = [
      "not-a-cursor",
      opaque({ v: 2, t: "2024-01-01T00:00:00.000Z", id: "ada-quill", dir: "next" }),
      opaque({ v: 1, t: "2024-01-01T00:00:00.000Z", id: "ada-quill", dir: "sideways" }),
      opaque({ v: 1, t: "now", id: "zzz", dir: "next" }),
      opaque({ v: 1, t: "today", id: "zzz", dir: "next" }),
      opaque({ v: 1, t: "yesterday", id: "zzz", dir: "next" }),
      opaque({ v: 1, t: "tomorrow", id: "zzz", dir: "next" }),
      opaque({ v: 1, t: "infinity", id: "zzz", dir: "next" }),
      opaque({ v: 1, t: "-infinity", id: "zzz", dir: "next" }),
      opaque({ v: 1, t: "epoch", id: "zzz", dir: "next" }),
      opaque({ v: 1, t: "", id: "zzz", dir: "next" }),
      opaque({ v: 1, id: "zzz", dir: "next" }),
      `${cachedCursor}&limit=2`,
    ];
    for (const cursor of malformed) {
      await expectInvalidCursor(`/api/v1/statements?limit=2&cursor=${encodeURIComponent(cursor)}`);
    }

    const people = await get("/api/v1/people?limit=2");
    expect(people.status).toBe(200);
    const peopleBody = await people.json();
    expect(peopleBody.data).toHaveLength(2);
    await expectInvalidCursor(`/api/v1/people?limit=2&cursor=${encodeURIComponent(opaque({ v: 1, t: "", id: "zzz", dir: "next" }))}`);
    await expectInvalidCursor(`/api/v1/sources?limit=2&cursor=${encodeURIComponent(opaque({ v: 1, t: "", id: "zzz", dir: "next" }))}`);

    const collided = await get(`/api/v1/statements?cursor=${encodeURIComponent(`${cachedCursor}&limit=2`)}`);
    expect(collided.status).toBe(400);
    const collidedBody = await collided.json();
    expect(collidedBody.data).toBeUndefined();
    expect(JSON.stringify(collidedBody)).not.toContain(secondBody.data[0].slug);
  });

  it("does not let an older response overwrite a newer cursor", async () => {
    const gate = createRequestGate();
    const olderId = gate.next();
    const newerId = gate.next();
    const newer = await get("/api/v1/statements?limit=2");
    const newerBody = await newer.json();
    const older = await get(`/api/v1/statements?limit=2&cursor=${encodeURIComponent(newerBody.page.next_cursor)}`);
    const olderBody = await older.json();
    let cursor: string | null = null;
    if (gate.shouldApply(newerId)) cursor = newerBody.page.next_cursor;
    if (gate.shouldApply(olderId)) cursor = olderBody.page.next_cursor;
    expect(cursor).toBe(newerBody.page.next_cursor);
    expect(olderBody.page.next_cursor).not.toBe(newerBody.page.next_cursor);

    const olderUrl = new URL("http://localhost/api/v1/statements?cursor=abc%26limit%3D2");
    const newerUrl = new URL("http://localhost/api/v1/statements?limit=2&cursor=abc");
    const olderKey = representationKey(olderUrl);
    const newerKey = representationKey(newerUrl);
    expect(olderKey).not.toBe(newerKey);

    let releaseOlder = () => {};
    const release = new Promise<void>((resolve) => {
      releaseOlder = resolve;
    });
    let markStarted = () => {};
    const started = new Promise<void>((resolve) => {
      markStarted = resolve;
    });
    const olderLoad = loadPublicRepresentation(olderKey, getPool(), async () => {
      markStarted();
      await release;
      return representPublicJson({ page: { next_cursor: "older-cursor" } });
    });
    try {
      await started;
      const stored = await loadPublicRepresentation(newerKey, getPool(), async () =>
        representPublicJson({ page: { next_cursor: "newer-cursor" } }),
      );
      expect(JSON.parse(stored?.body ?? "{}").page.next_cursor).toBe("newer-cursor");
      releaseOlder();
      await olderLoad;
      const again = await loadPublicRepresentation(newerKey, getPool(), async () =>
        representPublicJson({ page: { next_cursor: "clobbered" } }),
      );
      expect(JSON.parse(again?.body ?? "{}").page.next_cursor).toBe("newer-cursor");
    } finally {
      releaseOlder();
      await olderLoad;
    }
  });
});
