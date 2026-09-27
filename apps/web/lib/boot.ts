import { closePool, getPool, migrationsDirectory, readRuntimeConfig } from "@pdoom/db";

let registered = false;

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
  const shutdown = (signal: string) => {
    console.log(JSON.stringify({ event: "server_shutdown", signal }));
    void closePool();
  };
  process.once("SIGTERM", () => shutdown("SIGTERM"));
  process.once("SIGINT", () => shutdown("SIGINT"));
}
