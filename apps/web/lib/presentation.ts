import { countLabel, isHumanVerified, phraseLabel } from "@/lib/format";

export const APPLICATION_ERROR_TITLE = "The record could not be loaded";
export const APPLICATION_ERROR_BODY =
  "The database or application failed before this page could be rendered. Nothing on this screen is a finding about a person, a forecast, or a trend.";

export const NO_STATEMENT_COLLECTED = "No statement has been collected for this record.";
export const NO_STATEMENT_COLLECTED_NOTE =
  "That is a gap in what this observatory has stored. It is not evidence that this person has never spoken.";

export const PARTIAL_COLLECTION_NOTE = "Collection is partial. The stored excerpt may not be the full source.";

const FAILING_COLLECTION = new Set([
  "unavailable",
  "not_found",
  "rate_limited",
  "unauthorized",
  "blocked_by_policy",
  "parser_unsupported",
  "content_too_large",
  "invalid_content",
  "collector_bug",
]);

const FRESHNESS_LABELS: Record<string, string> = {
  current: "Checked within 14 days",
  aging: "Last success within 90 days",
  stale: "Stale, last success older than 90 days",
  never_checked: "Never successfully checked",
};

const PERSON_STATUS_LABELS: Record<string, string> = {
  active: "Active",
  historical: "Historical",
  review: "In review",
};

const RELATIONSHIP_LABELS: Record<string, string> = {
  updates: "Updates",
  clarifies: "Clarifies",
  retracts: "Retracts",
  contradicts: "Contradicts",
  repeats: "Repeats",
};

export type CoverageInput = {
  datasetKind: string | null;
  cohortSize: number;
  statementBearingPeople: number;
  publicStatementCount: number;
  humanVerifiedStatementCount: number;
};

export type CoverageTone = "unloaded" | "empty" | "unverified" | "thin" | "reported";

export function personStatusLabel(status: string): string {
  return PERSON_STATUS_LABELS[status] ?? phraseLabel(status);
}

export function relationshipLabel(type: string): string {
  return RELATIONSHIP_LABELS[type] ?? phraseLabel(type);
}

export function freshnessLabel(state: string): string {
  return FRESHNESS_LABELS[state] ?? phraseLabel(state);
}

export function sourceMaterialState(collectionStatus: string, availability: string): "available" | "partial" | "unavailable" {
  if (availability === "removed" || availability === "unknown") return "unavailable";
  if (collectionStatus === "partial") return "partial";
  if (FAILING_COLLECTION.has(collectionStatus)) return "unavailable";
  return "available";
}

export function unavailableCopy(collectionStatus: string, availability: string): string {
  return `The original material is not available. Collection status is ${phraseLabel(collectionStatus)}. Availability is ${phraseLabel(availability)}. This record is kept so the gap stays visible. Any excerpt below is only the text that was stored, and it may be incomplete.`;
}

export function coverageTone(input: CoverageInput): CoverageTone {
  if (!input.datasetKind) return "unloaded";
  if (input.publicStatementCount === 0) return "empty";
  if (input.datasetKind === "live" && input.humanVerifiedStatementCount === 0) return "unverified";
  if (input.cohortSize > 0 && input.statementBearingPeople / input.cohortSize < 0.5) return "thin";
  return "reported";
}

export function coverageCopy(input: CoverageInput): { tone: Exclude<CoverageTone, "reported">; title: string; body: string } | null {
  const tone = coverageTone(input);
  if (tone === "unloaded") {
    return {
      tone,
      title: "No dataset is loaded",
      body: "The observatory has no current dataset import. This page is waiting for data. It is not a forecast.",
    };
  }
  if (tone === "empty") {
    return {
      tone,
      title: "No statement has been collected",
      body: "This dataset is loaded and no public statement is attached. An empty collection is not a finding that anyone has been silent, and it is not evidence that a tracked person has never spoken.",
    };
  }
  if (tone === "unverified") {
    return {
      tone,
      title: "No human-verified statement yet",
      body: `This live dataset has ${countLabel(input.publicStatementCount, "collected statement")} and ${countLabel(input.humanVerifiedStatementCount, "human-verified statement")}. Published trends stay withheld until a statement is human verified. Machine-validated records, when present, stay labeled as machine output and are not a person's probability. An empty verified set is a review gap, not evidence that tracked people have never spoken.`,
    };
  }
  if (tone === "thin") {
    return {
      tone,
      title: "Thin coverage",
      body: `Collected statements cover ${input.statementBearingPeople} of ${input.cohortSize} tracked people (${countLabel(input.publicStatementCount, "statement")}). Trends describe that subset. People without a collected statement are missing from the record, which is not a zero and not evidence they have never spoken.`,
    };
  }
  return null;
}

