import { createPool } from "../packages/db/src/pool";
import {
  countSitemapRecords,
  getStatementDiscovery,
  listFeedEntries,
  listSitemapRecords,
} from "../packages/db/src/discovery";
import {
  isIndexableReviewState,
  isPublicReviewState,
  PUBLIC_REVIEW_STATES,
  REVIEW_STATES,
} from "@pdoom/contracts";
import { describe, expect, it } from "vitest";
import { renderAtomFeed } from "../apps/web/lib/feed";
import {
  absoluteUrl,
  canonicalOrigin,
  hasDiscoveryFilter,
  listPageFields,
  ogCardLines,
  pageMetadata,
  resolveCanonicalOrigin,
  robotsDocument,
  ROBOTS_DISALLOW,
  sitemapChunkBounds,
  sitemapChunkPlan,
  renderSitemapIndex,
  sourceItemFields,
  statementFields,
  toSitemapLinks,
  PRODUCTION_ORIGIN,
} from "../apps/web/lib/seo";
import {
  datasetStructuredData,
  personStructuredData,
  serializeJsonLd,
  statementStructuredData,
  trendStructuredData,
} from "../apps/web/lib/structured-data";

const pool = createPool(process.env.DATABASE_URL ?? "postgresql://postgres:postgres@localhost:5432/pdoom_live_test");
const origin = "https://pdoom.live";

function nestedKeys(value: unknown, found = new Set<string>()): Set<string> {
  if (Array.isArray(value)) {
    for (const item of value) nestedKeys(item, found);
    return found;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      found.add(key);
      nestedKeys(child, found);
    }
  }
  return found;
}

describe("canonical origins", () => {
  it("never advertises localhost from a production environment", () => {
    const configured = [
      undefined,
      "",
      "   ",
      "http://localhost:3000",
      "http://localhost:3000/",
      "http://127.0.0.1:3000",
      "http://[::1]:3000",
      "http://0.0.0.0:3000",
      "http://10.1.2.3",
      "http://192.168.1.20:3000",
      "http://169.254.169.254/latest",
      "http://metadata.google.internal",
      "file:///etc/passwd",
      "javascript:alert(1)",
      "https://user:pass@pdoom.live/path",
      "http://pdoom.live/people",
      "not a url",
    ];
    for (const value of configured) {
      const resolved = resolveCanonicalOrigin({ configured: value, nodeEnv: "production" });
      expect(resolved).toBe(PRODUCTION_ORIGIN);
      expect(resolved.toLowerCase()).not.toContain("localhost");
      expect(resolved).not.toContain("127.0.0.1");
    }
  });

  it("keeps an explicit public origin and a development localhost origin", () => {
    expect(resolveCanonicalOrigin({ configured: "https://preview.example/app", nodeEnv: "production" })).toBe(
      "https://preview.example",
    );
    expect(resolveCanonicalOrigin({ configured: "http://localhost:3000", nodeEnv: "development" })).toBe(
      "http://localhost:3000",
    );
    expect(resolveCanonicalOrigin({ configured: "http://192.168.0.8:3000", nodeEnv: "development" })).toBe(
      "http://localhost:3000",
    );
    expect(absoluteUrl(origin, "/statements/ada-extinction-2023?cursor=abc#x")).toBe(
      "https://pdoom.live/statements/ada-extinction-2023",
    );
    expect(absoluteUrl(origin, "/people/ada-quill/")).toBe("https://pdoom.live/people/ada-quill");
    expect(() => absoluteUrl(origin, "https://evil.example")).toThrow(/invalid public path/);
  });

  it("reads APP_BASE_URL without turning production localhost into a canonical host", () => {
    expect(canonicalOrigin({ APP_BASE_URL: "http://localhost:3000", NODE_ENV: "production" } as NodeJS.ProcessEnv)).toBe(
      PRODUCTION_ORIGIN,
    );
  });
});

