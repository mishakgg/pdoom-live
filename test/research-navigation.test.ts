import { describe, expect, it } from "vitest";
import { optionsFromSearch } from "../apps/web/lib/entity-options";
import {
  collectionReading,
  datasetFingerprint,
  fingerprintFromOverview,
  historyPreview,
  personResearchHref,
  revisionReading,
  selectCoveredTopics,
  selectFeaturedQuestion,
  statementsHref,
  timeRelation,
  topicResearchHref,
  withResearch,
} from "../apps/web/lib/presentation";
import type { SearchResponse } from "@pdoom/contracts";

describe("research navigation", () => {
  it("keeps person and topic together and can clear one filter", () => {
    const filters = {
      person: "ada-quill",
      topic: "ai-extinction",
      from: "2020-01-01",
      statement_type: "explicit_numeric",
      review_state: "human_verified",
    };
    expect(statementsHref(filters)).toBe(
      "/statements?person=ada-quill&topic=ai-extinction&statement_type=explicit_numeric&review_state=human_verified&from=2020-01-01",
    );
    expect(personResearchHref("ada-quill", filters)).toBe(
      "/people/ada-quill?topic=ai-extinction&statement_type=explicit_numeric&review_state=human_verified&from=2020-01-01",
    );
    expect(topicResearchHref("ai-extinction", filters)).toBe(
      "/topics/ai-extinction?person=ada-quill&statement_type=explicit_numeric&review_state=human_verified&from=2020-01-01",
    );
    expect(withResearch("/statements", filters, { topic: null })).toBe(
      "/statements?person=ada-quill&statement_type=explicit_numeric&review_state=human_verified&from=2020-01-01",
    );
    expect(withResearch("/statements", {}, {})).toBe("/statements");
  });

  it("calls a capped profile a preview and a full list complete", () => {
    expect(historyPreview(0, 0).tone).toBe("empty");
    expect(historyPreview(4, 4).summary).toMatch(/All 4 public statements/);
    const preview = historyPreview(50, 80);
    expect(preview.tone).toBe("preview");
    expect(preview.summary).toMatch(/50 of 80/);
    expect(preview.summary).toMatch(/not the complete history/);
    expect(preview.summary).toMatch(/30 older statements/);
  });

  it("features the widest comparable question instead of a fixed example slug", () => {
    const ranked = selectFeaturedQuestion([
      {
        slug: "extinction-by-2070-distribution",
        name: "Extinction",
        kind: "distribution",
        contributing_person_count: 1,
        contributing_statement_count: 1,
        calculated_at: "2026-01-01T00:00:00.000Z",
      },
      {
        slug: "statement-volume-by-topic-type",
        name: "Volume",
        kind: "volume",
        contributing_person_count: 9,
        contributing_statement_count: 40,
        calculated_at: "2026-02-01T00:00:00.000Z",
      },
      {
        slug: "coding-automation-share-by-2028",
        name: "Coding automation",
        kind: "quantity",
        contributing_person_count: 3,
        contributing_statement_count: 3,
        calculated_at: "2026-01-02T00:00:00.000Z",
      },
    ]);
    expect(ranked.featured?.slug).toBe("coding-automation-share-by-2028");
    expect(ranked.others.map((trend) => trend.slug)).toEqual([
      "extinction-by-2070-distribution",
      "statement-volume-by-topic-type",
    ]);
  });

  it("orders covered topics by statement count and then name", () => {
    const topics = selectCoveredTopics([
      { slug: "b", name: "Beta", statement_total: 2 },
      { slug: "a", name: "Alpha", statement_total: 2 },
      { slug: "c", name: "Gamma", statement_total: 0 },
      { slug: "d", name: "Delta", statement_total: 5 },
    ]);
    expect(topics.map((topic) => topic.slug)).toEqual(["d", "a", "b"]);
  });

  it("separates a recorded change from a repetition and from collection time", () => {
    expect(revisionReading("updates").title).toBe("Recorded change of view");
    expect(revisionReading("repeats").note).toMatch(/not a change of view/);
    expect(revisionReading("updates").note).not.toMatch(/overall belief score$/);
    expect(timeRelation({ published_at: null, observed_at: null }).label).toBe("Times unknown");
    expect(timeRelation({ published_at: "2020-01-01T00:00:00.000Z", observed_at: "2024-01-01T00:00:00.000Z" }).label).toBe(
      "Collected after publication",
    );
    expect(timeRelation({ published_at: "2024-01-01T00:00:00.000Z", observed_at: null }).label).toBe("Observation unknown");
    expect(collectionReading({ last_success_at: null, last_checked_at: "2024-01-01T00:00:00.000Z", freshness: "never_checked" }).label).toBe(
      "Check failed",
    );
    expect(collectionReading({ last_success_at: null, last_checked_at: null, freshness: "never_checked" }).label).toBe("Never checked");
  });

  it("builds a stable dataset fingerprint from stored clocks", () => {
    const fingerprint = datasetFingerprint({
      imported_at: "2026-01-01T00:00:00.000Z",
      statement_count: 4,
      latest_observed_at: null,
      latest_published_at: "2025-01-01T00:00:00.000Z",
      latest_successful_observation: "2026-01-02T00:00:00.000Z",
      stale_sources: 1,
      failing_sources: 0,
    });
    expect(fingerprintFromOverview({
      dataset: {
        imported_at: "2026-01-01T00:00:00.000Z",
        statement_count: 4,
        latest_observed_at: null,
        latest_published_at: "2025-01-01T00:00:00.000Z",
        coverage: { latest_successful_observation: "2026-01-02T00:00:00.000Z", stale_sources: 1, unavailable_or_failing_sources: 0 },
      },
    })).toBe(fingerprint);
    expect(fingerprintFromOverview({ dataset: { statement_count: 5 } })).not.toBe(fingerprint);
  });
});

function searchResponse(people: Array<{ slug: string; display_name: string; organization: string }>): SearchResponse {
  const empty = { data: [], page: { limit: 8, total: 0, next_cursor: null } };
  return {
    query: { text: "kim", normalized: "kim", tokens: ["kim"], truncated: false, reason: "ok", types: ["person"] },
    groups: {
      person: {
        data: people.map((person) => ({
          kind: "person" as const,
          id: person.slug,
          slug: person.slug,
          display_name: person.display_name,
          status: "active",
          organization: { slug: "lab", name: person.organization, role: "Researcher" },
          match: "exact_name" as const,
        })),
        page: { limit: 8, total: people.length, next_cursor: null },
      },
      organization: empty,
      statement: empty,
      topic: empty,
      source: empty,
      source_item: empty,
    },
  };
}

describe("entity option names", () => {
  it("distinguishes two people who share a display name", () => {
    const options = optionsFromSearch("person", searchResponse([
      { slug: "alex-kim-north", display_name: "Alex Kim", organization: "North Lab" },
      { slug: "alex-kim-south", display_name: "Alex Kim", organization: "South Lab" },
    ]));
    expect(options).toHaveLength(2);
    expect(options[0]?.accessible).not.toBe(options[1]?.accessible);
    expect(options[0]?.detail).toMatch(/North Lab/);
    expect(options[0]?.detail).toMatch(/alex-kim-north/);
    expect(options[1]?.detail).toMatch(/South Lab/);
    expect(options[1]?.detail).toMatch(/alex-kim-south/);
  });
});
