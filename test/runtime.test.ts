import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GET as live } from "../apps/web/app/api/live/route";
import { GET as ready } from "../apps/web/app/api/ready/route";
import { bootServer, detachBootSignals } from "../apps/web/lib/boot";
import { clearReadinessCache } from "../apps/web/lib/ready-cache";
import { contentSecurityPolicy } from "../apps/web/lib/security-headers";
import { proxy } from "../apps/web/proxy";
import {
  ConfigError,
  assertDatasetAllowed,
  assertDevelopmentMutation,
  assertFixtureLoadAllowed,
  closePool,
  createPool,
  importCanonical,
  markImportAborted,
  migrate,
  migrationState,
  parseDatabaseUrl,
  publicCommandError,
  readRuntimeConfig,
  readinessReport,
  resetDatabase,
  resetImportAbort,
} from "../packages/db/src/index";
import { MIGRATION_LOCK_KEYS } from "../packages/db/src/migrate";

const databaseUrl = process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test";
const pool = createPool(databaseUrl);

const previousEnv = new Map<string, string | undefined>();

function setEnv(values: Record<string, string | undefined>) {
  for (const [key, value] of Object.entries(values)) {
    if (!previousEnv.has(key)) previousEnv.set(key, process.env[key]);
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}

afterEach(() => {
  for (const [key, value] of previousEnv) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  previousEnv.clear();
  clearReadinessCache();
  resetImportAbort();
});

describe("production configuration", () => {
  it("requires an explicit production mode, database, and base URL", () => {
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "production",
        PDOOM_ENV: "production",
      }),
    ).toThrow(/DATABASE_URL is required/);
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "production",
        DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
      }),
    ).toThrow(/PDOOM_ENV must be production/);
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "production",
        PDOOM_ENV: "production",
        DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
      }),
    ).toThrow(/APP_BASE_URL is required/);
  });

  it("does not echo credentials in configuration errors", () => {
    const secret = "super-secret-db-password";
    expect(() => parseDatabaseUrl(`postgresql://pdoom:${secret}@`, "DATABASE_URL")).toThrow(ConfigError);
    try {
      parseDatabaseUrl(`not-a-url-${secret}`, "DATABASE_URL");
    } catch (error) {
      expect(publicCommandError(error)).not.toContain(secret);
      expect(publicCommandError(error)).not.toContain("postgresql://");
    }
    try {
      readRuntimeConfig({
        NODE_ENV: "production",
        PDOOM_ENV: "production",
        DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
        APP_BASE_URL: "https://user:hidden-pass@pdoom.example",
      });
    } catch (error) {
      expect(String(error)).not.toContain("hidden-pass");
      expect(String(error)).not.toContain("super-secret");
    }
  });

  it("enables HSTS only for an https origin or an explicit operator flag", () => {
    const httpConfig = readRuntimeConfig({
      NODE_ENV: "production",
      PDOOM_ENV: "production",
      DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
      APP_BASE_URL: "http://127.0.0.1:3000",
    });
    expect(httpConfig.hsts).toBe(false);
    const httpsConfig = readRuntimeConfig({
      NODE_ENV: "production",
      PDOOM_ENV: "production",
      DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
      APP_BASE_URL: "https://pdoom.example",
    });
    expect(httpsConfig.hsts).toBe(true);
    const forcedOff = readRuntimeConfig({
      NODE_ENV: "production",
      PDOOM_ENV: "production",
      DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
      APP_BASE_URL: "https://pdoom.example",
      PDOOM_HSTS: "off",
    });
    expect(forcedOff.hsts).toBe(false);
  });

  it("rejects unknown PDOOM settings and empty optional values", () => {
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "development",
        PDOOM_FUTURE_FLAG: "1",
      }),
    ).toThrow(/unknown configuration PDOOM_FUTURE_FLAG/);
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "production",
        PDOOM_ENV: "production",
        DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
        APP_BASE_URL: "https://pdoom.example",
        PDOOM_CURATION_MODE: "local",
      }),
    ).toThrow(/PDOOM_CURATION_MODE is not allowed in production/);
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "development",
        PDOOM_METRICS_ENABLED: "yes",
      }),
    ).toThrow(/PDOOM_METRICS_ENABLED must be 1 or true/);
    const metrics = readRuntimeConfig({
      NODE_ENV: "production",
      PDOOM_ENV: "production",
      DATABASE_URL: "postgresql://pdoom:super-secret@127.0.0.1:5432/pdoom_live",
      APP_BASE_URL: "https://pdoom.example",
      PDOOM_METRICS_ENABLED: "1",
      PDOOM_METRICS_TOKEN: "metrics-token-value",
    });
    expect(metrics.mode).toBe("production");
    expect(JSON.stringify(metrics)).not.toContain("metrics-token-value");
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "development",
        OPENAI_API_KEY: "",
      }),
    ).toThrow(/OPENAI_API_KEY is set but empty/);
    expect(() =>
      readRuntimeConfig({
        NODE_ENV: "development",
        PORT: "0",
      }),
    ).toThrow(/PORT must be an integer/);
  });

  it("does not log the database URL while booting", async () => {
    const secret = "super-secret-db-password";
    setEnv({
      NODE_ENV: "production",
      PDOOM_ENV: "production",
      DATABASE_URL: `postgresql://pdoom:${secret}@127.0.0.1:5432/pdoom_live_test`,
      APP_BASE_URL: "https://pdoom.example",
      GIT_COMMIT: `not-${secret}`,
      BUILD_TIME: "yesterday",
    });
    const logs: string[] = [];
    const spy = vi.spyOn(console, "log").mockImplementation((message?: unknown) => {
      logs.push(String(message));
    });
    try {
      bootServer();
      expect(logs.join("\n")).toContain("server_boot");
      expect(logs.join("\n")).toContain('"commit":null');
      expect(logs.join("\n")).toContain('"built_at":null');
      expect(logs.join("\n")).not.toContain(secret);
      expect(logs.join("\n")).not.toContain("postgresql://");
    } finally {
      spy.mockRestore();
      detachBootSignals();
      await closePool();
    }
  });
});

