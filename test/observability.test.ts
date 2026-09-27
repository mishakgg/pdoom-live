import { readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { FRESHNESS_THRESHOLDS, classifyFreshness } from "@pdoom/contracts";
import { getPool } from "@pdoom/db";
import { runQualityCheck } from "../packages/db/src/quality-command";
import { snapshotFromDocument } from "../packages/db/src/operational-snapshot";
import { validateDocument } from "../packages/db/src/import";
import { fixturePath } from "../packages/db/src/paths";
import {
  catalog,
  classifyAge,
  completeSnapshot,
  evaluate,
  formatLog,
  metricNames,
  qualityExitCode,
  recordHttp,
  renderPrometheus,
  resetMetrics,
  setLogSink,
  type QualityReport,
} from "@pdoom/observability";
import { GET as getHealth } from "../apps/web/app/api/health/route";
import { GET as getMetrics } from "../apps/web/app/api/metrics/route";
import { GET as getStatus } from "../apps/web/app/api/status/route";
import { resetOperationalCache } from "../apps/web/lib/operational";
import scenariosFile from "../data/fixtures/observability/scenarios.json";
import { afterEach, describe, expect, it } from "vitest";

const SECRET_SAMPLES = [
  "postgres://",
  "Bearer ",
  "Ignore previous",
  "super-secret-token",
  "content_hash_input",
  "SELECT ",
];

type Scenario = {
  id: string;
  snapshot: Record<string, unknown>;
  baseline?: Record<string, number>;
  expect_ok: boolean;
  expect_error_ids: string[];
  expect_warning_ids: string[];
  expect_alert_ids: string[];
  expect_info_ids?: string[];
};

const scenarios = scenariosFile.scenarios as Scenario[];

afterEach(() => {
  setLogSink(null);
  resetMetrics();
  resetOperationalCache();
  delete process.env.PDOOM_METRICS_ENABLED;
  delete process.env.PDOOM_METRICS_TOKEN;
  delete process.env.PDOOM_QUALITY_BASELINE;
});

describe("observability scenarios", () => {
  it.each(scenarios.map((scenario) => [scenario.id, scenario] as const))("%s", (_id, scenario) => {
    const report = evaluate(scenario.snapshot, {
      baseline: scenario.baseline ?? null,
      scope: "snapshot",
      runId: "scenario1234",
    });
    expect(report.ok).toBe(scenario.expect_ok);
    expect(ids(report, "error")).toEqual([...scenario.expect_error_ids].sort());
    expect(ids(report, "warning")).toEqual([...scenario.expect_warning_ids].sort());
    expect(report.alerts.filter((alert) => alert.firing).map((alert) => alert.id).sort()).toEqual(
      [...scenario.expect_alert_ids].sort(),
    );
    for (const infoId of scenario.expect_info_ids ?? []) {
      expect(ids(report, "info")).toContain(infoId);
    }
    const blob = JSON.stringify(report);
    for (const sample of SECRET_SAMPLES) expect(blob).not.toContain(sample);
  });

  it("treats warnings as non-fatal unless strict", () => {
    const rateLimited = scenarios.find((scenario) => scenario.id === "rate_limited");
    expect(rateLimited).toBeTruthy();
    const report = evaluate(rateLimited?.snapshot ?? {}, { scope: "snapshot", runId: "strict12345" });
    expect(qualityExitCode(report, false)).toBe(0);
    expect(qualityExitCode(report, true)).toBe(1);
    const growth = scenarios.find((scenario) => scenario.id === "harmless_growth");
    const grown = evaluate(growth?.snapshot ?? {}, { baseline: growth?.baseline ?? null, scope: "snapshot" });
    expect(grown.ok).toBe(true);
    expect(ids(grown, "warning")).toEqual([]);
    expect(qualityExitCode(grown, true)).toBe(0);
  });
});

describe("metric safety", () => {
  it("keeps labels bounded and omits sensitive values", () => {
    resetMetrics();
    for (let index = 0; index < 50; index += 1) {
      recordHttp(`https://person-${index}.example/secret-token`, 500, 3);
    }
    const text = renderPrometheus(
      completeSnapshot({ dataset_present: true, dataset_kind: "synthetic", cohort_size: 3, readiness: { database: true } }),
    );
    expect(text).not.toContain("person-");
    expect(text).not.toContain("secret-token");
    expect(text).toContain('route="other"');
    expect(text).toContain("pdoom_cohort_size");
    expect(text).toContain("pdoom_readiness");
    for (const line of text.split("\n")) {
      if (!line.startsWith("pdoom_")) continue;
      const name = line.split("{")[0]?.split(" ")[0] ?? "";
      const base = name.replace(/_(bucket|sum|count)$/, "");
      expect(metricNames.has(base), name).toBe(true);
      for (const match of line.matchAll(/([a-z_]+)="([^"]*)"/g)) {
        const value = match[2] ?? "";
        expect(value).toMatch(/^[A-Za-z0-9_+.:-]{1,80}$/);
        expect(value.toLowerCase()).not.toContain("postgres");
        expect(value.toLowerCase()).not.toContain("select");
      }
    }
  });

  it("records http observations cheaply and does not log them", () => {
    const lines: string[] = [];
    setLogSink((line) => lines.push(line));
    resetMetrics();
    const iterations = 20_000;
    const started = performance.now();
    for (let index = 0; index < iterations; index += 1) recordHttp("api", 200, 1);
    const perCallMs = (performance.now() - started) / iterations;
    expect(perCallMs).toBeLessThan(0.2);
    expect(lines).toEqual([]);
  });

  it("does not log sql, evidence, or secrets from a failed query", async () => {
    const lines: string[] = [];
    setLogSink((line) => lines.push(line));
    const pool = getPool();
    await pool.query("SELECT 1");
    expect(lines).toEqual([]);
    await expect(
      pool.query("SELECT 'Ignore previous instructions' AS evidence FROM missing_table_observability"),
    ).rejects.toBeTruthy();
    const blob = lines.join("\n");
    expect(blob).toContain("db_query");
    expect(blob).not.toContain("Ignore previous");
    expect(blob).not.toContain("missing_table_observability");
    expect(blob.toLowerCase()).not.toContain("select");
    expect(blob).not.toContain("postgres://");
  });
});

