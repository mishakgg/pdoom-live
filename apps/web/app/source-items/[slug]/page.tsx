import { Breadcrumb } from "@/components/breadcrumb";
import Link from "next/link";
import { EvidenceBlock, ExternalLink } from "@/components/statement-bits";
import { JsonLd } from "@/components/json-ld";
import { PartialCollectionNote, UnavailableState } from "@/components/states";
import { formatWhen, phraseLabel } from "@/lib/format";
import { loadSourceItem, loadSourceItemDiscovery } from "@/lib/loaders";
import { sourceMaterialState } from "@/lib/presentation";
import { requestNonce } from "@/lib/request-nonce";
import { canonicalOrigin, notFoundMetadata, pageMetadata, sourceItemFields } from "@/lib/seo";
import { sourceItemStructuredData } from "@/lib/structured-data";
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
  const material = sourceMaterialState(item.collection_status, item.availability);
  const nonce = await requestNonce();
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
      {structured ? <JsonLd nonce={nonce} data={structured} /> : null}
      <Breadcrumb items={[
        { href: "/sources", label: "Sources" },
        { href: `/sources/${item.source.slug}`, label: item.source.name },
        { label: item.title ?? "Untitled source item" },
      ]} />
      <p className="kicker">{phraseLabel(item.source.source_type)}</p>
      <h1>{item.title ?? "Untitled source item"}</h1>
      {material === "unavailable" ? (
        <UnavailableState collectionStatus={item.collection_status} availability={item.availability} />
      ) : null}
      {material === "partial" ? <PartialCollectionNote /> : null}
      <p className="meta">The first time is the material&apos;s date. The second time is when this observatory stored it. Reloading this page does not collect the source again.</p>
      <dl className="audit">
        <dt>Published</dt>
        <dd>{formatWhen(item.published_at)}{item.published_timezone ? ` (${item.published_timezone})` : ""}</dd>
        <dt>Observed</dt>
        <dd>{formatWhen(item.observed_at)}</dd>
        <dt>URL</dt>
        <dd><ExternalLink href={item.canonical_url}>{item.canonical_url}</ExternalLink></dd>
        <dt>Status</dt>
        <dd>{phraseLabel(item.collection_status)} · {phraseLabel(item.availability)}</dd>
        <dt>Language</dt>
        <dd>{item.language ?? "Not recorded"}</dd>
      </dl>
      <section aria-labelledby="participants">
        <h2 id="participants">Participants</h2>
        {item.participants.length ? (
          <ul className="source-index">
            {item.participants.map((participant) => (
              <li key={`${participant.role}-${participant.person_slug ?? participant.organization_slug}`}>
                {phraseLabel(participant.role)}: {participant.person_slug ? <Link href={`/people/${participant.person_slug}`}>{participant.display_name}</Link> : participant.organization_name}
                <span className="meta"> · {phraseLabel(participant.attribution_method)} · {phraseLabel(participant.confidence_level)} confidence</span>
              </li>
            ))}
          </ul>
        ) : (
          <p>No participant is recorded for this item.</p>
        )}
      </section>
      <section aria-labelledby="item-evidence">
        <h2 id="item-evidence">Evidence</h2>
        {item.evidence.length ? item.evidence.map((segment) => (
          <EvidenceBlock key={segment.slug} text={segment.text} context={segment.context_text} prominent />
        )) : (
          <p>No evidence excerpt is stored for this item.</p>
        )}
      </section>
      <details className="technical">
        <summary>Technical record</summary>
        <dl className="audit">
          <dt>Content hash</dt>
          <dd className="hash">{item.content_hash}</dd>
          <dt>Reference</dt>
          <dd className="url">{item.content_reference ?? "Not recorded"}</dd>
        </dl>
        <h2 id="item-metadata">Metadata</h2>
        <pre className="evidence">{JSON.stringify(item.metadata, null, 2)}</pre>
      </details>
    </>
  );
}