export function affiliationFact(organization: { name: string; role: string | null; review_state?: string | null } | null): {
  established: boolean;
  text: string;
} {
  if (!organization) return { established: false, text: "No current affiliation recorded" };
  const role = organization.role ?? "Role not recorded";
  const text = `${role} · ${organization.name}`;
  if (isHumanVerified(organization.review_state)) return { established: true, text };
  return { established: false, text: `Not established · ${text}` };
}

export function affiliationDates(start: string | null, end: string | null, settled: boolean): string {
  const startText = start ?? "start date unknown";
  const endText = end ?? (settled ? "present" : "no end date recorded");
  return `${startText} – ${endText}`;
}

export function evidenceSpan(evidence: {
  start_ms: number | null;
  end_ms: number | null;
  start_char: number | null;
  end_char: number | null;
  segment_kind: string;
}): string {
  const kind = phraseLabel(evidence.segment_kind);
  if (evidence.start_ms !== null || evidence.end_ms !== null) {
    return `${evidence.start_ms ?? "unknown"}–${evidence.end_ms ?? "unknown"} ms · ${kind}`;
  }
  if (evidence.start_char !== null || evidence.end_char !== null) {
    return `characters ${evidence.start_char ?? "unknown"}–${evidence.end_char ?? "unknown"} · ${kind}`;
  }
  return `Span not recorded · ${kind}`;
}

export function isNavCurrent(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function withCursor(path: string, params: Record<string, string | undefined>, cursor: string): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value && key !== "cursor") search.set(key, value);
  }
  search.set("cursor", cursor);
  return `${path}?${search.toString()}`;
}

export function documentTitle(prefix: string, detail: string, max = 72): string {
  const trimmed = detail.length > max ? `${detail.slice(0, max - 1)}…` : detail;
  return `${prefix}: ${trimmed}`;
}

export function identityGroup(state: string): "verified" | "machine" | "unestablished" {
  if (state === "human_verified") return "verified";
  if (state === "machine_validated") return "machine";
  return "unestablished";
}

export function missingValue(value: string | null | undefined, fallback = "Not stated"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return value;
}

export const RESEARCH_FILTER_KEYS = [
  "q",
  "person",
  "organization",
  "source",
  "topic",
  "statement_type",
  "review_state",
  "from",
  "to",
] as const;

export type ResearchFilterKey = (typeof RESEARCH_FILTER_KEYS)[number];
export type ResearchFilters = Partial<Record<ResearchFilterKey, string>>;

export function researchFilters(params: Record<string, string | undefined>): ResearchFilters {
  const filters: ResearchFilters = {};
  for (const key of RESEARCH_FILTER_KEYS) {
    const value = params[key]?.trim();
    if (value) filters[key] = value;
  }
  return filters;
}

export function filterStateKey(params: Record<string, string | undefined>): string {
  return RESEARCH_FILTER_KEYS.map((key) => `${key}=${params[key] ?? ""}`).join("&");
}

