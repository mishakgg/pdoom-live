import { isBlockedHostname, STATEMENT_TYPE_LABELS, type StatementType } from "@pdoom/contracts";
import type { Metadata } from "next";

export const SITE_NAME = "pdoom.live";
export const PRODUCTION_ORIGIN = "https://pdoom.live";
export const SITE_DESCRIPTION =
  "Provenance-first observatory of public AI forecasts from a purposive cohort. Not a census or a consensus. Numerical estimates, qualitative views, and model-inferred signals stay separate.";

export const PURPOSIVE_COHORT_NOTE =
  "The cohort is purposive. It is not a census of AI researchers and it is not a consensus sample.";

const PUBLIC_SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export function isPublicSlug(slug: string): boolean {
  return slug.length > 0 && slug.length <= 200 && PUBLIC_SLUG.test(slug);
}

function loopbackHost(hostname: string): boolean {
  const host = hostname.trim().toLowerCase().replace(/\.$/, "").replace(/^\[|\]$/g, "");
  return host === "localhost" || host.endsWith(".localhost") || host === "127.0.0.1" || host === "::1";
}

/**
 * Origin used for canonical, Open Graph, sitemap, and feed links.
 * Production never advertises localhost, loopback, or another blocked host.
 */
export function resolveCanonicalOrigin(input: { configured?: string | null; nodeEnv?: string | null }): string {
  const production = input.nodeEnv === "production";
  const fallback = production ? PRODUCTION_ORIGIN : "http://localhost:3000";
  const raw = input.configured?.trim();
  if (!raw) return fallback;
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return fallback;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return fallback;
  if (url.username || url.password) return fallback;
  if (isBlockedHostname(url.hostname)) {
    if (production) return PRODUCTION_ORIGIN;
    if (loopbackHost(url.hostname)) return url.origin;
    return "http://localhost:3000";
  }
  if (production && url.hostname.toLowerCase() === "pdoom.live") return PRODUCTION_ORIGIN;
  return url.origin;
}

export function canonicalOrigin(env: NodeJS.ProcessEnv = process.env): string {
  return resolveCanonicalOrigin({
    configured: env.APP_BASE_URL,
    nodeEnv: env.NODE_ENV,
  });
}

export function absoluteUrl(origin: string, pathname: string): string {
  const path = publicPath(pathname);
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("invalid public path");
  }
  const base = new URL(origin);
  const url = new URL(path, base.origin);
  if (url.origin !== base.origin) throw new Error("origin escape");
  return url.toString();
}

export function publicPath(pathname: string): string {
  const withoutHash = pathname.split("#")[0] ?? pathname;
  const withoutQuery = withoutHash.split("?")[0] ?? withoutHash;
  if (withoutQuery !== "/" && withoutQuery.endsWith("/")) return withoutQuery.slice(0, -1);
  return withoutQuery || "/";
}

export function clampText(input: string, max: number): string {
  const cleaned = input.replace(/[\u0000-\u001F\u007F]+/g, " ").replace(/\s+/g, " ").trim();
  if (cleaned.length <= max) return cleaned;
  const sliced = cleaned.slice(0, Math.max(0, max - 1)).trimEnd();
  return `${sliced}…`;
}

export type SocialCard = {
  kicker: string;
  title: string;
  detail: string;
};

export function ogCardLines(input: SocialCard): SocialCard {
  return {
    kicker: clampText(input.kicker, 48),
    title: clampText(input.title, 72),
    detail: clampText(input.detail, 160),
  };
}

export type DiscoveryFields = {
  title: string;
  description: string;
  canonicalPath: string;
  index: boolean;
  openGraphType: "website" | "article" | "profile";
  card: SocialCard;
};

export function socialTitle(title: string): string {
  if (title === SITE_NAME) return title;
  return `${title} · ${SITE_NAME}`;
}

