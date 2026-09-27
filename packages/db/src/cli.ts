import { readFile } from "node:fs/promises";
import { createCorrelationId, logEvent, recordImportResult, runWithCorrelation } from "@pdoom/observability";
import { closePool, createPool } from "./pool";
import { readDatabaseUrl } from "./env";
import { importCanonical, resetDatabase, validateDocument } from "./import";
import { migrate } from "./migrate";
import { executeQualityCheck } from "./quality-command";
import { getCoverage, getDatasetRecord } from "./queries";

const command = process.argv[2];
const file = process.argv[3];

async function readJson(path: string): Promise<unknown> {
  const raw = await readFile(path, "utf8");
  return JSON.parse(raw);
}

async function main() {
  if (command === "validate") {
    if (!file) throw new Error("usage: cli.ts validate <file>");
    const parsed = validateDocument(await readJson(file));
    console.log(
      JSON.stringify({
        ok: true,
        dataset_id: parsed.dataset_id,
        dataset_kind: parsed.dataset_kind,
        schema_version: parsed.schema_version,
        people: parsed.people.length,
        sources: parsed.sources.length,
        source_items: parsed.source_items.length,
        statements: parsed.statements.length,
      }),
    );
    return;
  }
  if (command === "quality") {
    const code = await executeQualityCheck(process.argv.slice(3));
    process.exit(code);
  }

  const pool = createPool(readDatabaseUrl("DATABASE_URL"));
  try {
    if (command === "migrate") {
      const applied = await migrate(pool);
      console.log(applied.length ? `applied ${applied.join(", ")}` : "migrations up to date");
      return;
    }
    if (command === "seed") {
      await migrate(pool);
      const result = await importDataset(() => importCanonical(pool));
      console.log(JSON.stringify(result.counts));
      return;
    }
    if (command === "reset") {
      await migrate(pool);
      const result = await resetDatabase(pool);
      console.log(JSON.stringify(result.counts));
      return;
    }
    if (command === "import") {
      if (!file) throw new Error("usage: cli.ts import <file>");
      const raw = await readJson(file);
      validateDocument(raw);
      await migrate(pool);
      const result = await importDataset(() => importCanonical(pool, raw));
      console.log(JSON.stringify({ imported: result.imported, counts: result.counts, dataset_id: result.dataset_id }));
      return;
    }
    if (command === "status") {
      await migrate(pool);
      const dataset = await getDatasetRecord(pool);
      const coverage = await getCoverage(new Date().toISOString(), pool);
      const counts = await pool.query(`
        SELECT
          (SELECT count(*)::int FROM people) AS people,
          (SELECT count(*)::int FROM sources) AS sources,
          (SELECT count(*)::int FROM source_items) AS source_items,
          (SELECT count(*)::int FROM statements) AS statements
      `);
      const latest = await pool.query("SELECT max(observed_at) AS observed_at FROM source_items");
      console.log(
        JSON.stringify({
          dataset,
          counts: counts.rows[0],
          latest_observation: latest.rows[0].observed_at,
          coverage,
        }),
      );
      return;
    }
    throw new Error("usage: cli.ts migrate|seed|reset|validate <file>|import <file>|status|quality check");
  } finally {
    if (command !== "validate") await pool.end();
    await closePool();
  }
}

async function importDataset<T>(load: () => Promise<T>): Promise<T> {
  const runId = createCorrelationId();
  const started = performance.now();
  return runWithCorrelation({ runId }, async () => {
    try {
      const result = await load();
      recordImportResult("succeeded");
      logEvent({
        level: "info",
        operation: "import",
        outcome: "succeeded",
        duration_ms: performance.now() - started,
        run_id: runId,
      });
      return result;
    } catch {
      recordImportResult("failed");
      logEvent({
        level: "error",
        operation: "import",
        outcome: "failed",
        duration_ms: performance.now() - started,
        run_id: runId,
        error_class: "unknown",
      });
      throw new Error("import failed");
    }
  });
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : "command failed");
  process.exit(1);
});
