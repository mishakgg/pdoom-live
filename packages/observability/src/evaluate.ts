import { catalog, type Guardrails } from "./catalog";
import { createCorrelationId } from "./correlation";
import { ageHours } from "./normalize";
import {
  completeSnapshot,
  publicStatementCount,
  statementTotal,
  type OperationalSnapshot,
} from "./snapshot";

export type Severity = "error" | "warning" | "info";
export type ReportScope = "database" | "document" | "snapshot";

export type Finding = {
  id: string;
  severity: Severity;
  summary: string;
  count: number | null;
};

export type SloStatus = "met" | "breach" | "not_applicable";

export type SloResult = {
  id: string;
  status: SloStatus;
  target: number;
  value: number | null;
  summary: string;
};

export type Alert = {
  id: string;
  severity: "critical" | "warning";
  firing: boolean;
  summary: string;
};

export type PublicStatus = {
  app: "operational" | "unavailable";
  dataset: "current" | "aging" | "stale" | "not_loaded" | "unknown";
  dataset_kind: "live" | "synthetic" | "unknown";
  dataset_generated_at: string | null;
  latest_successful_observation: string | null;
  freshness: {
    current: number;
    aging: number;
    stale: number;
    never_checked: number;
  };
};

export type Baseline = {
  cohort_size?: number;
  source_count?: number;
  statement_count?: number;
  human_verified_statements?: number;
  machine_validated_statements?: number;
  stale_ratio?: number;
};

export type QualityReport = {
  ok: boolean;
  run_id: string;
  scope: ReportScope;
  generated_at: string;
  dataset_kind: "live" | "synthetic" | "unknown";
  status: PublicStatus;
  findings: Finding[];
  alerts: Alert[];
  slos: SloResult[];
  counts: Record<string, number>;
  summary: string;
};

export type EvaluateOptions = {
  baseline?: Baseline | null;
  guardrails?: Partial<Guardrails>;
  runId?: string;
  scope?: ReportScope;
  now?: Date;
};

const alertOrder = catalog.labels.alert;

export function resolveGuardrails(override?: Partial<Guardrails>): Guardrails {
  const next: Guardrails = { ...catalog.guardrails };
  if (!override) return next;
  for (const key of Object.keys(catalog.guardrails) as Array<keyof Guardrails>) {
    const value = override[key];
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) continue;
    if (key.endsWith("_ratio") && value > 1) continue;
    next[key] = value;
  }
  return next;
}

export function parseBaseline(raw: unknown): Baseline {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("baseline must be a JSON object of counts");
  }
  const source = raw as Record<string, unknown>;
  const baseline: Baseline = {};
  const keys: Array<keyof Baseline> = [
    "cohort_size",
    "source_count",
    "statement_count",
    "human_verified_statements",
    "machine_validated_statements",
    "stale_ratio",
  ];
  for (const key of keys) {
    if (!(key in source)) continue;
    const value = source[key];
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
      throw new Error("baseline counts must be non-negative numbers");
    }
    if (key === "stale_ratio" && value > 1) throw new Error("baseline stale_ratio must be between 0 and 1");
    baseline[key] = value;
  }
  return baseline;
}

export function publicStatus(snapshot: OperationalSnapshot): PublicStatus {
  const freshness = snapshot.freshness;
  if (snapshot.database_checked && !snapshot.readiness.database) {
    return {
      app: "unavailable",
      dataset: "unknown",
      dataset_kind: snapshot.dataset_kind,
      dataset_generated_at: null,
      latest_successful_observation: null,
      freshness: { current: 0, aging: 0, stale: 0, never_checked: 0 },
    };
  }
  return {
    app: "operational",
    dataset: datasetState(snapshot),
    dataset_kind: snapshot.dataset_kind,
    dataset_generated_at: snapshot.dataset_generated_at,
    latest_successful_observation: snapshot.latest_successful_observation,
    freshness,
  };
}

