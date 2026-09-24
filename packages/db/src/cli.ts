import { closePool, createPool } from "./pool";
import { readDatabaseUrl } from "./env";
import { importCanonical, resetDatabase } from "./import";
import { migrate } from "./migrate";

const command = process.argv[2];

async function main() {
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
    throw new Error("usage: cli.ts migrate|seed|reset");
  } finally {
    await pool.end();
    await closePool();
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : "command failed");
  process.exit(1);
});
