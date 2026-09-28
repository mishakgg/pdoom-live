import { safeExternalUrl } from "@pdoom/contracts";
import {
  PRODUCTION_ORIGIN,
  PURPOSIVE_COHORT_NOTE,
  SITE_DESCRIPTION,
  SITE_NAME,
  absoluteUrl,
  sourceCurrentlyAccessible,
  statementTypeLabel,
} from "@/lib/seo";

export function serializeJsonLd(data: unknown): string {
  return JSON.stringify(data).replaceAll("&", "\\u0026").replaceAll("<", "\\u003c").replaceAll(">", "\\u003e");
}

function organization(origin: string) {
  return {
    "@type": "Organization",
    name: SITE_NAME,
    url: origin,
  };
}

export function websiteStructuredData(origin: string) {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: origin,
    description: SITE_DESCRIPTION,
    publisher: organization(origin),
  };
}

export function datasetStructuredData(input: {
  origin: string;
  datasetKind: string | null;
  notice?: string | null;
  cohortName?: string | null;
  url?: string;
}) {
  const synthetic =
    input.datasetKind === "synthetic"
      ? "The loaded dataset is a synthetic fixture and does not describe real researchers."
      : null;
  const description = [input.notice?.trim(), synthetic, PURPOSIVE_COHORT_NOTE, SITE_DESCRIPTION]
    .filter((part): part is string => Boolean(part))
    .join(" ");
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: input.datasetKind === "synthetic" ? "pdoom.live synthetic fixture dataset" : "pdoom.live public statement dataset",
    description,
    url: input.url ?? input.origin,
    creator: organization(input.origin),
    isAccessibleForFree: true,
    measurementTechnique:
      "Source-attributed extraction that keeps explicit numerical estimates, explicit qualitative views, and model-inferred signals in separate classes.",
    variableMeasured: "Public statements and forecasts from a purposive cohort, not a population probability.",
    ...(input.cohortName ? { keywords: input.cohortName } : {}),
  };
}

export function methodologyStructuredData(origin: string, datasetKind: string | null) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Methodology",
    url: absoluteUrl(origin, "/methodology"),
    description: `How pdoom.live separates statement classes, horizons, and coverage. ${PURPOSIVE_COHORT_NOTE}`,
    isPartOf: { "@type": "WebSite", name: SITE_NAME, url: origin },
    about: datasetStructuredData({ origin, datasetKind, url: origin }),
  };
}

type SettledAffiliation = {
  role: string | null;
  settled: boolean;
  organization: { name: string };
};

type SettledIdentity = {
  settled: boolean;
  canonical_url: string | null;
};

export function personStructuredData(input: {
  origin: string;
  slug: string;
  display_name: string;
  bio_short: string;
  dataset_kind: string | null;
  affiliations: SettledAffiliation[];
  identities: SettledIdentity[];
}) {
  const url = absoluteUrl(input.origin, `/people/${input.slug}`);
  const synthetic = input.dataset_kind === "synthetic";
  const description = synthetic
    ? `Synthetic fixture record. ${input.display_name} is not a real researcher. ${input.bio_short}`
    : input.bio_short;
  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: input.display_name,
    url,
    description,
  };
  if (synthetic) return data;
  const affiliation = input.affiliations.find((item) => item.settled && item.role && item.organization.name);
  if (affiliation?.role) {
    data.jobTitle = affiliation.role;
    data.affiliation = {
      "@type": "Organization",
      name: affiliation.organization.name,
    };
  }
  const sameAs = input.identities
    .filter((identity) => identity.settled)
    .map((identity) => safeExternalUrl(identity.canonical_url))
    .filter((value): value is string => Boolean(value));
  if (sameAs.length) data.sameAs = sameAs;
  return data;
}

export function topicStructuredData(input: { origin: string; slug: string; name: string; definition: string }) {
  return {
    "@context": "https://schema.org",
    "@type": "DefinedTerm",
    name: input.name,
    description: input.definition,
    url: absoluteUrl(input.origin, `/topics/${input.slug}`),
    inDefinedTermSet: absoluteUrl(input.origin, "/topics"),
  };
}