export function evaluate(partial: Partial<OperationalSnapshot> = {}, options: EvaluateOptions = {}): QualityReport {
  const snapshot = completeSnapshot(partial);
  const guardrails = resolveGuardrails(options.guardrails);
  const findings: Finding[] = [];
  const live = snapshot.dataset_kind === "live";

  if (snapshot.database_checked && !snapshot.readiness.database) {
    findings.push(finding("database_unavailable", "error", "Database readiness check failed.", null));
  } else {
    evaluateDataset(snapshot, options.baseline ?? null, guardrails, live, findings);
  }

  if (!snapshot.canonical_valid) {
    findings.push(finding("canonical_validation_failed", "error", "Canonical import failed validation.", 1));
  }
  if (snapshot.import_failure_streak >= guardrails.import_failure_streak && snapshot.import_failure_streak > 0) {
    findings.push(
      finding(
        "imports_repeatedly_fail",
        "error",
        `Imports failed ${snapshot.import_failure_streak} times in a row.`,
        snapshot.import_failure_streak,
      ),
    );
  }

  const slos = buildSlos(snapshot, findings);
  const alerts = buildAlerts(findings);
  const status = publicStatus(snapshot);
  const report: QualityReport = {
    ok: !findings.some((item) => item.severity === "error"),
    run_id: options.runId ?? createCorrelationId(),
    scope: options.scope ?? "snapshot",
    generated_at: (options.now ?? new Date()).toISOString(),
    dataset_kind: snapshot.dataset_kind,
    status,
    findings,
    alerts,
    slos,
    counts: countsOf(snapshot),
    summary: "",
  };
  report.summary = renderSummary(report);
  return report;
}

export function qualityExitCode(report: QualityReport, strict = false): number {
  if (!report.ok) return 1;
  if (strict && report.findings.some((item) => item.severity === "warning")) return 1;
  return 0;
}

function evaluateDataset(
  snapshot: OperationalSnapshot,
  baseline: Baseline | null,
  guardrails: Guardrails,
  live: boolean,
  findings: Finding[],
): void {
  if (!snapshot.dataset_present) {
    findings.push(finding("dataset_not_loaded", "warning", "No current dataset import is loaded.", null));
  } else if (snapshot.cohort_size === 0) {
    findings.push(finding("cohort_empty", "error", "The current dataset cohort has no members.", 0));
  }

  const enabled = snapshot.enabled_source_count;
  const enabledFresh = snapshot.enabled_freshness;
  const allStale = enabled > 0 && enabledFresh.current === 0 && enabledFresh.aging === 0;
  if (allStale) {
    findings.push(
      finding(
        "all_sources_stale",
        live ? "error" : "info",
        live
          ? "Every enabled cohort source is stale or has never succeeded."
          : "Enabled sources are stale or unchecked. Synthetic and fixture timestamps are not a live incident.",
        enabled,
      ),
    );
  }

  const stopped = live && snapshot.slo.cadence_eligible > 0 && snapshot.collection.succeeded === 0;
  if (snapshot.slo.cadence_eligible > 0 && snapshot.collection.succeeded === 0) {
    findings.push(
      finding(
        "collection_stopped",
        stopped ? "error" : "info",
        stopped
          ? "No collection run succeeded inside the expected window."
          : "No collection run succeeded inside the window. This dataset is not on a live collection clock.",
        snapshot.collection.attempted,
      ),
    );
  }

  if (snapshot.collection.rate_limited > 0) {
    findings.push(
      finding(
        "collection_rate_limited",
        live ? "warning" : "info",
        `Rate limiting was recorded ${snapshot.collection.rate_limited} times.`,
        snapshot.collection.rate_limited,
      ),
    );
  }

  pushIntegrity(snapshot, findings);
  pushRegression(snapshot, baseline, guardrails, findings);
  pushExtraction(snapshot, guardrails, findings);
  pushFreshnessWarning(snapshot, baseline, guardrails, live, allStale, findings);

  findings.push(
    finding(
      "freshness_distribution",
      "info",
      `Freshness is current ${snapshot.freshness.current}, aging ${snapshot.freshness.aging}, stale ${snapshot.freshness.stale}, never checked ${snapshot.freshness.never_checked}.`,
      snapshot.source_count,
    ),
  );
  findings.push(
    finding(
      "coverage_summary",
      "info",
      `Cohort ${snapshot.cohort_size}, sources ${snapshot.source_count}, statement-bearing people ${snapshot.statement_bearing_people}, human-verified ${snapshot.statements_by_review.human_verified}, machine-validated ${snapshot.statements_by_review.machine_validated}, needs review ${snapshot.statements_by_review.needs_review}, unresolved ${snapshot.statements_by_review.unreviewed}.`,
      snapshot.cohort_size,
    ),
  );
  if (!baseline) {
    findings.push(
      finding(
        "baseline_not_configured",
        "info",
        "No baseline file was provided, so relative dataset-size guardrails were not applied.",
        null,
      ),
    );
  }
}

