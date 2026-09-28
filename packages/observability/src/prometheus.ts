import { catalog } from "./catalog";
import { evaluate, type Alert } from "./evaluate";
import { counterSnapshot, databaseReadyFlag, histogramSnapshot } from "./metrics";
import { allowedLabel } from "./catalog";
import type { OperationalSnapshot } from "./snapshot";

const help = new Map(catalog.metrics.map((metric) => [metric.name, metric]));
const buckets = catalog.histogram_buckets_seconds;

export function renderPrometheus(snapshot: OperationalSnapshot, alerts?: Alert[]): string {
  emitted.clear();
  const firing = alerts ?? evaluate(snapshot).alerts;
  const lines: string[] = [];
  emitCounters(lines);
  emitHistograms(lines);
  emitGauge(lines, "pdoom_readiness", { check: "database" }, snapshot.readiness.database && databaseReadyFlag() ? 1 : 0);
  emitGauge(lines, "pdoom_cohort_size", {}, snapshot.cohort_size);
  emitGauge(lines, "pdoom_people_with_non_academic_source", {}, snapshot.people_with_non_academic_source);
  emitGauge(lines, "pdoom_statement_bearing_people", {}, snapshot.statement_bearing_people);
  emitGauge(lines, "pdoom_sources_due", {}, snapshot.sources_due);
  emitGauge(lines, "pdoom_collection_attempted", {}, snapshot.collection.attempted);
  emitGauge(lines, "pdoom_collection_succeeded", {}, snapshot.collection.succeeded);
  emitGauge(lines, "pdoom_collection_failed", {}, snapshot.collection.failed);
  emitGauge(lines, "pdoom_collection_unchanged", {}, snapshot.collection.unchanged);
  emitGauge(lines, "pdoom_collection_changed", {}, snapshot.collection.changed);
  emitGauge(lines, "pdoom_collection_new", {}, snapshot.collection.new);
  emitGauge(lines, "pdoom_extraction_items_processed", {}, snapshot.extraction.items_processed);
  emitGauge(lines, "pdoom_extraction_failures", {}, snapshot.extraction.failures);
  emitGauge(lines, "pdoom_extraction_missing_horizon_ratio", {}, ratio(snapshot.extraction.missing_horizon, snapshot.extraction.explicit_numeric));
  emitGauge(
    lines,
    "pdoom_extraction_missing_definition_ratio",
    {},
    ratio(snapshot.extraction.missing_definition, snapshot.extraction.explicit_numeric),
  );
  for (const state of catalog.labels.state) {
    emitGauge(lines, "pdoom_sources_freshness", { state }, snapshot.freshness[state as keyof typeof snapshot.freshness] ?? 0);
  }
  for (const review of ["unreviewed", "machine_validated", "human_verified", "rejected", "needs_review"] as const) {
    emitGauge(lines, "pdoom_statements", { review_state: review }, snapshot.statements_by_review[review]);
  }
  for (const statementType of ["explicit_numeric", "explicit_qualitative", "model_inferred_signal"] as const) {
    emitGauge(
      lines,
      "pdoom_extraction_candidates",
      { statement_type: statementType },
      snapshot.extraction.candidates_by_type[statementType],
    );
  }
  for (const check of catalog.labels.check) {
    emitGauge(lines, "pdoom_integrity_violations", { check }, snapshot.integrity[check as keyof typeof snapshot.integrity] ?? 0);
  }
  for (const alert of firing) {
    emitGauge(lines, "pdoom_alert_firing", { alert: allowedLabel("alert", alert.id, "other") }, alert.firing ? 1 : 0);
  }
  emitLabeledCounts(lines, "pdoom_sources_stale", "source_type", snapshot.stale_by_source_type);
  emitLabeledCounts(lines, "pdoom_sources_never_successful", "source_type", snapshot.never_successful_by_source_type);
  emitCollectionBreakdown(lines, snapshot);
  return `${lines.join("\n")}\n`;
}

