import { getOverview } from "@pdoom/db";
import Link from "next/link";
import { StatementCard } from "@/components/statement-bits";
import { DistributionPanel, VolumePanel } from "@/components/trends";
import { formatWhen } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const overview = await getOverview();
  const distribution = overview.trends.find((trend) => trend?.kind === "distribution");
  const volume = overview.trends.find((trend) => trend?.kind === "volume");
  return (
    <>
      <p className="fresh">
        {overview.dataset.dataset_kind === "synthetic" ? (
          <span><strong>Synthetic fixture</strong> · {overview.dataset.dataset_id}</span>
        ) : (
          <span><strong>Live dataset</strong> · {overview.dataset.dataset_id} · {overview.dataset.schema_version}</span>
        )}
        <span>Cohort {overview.dataset.cohort?.name} {overview.dataset.cohort?.version}</span>
        <span>{overview.dataset.coverage.cohort_size} tracked people</span>
        <span>{overview.dataset.statement_count} public statements</span>
        <span>{overview.dataset.coverage.people_with_sources} people with sources</span>
        <span>{overview.dataset.coverage.recent_successfully_checked_sources} sources checked in the last 14 days</span>
        <span>{overview.dataset.coverage.stale_sources} stale sources</span>
        <span>Latest observation {formatWhen(overview.dataset.coverage.latest_item_observed_at ?? overview.dataset.latest_observed_at)}</span>
      </p>
      <h1>Who said what, under which definition.</h1>
      <p className="lede">
        {overview.dataset.notice} Estimates are shown only when a person supplied a number. Qualitative views and model signals are never converted into a probability.
      </p>
      <div className="grid-2">
        <section>
          <div className="row">
            <h2>Recent statements</h2>
            <Link href="/statements">All statements</Link>
          </div>
          {overview.recent_statements.map((statement) => (
            <StatementCard key={statement.slug} statement={statement} />
          ))}
          <h2>Recorded changes</h2>
          <ul>
            {overview.revisions.map((revision) => (
              <li key={revision.to_slug}>
                <Link href={`/people/${revision.person_slug}`}>{revision.display_name}</Link>{" "}
                {revision.relationship_type} a statement ·{" "}
                <Link href={`/statements/${revision.from_slug}`}>earlier</Link> →{" "}
                <Link href={`/statements/${revision.to_slug}`}>later</Link>
              </li>
            ))}
          </ul>
        </section>
        <div className="stack">
          {distribution && distribution.kind === "distribution" ? (
            <DistributionPanel
              name={distribution.name}
              methodVersion={distribution.method_version}
              cohortDefinition={distribution.cohort_definition}
              included={distribution.distribution.included}
              median={distribution.distribution.median}
              minimum={distribution.distribution.minimum}
              maximum={distribution.distribution.maximum}
              contributingPersonCount={distribution.distribution.contributing_person_count}
              contributingStatementCount={distribution.distribution.contributing_statement_count}
              coverage={distribution.distribution.coverage}
              exclusions={distribution.distribution.exclusions}
            />
          ) : null}
          {volume && volume.kind === "volume" ? (
            <VolumePanel
              rows={volume.volume.rows}
              methodVersion={volume.method_version}
              contributingPersonCount={volume.volume.contributing_person_count}
              contributingStatementCount={volume.volume.contributing_statement_count}
            />
          ) : null}
          {overview.trends.length === 0 ? (
            <section className="panel">
              <h2>No verified trend</h2>
              <p>This dataset has no human-verified statements that meet a published trend method. Empty coverage is not a probability.</p>
            </section>
          ) : null}
        </div>
      </div>
    </>
  );
}
