import { safeExternalUrl } from "@pdoom/contracts";
import Link from "next/link";
import { formatValue, formatWhen, phraseLabel, reviewLabel, typeLabel } from "@/lib/format";

export type StatementCardData = {
  slug: string;
  statement_type: string;
  normalized_text: string;
  event_time: string | null;
  review_state: string;
  person: { slug: string; display_name: string };
  source: { slug: string; name: string; source_type: string };
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
}: {
  statement: StatementCardData;
  headingLevel?: "h2" | "h3";
}) {
  const Heading = headingLevel;
  const topics = Array.isArray(statement.topics) ? statement.topics : [];
  return (
    <article className="card">
      <Heading className="claim">
        <Link href={`/statements/${statement.slug}`}>{statement.normalized_text}</Link>
      </Heading>
      <p className="who">
        <Link href={`/people/${statement.person.slug}`}>{statement.person.display_name}</Link>
      </p>
      <p className="card-flags">
        <TypeBadge type={statement.statement_type} />
        <ReviewBadge state={statement.review_state} />
        <time className="meta" dateTime={statement.event_time ?? undefined}>
          {formatWhen(statement.event_time)}
        </time>
      </p>
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
              <Link href={`/topics/${topic.slug}`}>{topic.name}</Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="meta">No topic recorded</p>
      )}
    </article>
  );
}
