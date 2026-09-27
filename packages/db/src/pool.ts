import pg from "pg";
import { readDatabaseUrl } from "./env";

const { Pool } = pg;

let pool: pg.Pool | null = null;
const ending = new WeakMap<pg.Pool, Promise<void>>();

export type PoolOptions = {
  statementTimeoutMs?: number;
  applicationName?: string;
};

export function createPool(connectionString: string, options: PoolOptions = {}): pg.Pool {
  const created = new Pool({
    connectionString,
    max: 5,
    statement_timeout: options.statementTimeoutMs ?? 15_000,
    connectionTimeoutMillis: 5_000,
    idleTimeoutMillis: 30_000,
    keepAlive: true,
    application_name: options.applicationName ?? "pdoom-live",
  });
  created.on("error", (error: Error) => {
    const code = "code" in error && typeof error.code === "string" ? error.code : "unknown";
    console.error(`database pool dropped a connection (${code})`);
  });
  return created;
}

export function getPool(): pg.Pool {
  if (!pool) {
    pool = createPool(readDatabaseUrl("DATABASE_URL"), { applicationName: "pdoom-web" });
  }
  return pool;
}

export async function endPool(target: pg.Pool): Promise<void> {
  let pending = ending.get(target);
  if (!pending) {
    pending = target.end().then(
      () => undefined,
      () => undefined,
    );
    ending.set(target, pending);
  }
  await pending;
}

export async function closePool(): Promise<void> {
  if (!pool) return;
  const current = pool;
  pool = null;
  await endPool(current);
}
