import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { SEARCH_ENTITY_TYPES, SEARCH_RANK, SEARCH_SUGGEST_LIMITS, prepareSearchText, type SearchEntityType } from "@pdoom/contracts";
import { counterSnapshot } from "@pdoom/observability";
import { InvalidCursorError, listStatements } from "../packages/db/src/queries";
import { createPool } from "../packages/db/src/pool";
import { searchPublic } from "../packages/db/src/search";
import { GET as searchRoute } from "../apps/web/app/api/search/route";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { clearSearchFixture, seedSearchFixture } from "./search-fixture";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");

type RankingCase = {
  id: string;
  q: string;
  person?: string[];
  person_match?: string[];
  organization?: string[];
  organization_match?: string[];
  statement?: string[];
  statement_match?: string[];
  statement_type?: string[];
  statement_prefix?: string[];
  topic?: string[];
  topic_match?: string[];
  source?: string[];
  source_match?: string[];
  source_item?: string[];
  source_item_match?: string[];
};

const ranking = JSON.parse(readFileSync("data/fixtures/search/expected-ranking.json", "utf8")) as { cases: RankingCase[] };

beforeAll(async () => {
  await seedSearchFixture(pool);
});

afterAll(async () => {
  await clearSearchFixture(pool);
  await pool.end();
});

function slugs(rows: Array<{ slug: string }>): string[] {
  return rows.map((row) => row.slug);
}

describe("search ranking fixtures", () => {
  it.each(ranking.cases)("$id", async (expected) => {
    const result = await searchPublic({ q: expected.q, limit: 20 }, pool);
    if (expected.person) expect(slugs(result.groups.person.data)).toEqual(expected.person);
    if (expected.person_match) expect(result.groups.person.data.map((row) => row.match)).toEqual(expected.person_match);
    if (expected.organization) expect(slugs(result.groups.organization.data)).toEqual(expected.organization);
    if (expected.organization_match) {
      expect(result.groups.organization.data.map((row) => row.match)).toEqual(expected.organization_match);
    }
    if (expected.statement) expect(slugs(result.groups.statement.data)).toEqual(expected.statement);
    if (expected.statement_match) expect(result.groups.statement.data.map((row) => row.match)).toEqual(expected.statement_match);
    if (expected.statement_type) {
      expect(result.groups.statement.data.map((row) => row.statement_type)).toEqual(expected.statement_type);
    }
    if (expected.statement_prefix) {
      expect(slugs(result.groups.statement.data).slice(0, expected.statement_prefix.length)).toEqual(expected.statement_prefix);
    }
    if (expected.topic) expect(slugs(result.groups.topic.data)).toEqual(expected.topic);
    if (expected.topic_match) expect(result.groups.topic.data.map((row) => row.match)).toEqual(expected.topic_match);
    if (expected.source) expect(slugs(result.groups.source.data)).toEqual(expected.source);
    if (expected.source_match) expect(result.groups.source.data.map((row) => row.match)).toEqual(expected.source_match);
    if (expected.source_item) expect(slugs(result.groups.source_item.data)).toEqual(expected.source_item);
    if (expected.source_item_match) {
      expect(result.groups.source_item.data.map((row) => row.match)).toEqual(expected.source_item_match);
    }
    expect(JSON.stringify(result)).not.toContain("verification_detail");
    expect(JSON.stringify(result)).not.toContain("rights_notes");
    expect(JSON.stringify(result)).not.toContain("PRIVATE_REVIEW_NOTE_9f3a");
    expect(JSON.stringify(result)).not.toContain("REJECTED_SECRET_PHRASE");
    for (const group of Object.values(result.groups)) {
      for (const row of group.data) {
        expect(row).not.toHaveProperty("rank");
        expect(row).not.toHaveProperty("hit_rank");
      }
    }
  });
});

