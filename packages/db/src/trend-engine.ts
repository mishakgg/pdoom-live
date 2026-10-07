import {
  COMPARABILITY_POLICY_VERSION,
  CURRENT_CORPUS_HISTORY,
  MEDIAN_INTERPRETATION,
  SUMMARY_MIN_POINTS,
  classifyForecast,
  classifyQuestionKey,
  comparisonDecision,
  coverageSentence,
  describePreservedValue,
  exclusionLabel,
  isBoundPhrase,
  readProbabilitySemantics,
  type ExclusionReason,
  type ForecastClassification,
  type HistoryClaim,
  type TrendConditionality,
  type TrendDensity,
} from "@pdoom/contracts";
import { sha256 } from "./ids";

export type TrendCandidate = {
  statement_slug: string;
  person_slug: string;
  display_name: string;
  statement_type: string;
  review_state: string;
  forecast_review_state: string | null;
  topic_slugs: string[];
  question_key: string | null;
  question_text: string | null;
  definition_text: string | null;
  condition_text: string | null;
  forecast_kind: string | null;
  value_type: string | null;
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  horizon_text: string | null;
  target_date_start?: string | null;
  target_date_end?: string | null;
  value_text?: string | null;
  distribution?: Record<string, unknown> | null;
  probability_semantics?: string | null;
  resolution_criteria?: string | null;
  known_at?: string | null;
  reviewed_at?: string | null;
  event_time: string | null;
};

export type RevisionEdge = {
  from_statement_slug: string;
  to_statement_slug: string;
  relationship_type: string;
  review_state: string;
  method: string;
};

export type TrendScope = {
  topic_slug: string | null;
  sibling_topic_slugs: string[];
  question_key: string;
  statement_types: string[];
  review_states: string[];
  require_horizon: boolean;
  require_unit: string;
  conditionality: TrendConditionality;
  exact_question_id?: string;
};

export type Exclusion = {
  statement_slug: string;
  person_slug: string;
  display_name: string;
  reason: ExclusionReason;
  reason_label: string;
  preserved_value: string | null;
};

export type IncludedEstimate = {
  statement_slug: string;
  person_slug: string;
  display_name: string;
  value_type: "point" | "range";
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  unit: string;
  event_time: string | null;
  horizon_text: string | null;
  condition_text: string | null;
  target_date_start: string | null;
  target_date_end: string | null;
  stored_question_key: string | null;
  probability_semantics: "event_probability" | "unspecified";
  in_summary: boolean;
};

export type TrendCoverage = {
  cohort_slug: string;
  cohort_version: string;
  cohort_definition: string;
  cohort_size: number;
  method_version: string;
  question_key: string | null;
  question_text: string;
  definition_text: string;
  unit: string | null;
  conditionality: TrendConditionality;
  contributing_people: Array<{ person_slug: string; display_name: string }>;
  contributing_statement_count: number;
  contributing_person_count: number;
  cohort_members_with_included_estimate: number;
  cohort_members_without_included_estimate: number;
  missingness_note: string;
  window_start: string | null;
  window_end: string | null;
};

export type NumericTrendResult = {
  method_version: string;
  question_key: string;
  question_text: string;
  definition_text: string;
  topic_slug: string | null;
  unit: string;
  value_semantics: "probability" | "year" | "quantity";
  conditionality: TrendConditionality;
  cohort_slug: string;
  cohort_version: string;
  cohort_definition: string;
  density: TrendDensity;
  included: IncludedEstimate[];
  exclusions: Exclusion[];
  contributing_statement_count: number;
  contributing_person_count: number;
  point_count: number;
  range_count: number;
  minimum: number | null;
  maximum: number | null;
  median: number | null;
  summary_note: string;
  coverage: TrendCoverage;
  comparability_policy_version: typeof COMPARABILITY_POLICY_VERSION;
  exact_question_id: string;
  outcome_label: string;
  deadline_label: string | null;
  condition_label: string | null;
  probability_semantics: "event_probability" | "unspecified";
  median_interpretation: string;
  history: HistoryClaim;
};

export type RevisionPoint = {
  statement_slug: string;
  person_slug: string;
  display_name: string;
  event_time: string | null;
  value_numeric: number;
  unit: string | null;
  horizon_text: string | null;
};

export type RevisionLink = {
  from_statement_slug: string;
  to_statement_slug: string;
  relationship_type: string;
  method: string;
  from_value: number;
  to_value: number | null;
  from_event_time: string | null;
  to_event_time: string | null;
  withdrawal: boolean;
};

export type RevisionChain = {
  person_slug: string;
  display_name: string;
  points: RevisionPoint[];
  links: RevisionLink[];
};

export type RepeatRecord = {
  from_statement_slug: string;
  to_statement_slug: string;
  person_slug: string;
  display_name: string;
  from_value: number | null;
  to_value: number | null;
  unit: string | null;
  note: string;
};

export type RevisionResult = {
  method_version: string;
  question_key: string;
  question_text: string;
  definition_text: string;
  topic_slug: string | null;
  unit: string;
  conditionality: TrendConditionality;
  cohort_slug: string;
  cohort_version: string;
  cohort_definition: string;
  density: TrendDensity;
  chains: RevisionChain[];
  repeats: RepeatRecord[];
  eligible_estimate_count: number;
  exclusions: Exclusion[];
  contributing_statement_count: number;
  contributing_person_count: number;
  summary_note: string;
  coverage: TrendCoverage;
  comparability_policy_version: typeof COMPARABILITY_POLICY_VERSION;
  exact_question_id: string;
  outcome_label: string;
  deadline_label: string | null;
  condition_label: string | null;
  history: HistoryClaim;
  withdrawals: RevisionLink[];
};

type CohortContext = {
  method_version: string;
  cohort_slug: string;
  cohort_version: string;
  cohort_definition: string;
  cohort_size: number;
  question_text: string;
  definition_text: string;
};