function pushIntegrity(snapshot: OperationalSnapshot, findings: Finding[]): void {
  const checks: Array<[keyof OperationalSnapshot["integrity"], string]> = [
    ["duplicate_identity_ids", "Duplicate external identity ids are present."],
    ["multiple_current_versions", "More than one current version exists for a source item."],
    ["human_verified_missing_evidence", "A human-verified statement is missing evidence."],
    ["numeric_without_numeric_evidence", "An explicit numeric statement has no numeric value or no digit in its evidence."],
    ["impossible_probability", "A probability forecast is outside 0–1 or has a minimum above its maximum."],
    ["public_statement_unavailable_source", "A public statement points at an unavailable source without an explicit availability state."],
  ];
  for (const [id, summary] of checks) {
    const count = snapshot.integrity[id];
    if (count > 0) findings.push(finding(id, "error", summary, count));
  }
}

function pushRegression(
  snapshot: OperationalSnapshot,
  baseline: Baseline | null,
  guardrails: Guardrails,
  findings: Finding[],
): void {
  if (!baseline) return;
  const currentStatements = statementTotal(snapshot);
  warnDrop("cohort_drop", "Cohort size", baseline.cohort_size, snapshot.cohort_size, guardrails.cohort_drop_ratio, findings);
  warnDrop("source_count_drop", "Source count", baseline.source_count, snapshot.source_count, guardrails.source_drop_ratio, findings);
  warnDrop(
    "statement_count_drop",
    "Statement count",
    baseline.statement_count,
    currentStatements,
    guardrails.statement_drop_ratio,
    findings,
  );
  warnDrop(
    "human_verified_drop",
    "Human-verified statements",
    baseline.human_verified_statements,
    snapshot.statements_by_review.human_verified,
    guardrails.human_verified_drop_ratio,
    findings,
  );
  const grew =
    greater(snapshot.cohort_size, baseline.cohort_size) ||
    greater(snapshot.source_count, baseline.source_count) ||
    greater(currentStatements, baseline.statement_count);
  if (grew) {
    findings.push(finding("dataset_growth", "info", "Dataset counts grew relative to the baseline.", null));
  }
  const publicNow = publicStatementCount(snapshot);
  const publicBase = (baseline.human_verified_statements ?? 0) + (baseline.machine_validated_statements ?? 0);
  if (publicBase > 0 && publicNow === 0) {
    findings.push(
      finding(
        "public_verified_dataset_empty",
        "error",
        "Human-verified and machine-validated statements dropped to zero from a non-empty baseline.",
        0,
      ),
    );
  }
}

function pushExtraction(snapshot: OperationalSnapshot, guardrails: Guardrails, findings: Finding[]): void {
  const processed = snapshot.extraction.items_processed;
  if (processed >= guardrails.extractor_failure_min_processed) {
    const rate = snapshot.extraction.failures / processed;
    if (rate > guardrails.extractor_failure_ratio) {
      findings.push(
        finding(
          "extractor_failure_rate",
          "warning",
          `Extraction failed for ${formatRatio(rate)} of ${processed} runs in the window.`,
          snapshot.extraction.failures,
        ),
      );
    }
  }
  const numeric = snapshot.extraction.explicit_numeric;
  if (numeric > 0) {
    const horizon = snapshot.extraction.missing_horizon / numeric;
    const definition = snapshot.extraction.missing_definition / numeric;
    if (horizon > guardrails.missing_horizon_ratio) {
      findings.push(
        finding(
          "missing_horizon_rate",
          "warning",
          `${formatRatio(horizon)} of explicit numeric statements have no horizon.`,
          snapshot.extraction.missing_horizon,
        ),
      );
    }
    if (definition > guardrails.missing_definition_ratio) {
      findings.push(
        finding(
          "missing_definition_rate",
          "warning",
          `${formatRatio(definition)} of explicit numeric statements have no definition.`,
          snapshot.extraction.missing_definition,
        ),
      );
    }
  }
}

