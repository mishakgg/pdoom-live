import { getSourceItem } from "@pdoom/db";
import { EvidenceBlock, ExternalLink } from "@/components/statement-bits";
import { formatWhen } from "@/lib/format";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function SourceItemPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = await getSourceItem(slug);
  if (!item) notFound();
  return (
    <>
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