const CHANGE_RELATIONSHIPS = new Set(["updates", "retracts"]);
const NON_CHANGE_RELATIONSHIPS = new Set(["repeats", "clarifies", "contradicts"]);
const WITHDRAWAL_RELATIONSHIPS = new Set(["retracts", "withdraws"]);

function hasText(value: string | null | undefined): boolean {
  return Boolean(value && value.trim());
}

function inScope(candidate: TrendCandidate, scope: TrendScope): boolean {
  if (candidate.question_key && candidate.question_key === scope.question_key) return true;
  const exactId = scope.exact_question_id ?? scope.question_key;
  if (candidate.question_key && comparisonDecision(candidate, exactId).match) return true;
  if (scope.topic_slug && candidate.topic_slugs.includes(scope.topic_slug)) return true;
  return scope.sibling_topic_slugs.some((topic) => candidate.topic_slugs.includes(topic));
}

function horizonKnown(candidate: TrendCandidate): boolean {
  return hasText(candidate.horizon_text) || hasText(candidate.target_date_start) || hasText(candidate.target_date_end);
}

function sameQuestionFilters(candidate: TrendCandidate, scope: TrendScope): ExclusionReason | null {
  if (scope.conditionality === "unconditional" && hasText(candidate.condition_text)) return "conditionality_mismatch";
  if (scope.conditionality === "conditional" && !hasText(candidate.condition_text)) return "conditionality_mismatch";
  if (scope.conditionality === "unspecified" && hasText(candidate.condition_text)) return "conditionality_mismatch";
  if (candidate.unit !== scope.require_unit) return "unit_mismatch";
  if (scope.require_horizon && !horizonKnown(candidate)) return "missing_horizon";
  return null;
}