describe("production fixture isolation", () => {
  it("refuses fixture loads, synthetic imports, and resets in production", async () => {
    const before = await pool.query("SELECT count(*)::int AS count FROM people");
    setEnv({ PDOOM_ENV: "production", NODE_ENV: "production" });
    expect(() => assertFixtureLoadAllowed()).toThrow(/synthetic fixtures/);
    expect(() => assertDevelopmentMutation("seed")).toThrow(/refusing to seed/);
    expect(() => assertDatasetAllowed({ dataset_kind: "synthetic" })).toThrow(/synthetic dataset/);
    expect(() => assertDatasetAllowed({ dataset_kind: "live" })).not.toThrow();
    await expect(importCanonical(pool)).rejects.toThrow(/synthetic fixtures/);
    const fixture = JSON.parse(await readFile("data/fixtures/synthetic/dataset.json", "utf8")) as unknown;
    await expect(importCanonical(pool, fixture)).rejects.toThrow(/synthetic dataset/);
    await expect(resetDatabase(pool)).rejects.toThrow(/refusing to reset/);
    const after = await pool.query("SELECT count(*)::int AS count FROM people");
    expect(after.rows[0].count).toBe(before.rows[0].count);
  });

  it("rolls back an import when shutdown is requested before commit", async () => {
    const before = await pool.query("SELECT display_name FROM people WHERE slug = 'ada-quill'");
    const original = String(before.rows[0].display_name);
    const fixture = JSON.parse(await readFile("data/fixtures/synthetic/dataset.json", "utf8")) as {
      people: Array<{ slug: string; display_name: string }>;
    };
    fixture.people = fixture.people.map((person) =>
      person.slug === "ada-quill" ? { ...person, display_name: "Abort Sentinel" } : person,
    );
    markImportAborted();
    await expect(importCanonical(pool, fixture)).rejects.toThrow(/import aborted/);
    const after = await pool.query("SELECT display_name FROM people WHERE slug = 'ada-quill'");
    expect(String(after.rows[0].display_name)).toBe(original);
  });

  it("rolls back a held import when the process receives SIGTERM", async () => {
    const before = await pool.query("SELECT display_name FROM people WHERE slug = 'ada-quill'");
    const original = String(before.rows[0].display_name);
    const fixture = JSON.parse(await readFile("data/fixtures/synthetic/dataset.json", "utf8")) as {
      people: Array<{ slug: string; display_name: string }>;
    };
    fixture.people = fixture.people.map((person) =>
      person.slug === "ada-quill" ? { ...person, display_name: "Signal Sentinel" } : person,
    );
    const directory = await mkdtemp(join(tmpdir(), "pdoom-import-"));
    const file = join(directory, "dataset.json");
    await writeFile(file, JSON.stringify(fixture));
    const child = spawn("node_modules/.bin/tsx", ["packages/db/src/cli.ts", "import", file], {
      env: { ...process.env, PDOOM_ENV: "test", NODE_ENV: "test", PDOOM_IMPORT_HOLD: "1" },
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let output = "";
    child.stdout?.on("data", (chunk: Buffer) => {
      output += chunk.toString("utf8");
    });
    child.stderr?.on("data", (chunk: Buffer) => {
      output += chunk.toString("utf8");
    });
    try {
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(`import did not hold: ${output}`)), 25_000);
        const poll = setInterval(() => {
          if (output.includes("holding import for shutdown")) {
            clearInterval(poll);
            clearTimeout(timer);
            resolve();
          }
        }, 50);
      });
      child.kill("SIGTERM");
      const code = await new Promise<number | null>((resolve) => child.once("exit", resolve));
      expect(code).toBe(143);
      expect(output).not.toContain("postgresql://");
      const after = await pool.query("SELECT display_name FROM people WHERE slug = 'ada-quill'");
      expect(String(after.rows[0].display_name)).toBe(original);
    } finally {
      if (child.exitCode === null && child.pid) {
        try {
          process.kill(-child.pid, "SIGKILL");
        } catch {
          child.kill("SIGKILL");
        }
      }
      await rm(directory, { recursive: true, force: true });
      const after = await pool.query("SELECT display_name FROM people WHERE slug = 'ada-quill'");
      if (String(after.rows[0].display_name) !== original) {
        setEnv({ PDOOM_ENV: undefined, NODE_ENV: "test" });
        await resetDatabase(pool);
      }
    }
  });
});

