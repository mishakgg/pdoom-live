import { EvidenceBlock, ExternalLink } from "@/components/statement-bits";
import { JsonLd } from "@/components/json-ld";
import { formatWhen } from "@/lib/format";
import { loadSourceItem, loadSourceItemDiscovery } from "@/lib/loaders";
import { canonicalOrigin, notFoundMetadata, pageMetadata, sourceItemFields } from "@/lib/seo";
import { sourceItemStructuredData } from "@/lib/structured-data";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = await loadSourceItemDiscovery(slug);
  if (!item) return notFoundMetadata();
  return pageMetadata(canonicalOrigin(), sourceItemFields(item));
}

export default async function SourceItemPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [item, discovery] = await Promise.all([loadSourceItem(slug), loadSourceItemDiscovery(slug)]);
  if (!item || !discovery) notFound();
  const structured = sourceItemStructuredData({
    origin: canonicalOrigin(),
    slug: discovery.slug,
    title: discovery.indexable ? discovery.title : null,
    source_name: discovery.source_name,
    canonical_url: discovery.canonical_url,
    availability: discovery.availability,
    collection_status: discovery.collection_status,
    indexable: discovery.indexable,
  });
  return (
    <>
      {structured ? <JsonLd data={structured} /> : null}
      <p className="kicker"><Link href={`/sources/${item.source.slug}`}>{item.source.name}</Link> · {item.source.source_type}</p>
      <h1>{item.title}</h1>
      <dl className="audit">
        <dt>Published</dt><dd>{formatWhen(item.published_at)}{item.published_timezone ? ` (${item.published_timezone})` : ""}</dd>
        <dt>Observed</dt><dd>{formatWhen(item.observed_at)}</dd>
        <dt>URL</dt><dd><ExternalLink href={item.canonical_url}>{item.canonical_url}</ExternalLink></dd>
        <dt>Content hash</dt><dd className="meta">{item.content_hash}</dd>
        <dt>Reference</dt><dd>{item.content_reference}</dd>
        <dt>Status</dt><dd>{item.collection_status} · {item.availability}</dd>
      </dl>
      <h2>Participants</h2>
      <ul>
        {item.participants.map((participant) => (
          <li key={`${participant.role}-${participant.person_slug ?? participant.organization_slug}`}>
            {participant.role}: {participant.person_slug ? <Link href={`/people/${participant.person_slug}`}>{participant.display_name}</Link> : participant.organization_name}
            <span className="meta"> · {participant.attribution_method}</span>
          </li>
        ))}
      </ul>
      <h2>Evidence</h2>
      {item.evidence.map((segment) => (
        <EvidenceBlock key={segment.slug} text={segment.text} context={segment.context_text} />
      ))}
      <h2>Metadata</h2>
      <pre className="evidence">{JSON.stringify(item.metadata, null, 2)}</pre>
    </>
  );
}
