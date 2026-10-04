export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

export type RuntimeMode = "production" | "development" | "test";

export type RuntimeConfig = {
  mode: RuntimeMode;
  databaseUrl: string | null;
  appBaseUrl: URL | null;
  hsts: boolean;
};

const KNOWN_PDOOM_KEYS = new Set([
  "PDOOM_ENV",
  "PDOOM_HSTS",
  "PDOOM_MIGRATIONS_DIR",
  "PDOOM_IMPORT_HOLD",
  "PDOOM_FIXTURE_PATH",
  "PDOOM_DOCKER_TEST",
  "PDOOM_CURATION_MODE",
  "PDOOM_METRICS_ENABLED",
  "PDOOM_METRICS_TOKEN",
  "PDOOM_QUALITY_BASELINE",
  "PDOOM_PUBLIC_RATE_LIMIT",
  "PDOOM_PUBLIC_RATE_WINDOW_MS",
  "PDOOM_PUBLIC_PROCESS_RATE_LIMIT",
  "PDOOM_TRUSTED_PROXY_HOPS",
]);

export function deploymentMode(env: NodeJS.ProcessEnv = process.env): RuntimeMode {
  const explicit = env.PDOOM_ENV;
  if (explicit !== undefined && explicit !== "production" && explicit !== "development" && explicit !== "test") {
    throw new ConfigError("PDOOM_ENV must be production, development, or test");
  }
  if (explicit) return explicit;
  if (env.NODE_ENV === "production") return "production";
  if (env.NODE_ENV === "test") return "test";
  return "development";
}