describe("statement metadata classes", () => {
  const shared = {
    slug: "ada-extinction-2023",
    display_name: "Ada Quill",
    availability: "available",
    collection_status: "collected",
    dataset_kind: "live" as const,
    indexable: true,
  };

  it("distinguishes explicit numeric, qualitative, and model-inferred copy", () => {
    const numeric = statementFields({
      ...shared,
      statement_type: "explicit_numeric",
      normalized_text: "Ada Quill stated 8% for unconditional extinction by 2070.",
    });
    const qualitative = statementFields({
      ...shared,
      slug: "ada-misuse-2024",
      statement_type: "explicit_qualitative",
      normalized_text: "Ada Quill said she was more worried about misuse than before, without a number.",
    });
    const inferred = statementFields({
      ...shared,
      slug: "ada-inferred-2024",
      statement_type: "model_inferred_signal",
      normalized_text: "Model signal: the interview is consistent with increased concern.",
    });
    expect(numeric.description).toContain("Explicit numerical estimate");
    expect(numeric.description).not.toContain("Model-inferred");
    expect(qualitative.description).toContain("Explicit qualitative view");
    expect(qualitative.description).toContain("without inferring a probability");
    expect(inferred.description).toContain("Model-inferred signal");
    expect(inferred.description).not.toContain("Explicit numerical estimate");
    expect(numeric.canonicalPath).toBe("/statements/ada-extinction-2023");
    expect(pageMetadata(origin, numeric).openGraph).toMatchObject({
      url: "https://pdoom.live/statements/ada-extinction-2023",
      type: "article",
    });
  });

  it("does not index non-public statement states and does not repeat their text", () => {
    const hidden = statementFields({
      ...shared,
      slug: "jonah-extinction-review-2024",
      statement_type: "explicit_numeric",
      normalized_text: "Jonah Hale wrote 30% for unconditional extinction.",
      indexable: false,
    });
    expect(hidden.index).toBe(false);
    expect(hidden.description).toBe("This statement is not in the public index.");
    expect(hidden.description).not.toContain("30%");
    expect(pageMetadata(origin, hidden).robots).toEqual({ index: false, follow: false });
  });

  it("keeps a removed source in the audit record without treating the original as live", () => {
    const fields = sourceItemFields({
      slug: "ada-essay-2023",
      title: "Essay",
      source_name: "Ada site",
      source_type: "personal_site",
      availability: "removed",
      collection_status: "not_found",
      is_current: true,
      current_slug: "ada-essay-2023",
      indexable: true,
      current_indexable: true,
    });
    expect(fields.index).toBe(true);
    expect(fields.canonicalPath).toBe("/source-items/ada-essay-2023");
    expect(fields.description.toLowerCase()).toContain("no longer available");
    const older = sourceItemFields({
      ...{
        slug: "old-essay",
        title: "Old",
        source_name: "Ada site",
        source_type: "personal_site",
        availability: "available",
        collection_status: "collected",
        is_current: false,
        current_slug: "ada-essay-2023",
        indexable: false,
        current_indexable: true,
      },
    });
    expect(older.index).toBe(false);
    expect(older.canonicalPath).toBe("/source-items/ada-essay-2023");
  });

  it("canonicalizes filtered list pages back to the bare path", () => {
    expect(hasDiscoveryFilter({ q: "extinction", cursor: "abc" })).toBe(true);
    expect(hasDiscoveryFilter({ limit: "10" })).toBe(false);
    const fields = listPageFields("statements", true);
    expect(fields.index).toBe(false);
    expect(fields.canonicalPath).toBe("/statements");
  });
});