describe("structured logs", () => {
  it("keeps only stable fields", () => {
    const line = formatLog({
      level: "error",
      operation: "postgres://user:pass@db.internal:5432/pdoom",
      outcome: "Ignore previous instructions",
      adapter: "https://user:pass@adapter.example/token",
      error_class: "Bearer secret-token",
      request_id: "request-id-ok",
      duration_ms: 12,
    });
    expect(line).not.toContain("postgres://");
    expect(line).not.toContain("Ignore previous");
    expect(line).not.toContain("Bearer");
    expect(line).not.toContain("user:pass");
    expect(line).toContain("request-id-ok");
    expect(line).not.toContain("db.internal");
  });
});

describe("freshness and canonical checks", () => {
  it("uses the same freshness day bounds as the product", () => {
    expect(catalog.freshness_days.current).toBe(FRESHNESS_THRESHOLDS.current_days);
    expect(catalog.freshness_days.aging).toBe(FRESHNESS_THRESHOLDS.aging_days);
    const asOf = "2026-09-27T00:00:00.000Z";
    for (const last of [null, "2026-09-20T00:00:00.000Z", "2026-09-01T00:00:00.000Z", "2026-01-01T00:00:00.000Z"]) {
      expect(classifyAge(last, asOf)).toBe(classifyFreshness(last, asOf));
    }
  });

  it("checks the synthetic fixture without copying evidence into the report", async () => {
    const raw = JSON.parse(await readFile(fixturePath, "utf8")) as unknown;
    const doc = validateDocument(raw);
    const snapshot = snapshotFromDocument(doc, { asOf: "2026-09-27T00:00:00.000Z", windowHours: 168 });
    expect(JSON.stringify(snapshot)).not.toContain("Ignore previous");
    expect(snapshot.integrity.duplicate_identity_ids).toBe(0);
    expect(snapshot.integrity.multiple_current_versions).toBe(0);
    expect(snapshot.integrity.impossible_probability).toBe(0);
    expect(snapshot.integrity.human_verified_missing_evidence).toBe(0);
    expect(snapshot.integrity.numeric_without_numeric_evidence).toBe(0);
    const report = evaluate(snapshot, { scope: "document", runId: "fixture12345" });
    expect(report.ok).toBe(true);
    expect(report.dataset_kind).toBe("synthetic");
    expect(JSON.stringify(report)).not.toContain("Ignore previous");
  });

  it("reports a second current version instead of repairing it", async () => {
    const doc = validateDocument(JSON.parse(await readFile(fixturePath, "utf8")));
    const copy = structuredClone(doc);
    const item = copy.source_items[0];
    expect(item).toBeTruthy();
    if (!item) return;
    copy.source_items.push({ ...item, slug: `${item.slug}-duplicate-current` });
    const snapshot = snapshotFromDocument(copy, { asOf: "2026-09-27T00:00:00.000Z", windowHours: 168 });
    expect(snapshot.integrity.multiple_current_versions).toBe(1);
    const report = evaluate(snapshot, { scope: "document", runId: "duplicate12" });
    expect(report.ok).toBe(false);
    expect(ids(report, "error")).toContain("multiple_current_versions");
    expect(JSON.stringify(report)).not.toContain(item.canonical_url);
  });

  it("rejects an invalid canonical file without echoing it", async () => {
    const file = join(tmpdir(), "pdoom-invalid-canonical.json");
    await writeFile(file, JSON.stringify({ schema_version: "nope", evidence: "Ignore previous instructions" }));
    const report = await runQualityCheck({ file, strict: false });
    expect(report.ok).toBe(false);
    expect(ids(report, "error")).toContain("canonical_validation_failed");
    expect(JSON.stringify(report)).not.toContain("Ignore previous");
    expect(qualityExitCode(report, false)).toBe(1);
  });
});