export function parseDatabaseUrl(value: string | undefined, name = "DATABASE_URL"): string {
  if (value === undefined || value.trim() === "") {
    throw new ConfigError(`${name} is required`);
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new ConfigError(`${name} must be a postgres URL`);
  }
  if (url.protocol !== "postgres:" && url.protocol !== "postgresql:") {
    throw new ConfigError(`${name} must be a postgres URL`);
  }
  const database = url.pathname.replace(/^\//, "");
  if (!url.hostname && !database) {
    throw new ConfigError(`${name} must be a postgres URL`);
  }
  if (!database) {
    throw new ConfigError(`${name} must include a database name`);
  }
  return value;
}

export function readDatabaseUrl(name = "DATABASE_URL"): string {
  const value = process.env[name] ?? (name === "DATABASE_URL" ? undefined : process.env.DATABASE_URL);
  return parseDatabaseUrl(value, name);
}

export function assertTestDatabase(url: string): void {
  let dbName = "";
  try {
    dbName = new URL(url).pathname.replace(/^\//, "");
  } catch {
    throw new ConfigError("DATABASE_URL must be a postgres URL");
  }
  if (!dbName.includes("test")) {
    throw new Error(`Refusing to run destructive tests against database "${dbName}"`);
  }
}

function rejectUnknownPdoom(env: NodeJS.ProcessEnv): void {
  for (const key of Object.keys(env)) {
    if (key.startsWith("PDOOM_") && !KNOWN_PDOOM_KEYS.has(key)) {
      throw new ConfigError(`unknown configuration ${key}`);
    }
  }
}

function optionalPresent(env: NodeJS.ProcessEnv, name: string): string | undefined {
  if (!Object.prototype.hasOwnProperty.call(env, name)) return undefined;
  const value = env[name];
  if (value === undefined || value.trim() === "") {
    throw new ConfigError(`${name} is set but empty`);
  }
  return value;
}

export function hstsEnabled(env: NodeJS.ProcessEnv, appBaseUrl: URL | null): boolean {
  const flag = optionalPresent(env, "PDOOM_HSTS");
  if (flag !== undefined && flag !== "on" && flag !== "off") {
    throw new ConfigError("PDOOM_HSTS must be on or off");
  }
  if (flag === "off") return false;
  if (flag === "on") return true;
  return appBaseUrl?.protocol === "https:";
}

function readAppBaseUrl(env: NodeJS.ProcessEnv, required: boolean): URL | null {
  const value = optionalPresent(env, "APP_BASE_URL");
  if (!value) {
    if (required) throw new ConfigError("APP_BASE_URL is required");
    return null;
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new ConfigError("APP_BASE_URL must be an absolute http(s) URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new ConfigError("APP_BASE_URL must be an absolute http(s) URL");
  }
  if (url.username || url.password) {
    throw new ConfigError("APP_BASE_URL must not include credentials");
  }
  if ((url.pathname !== "/" && url.pathname !== "") || url.search || url.hash) {
    throw new ConfigError("APP_BASE_URL must be an origin without a path, query, or fragment");
  }
  return url;
}

function validateOptional(env: NodeJS.ProcessEnv, mode: RuntimeMode): void {
  const port = optionalPresent(env, "PORT");
  if (port !== undefined) {
    const parsed = Number(port);
    if (!/^[0-9]+$/.test(port) || parsed < 1 || parsed > 65535) {
      throw new ConfigError("PORT must be an integer from 1 to 65535");
    }
  }
  optionalPresent(env, "OPENAI_API_KEY");
  const migrations = optionalPresent(env, "PDOOM_MIGRATIONS_DIR");
  if (migrations !== undefined && /[\0\r\n]/.test(migrations)) {
    throw new ConfigError("PDOOM_MIGRATIONS_DIR is invalid");
  }
  if (mode === "production" && env.PDOOM_IMPORT_HOLD) {
    throw new ConfigError("PDOOM_IMPORT_HOLD is not allowed in production");
  }
  if (mode === "production" && env.PDOOM_FIXTURE_PATH) {
    throw new ConfigError("PDOOM_FIXTURE_PATH is not allowed in production");
  }
  if (mode === "production" && env.PDOOM_DOCKER_TEST) {
    throw new ConfigError("PDOOM_DOCKER_TEST is not allowed in production");
  }
  const metrics = optionalPresent(env, "PDOOM_METRICS_ENABLED");
  if (metrics !== undefined && metrics !== "1" && metrics !== "true") {
    throw new ConfigError("PDOOM_METRICS_ENABLED must be 1 or true");
  }
  const metricsToken = optionalPresent(env, "PDOOM_METRICS_TOKEN");
  if (metricsToken !== undefined && /[\0\r\n]/.test(metricsToken)) {
    throw new ConfigError("PDOOM_METRICS_TOKEN is invalid");
  }
  const baseline = optionalPresent(env, "PDOOM_QUALITY_BASELINE");
  if (baseline !== undefined && /[\0\r\n]/.test(baseline)) {
    throw new ConfigError("PDOOM_QUALITY_BASELINE is invalid");
  }
  const curation = optionalPresent(env, "PDOOM_CURATION_MODE");
  if (curation !== undefined && curation !== "local") {
    throw new ConfigError("PDOOM_CURATION_MODE must be local");
  }
  if (mode === "production" && curation) {
    throw new ConfigError("PDOOM_CURATION_MODE is not allowed in production");
  }
  optionalBoundedInt(env, "PDOOM_PUBLIC_RATE_LIMIT", 1, 1_000_000);
  optionalBoundedInt(env, "PDOOM_PUBLIC_RATE_WINDOW_MS", 1_000, 3_600_000);
  optionalBoundedInt(env, "PDOOM_PUBLIC_PROCESS_RATE_LIMIT", 1, 1_000_000);
  optionalBoundedInt(env, "PDOOM_TRUSTED_PROXY_HOPS", 0, 8);
}

function optionalBoundedInt(env: NodeJS.ProcessEnv, name: string, min: number, max: number): void {
  const raw = optionalPresent(env, name);
  if (raw === undefined) return;
  if (!/^[0-9]+$/.test(raw)) throw new ConfigError(`${name} must be an integer`);
  const parsed = Number(raw);
  if (parsed < min || parsed > max) throw new ConfigError(`${name} must be an integer from ${min} to ${max}`);
}

export function readRuntimeConfig(env: NodeJS.ProcessEnv = process.env): RuntimeConfig {
  rejectUnknownPdoom(env);
  const mode = deploymentMode(env);
  validateOptional(env, mode);
  if (mode === "production") {
    if (env.NODE_ENV !== "production") {
      throw new ConfigError("NODE_ENV must be production when PDOOM_ENV is production");
    }
    if (env.PDOOM_ENV !== "production") {
      throw new ConfigError("PDOOM_ENV must be production when NODE_ENV is production");
    }
    const databaseUrl = parseDatabaseUrl(env.DATABASE_URL, "DATABASE_URL");
    const appBaseUrl = readAppBaseUrl(env, true);
    return { mode, databaseUrl, appBaseUrl, hsts: hstsEnabled(env, appBaseUrl) };
  }
  const databaseRaw = optionalPresent(env, "DATABASE_URL");
  const databaseUrl = databaseRaw ? parseDatabaseUrl(databaseRaw, "DATABASE_URL") : null;
  const appBaseUrl = readAppBaseUrl(env, false);
  return { mode, databaseUrl, appBaseUrl, hsts: hstsEnabled(env, appBaseUrl) };
}

export function publicCommandError(error: unknown): string {
  if (!(error instanceof Error) || !error.message) return "command failed";
  return error.message.replace(/postgres(ql)?:\/\/\S+/gi, "[redacted]").slice(0, 500);
}

export function assertDevelopmentMutation(command: string): void {
  if (deploymentMode() === "production") {
    throw new ConfigError(`refusing to ${command} in production; production does not load synthetic fixtures or reset data`);
  }
}