describe("search publication boundary", () => {
  it("keeps machine_validated labeled and needs_review visible, and hides rejected rows", async () => {
    const ada = await searchPublic({ q: "Ada Quill", limit: 20 }, pool);
    const inferred = ada.groups.statement.data.find((row) => row.slug === "ada-inferred-2024");
    expect(inferred?.review_state).toBe("machine_validated");
    expect(inferred?.statement_type).toBe("model_inferred_signal");
    const extinction = await searchPublic({ q: "extinction", type: "statement", limit: 20 }, pool);
    expect(extinction.groups.statement.data.find((row) => row.slug === "jonah-extinction-review-2024")?.review_state).toBe("needs_review");
    const rejected = await searchPublic({ q: "REJECTED_SECRET_PHRASE", limit: 20 }, pool);
    expect(rejected.groups.statement.page.total).toBe(0);
    const listed = await listStatements({ q: "REJECTED_SECRET_PHRASE", limit: 20 }, pool);
    expect(listed.page.total).toBe(0);
  });

  it("follows the statement list for unreviewed canonical rows and ignores pipeline candidates", async () => {
    const found = await searchPublic({ q: "UNREVIEWED_CANONICAL_PHRASE", limit: 5 }, pool);
    expect(found.groups.statement.page.total).toBe(0);
    const listed = await listStatements({ q: "UNREVIEWED_CANONICAL_PHRASE", limit: 5 }, pool);
    expect(listed.data.map((row) => row.slug)).not.toContain("searchfix-unreviewed");
    const candidate = await searchPublic({ q: "exploits flaws or ambiguities in the reward function", limit: 5 }, pool);
    const body = JSON.stringify(candidate);
    expect(candidate.groups.statement.page.total).toBe(0);
    expect(body).not.toContain("lilianweng");
    expect(body).not.toContain("Reward hacking occurs");
    const ambiguity = await searchPublic({ q: "A5007218744", limit: 5 }, pool);
    expect(JSON.stringify(ambiguity)).not.toContain("Egyptian Petroleum");
    expect(Object.values(ambiguity.groups).every((group) => group.page.total === 0)).toBe(true);
  });

  it("does not search evidence, metadata, or private notes", async () => {
    const source = readFileSync("packages/db/src/search.ts", "utf8");
    for (const forbidden of ["evidence_segments", "verification_detail", "rights_notes", "metadata_json", "candidate_statements", "ambiguities.jsonl"]) {
      expect(source).not.toContain(forbidden);
    }
    const hostile = await searchPublic({ q: "Ignore previous instructions", limit: 10 }, pool);
    const body = JSON.stringify(hostile);
    expect(body).not.toContain("<script>");
    expect(body).not.toContain("Exfiltrate");
    expect(body).not.toContain("UNIQUE_BODY_MARKER");
    const note = await searchPublic({ q: "PRIVATE_REVIEW_NOTE_9f3a", limit: 10 }, pool);
    expect(Object.values(note.groups).every((group) => group.page.total === 0)).toBe(true);
    const role = await searchPublic({ q: "Searchfix private role", limit: 5 }, pool);
    expect(slugs(role.groups.organization.data)).toEqual(["searchfix-org"]);
    expect(JSON.stringify(role)).not.toContain("PRIVATE_REVIEW_NOTE_9f3a");
    expect(JSON.stringify(role)).not.toContain("SHOULD_NOT_LEAK_NOTE");
    const rejectedRole = await searchPublic({ q: "REJECTED_ROLE_SECRET", limit: 5 }, pool);
    expect(rejectedRole.groups.organization.page.total).toBe(0);
  });
});

