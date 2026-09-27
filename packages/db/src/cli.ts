import { readFile } from "node:fs/promises";
import { closePool, createPool } from "./pool";
import { readDatabaseUrl } from "./env";
import { importCanonical, resetDatabase, validateDocument } from "./import";
import { migrate } from "./migrate";
import { getCoverage, getDatasetRecord } from "./queries";
import { exportReviewManifest, importReviewManifest, reviewStatus, stageCandidates, validateReviewManifest, validateReviewManifestInDatabase } from "./review";

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

  const pool = createPool(readDatabaseUrl("DATABASE_URL"));
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
      validateDocument(raw);
      await migrate(pool);
      const result = await importCanonical(pool, raw);
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
    if (command === "review:status") {
      await migrate(pool);
      console.log(JSON.stringify(await reviewStatus(pool)));
      return;
    }
    if (command === "review:export") {
      if (!file) throw new Error("usage: cli.ts review:export <file>");
      await migrate(pool);
      const manifest = await exportReviewManifest(pool);
      const { writeFile } = await import("node:fs/promises");
      await writeFile(file, `${JSON.stringify(manifest, null, 2)}\n`);
      console.log(JSON.stringify({ decisions: manifest.decisions.length, file }));
      return;
    }
    if (command === "review:import") {
      if (!file) throw new Error("usage: cli.ts review:import <file>");
      const raw = await readJson(file);
      validateReviewManifest(raw);
      await migrate(pool);
      const errors = await validateReviewManifestInDatabase(pool, raw);
      if (errors.length) throw new Error(errors.join("; "));
      console.log(JSON.stringify(await importReviewManifest(pool, raw)));
      return;
    }
    if (command === "review:validate") {
      if (!file) throw new Error("usage: cli.ts review:validate <file>");
      const raw = await readJson(file);
      validateReviewManifest(raw);
      const errors = await validateReviewManifestInDatabase(pool, raw);
      if (errors.length) throw new Error(errors.join("; "));
      console.log(JSON.stringify({ ok: true, decisions: (raw as { decisions: unknown[] }).decisions.length }));
      return;
    }
    if (command === "review:stage") {
      if (!file) throw new Error("usage: cli.ts review:stage <jsonl>");
      const text = await readFile(file, "utf8");
      const rows = text.split("\n").filter((line) => line.trim()).map((line) => JSON.parse(line));
      await migrate(pool);
      console.log(JSON.stringify(await stageCandidates(pool, rows)));
      return;
    }
    throw new Error("usage: cli.ts migrate|seed|reset|validate <file>|import <file>|status|review:status|review:export <file>|review:import <file>|review:validate <file>|review:stage <jsonl>");
  } finally {
    if (command !== "validate") await pool.end();
    await closePool();
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : "command failed");
  process.exit(1);
});
