import { createHash } from "node:crypto";
import {
  SEARCH_ENTITY_TYPES,
  SEARCH_PAGE_LIMIT_DEFAULT,
  SEARCH_RANK,
  SEARCH_SUGGEST_LIMITS,
  prepareSearchText,
  type SearchEntityType,
} from "@pdoom/contracts";
import type pg from "pg";
import { describe, expect, it, vi } from "vitest";
import { InvalidCursorError } from "../packages/db/src/queries";
import { SearchTimeoutError, searchPublic } from "../packages/db/src/search";

type Row = Record<string, unknown>;
type Reply = Row[] | Error;
type QueryCall = [text: string, values?: unknown[]];

// Script database responses, not matching/publication predicates. These tests run
// the real builders and orchestration; search.test.ts exercises the SQL in Postgres.
function fakeClient(...replies: Reply[]) {
  let index = 0;
  const query = vi.fn(async (_text: string, _values?: unknown[]) => {
    const reply = replies[index++];
    if (reply === undefined) throw new Error("Unexpected database query");
    if (reply instanceof Error) throw reply;
    return { rows: reply };
  });
  const release = vi.fn();
  const client = { query, release } as unknown as pg.PoolClient;
  return { client, query, release };
}

function fakePool(client: pg.PoolClient) {
  const connect = vi.fn(async () => client);
  const query = vi.fn(async () => {
    throw new Error("Search must use the checked-out snapshot client");
  });
  return { pool: { connect, query } as unknown as pg.Pool, connect, query };
}

const COUNT_SELECT = "SELECT count(*)::int AS total_count FROM matched";
const PAGE_SELECT = "SELECT * FROM matched";
const EMPTY_CURSOR_ID = "00000000-0000-0000-0000-000000000000";
const VALID_CURSOR_IDS = [
  EMPTY_CURSOR_ID,
  "abcdefab-cdef-4abc-8def-abcdefabcdef",
  "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF",
  "aBcDeFaB-cDeF-4aBc-8dEf-AbCdEfAbCdEf",
  "ffffffff-ffff-ffff-ffff-ffffffffffff",
  "12345678-1234-0234-0234-123456789abc",
];
const MALFORMED_CURSOR_IDS: Array<{ label: string; id: unknown }> = [
  { label: "36 hyphens", id: "-".repeat(36) },
  { label: "36 hex digits", id: "a".repeat(36) },
  { label: "misplaced hyphen", id: "000000000-000-0000-0000-000000000000" },
  { label: "array-coerced UUID", id: [EMPTY_CURSOR_ID] },
  { label: "nested array-coerced UUID", id: [[EMPTY_CURSOR_ID]] },
  { label: "missing ID", id: undefined },
  { label: "null ID", id: null },
  { label: "object ID", id: {} },
  { label: "numeric ID", id: 0 },
  { label: "nonhex ID", id: "g0000000-0000-0000-0000-000000000000" },
  { label: "compact ID", id: "0".repeat(32) },
  { label: "braced ID", id: `{${EMPTY_CURSOR_ID}}` },
  { label: "trailing newline", id: `${EMPTY_CURSOR_ID}\n` },
];
const modes = ["page", "suggest"] as const;
const cases = SEARCH_ENTITY_TYPES.flatMap((type) => modes.map((mode) => ({ type, mode })));