export function pageMetadata(origin: string, fields: DiscoveryFields): Metadata {
  const description = clampText(fields.description, 240);
  const url = absoluteUrl(origin, fields.canonicalPath);
  const title = fields.title;
  return {
    title: title === SITE_NAME ? { absolute: SITE_NAME } : title,
    description,
    alternates: { canonical: fields.canonicalPath },
    robots: fields.index ? { index: true, follow: true } : { index: false, follow: false },
    openGraph: {
      title: socialTitle(title),
      description,
      url,
      siteName: SITE_NAME,
      type: fields.openGraphType,
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title: socialTitle(title),
      description,
    },
  };
}

export function siteMetadata(origin: string): Metadata {
  return {
    metadataBase: new URL(origin),
    title: { default: SITE_NAME, template: `%s · ${SITE_NAME}` },
    description: SITE_DESCRIPTION,
    applicationName: SITE_NAME,
    authors: [{ name: SITE_NAME, url: origin }],
    creator: SITE_NAME,
    publisher: SITE_NAME,
    alternates: {
      types: {
        "application/atom+xml": absoluteUrl(origin, "/feed.xml"),
      },
    },
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      title: SITE_NAME,
      description: SITE_DESCRIPTION,
      url: origin,
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title: SITE_NAME,
      description: SITE_DESCRIPTION,
    },
    robots: { index: true, follow: true },
  };
}

export function notFoundMetadata(): Metadata {
  return {
    title: "Not in the dataset",
    description: "That record is not in the current public dataset.",
    robots: { index: false, follow: false },
  };
}

const LIST_COPY: Record<string, { title: string; path: string; description: string }> = {
  home: {
    title: SITE_NAME,
    path: "/",
    description: SITE_DESCRIPTION,
  },
  people: {
    title: "People",
    path: "/people",
    description: "People included in the pdoom.live cohort, each with a stored inclusion reason. Similar names are kept distinct.",
  },
  topics: {
    title: "Topics",
    path: "/topics",
    description: "Topic definitions used to organize sourced statements. Different questions are not combined into one probability.",
  },
  statements: {
    title: "Statements",
    path: "/statements",
    description: "Sourced statements in three classes: explicit numerical estimates, explicit qualitative views, and model-inferred signals.",
  },
  sources: {
    title: "Sources",
    path: "/sources",
    description: "Channels and feeds tracked by pdoom.live. Publication time and observation time stay separate.",
  },
  trends: {
    title: "Trends",
    path: "/trends",
    description: "Published trend summaries. Each one names its method, cohort, and the records it leaves out. A summary is not a consensus.",
  },
  search: {
    title: "Search",
    path: "/search",
    description: "Search people, statements, topics, and sources in the public dataset. Query results are not indexed separately.",
  },
  data: {
    title: "Data",
    path: "/data",
    description: "Public dataset exports and the versioned read API. The export omits rejected, unreviewed, and needs-review records.",
  },
  methodology: {
    title: "Methodology",
    path: "/methodology",
    description: `How pdoom.live separates statement classes, horizons, and coverage. ${PURPOSIVE_COHORT_NOTE}`,
  },
};

export function hasDiscoveryFilter(params: Record<string, string | string[] | undefined>): boolean {
  return Object.entries(params).some(([key, value]) => {
    if (key === "limit") return false;
    if (Array.isArray(value)) return value.some((item) => item.trim().length > 0);
    return Boolean(value && value.trim());
  });
}

export function listPageFields(key: keyof typeof LIST_COPY, filtered = false): DiscoveryFields {
  const copy = LIST_COPY[key];
  if (!copy) throw new Error("unknown list page");
  return {
    title: copy.title,
    description: copy.description,
    canonicalPath: copy.path,
    index: !filtered,
    openGraphType: "website",
    card: { kicker: SITE_NAME, title: copy.title, detail: copy.description },
  };
}

