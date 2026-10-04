import type { EntityKind } from "@/lib/entity-options";
import { organizationOption, personOption, sourceOption, topicOption } from "@/lib/entity-options";
import { getPerson, listPublicOrganizations, listSources, listTopics, searchPublic } from "@pdoom/db";

export type EntityLabel = {
  slug: string;
  name: string;
  detail: string;
  unresolved: boolean;
};

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export type FilterLabels = {
  person: EntityLabel | null;
  organization: EntityLabel | null;
  source: EntityLabel | null;
  topic: EntityLabel | null;
};

function unresolved(slug: string): EntityLabel {
  return {
    slug,
    name: slug,
    detail: "This identifier is not in the current dataset.",
    unresolved: true,
  };
}

async function searchHit(kind: EntityKind, slug: string) {
  const q = slug.replaceAll("-", " ").trim();
  if (q.length < 2) return null;
  try {
    const result = await searchPublic({ q, type: kind, mode: "page", limit: 20 });
    return result.groups[kind].data.find((hit) => hit.slug === slug) ?? null;
  } catch {
    return null;
  }
}

async function resolvePerson(slug: string): Promise<EntityLabel> {
  const hit = await searchHit("person", slug);
  if (hit && hit.kind === "person") {
    const option = personOption(hit, false);
    return { slug, name: option.name, detail: option.detail, unresolved: false };
  }
  const person = await getPerson(slug);
  if (!person) return unresolved(slug);
  const current = person.affiliations.find((item) => item.settled && !item.end_date);
  const detail = current
    ? `${current.role ?? "Role not recorded"} · ${current.organization.name}`
    : "No current affiliation recorded";
  return { slug, name: person.display_name, detail, unresolved: false };
}

async function resolveOrganization(slug: string): Promise<EntityLabel> {
  const hit = await searchHit("organization", slug);
  if (hit && hit.kind === "organization") {
    const option = organizationOption(hit, false);
    return { slug, name: option.name, detail: option.detail, unresolved: false };
  }
  const organizations = await listPublicOrganizations();
  const organization = organizations.find((item) => item.slug === slug);
  if (!organization) return unresolved(slug);
  return { slug, name: organization.name, detail: organization.organization_type, unresolved: false };
}

async function resolveTopic(slug: string): Promise<EntityLabel> {
  const hit = await searchHit("topic", slug);
  if (hit && hit.kind === "topic") {
    const option = topicOption(hit, false);
    return { slug, name: option.name, detail: option.detail, unresolved: false };
  }
  const topics = await listTopics();
  const topic = topics.find((item) => item.slug === slug);
  if (!topic) return unresolved(slug);
  return { slug, name: topic.name, detail: `Version ${topic.version}`, unresolved: false };
}

async function resolveSource(slug: string): Promise<EntityLabel> {
  const hit = await searchHit("source", slug);
  if (hit && hit.kind === "source") {
    const option = sourceOption(hit, false);
    return { slug, name: option.name, detail: option.detail, unresolved: false };
  }
  const sources = await listSources();
  const source = sources.find((item) => item.slug === slug);
  if (!source) return unresolved(slug);
  return {
    slug,
    name: source.name,
    detail: source.owner_name ? `${source.source_type.replaceAll("_", " ")} · ${source.owner_name}` : source.source_type.replaceAll("_", " "),
    unresolved: false,
  };
}

async function resolveOne(kind: EntityKind, slug: string | undefined): Promise<EntityLabel | null> {
  if (!slug) return null;
  if (!SLUG.test(slug)) return unresolved(slug);
  if (kind === "person") return resolvePerson(slug);
  if (kind === "organization") return resolveOrganization(slug);
  if (kind === "topic") return resolveTopic(slug);
  return resolveSource(slug);
}

export async function resolveFilterLabels(input: {
  person?: string | undefined;
  organization?: string | undefined;
  source?: string | undefined;
  topic?: string | undefined;
}): Promise<FilterLabels> {
  const [person, organization, source, topic] = await Promise.all([
    resolveOne("person", input.person),
    resolveOne("organization", input.organization),
    resolveOne("source", input.source),
    resolveOne("topic", input.topic),
  ]);
  return { person, organization, source, topic };
}
