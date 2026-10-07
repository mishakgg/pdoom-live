import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { REVIEW_STATES, type ReviewState } from "@pdoom/contracts";
import { assertTestDatabase, readDatabaseUrl } from "../packages/db/src/env";
import { clearProductTables, importCanonical, resetDatabase, validateDocument } from "../packages/db/src/import";
import { createPool, closePool } from "../packages/db/src/pool";
import { getCoverage, getOverview, getPerson, getSource, getSourceItem, getStatement, getTopic, listPeople, listSources, listStatements, listTopics, listComputedTrends, loadTrendInputs } from "../packages/db/src/queries";
import { getSourceItemDiscovery, getStatementDiscovery, listFeedEntries, listSitemapRecords } from "../packages/db/src/discovery";
import { loadPublicExport } from "../packages/db/src/public-read";
import { searchPublic } from "../packages/db/src/search";
import { applyReviewDecision, emptyConfirmations, stageCandidates } from "../packages/db/src/review";
import { SourceRecord } from "../apps/web/app/sources/[slug]/page";
import { SourceItemRecord } from "../apps/web/app/source-items/[slug]/page";
import { PersonProfile } from "../apps/web/components/person-profile";
import { TrendView } from "../apps/web/components/trend-view";
import { GET as sourcesApi } from "../apps/web/app/api/sources/route";
import { GET as sourceApi } from "../apps/web/app/api/sources/[slug]/route";
import { GET as itemApi } from "../apps/web/app/api/source-items/[slug]/route";
import { GET as statementApi } from "../apps/web/app/api/statements/[slug]/route";
import { GET as trendApi } from "../apps/web/app/api/trends/[slug]/route";
import { handlePublicApi } from "../apps/web/lib/public-api-handler";
import { resetPublicRepresentationCache } from "../apps/web/lib/representation-cache";
import { publicApiLimiter } from "../apps/web/lib/rate-limit";

const pool = createPool(readDatabaseUrl());
const fixture = JSON.parse(readFileSync("data/fixtures/public-visibility/dataset.json", "utf8"));
const publicStates: ReviewState[] = ["needs_review", "machine_validated", "human_verified"];
const suffix = (state: string) => state.replaceAll("_", "-");
const asOf = "2026-10-01T00:00:00.000Z";

async function publicGet(path: string) {
  return handlePublicApi(new Request(`http://localhost/api/v1/${path}`));
}

function assertHiddenForecastValuesRedacted(value: unknown, hiddenSlugs: Set<string>): void {
  if (Array.isArray(value)) {
    for (const child of value) assertHiddenForecastValuesRedacted(child, hiddenSlugs);
  } else if (value && typeof value === "object") {
    const row = value as Record<string, unknown>;
    if (typeof row.statement_slug === "string" && hiddenSlugs.has(row.statement_slug)) {
      for (const key of ["preserved_value", "value_numeric", "value_min", "value_max", "distribution", "definition_text", "condition_text", "horizon_text", "resolution_criteria", "target_date_start", "target_date_end"]) {
        if (key in row) expect(row[key]).toBeNull();
      }
    }
    for (const child of Object.values(row)) assertHiddenForecastValuesRedacted(child, hiddenSlugs);
  }
}

beforeAll(async () => {
  assertTestDatabase(readDatabaseUrl());
  await clearProductTables(pool);
  await importCanonical(pool, fixture);
});

beforeEach(() => {
  resetPublicRepresentationCache();
  publicApiLimiter.reset();
});

afterAll(async () => {
  await resetDatabase(pool);
  await closePool();
  await pool.end();
});