function pushFreshnessWarning(
  snapshot: OperationalSnapshot,
  baseline: Baseline | null,
  guardrails: Guardrails,
  live: boolean,
  allStale: boolean,
  findings: Finding[],
): void {
  if (!live || snapshot.enabled_source_count === 0 || allStale) return;
  const ratio = snapshot.sources_stale / snapshot.enabled_source_count;
  const spiked = baseline?.stale_ratio !== undefined && ratio - baseline.stale_ratio > guardrails.stale_ratio_increase;
  if (ratio > guardrails.stale_source_ratio || spiked) {
    findings.push(
      finding(
        "stale_source_ratio",
        "warning",
        `${formatRatio(ratio)} of enabled cohort sources are stale.`,
        snapshot.sources_stale,
      ),
    );
  }
}

function buildSlos(snapshot: OperationalSnapshot, findings: Finding[]): SloResult[] {
  const live = snapshot.dataset_kind === "live" && snapshot.readiness.database;
  const cadenceTarget = catalog.slos.enabled_sources_within_cadence.target;
  const ageTarget = catalog.slos.latest_successful_collection_age_hours.target;
  const freshTarget = catalog.slos.statement_bearing_sources_fresh.target;
  const cadence = ratioSlo(
    "enabled_sources_within_cadence",
    live && snapshot.slo.cadence_eligible > 0,
    snapshot.slo.cadence_met,
    snapshot.slo.cadence_eligible,
    cadenceTarget,
    "Share of enabled rss, api, and sitemap sources successfully checked inside their cadence.",
  );
  const ageValue = ageHours(snapshot.latest_successful_observation, snapshot.as_of);
  const ageApplicable = live && snapshot.slo.cadence_eligible > 0;
  const ageBreached = ageApplicable && (ageValue === null || ageValue > ageTarget);
  const age: SloResult = {
    id: "latest_successful_collection_age_hours",
    status: !ageApplicable ? "not_applicable" : ageBreached ? "breach" : "met",
    target: ageTarget,
    value: ageApplicable ? ageValue : null,
    summary: "Age in hours of the latest successful collection. A stale source does not mean the researcher is inactive.",
  };
  const fresh = ratioSlo(
    "statement_bearing_sources_fresh",
    live && snapshot.slo.statement_bearing_sources > 0,
    snapshot.slo.statement_bearing_sources_fresh,
    snapshot.slo.statement_bearing_sources,
    freshTarget,
    "Share of statement-bearing cohort sources that are current or aging. A stale source does not mean the researcher is inactive.",
  );
  for (const slo of [cadence, age, fresh]) {
    if (slo.status === "breach") {
      findings.push(finding(slo.id, "warning", `${slo.summary} Target ${slo.target}, value ${slo.value ?? "none"}.`, null));
    }
  }
  return [cadence, age, fresh];
}

function buildAlerts(findings: Finding[]): Alert[] {
  const has = (id: string, severity?: Severity) =>
    findings.some((item) => item.id === id && (severity === undefined || item.severity === severity));
  const specs: Array<{ id: string; severity: "critical" | "warning"; firing: boolean; summary: string }> = [
    {
      id: "collection_stopped",
      severity: "critical",
      firing: has("collection_stopped", "error"),
      summary: "Collection produced no successful run inside the expected window.",
    },
    {
      id: "database_unavailable",
      severity: "critical",
      firing: has("database_unavailable", "error"),
      summary: "The database readiness check failed.",
    },
    {
      id: "imports_repeatedly_fail",
      severity: "critical",
      firing: has("imports_repeatedly_fail", "error"),
      summary: "Canonical imports are failing repeatedly.",
    },
    {
      id: "stale_source_percentage_spike",
      severity: "warning",
      firing: has("stale_source_ratio", "warning") || has("all_sources_stale", "error"),
      summary: "The share of stale enabled sources is above the guardrail.",
    },
    {
      id: "extractor_failure_rate_spike",
      severity: "warning",
      firing: has("extractor_failure_rate", "warning"),
      summary: "The extraction failure rate is above the guardrail.",
    },
    {
      id: "canonical_validation_failed",
      severity: "critical",
      firing: has("canonical_validation_failed", "error"),
      summary: "A canonical dataset document failed validation.",
    },
    {
      id: "public_verified_dataset_empty",
      severity: "critical",
      firing: has("public_verified_dataset_empty", "error"),
      summary: "The public verified statement set dropped to empty.",
    },
  ];
  return alertOrder.map((id) => {
    const spec = specs.find((item) => item.id === id);
    return spec ?? { id, severity: "warning" as const, firing: false, summary: "Alert is not configured." };
  });
}

