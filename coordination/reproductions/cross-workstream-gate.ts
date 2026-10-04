/**
 * Isolated cross-workstream gate for the recorded main tree.
 * Uses pdoom_coord_integration_test and pdoom_coord_cohort_test only.
 * Does not change product behavior. Exit 1 when a scenario misses its expected outcome.
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import pg from "pg";
import { publicJson } from "../../apps/web/lib/public-http.ts";
import { classifyFreshness } from "../../packages/contracts/src/freshness.ts";
import { createPool } from "../../packages/db/src/pool.ts";
import { migrate } from "../../packages/db/src/migrate.ts";
import { importCanonical, validateDocument } from "../../packages/db/src/import.ts";
import { applyReviewDecision, emptyConfirmations, exportReviewManifest, importReviewManifest } from "../../packages/db/src/review.ts";
import { getStatement, listStatements } from "../../packages/db/src/queries.ts";
import { listFeedEntries } from "../../packages/db/src/discovery.ts";
import { searchPublic } from "../../packages/db/src/search.ts";
import { getTrend } from "../../packages/db/src/trend-query.ts";
import { stableId } from "../../packages/db/src/ids.ts";
import {
  getDatasetStamp,
  getPublicStatement,
  listPublicStatements,
} from "../../packages/db/src/public-read.ts";
import { computeProbabilityDistribution, type TrendCandidate } from "../../packages/db/src/trend-engine.ts";
import { PREPARED_TRENDS } from "../../packages/db/src/trend-catalog.ts";

const ADMIN = "postgresql://postgres:postgres@127.0.0.1:5432/postgres";
const INTEGRATION = "postgresql://postgres:postgres@127.0.0.1:5432/pdoom_coord_integration_test";
const COHORT = "postgresql://postgres:postgres@127.0.0.1:5432/pdoom_coord_cohort_test";
const AS_OF = "2026-10-04T20:40:00.000Z";

type Scenario = {
  id: string;
  pass: boolean;
  expected: string;
  actual: unknown;
  owner: string | null;
};

const scenarios: Scenario[] = [];

function record(id: string, pass: boolean, expected: string, actual: unknown, owner: string | null = null) {
  scenarios.push({ id, pass, expected, actual, owner: pass ? null : owner });
}

async function recreate(name: string) {
  const admin = new pg.Client({ connectionString: ADMIN });
  await admin.connect();
  await admin.query(
    `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()`,
    [name],
  );
  await admin.query(`DROP DATABASE IF EXISTS ${name}`);
  await admin.query(`CREATE DATABASE ${name}`);
  await admin.end();
}

function loadFixture(): Record<string, unknown> {
  return JSON.parse(readFileSync("data/fixtures/synthetic/dataset.json", "utf8")) as Record<string, unknown>;
}

async function idsOf(pool: pg.Pool) {
  const result = await pool.query<{ slug: string; id: string }>(
    `SELECT slug, id::text FROM statements ORDER BY slug`,
  );
  return result.rows;
}

async function walkStatements(pool: pg.Pool, person: string) {
  const full = await listStatements({ person, limit: 50, sort: "event_time_desc" }, pool);
  const walked: string[] = [];
  let cursor: string | null = null;
  for (let page = 0; page < 30; page += 1) {
    const batch = await listStatements(
      { person, limit: 1, sort: "event_time_desc", cursor: cursor ?? undefined },
      pool,
    );
    walked.push(...batch.data.map((row) => row.slug));
    cursor = batch.page.next_cursor;
    if (!cursor) break;
  }
  return { full: full.data.map((row) => row.slug), walked };
}

function distributionOf(trend: Awaited<ReturnType<typeof getTrend>>) {
  if (!trend || !("distribution" in trend)) return null;
  return trend.distribution;
}

async function surfaces(pool: pg.Pool, slug: string, token: string) {
  const site = await listStatements({ q: token, limit: 20 }, pool);
  const research = await listPublicStatements({ q: token, limit: 20, sort: "event_time_desc" }, pool);
  const feed = await listFeedEntries(pool, 100);
  const search = await searchPublic({ q: token, limit: 20 }, pool);
  const searchSlugs = search.groups.statement.data.map((hit) => hit.slug);
  const included = distributionOf(await getTrend("extinction-by-2070-distribution", pool))?.included.map((row) => row.statement_slug) ?? [];
  return {
    site: site.data.some((row) => row.slug === slug),
    research: research.data.some((row) => row.slug === slug),
    feed: feed.some((row) => row.slug === slug),
    search: searchSlugs.includes(slug),
    trend: included.includes(slug),
    site_state: site.data.find((row) => row.slug === slug)?.review_state ?? null,
  };
}

async function main() {
  await recreate("pdoom_coord_integration_test");
  const pool = createPool(INTEGRATION, { applicationName: "pdoom-coord-integration" });
  await migrate(pool);
  const fixture = loadFixture();
  const first = await importCanonical(pool, fixture);
  const before = await idsOf(pool);
  const second = await importCanonical(pool, fixture);
  const after = await idsOf(pool);
  const publicPage = await listPublicStatements({ limit: 100, sort: "event_time_desc" }, pool);
  const publicSlugs = publicPage.data.map((row) => row.slug);
  record(
    "1-collect-twice",
    first.counts.statements === second.counts.statements &&
      before.length === after.length &&
      before.every((row, index) => row.slug === after[index]?.slug && row.id === after[index]?.id) &&
      new Set(publicSlugs).size === publicSlugs.length,
    "A second import of the same document keeps statement ids and does not duplicate public slugs.",
    {
      statements: [first.counts.statements, second.counts.statements],
      ids_stable: before.every((row, index) => row.id === after[index]?.id),
      public_slugs: publicSlugs.length,
      public_unique: new Set(publicSlugs).size,
    },
    "agent-3",
  );

  const detailSlug = publicPage.data.find((row) => row.statement_type === "explicit_numeric")?.slug;
  const detail = detailSlug ? await getPublicStatement(detailSlug, pool) : null;
  const forecast = detail?.forecast ?? null;
  record(
    "4-fields-through-public-read",
    Boolean(
      detail &&
        detail.person.slug &&
        detail.source.slug &&
        detail.source_item.canonical_url.startsWith("http") &&
        /^[a-f0-9]{64}$/.test(detail.source_item.content_hash) &&
        detail.evidence.segment_hash &&
        detail.evidence.slug &&
        detail.event_time &&
        forecast &&
        forecast.question_key &&
        forecast.unit &&
        (forecast.value_numeric !== null || forecast.value_min !== null || forecast.value_max !== null),
    ),
    "A public explicit numeric statement carries person, source URL, evidence hash, event time, and forecast question, unit, and value.",
    detail
      ? {
          slug: detail.slug,
          person: detail.person.slug,
          canonical_url: detail.source_item.canonical_url,
          content_hash: detail.source_item.content_hash,
          evidence: {
            slug: detail.evidence.slug,
            start_char: detail.evidence.start_char,
            end_char: detail.evidence.end_char,
            start_ms: detail.evidence.start_ms,
            segment_hash: detail.evidence.segment_hash,
          },
          event_time: detail.event_time,
          forecast,
        }
      : null,
    "agent-5",
  );

  const extinction = await getTrend("extinction-by-2070-distribution", pool);
  const conditional = await getTrend("conditional-extinction-given-agi", pool);
  const extinctionBody = distributionOf(extinction);
  const conditionalBody = distributionOf(conditional);
  const extinctionSlugs = extinctionBody?.included.map((row) => row.statement_slug) ?? [];
  const conditionalSlugs = conditionalBody?.included.map((row) => row.statement_slug) ?? [];
  record(
    "5-incompatible-questions-stay-separate",
    Boolean(
      extinction &&
        conditional &&
        extinction.question_key !== conditional.question_key &&
        extinctionSlugs.length > 0 &&
        extinctionSlugs.every((slug) => !conditionalSlugs.includes(slug)),
    ),
    "The unconditional extinction distribution and the conditional extinction distribution do not share included statements.",
    {
      extinction_key: extinction && "question_key" in extinction ? extinction.question_key : null,
      conditional_key: conditional && "question_key" in conditional ? conditional.question_key : null,
      extinction_slugs: extinctionSlugs,
      conditional_slugs: conditionalSlugs,
    },
    "agent-2",
  );

  const person = detail?.person.slug;
  if (person) {
    const walked = await walkStatements(pool, person);
    record(
      "10-person-history-pagination",
      walked.full.length > 1 &&
        walked.walked.length === walked.full.length &&
        new Set(walked.walked).size === walked.walked.length &&
        walked.walked.every((slug) => walked.full.includes(slug)),
      "Paging a person's statements with limit 1 returns each slug once and no other person's slug.",
      walked,
      "agent-1",
    );
  } else {
    record("10-person-history-pagination", false, "A public person with statements exists.", null, "agent-1");
  }

  const stampBefore = await getDatasetStamp(pool);
  const bodyBefore = await listPublicStatements({ limit: 100, sort: "event_time_desc" }, pool);
  const approved = await applyReviewDecision(pool, {
    statement_slug: detailSlug ?? "",
    decision: "needs_changes",
    reviewer: "coordination-gate",
    reviewed_at: "2026-10-04T20:41:00.000Z",
    note: "coordination cache probe",
    rejection_reason: null,
    confirmations: emptyConfirmations(false),
    corrections: {},
    relationship: null,
    source_content_hash: null,
    evidence_hash: null,
    content_version: null,
  }).catch(async () => {
    return applyReviewDecision(pool, {
      statement_slug: detailSlug ?? "",
      decision: "approve",
      reviewer: "coordination-gate",
      reviewed_at: "2026-10-04T20:41:00.000Z",
      note: null,
      rejection_reason: null,
      confirmations: emptyConfirmations(true),
      corrections: { normalized_text: `${detail?.normalized_text ?? ""} Coordination review wording.` },
      relationship: null,
      source_content_hash: null,
      evidence_hash: null,
      content_version: null,
    });
  });
  const stampAfter = await getDatasetStamp(pool);
  const bodyAfter = await listPublicStatements({ limit: 100, sort: "event_time_desc" }, pool);
  const etagBefore = createHash("sha256").update(JSON.stringify(bodyBefore)).digest("hex");
  const etagAfter = createHash("sha256").update(JSON.stringify(bodyAfter)).digest("hex");
  const cached = publicJson(
    new Request("http://127.0.0.1/api/v1/statements", {
      headers: { "if-modified-since": stampBefore.imported_at ? new Date(stampBefore.imported_at).toUTCString() : "" },
    }),
    bodyAfter,
    stampAfter.imported_at,
  );
  const reviewOnlyChangedPayload = etagBefore !== etagAfter;
  const stampMoved = stampBefore.imported_at !== stampAfter.imported_at;
  record(
    "7-cache-after-review",
    reviewOnlyChangedPayload && (stampMoved || cached.status !== 304),
    "A review-only wording change changes the public payload, and a client echoing the previous Last-Modified does not receive 304 for the new payload.",
    {
      decision_key: approved.decision_key,
      etag_changed: reviewOnlyChangedPayload,
      imported_at_before: stampBefore.imported_at,
      imported_at_after: stampAfter.imported_at,
      conditional_status: cached.status,
    },
    "agent-6",
  );

  const target = await pool.query<{
    slug: string;
    review_state: string;
    content_hash: string;
    content_version: number;
    logical_key: string;
    source_slug: string;
  }>(
    `SELECT s.slug, s.review_state, si.content_hash, si.content_version, si.logical_key, src.slug AS source_slug
     FROM statements s
     JOIN source_items si ON si.id = s.source_item_id
     JOIN sources src ON src.id = si.source_id
     WHERE s.slug = 'jonah-extinction-review-2024'`,
  );
  const candidate = target.rows[0];
  if (!candidate) {
    record("3-review-survives-reimport", false, "A needs_review explicit numeric statement exists to approve.", null, "agent-5");
    record("2-source-version-history", false, "A source item exists to version.", null, "agent-3");
    record("2-stale-approval-hidden", false, "A source item exists to version.", null, "agent-5");
  } else {
    const decision = await applyReviewDecision(pool, {
      statement_slug: candidate.slug,
      decision: "approve",
      reviewer: "coordination-gate",
      reviewed_at: "2026-10-04T20:42:00.000Z",
      note: null,
      rejection_reason: null,
      confirmations: emptyConfirmations(true),
      corrections: {},
      relationship: null,
      source_content_hash: candidate.content_hash,
      evidence_hash: null,
      content_version: candidate.content_version,
    });
    const manifest = await exportReviewManifest(pool);
    await importCanonical(pool, fixture);
    const afterReimport = await pool.query<{ review_state: string }>(
      `SELECT review_state FROM statements WHERE slug = $1`,
      [candidate.slug],
    );
    const visible = await getPublicStatement(candidate.slug, pool);
    const replay = await importReviewManifest(pool, manifest);
    const afterReplay = await getPublicStatement(candidate.slug, pool);
    record(
      "3-review-survives-reimport",
      afterReimport.rows[0]?.review_state === "human_verified" && visible !== null,
      "Reimporting the unchanged extraction keeps the approved statement human_verified and publicly readable without a second review import.",
      {
        slug: candidate.slug,
        fixture_review_state: "needs_review",
        decision_key: decision.decision_key,
        review_state_after_reimport: afterReimport.rows[0]?.review_state ?? null,
        public_after_reimport: visible !== null,
        replay_applied: replay.applied,
        replay_idempotent: replay.idempotent,
        public_after_replay: afterReplay !== null,
      },
      "agent-3",
    );

    const changed = structuredClone(fixture) as {
      source_items: Array<{ slug: string; content_hash: string; content_hash_input?: string | null; content_version: number; logical_key: string }>;
      statements: Array<{ slug: string; review_state: string }>;
      forecasts: Array<{ statement_slug: string; review_state: string }>;
    };
    const item = changed.source_items.find((row) => row.logical_key === candidate.logical_key);
    const nextHash = "c".repeat(64);
    if (item) {
      item.content_hash = nextHash;
      item.content_hash_input = null;
      item.content_version = candidate.content_version + 1;
    }
    const changedStatement = changed.statements.find((row) => row.slug === candidate.slug);
    if (changedStatement) changedStatement.review_state = "human_verified";
    for (const forecast of changed.forecasts) {
      if (forecast.statement_slug === candidate.slug) forecast.review_state = "human_verified";
    }
    await importCanonical(pool, changed);
    const versions = await pool.query<{ content_hash: string; content_version: number; is_current: boolean }>(
      `SELECT si.content_hash, si.content_version, si.is_current
       FROM source_items si
       JOIN sources src ON src.id = si.source_id
       WHERE src.slug = $1 AND si.logical_key = $2
       ORDER BY si.content_version`,
      [candidate.source_slug, candidate.logical_key],
    );
    const effective = await getStatement(candidate.slug, pool);
    const research = await getPublicStatement(candidate.slug, pool);
    const raw = await pool.query<{ review_state: string }>(`SELECT review_state FROM statements WHERE slug = $1`, [candidate.slug]);
    const hashes = versions.rows.map((row) => row.content_hash);
    const versionActual = {
      previous_hash: candidate.content_hash,
      versions: versions.rows,
      stored_review_state: raw.rows[0]?.review_state ?? null,
      effective_review_state: effective?.review_state ?? null,
      research_visible: research !== null,
    };
    record(
      "2-source-version-history",
      hashes.includes(candidate.content_hash) && hashes.includes(nextHash) && versions.rows.length >= 2,
      "A changed source hash keeps the previous version row and adds the new hash.",
      versionActual,
      "agent-3",
    );
    record(
      "2-stale-approval-hidden",
      raw.rows[0]?.review_state === "human_verified" && effective?.review_state === "needs_review" && research === null,
      "A reimport that marks the new hash human_verified is still hidden, because the stored approval names the previous hash.",
      versionActual,
      "agent-5",
    );
  }

  const method = PREPARED_TRENDS.find((trend) => trend.slug === "extinction-by-2070-distribution");
  if (!method) throw new Error("missing extinction method");
  const withdrawn: TrendCandidate = {
    statement_slug: "coord-withdrawn-estimate",
    person_slug: "coord-person",
    display_name: "Coordination Person",
    statement_type: "explicit_numeric",
    review_state: "human_verified",
    forecast_review_state: "human_verified",
    topic_slugs: ["ai-extinction"],
    question_key: "ai_extinction_unconditional_by_2070",
    question_text: method.question_text,
    definition_text: method.definition_text,
    condition_text: null,
    forecast_kind: "probability",
    value_type: "point",
    value_numeric: 0.2,
    value_min: null,
    value_max: null,
    unit: "probability",
    horizon_text: "by the end of 2070",
    event_time: "2024-01-01T00:00:00.000Z",
  };
  const withdrawal: TrendCandidate = {
    ...withdrawn,
    statement_slug: "coord-withdrawal",
    statement_type: "explicit_qualitative",
    question_key: null,
    value_type: null,
    value_numeric: null,
    unit: null,
    horizon_text: null,
    event_time: "2025-06-01T00:00:00.000Z",
  };
  const distribution = computeProbabilityDistribution({
    method_version: method.method_version,
    question_text: method.question_text,
    definition_text: method.definition_text,
    cohort_slug: "coordination-baseline",
    cohort_version: "0",
    cohort_definition: "Gate fixture. Not a real cohort.",
    cohort_size: 1,
    scope: method.scope,
    candidates: [withdrawn, withdrawal],
    edges: [
      {
        from_statement_slug: withdrawn.statement_slug,
        to_statement_slug: withdrawal.statement_slug,
        relationship_type: "retracts",
        review_state: "human_verified",
        method: "manual",
      },
    ],
  });
  record(
    "6-withdrawal-without-replacement",
    !distribution.included.some((row) => row.statement_slug === withdrawn.statement_slug),
    "A human-verified retraction to a qualitative withdrawal with no replacement number drops the old probability from the distribution.",
    {
      included: distribution.included.map((row) => row.statement_slug),
      exclusions: distribution.exclusions.map((row) => ({ slug: row.statement_slug, reason: row.reason })),
    },
    "agent-2",
  );

  const beforePartial = await pool.query<{ count: string }>(`SELECT count(*)::text AS count FROM statements`);
  const broken = structuredClone(fixture) as { dataset_id: string; statements: Array<{ evidence_slug: string }> };
  broken.dataset_id = "coord-broken";
  if (broken.statements[0]) broken.statements[0].evidence_slug = "missing-evidence";
  let brokenThrew = false;
  try {
    await importCanonical(pool, broken);
  } catch {
    brokenThrew = true;
  }
  const afterBroken = await pool.query<{ count: string }>(`SELECT count(*)::text AS count FROM statements`);
  const partial = structuredClone(fixture) as {
    dataset_id: string;
    statements: Array<{ slug: string }>;
    forecasts: Array<{ statement_slug: string }>;
    relationships: Array<{ from_statement_slug: string; to_statement_slug: string }>;
    sources: Array<{ slug: string; last_success_at: string | null }>;
    source_items: Array<{ source_slug: string; collection_status: string; availability: string }>;
    ingestion_runs: Array<{ status: string; error_summary: string | null }>;
  };
  const omitted = partial.statements[0]?.slug ?? "";
  partial.statements = partial.statements.filter((row) => row.slug !== omitted);
  partial.forecasts = partial.forecasts.filter((row) => row.statement_slug !== omitted);
  partial.relationships = partial.relationships.filter(
    (row) => row.from_statement_slug !== omitted && row.to_statement_slug !== omitted,
  );
  partial.dataset_id = "coord-partial";
  const source = partial.sources[0];
  if (source) source.last_success_at = "2000-01-01T00:00:00.000Z";
  for (const item of partial.source_items) {
    if (item.source_slug === source?.slug) {
      item.collection_status = "partial";
      item.availability = "available";
    }
  }
  if (partial.ingestion_runs[0]) {
    partial.ingestion_runs[0].status = "failed";
    partial.ingestion_runs[0].error_summary = "coordination partial failure";
  }
  await importCanonical(pool, partial);
  const omittedRow = omitted
    ? await pool.query(`SELECT slug FROM statements WHERE slug = $1`, [omitted])
    : { rowCount: 0 };
  const freshness = source ? classifyFreshness("2000-01-01T00:00:00.000Z", AS_OF) : null;
  const storedSuccess = source
    ? await pool.query<{ last_success_at: Date | null }>(`SELECT last_success_at FROM sources WHERE slug = $1`, [source.slug])
    : { rows: [] };
  const storedFreshness = storedSuccess.rows[0]
    ? classifyFreshness(storedSuccess.rows[0].last_success_at?.toISOString() ?? null, AS_OF)
    : null;
  record(
    "8-partial-failure-keeps-prior-data",
    brokenThrew &&
      beforePartial.rows[0]?.count === afterBroken.rows[0]?.count &&
      (omittedRow.rowCount ?? 0) === 1 &&
      freshness === "stale" &&
      storedFreshness === "stale",
    "A failed import rolls back. A later partial import keeps omitted statements and reports a year-2000 success as stale.",
    {
      broken_threw: brokenThrew,
      count_before: beforePartial.rows[0]?.count,
      count_after_broken: afterBroken.rows[0]?.count,
      omitted_slug: omitted,
      omitted_still_present: (omittedRow.rowCount ?? 0) === 1,
      freshness,
      stored_freshness: storedFreshness,
    },
    "agent-3",
  );

  const sample = await pool.query<{ slug: string; question_key: string | null }>(
    `SELECT s.slug, f.question_key
     FROM statements s
     JOIN forecasts f ON f.statement_id = s.id
     WHERE s.statement_type = 'explicit_numeric'
       AND f.question_key = 'ai_extinction_unconditional_by_2070'
     ORDER BY s.slug
     LIMIT 5`,
  );
  const [verified, machine, needs, unreviewed, rejected] = sample.rows;
  if (sample.rows.length < 5 || !verified || !machine || !needs || !unreviewed || !rejected) {
    record("9-eligibility", false, "Five unconditional extinction forecasts exist to assign review states.", sample.rows, "agent-5");
  } else {
    const tokens = {
      human_verified: "coordtoken verifiedalpha",
      machine_validated: "coordtoken machinealpha",
      needs_review: "coordtoken needsalpha",
      unreviewed: "coordtoken unreviewedalpha",
      rejected: "coordtoken rejectedalpha",
    };
    async function assign(slug: string, state: string, token: string, forecastState: string | null) {
      await pool.query(`UPDATE statements SET review_state = $2, normalized_text = $3 WHERE slug = $1`, [slug, state, token]);
      if (forecastState) {
        await pool.query(
          `UPDATE forecasts SET review_state = $2 WHERE statement_id = (SELECT id FROM statements WHERE slug = $1)`,
          [slug, forecastState],
        );
      }
    }
    await pool.query(
      `DELETE FROM review_decisions WHERE statement_id IN (SELECT id FROM statements WHERE slug = ANY($1::text[]))`,
      [[verified.slug, machine.slug, needs.slug, unreviewed.slug, rejected.slug]],
    );
    await assign(verified.slug, "human_verified", tokens.human_verified, "human_verified");
    await assign(machine.slug, "machine_validated", tokens.machine_validated, "machine_validated");
    await assign(needs.slug, "needs_review", tokens.needs_review, "needs_review");
    await assign(unreviewed.slug, "unreviewed", tokens.unreviewed, "unreviewed");
    await assign(rejected.slug, "rejected", tokens.rejected, "rejected");
    const seen = {
      human_verified: await surfaces(pool, verified.slug, tokens.human_verified),
      machine_validated: await surfaces(pool, machine.slug, tokens.machine_validated),
      needs_review: await surfaces(pool, needs.slug, tokens.needs_review),
      unreviewed: await surfaces(pool, unreviewed.slug, tokens.unreviewed),
      rejected: await surfaces(pool, rejected.slug, tokens.rejected),
    };
    const trendNow = distributionOf(await getTrend("extinction-by-2070-distribution", pool));
    const verifiedExclusion = trendNow?.exclusions.find((row) => row.statement_slug === verified.slug)?.reason ?? null;
    const verifiedInTrend = seen.human_verified.trend || verifiedExclusion === "not_latest" || verifiedExclusion === "superseded";
    const ok =
      verifiedInTrend &&
      seen.human_verified.site &&
      seen.human_verified.research &&
      seen.human_verified.feed &&
      seen.human_verified.search &&
      !seen.unreviewed.site &&
      !seen.unreviewed.research &&
      !seen.unreviewed.feed &&
      !seen.unreviewed.search &&
      !seen.unreviewed.trend &&
      !seen.rejected.site &&
      !seen.rejected.research &&
      !seen.rejected.feed &&
      !seen.rejected.search &&
      !seen.rejected.trend &&
      seen.needs_review.site &&
      !seen.needs_review.research &&
      !seen.needs_review.feed &&
      seen.needs_review.search &&
      !seen.needs_review.trend &&
      seen.machine_validated.site &&
      seen.machine_validated.research &&
      seen.machine_validated.feed &&
      !seen.machine_validated.trend;
    record(
      "9-eligibility",
      ok,
      "Site pages and search show needs_review. Research, feed, and numeric trends do not. Unreviewed and rejected stay off every public surface. machine_validated is public and indexed, and is not a numeric-trend point.",
      { verified_trend_reason: verifiedExclusion, seen },
      "agent-1",
    );
  }

  await pool.end();

  try {
  await recreate("pdoom_coord_cohort_test");
  const cohort = createPool(COHORT, { applicationName: "pdoom-coord-cohort", statementTimeoutMs: 30_000 });
  await migrate(cohort);
  const live = validateDocument(JSON.parse(readFileSync("data/collections/cohort-v2026-09/canonical-live.json", "utf8")));
  const imported = await importCanonical(cohort, live);
  const started = performance.now();
  const people = await cohort.query<{ slug: string }>(`SELECT slug FROM people ORDER BY slug LIMIT 1`);
  const list = await listPublicStatements({ limit: 50, sort: "event_time_desc" }, cohort);
  const one = people.rows[0] ? await listStatements({ person: people.rows[0].slug, limit: 20 }, cohort) : null;
  const trend = await getTrend("extinction-by-2070-distribution", cohort);
  const search = await searchPublic({ q: "extinction", limit: 10 }, cohort);
  const elapsed = Math.round(performance.now() - started);
  record(
    "11-populated-cohort-performance",
    imported.counts.people > 100 && list.page.total >= 0 && elapsed < 30_000 && search.groups.statement.page.total >= 0,
    "Import the published live cohort and answer statement, person, trend, and search reads.",
    {
      people: imported.counts.people,
      statements: imported.counts.statements,
      public_statements: list.page.total,
      person: people.rows[0]?.slug ?? null,
      person_statements: one?.page.total ?? null,
      trend_slug: trend?.slug ?? null,
      search_statements: search.groups.statement.page.total,
      elapsed_ms: elapsed,
    },
    "agent-6",
  );
  await cohort.end();
  } catch (error) {
    record("11-populated-cohort-performance", false, "Import the published live cohort and answer statement, person, trend, and search reads.", error instanceof Error ? error.message : String(error), "agent-6");
  }

  const failed = scenarios.filter((scenario) => !scenario.pass);
  const report = {
    base_sha: "d13c8ab9bc2d643e28b7f52daf1a4c15724e77d7",
    database: "pdoom_coord_integration_test",
    cohort_database: "pdoom_coord_cohort_test",
    stale_marker: stableId("coordination-gate"),
    scenarios,
    failed: failed.map((scenario) => scenario.id),
  };
  console.log(JSON.stringify(report, null, 2));
  if (failed.length > 0) process.exitCode = 1;
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.stack : error);
  process.exitCode = 1;
});