describe("website publication boundary", () => {
  it("fails closed on cross-item evidence even when the declared source or foreign item is public", async () => {
    const mismatches = ["rejected-source", "unreviewed-source", "public-item"].map((state) => `visibility-cross-${state}`);
    // Canonical import currently permits independent item and evidence references.
    expect(validateDocument(fixture).statements.filter((row) => mismatches.includes(row.slug))).toHaveLength(3);
    const listed = await listStatements({ sort: "event_time_desc", limit: 50 }, pool);
    const bundle = await loadPublicExport(asOf, pool);
    const inputs = await loadTrendInputs(pool);
    const paths = (await listSitemapRecords(pool, { offset: 0, limit: 500 })).map((row) => row.path);
    const feed = await listFeedEntries(pool, 100);
    for (const slug of mismatches) {
      expect(await getStatement(slug, pool)).toBeNull();
      expect(await getStatementDiscovery(slug, pool)).toBeNull();
      expect(await getSourceItem(`${slug}-item`, pool)).toBeNull();
      expect(await getSourceItemDiscovery(`${slug}-item`, pool)).toBeNull();
      expect(listed.data.some((row) => row.slug === slug)).toBe(false);
      expect(bundle.statements.some((row) => row.slug === slug)).toBe(false);
      expect(bundle.source_items.some((row) => row.slug === `${slug}-item`)).toBe(false);
      expect(inputs?.candidates.some((row) => row.statement_slug === slug)).toBe(false);
      expect(paths).not.toContain(`/statements/${slug}`);
      expect(paths).not.toContain(`/source-items/${slug}-item`);
      expect(feed.some((row) => row.slug === slug)).toBe(false);
      expect((await publicGet(`statements/${slug}`)).status).toBe(404);
      const response = await statementApi(new Request(`http://localhost/api/statements/${slug}`), { params: Promise.resolve({ slug }) });
      expect(response.status).toBe(404);
    }
    expect(listed.page.total).toBe(11);
    expect(bundle.catalog.counts.statements).toBe(9);
    const statementHits = await searchPublic({ q: "visibility cross", type: "statement", limit: 20, mode: "page" }, pool);
    const itemHits = await searchPublic({ q: "visibility cross", type: "source_item", limit: 20, mode: "page" }, pool);
    expect(statementHits.groups.statement.data).toEqual([]);
    expect(itemHits.groups.source_item.data).toEqual([]);
    const source = await getSource("visibility-source-human-verified", pool);
    expect(source?.items.some((row) => row.slug.startsWith("visibility-cross-"))).toBe(false);
    expect(renderToStaticMarkup(<SourceRecord source={source!} />)).not.toContain("visibility-cross-");
    expect(await getSourceItem("visibility-old-removed-item", pool)).not.toBeNull();
  });

  it("hides staged/rejected sources and item evidence, including exact routes and metadata", async () => {
    const sources = await listSources(pool);
    expect(sources.map((row) => row.review_state).sort()).toEqual([...publicStates].sort());
    for (const state of ["unreviewed", "rejected"]) {
      expect(await getSource(`visibility-source-${state}`, pool)).toBeNull();
      expect(await getSourceItem(`visibility-${state}-item`, pool)).toBeNull();
      expect(await getSourceItemDiscovery(`visibility-${state}-item`, pool)).toBeNull();
      const source = await sourceApi(new Request("http://localhost/api/sources/hidden"), { params: Promise.resolve({ slug: `visibility-source-${state}` }) });
      const item = await itemApi(new Request("http://localhost/api/source-items/hidden"), { params: Promise.resolve({ slug: `visibility-${state}-item` }) });
      expect(source.status).toBe(404);
      expect(item.status).toBe(404);
    }
    const response = await sourcesApi(new Request("http://localhost/api/sources"), {});
    expect((await response.json()).data.map((row: { slug: string }) => row.slug)).toEqual(sources.map((row) => row.slug));
    const source = await getSource("visibility-source-human-verified", pool);
    expect(source?.items).toHaveLength(source!.item_count);
    expect(source?.items.map((row) => row.slug)).not.toContain("visibility-unreviewed-item");
    const mixed = await getSourceItem("visibility-mixed-item", pool);
    expect(mixed?.metadata).toEqual({});
    expect(mixed?.evidence.map((row) => row.slug)).toEqual(["visibility-mixed-public-evidence"]);
    expect(mixed?.participants.map((row) => row.person_slug)).toEqual(["visibility-person"]);
    for (const item of source!.items) expect(await getSourceItem(item.slug, pool)).not.toBeNull();
    const markup = renderToStaticMarkup(<SourceItemRecord item={mixed!} />);
    expect(markup).toContain("visibility-mixed-public evidence");
    expect(markup).not.toContain("visibility-mixed-hidden");
    expect(markup).not.toContain("Private Attribution Marker");
    expect(markup).not.toContain("private_staging_marker");
  });

  it("keeps a minimal unreviewed-container audit page and historical removed evidence", async () => {
    expect((await listSources(pool)).some((row) => row.slug === "visibility-audit")).toBe(false);
    const audit = await getSource("visibility-audit", pool);
    expect(audit?.audit_only).toBe(true);
    expect(audit?.review_state).toBe("unreviewed");
    expect(audit?.items.map((row) => row.slug)).toEqual(["visibility-audit-public-item"]);
    expect(audit?.item_count).toBe(1);
    expect(audit?.owner_slug).toBeNull();
    expect(audit?.rights_notes).toBeNull();
    expect(audit?.collection_adapter).toBeNull();
    const markup = renderToStaticMarkup(<SourceRecord source={audit!} />);
    expect(markup).toContain("Only items supporting public statements");
    expect(markup).not.toContain("private-adapter-marker");
    expect(markup).not.toContain("private-rights-marker");
    expect(markup).not.toContain("visibility-audit-private");
    expect(await getSourceItem("visibility-audit-public-item", pool)).not.toBeNull();
    expect(await getSourceItem("visibility-audit-private-item", pool)).toBeNull();
    expect((await getSourceItem("visibility-old-removed-item", pool))?.availability).toBe("removed");
    expect((await getSourceItemDiscovery("visibility-old-removed-item", pool))?.indexable).toBe(false);
    expect((await getSourceItemDiscovery("visibility-old-removed-item", pool))?.current_slug).toBeNull();
    expect((await getStatementDiscovery("visibility-audit-public", pool))?.indexable).toBe(false);
    expect(await getStatement("visibility-rejected-container", pool)).toBeNull();
    expect(await getStatementDiscovery("visibility-rejected-container", pool)).toBeNull();
    expect(await getSourceItem("visibility-rejected-container-item", pool)).toBeNull();
  });

  it("filters identity/affiliation details, current affiliations, organization filters, and SSR", async () => {
    const person = await getPerson("visibility-person", pool);
    expect(person?.identities.map((row) => row.review_state).sort()).toEqual([...publicStates].sort());
    expect(person?.affiliations.map((row) => row.review_state).sort()).toEqual([...publicStates].sort());
    expect(person?.sources.map((row) => row.review_state).sort()).toEqual([...publicStates].sort());
    const people = await listPeople({ limit: 50 }, pool);
    expect(people.data.find((row) => row.slug === "visibility-person")?.organization).toBeNull();
    for (const state of REVIEW_STATES) {
      const organization = `visibility-org-${suffix(state)}`;
      const matches = await listPeople({ organization, limit: 50 }, pool);
      const statements = await listStatements({ sort: "event_time_desc", organization, limit: 50 }, pool);
      expect(matches.page.total).toBe(publicStates.includes(state) ? 1 : 0);
      expect(statements.page.total).toBe(publicStates.includes(state) ? person!.statement_total : 0);
      expect(matches.page.total).toBe(matches.data.length);
      expect(statements.page.total).toBe(statements.data.length);
    }
    const markup = renderToStaticMarkup(<PersonProfile person={person!} />);
    expect(markup).not.toContain("Role Marker unreviewed");
    expect(markup).not.toContain("Role Marker rejected");
    expect(markup).not.toContain("/identity/unreviewed");
    expect(markup).not.toContain("/identity/rejected");
    const hits = await searchPublic({ q: "Visibility Person", type: "person", limit: 20, mode: "page" }, pool);
    expect(hits.groups.person.data.find((row) => row.slug === "visibility-person")?.organization).toBeNull();
  });

  it("filters forecasts independently, relationship states and both endpoints on application reads", async () => {
    const listed = await listStatements({ sort: "event_time_desc", person: "visibility-person", limit: 50 }, pool);
    for (const state of REVIEW_STATES) {
      const slug = `visibility-forecast-${suffix(state)}`;
      const detail = await getStatement(slug, pool);
      const summary = listed.data.find((row) => row.slug === slug);
      expect(Boolean(detail?.forecast)).toBe(publicStates.includes(state));
      expect(Boolean(summary?.forecast)).toBe(publicStates.includes(state));
      const response = await statementApi(new Request(`http://localhost/api/statements/${slug}`), { params: Promise.resolve({ slug }) });
      expect(response.status).toBe(200);
      expect(Boolean((await response.json()).forecast)).toBe(publicStates.includes(state));
    }
    const relationships = (await getStatement("visibility-machine-validated", pool))!.relationships;
    expect(relationships.map((row) => row.review_state).sort()).toEqual([...publicStates].sort());
    for (const relation of relationships) {
      expect(await getStatement(relation.from_slug, pool)).not.toBeNull();
      expect(await getStatement(relation.to_slug, pool)).not.toBeNull();
    }
    const overview = await getOverview(pool);
    const topic = await getTopic("ai-extinction", pool);
    const person = await getPerson("visibility-person", pool);
    expect(listed.page.total).toBe(11);
    expect(overview.dataset.statement_count).toBe(listed.page.total);
    expect(person!.statement_total).toBe(listed.page.total);
    expect(topic!.statement_total).toBe(listed.page.total);
    expect((await listTopics(pool)).find((row) => row.slug === "ai-extinction")!.statement_total).toBe(listed.page.total);
    expect(overview.dataset.source_item_count).toBe(11);
    expect((await getCoverage(asOf, pool)).source_count).toBe((await listSources(pool)).length);
    expect(overview.revisions).toHaveLength(3);
    for (const statement of listed.data) {
      expect(await getSource(statement.source.slug, pool)).not.toBeNull();
      expect(await getSourceItem(statement.source_item.slug, pool)).not.toBeNull();
    }
  });

  it("keeps export/API/indexing stricter and internally linked, including explicit rejected sources", async () => {
    const bundle = await loadPublicExport(asOf, pool);
    const sourceSlugs = new Set(bundle.sources.map((row) => row.slug));
    const itemSlugs = new Set(bundle.source_items.map((row) => row.slug));
    const statementSlugs = new Set(bundle.statements.map((row) => row.slug));
    expect(bundle.statements).toHaveLength(9);
    expect(bundle.catalog.counts.statements).toBe(bundle.statements.length);
    expect(bundle.catalog.counts.forecasts).toBe(bundle.forecasts.length);
    expect(bundle.catalog.counts.source_items).toBe(bundle.source_items.length);
    expect(bundle.catalog.counts.relationships).toBe(bundle.relationships.length);
    expect(bundle.source_items.find((row) => row.slug === "visibility-mixed-item")?.participants.map((row) => row.person_slug)).toEqual(["visibility-person"]);
    for (const statement of bundle.statements) {
      expect(sourceSlugs.has(statement.source.slug)).toBe(true);
      expect(itemSlugs.has(statement.source_item.slug)).toBe(true);
      expect(["human_verified", "machine_validated"]).toContain(statement.review_state);
    }
    for (const relation of bundle.relationships) {
      expect(statementSlugs.has(relation.from_statement_slug)).toBe(true);
      expect(statementSlugs.has(relation.to_statement_slug)).toBe(true);
    }
    const response = await publicGet("statements?limit=50");
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.page.total).toBe(9);
    expect(body.data).toHaveLength(body.page.total);
    expect((await publicGet("statements/visibility-needs-review")).status).toBe(404);
    expect((await publicGet("statements/visibility-audit-public")).status).toBe(404);
    expect((await publicGet("statements/visibility-rejected-container")).status).toBe(404);
    const paths = (await listSitemapRecords(pool, { offset: 0, limit: 500 })).map((row) => row.path);
    expect(paths).not.toContain("/statements/visibility-needs-review");
    expect(paths).not.toContain("/statements/visibility-rejected-container");
    expect(paths).not.toContain("/sources/visibility-audit");
    expect(paths).not.toContain("/statements/visibility-audit-public");
    expect((await listFeedEntries(pool, 100)).some((row) => row.slug === "visibility-rejected-container")).toBe(false);
    expect((await loadTrendInputs(pool))?.candidates.some((row) => row.statement_slug === "visibility-rejected-container")).toBe(false);
    expect(JSON.stringify(bundle.trends)).not.toContain("visibility-audit-public");
    expect(JSON.stringify(bundle.trends)).not.toContain("visibility-rejected-container");
    const hits = await searchPublic({ q: "visibility", type: "source_item", limit: 20, mode: "page" }, pool);
    expect(hits.groups.source_item.data.some((row) => row.slug === "visibility-unreviewed-item")).toBe(false);
    expect(hits.groups.source_item.data.some((row) => row.slug === "visibility-rejected-container-item")).toBe(false);
    const forecastHits = await searchPublic({ q: "visibility forecast", type: "statement", limit: 20, mode: "page" }, pool);
    for (const state of ["unreviewed", "rejected"]) {
      expect(forecastHits.groups.statement.data.find((row) => row.slug === `visibility-forecast-${state}`)?.forecast).toBeNull();
    }
  });

  it("keeps hidden statement/forecast values out of trend exclusions, metadata, charts, API and exports", async () => {
    const privateMarkers = [
      "FORECAST_UNREVIEWED_PRIVATE_MARKER", "FORECAST_REJECTED_PRIVATE_MARKER",
      "STATEMENT_UNREVIEWED_PRIVATE_MARKER", "STATEMENT_REJECTED_PRIVATE_MARKER", "STATEMENT_MIXED_PRIVATE_MARKER",
    ];
    const hiddenStatementSlugs = ["visibility-unreviewed", "visibility-rejected", "visibility-mixed-hidden"];
    const inputs = await loadTrendInputs(pool);
    for (const slug of hiddenStatementSlugs) expect(inputs?.candidates.some((row) => row.statement_slug === slug)).toBe(false);
    for (const state of ["unreviewed", "rejected"]) {
      const candidate = inputs!.candidates.find((row) => row.statement_slug === `visibility-forecast-${state}`);
      expect(candidate?.value_numeric).toBeNull();
      expect(candidate?.value_min).toBeNull();
      expect(candidate?.value_max).toBeNull();
      expect(candidate?.distribution).toBeNull();
      expect(candidate?.question_key).toBeNull();
      expect(candidate?.definition_text).toBeNull();
      expect(candidate?.horizon_text).toBeNull();
      expect(candidate?.resolution_criteria).toBeNull();
    }
    expect(inputs!.candidates.find((row) => row.statement_slug === "visibility-forecast-needs-review")?.value_numeric).toBe(0.9539);
    const trends = await listComputedTrends(pool);
    const bundle = await loadPublicExport(asOf, pool);
    const hiddenForecastSlugs = new Set(["visibility-forecast-unreviewed", "visibility-forecast-rejected"]);
    assertHiddenForecastValuesRedacted(trends, hiddenForecastSlugs);
    assertHiddenForecastValuesRedacted(bundle.trends, new Set([...hiddenForecastSlugs, "visibility-forecast-needs-review"]));
    const inspection = trends.find((row) => row.kind === "inspection");
    expect(inspection?.inspection.rows.some((row) => row.statement_slug === "visibility-human-verified")).toBe(true);
    expect(inspection?.inspection.rows.some((row) => hiddenForecastSlugs.has(row.statement_slug))).toBe(false);
    expect(bundle.trends.find((row) => row.kind === "inspection")?.inspection.rows.some((row) => row.statement_slug === "visibility-human-verified")).toBe(true);
    const privateNumbers = ["0.7319", "0.8429", "0.6193", "0.6283", "0.6393", "73.19", "84.29", "61.93", "62.83", "63.93"];
    const websiteBytes = JSON.stringify(trends);
    const researchBytes = JSON.stringify(bundle);
    for (const marker of [...privateMarkers, ...privateNumbers, ...hiddenStatementSlugs]) {
      expect(websiteBytes).not.toContain(marker);
      expect(researchBytes).not.toContain(marker);
    }
    expect(researchBytes).not.toContain("FORECAST_NEEDS_REVIEW_MARKER");
    expect(researchBytes).not.toContain("0.9539");
    expect(researchBytes).not.toContain("95.39");
    expect(researchBytes).not.toContain('"visibility-needs-review"');
    const inspectionMarkup = renderToStaticMarkup(<TrendView trend={inspection!} />);
    expect(inspectionMarkup).toContain("visibility-human-verified");
    for (const marker of [...privateMarkers, ...privateNumbers, ...hiddenStatementSlugs]) expect(inspectionMarkup).not.toContain(marker);
    const distribution = trends.find((row) => row.kind === "distribution")!;
    expect(distribution).toBeTruthy();
    const markup = renderToStaticMarkup(<TrendView trend={distribution} />);
    for (const marker of [...privateMarkers, ...privateNumbers, ...hiddenStatementSlugs]) expect(markup).not.toContain(marker);
    const siteResponse = await trendApi(new Request(`http://localhost/api/trends/${distribution.slug}`), { params: Promise.resolve({ slug: distribution.slug }) });
    expect(siteResponse.status).toBe(200);
    const sitePayload = await siteResponse.json();
    assertHiddenForecastValuesRedacted(sitePayload, hiddenForecastSlugs);
    const siteBody = JSON.stringify(sitePayload);
    for (const marker of [...privateMarkers, ...privateNumbers, ...hiddenStatementSlugs]) expect(siteBody).not.toContain(marker);
    const researchResponse = await publicGet(`trends/${distribution.slug}`);
    expect(researchResponse.status).toBe(200);
    const researchPayload = await researchResponse.json();
    assertHiddenForecastValuesRedacted(researchPayload, new Set([...hiddenForecastSlugs, "visibility-forecast-needs-review"]));
    const researchBody = JSON.stringify(researchPayload);
    for (const marker of [...privateMarkers, ...privateNumbers, "FORECAST_NEEDS_REVIEW_MARKER", "0.9539", "95.39"]) expect(researchBody).not.toContain(marker);
  });

  it("uses only public speaker attribution or reviewed ownership for source-item person filters", async () => {
    const privateMatches = await searchPublic({ q: "visibility", type: "source_item", person: "visibility-private-person", limit: 20, mode: "page" }, pool);
    expect(privateMatches.groups.source_item.data).toEqual([]);
    expect(privateMatches.groups.source_item.page.total).toBe(0);
    const visibleMatches = await searchPublic({ q: "visibility", type: "source_item", person: "visibility-person", limit: 20, mode: "page" }, pool);
    expect(visibleMatches.groups.source_item.data.map((row) => row.slug)).toContain("visibility-mixed-item");
    expect(visibleMatches.groups.source_item.data.map((row) => row.slug)).toContain("visibility-audit-public-item");
  });

  it("publishes only covered evidence after real staging/approval and hides stale material from research/indexing", async () => {
    await stageCandidates(pool, [{
      person_id: "person:visibility-person", source_url: "https://synthetic.pdoom.example/visibility-stage",
      content_hash: "ab".repeat(32), evidence_text: "Extinction is unlikely.", normalized_text: "Extinction is unlikely.",
      extractor_name: "rule-extract", extractor_version: "rule-extract/0.4.0", statement_type: "explicit_qualitative",
      role: "author", ownership: "owned", source_type: "blog", attribution_method: "byline",
    }]);
    const staged = (await pool.query(`SELECT s.slug, si.slug AS item_slug, src.slug AS source_slug FROM statements s
      JOIN source_items si ON si.id = s.source_item_id JOIN sources src ON src.id = si.source_id
      WHERE si.canonical_url = 'https://synthetic.pdoom.example/visibility-stage'`)).rows[0];
    expect(await getSource(staged.source_slug, pool)).toBeNull();
    expect(await getSourceItem(staged.item_slug, pool)).toBeNull();
    await applyReviewDecision(pool, {
      decision_key: null,
      statement_slug: staged.slug, decision: "approve", reviewer: "visibility-fixture", reviewed_at: asOf,
      note: null, rejection_reason: null, confirmations: emptyConfirmations(false), corrections: {}, relationship: null,
      source_content_hash: null, evidence_hash: null, content_version: null,
    });
    expect((await getStatement(staged.slug, pool))?.review_state).toBe("human_verified");
    expect((await getSource(staged.source_slug, pool))?.audit_only).toBe(true);
    expect((await getSourceItem(staged.item_slug, pool))?.evidence).toHaveLength(1);
    expect((await listSources(pool)).some((row) => row.slug === staged.source_slug)).toBe(false);
    await pool.query(`UPDATE evidence_segments SET segment_hash = $1 WHERE source_item_id = (SELECT id FROM source_items WHERE slug = $2)`, ["cd".repeat(32), staged.item_slug]);
    expect((await getStatement(staged.slug, pool))?.review_state).toBe("needs_review");
    expect((await getStatementDiscovery(staged.slug, pool))?.indexable).toBe(false);
    expect((await getSourceItemDiscovery(staged.item_slug, pool))?.indexable).toBe(false);
    expect((await listStatements({ sort: "event_time_desc", review_state: "needs_review", limit: 50 }, pool)).data.some((row) => row.slug === staged.slug)).toBe(true);
    expect((await loadPublicExport(asOf, pool)).statements.some((row) => row.slug === staged.slug)).toBe(false);
  });

  it("uses the existing effective-state helper consistently when a rejection covers a rewritten row", async () => {
    const before = await getOverview(pool);
    const slug = "visibility-machine-validated";
    await applyReviewDecision(pool, {
      decision_key: null,
      statement_slug: slug, decision: "reject", reviewer: "visibility-fixture", reviewed_at: asOf,
      note: null, rejection_reason: "extraction_error", confirmations: emptyConfirmations(false), corrections: {}, relationship: null,
      source_content_hash: null, evidence_hash: null, content_version: null,
    });
    await pool.query(`UPDATE statements SET review_state = 'machine_validated' WHERE slug = $1`, [slug]);
    expect(await getStatement(slug, pool)).toBeNull();
    expect(await getSourceItem(`${slug}-item`, pool)).toBeNull();
    const after = await getOverview(pool);
    expect(after.dataset.statement_count).toBe(before.dataset.statement_count - 1);
    expect(after.dataset.source_item_count).toBe(before.dataset.source_item_count - 1);
    expect(after.revisions).toHaveLength(0);
    const person = await getPerson("visibility-person", pool);
    const listed = await listStatements({ sort: "event_time_desc", person: "visibility-person", limit: 50 }, pool);
    expect(person?.statement_total).toBe(listed.page.total);
    const topicStatements = await listStatements({ sort: "event_time_desc", topic: "ai-extinction", limit: 50 }, pool);
    expect((await getTopic("ai-extinction", pool))?.statement_total).toBe(topicStatements.page.total);
    expect((await loadPublicExport(asOf, pool)).statements.some((row) => row.slug === slug)).toBe(false);
  });
});
