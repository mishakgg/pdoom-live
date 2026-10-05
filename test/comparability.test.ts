import { readFileSync } from "node:fs";
import {
  COMPARABILITY_POLICY_VERSION,
  CURRENT_CORPUS_HISTORY,
  FORECAST_RESOLUTION_FIXTURES,
  QUESTION_TAXONOMY,
  assertResolutionFixtures,
  assessResolutionEligibility,
  classifyForecast,
  classifyHistory,
  classifyQuestionKey,
  comparabilityIdentityMaterial,
  comparabilityRegistryDocument,
  comparisonDecision,
  parseDeadline,
  describePreservedValue,
  historyClaimFor,
  prePolicyMethodKey,
  scoreResolvedForecast,
  selectKnownByCutoff,
} from "@pdoom/contracts";
import { PREPARED_TRENDS } from "../packages/db/src/trend-catalog";
import {
  computeHistoricalRevision,
  computeProbabilityDistribution,
  computeQuantityForecast,
  computeTimelineForecast,
  discoverQualitativeGroups,
  discoverQuestionTrends,
  listUnpooledForecasts,
  type TrendCandidate,
} from "../packages/db/src/trend-engine";
import { FORECAST_INPUT_SQL, mapForecastRow, resolveTrendMethods, trendMethodKey } from "../packages/db/src/trend-query";
import { describe, expect, it } from "vitest";

const context = {
  method_version: "comparability-test",
  cohort_slug: "comparability-cases",
  cohort_version: "1",
  cohort_definition: "Deterministic fixtures for exact-question comparisons.",
  cohort_size: 4,
};

function row(input: Partial<TrendCandidate> & Pick<TrendCandidate, "statement_slug" | "question_key">): TrendCandidate {
  return {
    person_slug: input.person_slug ?? "ada-example",
    display_name: input.display_name ?? "Ada Example",
    statement_type: input.statement_type ?? "explicit_numeric",
    review_state: input.review_state ?? "human_verified",
    forecast_review_state: input.forecast_review_state === undefined ? "human_verified" : input.forecast_review_state,
    topic_slugs: input.topic_slugs ?? ["ai-extinction"],
    question_text: input.question_text ?? input.question_key,
    definition_text: input.definition_text ?? null,
    condition_text: input.condition_text ?? null,
    forecast_kind: input.forecast_kind ?? "probability",
    value_type: input.value_type ?? "point",
    value_numeric: input.value_numeric === undefined ? 0.1 : input.value_numeric,
    value_min: input.value_min ?? null,
    value_max: input.value_max ?? null,
    unit: input.unit === undefined ? "probability" : input.unit,
    horizon_text: input.horizon_text === undefined ? null : input.horizon_text,
    target_date_start: input.target_date_start ?? null,
    target_date_end: input.target_date_end ?? null,
    value_text: input.value_text ?? null,
    distribution: input.distribution ?? null,
    probability_semantics: input.probability_semantics ?? null,
    event_time: input.event_time ?? "2024-01-01T00:00:00.000Z",
    statement_slug: input.statement_slug,
    question_key: input.question_key,
  };
}

const extinctionScope = PREPARED_TRENDS.find((trend) => trend.slug === "extinction-by-2070-distribution")!.scope;
const yearScope = PREPARED_TRENDS.find((trend) => trend.slug === "agi-arrival-year")!.scope;

describe("comparability registry", () => {
  it("keeps pipeline keys as families and does not assign them a horizon", () => {
    const source = readFileSync("pipeline/pdoom_pipeline/belief/taxonomy.py", "utf8");
    const block = source.slice(source.indexOf("QUESTION_KEYS"), source.indexOf("TOPICS"));
    const keys = [...block.matchAll(/"([a-z0-9_]+)"/g)].map((match) => match[1] ?? "");
    expect(keys.length).toBeGreaterThan(10);
    for (const key of keys) {
      const entry = classifyQuestionKey(key);
      expect(entry?.role, key).toBe("family");
      expect(entry?.deadline, key).toBeNull();
      expect(entry?.key).toBe(key);
    }
  });

  it("covers curation keys and catalog questions without renaming them", () => {
    for (const question of QUESTION_TAXONOMY) {
      expect(classifyQuestionKey(question.key)?.key).toBe(question.key);
    }
    for (const trend of PREPARED_TRENDS) {
      const entry = classifyQuestionKey(trend.question_key);
      expect(entry?.role).toBe("exact");
      expect(entry?.key).toBe(trend.question_key);
    }
    const document = comparabilityRegistryDocument();
    const committed = JSON.parse(readFileSync("packages/contracts/src/comparability-registry.json", "utf8"));
    expect(committed).toEqual(document);
    expect(document.policy_version).toBe(COMPARABILITY_POLICY_VERSION);
  });

  it("does not map a family key with no deadline onto the 2070 question", () => {
    const missing = classifyForecast({
      question_key: "extinction_unconditional",
      question_text: "Probability of human extinction from AI",
      definition_text: "Literal human extinction",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.2,
    });
    expect(missing.poolable).toBe(false);
    expect(missing.reason).toBe("ambiguous_horizon");
    expect(missing.exact_question_id).not.toBe("ai_extinction_unconditional_by_2070");
    expect(classifyQuestionKey("extinction_unconditional")?.deadline).toBeNull();
    expect(classifyQuestionKey("ai_extinction_unconditional")?.deadline).toBeNull();
  });
});

