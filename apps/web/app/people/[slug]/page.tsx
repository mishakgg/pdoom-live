import { getPerson } from "@pdoom/db";
import { ExternalLink, StatementCard } from "@/components/statement-bits";
import { formatWhen } from "@/lib/format";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const person = await getPerson(slug);
  return { title: person?.display_name ?? "Person" };
}

export default async function PersonPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const person = await getPerson(slug);
  if (!person) notFound();
  return (
    <>
      <p className="kicker">{person.status} · record updated {formatWhen(person.updated_at)}</p>
      <h1>{person.display_name}</h1>
      <p className="lede">{person.bio_short}</p>
      <section className="panel">
        <h2>Why this record exists</h2>
        <p>{person.inclusion_reason}</p>
        <p className="meta">Tags: {person.cohort_tags.join(", ") || "none"}</p>
      </section>
      <div className="grid-2">
        <section>
          <h2>Affiliations</h2>
          <ul>
            {person.affiliations.map((affiliation) => (
              <li key={`${affiliation.organization.slug}-${affiliation.start_date}`}>
                {affiliation.role} · {affiliation.organization.name} · {affiliation.start_date ?? "unknown"}–{affiliation.end_date ?? "present"}
              </li>
            ))}
          </ul>
          <h2>Public identities</h2>
          <ul>
            {person.identities.map((identity) => (
              <li key={`${identity.namespace}-${identity.external_id}`}>
                {identity.namespace}: <ExternalLink href={identity.canonical_url}>{identity.handle ?? identity.external_id}</ExternalLink>
                <span className="meta"> · {identity.verification_method}</span>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h2>Timeline</h2>
          <div className="timeline">
            {person.statements.map((statement) => (
              <StatementCard key={statement.slug} statement={statement} />
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
