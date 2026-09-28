import type pg from "pg";
import { endPool } from "./pool";

let abortRequested = false;
let activeClient: pg.PoolClient | null = null;
let activePid: number | null = null;
let activePool: pg.Pool | null = null;

export function importWasAborted(): boolean {
  return abortRequested;
}

export function setActiveClient(client: pg.PoolClient | null, pid: number | null = null): void {
  activeClient = client;
  activePid = pid;
}

export function markImportAborted(): void {
  if (process.env.NODE_ENV !== "test" && process.env.PDOOM_ENV !== "test") {
    throw new Error("import abort hook is not available");
  }
  abortRequested = true;
}

export function resetImportAbort(): void {
  if (process.env.NODE_ENV !== "test" && process.env.PDOOM_ENV !== "test") {
    throw new Error("import abort hook is not available");
  }
  abortRequested = false;
}

export function installCliShutdown(pool: pg.Pool): void {
  activePool = pool;
  const onSignal = (signal: NodeJS.Signals) => {
    if (abortRequested) return;
    abortRequested = true;
    console.error(`received ${signal}; rolling back open work`);
    const pid = activePid;
    const currentPool = activePool;
    if (pid !== null && currentPool) {
      void currentPool.query("SELECT pg_cancel_backend($1)", [pid]).catch(() => undefined);
    }
    setTimeout(() => {
      console.error("shutdown timed out");
      void endPool(pool).finally(() => {
        process.exit(signal === "SIGINT" ? 130 : 143);
      });
    }, 5_000).unref();
  };
  process.once("SIGINT", () => onSignal("SIGINT"));
  process.once("SIGTERM", () => onSignal("SIGTERM"));
}

export async function waitForTestHold(): Promise<void> {
  if (process.env.PDOOM_ENV !== "test" || process.env.PDOOM_IMPORT_HOLD !== "1") return;
  console.log("holding import for shutdown");
  await new Promise<void>((resolve) => {
    process.once("SIGTERM", () => resolve());
    process.once("SIGINT", () => resolve());
  });
}

export async function commitOrAbort(client: pg.PoolClient): Promise<void> {
  await waitForTestHold();
  if (abortRequested) {
    await client.query("ROLLBACK").catch(() => undefined);
    throw new Error("import aborted");
  }
  await client.query("COMMIT");
}
