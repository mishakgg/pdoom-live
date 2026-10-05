/**
 * A calculation timestamp is not a historical reconstruction.
 * "Statements dated before X" and "information known and reviewed by X" stay separate.
 */

export const HISTORY_POLICY_VERSION = "forecast-history/1.0.0";

export type HistoryMode = "current_corpus" | "event_time_only" | "known_and_reviewed";

export type HistoryClaim = {
  policy_version: typeof HISTORY_POLICY_VERSION;
  mode: HistoryMode;
  presented_as_reconstruction: boolean;
  cutoff: string | null;
  note: string;
};

export type HistoryRecord = {
  statement_slug: string;
  event_time?: string | null;
  known_at?: string | null;
  reviewed_at?: string | null;
};

export type HistoryStatus =
  | "eligible"
  | "after_cutoff"
  | "dated_before_cutoff_but_not_known"
  | "not_reviewed_by_cutoff"
  | "missing_history";

export const CURRENT_CORPUS_HISTORY: HistoryClaim = {
  policy_version: HISTORY_POLICY_VERSION,
  mode: "current_corpus",
  presented_as_reconstruction: false,
  cutoff: null,
  note: "This view uses the current reviewed corpus. A calculation time or dataset import time is not a reconstruction of what was known on that date. A statement dated before a cutoff can still have been observed or reviewed later.",
};

function atOrBefore(value: string | null | undefined, cutoff: string): boolean | null {
  if (!value) return null;
  const time = Date.parse(value);
  const end = Date.parse(cutoff);
  if (Number.isNaN(time) || Number.isNaN(end)) return null;
  return time <= end;
}

export function classifyHistory(record: HistoryRecord, cutoff: string): HistoryStatus {
  const dated = atOrBefore(record.event_time, cutoff);
  const known = atOrBefore(record.known_at, cutoff);
  const reviewed = atOrBefore(record.reviewed_at, cutoff);
  if (dated === false || known === false || reviewed === false) return "after_cutoff";
  if (dated === true && known !== true) return "dated_before_cutoff_but_not_known";
  if (dated === true && known === true && reviewed !== true) return "not_reviewed_by_cutoff";
  if (dated === true && known === true && reviewed === true) return "eligible";
  return "missing_history";
}

export function historyClaimFor(input: { cutoff?: string | null; mode?: HistoryMode | null }): HistoryClaim {
  if (!input.cutoff || !input.mode || input.mode === "current_corpus") return CURRENT_CORPUS_HISTORY;
  if (input.mode === "event_time_only") {
    return {
      policy_version: HISTORY_POLICY_VERSION,
      mode: "event_time_only",
      presented_as_reconstruction: false,
      cutoff: input.cutoff,
      note: `Statements with event_time on or before ${input.cutoff} are not a reconstruction. Observation time and review time are not filtered, so this is not what was known and reviewed by that date.`,
    };
  }
  return {
    policy_version: HISTORY_POLICY_VERSION,
    mode: "known_and_reviewed",
    presented_as_reconstruction: true,
    cutoff: input.cutoff,
    note: `Included records have event time, observation time, and human review time on or before ${input.cutoff}. Records dated earlier but observed or reviewed later stay out.`,
  };
}

export function selectKnownByCutoff<T extends HistoryRecord>(records: T[], cutoff: string): {
  eligible: T[];
  excluded: Array<{ record: T; status: HistoryStatus }>;
  claim: HistoryClaim;
} {
  const eligible: T[] = [];
  const excluded: Array<{ record: T; status: HistoryStatus }> = [];
  for (const record of records) {
    const status = classifyHistory(record, cutoff);
    if (status === "eligible") eligible.push(record);
    else excluded.push({ record, status });
  }
  return { eligible, excluded, claim: historyClaimFor({ cutoff, mode: "known_and_reviewed" }) };
}
