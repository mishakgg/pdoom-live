import { createHash } from "node:crypto";
import { mkdir, realpath, writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";
import {
  PUBLIC_EXPORT_SCHEMA_VERSION,
  PUBLIC_FORECAST_CSV_COLUMNS,
  PUBLIC_PEOPLE_CSV_COLUMNS,
  PUBLIC_STATEMENT_CSV_COLUMNS,
  normalizeTimestamp,
  toCsv,
} from "@pdoom/contracts";
import type pg from "pg";
import { repoRoot } from "./paths";
import { getPool } from "./pool";
import { loadPublicExport, type PublicExportBundle, type PublicStatement } from "./public-read";

const BLOCKED_PREFIXES = [
  "data/fixtures",
  "data/seed",
  "data/raw",
  "data/collections",
  "data/reports",
  "pipeline",
  "apps",
  "packages",
  "docs",
];

function isInside(parent: string, child: string): boolean {
  const rel = relative(parent, child);
  return rel === "" || (!rel.startsWith(`..${sep}`) && rel !== ".." && !isAbsolute(rel));
}

function blockedReason(candidate: string): string | null {
  const root = resolve(repoRoot);
  if (candidate === root) return "the repository root";
  for (const prefix of BLOCKED_PREFIXES) {
    if (isInside(resolve(root, prefix), candidate)) return prefix;
  }
  return null;
}

/** Refuse to overwrite fixtures, seeds, or application source with a generated snapshot. */
export function assertSnapshotOutputPath(outDir: string): void {
  const reason = blockedReason(resolve(outDir));
  if (reason) throw new Error(`refusing to write a public snapshot into ${reason}`);
}

async function assertRealSnapshotOutputPath(outDir: string): Promise<string> {
  assertSnapshotOutputPath(outDir);
  await mkdir(outDir, { recursive: true });
  const real = await realpath(outDir);
  const reason = blockedReason(real);
  if (reason) throw new Error(`refusing to write a public snapshot into ${reason}`);
  return real;
}

export function stableStringify(value: unknown): string {
  return `${JSON.stringify(sortValue(value), null, 2)}\n`;
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) sorted[key] = sortValue(record[key]);
    return sorted;
  }
  return value;
}

function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

function cell(value: string | number | boolean | null | undefined): string | number | boolean | null {
  return value === undefined ? null : value;
}

function peopleCsv(bundle: PublicExportBundle): string {
  return toCsv(
    PUBLIC_PEOPLE_CSV_COLUMNS,
    bundle.people.map((person) => ({
      slug: person.slug,
      display_name: person.display_name,
      given_name: cell(person.given_name),
      family_name: cell(person.family_name),
      status: person.status,
      in_current_cohort: person.in_current_cohort,
      inclusion_reason: person.inclusion_reason,
      organization_slug: cell(person.organization?.slug),
      organization_name: cell(person.organization?.name),
      organization_role: cell(person.organization?.role),
    })),
  );
}

function statementCsv(statement: PublicStatement) {
  return {
    slug: statement.slug,
    person_slug: statement.person.slug,
    person_display_name: statement.person.display_name,
    statement_type: statement.statement_type,
    review_state: statement.review_state,
    verified: statement.verified,
    machine_labeled: statement.machine_labeled,
    event_time: cell(statement.event_time),
    normalized_text: statement.normalized_text,
    source_slug: statement.source.slug,
    source_item_slug: statement.source_item.slug,
    canonical_url: statement.source_item.canonical_url,
    evidence_slug: statement.evidence.slug,
    evidence_segment_hash: statement.evidence.segment_hash,
    topic_slugs: statement.topics.map((topic) => topic.slug).join("|"),
    question_key: cell(statement.forecast?.question_key),
    question_text: cell(statement.forecast?.question_text),
    definition_text: cell(statement.forecast?.definition_text),
    condition_text: cell(statement.forecast?.condition_text),
    horizon_text: cell(statement.forecast?.horizon_text),
    unit: cell(statement.forecast?.unit),
    value_type: cell(statement.forecast?.value_type),
    value_numeric: cell(statement.forecast?.value_numeric),
    value_min: cell(statement.forecast?.value_min),
    value_max: cell(statement.forecast?.value_max),
  };
}

function forecastCsv(bundle: PublicExportBundle): string {
  const bySlug = new Map(bundle.statements.map((statement) => [statement.slug, statement]));
  return toCsv(
    PUBLIC_FORECAST_CSV_COLUMNS,
    bundle.forecasts.map((forecast) => {
      const statement = bySlug.get(forecast.statement_slug);
      return {
        statement_slug: forecast.statement_slug,
        person_slug: cell(statement?.person.slug),
        person_display_name: cell(statement?.person.display_name),
        statement_type: cell(statement?.statement_type),
        review_state: forecast.review_state,
        verified: forecast.verified,
        machine_labeled: forecast.machine_labeled,
        forecast_kind: forecast.forecast_kind,
        question_key: forecast.question_key,
        question_text: forecast.question_text,
        definition_text: cell(forecast.definition_text),
        condition_text: cell(forecast.condition_text),
        horizon_text: cell(forecast.horizon_text),
        target_date_start: cell(forecast.target_date_start),
        target_date_end: cell(forecast.target_date_end),
        value_type: forecast.value_type,
        value_numeric: cell(forecast.value_numeric),
        value_min: cell(forecast.value_min),
        value_max: cell(forecast.value_max),
        unit: cell(forecast.unit),
        event_time: cell(statement?.event_time),
        canonical_url: cell(statement?.source_item.canonical_url),
        source_item_slug: cell(statement?.source_item.slug),
      };
    }),
  );
}

