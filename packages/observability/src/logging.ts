import { allowedLabel } from "./catalog";
import { currentCorrelation } from "./correlation";
import { normalizeAdapter } from "./normalize";

const TOKEN = /^[a-z0-9_.:-]{1,64}$/;
const ID = /^[A-Za-z0-9_-]{8,64}$/;
const SECRET = /postgres(?:ql)?:\/\/|bearer\s+\S+|password\s*=|authorization\s*:|cookie\s*:|-----begin/i;

export type LogLevel = "info" | "warn" | "error";

export type LogInput = {
  level: LogLevel;
  operation: string;
  request_id?: string;
  run_id?: string;
  adapter?: string;
  outcome?: string;
  duration_ms?: number;
  error_class?: string;
};

let sink: (line: string) => void = (line) => {
  process.stderr.write(`${line}\n`);
};

export function setLogSink(next: ((line: string) => void) | null): void {
  sink = next ?? ((line) => process.stderr.write(`${line}\n`));
}

export function safeToken(value: string | undefined, fallback: string): string {
  if (value && TOKEN.test(value) && !SECRET.test(value)) return value;
  return fallback;
}

export function formatLog(input: LogInput, now = new Date()): string {
  const correlation = currentCorrelation();
  const requestId = input.request_id ?? correlation.requestId;
  const runId = input.run_id ?? correlation.runId;
  const record: Record<string, string | number> = {
    ts: now.toISOString(),
    level: input.level === "warn" || input.level === "error" ? input.level : "info",
    operation: safeToken(input.operation, "unknown"),
  };
  if (requestId && ID.test(requestId)) record.request_id = requestId;
  if (runId && ID.test(runId)) record.run_id = runId;
  if (input.adapter) record.adapter = normalizeAdapter(input.adapter);
  if (input.outcome) record.outcome = safeToken(input.outcome, "unknown");
  if (
    typeof input.duration_ms === "number" &&
    Number.isFinite(input.duration_ms) &&
    input.duration_ms >= 0 &&
    input.duration_ms < 1_000_000_000
  ) {
    record.duration_ms = Math.round(input.duration_ms);
  }
  if (input.error_class) record.error_class = allowedLabel("error_class", input.error_class, "unknown");
  const line = JSON.stringify(record);
  if (SECRET.test(line)) {
    return JSON.stringify({
      ts: record.ts,
      level: "error",
      operation: "log_redacted",
      outcome: "failed",
      error_class: "unknown",
    });
  }
  return line;
}

export function logEvent(input: LogInput): void {
  sink(formatLog(input));
}
