import { PREPARED_TRENDS } from "../packages/db/src/trend-catalog";
import {
  computeHistoricalRevision,
  computeProbabilityDistribution,
  computeQuantityForecast,
  computeTimelineForecast,
  type TrendCandidate,
  type TrendScope,
} from "../packages/db/src/trend-engine";
import { describe, expect, it } from "vitest";

const context = {
  method_version: "trend-class-gate",
  cohort_slug: "class-gate",
  cohort_version: "1",
  cohort_definition: "Fictional people used only to test which statement classes can enter a numeric trend.",
  cohort_size: 7,
};

const EXTINCTION = "ai_extinction_unconditional_by_2070";

function preparedScope(slug: string): TrendScope {
  const method = PREPARED_TRENDS.find((trend) => trend.slug === slug);
  if (!method) throw new Error(slug);
  return {
    ...method.scope,
    statement_types: ["explicit_numeric", "explicit_qualitative", "model_inferred_signal"],
    review_states: ["human_verified", "machine_validated", "needs_review"],
  };
}

function candidate(input: {
  slug: string;
  person: string;
  name: string;
  question_key: string;
  topic: string;
  statement_type?: string;
  review_state?: string;
  forecast_review_state?: string | null;
  value_numeric?: number | null;
  value_text?: string | null;
  unit?: string;
  event_time?: string;
  horizon_text?: string | null;
}): TrendCandidate {
  return {
    statement_slug: input.slug,
    person_slug: input.person,
    display_name: input.name,
    statement_type: input.statement_type ?? "explicit_numeric",
    review_state: input.review_state ?? "human_verified",
    forecast_review_state: input.forecast_review_state === undefined ? "human_verified" : input.forecast_review_state,
    topic_slugs: [input.topic],
    question_key: input.question_key,
    question_text: input.question_key,
    definition_text: null,
    condition_text: null,
    forecast_kind: input.statement_type === "explicit_qualitative" ? "qualitative" : input.statement_type === "model_inferred_signal" ? "classification" : "probability",
    value_type: "point",
    value_numeric: input.value_numeric === undefined ? 0.1 : input.value_numeric,
    value_min: null,
    value_max: null,
    unit: input.unit ?? "probability",
    horizon_text: input.horizon_text === undefined ? "by the stated horizon" : input.horizon_text,
    value_text: input.value_text ?? null,
    event_time: input.event_time ?? "2024-01-01T00:00:00.000Z",
  };
}

function reasonsOf(exclusions: Array<{ statement_slug: string; reason: string }>): Record<string, string> {
  return Object.fromEntries(exclusions.map((item) => [item.statement_slug, item.reason]));
}

