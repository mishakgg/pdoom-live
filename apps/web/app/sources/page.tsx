import { listSources } from "@pdoom/db";
import { ExternalLink } from "@/components/statement-bits";
import { formatWhen } from "@/lib/format";
import Link from "next/link";
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
      <p className="lede">A source is a feed or channel. Items keep publication time separate from observation time.</p>
      {sources.map((source) => (
        <article className="card" key={source.slug}>
          <div className="row">
            <h2><Link href={`/sources/${source.slug}`}>{source.name}</Link></h2>
            <span className="meta">{source.source_type}</span>
          </div>
          <p className="meta">
            {source.item_count} items · last success {formatWhen(source.last_success_at)} · {source.enabled ? "enabled" : "disabled"}
            {source.last_success_at ? "" : " · no successful check"}
          </p>
          <p><ExternalLink href={source.canonical_url}>{source.canonical_url}</ExternalLink></p>
        </article>
      ))}
    </>
  );
}
