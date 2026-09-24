import { getStatement } from "@pdoom/db";
import { EvidenceBlock, ExternalLink, ReviewBadge, TypeBadge } from "@/components/statement-bits";
import { formatValue, formatWhen } from "@/lib/format";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function StatementPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const statement = await getStatement(slug);
  if (!statement) notFound();
  return (
    <>
      <p className="kicker">Audit record</p>
      <h1>{statement.person.display_name}</h1>
      <p>
        <TypeBadge type={statement.statement_type} /> <ReviewBadge state={statement.review_state} />
      </p>
      {statement.statement_type === "model_inferred_signal" ? (
        <p className="warning">This is a model-inferred signal. It is not a quotation and it is not this person’s probability.</p>
      ) : null}
      {statement.statement_type === "explicit_qualitative" ? (
        <p className="warning">Explicit qualitative view. No probability has been inferred from the wording.</p>
      ) : null}
      <p className="lede">{statement.normalized_text}</p>
      <dl className="audit">
        <dt>Event time</dt><dd>{formatWhen(statement.event_time)}</dd>
        <dt>Person</dt><dd><Link href={`/people/${statement.person.slug}`}>{statement.person.display_name}</Link></dd>
        <dt>Source</dt><dd><Link href={`/sources/${statement.source.slug}`}>{statement.source.name}</Link> · {statement.source.source_type}</dd>
        <dt>Source item</dt><dd><Link href={`/source-items/${statement.source_item.slug}`}>{statement.source_item.title}</Link></dd>
        <dt>Published</dt><dd>{formatWhen(statement.source_item.published_at)}</dd>
        <dt>Observed</dt><dd>{formatWhen(statement.source_item.observed_at)}</dd>
        <dt>Canonical URL</dt><dd><ExternalLink href={statement.source_item.canonical_url}>{statement.source_item.canonical_url}</ExternalLink></dd>
        <dt>Question</dt><dd>{statement.forecast?.question_text ?? "Not a structured forecast"}</dd>
        <dt>Question key</dt><dd>{statement.forecast?.question_key ?? "—"}</dd>
        <dt>Value</dt><dd>{statement.forecast ? formatValue(statement.forecast) : "—"}</dd>
        <dt>Horizon</dt><dd>{statement.forecast?.horizon_text ?? "Not stated"}</dd>
        <dt>Topics</dt><dd>{statement.topics.map((topic) => <Link key={topic.slug} href={`/topics/${topic.slug}`}>{topic.name}</Link>).reduce<React.ReactNode[]>((nodes, link, index) => nodes.concat(index ? ", " : "", link), [])}</dd>
        <dt>Extractor</dt><dd>{statement.provenance.extractor_name ?? statement.extractor_version}</dd>
        <dt>Content hash</dt><dd className="meta">{statement.provenance.content_hash}</dd>
        <dt>Evidence hash</dt><dd className="meta">{statement.evidence.segment_hash}</dd>
        <dt>Span</dt><dd>{statement.evidence.start_ms !== null ? `${statement.evidence.start_ms}–${statement.evidence.end_ms} ms` : `chars ${statement.evidence.start_char}–${statement.evidence.end_char}`}</dd>
      </dl>
      <EvidenceBlock text={statement.evidence.text} context={statement.evidence.context_text} />
      {statement.relationships.length ? (
        <section>
          <h2>Revisions and relations</h2>
          <ul>
            {statement.relationships.map((relation) => (
              <li key={`${relation.from_slug}-${relation.to_slug}-${relation.relationship_type}`}>
                {relation.relationship_type}: <Link href={`/statements/${relation.from_slug}`}>{relation.from_slug}</Link> → <Link href={`/statements/${relation.to_slug}`}>{relation.to_slug}</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  );
}