export function snapshotId(input: {
  files: Array<{ name: string; sha256: string; bytes: number }>;
  generatedAt: string;
  importedAt: string | null;
  datasetId: string | null;
}): string {
  const lines = input.files
    .filter((file) => file.name !== "manifest.json")
    .sort((left, right) => left.name.localeCompare(right.name))
    .map((file) => `${file.name}\t${file.sha256}\t${file.bytes}`);
  lines.push(`export_schema_version\t${PUBLIC_EXPORT_SCHEMA_VERSION}`);
  lines.push(`generated_at\t${input.generatedAt}`);
  lines.push(`imported_at\t${input.importedAt ?? ""}`);
  lines.push(`dataset_id\t${input.datasetId ?? ""}`);
  return sha256(`${lines.join("\n")}\n`);
}

function fileRecord(name: string, body: string, records: number) {
  return { name, body, records, bytes: Buffer.byteLength(body), sha256: sha256(body) };
}

export async function writePublicSnapshot(outDir: string, bundle: PublicExportBundle) {
  const realDir = await assertRealSnapshotOutputPath(outDir);
  const jsonFiles = [
    fileRecord("people.json", stableStringify(bundle.people), bundle.people.length),
    fileRecord("organizations.json", stableStringify(bundle.organizations), bundle.organizations.length),
    fileRecord("identities.json", stableStringify(bundle.identities), bundle.identities.length),
    fileRecord("sources.json", stableStringify(bundle.sources), bundle.sources.length),
    fileRecord("source_items.json", stableStringify(bundle.source_items), bundle.source_items.length),
    fileRecord("statements.json", stableStringify(bundle.statements), bundle.statements.length),
    fileRecord("forecasts.json", stableStringify(bundle.forecasts), bundle.forecasts.length),
    fileRecord("topics.json", stableStringify(bundle.topics), bundle.topics.length),
    fileRecord("relationships.json", stableStringify(bundle.relationships), bundle.relationships.length),
    fileRecord("trends.json", stableStringify(bundle.trends), bundle.trends.length),
  ];
  const csvFiles = [
    fileRecord("people.csv", peopleCsv(bundle), bundle.people.length),
    fileRecord("statements.csv", toCsv(PUBLIC_STATEMENT_CSV_COLUMNS, bundle.statements.map(statementCsv)), bundle.statements.length),
    fileRecord("forecasts.csv", forecastCsv(bundle), bundle.forecasts.length),
  ];
  const dataFiles = [...jsonFiles, ...csvFiles];
  const generatedAt = bundle.catalog.as_of ?? new Date(0).toISOString();
  const id = snapshotId({
    files: dataFiles,
    generatedAt,
    importedAt: bundle.catalog.dataset?.imported_at ?? null,
    datasetId: bundle.catalog.dataset?.dataset_id ?? null,
  });
  const manifest = {
    ...bundle.catalog,
    generated_at: generatedAt,
    snapshot_id: id,
    about:
      "Public research export from pdoom.live. This is not the internal canonical import document. Rejected, unreviewed, and needs_review records are omitted. machine_validated is labeled and is not human verification.",
    files: Object.fromEntries(dataFiles.map((file) => [file.name, { sha256: file.sha256, bytes: file.bytes, records: file.records }])),
  };
  const manifestBody = stableStringify(manifest);
  await Promise.all([
    ...dataFiles.map((file) => writeFile(resolve(realDir, file.name), file.body)),
    writeFile(resolve(realDir, "manifest.json"), manifestBody),
  ]);
  return { outDir: realDir, manifest, snapshot_id: id };
}

export function resolveExportOptions(argv: string[]): { outDir: string; generatedAt: string } {
  let outDir = resolve(repoRoot, "data/exports/public");
  let generatedAt = new Date().toISOString();
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--out") {
      const next = argv[index + 1];
      if (!next) throw new Error("usage: npm run data:export -- --out <dir> [--generated-at <iso>]");
      outDir = resolve(next);
      index += 1;
      continue;
    }
    if (arg === "--generated-at") {
      const next = argv[index + 1];
      if (!next) throw new Error("usage: npm run data:export -- --out <dir> [--generated-at <iso>]");
      generatedAt = normalizeTimestamp(next);
      index += 1;
      continue;
    }
    throw new Error(`unknown export argument: ${arg ?? ""}`);
  }
  return { outDir, generatedAt };
}

export async function exportPublicSnapshot(
  options: { outDir: string; generatedAt: string },
  pool: pg.Pool = getPool(),
) {
  const client = await pool.connect();
  let bundle: PublicExportBundle;
  try {
    await client.query("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY");
    bundle = await loadPublicExport(options.generatedAt, client);
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
  return writePublicSnapshot(options.outDir, bundle);
}