export function statementTypeLabel(type: string): string {
  if (type in STATEMENT_TYPE_LABELS) return STATEMENT_TYPE_LABELS[type as StatementType];
  return "Statement";
}

export function sourceCurrentlyAccessible(availability: string, collectionStatus: string | null | undefined): boolean {
  if (availability !== "available") return false;
  if (collectionStatus === "not_found" || collectionStatus === "unavailable" || collectionStatus === "unauthorized") {
    return false;
  }
  return true;
}

export function sourceAvailabilitySentence(availability: string, collectionStatus: string | null | undefined): string | null {
  if (sourceCurrentlyAccessible(availability, collectionStatus)) return null;
  if (availability === "removed" || collectionStatus === "not_found" || collectionStatus === "unavailable") {
    return "The original source is no longer available. This page keeps the audit record.";
  }
  if (availability === "unknown") return "Original availability is unknown.";
  return "The original source is not currently accessible. This page keeps the audit record.";
}

function syntheticPrefix(datasetKind: string | null | undefined): string {
  return datasetKind === "synthetic" ? "Synthetic fixture. " : "";
}

export function statementFields(input: {
  slug: string;
  statement_type: string;
  normalized_text: string;
  display_name: string;
  availability: string;
  collection_status: string;
  dataset_kind: string | null;
  indexable: boolean;
}): DiscoveryFields {
  const path = `/statements/${input.slug}`;
  if (!input.indexable || !isPublicSlug(input.slug)) {
    return {
      title: "Statement",
      description: "This statement is not in the public index.",
      canonicalPath: isPublicSlug(input.slug) ? path : "/statements",
      index: false,
      openGraphType: "article",
      card: { kicker: SITE_NAME, title: SITE_NAME, detail: SITE_DESCRIPTION },
    };
  }
  const label = statementTypeLabel(input.statement_type);
  const availability = sourceAvailabilitySentence(input.availability, input.collection_status);
  const lead = statementClassSentence(input.statement_type, input.display_name);
  const description = [syntheticPrefix(input.dataset_kind) + lead, clampText(input.normalized_text, 160), availability]
    .filter(Boolean)
    .join(" ");
  const title = clampText(`${label} · ${input.display_name}`, 80);
  return {
    title,
    description,
    canonicalPath: path,
    index: true,
    openGraphType: "article",
    card: { kicker: label, title: input.display_name, detail: description },
  };
}

function statementClassSentence(type: string, name: string): string {
  if (type === "explicit_numeric") {
    return `Explicit numerical estimate attributed to ${name}. The number is taken from the source.`;
  }
  if (type === "explicit_qualitative") {
    return `Explicit qualitative view attributed to ${name}. The wording is stored without inferring a probability.`;
  }
  if (type === "model_inferred_signal") {
    return `Model-inferred signal concerning ${name}. This is machine classification, kept separate from anything the person stated as a probability.`;
  }
  return `Sourced statement concerning ${name}.`;
}

export function personFields(input: {
  slug: string;
  display_name: string;
  bio_short: string;
  status: string;
  dataset_kind: string | null;
  indexable: boolean;
}): DiscoveryFields {
  const path = `/people/${input.slug}`;
  if (!input.indexable || !isPublicSlug(input.slug)) {
    return {
      title: "Person",
      description: "This person record is not in the public index.",
      canonicalPath: isPublicSlug(input.slug) ? path : "/people",
      index: false,
      openGraphType: "profile",
      card: { kicker: SITE_NAME, title: SITE_NAME, detail: SITE_DESCRIPTION },
    };
  }
  const description = `${syntheticPrefix(input.dataset_kind)}${input.display_name} is included in the pdoom.live cohort. ${clampText(input.bio_short, 160)}`;
  return {
    title: clampText(input.display_name, 80),
    description,
    canonicalPath: path,
    index: true,
    openGraphType: "profile",
    card: { kicker: "Person", title: input.display_name, detail: description },
  };
}