describe("search filters and pagination", () => {
  it("paginates statements in the recorded order without duplicates", async () => {
    const expected = ranking.cases.find((item) => item.id === "extinction");
    const seen: string[] = [];
    let cursor: string | undefined;
    for (let page = 0; page < 8; page += 1) {
      const result = await searchPublic({ q: "extinction", type: "statement", limit: 2, cursor }, pool);
      expect(result.groups.statement.page.total).toBe(expected?.statement?.length);
      seen.push(...slugs(result.groups.statement.data));
      cursor = result.groups.statement.page.next_cursor ?? undefined;
      if (!cursor) break;
    }
    expect(seen).toEqual(expected?.statement);
    expect(new Set(seen).size).toBe(seen.length);
  });

  it("filters by entity, person, topic, class, and date", async () => {
    const people = await searchPublic({ q: "Okonkwo", type: "person", limit: 10 }, pool);
    expect(slugs(people.groups.person.data)).toEqual(["samir-okonkwo", "samira-okonkwo"]);
    expect(people.groups.statement.page.total).toBe(0);
    expect(people.groups.source.page.total).toBe(0);
    const ada = await searchPublic({ q: "extinction", person: "ada-quill", limit: 20 }, pool);
    expect(slugs(ada.groups.statement.data)).toEqual(["ada-extinction-2025", "ada-extinction-2023"]);
    const topic = await searchPublic({ q: "extinction", topic: "ai-extinction", type: "statement", limit: 20 }, pool);
    expect(topic.groups.statement.data.every((row) => row.topics.some((item) => item.slug === "ai-extinction"))).toBe(true);
    expect(slugs(topic.groups.statement.data)).not.toContain("jonah-catastrophe-2022");
    const qualitative = await searchPublic({ q: "extinction", statement_type: "explicit_qualitative", limit: 20 }, pool);
    expect(qualitative.groups.statement.page.total).toBe(0);
    expect(qualitative.groups.person.page.total).toBe(0);
    const year = await searchPublic({ q: "extinction", type: "statement", from: "2025-01-01", to: "2025-12-31", limit: 20 }, pool);
    expect(slugs(year.groups.statement.data)).toEqual([
      "jonah-extinction-no-horizon-2025",
      "noah-extinction-range-2025",
      "ada-extinction-2025",
    ]);
  });

  it("bounds suggest results", async () => {
    const result = await searchPublic({ q: "extinction", mode: "suggest" }, pool);
    expect(result.groups.statement.data.length).toBeLessThanOrEqual(SEARCH_SUGGEST_LIMITS.statement);
    expect(result.groups.statement.page.total).toBeGreaterThan(SEARCH_SUGGEST_LIMITS.statement);
    expect(result.groups.topic.data.length).toBeLessThanOrEqual(SEARCH_SUGGEST_LIMITS.topic);
  });
});

const groupedPaginationCases = [
  { type: "person", q: "Okonkwo", expected: ["samir-okonkwo", "samira-okonkwo"] },
  { type: "organization", q: "lead", expected: ["brightpath-robotics", "northwind-alignment-lab"] },
  { type: "statement", q: "extinction", expected: ranking.cases.find((item) => item.id === "extinction")!.statement! },
  { type: "topic", q: "extinction", expected: ["ai-extinction", "ai-catastrophic-harm", "labor-displacement"] },
  { type: "source", q: "Harbor", expected: ["harbor-blog", "harbor-papers", "harbor-video"] },
  { type: "source_item", q: "labor", expected: ["lumen-paper-2025", "samira-letter-2024"] },
] as const;