describe("exact questions", () => {
  it("keeps one person's 2030 and 2050 probabilities as different questions", () => {
    const shared = {
      question_key: "extinction_unconditional",
      question_text: "Probability of human extinction from AI",
      definition_text: "Literal human extinction",
      unit: "probability",
      value_type: "point" as const,
      forecast_kind: "probability",
    };
    const by2030 = classifyForecast({ ...shared, value_numeric: 0.1, target_date_end: "2030-12-31" });
    const by2050 = classifyForecast({ ...shared, value_numeric: 0.4, target_date_end: "2050-12-31" });
    expect(by2030.poolable).toBe(true);
    expect(by2050.poolable).toBe(true);
    expect(by2030.exact_question_id).not.toBe(by2050.exact_question_id);
    expect(by2030.exact_question_id).not.toBe("ai_extinction_unconditional_by_2070");
    expect(by2030.deadline_end).toBe("2030-12-31");
    expect(by2050.deadline_end).toBe("2050-12-31");
    expect(comparabilityIdentityMaterial({ ...shared, target_date_end: "2030-12-31" })).not.toBe(
      comparabilityIdentityMaterial({ ...shared, target_date_end: "2050-12-31" }),
    );

    const early = row({ statement_slug: "ada-2030", question_key: "extinction_unconditional", definition_text: "Literal human extinction", value_numeric: 0.1, target_date_end: "2030-12-31", event_time: "2024-01-01T00:00:00.000Z" });
    const late = row({ statement_slug: "ada-2050", question_key: "extinction_unconditional", definition_text: "Literal human extinction", value_numeric: 0.4, target_date_end: "2050-12-31", event_time: "2025-01-01T00:00:00.000Z" });
    const discovered = discoverQuestionTrends([late, early], new Set(PREPARED_TRENDS.map((trend) => trend.question_key)), new Set());
    expect(discovered).toHaveLength(2);
    const first = computeProbabilityDistribution({ ...context, question_text: discovered[0]!.question_text, definition_text: discovered[0]!.definition_text, scope: discovered[0]!.scope, candidates: [late, early], edges: [{ from_statement_slug: "ada-2030", to_statement_slug: "ada-2050", relationship_type: "updates", review_state: "human_verified", method: "machine_suggested" }] });
    const second = computeProbabilityDistribution({ ...context, question_text: discovered[1]!.question_text, definition_text: discovered[1]!.definition_text, scope: discovered[1]!.scope, candidates: [early, late], edges: [] });
    expect(first.included.map((item) => item.value_numeric)).not.toEqual(second.included.map((item) => item.value_numeric));
    expect(new Set([...first.included, ...second.included].map((item) => item.statement_slug))).toEqual(new Set(["ada-2030", "ada-2050"]));
    const revision = computeHistoricalRevision({
      ...context,
      question_text: discovered[0]!.question_text,
      definition_text: discovered[0]!.definition_text,
      scope: discovered[0]!.scope,
      candidates: [early, late],
      edges: [{ from_statement_slug: "ada-2030", to_statement_slug: "ada-2050", relationship_type: "updates", review_state: "human_verified", method: "different_deadline" }],
      relationship_types: ["updates", "retracts"],
    });
    expect(revision.chains).toEqual([]);
  });

  it("separates conditions and outcome definitions that share a family key", () => {
    const base = {
      question_key: "extinction_unconditional",
      unit: "probability",
      value_type: "point" as const,
      value_numeric: 0.2,
      target_date_end: "2030-12-31",
    };
    const unconditional = classifyForecast({ ...base, definition_text: "Literal human extinction", question_text: "extinction by 2030" });
    const conditional = classifyForecast({ ...base, definition_text: "Literal human extinction", question_text: "extinction by 2030", condition_text: "if frontier labs pause scaling" });
    const catastrophe = classifyForecast({ ...base, question_text: "catastrophic harm", definition_text: "catastrophic harm short of the named outcome" });
    expect(unconditional.exact_question_id).not.toBe(conditional.exact_question_id);
    expect(conditional.conditionality).toBe("conditional");
    expect(catastrophe.poolable).toBe(false);
    expect(catastrophe.reason).toBe("definition_mismatch");
    expect(classifyForecast({
      question_key: "ambiguous_doom",
      question_text: "p(doom)",
      definition_text: "unspecified doom",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.3,
      target_date_end: "2070-12-31",
    }).reason).toBe("insufficient_agreement");
  });

  it("does not pool productivity, GDP, and a vague growth quantity", () => {
    const productivity = classifyForecast({
      question_key: "productivity_growth",
      question_text: "labor productivity growth",
      definition_text: "annual labor productivity growth",
      unit: "percentage_points",
      value_type: "point",
      value_numeric: 2.5,
      target_date_end: "2035-12-31",
    });
    const gdp = classifyForecast({
      question_key: "economic_growth",
      question_text: "GDP growth",
      definition_text: "annual GDP growth",
      unit: "percentage_points",
      value_type: "point",
      value_numeric: 1.5,
      target_date_end: "2035-12-31",
    });
    const vague = classifyForecast({
      question_key: "productivity_growth",
      question_text: "the economy grows",
      definition_text: "growth",
      unit: "percentage_points",
      value_type: "point",
      value_numeric: 3,
      target_date_end: "2035-12-31",
    });
    expect(productivity.exact_question_id).toBe("labor_productivity_growth_pp_by_2035");
    expect(gdp.exact_question_id).toBe("gdp_growth_pp_by_2035");
    expect(vague.poolable).toBe(false);
    expect(vague.reason).toBe("insufficient_agreement");
    expect(comparisonDecision({ question_key: "labor_productivity_growth_pp_by_2035", unit: "percentage_points", horizon_text: "by 2035", value_type: "point", value_numeric: 2.5, definition_text: "labor productivity" }, "gdp_growth_pp_by_2035").reason).toBe("different_question");
  });

  it("joins a family record only when the structured deadline agrees", () => {
    const joined = row({
      statement_slug: "family-2070",
      question_key: "extinction_unconditional",
      question_text: "Unconditional human extinction by 2070",
      definition_text: "Literal human extinction",
      target_date_end: "2070-12-31",
      horizon_text: "by end of 2070",
      value_numeric: 0.11,
    });
    const otherDeadline = row({
      statement_slug: "family-2030",
      question_key: "extinction_unconditional",
      question_text: "Unconditional human extinction by 2030",
      definition_text: "Literal human extinction",
      target_date_end: "2030-12-31",
      value_numeric: 0.33,
    });
    const result = computeProbabilityDistribution({
      ...context,
      question_text: "Unconditional extinction by 2070",
      definition_text: "Literal human extinction by 2070",
      scope: extinctionScope,
      candidates: [otherDeadline, joined],
      edges: [],
    });
    expect(result.included.map((item) => item.statement_slug)).toEqual(["family-2070"]);
    expect(result.included[0]?.stored_question_key).toBe("extinction_unconditional");
    expect(result.exclusions.find((item) => item.statement_slug === "family-2030")?.reason).toBe("deadline_mismatch");
  });

  it("leaves a horizon that names two years ambiguous and unpooled", () => {
    const horizon = "between 2030 and 2050";
    expect(parseDeadline({ horizon_text: horizon })).toEqual({
      status: "ambiguous",
      start: null,
      end: null,
      label: null,
    });

    const span = classifyForecast({
      question_key: "extinction_unconditional",
      question_text: "Probability of human extinction from AI",
      definition_text: "Literal human extinction",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.2,
      horizon_text: horizon,
    });
    expect(span.poolable).toBe(false);
    expect(span.reason).toBe("ambiguous_horizon");
    expect(span.stored_question_key).toBe("extinction_unconditional");
    expect(span.stored_key_is_exact).toBe(false);
    expect(span.deadline_end).toBeNull();
    expect(span.exact_question_id).not.toBe("ai_extinction_unconditional_by_2070");
    expect(comparisonDecision({
      question_key: "extinction_unconditional",
      definition_text: "Literal human extinction",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.2,
      horizon_text: horizon,
    }, "ai_extinction_unconditional_by_2070").reason).toBe("ambiguous_horizon");

    const dated = row({
      statement_slug: "single-2070",
      question_key: "ai_extinction_unconditional_by_2070",
      horizon_text: "by the stated horizon",
      value_numeric: 0.11,
    });
    const spanned = row({
      statement_slug: "two-year-span",
      question_key: "extinction_unconditional",
      definition_text: "Literal human extinction",
      horizon_text: horizon,
      value_numeric: 0.2,
    });
    const distribution = computeProbabilityDistribution({
      ...context,
      question_text: "Unconditional extinction by 2070",
      definition_text: "Literal human extinction by 2070",
      scope: extinctionScope,
      candidates: [spanned, dated],
      edges: [],
    });
    expect(distribution.included.map((item) => item.statement_slug)).toEqual(["single-2070"]);
    expect(distribution.included.map((item) => item.value_numeric)).toEqual([0.11]);
    expect(distribution.exclusions.find((item) => item.statement_slug === "two-year-span")?.reason).toBe("ambiguous_horizon");
    expect(distribution.median).toBeNull();

    const productivity = classifyForecast({
      question_key: "productivity_growth",
      question_text: "labor productivity growth",
      definition_text: "annual labor productivity growth",
      unit: "percentage_points",
      value_type: "point",
      value_numeric: 2.5,
      horizon_text: horizon,
    });
    const gdp = classifyForecast({
      question_key: "economic_growth",
      question_text: "GDP growth",
      definition_text: "annual GDP growth",
      unit: "percentage_points",
      value_type: "point",
      value_numeric: 1.5,
      horizon_text: horizon,
    });
    expect(productivity.reason).toBe("ambiguous_horizon");
    expect(gdp.reason).toBe("ambiguous_horizon");
    expect(productivity.poolable).toBe(false);
    expect(gdp.poolable).toBe(false);
    expect(productivity.stored_question_key).toBe("productivity_growth");
    expect(gdp.stored_question_key).toBe("economic_growth");
    expect(productivity.exact_question_id).not.toBe("labor_productivity_growth_pp_by_2035");
    expect(gdp.exact_question_id).not.toBe("gdp_growth_pp_by_2035");
    const growthRows = [
      row({
        statement_slug: "labor-span",
        question_key: "productivity_growth",
        question_text: "labor productivity growth",
        definition_text: "annual labor productivity growth",
        topic_slugs: ["productivity"],
        unit: "percentage_points",
        value_numeric: 2.5,
        horizon_text: horizon,
      }),
      row({
        statement_slug: "gdp-span",
        question_key: "economic_growth",
        question_text: "GDP growth",
        definition_text: "annual GDP growth",
        topic_slugs: ["productivity"],
        unit: "percentage_points",
        value_numeric: 1.5,
        horizon_text: horizon,
      }),
    ];
    expect(discoverQuestionTrends(growthRows, new Set(), new Set())).toEqual([]);
    const unpooled = listUnpooledForecasts(growthRows, new Set());
    expect(unpooled.map((item) => [item.statement_slug, item.question_key, item.reason])).toEqual([
      ["gdp-span", "economic_growth", "ambiguous_horizon"],
      ["labor-span", "productivity_growth", "ambiguous_horizon"],
    ]);
  });

  it("treats a predicted year as the value and a probability deadline as part of the question", () => {
    const year2032 = classifyForecast({ question_key: "agi_timeline", question_text: "AGI", definition_text: "AGI arrival", unit: "year", value_type: "point", value_numeric: 2032, forecast_kind: "timeline", horizon_text: "2032" });
    const year2040 = classifyForecast({ question_key: "agi_timeline", question_text: "AGI", definition_text: "AGI arrival", unit: "year", value_type: "point", value_numeric: 2040, forecast_kind: "timeline", horizon_text: "2040" });
    expect(year2032.date_role).toBe("predicted_value");
    expect(year2032.exact_question_id).toBe("agi_arrival_calendar_year");
    expect(year2040.exact_question_id).toBe(year2032.exact_question_id);
    const probability2032 = classifyForecast({ question_key: "agi_by_year_probability", definition_text: "AGI", unit: "probability", value_type: "point", value_numeric: 0.4, target_date_end: "2032-12-31" });
    const probability2050 = classifyForecast({ question_key: "agi_by_year_probability", definition_text: "AGI", unit: "probability", value_type: "point", value_numeric: 0.8, target_date_end: "2050-12-31" });
    expect(probability2032.exact_question_id).toBe("agi_arrival_by_2032");
    expect(probability2050.exact_question_id).not.toBe("agi_arrival_by_2032");
    expect(comparisonDecision({ question_key: "agi_by_year_probability", definition_text: "AGI", unit: "probability", value_type: "point", value_numeric: 0.8, target_date_end: "2050-12-31" }, "agi_arrival_by_2032").reason).toBe("deadline_mismatch");

    const years = [2030, 2035, 2040].map((year, index) => row({
      statement_slug: `year-${year}`,
      person_slug: `person-${index}`,
      display_name: `Person ${index}`,
      question_key: "agi_timeline",
      question_text: "AGI arrival",
      definition_text: "AGI arrival",
      topic_slugs: ["agi-timeline"],
      unit: "year",
      forecast_kind: "timeline",
      value_numeric: year,
      horizon_text: String(year),
    }));
    const timeline = computeTimelineForecast({
      ...context,
      question_text: "AGI arrival year",
      definition_text: "A predicted year",
      scope: yearScope,
      candidates: [years[2]!, years[0]!, years[1]!],
      edges: [],
      accept_ranges: true,
    });
    expect(timeline.included.map((item) => item.value_numeric)).toEqual([2030, 2035, 2040]);
    expect(timeline.median).toBe(2035);
    expect(timeline.exact_question_id).toBe("agi_arrival_calendar_year");
  });

  it("preserves ranges, bounds, and quantiles instead of inventing a midpoint", () => {
    const quantiles = describePreservedValue({ value_type: "distribution", distribution: { quantiles: [{ p: 0.1, value: 0.05 }, { p: 0.9, value: 0.4 }], bounds: { lower: 0.05, upper: 0.4, kind: "central" } } });
    expect(quantiles).toContain("p0.1=0.05");
    expect(quantiles).toContain("bounds 0.05–0.4");
    const bound = row({ statement_slug: "bound", question_key: "ai_extinction_unconditional_by_2070", horizon_text: "by the stated horizon", value_text: "at least 10%", value_numeric: 0.1 });
    const range = row({ statement_slug: "range", question_key: "ai_extinction_unconditional_by_2070", horizon_text: "by the stated horizon", value_type: "range", value_numeric: null, value_min: 0.1, value_max: 0.2 });
    const point = row({ statement_slug: "point", question_key: "ai_extinction_unconditional_by_2070", horizon_text: "by the stated horizon", value_numeric: 0.15 });
    const semantics = row({ statement_slug: "event-prob", question_key: "ai_extinction_unconditional_by_2070", horizon_text: "by the stated horizon", probability_semantics: "event_probability", value_numeric: 0.9 });
    const result = computeProbabilityDistribution({
      ...context,
      question_text: "Extinction by 2070",
      definition_text: "Literal human extinction",
      scope: extinctionScope,
      candidates: [semantics, range, bound, point],
      edges: [],
    });
    expect(result.included.map((item) => item.statement_slug)).toEqual(["point"]);
    expect(result.median).toBeNull();
    const reasons = Object.fromEntries(result.exclusions.map((item) => [item.statement_slug, item.reason]));
    expect(reasons.bound).toBe("value_type_not_point");
    expect(reasons.range).toBe("value_type_not_point");
    expect(result.exclusions.find((item) => item.statement_slug === "range")?.preserved_value).toBe("0.1–0.2");
    expect(result.exclusions.find((item) => item.statement_slug === "bound")?.preserved_value).toBe("at least 10%");
    expect(reasons["event-prob"]).not.toBeUndefined();
    expect(result.included.map((item) => item.value_numeric)).not.toContain(0.9);
    expect(result.median_interpretation).toMatch(/not automatically the probability of the event/);
  });
});

