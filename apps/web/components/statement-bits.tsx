import { safeExternalUrl } from "@pdoom/contracts";
import Link from "next/link";
import { formatValue, formatWhen, phraseLabel, reviewLabel, typeLabel } from "@/lib/format";
import { personResearchHref, timeRelation, topicResearchHref, type ResearchFilters } from "@/lib/presentation";

export type StatementCardData = {
  slug: string;
  statement_type: string;
  normalized_text: string;
  event_time: string | null;
  review_state: string;
  person: { slug: string; display_name: string };
  source: { slug: string; name: string; source_type: string };
  source_item?: {
    published_at?: string | null;
    observed_at?: string | null;
  } | null;
  forecast: {
    value_type?: string | null;
    value_numeric?: number | null;
    value_min?: number | null;
    value_max?: number | null;
    unit?: string | null;
    horizon_text?: string | null;
    question_key?: string | null;
  } | null;
  topics: Array<{ slug: string; name: string }>;
};

export function TypeBadge({ type }: { type: string }) {
  return <span className={`badge ${type}`}>{typeLabel(type)}</span>;
}

export function ReviewBadge({ state }: { state: string }) {
  return <span className={`badge review ${state}`}>{reviewLabel(state)}</span>;
}

export function ExternalLink({ href, children }: { href: string | null | undefined; children: string }) {
  const safe = safeExternalUrl(href);
  if (!safe) return <span className="url">{children}</span>;
  return (
    <a className="external" href={safe} target="_blank" rel="noopener noreferrer nofollow">
      <span className="url">{children}</span>
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

export function EvidenceBlock({
  text,
  context,
  prominent = false,
}: {
  text: string;
  context?: string | null;
  prominent?: boolean;
}) {
  return (
    <figure className={prominent ? "evidence-figure prominent" : "evidence-figure"}>
      <figcaption className="kicker">Evidence excerpt · untrusted source text</figcaption>
      <blockquote className="evidence">{text}</blockquote>
      {context ? <p className="meta">Surrounding context: {context}</p> : null}
    </figure>
  );
}

export function StatementCard({
  statement,
  headingLevel = "h2",
  filters,
}: {
  statement: StatementCardData;
  headingLevel?: "h2" | "h3";
  filters?: ResearchFilters;
}) {
  const Heading = headingLevel;
  const typeClass = statement.statement_type === "explicit_numeric"
    || statement.statement_type === "explicit_qualitative"
    || statement.statement_type === "model_inferred_signal"
    ? ` type-${statement.statement_type}`
    : "";
  const topics = Array.isArray(statement.topics) ? statement.topics : [];
  const research = filters ?? {};
  const sourceItem = statement.source_item;
  const hasPublished = sourceItem != null && "published_at" in sourceItem;
  const hasObserved = sourceItem != null && "observed_at" in sourceItem;
  const relation = hasPublished && hasObserved
    ? timeRelation({
        published_at: sourceItem?.published_at,
        observed_at: sourceItem?.observed_at,
      })
    : null;
  return (
    <article className={`card statement-card${typeClass}`}>
      <Heading className="claim">
        <Link href={`/statements/${statement.slug}`}>{statement.normalized_text}</Link>
      </Heading>
      <p className="who">
        <Link href={personResearchHref(statement.person.slug, research)}>{statement.person.display_name}</Link>
      </p>
      <p className="card-flags">
        <TypeBadge type={statement.statement_type} />
        <ReviewBadge state={statement.review_state} />
        <time className="meta" dateTime={statement.event_time ?? undefined}>
          Event {formatWhen(statement.event_time)}
        </time>
      </p>
      {hasPublished || hasObserved ? (
        <p className="meta">
          {hasPublished ? `Published ${formatWhen(sourceItem?.published_at)}` : ""}
          {hasPublished && hasObserved ? " · " : ""}
          {hasObserved ? `Observed ${formatWhen(sourceItem?.observed_at)}` : ""}
          {relation ? ` · ${relation.label}` : ""}
        </p>
      ) : null}
      <p className="meta">
        <Link href={`/sources/${statement.source.slug}`}>{statement.source.name}</Link>
        {" · "}
        {phraseLabel(statement.source.source_type)}
        {statement.forecast?.horizon_text ? ` · Horizon ${statement.forecast.horizon_text}` : ""}
        {statement.forecast ? ` · ${formatValue(statement.forecast)}` : ""}
      </p>
      {topics.length ? (
        <ul className="chips" aria-label="Topics">
          {topics.map((topic) => (
            <li key={topic.slug}>
              <Link href={topicResearchHref(topic.slug, research)}>{topic.name}</Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="meta">No topic recorded</p>
      )}
    </article>
  );
}