describe("migrations and readiness", () => {
  it("does not record a failed migration and does not run two migrations at once", async () => {
    const directory = await mkdtemp(join(tmpdir(), "pdoom-migrate-"));
    await writeFile(join(directory, "099_bad.sql"), "SELECT does_not_exist_column;");
    const before = await pool.query("SELECT version FROM schema_migrations ORDER BY version");
    await expect(migrate(pool, { directory })).rejects.toThrow(/099_bad.sql/);
    const after = await pool.query("SELECT version FROM schema_migrations ORDER BY version");
    expect(after.rows.map((row) => row.version)).toEqual(before.rows.map((row) => row.version));
    expect(await migrationState(pool, directory)).toBe("pending");

    const client = await pool.connect();
    try {
      const lock = await client.query<{ locked: boolean }>(
        "SELECT pg_try_advisory_lock($1::int, $2::int) AS locked",
        [...MIGRATION_LOCK_KEYS],
      );
      expect(lock.rows[0]?.locked).toBe(true);
      await expect(migrate(pool)).rejects.toThrow(/migration already in progress/);
    } finally {
      await client.query("SELECT pg_advisory_unlock($1::int, $2::int)", [...MIGRATION_LOCK_KEYS]);
      client.release();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("reports a diverged schema and a database that cannot be reached", async () => {
    await pool.query("INSERT INTO schema_migrations (version) VALUES ('999_not_shipped.sql')");
    try {
      expect(await migrationState(pool)).toBe("diverged");
      const report = await readinessReport(pool);
      expect(report.status).toBe("not_ready");
      expect(report.checks.migrations).toBe("diverged");
      expect(JSON.stringify(report)).not.toContain("postgresql://");
      expect(JSON.stringify(report)).not.toContain("/workspace");
    } finally {
      await pool.query("DELETE FROM schema_migrations WHERE version = '999_not_shipped.sql'");
    }

    const unreachable = createPool("postgresql://pdoom:super-secret@127.0.0.1:1/pdoom_live_test", {
      applicationName: "pdoom-unreachable",
    });
    try {
      const report = await readinessReport(unreachable);
      expect(report).toEqual({
        status: "not_ready",
        checks: { process: "live", database: "unavailable", migrations: "unknown" },
      });
      expect(JSON.stringify(report)).not.toContain("super-secret");
    } finally {
      await unreachable.end();
    }
  });

  it("keeps probes small and blocks traffic while migrations are pending", async () => {
    const healthy = await ready();
    expect(healthy.status).toBe(200);
    const body = await healthy.json();
    expect(body.checks).toEqual({ process: "live", database: "ok", migrations: "current" });
    expect(JSON.stringify(body)).not.toMatch(/postgres(ql)?:\/\//);
    expect(JSON.stringify(body)).not.toContain("stack");
    const alive = await live();
    expect(alive.status).toBe(200);
    expect(await alive.json()).toEqual({ status: "live" });

    const directory = await mkdtemp(join(tmpdir(), "pdoom-pending-"));
    await writeFile(join(directory, "099_pending.sql"), "SELECT 1;");
    setEnv({ PDOOM_MIGRATIONS_DIR: directory });
    clearReadinessCache();
    try {
      const pending = await ready();
      expect(pending.status).toBe(503);
      const pendingBody = await pending.json();
      expect(pendingBody.checks.migrations).toBe("pending");
      expect(JSON.stringify(pendingBody)).not.toContain(directory);
      const stillAlive = await live();
      expect(stillAlive.status).toBe(200);
      const blocked = await proxy(new NextRequest("http://127.0.0.1:3000/people"));
      expect(blocked.status).toBe(503);
      expect(await blocked.json()).toEqual({
        error: { code: "not_ready", message: "Application is not ready." },
      });
      const probe = await proxy(new NextRequest("http://127.0.0.1:3000/api/live"));
      expect(probe.status).toBe(200);
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("closes the shared pool and drops idle connections without crashing", async () => {
    expect(pool.listenerCount("error")).toBeGreaterThan(0);
    const first = createPool(databaseUrl);
    await first.query("SELECT 1");
    const { endPool } = await import("../packages/db/src/pool");
    await endPool(first);
    await expect(first.query("SELECT 1")).rejects.toThrow();
  });

  it("does not migrate from the web boot path", async () => {
    const boot = await readFile("apps/web/lib/boot.ts", "utf8");
    const instrumentation = await readFile("apps/web/instrumentation.ts", "utf8");
    const registerNode = await readFile("apps/web/lib/register-node.ts", "utf8");
    expect(boot).not.toMatch(/\bmigrate\s*\(/);
    expect(boot).not.toContain("importCanonical");
    expect(boot).not.toContain("resetDatabase");
    expect(instrumentation).not.toContain("importCanonical");
    expect(instrumentation).not.toContain("resetDatabase");
    expect(instrumentation).not.toContain("process.exit");
    expect(registerNode).toContain("publicCommandError");
    expect(registerNode).toContain("process.exit(1)");
    expect(registerNode).not.toContain("importCanonical");
    expect(registerNode).not.toContain("resetDatabase");
  });
});

describe("security headers", () => {
  it("uses a nonce CSP without host wildcards and omits HSTS on http", async () => {
    const first = await proxy(new NextRequest("http://127.0.0.1:3000/"));
    const second = await proxy(new NextRequest("http://127.0.0.1:3000/"));
    const csp = first.headers.get("content-security-policy") ?? "";
    const other = second.headers.get("content-security-policy") ?? "";
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("frame-src 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("script-src-attr 'none'");
    expect(csp).not.toContain("*");
    expect(csp).not.toContain("https:");
    expect(csp).not.toContain("http:");
    expect(csp).not.toMatch(/script-src[^;]*unsafe-inline/);
    expect(csp).not.toContain("unsafe-eval");
    expect(csp).not.toContain("unsafe-inline");
    expect(csp).not.toContain("upgrade-insecure-requests");
    expect(first.headers.get("x-content-type-options")).toBe("nosniff");
    expect(first.headers.get("referrer-policy")).toBe("strict-origin-when-cross-origin");
    expect(first.headers.get("x-frame-options")).toBe("DENY");
    expect(first.headers.get("permissions-policy")).toContain("camera=()");
    expect(first.headers.get("strict-transport-security")).toBeNull();
    expect(csp).not.toBe(other);
    const dev = contentSecurityPolicy({ nonce: "dev", development: true, hsts: false });
    expect(dev).toContain("unsafe-eval");
    expect(dev).toMatch(/style-src 'self' 'unsafe-inline'/);
  });

  it("sends HSTS when the public origin is https", async () => {
    setEnv({
      NODE_ENV: "production",
      PDOOM_ENV: "production",
      APP_BASE_URL: "https://pdoom.example",
      DATABASE_URL: databaseUrl,
    });
    clearReadinessCache();
    const response = await proxy(new NextRequest("https://pdoom.example/"));
    expect(response.headers.get("strict-transport-security")).toBe("max-age=15552000");
    expect(response.headers.get("content-security-policy")).toContain("upgrade-insecure-requests");
  });
});

describe("deployment files", () => {
  it("keeps public workflows on GitHub-hosted runners without deployment credentials", async () => {
    const { readdir, readFile: readText } = await import("node:fs/promises");
    const files = (await readdir(".github/workflows")).filter((file) => file.endsWith(".yml") || file.endsWith(".yaml"));
    expect(files.length).toBeGreaterThan(0);
    for (const file of files) {
      const text = await readText(join(".github/workflows", file), "utf8");
      expect(text).not.toMatch(/pull_request_target/);
      expect(text).not.toMatch(/self-hosted/);
      expect(text).not.toContain("secrets.");
      expect(text).toMatch(/contents:\s*read/);
      expect(text).not.toMatch(/contents:\s*write/);
      expect(text).not.toMatch(/id-token:\s*write/);
      expect(text).toContain("persist-credentials: false");
    }
  });

  it("packages a non-root multi-stage web image and a postgres compose file", async () => {
    const docker = await readFile("Dockerfile", "utf8");
    const runtime = docker.split("FROM node:22-bookworm-slim AS runtime")[1] ?? "";
    expect(docker).toContain("FROM node:22-bookworm-slim AS deps");
    expect(docker).toContain("FROM node:22-bookworm-slim AS build");
    expect(docker).toContain("npm ci");
    expect(docker).toContain("USER pdoom");
    expect(docker).toContain("HEALTHCHECK");
    expect(docker).toContain("/usr/bin/tini");
    expect(runtime).not.toContain("npm ci");
    expect(runtime).not.toMatch(/npm install/);
    expect(runtime).toContain("pdoom-cli.mjs");
    const rootPackage = JSON.parse(await readFile("package.json", "utf8")) as { scripts: { "build:cli": string } };
    expect(rootPackage.scripts["build:cli"]).toContain("createRequire");
    expect(rootPackage.scripts["build:cli"]).toContain("dist/pdoom-cli.mjs");
    const compose = await readFile("compose.yaml", "utf8");
    expect(compose).toContain("postgres:");
    expect(compose).toContain("web:");
    expect(compose).not.toMatch(/redis|crawler|queue/i);
  });
});
