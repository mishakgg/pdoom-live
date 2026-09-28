export { catalog, metricNames, type Guardrails } from "./catalog";
export { acceptCorrelationId, createCorrelationId, currentCorrelation, runWithCorrelation } from "./correlation";
export { dbErrorClass } from "./db-error";
export {
  evaluate,
  parseBaseline,
  publicStatus,
  qualityExitCode,
  resolveGuardrails,
  type Alert,
  type Baseline,
  type EvaluateOptions,
  type Finding,
  type PublicStatus,
  type QualityReport,
  type ReportScope,
  type Severity,
  type SloResult,
} from "./evaluate";
export { formatLog, logEvent, setLogSink, type LogInput } from "./logging";
export {
  counterSnapshot,
  databaseReadyFlag,
  histogramSnapshot,
  importFailureStreak,
  recordDbQuery,
  recordHttp,
  recordImportResult,
  resetMetrics,
  setDatabaseReady,
} from "./metrics";
export {
  ageDays,
  ageHours,
  cadenceDays,
  classifyAge,
  failureClass,
  inWindow,
  laterIso,
  normalizeAdapter,
  statusClass,
} from "./normalize";
export { renderPrometheus } from "./prometheus";
export {
  completeSnapshot,
  defaultSnapshot,
  publicStatementCount,
  statementTotal,
  type CollectionCounts,
  type FreshnessCounts,
  type IntegrityCounts,
  type OperationalSnapshot,
  type ReviewCounts,
} from "./snapshot";

import { databaseReadyFlag, importFailureStreak } from "./metrics";
import { completeSnapshot, type OperationalSnapshot } from "./snapshot";

export function overlayProcessSignals(snapshot: OperationalSnapshot): OperationalSnapshot {
  return completeSnapshot({
    ...snapshot,
    readiness: { database: snapshot.readiness.database && databaseReadyFlag() },
    import_failure_streak: Math.max(snapshot.import_failure_streak, importFailureStreak()),
  });
}
