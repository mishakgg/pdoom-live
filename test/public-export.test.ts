import { mkdtemp, readFile, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { describe, expect, it } from "vitest";
import { parseCsv, toCsv, PUBLIC_API_PATHS, validateOpenApiDocument } from "@pdoom/contracts";
import { assertSnapshotOutputPath, exportPublicSnapshot, snapshotId } from "@pdoom/db";
import { createPool } from "../packages/db/src/pool";
import { readDatabaseUrl } from "../packages/db/src/env";
import { repoRoot } from "../packages/db/src/paths";

const execFileAsync = promisify(execFile);
const GENERATED_AT = "2026-09-27T00:00:00.000Z";
const FORBIDDEN_KEYS = [
  "verification_detail",
  "extractor_version",
  "extraction_run_slug",
  "prompt_contract_version",
  "model_name",
  "model_provider",
  "input_hash",
  "output_hash",
  "content_hash_input",
  "rights_notes",
  "attribution_detail",
  "collection_adapter",
  "error_summary",
  "logical_key",
  "ingestion_run_slug",
];

function walk(value: unknown, visit: (key: string, child: unknown) => void) {
  if (Array.isArray(value)) {
    for (const item of value) walk(item, visit);
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      visit(key, child);
      walk(child, visit);
    }
  }
}