describe("untyped group continuation on PostgreSQL", () => {
  it.each(groupedPaginationCases)("continues $type with stable totals and exact order", async ({ type, q, expected }) => {
    const initial = await searchPublic({ q, limit: 1 }, pool);
    const typed = await searchPublic({ q, type, limit: 1 }, pool);
    expect(initial.query.types).toEqual(SEARCH_ENTITY_TYPES);
    expect(initial.groups[type]).toEqual(typed.groups[type]);
    expect(initial.groups[type].page.next_cursor).toEqual(expect.any(String));
    const seen = slugs(initial.groups[type].data);
    let cursor = initial.groups[type].page.next_cursor;
    for (let page = 1; page < expected.length && cursor; page += 1) {
      const result = await searchPublic({ q, type, limit: 1, cursor }, pool);
      const group = result.groups[type];
      expect(group.page.total).toBe(expected.length);
      expect(group.data).toHaveLength(1);
      expect(seen).not.toContain(group.data[0]!.slug);
      seen.push(...slugs(group.data));
      cursor = group.page.next_cursor;
    }
    expect(initial.groups[type].page.total).toBe(expected.length);
    expect(cursor).toBeNull();
    expect(seen).toEqual(expected);
    expect(new Set(seen).size).toBe(seen.length);
  });

  it("continues a normalized Unicode query narrowed to statements by all filters", async () => {
    const input = {
      q: "  ＥＸＴＩＮＣＴＩＯＮ\u200B　\t ", person: "ada-quill", topic: "ai-extinction",
      statement_type: "explicit_numeric" as const, from: "2020-01-01", to: "2026-12-31", limit: 1,
    };
    const initial = await searchPublic(input, pool);
    expect(initial.query.normalized).toBe("extinction");
    expect(initial.query.types).toEqual(["statement"]);
    expect(slugs(initial.groups.statement.data)).toEqual(["ada-extinction-2025"]);
    const cursor = initial.groups.statement.page.next_cursor;
    expect(cursor).toEqual(expect.any(String));
    const next = await searchPublic({ ...input, q: "extinction", type: "statement", cursor: cursor! }, pool);
    expect(slugs(next.groups.statement.data)).toEqual(["ada-extinction-2023"]);
    expect(next.groups.statement.page).toEqual({ limit: 1, total: initial.groups.statement.page.total, next_cursor: null });
    expect(next.groups.statement.page.total).toBe(2);
    for (const changes of [{ q: "risk" }, { person: "jonah-hale" }, { topic: "ai-catastrophic-harm" }, { statement_type: "explicit_qualitative" as const }, { from: "2021-01-01" }, { to: "2025-12-31" }]) {
      const before = searchDbQueryCount();
      await expect(searchPublic({ ...input, ...changes, type: "statement", cursor: cursor! }, pool)).rejects.toBeInstanceOf(InvalidCursorError);
      expect(searchDbQueryCount() - before).toBe(0);
    }
  });

  it("normalizes multiword fullwidth text and whitespace across group continuation", async () => {
    const initial = await searchPublic({ q: " Ｓｅａｒｃｈ\u200B　\tＦｉｘｔｕｒｅ ", limit: 1 }, pool);
    expect(slugs(initial.groups.person.data)).toEqual(["searchfix-other"]);
    const cursor = initial.groups.person.page.next_cursor;
    expect(cursor).toEqual(expect.any(String));
    const next = await searchPublic({ q: "search fixture", type: "person", limit: 1, cursor: cursor! }, pool);
    expect(slugs(next.groups.person.data)).toEqual(["searchfix-speaker"]);
    expect(next.groups.person.page).toEqual({ limit: 1, total: 2, next_cursor: null });
  });

  it("continues actual API group cursors and rejects same-sort wrong groups", async () => {
    const response = await searchRoute(new Request("http://localhost/api/search?q=extinction&limit=1"));
    expect(response.status).toBe(200);
    const initial = await response.json();
    for (const type of ["statement", "topic"] as const) {
      const cursor = initial.groups[type].page.next_cursor as string;
      expect(cursor).toEqual(expect.any(String));
      const params = new URLSearchParams({ q: "extinction", type, limit: "1", cursor });
      const continued = await searchRoute(new Request(`http://localhost/api/search?${params}`));
      expect(continued.status).toBe(200);
      const result = await continued.json();
      expect(result.groups[type].page.total).toBe(initial.groups[type].page.total);
      expect(result.groups[type].data[0].id).not.toBe(initial.groups[type].data[0].id);
      params.set("type", type === "statement" ? "source_item" : "source");
      const wrong = await searchRoute(new Request(`http://localhost/api/search?${params}`));
      expect(wrong.status).toBe(400);
      expect(await wrong.json()).toEqual({ error: { code: "invalid_cursor", message: "Cursor is invalid." } });
    }
  });
});

describe("search query safety", () => {
  it("rejects empty, oversized, and incompatible queries", async () => {
    const cases = [
      "/api/search",
      "/api/search?q=",
      "/api/search?q=%20%20",
      `/api/search?q=${"a".repeat(201)}`,
      "/api/search?q=ada&limit=0",
      "/api/search?q=ada&limit=21",
      "/api/search?q=ada&type=ideology",
      "/api/search?q=ada&statement_type=sentiment",
      "/api/search?q=ada&from=yesterday",
      "/api/search?q=ada&from=2025-02-01&to=2024-01-01",
      "/api/search?q=ada&cursor=not-a-cursor",
      "/api/search?q=ada&type=person&statement_type=explicit_numeric",
      "/api/search?q=ada&q=quill",
    ];
    for (const path of cases) {
      const response = await searchRoute(new Request(`http://localhost${path}`));
      expect(response.status, path).toBe(400);
    }
  });

  it("accepts punctuation, unicode, and injection-shaped text as data", async () => {
    const punctuation = await searchRoute(new Request("http://localhost/api/search?q=!!!"));
    expect(punctuation.status).toBe(200);
    const punctuationBody = await punctuation.json();
    expect(punctuationBody.query.reason).toBe("no_tokens");
    const wide = await searchPublic({ q: "Ａｄａ　Ｑｕｉｌｌ" }, pool);
    expect(wide.groups.person.data[0]?.slug).toBe("ada-quill");
    expect(wide.groups.person.data[0]?.match).toBe("exact_name");
    const hidden = await searchPublic({ q: "Ada\u200B Quill" }, pool);
    expect(hidden.groups.person.data[0]?.slug).toBe("ada-quill");
    const injection = await searchRoute(new Request("http://localhost/api/search?q=%25'%20OR%201%3D1%20--"));
    expect(injection.status).toBe(200);
    const injected = await injection.json();
    expect(injected.groups.person.page.total).toBeLessThan(9);
    const hostile = await searchRoute(new Request("http://localhost/api/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E"));
    expect(hostile.status).toBe(200);
    const hostileBody = await hostile.json();
    expect(hostileBody.query.text).toBe("<script>alert(1)</script>");
    expect(JSON.stringify(hostileBody.groups)).not.toContain("<script>");
    expect(Object.values(hostileBody.groups).every((group) => (group as { page: { total: number } }).page.total === 0)).toBe(true);
  });
});