describe("revisions and withdrawals", () => {
  const scope = extinctionScope;

  function revision(candidates: TrendCandidate[], edges: Array<{ from: string; to: string; type: string; review?: string; method?: string }>) {
    return computeHistoricalRevision({
      ...context,
      question_text: "Extinction by 2070",
      definition_text: "Literal human extinction",
      scope,
      candidates,
      edges: edges.map((edge) => ({
        from_statement_slug: edge.from,
        to_statement_slug: edge.to,
        relationship_type: edge.type,
        review_state: edge.review ?? "human_verified",
        method: edge.method ?? "fixture",
      })),
      relationship_types: ["updates", "retracts"],
    });
  }

  it("keeps verified updates, repeats, clarifications, contradictions, and withdrawals distinct", () => {
    const earlier = row({ statement_slug: "update-old", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.4, event_time: "2021-01-01T00:00:00.000Z" });
    const later = row({ statement_slug: "update-new", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.15, event_time: "2024-01-01T00:00:00.000Z" });
    const updated = revision([later, earlier], [{ from: "update-old", to: "update-new", type: "updates" }]);
    expect(updated.chains[0]?.links[0]).toMatchObject({ relationship_type: "updates", from_value: 0.4, to_value: 0.15, withdrawal: false });

    const repeatA = row({ statement_slug: "repeat-a", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2, event_time: "2022-01-01T00:00:00.000Z" });
    const repeatB = row({ statement_slug: "repeat-b", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2, event_time: "2023-01-01T00:00:00.000Z" });
    const repeated = revision([repeatA, repeatB], [{ from: "repeat-a", to: "repeat-b", type: "repeats" }]);
    expect(repeated.chains).toEqual([]);
    expect(repeated.repeats.map((item) => item.from_statement_slug)).toEqual(["repeat-a"]);

    const clarify = revision([
      row({ statement_slug: "clarify-a", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2 }),
      row({ statement_slug: "clarify-b", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2, event_time: "2024-02-01T00:00:00.000Z" }),
    ], [{ from: "clarify-a", to: "clarify-b", type: "clarifies" }]);
    expect(clarify.chains).toEqual([]);
    expect(clarify.exclusions.some((item) => item.reason === "relationship_not_a_revision")).toBe(true);

    const contradict = revision([
      row({ statement_slug: "contra-a", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2 }),
      row({ statement_slug: "contra-b", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.8, event_time: "2024-03-01T00:00:00.000Z" }),
    ], [{ from: "contra-a", to: "contra-b", type: "contradicts" }]);
    expect(contradict.chains).toEqual([]);
    expect(contradict.exclusions.some((item) => item.reason === "relationship_not_a_revision")).toBe(true);

    const withdrawn = row({ statement_slug: "withdrawn", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.3, event_time: "2022-06-01T00:00:00.000Z" });
    const note = row({ statement_slug: "withdrawal-note", question_key: scope.question_key, statement_type: "explicit_qualitative", forecast_kind: "qualitative", value_type: "none", value_numeric: null, unit: null, horizon_text: null, forecast_review_state: null });
    const withdrawal = revision([withdrawn, note], [{ from: "withdrawn", to: "withdrawal-note", type: "retracts" }]);
    expect(withdrawal.withdrawals).toEqual([expect.objectContaining({ from_statement_slug: "withdrawn", to_value: null, withdrawal: true, from_value: 0.3 })]);
    expect(withdrawal.chains[0]?.points.map((point) => point.value_numeric)).toEqual([0.3]);

    const machine = revision([
      row({ statement_slug: "machine-old", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.1, event_time: "2020-01-01T00:00:00.000Z" }),
      row({ statement_slug: "machine-new", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.6, event_time: "2024-04-01T00:00:00.000Z" }),
    ], [{ from: "machine-old", to: "machine-new", type: "updates", review: "machine_validated", method: "model_suggested" }]);
    expect(machine.chains).toEqual([]);
    expect(machine.exclusions.some((item) => item.statement_slug === "machine-old" && item.reason === "review_state")).toBe(true);
  });

  it("drops a withdrawn estimate from the cross-section without inventing a replacement", () => {
    const kept = row({ statement_slug: "still-current", person_slug: "noor-example", display_name: "Noor Example", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.05, event_time: "2024-01-01T00:00:00.000Z" });
    const withdrawn = row({ statement_slug: "ada-withdrawn", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.3, event_time: "2023-01-01T00:00:00.000Z" });
    const note = row({ statement_slug: "ada-note", question_key: scope.question_key, statement_type: "explicit_qualitative", forecast_kind: "qualitative", value_type: "none", value_numeric: null, unit: null, forecast_review_state: null });
    const result = computeProbabilityDistribution({
      ...context,
      question_text: "Extinction",
      definition_text: "Literal human extinction",
      scope,
      candidates: [withdrawn, note, kept],
      edges: [{ from_statement_slug: "ada-withdrawn", to_statement_slug: "ada-note", relationship_type: "retracts", review_state: "human_verified", method: "verified_withdrawal" }],
    });
    expect(result.included.map((item) => item.statement_slug)).toEqual(["still-current"]);
    expect(result.exclusions.find((item) => item.statement_slug === "ada-withdrawn")?.reason).toBe("withdrawn");
    expect(result.included.map((item) => item.value_numeric)).not.toContain(0.3);
  });

  it("treats an identical same-time statement as a duplicate and a different value as a tie", () => {
    const scopeOnly = { ...scope, sibling_topic_slugs: [] };
    const duplicate = computeProbabilityDistribution({
      ...context,
      question_text: "Tie",
      definition_text: "Same value",
      scope: scopeOnly,
      candidates: [
        row({ statement_slug: "dup-b", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2, event_time: "2024-01-01T00:00:00.000Z" }),
        row({ statement_slug: "dup-a", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2, event_time: "2024-01-01T00:00:00.000Z" }),
      ],
      edges: [],
    });
    expect(duplicate.included.map((item) => item.statement_slug)).toEqual(["dup-a"]);
    expect(duplicate.exclusions.find((item) => item.statement_slug === "dup-b")?.reason).toBe("duplicate_statement");
    const tie = computeProbabilityDistribution({
      ...context,
      question_text: "Tie",
      definition_text: "Different value",
      scope: scopeOnly,
      candidates: [
        row({ statement_slug: "tie-b", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.8, event_time: "2024-01-01T00:00:00.000Z" }),
        row({ statement_slug: "tie-a", question_key: scope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2, event_time: "2024-01-01T00:00:00.000Z" }),
      ],
      edges: [],
    });
    expect(tie.included.map((item) => item.statement_slug)).toEqual(["tie-a"]);
    expect(tie.exclusions.find((item) => item.statement_slug === "tie-b")?.reason).toBe("not_latest");
  });
});