export function topicFields(input: { slug: string; name: string; definition: string }): DiscoveryFields {
  const description = clampText(input.definition, 220);
  return {
    title: clampText(input.name, 80),
    description,
    canonicalPath: `/topics/${input.slug}`,
    index: isPublicSlug(input.slug),
    openGraphType: "website",
    card: { kicker: "Topic", title: input.name, detail: description },
  };
}

export function sourceFields(input: {
  slug: string;
  name: string;
  source_type: string;
  indexable: boolean;
}): DiscoveryFields {
  const path = `/sources/${input.slug}`;
  if (!input.indexable || !isPublicSlug(input.slug)) {
    return {
      title: "Source",
      description: "This source is not in the public index.",
      canonicalPath: isPublicSlug(input.slug) ? path : "/sources",
      index: false,
      openGraphType: "website",
      card: { kicker: SITE_NAME, title: SITE_NAME, detail: SITE_DESCRIPTION },
    };
  }
  const description = `Tracked ${input.source_type.replaceAll("_", " ")} source: ${input.name}.`;
  return {
    title: clampText(input.name, 80),
    description,
    canonicalPath: path,
    index: true,
    openGraphType: "website",
    card: { kicker: "Source", title: input.name, detail: description },
  };
}

export function sourceItemFields(input: {
  slug: string;
  title: string | null;
  source_name: string;
  source_type: string;
  availability: string;
  collection_status: string;
  is_current: boolean;
  current_slug: string | null;
  indexable: boolean;
  current_indexable: boolean;
}): DiscoveryFields {
  const self = `/source-items/${input.slug}`;
  const currentPath =
    input.current_slug && isPublicSlug(input.current_slug) ? `/source-items/${input.current_slug}` : self;
  const canonicalPath = !input.is_current && input.current_indexable ? currentPath : self;
  const index = input.indexable && input.is_current && isPublicSlug(input.slug);
  if (!index) {
    return {
      title: "Source item",
      description: input.is_current
        ? "This source item is not in the public index."
        : "This is an older source version and is not the indexed record.",
      canonicalPath: isPublicSlug(input.slug) ? canonicalPath : "/sources",
      index: false,
      openGraphType: "article",
      card: { kicker: SITE_NAME, title: SITE_NAME, detail: SITE_DESCRIPTION },
    };
  }
  const title = input.title?.trim() || input.source_name;
  const availability = sourceAvailabilitySentence(input.availability, input.collection_status);
  const description = [
    availability,
    `Source item from ${input.source_name} (${input.source_type.replaceAll("_", " ")}).`,
  ]
    .filter(Boolean)
    .join(" ");
  return {
    title: clampText(title, 80),
    description,
    canonicalPath: self,
    index: true,
    openGraphType: "article",
    card: { kicker: "Source item", title, detail: description },
  };
}

export function trendFields(input: {
  slug: string;
  name: string;
  method_version: string;
  cohort_version: string;
}): DiscoveryFields {
  const description = `${input.name}. Method ${input.method_version}. Cohort version ${input.cohort_version}. ${PURPOSIVE_COHORT_NOTE}`;
  return {
    title: clampText(input.name, 80),
    description,
    canonicalPath: `/trends/${input.slug}`,
    index: isPublicSlug(input.slug),
    openGraphType: "website",
    card: { kicker: "Trend", title: input.name, detail: description },
  };
}

export const STATIC_SITEMAP_PATHS = [
  "/",
  "/people",
  "/topics",
  "/statements",
  "/sources",
  "/search",
  "/trends",
  "/data",
  "/methodology",
] as const;

export const SITEMAP_CHUNK_SIZE = 10_000;
export const SITEMAP_CHUNK_CAP = 50;

