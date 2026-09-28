import { readFile } from "node:fs/promises";
import {
  catalog,
  createCorrelationId,
  evaluate,
  logEvent,
  parseBaseline,
  qualityExitCode,
  resolveGuardrails,
  runWithCorrelation,
  type Baseline,
  type Guardrails,
  type QualityReport,
  type ReportScope,
} from "@pdoom/observability";
import type pg from "pg";
import { validateDocument } from "./import";
import { loadOperationalSnapshot, snapshotFromDocument } from "./operational-snapshot";
import { createPool } from "./pool";
import { readDatabaseUrl } from "./env";

const MAX_BYTES = 32 * 1024 * 1024;

export type QualityArgs = {
  file?: string;
  baseline?: string;
  guardrails?: string;
  asOf?: string;
  strict: boolean;
  pool?: pg.Pool | null;
};

export async function runQualityCheck(args: QualityArgs): Promise<QualityReport> {
  const asOf = args.asOf ?? new Date().toISOString();
  if (Number.isNaN(Date.parse(asOf))) throw new Error("as-of must be an ISO timestamp");
  const baseline = args.baseline ? parseBaseline(await readJson(args.baseline, "baseline")) : null;
  const guardrails = args.guardrails ? parseGuardrails(await readJson(args.guardrails, "guardrails")) : undefined;
  const windowHours = resolveGuardrails(guardrails).collection_success_window_hours;
  const runId = createCorrelationId();
  return runWithCorrelation({ runId }, async () => {
    if (args.file) {
      const report = checkFile(await readJson(args.file, "dataset"), { asOf, windowHours, baseline, guardrails, runId });
      return report;
    }
    const pool = args.pool ?? createPool(readDatabaseUrl("DATABASE_URL"));
    const close = !args.pool;
    try {
      const snapshot = await loadOperationalSnapshot(pool, { asOf, windowHours });
      return evaluate(snapshot, { baseline, guardrails, runId, scope: "database", now: new Date(asOf) });
    } finally {
      if (close) await pool.end();
    }
  });
}

export async function executeQualityCheck(argv: string[]): Promise<number> {
  const started = performance.now();
  const args = parseQualityArgs(argv);
  const runId = createCorrelationId();
  try {
    const report = await runQualityCheck(args);
    process.stderr.write(`${report.summary}\n`);
    process.stdout.write(`${JSON.stringify(report)}\n`);
    logEvent({
      level: report.ok ? "info" : "error",
      operation: "quality_check",
      outcome: report.ok ? "succeeded" : "failed",
      duration_ms: performance.now() - started,
      run_id: report.run_id,
      error_class: report.ok ? undefined : "unknown",
    });
    return qualityExitCode(report, args.strict);
  } catch (error) {
    logEvent({
      level: "error",
      operation: "quality_check",
      outcome: "failed",
      duration_ms: performance.now() - started,
      run_id: runId,
      error_class: "unknown",
    });
    const message = error instanceof Error ? safeCommandError(error.message) : "quality check failed";
    throw new Error(message);
  }
}

export function parseQualityArgs(argv: string[]): QualityArgs {
  if (argv[0] !== "check") throw new Error(usage);
  const file = flag(argv, "--file");
  const baseline = flag(argv, "--baseline");
  const guardrails = flag(argv, "--guardrails");
  const asOf = flag(argv, "--as-of");
  const strict = argv.includes("--strict");
  const known = new Set(["check", "--file", "--baseline", "--guardrails", "--as-of", "--strict", file, baseline, guardrails, asOf]);
  for (const arg of argv) {
    if (!known.has(arg)) throw new Error(usage);
  }
  return { file, baseline, guardrails, asOf, strict };
}

function checkFile(
  raw: unknown,
  options: { asOf: string; windowHours: number; baseline: Baseline | null; guardrails?: Partial<Guardrails>; runId: string },
): QualityReport {
  let doc;
  try {
    doc = validateDocument(raw);
  } catch {
    return invalidDocumentReport(options);
  }
  const snapshot = snapshotFromDocument(doc, { asOf: options.asOf, windowHours: options.windowHours });
  return evaluate(snapshot, {
    baseline: options.baseline,
    guardrails: options.guardrails,
    runId: options.runId,
    scope: "document",
    now: new Date(options.asOf),
  });
}

function invalidDocumentReport(options: {
  asOf: string;
  baseline: Baseline | null;
  guardrails?: Partial<Guardrails>;
  runId: string;
}): QualityReport {
  return evaluate(
    {
      as_of: options.asOf,
      canonical_valid: false,
      database_checked: false,
      dataset_present: true,
      dataset_kind: "unknown",
      cohort_size: 1,
      readiness: { database: true },
    },
    { baseline: options.baseline, guardrails: options.guardrails, runId: options.runId, scope: "document" satisfies ReportScope },
  );
}

async function readJson(path: string, label: string): Promise<unknown> {
  let text: string;
  try {
    const file = await readFile(path);
    if (file.byteLength > MAX_BYTES) throw new Error(`${label} file is too large`);
    text = file.toString("utf8");
  } catch (error) {
    if (error instanceof Error && error.message.endsWith("file is too large")) throw error;
    throw new Error(`could not read ${label} file`);
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label} file is not valid JSON`);
  }
}

function parseGuardrails(raw: unknown): Partial<Guardrails> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("guardrails must be a JSON object");
  const source = raw as Record<string, unknown>;
  const body =
    source.guardrails && typeof source.guardrails === "object" && !Array.isArray(source.guardrails)
      ? (source.guardrails as Record<string, unknown>)
      : source;
  const override: Partial<Guardrails> = {};
  for (const key of Object.keys(catalog.guardrails) as Array<keyof Guardrails>) {
    if (!(key in body)) continue;
    const value = body[key];
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
      throw new Error("guardrail values must be non-negative numbers");
    }
    if (key.endsWith("_ratio") && value > 1) throw new Error("guardrail ratios must be between 0 and 1");
    if (key === "collection_success_window_hours" && (value < 1 || value > 24 * 366)) {
      throw new Error("collection window must be between 1 and 8784 hours");
    }
    override[key] = value;
  }
  return override;
}

function flag(argv: string[], name: string): string | undefined {
  const index = argv.indexOf(name);
  if (index === -1) return undefined;
  const value = argv[index + 1];
  if (!value || value.startsWith("--")) throw new Error(usage);
  return value;
}

function safeCommandError(message: string): string {
  if (/postgres(?:ql)?:\/\//i.test(message) || /@[a-z0-9.-]+:\d+/i.test(message)) return "quality check failed";
  if (
    message.startsWith("usage:") ||
    message.startsWith("as-of") ||
    message === "DATABASE_URL is missing or not a postgres URL" ||
    message.includes("file") ||
    message.includes("baseline") ||
    message.includes("guardrail") ||
    message.includes("ISO")
  ) {
    return message;
  }
  return "quality check failed";
}

const usage = "usage: cli.ts quality check [--file <json>] [--baseline <json>] [--guardrails <json>] [--as-of <iso>] [--strict]";
