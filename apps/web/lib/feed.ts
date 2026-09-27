import { safeExternalUrl } from "@pdoom/contracts";
import type { FeedEntry } from "@pdoom/db";
import { SITE_DESCRIPTION, SITE_NAME, absoluteUrl, sourceCurrentlyAccessible, statementTypeLabel } from "@/lib/seo";

export const FEED_LIMIT = 50;

export function escapeXml(value: string): string {
  return value
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function attribution(origin: string, entry: FeedEntry): string {
  const audit = absoluteUrl(origin, `/source-items/${entry.source_item_slug}`);
  if (!sourceCurrentlyAccessible(entry.availability, entry.collection_status)) {
    return `Source: ${entry.source_name} (${entry.source_type}). The original is no longer available. Audit record: ${audit}`;
  }
  const url = safeExternalUrl(entry.source_canonical_url);
  if (!url) {
    return `Source: ${entry.source_name} (${entry.source_type}). Audit record: ${audit}`;
  }
  return `Source: ${entry.source_name} (${entry.source_type}). Original: ${url}. Audit record: ${audit}`;
}

function entryBody(origin: string, entry: FeedEntry): string {
  const label = statementTypeLabel(entry.statement_type);
  const credit = attribution(origin, entry);
  if (entry.statement_type === "model_inferred_signal") {
    return `${label} concerning ${entry.display_name}. Machine classification, kept separate from a stated probability. ${entry.normalized_text} ${credit}`;
  }
  if (entry.statement_type === "explicit_qualitative") {
    return `${label} attributed to ${entry.display_name}. No probability is inferred. ${entry.normalized_text} ${credit}`;
  }
  if (entry.statement_type === "explicit_numeric") {
    return `${label} attributed to ${entry.display_name}. The number is taken from the source. ${entry.normalized_text} ${credit}`;
  }
  return `${entry.normalized_text} ${credit}`;
}

export function renderAtomFeed(origin: string, entries: FeedEntry[], generatedAt = new Date()): string {
  const feedUrl = absoluteUrl(origin, "/feed.xml");
  const updated = entries[0]?.event_time ?? entries[0]?.created_at ?? generatedAt.toISOString();
  const items = entries
    .map((entry) => {
      const href = absoluteUrl(origin, `/statements/${entry.slug}`);
      const when = entry.event_time ?? entry.created_at;
      const label = statementTypeLabel(entry.statement_type);
      const inferred = entry.statement_type === "model_inferred_signal";
      const authorName = inferred ? SITE_NAME : entry.display_name;
      const authorUri = inferred ? origin : absoluteUrl(origin, `/people/${entry.person_slug}`);
      const title = `${label} · ${entry.display_name}`;
      return `  <entry>
    <title>${escapeXml(title)}</title>
    <id>${escapeXml(href)}</id>
    <link rel="alternate" type="text/html" href="${escapeXml(href)}"/>
    <updated>${escapeXml(when)}</updated>
    <published>${escapeXml(when)}</published>
    <author><name>${escapeXml(authorName)}</name><uri>${escapeXml(authorUri)}</uri></author>
    <category term="${escapeXml(entry.statement_type)}" label="${escapeXml(label)}"/>
    <summary type="text">${escapeXml(entryBody(origin, entry))}</summary>
  </entry>`;
    })
    .join("\n");
  return `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">
  <title>${escapeXml(`${SITE_NAME} public statements`)}</title>
  <subtitle>${escapeXml(SITE_DESCRIPTION)}</subtitle>
  <id>${escapeXml(feedUrl)}</id>
  <updated>${escapeXml(updated)}</updated>
  <link rel="self" type="application/atom+xml" href="${escapeXml(feedUrl)}"/>
  <link rel="alternate" type="text/html" href="${escapeXml(absoluteUrl(origin, "/statements"))}"/>
  <generator>pdoom.live</generator>
${items}
</feed>
`;
}