function searchDbQueryCount() {
  return counterSnapshot()
    .filter((row) => row.name === "pdoom_db_queries_total")
    .reduce((total, row) => total + row.value, 0);
}

describe("empty search groups on PostgreSQL", () => {
  it.each(SEARCH_ENTITY_TYPES)("skips only the empty %s page", async (type) => {
    const before = searchDbQueryCount();
    const result = await searchPublic({ q: "zzzznoterm9f3a", type, mode: "page", limit: 5 }, pool);
    expect(searchDbQueryCount() - before).toBe(5);
    expect(result.groups[type]).toEqual({ data: [], page: { limit: 5, total: 0, next_cursor: null } });
  });

  it.each([
    { type: "person", q: "Ada Quill" },
    { type: "organization", q: "AGI 2030" },
    { type: "statement", q: "extinction" },
    { type: "topic", q: "extinction" },
    { type: "source", q: "Harbor Compute notes" },
    { type: "source_item", q: "Fictional labor paper" },
  ] as const)("retains count and page for nonempty $type results", async ({ type, q }) => {
    const before = searchDbQueryCount();
    const result = await searchPublic({ q, type, mode: "page", limit: 5 }, pool);
    expect(searchDbQueryCount() - before).toBe(6);
    expect(result.groups[type].page.total).toBeGreaterThan(0);
    expect(result.groups[type].data.length).toBeGreaterThan(0);
  });

  it.each([
    { type: "person", q: "Ada Quill", person: "searchfix-missing" },
    { type: "statement", q: "AGI 2030", person: "searchfix-other" },
    { type: "topic", q: "extinction", topic: "searchfix-missing" },
    { type: "source", q: "AGI 2030", person: "searchfix-other" },
    { type: "source_item", q: "AGI 2030", person: "searchfix-other" },
  ] as const)("counts with the existing $type filters before skipping its page", async (query) => {
    const before = searchDbQueryCount();
    const result = await searchPublic({ ...query, mode: "page", limit: 5 }, pool);
    expect(searchDbQueryCount() - before).toBe(5);
    expect(result.groups[query.type]).toEqual({ data: [], page: { limit: 5, total: 0, next_cursor: null } });
  });

  it.each([
    { type: "statement", q: "REJECTED_SECRET_PHRASE" },
    { type: "statement", q: "UNREVIEWED_CANONICAL_PHRASE" },
    { type: "organization", q: "REJECTED_ROLE_SECRET" },
  ] as const)("keeps private-only $q matches empty", async (query) => {
    const before = searchDbQueryCount();
    const result = await searchPublic({ ...query, mode: "page", limit: 5 }, pool);
    expect(searchDbQueryCount() - before).toBe(5);
    expect(result.groups[query.type]).toEqual({ data: [], page: { limit: 5, total: 0, next_cursor: null } });
  });

  it("keeps every selected count for an untyped no-match request", async () => {
    const before = searchDbQueryCount();
    const result = await searchPublic({ q: "zzzznoterm9f3a", mode: "page", limit: 5 }, pool);
    expect(searchDbQueryCount() - before).toBe(10);
    expect(result.query.types).toEqual(SEARCH_ENTITY_TYPES);
    for (const group of Object.values(result.groups)) {
      expect(group).toEqual({ data: [], page: { limit: 5, total: 0, next_cursor: null } });
    }
  });
});

