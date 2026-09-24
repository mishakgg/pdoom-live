export type TrendCandidate = {
  statement_slug: string;
  person_slug: string;
  display_name: string;
  statement_type: string;
  review_state: string;
  topic_slugs: string[];
  question_key: string | null;
  value_type: string | null;
  value_numeric: number | null;
  unit: string | null;
  horizon_text: string | null;
  event_time: string | null;
};

export type DistributionAggregation = {
  type: "explicit_numeric_distribution";
  question_key: string;
  topic_slug: string;
  sibling_topic_slugs: string[];
  statement_types: string[];
  review_states: string[];
  person_reducer: "latest_event_time";
  require_horizon: boolean;
  require_unit: string;
  value_type: "point";
};

export type Exclusion = {
  statement_slug: string;
  person_slug: string;
  reason: string;
};

export type DistributionResult = {
  method_version: string;
  question_key: string;
  topic_slug: string;
  cohort_slug: string;
  cohort_version: string;
  cohort_definition: string;
  included: Array<{
    statement_slug: string;
    person_slug: string;
    display_name: string;
    value_numeric: number;
    event_time: string | null;
  }>;
  exclusions: Exclusion[];
  contributing_statement_count: number;
  contributing_person_count: number;
  minimum: number | null;
  maximum: number | null;
  median: number | null;
  coverage: {
    cohort_size: number;
    cohort_members_with_included_estimate: number;
    cohort_members_without_included_estimate: number;
    missingness_note: string;
  };
};

function consider(candidate: TrendCandidate, topics: Set<string>): boolean {
  return candidate.topic_slugs.some((slug) => topics.has(slug));
}

function exclusionReason(candidate: TrendCandidate, aggregation: DistributionAggregation): string | null {
  if (!candidate.topic_slugs.includes(aggregation.topic_slug)) return "topic_not_target";
  if (!aggregation.statement_types.includes(candidate.statement_type)) return "statement_type";
  if (!aggregation.review_states.includes(candidate.review_state)) return "review_state";
  if (!candidate.question_key) return "missing_forecast";
  if (candidate.question_key !== aggregation.question_key) return "question_key_mismatch";
  if (candidate.unit !== aggregation.require_unit) return "unit_mismatch";
  if (aggregation.require_horizon && !candidate.horizon_text) return "missing_horizon";
  if (candidate.value_type !== aggregation.value_type || candidate.value_numeric === null) {
    return "value_type_not_point";
  }
  return null;
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

export function computeExplicitNumericDistribution(input: {
  method_version: string;
  cohort_slug: string;
  cohort_version: string;
  cohort_definition: string;
  cohort_size: number;
  aggregation: DistributionAggregation;
  candidates: TrendCandidate[];
}): DistributionResult {
  const watched = new Set([input.aggregation.topic_slug, ...input.aggregation.sibling_topic_slugs]);
  const exclusions: Exclusion[] = [];
  const eligible: TrendCandidate[] = [];

  for (const candidate of input.candidates) {
    if (!consider(candidate, watched)) continue;
    const reason = exclusionReason(candidate, input.aggregation);
    if (reason) {
      exclusions.push({
        statement_slug: candidate.statement_slug,
        person_slug: candidate.person_slug,
        reason,
      });
    } else {
      eligible.push(candidate);
    }
  }

  const latest = new Map<string, TrendCandidate>();
  const ranked = [...eligible].sort((a, b) => {
    const time = (b.event_time ?? "").localeCompare(a.event_time ?? "");
    if (time !== 0) return time;
    return a.statement_slug.localeCompare(b.statement_slug);
  });
  for (const candidate of ranked) {
    const current = latest.get(candidate.person_slug);
    if (!current) {
      latest.set(candidate.person_slug, candidate);
      continue;
    }
    exclusions.push({
      statement_slug: candidate.statement_slug,
      person_slug: candidate.person_slug,
      reason: "not_latest",
    });
  }

  const included = [...latest.values()]
    .map((candidate) => ({
      statement_slug: candidate.statement_slug,
      person_slug: candidate.person_slug,
      display_name: candidate.display_name,
      value_numeric: candidate.value_numeric ?? 0,
      event_time: candidate.event_time,
    }))
    .sort((a, b) => a.value_numeric - b.value_numeric);

  const values = included.map((item) => item.value_numeric);
  return {
    method_version: input.method_version,
    question_key: input.aggregation.question_key,
    topic_slug: input.aggregation.topic_slug,
    cohort_slug: input.cohort_slug,
    cohort_version: input.cohort_version,
    cohort_definition: input.cohort_definition,
    included,
    exclusions,
    contributing_statement_count: included.length,
    contributing_person_count: included.length,
    minimum: values.length ? Math.min(...values) : null,
    maximum: values.length ? Math.max(...values) : null,
    median: median(values),
    coverage: {
      cohort_size: input.cohort_size,
      cohort_members_with_included_estimate: included.length,
      cohort_members_without_included_estimate: input.cohort_size - included.length,
      missingness_note:
        "People without an included estimate are missing from this distribution. That absence is not a zero probability.",
    },
  };
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
  rows: Array<{
    statement_slug: string;
    person_slug: string;
    statement_type: string;
    review_state: string;
    topic_slug: string;
    event_time: string | null;
  }>;
}): { rows: VolumeRow[]; exclusions: Exclusion[]; contributing_statement_count: number; contributing_person_count: number } {
  const exclusions: Exclusion[] = [];
  const kept: typeof input.rows = [];
  const seen = new Set<string>();
  for (const row of input.rows) {
    if (!input.review_states.includes(row.review_state)) {
      if (!seen.has(row.statement_slug)) {
        exclusions.push({
          statement_slug: row.statement_slug,
          person_slug: row.person_slug,
          reason: "review_state",
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
  const statementIds = new Set(kept.map((row) => row.statement_slug));
  const people = new Set(kept.map((row) => row.person_slug));
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
    exclusions,
    contributing_statement_count: statementIds.size,
    contributing_person_count: people.size,
  };
}

function quarterKey(iso: string): string {
  const date = new Date(iso);
  const quarter = Math.floor(date.getUTCMonth() / 3) + 1;
  return `${date.getUTCFullYear()}-Q${quarter}`;
}
