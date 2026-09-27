import { dbErrorClass, logEvent, recordDbQuery, setDatabaseReady } from "@pdoom/observability";
import pg from "pg";
import { readDatabaseUrl } from "./env";

const { Pool } = pg;
const WRAPPED = Symbol("pdoomQueryWrapped");

let pool: pg.Pool | null = null;

export function createPool(connectionString: string): pg.Pool {
  const created = new Pool({
    connectionString,
    max: 5,
    statement_timeout: 15_000,
  });
  wrapQueryable(created);
  const originalConnect = created.connect.bind(created);
  created.connect = ((...args: unknown[]) => {
    if (typeof args[0] === "function") return originalConnect(...(args as Parameters<pg.Pool["connect"]>));
    return Promise.resolve(originalConnect()).then((client) => {
      wrapQueryable(client);
      return client;
    });
  }) as pg.Pool["connect"];
  return created;
}

export function getPool(): pg.Pool {
  if (!pool) pool = createPool(readDatabaseUrl("DATABASE_URL"));
  return pool;
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}

function wrapQueryable(target: { query: pg.Pool["query"] }): void {
  const marked = target as { query: pg.Pool["query"]; [WRAPPED]?: boolean };
  if (marked[WRAPPED]) return;
  const original = marked.query.bind(target) as (...args: unknown[]) => Promise<unknown>;
  marked.query = ((...args: unknown[]) => {
    const started = performance.now();
    const operation = classifySql(sqlText(args[0]));
    return original(...args).then(
      (result) => {
        recordDbQuery(operation, "ok", performance.now() - started);
        return result;
      },
      (error: unknown) => {
        const errorClass = dbErrorClass(error);
        const duration = performance.now() - started;
        recordDbQuery(operation, "error", duration, errorClass);
        if (errorClass === "connection") setDatabaseReady(false);
        logEvent({
          level: "error",
          operation: "db_query",
          outcome: "failed",
          duration_ms: duration,
          error_class: errorClass,
        });
        throw error;
      },
    );
  }) as pg.Pool["query"];
  marked[WRAPPED] = true;
}

function sqlText(query: unknown): string {
  if (typeof query === "string") return query.slice(0, 32);
  if (query && typeof query === "object" && "text" in query) {
    const text = (query as { text?: unknown }).text;
    if (typeof text === "string") return text.slice(0, 32);
  }
  return "";
}

function classifySql(text: string): "read" | "write" | "other" {
  const word = text.trimStart().slice(0, 7).toLowerCase();
  if (word.startsWith("select") || word.startsWith("with")) return "read";
  if (word.startsWith("insert") || word.startsWith("update") || word.startsWith("delete")) return "write";
  return "other";
}