describe("query to engine", () => {
  it("carries stored target dates through the forecast input SQL and method identity", () => {
    expect(FORECAST_INPUT_SQL).toContain("f.target_date_start");
    expect(FORECAST_INPUT_SQL).toContain("f.target_date_end");
    expect(FORECAST_INPUT_SQL).toContain("f.distribution_json");
    expect(FORECAST_INPUT_SQL).toContain("si.observed_at AS known_at");
    expect(FORECAST_INPUT_SQL).toContain("rd.reviewed_at");
    const mapped = mapForecastRow({
      statement_slug: "mapped-2030",
      person_slug: "ada-example",
      display_name: "Ada Example",
      statement_type: "explicit_numeric",
      review_state: "human_verified",
      forecast_review_state: "human_verified",
      topic_slugs: ["ai-extinction"],
      question_key: "extinction_unconditional",
      question_text: "human extinction",
      definition_text: "Literal human extinction",
      condition_text: null,
      forecast_kind: "probability",
      value_type: "point",
      value_numeric: "0.20000",
      value_min: null,
      value_max: null,
      unit: "probability",
      horizon_text: null,
      target_date_start: null,
      target_date_end: "2030-12-31",
      distribution_json: { quantiles: [{ p: 0.5, value: 0.2 }] },
      resolution_criteria: "Literal extinction by the stored deadline",
      known_at: "2024-02-01T00:00:00.000Z",
      reviewed_at: "2024-03-01T00:00:00.000Z",
      event_time: "2024-01-01T00:00:00.000Z",
    });
    expect(mapped.target_date_end).toBe("2030-12-31");
    expect(mapped.known_at).toBe("2024-02-01T00:00:00.000Z");
    expect(mapped.reviewed_at).toBe("2024-03-01T00:00:00.000Z");
    const conditional = row({
      statement_slug: "pause-2030",
      question_key: "extinction_unconditional",
      definition_text: "Literal human extinction",
      condition_text: "if frontier labs pause scaling",
      target_date_end: "2030-12-31",
      value_numeric: 0.05,
    });
    const unconditional = { ...mapped, statement_slug: "plain-2030" };
    expect(prePolicyMethodKey({ kind: "distribution", question_key: "extinction_unconditional", unit: "probability" })).toBe(
      prePolicyMethodKey({ kind: "distribution", question_key: conditional.question_key, unit: conditional.unit }),
    );
    const methods = resolveTrendMethods([], [unconditional, conditional].reverse());
    const discovered = methods.filter((method) => method.source === "discovered_question" && method.question_key === "extinction_unconditional");
    expect(discovered).toHaveLength(2);
    expect(new Set(discovered.map((method) => trendMethodKey(method))).size).toBe(2);
    expect(trendMethodKey(discovered[0]!)).not.toBe(trendMethodKey(discovered[1]!));
    const computed = computeProbabilityDistribution({
      ...context,
      question_text: discovered.find((method) => method.scope.conditionality !== "conditional")!.question_text,
      definition_text: "Literal human extinction",
      scope: discovered.find((method) => method.scope.conditionality !== "conditional")!.scope,
      candidates: [conditional, unconditional],
      edges: [],
    });
    expect(computed.included.map((item) => item.statement_slug)).toEqual(["plain-2030"]);
    expect(computed.included[0]?.target_date_end).toBe("2030-12-31");
    expect(computed.history.presented_as_reconstruction).toBe(false);
    expect(computed.comparability_policy_version).toBe("comparability/1.0.0");
  });

  it("is stable when input order is shuffled", () => {
    const candidates = [
      row({ statement_slug: "c", person_slug: "c-person", display_name: "C Person", question_key: extinctionScope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.5 }),
      row({ statement_slug: "a", person_slug: "a-person", display_name: "A Person", question_key: extinctionScope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.1 }),
      row({ statement_slug: "b", person_slug: "b-person", display_name: "B Person", question_key: extinctionScope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.2 }),
    ];
    const forward = computeProbabilityDistribution({ ...context, question_text: "q", definition_text: "d", scope: extinctionScope, candidates, edges: [] });
    const backward = computeProbabilityDistribution({ ...context, question_text: "q", definition_text: "d", scope: extinctionScope, candidates: [...candidates].reverse(), edges: [] });
    expect(backward.included.map((item) => item.statement_slug)).toEqual(forward.included.map((item) => item.statement_slug));
    expect(backward.median).toBe(forward.median);
    expect(forward.median).toBe(0.2);
    expect(forward.density).toBe("comparable");
  });

  it("leaves qualitative wording as statements and does not score unresolved forecasts", () => {
    const qualitative = row({
      statement_slug: "qual",
      question_key: "misuse_concern_direction",
      statement_type: "explicit_qualitative",
      forecast_kind: "qualitative",
      value_type: "none",
      value_numeric: null,
      unit: null,
      forecast_review_state: null,
      question_text: "Concern about misuse has increased",
    });
    const groups = discoverQualitativeGroups([qualitative]);
    expect(groups[0]?.rows[0]?.statement_slug).toBe("qual");
    expect(groups[0]?.rows[0]).not.toHaveProperty("value_numeric");
    const numeric = computeProbabilityDistribution({
      ...context,
      question_text: "Extinction",
      definition_text: "Literal human extinction",
      scope: extinctionScope,
      candidates: [qualitative, row({ statement_slug: "num", question_key: extinctionScope.question_key, horizon_text: "by the stated horizon", value_numeric: 0.1 })],
      edges: [],
    });
    expect(numeric.exclusions.find((item) => item.statement_slug === "qual")?.reason).toBe("statement_type");
    expect(numeric.included.map((item) => item.value_numeric)).toEqual([0.1]);

    assertResolutionFixtures();
    for (const fixture of FORECAST_RESOLUTION_FIXTURES) {
      const assessment = assessResolutionEligibility(fixture);
      expect(assessment.eligible).toBe(fixture.eligible);
    }
    const scored = scoreResolvedForecast({ question_key: "ai_extinction_unconditional_by_2070", resolved: false, eligible: true });
    expect(scored.status).toBe("disabled");
    expect(scored.score).toBeNull();
    expect(scored.reason).toMatch(/unresolved extinction forecast is not a failure/);
    expect(scored.reason).toMatch(/speaker count is not a confidence interval/);
  });
});

