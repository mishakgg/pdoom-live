import { readFileSync } from "node:fs";
import { SEARCH_SUGGEST_LIMITS } from "@pdoom/contracts";
import { listStatements } from "../packages/db/src/queries";
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
    expect(slugs(found.groups.statement.data)).toEqual(["searchfix-unreviewed"]);
    const listed = await listStatements({ q: "UNREVIEWED_CANONICAL_PHRASE", limit: 5 }, pool);
    expect(listed.data.map((row) => row.slug)).toContain("searchfix-unreviewed");
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