describe("numeric trend class gate", () => {
  const scope = preparedScope("extinction-by-2070-distribution");
  const admitted = [
    candidate({ slug: "sable-number", person: "sable-orth", name: "Sable Orth", question_key: EXTINCTION, topic: "ai-extinction", value_numeric: 0, event_time: "2022-01-01T00:00:00.000Z" }),
    candidate({ slug: "remy-number", person: "remy-cho", name: "Remy Cho", question_key: EXTINCTION, topic: "ai-extinction", value_numeric: 0.2, event_time: "2023-01-01T00:00:00.000Z" }),
    candidate({ slug: "nico-number", person: "nico-pell", name: "Nico Pell", question_key: EXTINCTION, topic: "ai-extinction", value_numeric: 0.4, event_time: "2024-01-01T00:00:00.000Z" }),
  ];
  const rejected = [
    candidate({
      slug: "sable-qual",
      person: "sable-orth",
      name: "Sable Orth",
      question_key: EXTINCTION,
      topic: "ai-extinction",
      statement_type: "explicit_qualitative",
      value_numeric: 0.99,
      value_text: "almost certain",
      event_time: "2025-01-01T00:00:00.000Z",
    }),
    candidate({
      slug: "wren-inferred",
      person: "wren-ade",
      name: "Wren Ade",
      question_key: EXTINCTION,
      topic: "ai-extinction",
      statement_type: "model_inferred_signal",
      value_numeric: 0.01,
      event_time: "2024-06-01T00:00:00.000Z",
    }),
    candidate({
      slug: "sable-missing",
      person: "sable-orth",
      name: "Sable Orth",
      question_key: EXTINCTION,
      topic: "ai-extinction",
      value_numeric: null,
      value_text: "50%",
      event_time: "2026-01-01T00:00:00.000Z",
    }),
    candidate({
      slug: "lark-blank",
      person: "lark-benn",
      name: "Lark Benn",
      question_key: EXTINCTION,
      topic: "ai-extinction",
      value_numeric: Number.NaN,
      value_text: "a high chance",
    }),
    candidate({
      slug: "kit-machine",
      person: "kit-osei",
      name: "Kit Osei",
      question_key: EXTINCTION,
      topic: "ai-extinction",
      review_state: "machine_validated",
      forecast_review_state: "machine_validated",
      value_numeric: 0.7,
    }),
    candidate({
      slug: "joss-review",
      person: "joss-mare",
      name: "Joss Mare",
      question_key: EXTINCTION,
      topic: "ai-extinction",
      review_state: "needs_review",
      forecast_review_state: "needs_review",
      value_numeric: 0.5,
    }),
    candidate({
      slug: "joss-forecast",
      person: "joss-mare",
      name: "Joss Mare",
      question_key: EXTINCTION,
      topic: "ai-extinction",
      forecast_review_state: "machine_validated",
      value_numeric: 0.6,
      event_time: "2024-02-01T00:00:00.000Z",
    }),
  ];

  it("admits only explicit numeric human-verified point estimates that already have a number", () => {
    const result = computeProbabilityDistribution({
      ...context,
      question_text: "Unconditional extinction probability by 2070.",
      definition_text: "Literal human extinction. Qualitative wording and model labels stay out of the distribution.",
      scope,
      candidates: [...admitted, ...rejected],
      edges: [],
    });
    expect(result.included.map((item) => item.statement_slug)).toEqual(["sable-number", "remy-number", "nico-number"]);
    expect(result.included.map((item) => item.value_numeric)).toEqual([0, 0.2, 0.4]);
    expect(result.point_count).toBe(3);
    expect(result.median).toBe(0.2);
    expect(result.minimum).toBe(0);
    expect(result.maximum).toBe(0.4);
    expect(result.density).toBe("comparable");
    const reasons = reasonsOf(result.exclusions);
    expect(reasons["sable-qual"]).toBe("statement_type");
    expect(reasons["wren-inferred"]).toBe("statement_type");
    expect(reasons["sable-missing"]).toBe("value_type_not_point");
    expect(reasons["lark-blank"]).toBe("value_type_not_point");
    expect(reasons["kit-machine"]).toBe("review_state");
    expect(reasons["joss-review"]).toBe("review_state");
    expect(reasons["joss-forecast"]).toBe("review_state");
    const serialized = JSON.stringify(result.included);
    expect(serialized).not.toContain("0.99");
    expect(serialized).not.toContain("0.01");
    expect(serialized).not.toContain("0.7");
    expect(serialized).not.toContain("0.5");
    expect(serialized).not.toContain("0.6");
    expect(result.summary_note).toMatch(/not automatically the probability of the event/);
  });

  it("does not invent a median when excluded classes would otherwise fill the summary", () => {
    const sparse = computeProbabilityDistribution({
      ...context,
      question_text: "Unconditional extinction probability by 2070.",
      definition_text: "Two explicit numbers are not a field probability.",
      scope,
      candidates: [admitted[1]!, admitted[2]!, ...rejected],
      edges: [],
    });
    expect(sparse.included.map((item) => item.value_numeric)).toEqual([0.2, 0.4]);
    expect(sparse.median).toBeNull();
    expect(sparse.minimum).toBeNull();
    expect(sparse.maximum).toBeNull();
    expect(sparse.density).toBe("sparse");
    expect(sparse.summary_note).toMatch(/withheld below 3/);

    const empty = computeProbabilityDistribution({
      ...context,
      question_text: "Unconditional extinction probability by 2070.",
      definition_text: "No explicit number is stored.",
      scope,
      candidates: rejected,
      edges: [],
    });
    expect(empty.included).toEqual([]);
    expect(empty.median).toBeNull();
    expect(empty.point_count).toBe(0);
    expect(empty.density).toBe("empty");
    expect(empty.summary_note).not.toMatch(/99%|p\(doom\)|consensus|the frontier believes/i);
    expect(JSON.stringify(empty)).not.toMatch(/"median":0\.99|"value_numeric":0\.99|"value_numeric":0/);
  });

  it("keeps qualitative, inferred, and missing numbers out of timeline, quantity, and revision points", () => {
    const yearScope = preparedScope("agi-arrival-year");
    const years = computeTimelineForecast({
      ...context,
      question_text: "AGI arrival year.",
      definition_text: "A predicted year. A missing year stays absent.",
      scope: yearScope,
      accept_ranges: true,
      candidates: [
        candidate({ slug: "remy-year", person: "remy-cho", name: "Remy Cho", question_key: yearScope.question_key, topic: "agi-arrival", value_numeric: 2035, unit: "year", horizon_text: null }),
        candidate({ slug: "nico-year-missing", person: "nico-pell", name: "Nico Pell", question_key: yearScope.question_key, topic: "agi-arrival", value_numeric: null, value_text: "sometime next decade", unit: "year", horizon_text: null }),
        candidate({ slug: "sable-year-qual", person: "sable-orth", name: "Sable Orth", question_key: yearScope.question_key, topic: "agi-arrival", statement_type: "explicit_qualitative", value_numeric: 2099, unit: "year", horizon_text: null }),
        candidate({ slug: "wren-year-inferred", person: "wren-ade", name: "Wren Ade", question_key: yearScope.question_key, topic: "agi-arrival", statement_type: "model_inferred_signal", value_numeric: 2001, unit: "year", horizon_text: null }),
      ],
      edges: [],
    });
    expect(years.included.map((item) => item.statement_slug)).toEqual(["remy-year"]);
    expect(years.included.map((item) => item.value_numeric)).toEqual([2035]);
    expect(years.median).toBeNull();

    const shareScope = preparedScope("coding-automation-share-by-2028");
    const shares = computeQuantityForecast({
      ...context,
      question_text: "Coding task share.",
      definition_text: "A share. Qualitative wording is not converted into a share.",
      scope: shareScope,
      accept_ranges: true,
      candidates: [
        candidate({ slug: "remy-share", person: "remy-cho", name: "Remy Cho", question_key: shareScope.question_key, topic: "coding-automation", value_numeric: 0.25, unit: "share", horizon_text: "by end of 2028" }),
        candidate({ slug: "nico-share-missing", person: "nico-pell", name: "Nico Pell", question_key: shareScope.question_key, topic: "coding-automation", value_numeric: null, value_text: "most tasks", unit: "share", horizon_text: "by end of 2028" }),
        candidate({ slug: "sable-share-qual", person: "sable-orth", name: "Sable Orth", question_key: shareScope.question_key, topic: "coding-automation", statement_type: "explicit_qualitative", value_numeric: 0.9, unit: "share", horizon_text: "by end of 2028" }),
      ],
      edges: [],
    });
    expect(shares.included.map((item) => item.value_numeric)).toEqual([0.25]);
    expect(shares.median).toBeNull();
    expect(shares.summary_note).not.toMatch(/p\(doom\)|consensus/i);

    const revisionScope = preparedScope("extinction-by-2070-revisions");
    const revision = computeHistoricalRevision({
      ...context,
      question_text: "Extinction revisions.",
      definition_text: "Only explicit numbers with a verified link are points.",
      scope: revisionScope,
      relationship_types: ["updates", "retracts"],
      candidates: [
        candidate({ slug: "sable-old", person: "sable-orth", name: "Sable Orth", question_key: EXTINCTION, topic: "ai-extinction", value_numeric: 0.08, event_time: "2020-01-01T00:00:00.000Z" }),
        candidate({ slug: "sable-new", person: "sable-orth", name: "Sable Orth", question_key: EXTINCTION, topic: "ai-extinction", value_numeric: 0.12, event_time: "2024-01-01T00:00:00.000Z" }),
        candidate({ slug: "sable-gap", person: "sable-orth", name: "Sable Orth", question_key: EXTINCTION, topic: "ai-extinction", value_numeric: null, value_text: "higher now", event_time: "2023-01-01T00:00:00.000Z" }),
        candidate({ slug: "sable-note", person: "sable-orth", name: "Sable Orth", question_key: EXTINCTION, topic: "ai-extinction", statement_type: "explicit_qualitative", value_numeric: 0.99, event_time: "2025-01-01T00:00:00.000Z" }),
        candidate({ slug: "sable-label", person: "sable-orth", name: "Sable Orth", question_key: EXTINCTION, topic: "ai-extinction", statement_type: "model_inferred_signal", value_numeric: 0.01, event_time: "2021-01-01T00:00:00.000Z" }),
      ],
      edges: [
        { from_statement_slug: "sable-old", to_statement_slug: "sable-new", relationship_type: "updates", review_state: "human_verified", method: "fixture_verified_update" },
        { from_statement_slug: "sable-gap", to_statement_slug: "sable-new", relationship_type: "updates", review_state: "human_verified", method: "fixture_missing_number" },
        { from_statement_slug: "sable-note", to_statement_slug: "sable-new", relationship_type: "updates", review_state: "human_verified", method: "fixture_qualitative" },
        { from_statement_slug: "sable-label", to_statement_slug: "sable-old", relationship_type: "updates", review_state: "human_verified", method: "fixture_inferred" },
      ],
    });
    expect(revision.chains).toHaveLength(1);
    expect(revision.chains[0]?.points.map((point) => point.statement_slug)).toEqual(["sable-old", "sable-new"]);
    expect(revision.chains[0]?.points.map((point) => point.value_numeric)).toEqual([0.08, 0.12]);
    expect(revision.chains[0]?.points.map((point) => point.value_numeric)).not.toContain(0);
    expect(reasonsOf(revision.exclusions)["sable-note"]).toBe("statement_type");
    expect(reasonsOf(revision.exclusions)["sable-label"]).toBe("statement_type");
    expect(reasonsOf(revision.exclusions)["sable-gap"]).toBe("value_type_not_point");
  });
});
