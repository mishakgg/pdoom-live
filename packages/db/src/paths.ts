import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
export const migrationsDir = resolve(dirname(fileURLToPath(import.meta.url)), "../migrations");
export const fixturePath = resolve(repoRoot, "data/fixtures/synthetic/dataset.json");
