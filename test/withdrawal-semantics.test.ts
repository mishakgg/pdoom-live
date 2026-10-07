import { describe, expect, it } from "vitest";
import { exclusionLabel } from "@pdoom/contracts";
import { PREPARED_TRENDS } from "../packages/db/src/trend-catalog";
import { computeHistoricalRevision, computeProbabilityDistribution, computeTimelineForecast, type RevisionEdge, type TrendCandidate } from "../packages/db/src/trend-engine";

const method = PREPARED_TRENDS.find((item) => item.slug === "extinction-by-2070-distribution")!;
const context = { method_version: "withdrawal-regression", cohort_slug: "fixture", cohort_version: "1", cohort_definition: "Fictional people", cohort_size: 2, question_text: method.question_text, definition_text: method.definition_text, scope: method.scope };
function row(slug: string, time: string | null, value: number | null, extra: Partial<TrendCandidate> = {}): TrendCandidate {
  return { statement_slug: slug, person_slug: "ada-example", display_name: "Ada Example", statement_type: value === null ? "explicit_qualitative" : "explicit_numeric", review_state: "human_verified", forecast_review_state: value === null ? null : "human_verified", topic_slugs: ["ai-extinction"], question_key: method.question_key, question_text: method.question_text, definition_text: method.definition_text, condition_text: null, forecast_kind: value === null ? "qualitative" : "probability", value_type: value === null ? "none" : "point", value_numeric: value, value_min: null, value_max: null, unit: value === null ? null : "probability", horizon_text: "by 2070", event_time: time, ...extra };
}
function edge(from: string, to: string, type = "retracts", review_state = "human_verified"): RevisionEdge {
  return { from_statement_slug: from, to_statement_slug: to, relationship_type: type, review_state, method: "fixture" };
}
const old = row("old", "2020-01-01T00:00:00Z", 0.4);
const latest = row("latest", "2024-01-01T00:00:00Z", 0.1);
const note = row("note", "2025-01-01T00:00:00Z", null);
function numeric(candidates: TrendCandidate[], edges: RevisionEdge[], scope = context.scope) { return computeProbabilityDistribution({ ...context, scope, candidates, edges }); }
function revision(candidates: TrendCandidate[], edges: RevisionEdge[], scope = context.scope) { return computeHistoricalRevision({ ...context, scope, candidates, edges, relationship_types: ["updates", "retracts"] }); }

