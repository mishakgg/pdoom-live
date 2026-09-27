import { readFile } from "node:fs/promises";
import { assertDevelopmentMutation, publicCommandError, readDatabaseUrl, readRuntimeConfig } from "./env";
import { importCanonical, resetDatabase, validateDocument } from "./import";
import { migrate, migrationState } from "./migrate";
import { createPool, closePool, endPool } from "./pool";
import { getCoverage, getDatasetRecord } from "./queries";
import { importWasAborted, installCliShutdown } from "./shutdown";

const command = process.argv[2];
const file = process.argv[3];

async function readJson(path: string): Promise<unknown> {
  const raw = await readFile(path, "utf8");
  return JSON.parse(raw);
}

async function main() {
  if (command === "seed" || command === "reset") {
    assertDevelopmentMutation(command);
  }
  readRuntimeConfig();

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

  const pool = createPool(readDatabaseUrl("DATABASE_URL"), {
    statementTimeoutMs: 120_000,
    applicationName: "pdoom-cli",
  });
  installCliShutdown(pool);
  try {
    if (command === "migrate") {
      const applied = await migrate(pool);
      console.log(applied.length ? `applied ${applied.join(", ")}` : "migrations up to date");
      return;
    }
    if (command === "seed") {
      await migrate(pool);
      const result = await importCanonical(pool);
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
      const result = await importCanonical(pool, raw);
      console.log(JSON.stringify({ imported: result.imported, counts: result.counts, dataset_id: result.dataset_id }));
      return;
    }
    if (command === "status") {
      const state = await migrationState(pool);
      if (state !== "current") {
        console.log(JSON.stringify({ migrations: state }));
        return;
      }
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
          migrations: state,
          dataset,
          counts: counts.rows[0],
          latest_observation: latest.rows[0].observed_at,
          coverage,
        }),
      );
      return;
    }
    throw new Error("usage: cli.ts migrate|seed|reset|validate <file>|import <file>|status");
  } finally {
    await endPool(pool);
    await closePool();
  }
}

main().catch((error: unknown) => {
  console.error(publicCommandError(error));
  process.exit(importWasAborted() ? 143 : 1);
});