function countsOf(snapshot: OperationalSnapshot): Record<string, number> {
  return {
    cohort_size: snapshot.cohort_size,
    source_count: snapshot.source_count,
    enabled_source_count: snapshot.enabled_source_count,
    sources_due: snapshot.sources_due,
    sources_stale: snapshot.sources_stale,
    sources_never_successful: snapshot.sources_never_successful,
    statement_bearing_people: snapshot.statement_bearing_people,
    people_with_non_academic_source: snapshot.people_with_non_academic_source,
    human_verified: snapshot.statements_by_review.human_verified,
    machine_validated: snapshot.statements_by_review.machine_validated,
    needs_review: snapshot.statements_by_review.needs_review,
    unreviewed: snapshot.statements_by_review.unreviewed,
    statements: statementTotal(snapshot),
    collection_attempted: snapshot.collection.attempted,
    collection_succeeded: snapshot.collection.succeeded,
    collection_failed: snapshot.collection.failed,
    collection_unchanged: snapshot.collection.unchanged,
    collection_changed: snapshot.collection.changed,
    collection_new: snapshot.collection.new,
    collection_rate_limited: snapshot.collection.rate_limited,
    extraction_processed: snapshot.extraction.items_processed,
    extraction_failures: snapshot.extraction.failures,
    explicit_numeric: snapshot.extraction.explicit_numeric,
  };
}

function renderSummary(report: QualityReport): string {
  const errors = report.findings.filter((item) => item.severity === "error").length;
  const warnings = report.findings.filter((item) => item.severity === "warning").length;
  const info = report.findings.filter((item) => item.severity === "info").length;
  const lines = [
    `quality check (${report.scope}): ${report.ok ? "ok" : "failed"}`,
    `errors: ${errors}`,
    `warnings: ${warnings}`,
    `info: ${info}`,
    "",
  ];
  for (const item of report.findings) {
    lines.push(`${item.severity.padEnd(8)} ${item.id}  ${item.summary}`);
  }
  lines.push("", "alerts:");
  const firing = report.alerts.filter((alert) => alert.firing);
  if (firing.length === 0) lines.push("none firing");
  for (const alert of firing) {
    lines.push(`firing   ${alert.severity}  ${alert.id}  ${alert.summary}`);
  }
  lines.push("", "service objectives:");
  for (const slo of report.slos) {
    lines.push(`${slo.status.padEnd(16)} ${slo.id}  ${slo.summary}`);
  }
  return lines.join("\n");
}

function datasetState(snapshot: OperationalSnapshot): PublicStatus["dataset"] {
  if (!snapshot.dataset_present) return "not_loaded";
  const enabled = snapshot.enabled_source_count;
  if (enabled === 0) return "unknown";
  const fresh = snapshot.enabled_freshness;
  if (fresh.current / enabled >= 0.8) return "current";
  if ((fresh.current + fresh.aging) / enabled >= 0.8) return "aging";
  return "stale";
}

function ratioSlo(
  id: string,
  applicable: boolean,
  numerator: number,
  denominator: number,
  target: number,
  summary: string,
): SloResult {
  if (!applicable || denominator <= 0) {
    return { id, status: "not_applicable", target, value: null, summary };
  }
  const value = numerator / denominator;
  return { id, status: value + 1e-12 >= target ? "met" : "breach", target, value, summary };
}

function warnDrop(
  id: string,
  label: string,
  baseline: number | undefined,
  current: number,
  limit: number,
  findings: Finding[],
): void {
  if (baseline === undefined || baseline <= 0 || current >= baseline) return;
  const drop = (baseline - current) / baseline;
  if (drop > limit) {
    findings.push(
      finding(id, "warning", `${label} fell from ${baseline} to ${current} (${formatRatio(drop)}).`, current),
    );
  }
}

function greater(current: number, baseline: number | undefined): boolean {
  return baseline !== undefined && current > baseline;
}

function finding(id: string, severity: Severity, summary: string, count: number | null): Finding {
  return { id, severity, summary, count };
}

function formatRatio(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}