describe("robots and sitemap shape", () => {
  it("allows public pages and excludes api, admin, and curation paths", () => {
    const robots = robotsDocument(origin);
    expect(robots.sitemap).toBe("https://pdoom.live/sitemap.xml");
    expect(robots.host).toBe(origin);
    expect(robots.rules.allow).toBe("/");
    expect(robots.rules.disallow).toEqual(expect.arrayContaining(["/api/", "/admin", "/curation", "/curator", "/ambiguity"]));
    for (const path of ["/people", "/statements", "/topics", "/sources", "/trends", "/methodology"]) {
      expect(ROBOTS_DISALLOW.some((rule) => path.startsWith(rule.replace("/*", "")))).toBe(false);
    }
  });

  it("splits sitemap chunks only after the first page fills", () => {
    expect(sitemapChunkPlan(0)).toEqual([0]);
    expect(sitemapChunkPlan(9993)).toEqual([0]);
    expect(sitemapChunkPlan(9994)).toEqual([0, 1]);
    expect(sitemapChunkBounds(0)).toEqual({ offset: 0, limit: 9993 });
    expect(sitemapChunkBounds(1).offset).toBe(9993);
    const links = toSitemapLinks(
      origin,
      [
        { path: "/statements/ada-extinction-2023", lastModified: "2023-01-01T00:00:00.000Z" },
        { path: "/api/admin", lastModified: null },
        { path: "/people/../secrets", lastModified: null },
      ],
      true,
    );
    expect(links.map((link) => link.url)).toContain("https://pdoom.live/");
    expect(links.map((link) => link.url)).toContain("https://pdoom.live/statements/ada-extinction-2023");
    expect(links.map((link) => link.url).join(" ")).not.toContain("/api/");
    expect(links.every((link) => link.url.startsWith(origin))).toBe(true);
    const index = renderSitemapIndex(origin, [0, 1]);
    expect(index).toContain("https://pdoom.live/sitemaps/0.xml");
    expect(index).toContain("https://pdoom.live/sitemaps/1.xml");
    expect(index).not.toContain("localhost");
  });
});

describe("structured data", () => {
  it("describes a purposive dataset and refuses invented person facts", () => {
    const dataset = datasetStructuredData({
      origin,
      datasetKind: "live",
      cohortName: "Frontier seed",
      notice: "Live public records.",
    });
    expect(dataset["@context"]).toBe("https://schema.org");
    expect(dataset["@type"]).toBe("Dataset");
    expect(dataset.description).toContain("purposive");
    expect(dataset.description.toLowerCase()).toContain("not a census");
    expect(dataset.description.toLowerCase()).toContain("not a consensus");
    const keys = nestedKeys(dataset);
    expect(keys.has("nationality")).toBe(false);

    const synthetic = personStructuredData({
      origin,
      slug: "ada-quill",
      display_name: "Ada Quill",
      bio_short: "Writes about forecasts.",
      dataset_kind: "synthetic",
      affiliations: [{ role: "Research lead", settled: true, organization: { name: "Northwind" } }],
      identities: [{ settled: true, canonical_url: "https://orcid.org/0000-0001-0000-0001" }],
    });
    expect(synthetic.description).toContain("Synthetic fixture");
    expect(synthetic).not.toHaveProperty("jobTitle");
    expect(synthetic).not.toHaveProperty("sameAs");
    expect(nestedKeys(synthetic).has("nationality")).toBe(false);

    const live = personStructuredData({
      origin,
      slug: "ada-quill",
      display_name: "Ada Quill",
      bio_short: "Writes about forecasts.",
      dataset_kind: "live",
      affiliations: [{ role: "Research lead", settled: true, organization: { name: "Northwind" } }],
      identities: [{ settled: true, canonical_url: "https://orcid.org/0000-0001-0000-0001" }],
    });
    expect(live.jobTitle).toBe("Research lead");
    expect(live.sameAs).toEqual(["https://orcid.org/0000-0001-0000-0001"]);
    expect(nestedKeys(live).has("alumniOf")).toBe(false);
    expect(nestedKeys(live).has("hasCredential")).toBe(false);

    const unsettled = personStructuredData({
      origin,
      slug: "ada-quill",
      display_name: "Ada Quill",
      bio_short: "Writes about forecasts.",
      dataset_kind: "live",
      affiliations: [{ role: "Research lead", settled: false, organization: { name: "Northwind" } }],
      identities: [{ settled: false, canonical_url: "https://orcid.org/0000-0001-0000-0001" }],
    });
    expect(unsettled).not.toHaveProperty("jobTitle");
    expect(unsettled).not.toHaveProperty("sameAs");
  });

  it("types statement classes and marks a removed original offline", () => {
    const numeric = statementStructuredData({
      origin,
      slug: "ada-extinction-2023",
      statement_type: "explicit_numeric",
      normalized_text: "Ada Quill stated 8%.",
      display_name: "Ada Quill",
      person_slug: "ada-quill",
      event_time: "2023-05-01T00:00:00.000Z",
      source_name: "Ada site",
      source_canonical_url: "https://synthetic.pdoom.example/items/ada-essay-2023",
      availability: "available",
      collection_status: "collected",
      dataset_kind: "live",
      indexable: true,
    });
    expect(numeric?.["@type"]).toBe("Article");
    expect(numeric?.author).toMatchObject({ name: "Ada Quill" });
    expect(numeric?.isBasedOn).toBe("https://synthetic.pdoom.example/items/ada-essay-2023");

    const inferred = statementStructuredData({
      origin,
      slug: "ada-inferred-2024",
      statement_type: "model_inferred_signal",
      normalized_text: "Model signal only.",
      display_name: "Ada Quill",
      person_slug: "ada-quill",
      event_time: null,
      source_name: "Ada site",
      source_canonical_url: "https://synthetic.pdoom.example/items/ada-interview-2024",
      availability: "available",
      collection_status: "collected",
      dataset_kind: "live",
      indexable: true,
    });
    expect(inferred?.["@type"]).toBe("CreativeWork");
    expect(inferred).not.toHaveProperty("author");
    expect(inferred?.creator).toMatchObject({ "@type": "Organization" });
    expect(String(inferred?.description)).toContain("Model signal only.");

    const removed = statementStructuredData({
      origin,
      slug: "ada-extinction-2023",
      statement_type: "explicit_numeric",
      normalized_text: "Ada Quill stated 8%.",
      display_name: "Ada Quill",
      person_slug: "ada-quill",
      event_time: "2023-05-01T00:00:00.000Z",
      source_name: "Ada site",
      source_canonical_url: "https://synthetic.pdoom.example/items/ada-essay-2023",
      availability: "removed",
      collection_status: "not_found",
      dataset_kind: "live",
      indexable: true,
    });
    expect(removed).not.toHaveProperty("isBasedOn");
    expect(removed?.creativeWorkStatus).toBe("Offline");
    expect(String(removed?.description)).toContain("no longer available");
    expect(
      statementStructuredData({
        origin,
        slug: "jonah-extinction-review-2024",
        statement_type: "explicit_numeric",
        normalized_text: "hidden",
        display_name: "Jonah Hale",
        person_slug: "jonah-hale",
        event_time: null,
        source_name: "Cast",
        source_canonical_url: "https://synthetic.pdoom.example/items/jonah-review-2024",
        availability: "available",
        collection_status: "collected",
        dataset_kind: "live",
        indexable: false,
      }),
    ).toBeNull();

    const trend = trendStructuredData({
      origin,
      slug: "extinction-by-2070-distribution",
      name: "Unconditional human-extinction probability by 2070",
      method_version: "explicit-numeric-distribution/1.0.0",
      cohort_definition: "Latest comparable point estimates.",
    });
    expect(trend["@type"]).toBe("Dataset");
    expect(trend.description).toContain("purposive");
    expect(serializeJsonLd({ description: `</script><img src=x>` })).not.toContain("</script>");
  });
});