describe("withdrawal state and revision chronology", () => {
  it("does not resurrect earlier estimates after the latest estimate is withdrawn", () => {
    for (const updates of [[], [edge("old", "latest", "updates")]]) {
      const result = numeric([old, latest, note], [...updates, edge("latest", "note")]);
      expect(result.included).toEqual([]);
      expect(result.exclusions).toContainEqual(expect.objectContaining({ statement_slug: "latest", reason: "withdrawn" }));
      expect(result.exclusions).toContainEqual(expect.objectContaining({ statement_slug: "old", reason: updates.length ? "superseded" : "not_latest" }));
    }
  });
  it("allows a genuinely later estimate after withdrawal, including multiple update links", () => {
    const next = row("next", "2026-01-01T00:00:00Z", 0.2);
    const edges = [edge("old", "latest", "updates"), edge("latest", "note")];
    const result = numeric([old, latest, note, next], edges);
    expect(result.included.map((item) => item.statement_slug)).toEqual(["next"]);
    expect(numeric([next, note, latest, old], [...edges].reverse())).toEqual(result);
  });
  it("withdrawing an older estimate does not erase an independent newer estimate", () => {
    expect(numeric([old, latest, note], [edge("old", "note")]).included.map((item) => item.statement_slug)).toEqual(["latest"]);
  });
  it("requires human-reviewed relationships even when a scope permits machine records", () => {
    const scope = { ...context.scope, review_states: ["human_verified", "machine_validated"] };
    expect(numeric([old, latest, note], [edge("latest", "note", "retracts", "machine_validated")], scope).included.map((item) => item.statement_slug)).toEqual(["latest"]);
    expect(revision([old, latest], [edge("old", "latest", "updates", "machine_validated")], scope).chains).toEqual([]);
  });
  it("does not use a target whose human approval is missing or stale", () => {
    const stale = { ...note, review_state: "needs_review" };
    expect(numeric([latest, stale], [edge("latest", "note")]).included.map((item) => item.statement_slug)).toEqual(["latest"]);
    expect(revision([latest, stale], [edge("latest", "note")]).withdrawals).toEqual([]);
  });
  it.each([null, "invalid", "2023-01-01T00:00:00Z", latest.event_time])("does not apply an undated, invalid, reversed, or tied withdrawal (%s)", (time) => {
    const target = { ...note, event_time: time };
    expect(numeric([old, latest, target], [edge("latest", "note")]).included.map((item) => item.statement_slug)).toEqual(["latest"]);
    const result = revision([old, latest, target], [edge("latest", "note")]);
    expect(result.withdrawals).toEqual([]);
    expect(result.exclusions).toContainEqual(expect.objectContaining({ statement_slug: "latest", reason: "relationship_time_order" }));
  });
  it("rejects reversed updates and cyclic backward edges while keeping the forward link", () => {
    const edges = [edge("old", "latest", "updates"), edge("latest", "old", "updates")];
    const result = revision([old, latest], edges);
    expect(result.chains).toHaveLength(1);
    expect(result.chains[0]!.links).toHaveLength(1);
    expect(result.chains[0]!.links[0]).toMatchObject({ from_statement_slug: "old", to_statement_slug: "latest" });
    expect(result.exclusions).toContainEqual(expect.objectContaining({ statement_slug: "latest", reason: "relationship_time_order" }));
    expect(numeric([old, latest], edges).included.map((item) => item.statement_slug)).toEqual(["latest"]);
  });
  it("never withdraws one person's estimate using a different person's note", () => {
    const other = { ...note, person_slug: "ben-example" };
    expect(numeric([latest, other], [edge("latest", "note")]).included.map((item) => item.statement_slug)).toEqual(["latest"]);
    expect(revision([latest, other], [edge("latest", "note")]).exclusions).toContainEqual(expect.objectContaining({ reason: "different_person" }));
  });
  it("does not resurrect an older timeline point when a latest range is withdrawn", () => {
    const years = PREPARED_TRENDS.find((item) => item.slug === "agi-arrival-year")!;
    const adapt = (candidate: TrendCandidate): TrendCandidate => ({ ...candidate, question_key: years.question_key, question_text: years.question_text, definition_text: years.definition_text, topic_slugs: ["agi-arrival"], unit: candidate.value_type === "none" ? null : "year", horizon_text: null });
    const candidates = [adapt({ ...old, value_numeric: 2035 }), adapt({ ...latest, value_type: "range", value_numeric: null, value_min: 2030, value_max: 2040 }), adapt(note)];
    const result = computeTimelineForecast({ ...context, scope: years.scope, candidates, edges: [edge("latest", "note")], accept_ranges: true });
    expect(result.included).toEqual([]);
  });
  it("uses time instants rather than timestamp text to order edges", () => {
    const earlier = { ...old, event_time: "2024-01-01T01:00:00+02:00" };
    const later = { ...latest, event_time: "2024-01-01T00:00:00Z" };
    expect(revision([earlier, later], [edge("old", "latest", "updates")]).chains[0]?.links).toHaveLength(1);
    expect(numeric([earlier, later], []).included.map((item) => item.statement_slug)).toEqual(["latest"]);
  });
  it("explains a chronology exclusion without calling it a repeat or contradiction", () => {
    expect(exclusionLabel("relationship_time_order")).toMatch(/later|chronolog/);
    expect(exclusionLabel("relationship_time_order")).not.toMatch(/repeat|contradiction/);
  });
});
