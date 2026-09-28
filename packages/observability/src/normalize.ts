import { allowedLabel, catalog } from "./catalog";

const cadenceTable: Record<string, number> = catalog.cadence_days;
const cadenceMethods = new Set<string>(catalog.cadence_methods);

export type FreshnessState = "current" | "aging" | "stale" | "never_checked";

export function normalizeAdapter(value: string | null | undefined): string {
  const text = (value ?? "").toLowerCase();
  if (text.includes("openalex")) return "openalex";
  if (text.includes("arxiv")) return "arxiv";
  if (text.includes("github")) return "github";
  if (text.includes("rss") || text.includes("atom")) return "rss";
  if (text.includes("fixture") || text.includes("synthetic")) return "fixture";
  if (text.includes("sitemap")) return "sitemap";
  if (text.includes("manual")) return "manual";
  if (text.includes("api")) return "api";
  return "other";
}

export function failureClass(value: string | null | undefined): string {
  return allowedLabel("failure_class", value, "unclassified");
}

export function classifyAge(lastSuccessAt: string | null | undefined, asOf: string): FreshnessState {
  if (!lastSuccessAt) return "never_checked";
  const days = ageDays(lastSuccessAt, asOf);
  if (days === null) return "never_checked";
  if (days <= catalog.freshness_days.current) return "current";
  if (days <= catalog.freshness_days.aging) return "aging";
  return "stale";
}

export function ageDays(timestamp: string | null | undefined, asOf: string): number | null {
  if (!timestamp) return null;
  const at = Date.parse(timestamp);
  const end = Date.parse(asOf);
  if (Number.isNaN(at) || Number.isNaN(end)) return null;
  return (end - at) / 86_400_000;
}

export function ageHours(timestamp: string | null | undefined, asOf: string): number | null {
  const days = ageDays(timestamp, asOf);
  return days === null ? null : days * 24;
}

export function cadenceDays(sourceType: string, method: string): number | null {
  if (!cadenceMethods.has(method)) return null;
  return cadenceTable[sourceType] ?? cadenceTable.default ?? 14;
}

export function inWindow(timestamp: string | null | undefined, asOf: string, windowHours: number): boolean {
  if (!timestamp) return false;
  const at = Date.parse(timestamp);
  const end = Date.parse(asOf);
  if (Number.isNaN(at) || Number.isNaN(end)) return false;
  return at >= end - windowHours * 3_600_000 && at <= end;
}

export function statusClass(status: number): string {
  if (status >= 200 && status < 300) return "2xx";
  if (status >= 300 && status < 400) return "3xx";
  if (status >= 400 && status < 500) return "4xx";
  if (status >= 500 && status < 600) return "5xx";
  return "unobserved";
}

export function laterIso(left: string | null, right: string | null): string | null {
  if (!left) return right;
  if (!right) return left;
  const a = Date.parse(left);
  const b = Date.parse(right);
  if (Number.isNaN(a)) return Number.isNaN(b) ? null : right;
  if (Number.isNaN(b)) return left;
  return a >= b ? left : right;
}
