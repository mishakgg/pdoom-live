import { safeExternalUrl } from "@pdoom/contracts";
import Link from "next/link";
import { formatValue, formatWhen, reviewLabel, typeLabel } from "@/lib/format";

export function TypeBadge({ type }: { type: string }) {
  return <span className={`badge ${type}`}>{typeLabel(type)}</span>;
}

export function ReviewBadge({ state }: { state: string }) {
  return <span className="badge review">{reviewLabel(state)}</span>;
}

export function ExternalLink({ href, children }: { href: string | null | undefined; children: string }) {
  const safe = safeExternalUrl(href);
  if (!safe) return <span>{children}</span>;
  return (
    <a href={safe} target="_blank" rel="noopener noreferrer nofollow">
      {children}
    </a>
  );
}

export function EvidenceBlock({ text, context }: { text: string; context?: string | null }) {
  return (
    <figure>
      <figcaption className="kicker">Evidence excerpt · untrusted source text</figcaption>
      <blockquote className="evidence">{text}</blockquote>
      {context ? <p className="meta">{context}</p> : null}
    </figure>
  );
}

export function StatementCard({
  statement,
}: {
  statement: {
    slug: string;
    statement_type: string;
    normalized_text: string;
    event_time: string | null;
    review_state: string;
    person: { slug: string; display_name: string };
    source: { name: string; source_type: string };
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
}) {
  return (
    <article className="card">
      <div className="row">
        <TypeBadge type={statement.statement_type} />
        <time className="meta" dateTime={statement.event_time ?? undefined}>
          {formatWhen(statement.event_time)}
        </time>
      </div>
      <p>
        <Link href={`/people/${statement.person.slug}`}>{statement.person.display_name}</Link>
        {" · "}
        <Link href={`/statements/${statement.slug}`}>{statement.normalized_text}</Link>
      </p>
      <p className="meta">
        {statement.source.source_type} · {statement.source.name}
        {statement.forecast?.horizon_text ? ` · ${statement.forecast.horizon_text}` : ""}
        {statement.forecast ? ` · ${formatValue(statement.forecast)}` : ""}
        {" · "}
        {statement.topics.map((topic) => topic.name).join(", ")}
        {" · "}
        {reviewLabel(statement.review_state)}
      </p>
    </article>
  );
}
