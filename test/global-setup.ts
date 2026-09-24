import { createPool } from "../packages/db/src/pool";
import { assertTestDatabase, readDatabaseUrl } from "../packages/db/src/env";
import { migrate } from "../packages/db/src/migrate";
import { resetDatabase } from "../packages/db/src/import";

export default async function setup() {
  const url = process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test";
  process.env.DATABASE_URL = url;
  assertTestDatabase(url);
  const pool = createPool(readDatabaseUrl("DATABASE_URL"));
  await migrate(pool);
  await resetDatabase(pool);
  await pool.end();
}
