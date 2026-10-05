import { readFile } from "node:fs/promises";
import { loadOperationalSnapshot } from "@pdoom/db";
import { getPool } from "@pdoom/db";
import {
  evaluate,
  logEvent,
  overlayProcessSignals,
  parseBaseline,
  renderPrometheus,
  resolveGuardrails,
  type QualityReport,
} from "@pdoom/observability";
import { singleFlight } from "./single-flight";

const TTL_MS = 15_000;

let cache: { at: number; report: QualityReport; metrics: string } | null = null;

export function resetOperationalCache(): void {
  cache = null;
}

async function loadReport(): Promise<QualityReport> {
  const asOf = new Date().toISOString();
  const snapshot = overlayProcessSignals(
    await loadOperationalSnapshot(getPool(), {
      asOf,
      windowHours: resolveGuardrails().collection_success_window_hours,
    }),
  );
  const report = evaluate(snapshot, { baseline: await baselineFromEnv(), scope: "database", now: new Date(asOf) });
  cache = { at: Date.now(), report, metrics: renderPrometheus(snapshot, report.alerts) };
  return report;
}

export async function operationalReport(load: () => Promise<QualityReport> = loadReport): Promise<QualityReport> {
  const now = Date.now();
  if (cache && now - cache.at < TTL_MS) return cache.report;
  return singleFlight("operational", async () => {
    const current = Date.now();
    if (cache && current - cache.at < TTL_MS) return cache.report;
    const report = await load();
    if (!cache || Date.now() - cache.at >= TTL_MS) {
      cache = { at: Date.now(), report, metrics: "" };
    }
    return cache.report;
  });
}

export async function operationalMetrics(): Promise<string> {
  await operationalReport();
  return cache?.metrics ?? "";
}

async function baselineFromEnv() {
  const path = process.env.PDOOM_QUALITY_BASELINE;
  if (!path) return null;
  try {
    return parseBaseline(JSON.parse(await readFile(path, "utf8")));
  } catch {
    logEvent({ level: "warn", operation: "baseline", outcome: "failed", error_class: "unknown" });
    return null;
  }
}