function pointValue(candidate: TrendCandidate): number | null {
  if (candidate.value_type !== "point") return null;
  const value = candidate.value_numeric;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function eventTime(candidate: TrendCandidate): number | null {
  if (!candidate.event_time) return null;
  const time = Date.parse(candidate.event_time);
  return Number.isFinite(time) ? time : null;
}

/** A verified link does not establish a chronology absent from its endpoints. */
function isForwardRelationship(from: TrendCandidate, to: TrendCandidate): boolean {
  const fromTime = eventTime(from);
  const toTime = eventTime(to);
  return fromTime !== null && toTime !== null && toTime > fromTime;
}

function relationshipReviewed(edge: RevisionEdge, target: TrendCandidate, reviewStates: string[]): boolean {
  return edge.review_state === "human_verified" && reviewStates.includes(edge.review_state)
    && target.review_state === "human_verified";
}

function exclusionReason(
  candidate: TrendCandidate,
  scope: TrendScope,
  valueMode: "point" | "point_or_range",
): ExclusionReason | null {
  const keyMatches = candidate.question_key === scope.question_key && candidate.question_key !== null;
  const exactId = scope.exact_question_id ?? scope.question_key;
  const decision = candidate.question_key ? comparisonDecision(candidate, exactId) : null;
  if (!keyMatches && !decision?.match && scope.topic_slug && !candidate.topic_slugs.includes(scope.topic_slug)) return "topic_not_target";
  if (candidate.statement_type !== "explicit_numeric" || !scope.statement_types.includes(candidate.statement_type)) return "statement_type";
  if (candidate.review_state !== "human_verified" || !scope.review_states.includes(candidate.review_state)) return "review_state";
  if (candidate.forecast_review_state && (candidate.forecast_review_state !== "human_verified" || !scope.review_states.includes(candidate.forecast_review_state))) return "review_state";
  if (!candidate.question_key) return "missing_forecast";
  if (keyMatches) {
    const filters = sameQuestionFilters(candidate, scope);
    if (filters) return filters;
  }
  if (!decision) return "missing_forecast";
  if (!decision.match) {
    if (decision.reason === "different_question") return "question_key_mismatch";
    return decision.reason ?? "insufficient_agreement";
  }
  if (!keyMatches) {
    const filters = sameQuestionFilters(candidate, scope);
    if (filters) return filters;
  }
  if (isBoundPhrase(candidate)) return "value_type_not_point";
  if (valueMode === "point") {
    if (pointValue(candidate) === null) return "value_type_not_point";
    return null;
  }
  if (pointValue(candidate) !== null) return null;
  if (candidate.value_type === "range" && candidate.value_min !== null && candidate.value_max !== null) return null;
  return "value_type_not_point";
}

function exclusion(candidate: TrendCandidate, reason: ExclusionReason): Exclusion {
  return {
    statement_slug: candidate.statement_slug,
    person_slug: candidate.person_slug,
    display_name: candidate.display_name,
    reason,
    reason_label: exclusionLabel(reason),
    preserved_value: describePreservedValue(candidate),
  };
}

function edgeExclusion(edge: RevisionEdge, person: TrendCandidate, reason: ExclusionReason): Exclusion {
  return {
    statement_slug: edge.from_statement_slug,
    person_slug: person.person_slug,
    display_name: person.display_name,
    reason,
    reason_label: exclusionLabel(reason),
    preserved_value: null,
  };
}

function sortExclusions(items: Exclusion[]): Exclusion[] {
  const seen = new Set<string>();
  const unique: Exclusion[] = [];
  for (const item of items) {
    const key = `${item.statement_slug}\0${item.reason}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(item);
  }
  return unique.sort((a, b) => `${a.statement_slug}\0${a.reason}`.localeCompare(`${b.statement_slug}\0${b.reason}`));
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid] ?? null;
  const left = sorted[mid - 1];
  const right = sorted[mid];
  if (left === undefined || right === undefined) return null;
  return (left + right) / 2;
}

function peopleOf(rows: Array<{ person_slug: string; display_name: string }>): Array<{ person_slug: string; display_name: string }> {
  const names = new Map<string, string>();
  for (const row of rows) names.set(row.person_slug, row.display_name);
  return [...names.entries()]
    .map(([person_slug, display_name]) => ({ person_slug, display_name }))
    .sort((a, b) => a.display_name.localeCompare(b.display_name) || a.person_slug.localeCompare(b.person_slug));
}

function windowOf(times: Array<string | null>): { window_start: string | null; window_end: string | null } {
  const known = times.filter((time): time is string => hasText(time)).sort((a, b) => a.localeCompare(b));
  return { window_start: known[0] ?? null, window_end: known.at(-1) ?? null };
}

function partition(candidates: TrendCandidate[], scope: TrendScope, valueMode: "point" | "point_or_range"): {
  eligible: TrendCandidate[];
  exclusions: Exclusion[];
} {
  const eligible: TrendCandidate[] = [];
  const exclusions: Exclusion[] = [];
  for (const candidate of candidates) {
    if (!inScope(candidate, scope)) continue;
    const reason = exclusionReason(candidate, scope, valueMode);
    if (reason) exclusions.push(exclusion(candidate, reason));
    else eligible.push(candidate);
  }
  return { eligible, exclusions };
}

function isSuperseded(
  candidate: TrendCandidate,
  eligibleSlugs: Set<string>,
  bySlug: Map<string, TrendCandidate>,
  edges: RevisionEdge[],
  reviewStates: string[],
): boolean {
  return edges.some((edge) => {
    if (edge.from_statement_slug !== candidate.statement_slug) return false;
    if (!CHANGE_RELATIONSHIPS.has(edge.relationship_type)) return false;
    if (!eligibleSlugs.has(edge.to_statement_slug)) return false;
    const target = bySlug.get(edge.to_statement_slug);
    return Boolean(target && target.person_slug === candidate.person_slug
      && relationshipReviewed(edge, target, reviewStates) && isForwardRelationship(candidate, target));
  });
}

function isBareWithdrawal(
  candidate: TrendCandidate,
  eligibleSlugs: Set<string>,
  bySlug: Map<string, TrendCandidate>,
  allBySlug: Map<string, TrendCandidate>,
  edges: RevisionEdge[],
  reviewStates: string[],
): boolean {
  return edges.some((edge) => {
    if (edge.from_statement_slug !== candidate.statement_slug) return false;
    if (!WITHDRAWAL_RELATIONSHIPS.has(edge.relationship_type)) return false;
    const target = allBySlug.get(edge.to_statement_slug) ?? bySlug.get(edge.to_statement_slug);
    if (!target || target.person_slug !== candidate.person_slug) return false;
    if (!relationshipReviewed(edge, target, reviewStates) || !isForwardRelationship(candidate, target)) return false;
    if (edge.relationship_type === "retracts" && eligibleSlugs.has(edge.to_statement_slug) && pointValue(target) !== null) return false;
    return true;
  });
}

function sameContribution(left: TrendCandidate, right: TrendCandidate): boolean {
  if ((left.event_time ?? "") !== (right.event_time ?? "")) return false;
  if (left.value_type === "point" && right.value_type === "point") return left.value_numeric === right.value_numeric;
  if (left.value_type === "range" && right.value_type === "range") return left.value_min === right.value_min && left.value_max === right.value_max;
  return false;
}

function reduceLatest(
  eligible: TrendCandidate[],
  edges: RevisionEdge[],
  reviewStates: string[],
  allCandidates: TrendCandidate[],
): { kept: TrendCandidate[]; exclusions: Exclusion[] } {
  const eligibleSlugs = new Set(eligible.map((item) => item.statement_slug));
  const bySlug = new Map(eligible.map((item) => [item.statement_slug, item]));
  const allBySlug = new Map(allCandidates.map((item) => [item.statement_slug, item]));
  const withdrawn = eligible.filter((candidate) => isBareWithdrawal(candidate, eligibleSlugs, bySlug, allBySlug, edges, reviewStates));
  const withdrawnSlugs = new Set(withdrawn.map((candidate) => candidate.statement_slug));
  // Choose the latest estimate before applying withdrawal. Removing it first
  // would silently reinstate an older belief that the person has not restored.
  const ranked = [...eligible].sort((a, b) => {
    const leftTime = eventTime(a);
    const rightTime = eventTime(b);
    if (leftTime !== rightTime) {
      if (leftTime === null) return 1;
      if (rightTime === null) return -1;
      return rightTime - leftTime;
    }
    return a.statement_slug.localeCompare(b.statement_slug);
  });
  const latest = new Map<string, TrendCandidate>();
  const dropped: TrendCandidate[] = [];
  for (const candidate of ranked) {
    if (!latest.has(candidate.person_slug)) latest.set(candidate.person_slug, candidate);
    else if (!withdrawnSlugs.has(candidate.statement_slug)) dropped.push(candidate);
  }
  return {
    kept: [...latest.values()].filter((candidate) => !withdrawnSlugs.has(candidate.statement_slug)),
    exclusions: [
      ...withdrawn.map((candidate) => exclusion(candidate, "withdrawn")),
      ...dropped.map((candidate) => {
        const kept = latest.get(candidate.person_slug);
        if (kept && !withdrawnSlugs.has(kept.statement_slug) && sameContribution(candidate, kept)) return exclusion(candidate, "duplicate_statement");
        return exclusion(
          candidate,
          isSuperseded(candidate, eligibleSlugs, bySlug, edges, reviewStates) ? "superseded" : "not_latest",
        );
      }),
    ],
  };
}

function toIncluded(candidate: TrendCandidate): IncludedEstimate {
  const range = candidate.value_type === "range";
  return {
    statement_slug: candidate.statement_slug,
    person_slug: candidate.person_slug,
    display_name: candidate.display_name,
    value_type: range ? "range" : "point",
    value_numeric: candidate.value_numeric,
    value_min: candidate.value_min,
    value_max: candidate.value_max,
    unit: candidate.unit ?? "",
    event_time: candidate.event_time,
    horizon_text: candidate.horizon_text,
    condition_text: candidate.condition_text,
    target_date_start: candidate.target_date_start ?? null,
    target_date_end: candidate.target_date_end ?? null,
    stored_question_key: candidate.question_key,
    probability_semantics: readProbabilitySemantics(candidate),
    in_summary: !range && pointValue(candidate) !== null && !isBoundPhrase(candidate),
  };
}

function sortIncluded(items: IncludedEstimate[]): IncludedEstimate[] {
  const valueOf = (item: IncludedEstimate) => (item.value_type === "range" ? item.value_min ?? Number.POSITIVE_INFINITY : item.value_numeric ?? Number.POSITIVE_INFINITY);
  return [...items].sort((a, b) => {
    const value = valueOf(a) - valueOf(b);
    if (value !== 0) return value;
    const person = a.person_slug.localeCompare(b.person_slug);
    if (person !== 0) return person;
    return a.statement_slug.localeCompare(b.statement_slug);
  });
}

function summaryNote(semantics: NumericTrendResult["value_semantics"], density: TrendDensity, pointCount: number): string {
  if (semantics === "year") {
    if (density === "empty") return "No comparable year forecasts are in this cohort for this question. A predicted year is a date.";
    if (density === "sparse") return "Each row is one person's predicted year or year range. A median year is withheld below 3 point years. A year is a date.";
    return `Median of ${pointCount} included point years. Ranges stay listed as intervals. ${MEDIAN_INTERPRETATION.year}`;
  }
  if (semantics === "quantity") {
    if (density === "empty") return "No comparable quantity forecasts with this unit are in this cohort for this question.";
    if (density === "sparse") return "Each row keeps its unit. A median is withheld below 3 point estimates. Units are not converted.";
    return `Median of ${pointCount} included point estimates in this unit. Ranges stay listed as intervals. ${MEDIAN_INTERPRETATION.quantity}`;
  }
  if (density === "empty") return "No comparable point estimates are in this cohort for this question.";
  if (density === "sparse") return "Each row is one person's point estimate. A median is withheld below 3 comparable point estimates.";
  return `Median of ${pointCount} included point estimates. ${MEDIAN_INTERPRETATION.probability}`;
}

function buildCoverage(input: CohortContext & {
  scope: TrendScope;
  density: TrendDensity;
  people: Array<{ person_slug: string; display_name: string }>;
  statementCount: number;
  times: Array<string | null>;
  unit: string | null;
}): TrendCoverage {
  const people = peopleOf(input.people);
  const window = windowOf(input.times);
  return {
    cohort_slug: input.cohort_slug,
    cohort_version: input.cohort_version,
    cohort_definition: input.cohort_definition,
    cohort_size: input.cohort_size,
    method_version: input.method_version,
    question_key: input.scope.question_key,
    question_text: input.question_text,
    definition_text: input.definition_text,
    unit: input.unit,
    conditionality: input.scope.conditionality,
    contributing_people: people,
    contributing_statement_count: input.statementCount,
    contributing_person_count: people.length,
    cohort_members_with_included_estimate: people.length,
    cohort_members_without_included_estimate: Math.max(0, input.cohort_size - people.length),
    missingness_note: coverageSentence({
      includedPeople: people.length,
      cohortSize: input.cohort_size,
      density: input.density,
    }),
    window_start: window.window_start,
    window_end: window.window_end,
  };
}

function computeNumeric(input: CohortContext & {
  scope: TrendScope;
  candidates: TrendCandidate[];
  edges: RevisionEdge[];
  valueMode: "point" | "point_or_range";
  value_semantics: NumericTrendResult["value_semantics"];
}): NumericTrendResult {
  const partitioned = partition(input.candidates, input.scope, input.valueMode);
  const reduced = reduceLatest(partitioned.eligible, input.edges, input.scope.review_states, input.candidates);
  const included = sortIncluded(reduced.kept.map(toIncluded));
  const pointValues = included.flatMap((item) => {
    if (!item.in_summary || item.value_numeric === null || !Number.isFinite(item.value_numeric)) return [];
    return [item.value_numeric];
  });
  const density: TrendDensity = included.length === 0 ? "empty" : pointValues.length >= SUMMARY_MIN_POINTS ? "comparable" : "sparse";
  const coverage = buildCoverage({
    ...input,
    density,
    people: included,
    statementCount: included.length,
    times: included.map((item) => item.event_time),
    unit: input.scope.require_unit,
  });
  return {
    method_version: input.method_version,
    question_key: input.scope.question_key,
    question_text: input.question_text,
    definition_text: input.definition_text,
    topic_slug: input.scope.topic_slug,
    unit: input.scope.require_unit,
    value_semantics: input.value_semantics,
    conditionality: input.scope.conditionality,
    cohort_slug: input.cohort_slug,
    cohort_version: input.cohort_version,
    cohort_definition: input.cohort_definition,
    density,
    included,
    exclusions: sortExclusions([...partitioned.exclusions, ...reduced.exclusions]),
    contributing_statement_count: included.length,
    contributing_person_count: coverage.contributing_person_count,
    point_count: pointValues.length,
    range_count: included.filter((item) => item.value_type === "range").length,
    minimum: density === "comparable" ? Math.min(...pointValues) : null,
    maximum: density === "comparable" ? Math.max(...pointValues) : null,
    median: density === "comparable" ? median(pointValues) : null,
    summary_note: summaryNote(input.value_semantics, density, pointValues.length),
    coverage,
    ...comparisonMeta(input.scope, input.value_semantics, included[0]?.probability_semantics ?? "unspecified"),
  };
}

function comparisonMeta(scope: TrendScope, semantics: NumericTrendResult["value_semantics"], probability: "event_probability" | "unspecified"): Pick<NumericTrendResult, "comparability_policy_version" | "exact_question_id" | "outcome_label" | "deadline_label" | "condition_label" | "probability_semantics" | "median_interpretation" | "history"> {
  const exactId = scope.exact_question_id ?? scope.question_key;
  const entry = classifyQuestionKey(exactId);
  return {
    comparability_policy_version: COMPARABILITY_POLICY_VERSION,
    exact_question_id: exactId,
    outcome_label: entry?.label ?? exactId,
    deadline_label: entry?.deadline?.label ?? null,
    condition_label: entry?.condition_text ?? null,
    probability_semantics: probability,
    median_interpretation: semantics === "year" ? MEDIAN_INTERPRETATION.year : semantics === "quantity" ? MEDIAN_INTERPRETATION.quantity : MEDIAN_INTERPRETATION.probability,
    history: CURRENT_CORPUS_HISTORY,
  };
}

export function computeProbabilityDistribution(input: CohortContext & {
  scope: TrendScope;
  candidates: TrendCandidate[];
  edges?: RevisionEdge[];
}): NumericTrendResult {
  return computeNumeric({ ...input, edges: input.edges ?? [], valueMode: "point", value_semantics: "probability" });
}

export function computeTimelineForecast(input: CohortContext & {
  scope: TrendScope;
  candidates: TrendCandidate[];
  edges?: RevisionEdge[];
  accept_ranges: boolean;
}): NumericTrendResult {
  return computeNumeric({
    ...input,
    edges: input.edges ?? [],
    valueMode: input.accept_ranges ? "point_or_range" : "point",
    value_semantics: "year",
  });
}

export function computeQuantityForecast(input: CohortContext & {
  scope: TrendScope;
  candidates: TrendCandidate[];
  edges?: RevisionEdge[];
  accept_ranges: boolean;
}): NumericTrendResult {
  return computeNumeric({
    ...input,
    edges: input.edges ?? [],
    valueMode: input.accept_ranges ? "point_or_range" : "point",
    value_semantics: "quantity",
  });
}

export function computeHistoricalRevision(input: CohortContext & {
  scope: TrendScope;
  candidates: TrendCandidate[];
  edges: RevisionEdge[];
  relationship_types: string[];
}): RevisionResult {
  const partitioned = partition(input.candidates, input.scope, "point");
  const eligibleBySlug = new Map(partitioned.eligible.map((item) => [item.statement_slug, item]));
  const bySlug = new Map(input.candidates.map((item) => [item.statement_slug, item]));
  const allowedChanges = new Set(input.relationship_types);
  const links: RevisionLink[] = [];
  const repeats: RepeatRecord[] = [];
  const edgeExclusions: Exclusion[] = [];
  const linked = new Set<string>();
  const repeated = new Set<string>();

  const relevantEdges = [...input.edges].sort((a, b) =>
    `${a.from_statement_slug}\0${a.to_statement_slug}\0${a.relationship_type}`.localeCompare(
      `${b.from_statement_slug}\0${b.to_statement_slug}\0${b.relationship_type}`,
    ),
  );

  for (const edge of relevantEdges) {
    const from = bySlug.get(edge.from_statement_slug);
    const to = bySlug.get(edge.to_statement_slug);
    if (!from || !to) continue;
    if (!inScope(from, input.scope) && !inScope(to, input.scope)) continue;
    const anchor = inScope(from, input.scope) ? from : to;
    if (!relationshipReviewed(edge, to, input.scope.review_states)) {
      if (CHANGE_RELATIONSHIPS.has(edge.relationship_type) || WITHDRAWAL_RELATIONSHIPS.has(edge.relationship_type) || edge.relationship_type === "repeats") {
        edgeExclusions.push(edgeExclusion(edge, anchor, "review_state"));
      }
      continue;
    }
    if ((CHANGE_RELATIONSHIPS.has(edge.relationship_type) || WITHDRAWAL_RELATIONSHIPS.has(edge.relationship_type) || edge.relationship_type === "repeats")
      && !isForwardRelationship(from, to)) {
      edgeExclusions.push(edgeExclusion(edge, anchor, "relationship_time_order"));
      continue;
    }
    const withdrawalAllowed = allowedChanges.has("retracts") || allowedChanges.has("withdraws");
    if (withdrawalAllowed && (edge.relationship_type === "withdraws" || edge.relationship_type === "retracts")) {
      const fromEligible = eligibleBySlug.get(from.statement_slug);
      const toEligible = eligibleBySlug.get(to.statement_slug);
      const replacement = edge.relationship_type === "retracts"
        && Boolean(fromEligible && toEligible && fromEligible.person_slug === toEligible.person_slug && pointValue(fromEligible) !== null && pointValue(toEligible) !== null);
      const withdrawnValue = fromEligible ? pointValue(fromEligible) : null;
      if (!replacement && fromEligible && withdrawnValue !== null && from.person_slug === to.person_slug && (edge.relationship_type === "withdraws" || !toEligible || pointValue(to) === null)) {
        links.push({
          from_statement_slug: fromEligible.statement_slug,
          to_statement_slug: to.statement_slug,
          relationship_type: edge.relationship_type,
          method: edge.method,
          from_value: withdrawnValue,
          to_value: null,
          from_event_time: fromEligible.event_time,
          to_event_time: to.event_time,
          withdrawal: true,
        });
        linked.add(fromEligible.statement_slug);
        continue;
      }
      if (!replacement && fromEligible && to.person_slug !== from.person_slug) {
        edgeExclusions.push(edgeExclusion(edge, fromEligible, "different_person"));
        continue;
      }
    }
    if (edge.relationship_type === "repeats") {
      const fromEligible = eligibleBySlug.get(from.statement_slug);
      const toEligible = eligibleBySlug.get(to.statement_slug);
      if (fromEligible && toEligible && fromEligible.person_slug === toEligible.person_slug) {
        repeats.push({
          from_statement_slug: from.statement_slug,
          to_statement_slug: to.statement_slug,
          person_slug: from.person_slug,
          display_name: from.display_name,
          from_value: pointValue(from),
          to_value: pointValue(to),
          unit: from.unit,
          note: "Marked as a repeat. A repeat stays out of the change chart.",
        });
        repeated.add(from.statement_slug);
        repeated.add(to.statement_slug);
      }
      continue;
    }
    if (NON_CHANGE_RELATIONSHIPS.has(edge.relationship_type) || !allowedChanges.has(edge.relationship_type)) {
      edgeExclusions.push(edgeExclusion(edge, anchor, "relationship_not_a_revision"));
      continue;
    }
    const fromEligible = eligibleBySlug.get(from.statement_slug);
    const toEligible = eligibleBySlug.get(to.statement_slug);
    if (!fromEligible || !toEligible) continue;
    if (fromEligible.person_slug !== toEligible.person_slug) {
      edgeExclusions.push(edgeExclusion(edge, fromEligible, "different_person"));
      continue;
    }
    const fromValue = pointValue(fromEligible);
    const toValue = pointValue(toEligible);
    if (fromValue === null || toValue === null) continue;
    links.push({
      from_statement_slug: fromEligible.statement_slug,
      to_statement_slug: toEligible.statement_slug,
      relationship_type: edge.relationship_type,
      method: edge.method,
      from_value: fromValue,
      to_value: toValue,
      from_event_time: fromEligible.event_time,
      to_event_time: toEligible.event_time,
      withdrawal: false,
    });
    linked.add(fromEligible.statement_slug);
    linked.add(toEligible.statement_slug);
  }

  for (const candidate of partitioned.eligible) {
    if (!linked.has(candidate.statement_slug) && !repeated.has(candidate.statement_slug)) {
      edgeExclusions.push(exclusion(candidate, "no_verified_revision"));
    }
  }

  const chains = buildChains(links, eligibleBySlug);
  const chainPeople = peopleOf(chains);
  const density: TrendDensity = chains.length > 0 ? "individual" : partitioned.eligible.length > 0 ? "unlinked" : "empty";
  const chainStatements = new Set(chains.flatMap((chain) => chain.points.map((point) => point.statement_slug)));
  const coverage = buildCoverage({
    ...input,
    density,
    people: chainPeople,
    statementCount: chainStatements.size,
    times: chains.flatMap((chain) => chain.points.map((point) => point.event_time)),
    unit: input.scope.require_unit,
  });
  const summary_note = density === "individual"
    ? "Each section is one person's verified change. Separate numbers without a verified link are not drawn as a revision."
    : density === "unlinked"
      ? "Comparable estimates are listed in the exclusions. No human-verified update or retraction joins them, so no change is drawn."
      : "No comparable point estimates are available to revise for this question.";
  return {
    method_version: input.method_version,
    question_key: input.scope.question_key,
    question_text: input.question_text,
    definition_text: input.definition_text,
    topic_slug: input.scope.topic_slug,
    unit: input.scope.require_unit,
    conditionality: input.scope.conditionality,
    cohort_slug: input.cohort_slug,
    cohort_version: input.cohort_version,
    cohort_definition: input.cohort_definition,
    density,
    chains,
    repeats: repeats.sort((a, b) => `${a.from_statement_slug}\0${a.to_statement_slug}`.localeCompare(`${b.from_statement_slug}\0${b.to_statement_slug}`)),
    eligible_estimate_count: partitioned.eligible.length,
    exclusions: sortExclusions([...partitioned.exclusions, ...edgeExclusions]),
    contributing_statement_count: chainStatements.size,
    contributing_person_count: chainPeople.length,
    summary_note,
    coverage,
    comparability_policy_version: COMPARABILITY_POLICY_VERSION,
    exact_question_id: input.scope.exact_question_id ?? input.scope.question_key,
    outcome_label: classifyQuestionKey(input.scope.exact_question_id ?? input.scope.question_key)?.label ?? input.question_text,
    deadline_label: classifyQuestionKey(input.scope.exact_question_id ?? input.scope.question_key)?.deadline?.label ?? null,
    condition_label: classifyQuestionKey(input.scope.exact_question_id ?? input.scope.question_key)?.condition_text ?? null,
    history: CURRENT_CORPUS_HISTORY,
    withdrawals: links.filter((link) => link.withdrawal),
  };
}

function buildChains(links: RevisionLink[], eligibleBySlug: Map<string, TrendCandidate>): RevisionChain[] {
  const parent = new Map<string, string>();
  const find = (id: string): string => {
    const current = parent.get(id) ?? id;
    if (current === id) return id;
    const root = find(current);
    parent.set(id, root);
    return root;
  };
  const union = (left: string, right: string) => {
    const rootLeft = find(left);
    const rootRight = find(right);
    if (rootLeft !== rootRight) parent.set(rootLeft, rootRight);
  };
  for (const link of links) {
    parent.set(link.from_statement_slug, parent.get(link.from_statement_slug) ?? link.from_statement_slug);
    parent.set(link.to_statement_slug, parent.get(link.to_statement_slug) ?? link.to_statement_slug);
    union(link.from_statement_slug, link.to_statement_slug);
  }
  const groups = new Map<string, RevisionLink[]>();
  for (const link of links) {
    const root = find(link.from_statement_slug);
    const group = groups.get(root) ?? [];
    group.push(link);
    groups.set(root, group);
  }
  const chains: RevisionChain[] = [];
  for (const group of groups.values()) {
    const orderedLinks = [...group].sort((a, b) =>
      `${a.from_event_time ?? ""}\0${a.to_event_time ?? ""}\0${a.from_statement_slug}\0${a.to_statement_slug}`.localeCompare(
        `${b.from_event_time ?? ""}\0${b.to_event_time ?? ""}\0${b.from_statement_slug}\0${b.to_statement_slug}`,
      ),
    );
    const slugs = [...new Set(orderedLinks.flatMap((link) => [link.from_statement_slug, link.to_statement_slug]))];
    const points = slugs.flatMap((slug) => {
      const candidate = eligibleBySlug.get(slug);
      const value = candidate ? pointValue(candidate) : null;
      if (!candidate || value === null) return [];
      return [{
        statement_slug: candidate.statement_slug,
        person_slug: candidate.person_slug,
        display_name: candidate.display_name,
        event_time: candidate.event_time,
        value_numeric: value,
        unit: candidate.unit,
        horizon_text: candidate.horizon_text,
      }];
    }).sort((a, b) => (a.event_time ?? "").localeCompare(b.event_time ?? "") || a.statement_slug.localeCompare(b.statement_slug));
    const person = points[0];
    if (!person) continue;
    chains.push({
      person_slug: person.person_slug,
      display_name: person.display_name,
      points,
      links: orderedLinks,
    });
  }
  return chains.sort((a, b) => a.person_slug.localeCompare(b.person_slug) || a.points[0]!.statement_slug.localeCompare(b.points[0]!.statement_slug));
}

export type DiscoveredTrend = {
  slug: string;
  name: string;
  method_version: "discovered-question/1.1.0";
  source: "discovered_question";
  kind: "distribution" | "timeline" | "quantity";
  question_key: string;
  exact_question_id: string;
  question_text: string;
  definition_text: string;
  scope: TrendScope;
  accept_ranges: boolean;
};

export type UnpooledForecast = {
  statement_slug: string;
  person_slug: string;
  display_name: string;
  question_key: string;
  family_id: string;
  reason: ExclusionReason;
  reason_label: string;
  question_text: string | null;
  definition_text: string | null;
  condition_text: string | null;
  horizon_text: string | null;
  target_date_start: string | null;
  target_date_end: string | null;
  unit: string | null;
  value_type: string | null;
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  preserved_value: string | null;
  event_time: string | null;
};

export type QualitativeGroup = {
  slug: string;
  question_key: string;
  name: string;
  definition_text: string;
  rows: Array<{
    statement_slug: string;
    person_slug: string;
    display_name: string;
    question_text: string | null;
    event_time: string | null;
  }>;
};

function discoveredSlug(questionKey: string, unit: string, conditionality: string): string {
  const kebab = `${questionKey}-${unit}-${conditionality}`.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  if (kebab.length <= 80 && kebab.length > 0) return kebab;
  const trimmed = kebab.slice(0, 71).replace(/-$/g, "");
  return `${trimmed}-${sha256(kebab).slice(0, 8)}`;
}

function verifiedNumeric(candidate: TrendCandidate): boolean {
  if (candidate.statement_type !== "explicit_numeric") return false;
  if (candidate.review_state !== "human_verified") return false;
  if (candidate.forecast_review_state && candidate.forecast_review_state !== "human_verified") return false;
  if (!candidate.question_key || !candidate.unit) return false;
  if (candidate.value_type !== "point" && candidate.value_type !== "range" && candidate.value_type !== "distribution") return false;
  if (candidate.value_type === "point" && pointValue(candidate) === null) return false;
  if (candidate.value_type === "range" && (candidate.value_min === null || candidate.value_max === null)) return false;
  return true;
}

export function discoverQuestionTrends(
  candidates: TrendCandidate[],
  takenQuestionKeys: Set<string>,
  takenSlugs: Set<string>,
): DiscoveredTrend[] {
  const buckets = new Map<string, { classified: ForecastClassification; rows: TrendCandidate[] }>();
  for (const candidate of candidates) {
    if (!verifiedNumeric(candidate)) continue;
    if (takenQuestionKeys.has(candidate.question_key ?? "")) continue;
    const classified = classifyForecast(candidate);
    if (!classified.poolable) continue;
    if (takenQuestionKeys.has(classified.exact_question_id)) continue;
    const bucket = buckets.get(classified.exact_question_id) ?? { classified, rows: [] };
    bucket.rows.push(candidate);
    buckets.set(classified.exact_question_id, bucket);
  }
  return [...buckets.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([, bucket]) => {
      const sample = [...bucket.rows].sort((a, b) => a.statement_slug.localeCompare(b.statement_slug))[0]!;
      const classified = bucket.classified;
      const unit = sample.unit ?? "";
      const kind: DiscoveredTrend["kind"] = classified.value_semantics === "probability" ? "distribution" : classified.value_semantics === "year" ? "timeline" : "quantity";
      const conditionality = classified.conditionality === "unspecified" && !hasText(sample.condition_text) ? "unconditional" : classified.conditionality;
      let slug = discoveredSlug(classified.exact_question_id, unit, conditionality);
      if (takenSlugs.has(slug)) slug = discoveredSlug(`${classified.exact_question_id}-extra`, unit, conditionality);
      const questionText = (classified.deadline_label ? `${sample.question_text ?? sample.question_key} (${classified.deadline_label})` : (sample.question_text ?? sample.question_key ?? "Stored question")).replace(/\s+/g, " ").trim();
      return {
        slug,
        name: questionText.length <= 140 ? questionText : `${questionText.slice(0, 137)}...`,
        method_version: "discovered-question/1.1.0" as const,
        source: "discovered_question" as const,
        kind,
        question_key: sample.question_key ?? "",
        exact_question_id: classified.exact_question_id,
        question_text: questionText,
        definition_text: classified.definition,
        scope: {
          topic_slug: null,
          sibling_topic_slugs: [],
          question_key: sample.question_key ?? "",
          exact_question_id: classified.exact_question_id,
          statement_types: ["explicit_numeric"],
          review_states: ["human_verified"],
          require_horizon: classified.date_role !== "predicted_value",
          require_unit: unit,
          conditionality,
        },
        accept_ranges: kind !== "distribution",
      };
    })
    .sort((a, b) => a.slug.localeCompare(b.slug) || a.exact_question_id.localeCompare(b.exact_question_id));
}

export function listUnpooledForecasts(candidates: TrendCandidate[], takenQuestionKeys: Set<string>): UnpooledForecast[] {
  const rows: UnpooledForecast[] = [];
  for (const candidate of candidates) {
    if (!verifiedNumeric(candidate)) continue;
    if (takenQuestionKeys.has(candidate.question_key ?? "")) continue;
    const classified = classifyForecast(candidate);
    if (classified.poolable || takenQuestionKeys.has(classified.exact_question_id)) continue;
    const reason = classified.reason ?? "insufficient_agreement";
    rows.push({
      statement_slug: candidate.statement_slug,
      person_slug: candidate.person_slug,
      display_name: candidate.display_name,
      question_key: candidate.question_key ?? "",
      family_id: classified.family_id,
      reason,
      reason_label: exclusionLabel(reason),
      question_text: candidate.question_text,
      definition_text: candidate.definition_text,
      condition_text: candidate.condition_text,
      horizon_text: candidate.horizon_text,
      target_date_start: candidate.target_date_start ?? null,
      target_date_end: candidate.target_date_end ?? null,
      unit: candidate.unit,
      value_type: candidate.value_type,
      value_numeric: candidate.value_numeric,
      value_min: candidate.value_min,
      value_max: candidate.value_max,
      preserved_value: classified.preserved_value,
      event_time: candidate.event_time,
    });
  }
  return rows.sort((a, b) => `${a.family_id}\0${a.statement_slug}`.localeCompare(`${b.family_id}\0${b.statement_slug}`));
}

export function discoverQualitativeGroups(candidates: TrendCandidate[]): QualitativeGroup[] {
  const buckets = new Map<string, TrendCandidate[]>();
  for (const candidate of candidates) {
    if (candidate.statement_type !== "explicit_qualitative") continue;
    if (candidate.review_state !== "human_verified") continue;
    if (!candidate.question_key) continue;
    const list = buckets.get(candidate.question_key) ?? [];
    list.push(candidate);
    buckets.set(candidate.question_key, list);
  }
  return [...buckets.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([questionKey, rows]) => {
      const sample = [...rows].sort((a, b) => a.statement_slug.localeCompare(b.statement_slug))[0]!;
      const entry = classifyQuestionKey(questionKey);
      const slug = discoveredSlug(questionKey, "qualitative", "statements");
      return {
        slug,
        question_key: questionKey,
        name: entry?.label ?? (sample.question_text ?? questionKey),
        definition_text: entry?.definition ?? "Qualitative statements. No probability is inferred from this wording.",
        rows: [...rows]
          .sort((a, b) => (a.event_time ?? "").localeCompare(b.event_time ?? "") || a.statement_slug.localeCompare(b.statement_slug))
          .map((row) => ({
            statement_slug: row.statement_slug,
            person_slug: row.person_slug,
            display_name: row.display_name,
            question_text: row.question_text,
            event_time: row.event_time,
          })),
      };
    });
}

export type VolumeRow = {
  bucket: string | null;
  topic_slug: string;
  statement_type: string;
  statement_count: number;
  person_count: number;
};

export function computeStatementVolume(input: {
  review_states: string[];
  cohort_size: number;
  rows: Array<{
    statement_slug: string;
    person_slug: string;
    display_name?: string;
    statement_type: string;
    review_state: string;
    topic_slug: string;
    event_time: string | null;
  }>;
}): {
  rows: VolumeRow[];
  exclusions: Exclusion[];
  contributing_statement_count: number;
  contributing_person_count: number;
  contributing_people: Array<{ person_slug: string; display_name: string }>;
  coverage: {
    cohort_size: number;
    cohort_members_with_included_estimate: number;
    cohort_members_without_included_estimate: number;
    missingness_note: string;
  };
} {
  const exclusions: Exclusion[] = [];
  const kept: typeof input.rows = [];
  const seen = new Set<string>();
  for (const row of input.rows) {
    if (!input.review_states.includes(row.review_state)) {
      if (!seen.has(row.statement_slug)) {
        exclusions.push({
          statement_slug: row.statement_slug,
          person_slug: row.person_slug,
          display_name: row.display_name ?? row.person_slug,
          reason: "review_state",
          reason_label: exclusionLabel("review_state"),
          preserved_value: null,
        });
        seen.add(row.statement_slug);
      }
      continue;
    }
    kept.push(row);
  }
  const groups = new Map<string, { statements: Set<string>; people: Set<string>; bucket: string | null; topic_slug: string; statement_type: string }>();
  for (const row of kept) {
    const bucket = row.event_time ? quarterKey(row.event_time) : null;
    const key = `${bucket ?? "unknown"}|${row.topic_slug}|${row.statement_type}`;
    const group = groups.get(key) ?? {
      statements: new Set<string>(),
      people: new Set<string>(),
      bucket,
      topic_slug: row.topic_slug,
      statement_type: row.statement_type,
    };
    group.statements.add(row.statement_slug);
    group.people.add(row.person_slug);
    groups.set(key, group);
  }
  const people = peopleOf(kept.map((row) => ({ person_slug: row.person_slug, display_name: row.display_name ?? row.person_slug })));
  const statementIds = new Set(kept.map((row) => row.statement_slug));
  const missing = Math.max(0, input.cohort_size - people.length);
  return {
    rows: [...groups.values()]
      .map((group) => ({
        bucket: group.bucket,
        topic_slug: group.topic_slug,
        statement_type: group.statement_type,
        statement_count: group.statements.size,
        person_count: group.people.size,
      }))
      .sort((a, b) => `${a.bucket ?? ""}|${a.topic_slug}|${a.statement_type}`.localeCompare(`${b.bucket ?? ""}|${b.topic_slug}|${b.statement_type}`)),
    exclusions: sortExclusions(exclusions),
    contributing_statement_count: statementIds.size,
    contributing_person_count: people.length,
    contributing_people: people,
    coverage: {
      cohort_size: input.cohort_size,
      cohort_members_with_included_estimate: people.length,
      cohort_members_without_included_estimate: missing,
      missingness_note: `${people.length} of ${input.cohort_size} cohort members have a counted statement. ${missing} members are absent from this count. Counts stay split by statement class.`,
    },
  };
}

function quarterKey(iso: string): string {
  const date = new Date(iso);
  const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
  return `${date.getUTCFullYear()}-Q${quarter}`;
}