function withCursorPayload(cursor: string, changes: Record<string, unknown>): string {
  const payload = JSON.parse(Buffer.from(cursor, "base64url").toString("utf8")) as Record<string, unknown>;
  Object.assign(payload, changes);
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function expectCount(call: QueryCall) {
  expect(call[0].trimEnd().endsWith(COUNT_SELECT)).toBe(true);
  expect(call[1]).toBeDefined();
}

function expectSharedRelation(count: QueryCall, page: QueryCall) {
  expectCount(count);
  const countEnd = count[0].lastIndexOf(COUNT_SELECT);
  const pageEnd = page[0].lastIndexOf(PAGE_SELECT);
  expect(pageEnd).toBeGreaterThan(0);
  expect(page[0].slice(0, pageEnd)).toBe(count[0].slice(0, countEnd));
  expect(page[1]?.slice(0, count[1]!.length)).toEqual(count[1]);
  expect(page[1]).toHaveLength(count[1]!.length + 4);
}

function hitRow(type: SearchEntityType, index: number) {
  const timeSorted = type === "statement" || type === "source_item";
  return {
    id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    slug: `${type.replaceAll("_", "-")}-${index}`,
    hit_rank: SEARCH_RANK.all_tokens,
    hit_match: "all_tokens",
    tie: timeSorted ? `2026-01-01 00:00:00.${String(100 - index).padStart(6, "0")}` : `result ${index}`,
    display_name: `Person ${index}`,
    status: "active",
    name: `Result ${index}`,
    organization_type: "research_lab",
    definition: "Topic definition",
    statement_type: "explicit_qualitative",
    normalized_text: "A sourced statement",
    event_time: "2026-01-01T00:00:00.000Z",
    review_state: "machine_validated",
    person_slug: "fixture-person",
    source_slug: "fixture-source",
    source_name: "Fixture source",
    source_type: "blog",
    source_item_slug: "fixture-item",
    source_item_title: "Fixture item",
    title: `Item ${index}`,
    published_at: "2026-01-01T00:00:00.000Z",
    topics: [],
  };
}

describe("search count/page query budget", () => {
  it.each(cases)("skips the $type page query after a zero count in $mode mode", async ({ type, mode }) => {
    const db = fakeClient([{ total_count: "0" }]);
    const result = await searchPublic({ q: "missing", type, mode, limit: 7 }, db.client);

    expect(db.query).toHaveBeenCalledTimes(1);
    expectCount(db.query.mock.calls[0]!);
    expect(result.groups[type]).toEqual({
      data: [],
      page: { limit: mode === "suggest" ? SEARCH_SUGGEST_LIMITS[type] : 7, total: 0, next_cursor: null },
    });
    expect(result.query.types).toEqual([type]);
    expect(db.release).not.toHaveBeenCalled();
  });

  it.each([
    { label: "numeric zero", rows: [{ total_count: 0 }] },
    { label: "missing count row", rows: [] },
    { label: "missing count value", rows: [{}] },
    { label: "null count value", rows: [{ total_count: null }] },
  ])("preserves count parsing for $label", async ({ rows }) => {
    const db = fakeClient(rows);
    const result = await searchPublic({ q: "missing", type: "statement", mode: "page" }, db.client);

    expect(db.query).toHaveBeenCalledTimes(1);
    expect(result.groups.statement).toEqual({
      data: [],
      page: { limit: SEARCH_PAGE_LIMIT_DEFAULT, total: 0, next_cursor: null },
    });
  });

  it.each(modes)("uses six count queries and no page queries for empty %s groups", async (mode) => {
    const db = fakeClient(...SEARCH_ENTITY_TYPES.map(() => [{ total_count: 0 }]));
    const result = await searchPublic({ q: "missing", mode }, db.client);

    expect(db.query).toHaveBeenCalledTimes(6);
    db.query.mock.calls.forEach(expectCount);
    expect(result.query.types).toEqual(SEARCH_ENTITY_TYPES);
    for (const type of SEARCH_ENTITY_TYPES) {
      expect(result.groups[type]).toEqual({
        data: [],
        page: {
          limit: mode === "suggest" ? SEARCH_SUGGEST_LIMITS[type] : SEARCH_PAGE_LIMIT_DEFAULT,
          total: 0,
          next_cursor: null,
        },
      });
    }
  });

  it.each(cases)("keeps the count/page relation and bounded $type results in $mode mode", async ({ type, mode }) => {
    const limit = mode === "suggest" ? SEARCH_SUGGEST_LIMITS[type] : 3;
    const rows = Array.from({ length: limit + 1 }, (_, index) => hitRow(type, index + 1));
    const db = fakeClient([{ total_count: "12" }], rows);
    const result = await searchPublic({ q: "result", type, mode, limit: 3 }, db.client);

    expect(db.query).toHaveBeenCalledTimes(2);
    expectSharedRelation(db.query.mock.calls[0]!, db.query.mock.calls[1]!);
    expect(db.query.mock.calls[1]![1]?.slice(-4)).toEqual([null, "", EMPTY_CURSOR_ID, limit + 1]);
    const group = result.groups[type];
    expect(group.page).toEqual({ limit, total: 12, next_cursor: expect.any(String) });
    expect(group.data.map((hit) => hit.id)).toEqual(rows.slice(0, limit).map((row) => row.id));
    for (const hit of group.data) {
      expect(hit).toMatchObject({ kind: type, match: "all_tokens" });
      expect(hit).not.toHaveProperty("hit_rank");
      expect(hit).not.toHaveProperty("hit_match");
      expect(hit).not.toHaveProperty("tie");
    }
    expect(db.release).not.toHaveBeenCalled();
  });

  it.each(modes)("queries pages only for nonempty groups in a mixed %s response", async (mode) => {
    const nonempty = new Set<SearchEntityType>(["organization", "statement", "source_item"]);
    const replies: Reply[] = [];
    for (const type of SEARCH_ENTITY_TYPES) {
      replies.push([{ total_count: nonempty.has(type) ? 1 : 0 }]);
      if (nonempty.has(type)) replies.push([hitRow(type, 1)]);
    }
    const db = fakeClient(...replies);
    const result = await searchPublic({ q: "result", mode, limit: 5 }, db.client);

    expect(db.query).toHaveBeenCalledTimes(6 + nonempty.size);
    let call = 0;
    for (const type of SEARCH_ENTITY_TYPES) {
      const count = db.query.mock.calls[call++]!;
      expectCount(count);
      if (nonempty.has(type)) expectSharedRelation(count, db.query.mock.calls[call++]!);
      expect(result.groups[type].data.map((hit) => hit.kind)).toEqual(nonempty.has(type) ? [type] : []);
      expect(result.groups[type].page).toEqual({
        limit: mode === "suggest" ? SEARCH_SUGGEST_LIMITS[type] : 5,
        total: nonempty.has(type) ? 1 : 0,
        next_cursor: null,
      });
    }
  });

  it.each(SEARCH_ENTITY_TYPES)("preserves the total and cursor continuation for %s", async (type) => {
    const first = hitRow(type, 1);
    const second = hitRow(type, 2);
    const db = fakeClient([{ total_count: 2 }], [first, second], [{ total_count: 2 }], [second]);
    const input = { q: "result", type, mode: "page" as const, limit: 1 };
    const initial = await searchPublic(input, db.client);
    const cursor = initial.groups[type].page.next_cursor;
    expect(cursor).toEqual(expect.any(String));
    expect(JSON.parse(Buffer.from(cursor!, "base64url").toString("utf8"))).toEqual({
      v: 2,
      fp: expect.any(String),
      rank: first.hit_rank,
      tie: first.tie,
      id: first.id,
      sort: type === "statement" || type === "source_item" ? "time" : "name",
    });

    const next = await searchPublic({ ...input, cursor: cursor! }, db.client);
    expect(db.query).toHaveBeenCalledTimes(4);
    expectSharedRelation(db.query.mock.calls[2]!, db.query.mock.calls[3]!);
    expect(db.query.mock.calls[2]).toEqual(db.query.mock.calls[0]);
    expect(db.query.mock.calls[3]![1]?.slice(-4)).toEqual([first.hit_rank, first.tie, first.id, 2]);
    expect(initial.groups[type].data.map((hit) => hit.id)).toEqual([first.id]);
    expect(next.groups[type].data.map((hit) => hit.id)).toEqual([second.id]);
    expect(next.groups[type].page).toEqual({ limit: 1, total: 2, next_cursor: null });
  });

  it.each(["person", "statement"] as const)("keeps a positive %s total when a cursor page is empty", async (type) => {
    const first = hitRow(type, 1);
    const db = fakeClient([{ total_count: 7 }], [first, hitRow(type, 2)], [{ total_count: "7" }], []);
    const input = { q: "result", type, mode: "page" as const, limit: 1 };
    const initial = await searchPublic(input, db.client);
    const result = await searchPublic({ ...input, cursor: initial.groups[type].page.next_cursor! }, db.client);

    expect(db.query).toHaveBeenCalledTimes(4);
    expectSharedRelation(db.query.mock.calls[2]!, db.query.mock.calls[3]!);
    expect(result.groups[type]).toEqual({ data: [], page: { limit: 1, total: 7, next_cursor: null } });
  });

  it.each(["person", "statement"] as const)("still queries an empty %s page when a valid cursor is present", async (type) => {
    const first = hitRow(type, 1);
    const db = fakeClient([{ total_count: 2 }], [first, hitRow(type, 2)], [{ total_count: 0 }], []);
    const input = { q: "result", type, mode: "page" as const, limit: 1 };
    const initial = await searchPublic(input, db.client);
    const result = await searchPublic({ ...input, cursor: initial.groups[type].page.next_cursor! }, db.client);

    expect(db.query).toHaveBeenCalledTimes(4);
    expect(db.query.mock.calls[2]).toEqual(db.query.mock.calls[0]);
    expectSharedRelation(db.query.mock.calls[2]!, db.query.mock.calls[3]!);
    expect(db.query.mock.calls[3]![1]?.slice(-4)).toEqual([first.hit_rank, first.tie, first.id, 2]);
    expect(result.groups[type]).toEqual({ data: [], page: { limit: 1, total: 0, next_cursor: null } });
  });

  it.each(SEARCH_ENTITY_TYPES)("rejects malformed %s cursor IDs before a direct client query", async (type) => {
    const mint = fakeClient([{ total_count: 2 }], [hitRow(type, 1), hitRow(type, 2)]);
    const input = { q: "result", type, mode: "page" as const, limit: 1 };
    const initial = await searchPublic(input, mint.client);
    for (const { label, id } of MALFORMED_CURSOR_IDS) {
      const db = fakeClient();
      const cursor = withCursorPayload(initial.groups[type].page.next_cursor!, { id });
      await expect(searchPublic({ ...input, cursor }, db.client), label).rejects.toBeInstanceOf(InvalidCursorError);
      expect(db.query, label).not.toHaveBeenCalled();
      expect(db.release, label).not.toHaveBeenCalled();
    }
  });

  it.each(["person", "statement"] as const)("preserves canonical %s IDs, ranks, ties, and base64 padding", async (type) => {
    const mint = fakeClient([{ total_count: 2 }], [hitRow(type, 1), hitRow(type, 2)]);
    const input = { q: "result", type, mode: "page" as const, limit: 1 };
    const initial = await searchPublic(input, mint.client);
    for (const id of VALID_CURSOR_IDS) {
      for (const rank of [0, ...Object.values(SEARCH_RANK)]) {
        for (const tie of ["", type === "statement" ? "2026-01-01 00:00:00.000001" : "Äda researcher"]) {
          const db = fakeClient([{ total_count: 0 }], []);
          const cursor = withCursorPayload(initial.groups[type].page.next_cursor!, { id, rank, tie }) + "==";
          const result = await searchPublic({ ...input, cursor }, db.client);
          expect(db.query).toHaveBeenCalledTimes(2);
          expect(db.query.mock.calls[1]![1]?.slice(-4)).toEqual([rank, tie, id, 2]);
          expect(result.groups[type]).toEqual({ data: [], page: { limit: 1, total: 0, next_cursor: null } });
        }
      }
    }
  });

  it("still rejects incompatible cursor metadata before database access", async () => {
    const mint = fakeClient([{ total_count: 2 }], [hitRow("person", 1), hitRow("person", 2)]);
    const input = { q: "result", type: "person" as const, mode: "page" as const, limit: 1 };
    const initial = await searchPublic(input, mint.client);
    for (const changes of [{ v: 1 }, { fp: "stale" }, { sort: "time" }, { rank: -1 }, { rank: 1 }, { rank: 1001 }, { rank: 1.5 }, { tie: null }, { tie: "a".repeat(81) }]) {
      const db = fakeClient();
      const cursor = withCursorPayload(initial.groups.person.page.next_cursor!, changes);
      await expect(searchPublic({ ...input, cursor }, db.client)).rejects.toBeInstanceOf(InvalidCursorError);
      expect(db.query).not.toHaveBeenCalled();
    }
  });

  it("validates cursor IDs before the no-token early return", async () => {
    const input = { q: "!!!", type: "person" as const, mode: "page" as const, limit: 1 };
    const prepared = prepareSearchText(input.q);
    const fp = createHash("sha256").update(JSON.stringify({
      q: prepared.normalized, tokens: prepared.tokens, type: input.type,
      topic: null, person: null, statement_type: null, from: null, to: null,
    })).digest("hex").slice(0, 16);
    const valid = Buffer.from(JSON.stringify({ v: 2, fp, rank: 0, tie: "", id: EMPTY_CURSOR_ID, sort: "name" })).toString("base64url");
    const db = fakeClient();
    const pool = fakePool(db.client);
    for (const { label, id } of MALFORMED_CURSOR_IDS) {
      const cursor = withCursorPayload(valid, { id });
      await expect(searchPublic({ ...input, cursor }, pool.pool), label).rejects.toBeInstanceOf(InvalidCursorError);
    }
    const result = await searchPublic({ ...input, cursor: valid }, pool.pool);
    expect(result.query.reason).toBe("no_tokens");
    expect(pool.connect).not.toHaveBeenCalled();
    expect(pool.query).not.toHaveBeenCalled();
    expect(db.query).not.toHaveBeenCalled();
    expect(db.release).not.toHaveBeenCalled();
  });

  it.each([false, true])("propagates count failures rather than returning empty (timeout=%s)", async (timeout) => {
    const error = Object.assign(new Error("count failed"), { code: timeout ? "57014" : "XX000" });
    const db = fakeClient(error);
    const pending = searchPublic({ q: "result", type: "statement", mode: "page" }, db.client);

    if (timeout) await expect(pending).rejects.toBeInstanceOf(SearchTimeoutError);
    else await expect(pending).rejects.toBe(error);
    expect(db.query).toHaveBeenCalledTimes(1);
    expectCount(db.query.mock.calls[0]!);
    expect(db.release).not.toHaveBeenCalled();
  });
});

describe("search snapshot lifecycle", () => {
  function expectSnapshotStart(calls: QueryCall[]) {
    expect(calls[0]).toEqual(["BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"]);
    expect(calls[1]![0]).toContain("set_config('statement_timeout', '15s', true)");
    expect(calls[1]![0]).toContain("set_config('lock_timeout', '2s', true)");
    expect(calls[1]![0]).toContain("set_config('idle_in_transaction_session_timeout', '15s', true)");
    expect(calls[2]).toEqual(["SET LOCAL statement_timeout = '2s'"]);
  }

  it.each([0, 1])("commits and releases the same snapshot client after a total of %s", async (total) => {
    const replies: Reply[] = [[], [], [], [{ total_count: total }]];
    if (total > 0) replies.push([hitRow("statement", 1)]);
    replies.push([]);
    const db = fakeClient(...replies);
    const pool = fakePool(db.client);
    const result = await searchPublic({ q: "result", type: "statement", mode: "page" }, pool.pool);

    expect(pool.connect).toHaveBeenCalledTimes(1);
    expect(pool.query).not.toHaveBeenCalled();
    expectSnapshotStart(db.query.mock.calls);
    expectCount(db.query.mock.calls[3]!);
    if (total > 0) expectSharedRelation(db.query.mock.calls[3]!, db.query.mock.calls[4]!);
    expect(db.query).toHaveBeenCalledTimes(total === 0 ? 5 : 6);
    expect(db.query.mock.calls.at(-1)).toEqual(["COMMIT"]);
    expect(result.groups.statement.page.total).toBe(total);
    expect(db.release).toHaveBeenCalledTimes(1);
  });

  it.each([
    { stage: "count", timeout: false },
    { stage: "count", timeout: true },
    { stage: "page", timeout: false },
    { stage: "page", timeout: true },
  ])("rolls back and releases after a $stage failure (timeout=$timeout)", async ({ stage, timeout }) => {
    const error = Object.assign(new Error(`${stage} failed`), { code: timeout ? "57014" : "XX000" });
    const replies: Reply[] = [[], [], []];
    if (stage === "page") replies.push([{ total_count: 1 }]);
    replies.push(error, []);
    const db = fakeClient(...replies);
    const pool = fakePool(db.client);
    const pending = searchPublic({ q: "result", type: "statement", mode: "page" }, pool.pool);

    if (timeout) await expect(pending).rejects.toBeInstanceOf(SearchTimeoutError);
    else await expect(pending).rejects.toBe(error);
    expectSnapshotStart(db.query.mock.calls);
    expect(db.query).toHaveBeenCalledTimes(stage === "count" ? 5 : 6);
    expect(db.query.mock.calls.at(-1)).toEqual(["ROLLBACK"]);
    expect(db.query.mock.calls.some(([sql]) => sql === "COMMIT")).toBe(false);
    expect(pool.connect).toHaveBeenCalledTimes(1);
    expect(pool.query).not.toHaveBeenCalled();
    expect(db.release).toHaveBeenCalledTimes(1);
  });

  it("preserves the count error and releases even if rollback fails", async () => {
    const error = new Error("count failed");
    const db = fakeClient([], [], [], error, new Error("connection lost during rollback"));
    const pool = fakePool(db.client);

    await expect(searchPublic({ q: "result", type: "statement", mode: "page" }, pool.pool)).rejects.toBe(error);
    expect(db.query).toHaveBeenCalledTimes(5);
    expect(db.query.mock.calls.at(-1)).toEqual(["ROLLBACK"]);
    expect(db.release).toHaveBeenCalledTimes(1);
  });

  it.each(SEARCH_ENTITY_TYPES)("rejects malformed %s cursor IDs before pool checkout", async (type) => {
    const mint = fakeClient([{ total_count: 2 }], [hitRow(type, 1), hitRow(type, 2)]);
    const input = { q: "result", type, mode: "page" as const, limit: 1 };
    const initial = await searchPublic(input, mint.client);
    for (const { label, id } of MALFORMED_CURSOR_IDS) {
      const db = fakeClient();
      const pool = fakePool(db.client);
      const cursor = withCursorPayload(initial.groups[type].page.next_cursor!, { id });
      await expect(searchPublic({ ...input, cursor }, pool.pool), label).rejects.toBeInstanceOf(InvalidCursorError);
      expect(pool.connect, label).not.toHaveBeenCalled();
      expect(pool.query, label).not.toHaveBeenCalled();
      expect(db.query, label).not.toHaveBeenCalled();
      expect(db.release, label).not.toHaveBeenCalled();
    }
  });
});
