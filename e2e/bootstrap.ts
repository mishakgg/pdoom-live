import { readFileSync } from "node:fs";
import { assertTestDatabase, clearProductTables, createPool, importCanonical, migrate, resetDatabase } from "@pdoom/db";
import {
  adminDatabaseUrl,
  emptyDatabaseUrl,
  fixtureDatabaseUrl,
  hostileEvidence,
  longEvidenceText,
  rejectedMarker,
  rejectedSlug,
  unreviewedMarker,
  unreviewedSlug,
} from "./support/env";

const databaseName = /^[a-z0-9_]+$/;

async function ensureDatabase(name: string): Promise<void> {
  if (!databaseName.test(name)) throw new Error(`refusing to create database ${name}`);
  const admin = createPool(adminDatabaseUrl);
  try {
    const existing = await admin.query("SELECT 1 FROM pg_database WHERE datname = $1", [name]);
    if (existing.rowCount === 0) await admin.query(`CREATE DATABASE ${name}`);
  } finally {
    await admin.end();
  }
}

function databaseNameFromUrl(url: string): string {
  return new URL(url).pathname.replace(/^\//, "");
}

async function applyOverlay(databaseUrl: string): Promise<void> {
  if (hostileEvidence.length > 2000) throw new Error("hostile evidence exceeds the segment limit");
  if (longEvidenceText.length > 2000) throw new Error("long evidence exceeds the segment limit");
  const pool = createPool(databaseUrl);
  try {
    const evidence = await pool.query("UPDATE evidence_segments SET text = $1 WHERE slug = 'riley-hostile-2025-evidence'", [
      hostileEvidence,
    ]);
    if (evidence.rowCount !== 1) throw new Error("hostile evidence overlay did not match the fixture segment");
    const longEvidence = await pool.query("UPDATE evidence_segments SET text = $1 WHERE slug = 'harbor-large-note-evidence'", [
      longEvidenceText,
    ]);
    if (longEvidence.rowCount !== 1) throw new Error("long evidence overlay did not match the fixture segment");
    const stale = await pool.query(
      "UPDATE sources SET last_success_at = '2000-01-01T00:00:00Z', last_checked_at = '2000-01-01T00:00:00Z' WHERE slug = 'jonah-blog'",
    );
    if (stale.rowCount !== 1) throw new Error("stale source overlay did not match jonah-blog");
    for (const [slug, marker, reviewState] of [
      [unreviewedSlug, unreviewedMarker, "unreviewed"],
      [rejectedSlug, rejectedMarker, "rejected"],
    ] as const) {
      const inserted = await pool.query(
        `INSERT INTO statements (
           slug, person_id, source_item_id, statement_type, normalized_text, event_time,
           evidence_segment_id, extractor_name, extractor_version, confidence, review_state, extraction_run_id
         )
         SELECT $1, s.person_id, s.source_item_id, 'explicit_qualitative', $2, s.event_time,
                s.evidence_segment_id, s.extractor_name, s.extractor_version, s.confidence, $3, s.extraction_run_id
         FROM statements s
         WHERE s.slug = 'riley-hostile-2025'
         RETURNING slug`,
        [slug, marker, reviewState],
      );
      if (inserted.rowCount !== 1) throw new Error(`overlay statement ${slug} was not inserted`);
    }
  } finally {
    await pool.end();
  }
}

async function seedFixture(): Promise<void> {
  assertTestDatabase(fixtureDatabaseUrl);
  await ensureDatabase(databaseNameFromUrl(fixtureDatabaseUrl));
  const pool = createPool(fixtureDatabaseUrl);
  try {
    await migrate(pool);
    await resetDatabase(pool);
  } finally {
    await pool.end();
  }
  await applyOverlay(fixtureDatabaseUrl);
}

async function seedEmptyLive(): Promise<void> {
  assertTestDatabase(emptyDatabaseUrl);
  await ensureDatabase(databaseNameFromUrl(emptyDatabaseUrl));
  const document = JSON.parse(readFileSync(new URL("./fixtures/empty-live.json", import.meta.url), "utf8")) as unknown;
  const pool = createPool(emptyDatabaseUrl);
  try {
    await migrate(pool);
    await clearProductTables(pool);
    const result = await importCanonical(pool, document);
    if (result.dataset_kind !== "live") throw new Error("empty browser dataset must be live");
    if ((result.imported.statements ?? 0) !== 0) throw new Error("empty browser dataset must not include statements");
  } finally {
    await pool.end();
  }
}

await seedFixture();
await seedEmptyLive();
console.log("e2e databases ready");
