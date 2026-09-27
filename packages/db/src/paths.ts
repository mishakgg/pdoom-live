import { existsSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { ConfigError } from "./env";

export const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
export const migrationsDir = resolve(dirname(fileURLToPath(import.meta.url)), "../migrations");
export const fixturePath = resolve(repoRoot, "data/fixtures/synthetic/dataset.json");

function isDirectory(path: string): boolean {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

function hasMigrationMarker(path: string): boolean {
  return existsSync(join(path, "001_init.sql"));
}

export function migrationsDirectory(): string {
  const override = process.env.PDOOM_MIGRATIONS_DIR;
  if (override !== undefined) {
    if (!override.trim() || /[\0\r\n]/.test(override) || !isDirectory(override)) {
      throw new ConfigError("PDOOM_MIGRATIONS_DIR is not a directory");
    }
    return resolve(override);
  }
  const candidates = [
    migrationsDir,
    resolve(process.cwd(), "packages/db/migrations"),
    resolve(process.cwd(), "../../packages/db/migrations"),
    resolve(process.cwd(), "../../../packages/db/migrations"),
    resolve(process.cwd(), "migrations"),
    "/app/migrations",
  ];
  for (const candidate of candidates) {
    if (hasMigrationMarker(candidate)) return resolve(candidate);
  }
  throw new ConfigError("migrations directory is not available");
}

export function fixtureFile(): string {
  if (process.env.PDOOM_FIXTURE_PATH) return resolve(process.env.PDOOM_FIXTURE_PATH);
  const candidates = [
    fixturePath,
    resolve(process.cwd(), "data/fixtures/synthetic/dataset.json"),
    resolve(process.cwd(), "../../data/fixtures/synthetic/dataset.json"),
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return fixturePath;
}