// Construct the v2 cursor format without mutating the fixture, including queries
// with no matching rows, so both validation and real SQL casts are exercised.
function cursorFor(q: string, type: SearchEntityType, id: unknown): string {
  const prepared = prepareSearchText(q);
  const fp = createHash("sha256").update(JSON.stringify({
    q: prepared.normalized,
    tokens: prepared.tokens,
    type,
    topic: null,
    person: null,
    statement_type: null,
    from: null,
    to: null,
  })).digest("hex").slice(0, 16);
  return Buffer.from(JSON.stringify({
    v: 2,
    fp,
    rank: SEARCH_RANK.all_tokens,
    tie: "",
    id,
    sort: type === "statement" || type === "source_item" ? "time" : "name",
  }), "utf8").toString("base64url");
}

describe("empty search cursor pages on PostgreSQL", () => {
  it.each(["person", "statement"] as const)("retains %s cursor pages for canonical UUID strings", async (type) => {
    const input = { q: "zzzznoterm9f3a", type, mode: "page" as const, limit: 5 };
    for (const id of [
      "00000000-0000-0000-0000-000000000000",
      "abcdefab-cdef-4abc-8def-abcdefabcdef",
      "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF",
      "aBcDeFaB-cDeF-4aBc-8dEf-AbCdEfAbCdEf",
      "ffffffff-ffff-ffff-ffff-ffffffffffff",
      "12345678-1234-0234-0234-123456789abc",
    ]) {
      const before = searchDbQueryCount();
      const result = await searchPublic({ ...input, cursor: cursorFor(input.q, type, id) }, pool);
      expect(searchDbQueryCount() - before).toBe(6);
      expect(result.groups[type]).toEqual({ data: [], page: { limit: 5, total: 0, next_cursor: null } });
    }
  });

  it.each(SEARCH_ENTITY_TYPES)("rejects malformed %s IDs before PostgreSQL even for empty searches", async (type) => {
    const input = { q: "zzzznoterm9f3a", type, mode: "page" as const, limit: 5 };
    const before = searchDbQueryCount();
    await expect(searchPublic({ ...input, cursor: cursorFor(input.q, type, "-".repeat(36)) }, pool)).rejects.toBeInstanceOf(InvalidCursorError);
    expect(searchDbQueryCount() - before).toBe(0);
  });
});

describe("search cursor API errors", () => {
  it.each([
    { type: "person", q: "Ada Quill" },
    { type: "organization", q: "AGI 2030" },
    { type: "statement", q: "extinction" },
    { type: "topic", q: "extinction" },
    { type: "source", q: "Harbor Compute notes" },
    { type: "source_item", q: "Fictional labor paper" },
  ] as const)("returns invalid_cursor for malformed $type IDs with matching and empty queries", async ({ type, q }) => {
    for (const text of [q, "zzzznoterm9f3a", "!!!"]) {
      for (const id of ["-".repeat(36), "a".repeat(36), "000000000-000-0000-0000-000000000000", ["00000000-0000-4000-8000-000000000001"]]) {
        const params = new URLSearchParams({ q: text, type, cursor: cursorFor(text, type, id) });
        const before = searchDbQueryCount();
        const response = await searchRoute(new Request(`http://localhost/api/search?${params}`));
        expect(response.status).toBe(400);
        expect(await response.json()).toEqual({ error: { code: "invalid_cursor", message: "Cursor is invalid." } });
        expect(searchDbQueryCount() - before).toBe(0);
      }
    }
  });

  it("distinguishes an invalid typed cursor from a schema-invalid cursor request", async () => {
    const invalidCursor = await searchRoute(new Request("http://localhost/api/search?q=ada&type=person&cursor=not-a-cursor"));
    expect(invalidCursor.status).toBe(400);
    expect(await invalidCursor.json()).toEqual({ error: { code: "invalid_cursor", message: "Cursor is invalid." } });
    const invalidQuery = await searchRoute(new Request("http://localhost/api/search?q=ada&cursor=not-a-cursor"));
    expect(invalidQuery.status).toBe(400);
    expect(await invalidQuery.json()).toEqual({ error: { code: "invalid_query", message: "Query parameters are invalid." } });
  });
});
