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
