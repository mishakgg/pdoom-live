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

function publicReleaseIdentity(): { commit: string | null; built_at: string | null } {
  const commit = process.env.GIT_COMMIT ?? "";
  const builtAt = process.env.BUILD_TIME ?? "";
  return {
    commit: /^[0-9a-f]{7,40}$/.test(commit) ? commit : null,
    built_at: /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(builtAt) ? builtAt : null,
  };
}

export function bootServer(): void {
  const config = readRuntimeConfig();
  if (config.mode === "production") {
    migrationsDirectory();
    getPool();
  } else if (process.env.DATABASE_URL) {
    getPool();
  }
  const release = publicReleaseIdentity();
  console.log(
    JSON.stringify({
      event: "server_boot",
      mode: config.mode,
      hsts: config.hsts,
      origin: config.appBaseUrl?.origin ?? null,
      commit: release.commit,
      built_at: release.built_at,
    }),
  );
  if (registered) return;
  registered = true;
  process.once("SIGTERM", onSigterm);
  process.once("SIGINT", onSigint);
}
