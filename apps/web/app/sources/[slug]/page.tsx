import { isIndexableReviewState } from "@pdoom/contracts";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import { ExternalLink } from "@/components/statement-bits";
import { PartialCollectionNote } from "@/components/states";
import { formatWhen, isHumanVerified, phraseLabel, reviewLabel } from "@/lib/format";
import { loadSource } from "@/lib/loaders";
import { collectionReading, freshnessLabel, sourceMaterialState } from "@/lib/presentation";
import { requestNonce } from "@/lib/request-nonce";
import { canonicalOrigin, notFoundMetadata, pageMetadata, sourceFields } from "@/lib/seo";
import { sourceStructuredData } from "@/lib/structured-data";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const source = await loadSource(slug);
  if (!source) return notFoundMetadata();
  return pageMetadata(
    canonicalOrigin(),
    sourceFields({
      slug: source.slug,
      name: source.name,
      source_type: source.source_type,
      indexable: isIndexableReviewState(source.review_state),
    }),
  );
}

export type LoadedSource = NonNullable<Awaited<ReturnType<typeof loadSource>>>;

export function SourceRecord({ source }: { source: LoadedSource }) {
  const reading = collectionReading(source);
  return (
    <>
      <p className="kicker">{phraseLabel(source.source_type)}{source.audit_only ? " · Statement audit source" : ` · ${phraseLabel(source.collection_method)} · ${freshnessLabel(source.freshness)}`}</p>
      <h1>{source.name}</h1>
      {source.audit_only ? <p className="lede">This source container is unreviewed. Only items supporting public statements are shown for audit.</p> : source.rights_notes ? <p className="lede">{source.rights_notes}</p> : <p className="lede">No rights note is recorded for this source.</p>}
      <dl className="audit">
        <dt>Source type</dt>
        <dd>{phraseLabel(source.source_type)}</dd>
        <dt>Canonical URL</dt>
        <dd><ExternalLink href={source.canonical_url}>{source.canonical_url}</ExternalLink></dd>
        <dt>Review</dt>
        <dd>
          {reviewLabel(source.review_state)}
          {isHumanVerified(source.review_state) ? "" : " · not a settled source record"}
        </dd>
        {!source.audit_only ? (
          <>
            <dt>Last successful collection</dt>
            <dd>{formatWhen(source.last_success_at)}</dd>
            <dt>Last check</dt>
            <dd>{formatWhen(source.last_checked_at)}</dd>
            <dt>Collection reading</dt>
            <dd>{reading.label}. {reading.detail}</dd>
            <dt>Collection</dt>
            <dd>{source.enabled ? "Enabled" : "Disabled"}{source.collection_adapter ? ` · ${source.collection_adapter}` : ""}</dd>
          </>
        ) : null}
        {source.owner_slug && source.owner_name ? (
          <>
            <dt>Owner</dt>
            <dd><Link href={`/people/${source.owner_slug}`}>{source.owner_name}</Link></dd>
          </>
        ) : null}
      </dl>
      {!source.audit_only && !source.enabled ? <p className="warning">This source is disabled. Items already stored remain listed.</p> : null}
      <section aria-labelledby="source-items">
        <h2 id="source-items">Items</h2>
        {source.items.length ? source.items.map((item) => {
          const material = sourceMaterialState(item.collection_status, item.availability);
          return (
            <article className="card" key={item.slug}>
              <h3><Link href={`/source-items/${item.slug}`}>{item.title ?? "Untitled source item"}</Link></h3>
              <dl className="audit">
                <dt>Published</dt>
                <dd>{formatWhen(item.published_at)}</dd>
                <dt>Observed</dt>
                <dd>{formatWhen(item.observed_at)}</dd>
                <dt>Canonical URL</dt>
                <dd><ExternalLink href={item.canonical_url}>{item.canonical_url}</ExternalLink></dd>
              </dl>
              <p className="meta">{phraseLabel(item.collection_status)} · {phraseLabel(item.availability)}</p>
              {material === "unavailable" ? <p>Original material is not available. The catalog row is kept so the gap stays visible.</p> : null}
              {material === "partial" ? <PartialCollectionNote /> : null}
            </article>
          );
        }) : (
          <p>No item has been collected for this source. An empty item list is a collection gap, not proof the channel never published.</p>
        )}
      </section>
    </>
  );
}

export default async function SourcePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const source = await loadSource(slug);
  if (!source) notFound();
  const indexable = isIndexableReviewState(source.review_state);
  const nonce = await requestNonce();
  return (
    <>
      {indexable ? (
        <JsonLd
          nonce={nonce}
          data={sourceStructuredData({
            origin: canonicalOrigin(),
            slug: source.slug,
            name: source.name,
            source_type: source.source_type,
          })}
        />
      ) : null}
      <SourceRecord source={source} />
    </>
  );
}
