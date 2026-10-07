import type pg from "pg";
import { afterAll, describe, expect, it, vi } from "vitest";
import { GET as statementRoute } from "../apps/web/app/api/statements/route";
import { GET as peopleRoute } from "../apps/web/app/api/people/route";
import { listPublicStatements } from "../packages/db/src/public-read";
import { handlePublicApi } from "../apps/web/lib/public-api-handler";
import { createPool } from "../packages/db/src/pool";
import { InvalidCursorError, listPeople, listStatements, type Page } from "../packages/db/src/queries";

const pool = createPool(process.env.DATABASE_URL!);
const marker = "paginationfixture";
const times = [null, null, null, "2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-03", "2024-01-04"];
const id = (n: number) => `90000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const encode = (payload: unknown) => Buffer.from(JSON.stringify(payload)).toString("base64url");

type Listed = { id: string };
async function checkNavigation(load: (cursor?: string) => Promise<Page<Listed>>, expected: string[], limit: number) {
  const pages: Page<Listed>[] = [];
  let cursor: string | undefined;
  for (let index = 0; index < 20; index += 1) {
    const page = await load(cursor);
    pages.push(page);
    expect(page.page.total).toBe(expected.length);
    expect(page.data.map((row) => row.id)).toEqual(expected.slice(index * limit, (index + 1) * limit));
    expect(Boolean(page.page.prev_cursor)).toBe(index > 0);
    if (!page.page.next_cursor) break;
    cursor = page.page.next_cursor;
  }
  expect(pages.flatMap((page) => page.data.map((row) => row.id))).toEqual(expected);
  for (let index = pages.length - 1; index > 0; index -= 1) {
    const previous = await load(pages[index].page.prev_cursor!);
    expect(previous.data.map((row) => row.id)).toEqual(pages[index - 1].data.map((row) => row.id));
    expect(Boolean(previous.page.prev_cursor)).toBe(index > 1);
    expect(previous.page.next_cursor).toBeTruthy();
    const next = await load(previous.page.next_cursor!);
    expect(next.data.map((row) => row.id)).toEqual(pages[index].data.map((row) => row.id));
  }
}

async function withRows(run: (client: pg.PoolClient) => Promise<void>) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    for (let index = 0; index < times.length; index += 1) {
      await client.query(`INSERT INTO statements (
        id, slug, person_id, source_item_id, statement_type, normalized_text, event_time,
        evidence_segment_id, extractor_name, extractor_version, confidence, review_state
      ) SELECT $1, $2, person_id, source_item_id, 'explicit_qualitative', $3, $4,
        evidence_segment_id, extractor_name, extractor_version, confidence, 'machine_validated'
        FROM statements WHERE slug = 'ada-extinction-2023'`,
      [id(index + 1), `${marker}-${index + 1}`, marker, times[index]]);
      await client.query(`INSERT INTO people (id, slug, display_name, bio_short, inclusion_reason, status)
        VALUES ($1, $2, $3, 'Synthetic pagination fixture', 'Test only', 'active')`,
      [id(index + 101), `${marker}-person-${index + 1}`, `${marker} Person ${Math.floor(index / 2)}`]);
    }
    await run(client);
  } finally {
    await client.query("ROLLBACK");
    client.release();
  }
}

describe("application keyset pagination", () => {
  afterAll(() => pool.end());

  it.each([1, 2, 3, 4])("round-trips dated, tied, and unknown-time statements with page size %i", async (limit) => {
    await withRows(async (client) => {
      for (const sort of ["event_time_asc", "event_time_desc"] as const) {
        const order = sort === "event_time_asc" ? "event_time ASC NULLS FIRST, id ASC" : "event_time DESC NULLS LAST, id DESC";
        const expected = (await client.query(`SELECT id FROM statements WHERE normalized_text = $1 ORDER BY ${order}`, [marker])).rows.map((row) => String(row.id));
        expect(expected).toHaveLength(times.length);
        await checkNavigation((cursor) => listStatements({ q: marker, sort, limit, cursor }, client), expected, limit);
      }
    });
  });

  it.each([1, 2, 3, 4])("retains database microseconds across both directions with page size %i", async (limit) => {
    await withRows(async (client) => {
      await client.query(`UPDATE statements SET event_time = timestamp '2024-01-01T00:00:00.000000Z'
        + substring(slug FROM '([0-9]+)$')::int * interval '1 microsecond'
        WHERE normalized_text = $1`, [marker]);
      for (const sort of ["event_time_asc", "event_time_desc"] as const) {
        const expected = times.map((_, index) => id(index + 1));
        if (sort === "event_time_desc") expected.reverse();
        await checkNavigation((cursor) => listStatements({ q: marker, sort, limit, cursor }, client), expected, limit);
      }
    });
  });

  it.each([1, 2, 3, 4])("retains microseconds in versioned research API cursors with page size %i", async (limit) => {
    await withRows(async (client) => {
      await client.query(`UPDATE statements SET event_time = timestamp '2024-01-01T00:00:00.000000Z'
        + substring(slug FROM '([0-9]+)$')::int * interval '1 microsecond'
        WHERE normalized_text = $1`, [marker]);
      for (const sort of ["event_time_asc", "event_time_desc"] as const) {
        const expected = times.map((_, index) => `${marker}-${index + 1}`);
        if (sort === "event_time_desc") expected.reverse();
        await checkNavigation(async (cursor) => {
          const page = await listPublicStatements({ q: marker, sort, limit, cursor }, client);
          return { ...page, data: page.data.map((row) => ({ id: row.slug })) };
        }, expected, limit);
      }
    });
  });

  it("continues accepting previously issued millisecond version-1 cursors", async () => {
    await withRows(async (client) => {
      const cursor = encode({ v: 1, t: "2024-01-01T00:00:00.000Z", id: id(5), dir: "next" });
      const page = await listStatements({ q: marker, sort: "event_time_asc", limit: 4, cursor }, client);
      expect(page.data.map((row) => row.id)).toEqual([id(6), id(7), id(8), id(9)]);
      const publicCursor = encode({ v: 1, t: "2024-01-01T00:00:00.000Z", id: `${marker}-5`, dir: "next" });
      const publicPage = await listPublicStatements({ q: marker, sort: "event_time_asc", limit: 4, cursor: publicCursor }, client);
      expect(publicPage.data.map((row) => row.slug)).toEqual([6, 7, 8, 9].map((n) => `${marker}-${n}`));
    });
  });

  it.each([1, 2, 3, 4])("returns the immediately preceding people page with page size %i", async (limit) => {
    await withRows(async (client) => {
      const expected = (await client.query("SELECT id FROM people WHERE slug LIKE $1 ORDER BY display_name ASC, id ASC", [`${marker}-person-%`])).rows.map((row) => String(row.id));
      await checkNavigation((cursor) => listPeople({ q: marker, limit, cursor }, client), expected, limit);
    });
  });

  it("returns HTTP 400 for malformed application cursors", async () => {
    const base = { v: 1, t: "2024-01-01T00:00:00.000Z", id: id(1), dir: "next" };
    for (const payload of [{ ...base, t: "now" }, { ...base, t: "0000-01-01T00:00:00.000Z" }, { ...base, id: "-".repeat(36) }]) {
      const response = await statementRoute(new Request(`http://localhost/api/statements?cursor=${encode(payload)}`));
      expect(response.status).toBe(400);
      expect(await response.json()).toMatchObject({ error: { code: "invalid_cursor" } });
    }
    const publicResponse = await handlePublicApi(new Request(`http://localhost/api/v1/statements?cursor=${encode({ ...base, id: "public-slug", t: "0000-01-01T00:00:00.000Z" })}`));
    expect(publicResponse.status).toBe(400);
    expect(await publicResponse.json()).toMatchObject({ error: { code: "invalid_cursor" } });
    const response = await peopleRoute(new Request(`http://localhost/api/people?cursor=${encode({ ...base, t: null })}`));
    expect(response.status).toBe(400);
    expect(await response.json()).toMatchObject({ error: { code: "invalid_cursor" } });
  });

  it("rejects malformed timestamp and UUID cursors before querying PostgreSQL", async () => {
    const query = vi.fn();
    const client = { query, release() {} } as unknown as pg.PoolClient;
    const base = { v: 1, t: "2024-01-01T00:00:00.000Z", id: id(1), dir: "next" };
    for (const payload of [
      { ...base, t: "now" }, { ...base, t: "2024-02-30T00:00:00.000Z" },
      { ...base, t: "0000-01-01T00:00:00.000Z" }, { ...base, t: "" }, { ...base, id: "-".repeat(36) }, { ...base, id: null },
      { ...base, dir: "sideways" }, { ...base, v: 2 },
    ]) {
      await expect(listStatements({ cursor: encode(payload), limit: 2, sort: "event_time_desc" }, client)).rejects.toBeInstanceOf(InvalidCursorError);
    }
    for (const t of [null, ""]) {
      await expect(listPeople({ cursor: encode({ ...base, t }), limit: 2 }, client)).rejects.toBeInstanceOf(InvalidCursorError);
    }
    expect(query).not.toHaveBeenCalled();
  });
});