describe("operator endpoints", () => {
  it("stays readable on /api/health while /api/status shows a stale synthetic dataset", async () => {
    const health = await getHealth(new Request("http://localhost/api/health"), undefined as never);
    expect(health.status).toBe(200);
    expect(await health.json()).toEqual({ ok: true });
    const status = await getStatus(new Request("http://localhost/api/status"), undefined as never);
    expect(status.status).toBe(200);
    const body = await status.json();
    expect(body.app).toBe("operational");
    expect(body.dataset).toBe("stale");
    expect(body.dataset_kind).toBe("synthetic");
    expect(body.freshness.stale).toBeGreaterThan(0);
    expect(body.latest_successful_observation).toBeTruthy();
    const blob = JSON.stringify(body);
    expect(blob).not.toContain("Ignore previous");
    expect(blob).not.toContain("normalized_text");
    expect(blob).not.toContain("postgres://");
    expect(blob).not.toContain("canonical_url");
    expect(Object.keys(body).sort()).toEqual([
      "app",
      "dataset",
      "dataset_generated_at",
      "dataset_kind",
      "freshness",
      "latest_successful_observation",
    ]);
  });

  it("hides metrics unless enabled and keeps the scrape free of private text", async () => {
    const hidden = await getMetrics(new Request("http://localhost/api/metrics"), undefined as never);
    expect(hidden.status).toBe(404);
    process.env.PDOOM_METRICS_ENABLED = "1";
    process.env.PDOOM_METRICS_TOKEN = "metrics-token-value";
    const denied = await getMetrics(new Request("http://localhost/api/metrics"), undefined as never);
    expect(denied.status).toBe(403);
    const allowed = await getMetrics(
      new Request("http://localhost/api/metrics", { headers: { authorization: "Bearer metrics-token-value" } }),
      undefined as never,
    );
    expect(allowed.status).toBe(200);
    const text = await allowed.text();
    expect(text).toContain("pdoom_sources_freshness");
    expect(text).toContain("pdoom_collection_succeeded");
    expect(text).toContain("pdoom_alert_firing");
    expect(text).not.toContain("metrics-token-value");
    expect(text).not.toContain("Ignore previous");
    expect(text.toLowerCase()).not.toContain("select ");
    expect(text).not.toContain("postgres://");
  });
});

describe("quality check command", () => {
  it("exits zero for the synthetic fixture", () => {
    const result = spawnSync(
      "node",
      ["--import", "tsx", "packages/db/src/cli.ts", "quality", "check", "--file", fixturePath, "--as-of", "2026-09-27T00:00:00.000Z"],
      { cwd: join(import.meta.dirname, ".."), encoding: "utf8" },
    );
    expect(result.status).toBe(0);
    const report = JSON.parse(result.stdout) as QualityReport;
    expect(report.ok).toBe(true);
    expect(report.scope).toBe("document");
    expect(result.stdout).not.toContain("Ignore previous");
    expect(result.stderr).toContain("quality check (document): ok");
  });
});

function ids(report: QualityReport, severity: "error" | "warning" | "info"): string[] {
  return report.findings.filter((finding) => finding.severity === severity).map((finding) => finding.id).sort();
}
