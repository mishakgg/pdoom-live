import { listSources } from "@pdoom/db";
import Link from "next/link";
import { ExternalLink } from "@/components/statement-bits";
import { EmptyState } from "@/components/states";
import { formatWhen, isHumanVerified, phraseLabel, reviewLabel } from "@/lib/format";
import { freshnessLabel } from "@/lib/presentation";
import { canonicalOrigin, listPageFields, pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return pageMetadata(canonicalOrigin(), listPageFields("sources"));
}

export default async function SourcesPage() {
  const sources = await listSources();
  return (
    <>
      <h1>Sources</h1>
      <p className="lede">A source is a feed or channel. Items keep publication time separate from observation time. Freshness describes collection, not whether anyone has spoken.</p>
      {sources.length ? sources.map((source) => (
        <article className="card" key={source.slug}>
          <p className="kicker">{phraseLabel(source.source_type)} · {freshnessLabel(source.freshness)}</p>
          <h2><Link href={`/sources/${source.slug}`}>{source.name}</Link></h2>
          <p className="meta">
            {source.item_count} {source.item_count === 1 ? "item" : "items"}
            {" · "}
            Last check {formatWhen(source.last_checked_at)}
            {" · "}
            Last success {formatWhen(source.last_success_at)}
            {" · "}
            {source.enabled ? "Enabled" : "Disabled"}
            {" · "}
            {reviewLabel(source.review_state)}
            {isHumanVerified(source.review_state) ? "" : " · not a settled source record"}
          </p>
          {source.owner_slug && source.owner_name ? (
            <p>Owner <Link href={`/people/${source.owner_slug}`}>{source.owner_name}</Link></p>
          ) : null}
          {source.organization_name ? <p className="meta">Organization {source.organization_name}</p> : null}
          <p><ExternalLink href={source.canonical_url}>{source.canonical_url}</ExternalLink></p>
          {source.freshness === "never_checked" ? (
            <p>No successful check is recorded. That is a collection gap, not evidence the channel is empty of speech.</p>
          ) : null}
        </article>
      )) : (
        <EmptyState title="No sources are loaded">
          <p>No source channel is in this dataset. Coverage cannot be judged until sources are registered.</p>
        </EmptyState>
      )}
    </>
  );
}