describe("public snapshot", () => {
  it("escapes CSV commas, quotes, and newlines", () => {
    const csv = toCsv(["note", "value"], [{ note: 'she said "12%, maybe"\nnext', value: 0.12 }]);
    const rows = parseCsv(csv);
    expect(rows[0]).toEqual(["note", "value"]);
    expect(rows[1]).toEqual(['she said "12%, maybe"\nnext', "0.12"]);
  });

  it("refuses to write into source data", () => {
    expect(() => assertSnapshotOutputPath(resolve(repoRoot, "data/fixtures/synthetic"))).toThrow(/fixtures/);
    expect(() => assertSnapshotOutputPath(resolve(repoRoot, "data/seed/cohort"))).toThrow(/seed/);
  });

  it("writes a deterministic snapshot with public records only", async () => {
    const pool = createPool(readDatabaseUrl("DATABASE_URL"));
    const leftDir = await mkdtemp(join(tmpdir(), "pdoom-export-a-"));
    const rightDir = await mkdtemp(join(tmpdir(), "pdoom-export-b-"));
    try {
      const left = await exportPublicSnapshot({ outDir: leftDir, generatedAt: GENERATED_AT }, pool);
      const right = await exportPublicSnapshot({ outDir: rightDir, generatedAt: GENERATED_AT }, pool);
      const names = (await readdir(leftDir)).sort();
      expect(names).toEqual((await readdir(rightDir)).sort());
      for (const name of names) {
        const leftBody = await readFile(join(leftDir, name));
        const rightBody = await readFile(join(rightDir, name));
        expect(leftBody.equals(rightBody)).toBe(true);
      }
      expect(left.snapshot_id).toBe(right.snapshot_id);
      const manifest = left.manifest;
      expect(manifest.export_schema_version).toBe("1.0.0");
      expect(manifest.generated_at).toBe(GENERATED_AT);
      expect(manifest.dataset?.dataset_kind).toBe("synthetic");
      expect(manifest.cohort?.slug).toBe("synthetic-frontier-v1");
      expect(manifest.methodology.cohort_methodology_version).toBe("2026.09.0");
      expect(manifest.methodology.provenance_policy_ref).toContain("SOURCE_AND_PROVENANCE_POLICY");
      expect(manifest.license.status).toBe("cc0-1.0");
      expect(manifest.counts.statements).toBeGreaterThan(0);
      expect(manifest.counts.statements).toBe(manifest.files["statements.json"]?.records);
      expect(manifest.snapshot_id).toBe(
        snapshotId({
          files: Object.entries(manifest.files).map(([name, file]) => ({ name, sha256: file.sha256, bytes: file.bytes })),
          generatedAt: GENERATED_AT,
          importedAt: manifest.dataset?.imported_at ?? null,
          datasetId: manifest.dataset?.dataset_id ?? null,
        }),
      );

      const statements = JSON.parse(await readFile(join(leftDir, "statements.json"), "utf8")) as Array<Record<string, unknown>>;
      const people = JSON.parse(await readFile(join(leftDir, "people.json"), "utf8")) as Array<Record<string, unknown>>;
      const sources = JSON.parse(await readFile(join(leftDir, "sources.json"), "utf8")) as Array<Record<string, unknown>>;
      const items = JSON.parse(await readFile(join(leftDir, "source_items.json"), "utf8")) as Array<Record<string, unknown>>;
      expect(statements.some((row) => row.slug === "jonah-extinction-review-2024")).toBe(false);
      expect(items.some((row) => row.slug === "jonah-review-2024")).toBe(false);
      const ada = statements.find((row) => row.slug === "ada-extinction-2025");
      expect(ada).toMatchObject({
        review_state: "human_verified",
        verified: true,
        machine_labeled: false,
        statement_type: "explicit_numeric",
      });
      const forecast = ada?.forecast as Record<string, unknown>;
      expect(forecast.question_key).toBe("ai_extinction_unconditional_by_2070");
      expect(forecast.definition_text).toEqual(expect.any(String));
      expect(forecast.horizon_text).toEqual(expect.any(String));
      expect(forecast.unit).toBe("probability");
      expect(forecast.value_numeric).toBeCloseTo(0.12);
      expect(people.some((person) => person.slug === (ada?.person as { slug: string }).slug)).toBe(true);
      expect(sources.some((source) => source.slug === (ada?.source as { slug: string }).slug)).toBe(true);
      const item = items.find((row) => row.slug === (ada?.source_item as { slug: string }).slug);
      expect(item?.canonical_url).toBe((ada?.source_item as { canonical_url: string }).canonical_url);
      expect((ada?.evidence as { segment_hash: string }).segment_hash).toMatch(/^[a-f0-9]{64}$/);

      const inferred = statements.find((row) => row.slug === "ada-inferred-2024");
      expect(inferred).toMatchObject({ review_state: "machine_validated", verified: false, machine_labeled: true });
      expect((inferred?.forecast as { value_numeric?: number } | null)?.value_numeric ?? null).toBeNull();

      const riley = people.find((person) => person.slug === "riley-moss");
      expect(riley).toMatchObject({ status: "review", in_current_cohort: false });

      for (const name of names.filter((file) => file.endsWith(".json") && file !== "manifest.json")) {
        const body = JSON.parse(await readFile(join(leftDir, name), "utf8")) as unknown;
        const seen = new Set<string>();
        walk(body, (key, child) => {
          seen.add(key);
          if (key === "review_state") {
            expect(["human_verified", "machine_validated"]).toContain(child);
          }
        });
        for (const key of FORBIDDEN_KEYS) expect(seen.has(key)).toBe(false);
        expect(JSON.stringify(body)).not.toContain("jonah-extinction-review-2024");
        expect(JSON.stringify(body)).not.toContain("content_hash_input");
      }

      const table = parseCsv(await readFile(join(leftDir, "statements.csv"), "utf8"));
      const header = table[0] ?? [];
      const textIndex = header.indexOf("normalized_text");
      const quoted = table.find((row) => (row[textIndex] ?? "").includes(","));
      expect(quoted?.length).toBe(header.length);
      expect(manifest.counts.people).toBe(people.length);
      expect(manifest.counts.statements).toBe(statements.length);
      expect(manifest.counts.forecasts).toBeLessThanOrEqual(statements.length);
    } finally {
      await pool.end();
    }
  });

  it("runs the operator export command", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "pdoom-export-cli-"));
    const result = await execFileAsync(
      process.execPath,
      [join(repoRoot, "node_modules/tsx/dist/cli.mjs"), "packages/db/src/cli.ts", "export", "--out", outDir, "--generated-at", GENERATED_AT],
      { cwd: repoRoot, env: { ...process.env, DATABASE_URL: process.env.DATABASE_URL } },
    );
    const printed = JSON.parse(result.stdout) as { snapshot_id: string; counts: { statements: number } };
    expect(printed.snapshot_id).toMatch(/^[a-f0-9]{64}$/);
    expect(printed.counts.statements).toBeGreaterThan(0);
    const manifest = JSON.parse(await readFile(join(outDir, "manifest.json"), "utf8")) as { snapshot_id: string };
    expect(manifest.snapshot_id).toBe(printed.snapshot_id);
  });
});

describe("OpenAPI document", () => {
  it("is a valid public v1 description without real researcher names", async () => {
    const specPath = resolve(repoRoot, "packages/contracts/openapi/public-v1.openapi.json");
    const specText = await readFile(specPath, "utf8");
    const document = JSON.parse(specText) as unknown;
    const issues = validateOpenApiDocument(document, PUBLIC_API_PATHS);
    expect(issues).toEqual([]);
    const resolution = await readFile(resolve(repoRoot, "data/seed/cohort/v2026-09/resolution.json"), "utf8");
    const names = new Set<string>();
    for (const match of resolution.matchAll(/"(?:matched_name|display_name)"\s*:\s*"([^"]+)"/g)) {
      const name = match[1];
      if (name && name.length >= 8) names.add(name);
    }
    expect(names.size).toBeGreaterThan(10);
    for (const name of names) expect(specText.includes(name)).toBe(false);
    expect(specText).toContain("Example Researcher");
    expect(specText).toContain("machine_labeled");
  });
});