export function sitemapChunkPlan(dynamicCount: number): number[] {
  const safeCount = Math.max(0, dynamicCount);
  const first = Math.max(1, SITEMAP_CHUNK_SIZE - STATIC_SITEMAP_PATHS.length);
  if (safeCount <= first) return [0];
  const extra = Math.ceil((safeCount - first) / SITEMAP_CHUNK_SIZE);
  const total = Math.min(1 + extra, SITEMAP_CHUNK_CAP);
  return Array.from({ length: total }, (_, id) => id);
}

export function sitemapChunkBounds(id: number): { offset: number; limit: number } {
  const first = SITEMAP_CHUNK_SIZE - STATIC_SITEMAP_PATHS.length;
  if (id <= 0) return { offset: 0, limit: first };
  return { offset: first + (id - 1) * SITEMAP_CHUNK_SIZE, limit: SITEMAP_CHUNK_SIZE };
}

const INDEXABLE_PATH = [
  /^\/$/,
  /^\/people$/,
  /^\/people\/[a-z0-9]+(?:-[a-z0-9]+)*$/,
  /^\/topics$/,
  /^\/topics\/[a-z0-9]+(?:-[a-z0-9]+)*$/,
  /^\/statements$/,
  /^\/statements\/[a-z0-9]+(?:-[a-z0-9]+)*$/,
  /^\/sources$/,
  /^\/sources\/[a-z0-9]+(?:-[a-z0-9]+)*$/,
  /^\/source-items\/[a-z0-9]+(?:-[a-z0-9]+)*$/,
  /^\/search$/,
  /^\/trends$/,
  /^\/trends\/[a-z0-9]+(?:-[a-z0-9]+)*$/,
  /^\/data$/,
  /^\/methodology$/,
];

export function isIndexablePath(pathname: string): boolean {
  return INDEXABLE_PATH.some((pattern) => pattern.test(pathname));
}

export type SitemapLink = {
  url: string;
  lastModified?: Date;
};

export function toSitemapLinks(
  origin: string,
  records: Array<{ path: string; lastModified: string | null }>,
  includeStatic: boolean,
): SitemapLink[] {
  const staticRecords = includeStatic ? STATIC_SITEMAP_PATHS.map((path) => ({ path, lastModified: null })) : [];
  const links: SitemapLink[] = [];
  for (const record of [...staticRecords, ...records]) {
    if (!isIndexablePath(record.path)) continue;
    const link: SitemapLink = { url: absoluteUrl(origin, record.path) };
    if (record.lastModified) {
      const date = new Date(record.lastModified);
      if (!Number.isNaN(date.getTime())) link.lastModified = date;
    }
    links.push(link);
  }
  return links;
}

export const ROBOTS_DISALLOW = [
  "/api/",
  "/admin",
  "/admin/",
  "/curation",
  "/curation/",
  "/curator",
  "/curator/",
  "/ambiguity",
  "/ambiguity/",
  "/review-queue",
  "/review-queue/",
  "/internal",
  "/internal/",
  "/*?",
] as const;

function escapeXmlText(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

export function renderUrlSet(links: SitemapLink[]): string {
  const urls = links
    .map((link) => {
      const lastmod = link.lastModified ? `\n    <lastmod>${link.lastModified.toISOString()}</lastmod>` : "";
      return `  <url>\n    <loc>${escapeXmlText(link.url)}</loc>${lastmod}\n  </url>`;
    })
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

export function renderSitemapIndex(origin: string, ids: number[]): string {
  const body = ids
    .map((id) => `  <sitemap><loc>${escapeXmlText(absoluteUrl(origin, `/sitemaps/${id}.xml`))}</loc></sitemap>`)
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${body}
</sitemapindex>
`;
}

export function robotsDocument(origin: string): {
  rules: { userAgent: string; allow: string; disallow: string[] };
  sitemap: string;
  host: string;
} {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [...ROBOTS_DISALLOW],
    },
    sitemap: absoluteUrl(origin, "/sitemap.xml"),
    host: origin,
  };
}
