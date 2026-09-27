import Link from "next/link";
import { EvidenceBlock, ExternalLink } from "@/components/statement-bits";
import { PartialCollectionNote, UnavailableState } from "@/components/states";
import { formatWhen, phraseLabel } from "@/lib/format";
import { loadSourceItem } from "@/lib/loaders";
import { documentTitle, sourceMaterialState } from "@/lib/presentation";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = await loadSourceItem(slug);
  if (!item) return { title: "Source item" };
  return { title: documentTitle(item.source.name, item.title ?? "Untitled source item") };
}

export default async function SourceItemPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = await loadSourceItem(slug);
  if (!item) notFound();
  const material = sourceMaterialState(item.collection_status, item.availability);
  return (
    <>
      <p className="kicker">
        <Link href={`/sources/${item.source.slug}`}>{item.source.name}</Link>
        {" · "}
        {phraseLabel(item.source.source_type)}
      </p>
      <h1>{item.title ?? "Untitled source item"}</h1>
      {material === "unavailable" ? (
        <UnavailableState collectionStatus={item.collection_status} availability={item.availability} />
      ) : null}
      {material === "partial" ? <PartialCollectionNote /> : null}
      <dl className="audit">
        <dt>Published</dt>
        <dd>{formatWhen(item.published_at)}{item.published_timezone ? ` (${item.published_timezone})` : ""}</dd>
        <dt>Observed</dt>
        <dd>{formatWhen(item.observed_at)}</dd>
        <dt>URL</dt>
        <dd><ExternalLink href={item.canonical_url}>{item.canonical_url}</ExternalLink></dd>
        <dt>Content hash</dt>
        <dd className="hash">{item.content_hash}</dd>
        <dt>Reference</dt>
        <dd className="url">{item.content_reference ?? "Not recorded"}</dd>
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
      <section aria-labelledby="item-metadata">
        <h2 id="item-metadata">Metadata</h2>
        <pre className="evidence">{JSON.stringify(item.metadata, null, 2)}</pre>
      </section>
    </>
  );
}