describe("history", () => {
  const cutoff = "2024-06-01T00:00:00.000Z";

  it("distinguishes a dated statement from information known and reviewed by the cutoff", () => {
    expect(classifyHistory({ statement_slug: "ready", event_time: "2024-01-01T00:00:00.000Z", known_at: "2024-02-01T00:00:00.000Z", reviewed_at: "2024-03-01T00:00:00.000Z" }, cutoff)).toBe("eligible");
    expect(classifyHistory({ statement_slug: "late-observation", event_time: "2024-01-01T00:00:00.000Z", known_at: "2024-07-01T00:00:00.000Z", reviewed_at: "2024-03-01T00:00:00.000Z" }, cutoff)).toBe("after_cutoff");
    expect(classifyHistory({ statement_slug: "dated-only", event_time: "2024-01-01T00:00:00.000Z", known_at: null, reviewed_at: "2024-03-01T00:00:00.000Z" }, cutoff)).toBe("dated_before_cutoff_but_not_known");
    expect(classifyHistory({ statement_slug: "unreviewed", event_time: "2024-01-01T00:00:00.000Z", known_at: "2024-02-01T00:00:00.000Z", reviewed_at: null }, cutoff)).toBe("not_reviewed_by_cutoff");
    const selected = selectKnownByCutoff([
      { statement_slug: "ready", event_time: "2024-01-01T00:00:00.000Z", known_at: "2024-02-01T00:00:00.000Z", reviewed_at: "2024-03-01T00:00:00.000Z" },
      { statement_slug: "dated-only", event_time: "2024-01-01T00:00:00.000Z", known_at: null, reviewed_at: null },
    ], cutoff);
    expect(selected.eligible.map((item) => item.statement_slug)).toEqual(["ready"]);
    expect(selected.claim.presented_as_reconstruction).toBe(true);
    expect(historyClaimFor({ cutoff, mode: "event_time_only" }).presented_as_reconstruction).toBe(false);
    expect(CURRENT_CORPUS_HISTORY.presented_as_reconstruction).toBe(false);
    expect(CURRENT_CORPUS_HISTORY.note).toMatch(/not a reconstruction/);
  });
});

