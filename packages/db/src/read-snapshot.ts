import type pg from "pg";
import { getPool } from "./pool";

const ADMISSION_LIMIT = 3;
const ADMISSION_WAIT_MS = 200;
const MAX_ADMISSION_WAITERS = 64;

/**
 * Public reads share a pool of 5. Keep a few connections for probes and
 * short revision checks, and fail the rest quickly instead of queueing
 * until the connection timeout.
 */
export class AdmissionError extends Error {
  readonly retryAfter = 1;

  constructor() {
    super("admission_limited");
    this.name = "AdmissionError";
  }
}

type Waiter = () => void;

let activeReads = 0;
const waiters: Waiter[] = [];

function releaseAdmission(): void {
  const next = waiters.shift();
  if (next) next();
  else activeReads -= 1;
}

async function acquireAdmission(): Promise<() => void> {
  if (activeReads >= ADMISSION_LIMIT) {
    if (waiters.length >= MAX_ADMISSION_WAITERS) throw new AdmissionError();
    const granted = await new Promise<boolean>((resolve) => {
      let settled = false;
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        const index = waiters.indexOf(grant);
        if (index >= 0) waiters.splice(index, 1);
        resolve(false);
      }, ADMISSION_WAIT_MS);
      function grant() {
        if (settled) {
          activeReads -= 1;
          return;
        }
        settled = true;
        clearTimeout(timer);
        resolve(true);
      }
      waiters.push(grant);
    });
    if (!granted) throw new AdmissionError();
  } else {
    activeReads += 1;
  }
  let released = false;
  return () => {
    if (released) return;
    released = true;
    releaseAdmission();
  };
}

export function isPool(db: pg.Pool | pg.PoolClient): db is pg.Pool {
  return typeof (db as pg.Pool).connect === "function" && typeof (db as pg.PoolClient).release !== "function";
}

/** Run `fn` on one snapshot client. A client that is already in a transaction is reused. */
export function queryOnClient<T>(db: pg.Pool | pg.PoolClient, fn: (client: pg.PoolClient) => Promise<T>): Promise<T> {
  if (isPool(db)) return withConsistentRead(db, fn);
  return fn(db);
}

/**
 * One REPEATABLE READ, read-only transaction for every statement in a public
 * response. Callers that already hold a transaction client reuse it.
 * The transaction is bounded by statement, lock, and idle timeouts.
 */
export async function withConsistentRead<T>(
  db: pg.Pool | pg.PoolClient,
  fn: (db: pg.PoolClient) => Promise<T>,
): Promise<T> {
  if (!isPool(db)) return fn(db);
  const release = await acquireAdmission();
  const pool = db;
  let client: pg.PoolClient | null = null;
  try {
    client = await pool.connect();
    await client.query("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY");
    await client.query(
      `SELECT set_config('statement_timeout', '15s', true),
              set_config('lock_timeout', '2s', true),
              set_config('idle_in_transaction_session_timeout', '15s', true)`,
    );
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    if (client) {
      try {
        await client.query("ROLLBACK");
      } catch {
        // The connection may already be aborted.
      }
    }
    throw error;
  } finally {
    client?.release();
    release();
  }
}

export function readPool(db?: pg.Pool | pg.PoolClient): pg.Pool | pg.PoolClient {
  return db ?? getPool();
}

export function isStatementTimeout(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && (error as { code?: string }).code === "57014";
}
