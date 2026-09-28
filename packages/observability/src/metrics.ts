import { allowedLabel } from "./catalog";
import { catalog } from "./catalog";
import { statusClass } from "./normalize";

type Labels = Record<string, string>;

type Histogram = {
  buckets: number[];
  sum: number;
  count: number;
};

const counters = new Map<string, number>();
const histograms = new Map<string, Histogram>();
let databaseReady = true;
let importFailures = 0;

const buckets = catalog.histogram_buckets_seconds;

function seriesKey(name: string, labels: Labels): string {
  const encoded = Object.keys(labels)
    .sort()
    .map((key) => `${key}=${labels[key]}`)
    .join(",");
  return `${name}|${encoded}`;
}

function increment(name: string, labels: Labels, by = 1): void {
  const key = seriesKey(name, labels);
  counters.set(key, (counters.get(key) ?? 0) + by);
}

function observe(name: string, labels: Labels, seconds: number): void {
  const key = seriesKey(name, labels);
  const histogram = histograms.get(key) ?? { buckets: buckets.map(() => 0), sum: 0, count: 0 };
  const bounded = Math.min(Math.max(seconds, 0), 1_000_000);
  histogram.count += 1;
  histogram.sum += bounded;
  for (let index = 0; index < buckets.length; index += 1) {
    const bound = buckets[index];
    if (bound !== undefined && bounded <= bound) histogram.buckets[index] = (histogram.buckets[index] ?? 0) + 1;
  }
  histograms.set(key, histogram);
}

export function recordHttp(route: string, status: number, durationMs: number | null): void {
  const labels = {
    route: allowedLabel("route", route, "other"),
    status_class: statusClass(status),
  };
  increment("pdoom_http_requests_total", labels);
  if (status >= 500 && status < 600) increment("pdoom_http_errors_total", labels);
  if (durationMs !== null && Number.isFinite(durationMs) && durationMs >= 0) {
    observe("pdoom_http_request_duration_seconds", labels, durationMs / 1000);
  }
}

export function recordDbQuery(
  operation: string,
  outcome: "ok" | "error",
  durationMs: number,
  errorClass?: string,
): void {
  const op = allowedLabel("db_operation", operation, "other");
  increment("pdoom_db_queries_total", { operation: op, outcome: outcome === "error" ? "error" : "ok" });
  if (outcome === "ok") databaseReady = true;
  if (outcome === "error") {
    const error_class = allowedLabel("error_class", errorClass, "unknown");
    increment("pdoom_db_query_failures_total", { operation: op, error_class });
    if (error_class === "connection") databaseReady = false;
  }
  if (Number.isFinite(durationMs) && durationMs >= 0) {
    observe("pdoom_db_query_duration_seconds", { operation: op }, durationMs / 1000);
  }
}

export function setDatabaseReady(ready: boolean): void {
  databaseReady = ready;
}

export function databaseReadyFlag(): boolean {
  return databaseReady;
}

export function recordImportResult(outcome: "succeeded" | "failed"): void {
  importFailures = outcome === "succeeded" ? 0 : importFailures + 1;
}

export function importFailureStreak(): number {
  return importFailures;
}

export function resetMetrics(): void {
  counters.clear();
  histograms.clear();
  databaseReady = true;
  importFailures = 0;
}

export function counterSnapshot(): Array<{ name: string; labels: Labels; value: number }> {
  const rows: Array<{ name: string; labels: Labels; value: number }> = [];
  for (const [key, value] of counters) {
    const [name, encoded] = splitKey(key);
    rows.push({ name, labels: decodeLabels(encoded), value });
  }
  return rows;
}

export function histogramSnapshot(): Array<{ name: string; labels: Labels; histogram: Histogram }> {
  const rows: Array<{ name: string; labels: Labels; histogram: Histogram }> = [];
  for (const [key, histogram] of histograms) {
    const [name, encoded] = splitKey(key);
    rows.push({ name, labels: decodeLabels(encoded), histogram });
  }
  return rows;
}

function splitKey(key: string): [string, string] {
  const index = key.indexOf("|");
  return [key.slice(0, index), key.slice(index + 1)];
}

function decodeLabels(encoded: string): Labels {
  if (!encoded) return {};
  const labels: Labels = {};
  for (const part of encoded.split(",")) {
    const index = part.indexOf("=");
    if (index === -1) continue;
    labels[part.slice(0, index)] = part.slice(index + 1);
  }
  return labels;
}