export function statementStructuredData(input: {
  origin: string;
  slug: string;
  statement_type: string;
  normalized_text: string;
  display_name: string;
  person_slug: string;
  event_time: string | null;
  source_name: string;
  source_canonical_url: string;
  availability: string;
  collection_status: string;
  dataset_kind: string | null;
  indexable: boolean;
}) {
  if (!input.indexable) return null;
  const url = absoluteUrl(input.origin, `/statements/${input.slug}`);
  const inferred = input.statement_type === "model_inferred_signal";
  const accessible = sourceCurrentlyAccessible(input.availability, input.collection_status);
  const sourceUrl = accessible ? safeExternalUrl(input.source_canonical_url) : null;
  const label = statementTypeLabel(input.statement_type);
  const synthetic = input.dataset_kind === "synthetic" ? "Synthetic fixture. " : "";
  const offline =
    !accessible && (input.availability === "removed" || input.collection_status === "not_found" || input.collection_status === "unavailable")
      ? "The original source is no longer available. "
      : "";
  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": inferred ? "CreativeWork" : "Article",
    headline: `${label} · ${input.display_name}`,
    description: `${synthetic}${offline}${input.normalized_text}`,
    url,
    mainEntityOfPage: url,
    datePublished: input.event_time ?? undefined,
    publisher: { "@type": "Organization", name: SITE_NAME, url: input.origin },
    isAccessibleForFree: true,
  };
  if (inferred) {
    data.creator = { "@type": "Organization", name: SITE_NAME, url: input.origin };
    data.about = {
      "@type": "Person",
      name: input.display_name,
      url: absoluteUrl(input.origin, `/people/${input.person_slug}`),
    };
  } else {
    data.author = {
      "@type": "Person",
      name: input.display_name,
      url: absoluteUrl(input.origin, `/people/${input.person_slug}`),
    };
  }
  if (sourceUrl) data.isBasedOn = sourceUrl;
  if (!accessible && input.availability === "removed") data.creativeWorkStatus = "Offline";
  return data;
}

export function sourceStructuredData(input: { origin: string; slug: string; name: string; source_type: string }) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: input.name,
    description: `Tracked ${input.source_type.replaceAll("_", " ")} source recorded by ${SITE_NAME}.`,
    url: absoluteUrl(input.origin, `/sources/${input.slug}`),
    isPartOf: { "@type": "WebSite", name: SITE_NAME, url: input.origin },
  };
}

export function sourceItemStructuredData(input: {
  origin: string;
  slug: string;
  title: string | null;
  source_name: string;
  canonical_url: string;
  availability: string;
  collection_status: string;
  indexable: boolean;
}) {
  if (!input.indexable) return null;
  const accessible = sourceCurrentlyAccessible(input.availability, input.collection_status);
  const sourceUrl = accessible ? safeExternalUrl(input.canonical_url) : null;
  const url = absoluteUrl(input.origin, `/source-items/${input.slug}`);
  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: input.title || input.source_name,
    url,
    publisher: { "@type": "Organization", name: input.source_name },
    description: accessible
      ? `Source item from ${input.source_name}, recorded by ${SITE_NAME}.`
      : `Audit record from ${input.source_name}. The original source is no longer available.`,
  };
  if (sourceUrl) data.sameAs = sourceUrl;
  if (!accessible && input.availability === "removed") data.creativeWorkStatus = "Offline";
  return data;
}

export function trendStructuredData(input: {
  origin: string;
  slug: string;
  name: string;
  method_version: string;
  cohort_definition: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: input.name,
    description: `${input.cohort_definition} Method ${input.method_version}. ${PURPOSIVE_COHORT_NOTE}`,
    url: absoluteUrl(input.origin, `/trends/${input.slug}`),
    creator: { "@type": "Organization", name: SITE_NAME, url: input.origin },
    isBasedOn: input.origin,
    measurementTechnique: input.method_version,
    variableMeasured: "A declared aggregate over a purposive cohort, not a field consensus.",
  };
}

export const STRUCTURED_DATA_CONTEXT = "https://schema.org";
export const PRODUCTION_SITE_ORIGIN = PRODUCTION_ORIGIN;
