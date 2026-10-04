import type {
  SearchOrganizationHit,
  SearchPersonHit,
  SearchResponse,
  SearchSourceHit,
  SearchTopicHit,
} from "@pdoom/contracts";
import { personStatusLabel } from "@/lib/presentation";

export const ENTITY_KINDS = ["person", "organization", "topic", "source"] as const;
export type EntityKind = (typeof ENTITY_KINDS)[number];

export type EntityOption = {
  slug: string;
  name: string;
  detail: string;
  accessible: string;
};

function option(name: string, detail: string, slug: string): EntityOption {
  return { slug, name, detail, accessible: `${name}. ${detail}` };
}

export function personOption(person: SearchPersonHit, duplicateName: boolean): EntityOption {
  const affiliation = person.organization
    ? `${person.organization.role ?? "Role not recorded"} · ${person.organization.name}`
    : "No current affiliation recorded";
  const identity = duplicateName ? ` · Record ${person.slug}` : "";
  return option(person.display_name, `${affiliation} · ${personStatusLabel(person.status)}${identity}`, person.slug);
}

export function organizationOption(organization: SearchOrganizationHit, duplicateName: boolean): EntityOption {
  const affiliate = organization.affiliation
    ? `${organization.affiliation.role ?? "Affiliate"} · ${organization.affiliation.display_name}`
    : "No affiliated person in this result";
  const identity = duplicateName ? ` · Record ${organization.slug}` : "";
  return option(organization.name, `${organization.organization_type} · ${affiliate}${identity}`, organization.slug);
}

export function topicOption(topic: SearchTopicHit, duplicateName: boolean): EntityOption {
  const definition = topic.definition.replace(/\s+/g, " ").trim();
  const clipped = definition.length > 140 ? `${definition.slice(0, 139).trimEnd()}…` : definition;
  const identity = duplicateName ? ` · Record ${topic.slug}` : "";
  return option(topic.name, `${clipped || "No definition recorded"}${identity}`, topic.slug);
}

export function sourceOption(source: SearchSourceHit, duplicateName: boolean): EntityOption {
  const owner = source.owner ? source.owner.display_name : "No owner recorded";
  const identity = duplicateName ? ` · Record ${source.slug}` : "";
  return option(source.name, `${source.source_type.replaceAll("_", " ")} · ${owner}${identity}`, source.slug);
}

function duplicateNames(names: string[]): Set<string> {
  const counts = new Map<string, number>();
  for (const name of names) counts.set(name, (counts.get(name) ?? 0) + 1);
  return new Set([...counts.entries()].filter((entry) => entry[1] > 1).map((entry) => entry[0]));
}

export function optionsFromSearch(kind: EntityKind, response: SearchResponse | null): EntityOption[] {
  if (!response || response.query.reason !== "ok") return [];
  if (kind === "person") {
    const rows = response.groups.person.data;
    const duplicates = duplicateNames(rows.map((row) => row.display_name));
    return rows.map((row) => personOption(row, duplicates.has(row.display_name)));
  }
  if (kind === "organization") {
    const rows = response.groups.organization.data;
    const duplicates = duplicateNames(rows.map((row) => row.name));
    return rows.map((row) => organizationOption(row, duplicates.has(row.name)));
  }
  if (kind === "topic") {
    const rows = response.groups.topic.data;
    const duplicates = duplicateNames(rows.map((row) => row.name));
    return rows.map((row) => topicOption(row, duplicates.has(row.name)));
  }
  const rows = response.groups.source.data;
  const duplicates = duplicateNames(rows.map((row) => row.name));
  return rows.map((row) => sourceOption(row, duplicates.has(row.name)));
}