describe("social cards", () => {
  it("truncates long names and keeps them as text", () => {
    const card = ogCardLines({
      kicker: "Person",
      title: `${"N".repeat(500)} https://evil.example/a.png`,
      detail: `${"D".repeat(400)} <script>alert(1)</script>`,
    });
    expect(card.title.length).toBeLessThanOrEqual(72);
    expect(card.title.endsWith("…")).toBe(true);
    expect(card.title).not.toContain("http");
    expect(card.detail.length).toBeLessThanOrEqual(160);
    expect(card.detail.endsWith("…")).toBe(true);
    expect(Object.keys(card).sort()).toEqual(["detail", "kicker", "title"]);
    expect(JSON.stringify(card)).not.toContain("src=");
  });
});

describe("public feed and sitemap filtering", () => {
  it("locks indexable review states to verified and machine-validated records", () => {
    expect(REVIEW_STATES.filter(isIndexableReviewState).sort()).toEqual([...PUBLIC_REVIEW_STATES].sort());
    expect(isPublicReviewState("needs_review")).toBe(true);
    expect(isIndexableReviewState("needs_review")).toBe(false);
    expect(isIndexableReviewState("unreviewed")).toBe(false);
    expect(isIndexableReviewState("rejected")).toBe(false);
  });

  it("omits non-indexable records and escapes feed text", async () => {
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      await client.query(`UPDATE statements SET review_state = 'rejected' WHERE slug = 'ada-misuse-2024'`);
      await client.query(`UPDATE statements SET review_state = 'unreviewed' WHERE slug = 'priya-coding-2025'`);
      await client.query(
        `UPDATE source_items SET availability = 'removed', collection_status = 'not_found' WHERE slug = 'ada-essay-2023'`,
      );
      await client.query(`UPDATE sources SET review_state = 'needs_review' WHERE slug = 'samira-letter'`);
      await client.query(`UPDATE source_items SET is_current = false WHERE slug = 'samira-letter-2024'`);
      await client.query(`UPDATE trend_definitions SET published = false WHERE slug = 'extinction-by-2070-distribution'`);

      const records = await listSitemapRecords(client, { offset: 0, limit: 5000 });
      const paths = records.map((record) => record.path);
      expect(paths).toContain("/statements/ada-extinction-2023");
      expect(paths).toContain("/statements/ada-inferred-2024");
      expect(paths).toContain("/statements/samira-labor-2024");
      expect(paths).toContain("/people/ada-quill");
      expect(paths).toContain("/source-items/ada-essay-2023");
      expect(paths).not.toContain("/statements/jonah-extinction-review-2024");
      expect(paths).not.toContain("/statements/ada-misuse-2024");
      expect(paths).not.toContain("/statements/priya-coding-2025");
      expect(paths).not.toContain("/statements/riley-hostile-2025");
      expect(paths).not.toContain("/people/riley-moss");
      expect(paths).not.toContain("/source-items/jonah-review-2024");
      expect(paths).not.toContain("/sources/samira-letter");
      expect(paths).not.toContain("/source-items/samira-letter-2024");
      expect(paths).not.toContain("/source-items/samira-letter-2025");
      expect(paths).not.toContain("/trends/extinction-by-2070-distribution");
      expect(paths.some((path) => path.startsWith("/api") || path.includes("admin") || path.includes("curat"))).toBe(false);
      expect(await countSitemapRecords(client)).toBe(paths.length);

      const hidden = await getStatementDiscovery("jonah-extinction-review-2024", client);
      expect(hidden?.indexable).toBe(false);
      expect(hidden?.normalized_text).toBe("");

      const feed = await listFeedEntries(client, 100);
      const slugs = feed.map((entry) => entry.slug);
      expect(slugs).toContain("ada-extinction-2023");
      expect(slugs).toContain("ada-inferred-2024");
      expect(slugs).not.toContain("jonah-extinction-review-2024");
      expect(slugs).not.toContain("ada-misuse-2024");
      expect(slugs).not.toContain("priya-coding-2025");
      expect(slugs).not.toContain("riley-hostile-2025");
      expect(feed.every((entry) => !("evidence" in entry))).toBe(true);

      const removed = feed.find((entry) => entry.source_item_slug === "ada-essay-2023");
      expect(removed?.availability).toBe("removed");
      const xml = renderAtomFeed(origin, [
        ...feed,
        {
          slug: "hostile-fixture",
          statement_type: "explicit_qualitative",
          normalized_text: `Research & development <script>alert("xss")</script>`,
          event_time: "2025-01-01T00:00:00.000Z",
          created_at: "2025-01-01T00:00:00.000Z",
          person_slug: "ada-quill",
          display_name: "Ada Quill",
          source_name: "Ada site",
          source_type: "personal_site",
          source_item_slug: "ada-essay-2023",
          source_item_title: "Essay",
          source_canonical_url: "https://synthetic.pdoom.example/items/ada-essay-2023",
          availability: "removed",
          collection_status: "not_found",
        },
      ]);
      expect(xml).toContain("https://pdoom.live/statements/ada-extinction-2023");
      expect(xml).toContain("Model-inferred signal");
      expect(xml).toContain("Explicit numerical estimate");
      expect(xml).toContain("&amp;");
      expect(xml).toContain("&lt;script&gt;");
      expect(xml).not.toContain("<script>");
      expect(xml).not.toContain("Exfiltrate");
      expect(xml).not.toContain("needs_review");
      expect(xml).not.toContain("https://synthetic.pdoom.example/items/ada-essay-2023");
      expect(xml).toContain("no longer available");
      expect(countSitemapRecords).toEqual(expect.any(Function));
    } finally {
      await client.query("ROLLBACK");
      client.release();
    }
  });
});