export function withResearch(
  path: string,
  filters: ResearchFilters,
  overrides: Partial<Record<ResearchFilterKey, string | null>> = {},
): string {
  const merged: ResearchFilters = { ...filters };
  for (const [key, value] of Object.entries(overrides) as Array<[ResearchFilterKey, string | null | undefined]>) {
    if (value === null || value === undefined || value === "") delete merged[key];
    else merged[key] = value;
  }
  const search = new URLSearchParams();
  for (const key of RESEARCH_FILTER_KEYS) {
    const value = merged[key];
    if (value) search.set(key, value);
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export function statementsHref(
  filters: ResearchFilters,
  overrides: Partial<Record<ResearchFilterKey, string | null>> = {},
): string {
  return withResearch("/statements", filters, overrides);
}

export function personResearchHref(slug: string, filters: ResearchFilters): string {
  return withResearch(`/people/${slug}`, filters, { person: null });
}

export function topicResearchHref(slug: string, filters: ResearchFilters): string {
  return withResearch(`/topics/${slug}`, filters, { topic: null });
}

export function hasNarrowingFilters(filters: ResearchFilters, kept: ResearchFilterKey): boolean {
  return RESEARCH_FILTER_KEYS.some((key) => key !== kept && Boolean(filters[key]));
}

export type HistoryPreview = {
  tone: "empty" | "complete" | "preview";
  summary: string;
};

/** Distinguish a complete list from the newest slice returned by a capped profile or topic query. */
export function historyPreview(shown: number, total: number): HistoryPreview {
  if (total <= 0 || shown <= 0) {
    return { tone: "empty", summary: "No public statement is collected for this view." };
  }
  if (shown >= total) {
    const summary = total === 1
      ? "All 1 public statement collected for this view is listed here."
      : `All ${total} public statements collected for this view are listed here.`;
    return { tone: "complete", summary };
  }
  const hidden = total - shown;
  const hiddenNoun = hidden === 1 ? "statement is" : "statements are";
  return {
    tone: "preview",
    summary: `This page lists ${shown} of ${total} public statements, newest by event time. ${hidden} older ${hiddenNoun} not on this page. This is a preview, not the complete history.`,
  };
}

export type TrendRankInput = {
  slug: string;
  name: string;
  kind: string;
  contributing_person_count: number;
  contributing_statement_count: number;
  calculated_at: string;
};

/**
 * Comparable questions sort ahead of volume.
 * Coverage is cohort members with a record, then statement count, then calculation time, then name.
 */
export function rankCoveredQuestions<T extends TrendRankInput>(trends: T[]): T[] {
  return [...trends].sort((a, b) => {
    const aVolume = a.kind === "volume" ? 1 : 0;
    const bVolume = b.kind === "volume" ? 1 : 0;
    if (aVolume !== bVolume) return aVolume - bVolume;
    if (b.contributing_person_count !== a.contributing_person_count) {
      return b.contributing_person_count - a.contributing_person_count;
    }
    if (b.contributing_statement_count !== a.contributing_statement_count) {
      return b.contributing_statement_count - a.contributing_statement_count;
    }
    const time = b.calculated_at.localeCompare(a.calculated_at);
    if (time !== 0) return time;
    return a.name.localeCompare(b.name) || a.slug.localeCompare(b.slug);
  });
}

export function selectFeaturedQuestion<T extends TrendRankInput>(trends: T[]): { featured: T | null; others: T[] } {
  const ranked = rankCoveredQuestions(trends);
  const featured = ranked.find((trend) => trend.kind !== "volume" && trend.contributing_statement_count > 0) ?? null;
  return { featured, others: ranked.filter((trend) => trend.slug !== featured?.slug) };
}

export function rankTopicsByCoverage<T extends { name: string; slug: string; statement_total: number }>(topics: T[]): T[] {
  return [...topics].sort((a, b) => {
    if (b.statement_total !== a.statement_total) return b.statement_total - a.statement_total;
    return a.name.localeCompare(b.name) || a.slug.localeCompare(b.slug);
  });
}

export function selectCoveredTopics<T extends { name: string; slug: string; statement_total: number }>(
  topics: T[],
  limit = 6,
): T[] {
  return rankTopicsByCoverage(topics).filter((topic) => topic.statement_total > 0).slice(0, limit);
}

export function revisionReading(type: string): { title: string; note: string } {
  switch (type) {
    case "updates":
      return {
        title: "Recorded change of view",
        note: "A later statement is linked as an update of an earlier one. This is not an overall belief score.",
      };
    case "retracts":
      return {
        title: "Recorded retraction",
        note: "A later statement is linked as a retraction of an earlier one. This is not an overall belief score.",
      };
    case "contradicts":
      return {
        title: "Recorded contradiction",
        note: "The statements are linked as a contradiction. This is not an overall belief score.",
      };
    case "clarifies":
      return {
        title: "Clarification",
        note: "A later statement clarifies an earlier one. That is not by itself a new probability.",
      };
    case "repeats":
      return {
        title: "Repetition",
        note: "The later statement repeats an earlier one. This is not a change of view.",
      };
    default:
      return {
        title: phraseLabel(type),
        note: "This is a recorded link between two statements, not a computed personal score.",
      };
  }
}

export function timeRelation(input: {
  published_at: string | null | undefined;
  observed_at: string | null | undefined;
}): { label: string; detail: string } {
  const published = input.published_at ?? null;
  const observed = input.observed_at ?? null;
  if (!published && !observed) {
    return { label: "Times unknown", detail: "Publication time and observation time are both unknown." };
  }
  if (!published) {
    return { label: "Publication unknown", detail: "An observation time is stored and the publication time is unknown." };
  }
  if (!observed) {
    return { label: "Observation unknown", detail: "A publication time is stored and the observation time is unknown." };
  }
  const publishedMs = Date.parse(published);
  const observedMs = Date.parse(observed);
  if (Number.isNaN(publishedMs) || Number.isNaN(observedMs)) {
    return { label: "Times unknown", detail: "A stored timestamp could not be read." };
  }
  const day = 24 * 60 * 60 * 1000;
  if (observedMs > publishedMs + day) {
    return {
      label: "Collected after publication",
      detail: "Observation is later than publication. The observatory collected existing material. That is not, by itself, a newly published statement.",
    };
  }
  if (publishedMs > observedMs + day) {
    return {
      label: "Publication after observation",
      detail: "The stored publication time is later than the observation time.",
    };
  }
  return {
    label: "Observed near publication",
    detail: "Publication and observation fall within one day of each other.",
  };
}

export function collectionReading(input: {
  last_success_at: string | null;
  last_checked_at: string | null;
  freshness: string;
}): { label: string; detail: string } {
  if (!input.last_success_at && !input.last_checked_at) {
    return {
      label: "Never checked",
      detail: "No collection check is recorded. That is a collection gap, not evidence that the channel is empty.",
    };
  }
  if (!input.last_success_at && input.last_checked_at) {
    return {
      label: "Check failed",
      detail: "A check was recorded and no successful collection is stored.",
    };
  }
  const successMs = input.last_success_at ? Date.parse(input.last_success_at) : Number.NaN;
  const checkedMs = input.last_checked_at ? Date.parse(input.last_checked_at) : Number.NaN;
  if (!Number.isNaN(successMs) && !Number.isNaN(checkedMs) && checkedMs > successMs + 1000) {
    return {
      label: freshnessLabel(input.freshness),
      detail: "A later check did not replace the last successful collection. The last success time is unchanged.",
    };
  }
  if (!input.last_success_at || Number.isNaN(successMs)) {
    return {
      label: "Collection time unknown",
      detail: "The last successful collection time could not be read.",
    };
  }
  return {
    label: freshnessLabel(input.freshness),
    detail: "This describes the last successful collection, not publication time and not whether anyone has spoken.",
  };
}

export type DatasetFingerprintInput = {
  imported_at?: string | null;
  statement_count?: number | null;
  latest_observed_at?: string | null;
  latest_published_at?: string | null;
  latest_successful_observation?: string | null;
  stale_sources?: number | null;
  failing_sources?: number | null;
};

export function datasetFingerprint(input: DatasetFingerprintInput): string {
  return [
    input.imported_at ?? "",
    input.statement_count ?? "",
    input.latest_observed_at ?? "",
    input.latest_published_at ?? "",
    input.latest_successful_observation ?? "",
    input.stale_sources ?? "",
    input.failing_sources ?? "",
  ].join("|");
}

export function fingerprintFromOverview(body: unknown): string {
  if (!body || typeof body !== "object") return datasetFingerprint({});
  const dataset = (body as { dataset?: unknown }).dataset;
  if (!dataset || typeof dataset !== "object") return datasetFingerprint({});
  const record = dataset as Record<string, unknown>;
  const coverage = record.coverage && typeof record.coverage === "object"
    ? record.coverage as Record<string, unknown>
    : {};
  const text = (value: unknown): string | null => (typeof value === "string" ? value : null);
  const count = (value: unknown): number | null => (typeof value === "number" && Number.isFinite(value) ? value : null);
  return datasetFingerprint({
    imported_at: text(record.imported_at),
    statement_count: count(record.statement_count),
    latest_observed_at: text(record.latest_observed_at),
    latest_published_at: text(record.latest_published_at),
    latest_successful_observation: text(coverage.latest_successful_observation),
    stale_sources: count(coverage.stale_sources),
    failing_sources: count(coverage.unavailable_or_failing_sources),
  });
}
