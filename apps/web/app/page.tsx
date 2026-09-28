import { getOverview } from "@pdoom/db";
import { trendKindLabel } from "@pdoom/contracts";
import Link from "next/link";
import { StatementCard } from "@/components/statement-bits";
import { TrendView } from "@/components/trend-view";
import { DensityMark } from "@/components/trends";
import { formatWhen } from "@/lib/format";
import { coverageCopy } from "@/lib/presentation";

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
  const coverage = coverageCopy(coverageInput);
  const kindLabel = overview.dataset.dataset_kind === "synthetic"
    ? "Synthetic fixture"
    : overview.dataset.dataset_kind === "live"
      ? "Live dataset"
      : "Dataset";
  const distribution = overview.trends.find((trend) => trend.slug === "extinction-by-2070-distribution");
  const volume = overview.trends.find((trend) => trend.slug === "statement-volume-by-topic-type");
  const others = overview.trends.filter((trend) => trend.slug !== distribution?.slug && trend.slug !== volume?.slug);
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
          {distribution ? <TrendView trend={distribution} /> : null}
          {volume ? <TrendView trend={volume} /> : null}
          {others.length > 0 ? (
            <section className="panel">
              <h2>Other questions</h2>
              <p>Each link is a separate question. Counts are cohort members with a comparable record.</p>
              <ul className="trend-index">
                {others.map((trend) => (
                  <li key={trend.slug}>
                    <Link href={`/trends/${trend.slug}`}>{trend.name}</Link>
                    <span className="meta">
                      {" "}
                      {trendKindLabel(trend.kind)} · <DensityMark density={trend.density} /> · {trend.contributing_person_count} of {trend.cohort_size}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {overview.trends.length === 0 && overview.dataset.dataset_id ? (
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