describe("quantity units", () => {
  it("keeps a mismatched unit out of a quantity comparison", () => {
    const scope = PREPARED_TRENDS.find((trend) => trend.slug === "coding-automation-share-by-2028")!.scope;
    const result = computeQuantityForecast({
      ...context,
      question_text: "Coding share",
      definition_text: "A share of coding tasks",
      scope,
      accept_ranges: true,
      candidates: [
        row({ statement_slug: "share", question_key: scope.question_key, topic_slugs: ["coding-automation"], unit: "share", value_numeric: 0.4, horizon_text: "by 2028" }),
        row({ statement_slug: "jobs", question_key: scope.question_key, topic_slugs: ["coding-automation"], unit: "jobs", value_numeric: 12, horizon_text: "by 2028" }),
        row({ statement_slug: "missing-unit", question_key: "coding_automation", topic_slugs: ["coding-automation"], unit: null, value_numeric: 0.5, definition_text: "coding", target_date_end: "2028-12-31" }),
      ],
      edges: [],
    });
    expect(result.included.map((item) => item.statement_slug)).toEqual(["share"]);
    expect(result.exclusions.find((item) => item.statement_slug === "jobs")?.reason).toBe("unit_mismatch");
    expect(result.exclusions.find((item) => item.statement_slug === "missing-unit")?.reason).not.toBeUndefined();
  });
});
