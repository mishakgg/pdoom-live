import { closePool, getPool, migrationsDirectory, readRuntimeConfig } from "@pdoom/db";

let registered = false;

function shutdown(signal: string) {
  console.log(JSON.stringify({ event: "server_shutdown", signal }));
  void closePool();
}

function onSigterm() {
  shutdown("SIGTERM");
}

function onSigint() {
  shutdown("SIGINT");
}

export function detachBootSignals(): void {
  process.removeListener("SIGTERM", onSigterm);
  process.removeListener("SIGINT", onSigint);
  registered = false;
}

export function bootServer(): void {
  const config = readRuntimeConfig();
  if (config.mode === "production") {
    migrationsDirectory();
    getPool();
  } else if (process.env.DATABASE_URL) {
    getPool();
  }
  console.log(
    JSON.stringify({
      event: "server_boot",
      mode: config.mode,
      hsts: config.hsts,
      origin: config.appBaseUrl?.origin ?? null,
    }),
  );
  if (registered) return;
  registered = true;
  process.once("SIGTERM", onSigterm);
  process.once("SIGINT", onSigint);
}