function emitCounters(lines: string[]): void {
  const groups = new Map<string, Array<{ labels: Record<string, string>; value: number }>>();
  for (const row of counterSnapshot()) {
    const group = groups.get(row.name) ?? [];
    group.push({ labels: row.labels, value: row.value });
    groups.set(row.name, group);
  }
  for (const [name, series] of [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
    header(lines, name);
    for (const row of series.sort((a, b) => labelText(a.labels).localeCompare(labelText(b.labels)))) {
      lines.push(`${name}${labelText(row.labels)} ${formatNumber(row.value)}`);
    }
  }
}

function emitHistograms(lines: string[]): void {
  const groups = new Map<string, Array<{ labels: Record<string, string>; histogram: { buckets: number[]; sum: number; count: number } }>>();
  for (const row of histogramSnapshot()) {
    const group = groups.get(row.name) ?? [];
    group.push(row);
    groups.set(row.name, group);
  }
  for (const [name, series] of [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
    header(lines, name);
    for (const row of series.sort((a, b) => labelText(a.labels).localeCompare(labelText(b.labels)))) {
      for (let index = 0; index < buckets.length; index += 1) {
        const bound = buckets[index];
        const count = row.histogram.buckets[index] ?? 0;
        lines.push(`${name}_bucket${labelText({ ...row.labels, le: String(bound) })} ${count}`);
      }
      lines.push(`${name}_bucket${labelText({ ...row.labels, le: "+Inf" })} ${row.histogram.count}`);
      lines.push(`${name}_sum${labelText(row.labels)} ${formatNumber(row.histogram.sum)}`);
      lines.push(`${name}_count${labelText(row.labels)} ${row.histogram.count}`);
    }
  }
}

function emitCollectionBreakdown(lines: string[], snapshot: OperationalSnapshot): void {
  const runs = snapshot.collection.runs_by_adapter;
  const adapters = Object.keys(runs).sort();
  if (adapters.length) {
    header(lines, "pdoom_collection_runs");
    for (const adapter of adapters) {
      const counts = runs[adapter];
      if (!counts) continue;
      emitSeries(lines, "pdoom_collection_runs", { adapter, outcome: "succeeded" }, counts.succeeded);
      emitSeries(lines, "pdoom_collection_runs", { adapter, outcome: "failed" }, counts.failed);
    }
  }
  const failureAdapters = Object.keys(snapshot.collection.failures_by_adapter).sort();
  if (failureAdapters.length) {
    header(lines, "pdoom_collection_failures");
    for (const adapter of failureAdapters) {
      const classes = snapshot.collection.failures_by_adapter[adapter] ?? {};
      for (const failure of Object.keys(classes).sort()) {
        emitSeries(lines, "pdoom_collection_failures", { adapter, failure_class: failure }, classes[failure] ?? 0);
      }
    }
  } else if (Object.keys(snapshot.collection.failures_by_class).length) {
    header(lines, "pdoom_collection_failures");
    for (const failure of Object.keys(snapshot.collection.failures_by_class).sort()) {
      emitSeries(
        lines,
        "pdoom_collection_failures",
        { adapter: "other", failure_class: failure },
        snapshot.collection.failures_by_class[failure] ?? 0,
      );
    }
  }
  const rateAdapters = Object.keys(snapshot.collection.rate_limits_by_adapter).sort();
  header(lines, "pdoom_collection_rate_limits");
  if (rateAdapters.length) {
    for (const adapter of rateAdapters) {
      emitSeries(lines, "pdoom_collection_rate_limits", { adapter }, snapshot.collection.rate_limits_by_adapter[adapter] ?? 0);
    }
  } else {
    emitSeries(lines, "pdoom_collection_rate_limits", { adapter: "other" }, snapshot.collection.rate_limited);
  }
}

function emitLabeledCounts(lines: string[], name: string, label: string, counts: Record<string, number>): void {
  const keys = Object.keys(counts).filter((key) => (counts[key] ?? 0) > 0).sort();
  if (!keys.length) return;
  header(lines, name);
  for (const key of keys) {
    emitSeries(lines, name, { [label]: allowedLabel("source_type", key, "other") }, counts[key] ?? 0);
  }
}

function emitGauge(lines: string[], name: string, labels: Record<string, string>, value: number): void {
  header(lines, name);
  emitSeries(lines, name, labels, value);
}

function emitSeries(lines: string[], name: string, labels: Record<string, string>, value: number): void {
  lines.push(`${name}${labelText(labels)} ${formatNumber(value)}`);
}

const emitted = new Set<string>();

function header(lines: string[], name: string): void {
  if (emitted.has(name)) return;
  emitted.add(name);
  const meta = help.get(name);
  if (!meta) throw new Error(`unknown metric ${name}`);
  lines.push(`# HELP ${name} ${meta.help}`);
  lines.push(`# TYPE ${name} ${meta.type}`);
}

function labelText(labels: Record<string, string>): string {
  const keys = Object.keys(labels).filter((key) => key !== "le").sort();
  if (labels.le !== undefined) keys.push("le");
  if (!keys.length) return "";
  return `{${keys.map((key) => `${key}="${escapeLabel(labels[key] ?? "")}"`).join(",")}}`;
}

function escapeLabel(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\n/g, "").replace(/"/g, "");
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "0";
  return String(Math.round(value * 1_000_000) / 1_000_000);
}

function ratio(part: number, whole: number): number {
  if (whole <= 0) return 0;
  return part / whole;
}

export function resetPrometheusHeaders(): void {
  emitted.clear();
}
