import { getOverview } from "@pdoom/db";
import Link from "next/link";
import { StatementCard } from "@/components/statement-bits";
import { DistributionPanel, VolumePanel } from "@/components/trends";
import { formatWhen } from "@/lib/format";
import { coverageCopy, coverageTone } from "@/lib/presentation";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const overview = await getOverview();
  const coverageInput = {
    datasetKind: overview.dataset.dataset_kind,
    cohortSize: overview.dataset.coverage.cohort_size,
    statementBearingPeople: overview.dataset.coverage.statement_bearing_people,
    publicStatementCount: overview.dataset.statement_count,
    humanVerifiedStatementCount: overview.dataset.human_verified_statement_count,
  };
  const tone = coverageTone(coverageInput);
  const coverage = coverageCopy(coverageInput);
  const distribution = overview.trends.find((trend) => trend?.kind === "distribution");
  const volume = overview.trends.find((trend) => trend?.kind === "volume");
  const kindLabel = overview.dataset.dataset_kind === "synthetic"
    ? "Synthetic fixture"
    : overview.dataset.dataset_kind === "live"
      ? "Live dataset"
      : "Dataset";
  return (
    <>
      <p className="kicker">{overview.dataset.dataset_id ? kindLabel : "Observatory"}</p>
      <h1>Who said what, under which definition.</h1>
      <p className="lede">
        {overview.dataset.notice} Estimates are shown only when a person supplied a number. Qualitative views and model signals are never converted into a probability.
      </p>
      {overview.dataset.dataset_id ? (
        <section className="status-bar" aria-labelledby="dataset-status">
          <h2 id="dataset-status" className="sr-only">Dataset status</h2>
          <dl>
            <div>
              <dt>Dataset</dt>
              <dd>{kindLabel} · {overview.dataset.dataset_id}</dd>
            </div>
            <div>
              <dt>Cohort</dt>
              <dd>{overview.dataset.cohort ? `${overview.dataset.cohort.name} ${overview.dataset.cohort.version}` : "Not recorded"}</dd>
            </div>
            <div>
              <dt>Tracked people</dt>
              <dd>{overview.dataset.coverage.cohort_size}</dd>
            </div>
            <div>
              <dt>Collected statements</dt>
              <dd>{overview.dataset.statement_count}</dd>
            </div>
            <div>
              <dt>Human verified</dt>
              <dd>{overview.dataset.human_verified_statement_count}</dd>
            </div>
            <div>
              <dt>People with sources</dt>
              <dd>{overview.dataset.coverage.people_with_sources}</dd>
            </div>
            <div>
              <dt>Sources checked in 14 days</dt>
              <dd>{overview.dataset.coverage.recent_successfully_checked_sources}</dd>
            </div>
            <div>
              <dt>Stale sources</dt>
              <dd>{overview.dataset.coverage.stale_sources}</dd>
            </div>
            <div>
              <dt>Latest observation</dt>
              <dd>{formatWhen(overview.dataset.coverage.latest_item_observed_at ?? overview.dataset.latest_observed_at)}</dd>
            </div>
          </dl>
        </section>
      ) : null}
      {coverage ? (
        <section className="panel state">
          <p className="kicker">Coverage</p>
          <h2>{coverage.title}</h2>
          <p>{coverage.body}</p>
        </section>
      ) : null}
      <div className="grid-2">
        <section aria-labelledby="recent-statements">
          <div className="card-flags">
            <h2 id="recent-statements">Recent statements</h2>
            <Link href="/statements">All statements</Link>
          </div>
          {overview.recent_statements.length ? overview.recent_statements.map((statement) => (
            <StatementCard key={statement.slug} statement={statement} headingLevel="h3" />
          )) : (
            <p>No public statement is available to list.</p>
          )}
          <h2>Recorded changes</h2>
          {overview.revisions.length ? (
            <ul className="relation-list">
              {overview.revisions.map((revision) => (
                <li key={revision.to_slug}>
                  <Link href={`/people/${revision.person_slug}`}>{revision.display_name}</Link>
                  {" "}
                  {revision.relationship_type.replaceAll("_", " ")} a statement.
                  {" "}
                  <Link href={`/statements/${revision.from_slug}`}>
                    Earlier statement
                    <span className="sr-only"> by {revision.display_name}</span>
                  </Link>
                  {" → "}
                  <Link href={`/statements/${revision.to_slug}`}>
                    Later statement
                    <span className="sr-only"> by {revision.display_name}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p>No revision between collected statements is recorded.</p>
          )}
        </section>
        <div className="stack">
          {distribution && distribution.kind === "distribution" ? (
            <DistributionPanel
              name={distribution.name}
              titleId="home-distribution"
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
              titleId="home-volume"
              rows={volume.volume.rows}
              methodVersion={volume.method_version}
              contributingPersonCount={volume.volume.contributing_person_count}
              contributingStatementCount={volume.volume.contributing_statement_count}
            />
          ) : null}
          {overview.trends.length === 0 && (tone === "reported" || tone === "thin") ? (
            <section className="panel state">
              <h2>No verified trend</h2>
              <p>This dataset has no human-verified statements that meet a published trend method. Empty coverage is not a probability.</p>
            </section>
          ) : null}
        </div>
      </div>
    </>
  );
}
