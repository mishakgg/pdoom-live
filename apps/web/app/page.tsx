import { trendKindLabel } from "@pdoom/contracts";
import { getOverview, listTopics } from "@pdoom/db";
import Link from "next/link";
import { DatasetWatch } from "@/components/dataset-watch";
import { JsonLd } from "@/components/json-ld";
import { StatementCard } from "@/components/statement-bits";
import { TrendView } from "@/components/trend-view";
import { DensityMark } from "@/components/trends";
import { countLabel, formatWhen } from "@/lib/format";
import { coverageCopy, datasetFingerprint, revisionReading, selectCoveredTopics, selectFeaturedQuestion } from "@/lib/presentation";
import { requestNonce } from "@/lib/request-nonce";
import { canonicalOrigin, listPageFields, pageMetadata } from "@/lib/seo";
import { datasetStructuredData, websiteStructuredData } from "@/lib/structured-data";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return pageMetadata(canonicalOrigin(), listPageFields("home"));
}

export default async function HomePage() {
  const [overview, topics] = await Promise.all([getOverview(), listTopics()]);
  const origin = canonicalOrigin();
  const nonce = await requestNonce();
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
  const { featured, others } = selectFeaturedQuestion(overview.trends);
  const coveredTopics = selectCoveredTopics(topics);
  const fingerprint = datasetFingerprint({
    imported_at: overview.dataset.imported_at,
    statement_count: overview.dataset.statement_count,
    latest_observed_at: overview.dataset.latest_observed_at,
    latest_published_at: overview.dataset.latest_published_at,
    latest_successful_observation: overview.dataset.coverage.latest_successful_observation,
    stale_sources: overview.dataset.coverage.stale_sources,
    failing_sources: overview.dataset.coverage.unavailable_or_failing_sources,
  });
  const freshness = overview.dataset.coverage.freshness;
  return (
    <>
      <JsonLd nonce={nonce} data={websiteStructuredData(origin)} />
      <JsonLd
        nonce={nonce}
        data={datasetStructuredData({
          origin,
          datasetKind: overview.dataset.dataset_kind,
          notice: overview.dataset.notice,
          cohortName: overview.dataset.cohort?.name ?? null,
        })}
      />
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
              <dt>Latest publication</dt>
              <dd>{formatWhen(overview.dataset.latest_published_at)}</dd>
            </div>
            <div>
              <dt>Latest observation</dt>
              <dd>{formatWhen(overview.dataset.coverage.latest_item_observed_at ?? overview.dataset.latest_observed_at)}</dd>
            </div>
            <div>
              <dt>Last successful collection</dt>
              <dd>{formatWhen(overview.dataset.coverage.latest_successful_observation)}</dd>
            </div>
            <div>
              <dt>Dataset updated</dt>
              <dd>{formatWhen(overview.dataset.imported_at)}</dd>
            </div>
            <div>
              <dt>Collection states</dt>
              <dd>
                {freshness.current} current · {freshness.aging} aging · {freshness.stale} stale · {freshness.never_checked} never checked · {overview.dataset.coverage.unavailable_or_failing_sources} failing or unavailable
              </dd>
            </div>
          </dl>
          <p className="meta">
            Publication time, observation time, last successful collection, and dataset update are different clocks.
            A stale, unknown, partial, or failed source stays labeled on its own page.
            Reloading this page reads the stored dataset. It does not collect sources again.
          </p>
        </section>
      ) : null}
      <DatasetWatch fingerprint={fingerprint} />
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
            <h2 id="recent-statements">Newest statements by event time</h2>
            <Link href="/statements">All statements</Link>
          </div>
          <p className="meta">Ordered by event time, not by when a source was collected and not by publication time. Each row keeps those clocks separate.</p>
          {overview.recent_statements.length ? overview.recent_statements.map((statement) => (
            <StatementCard key={statement.slug} statement={statement} headingLevel="h3" />
          )) : (
            <p>No public statement is available to list.</p>
          )}
          <h2>Recorded changes</h2>
          <p className="meta">A recorded link is not a new collection and not newly published material. It is a relationship between two stored statements.</p>
          {overview.revisions.length ? (
            <ul className="relation-list">
              {overview.revisions.map((revision) => {
                const reading = revisionReading(revision.relationship_type);
                return (
                  <li key={revision.to_slug}>
                    <p>
                      <strong>{reading.title}.</strong> {reading.note}
                    </p>
                    <p>
                      <Link href={`/people/${revision.person_slug}`}>{revision.display_name}</Link>
                      {" · "}
                      <Link href={`/statements/${revision.from_slug}`}>
                        Earlier statement
                        <span className="sr-only"> by {revision.display_name}</span>
                      </Link>
                      {" → "}
                      <Link href={`/statements/${revision.to_slug}`}>
                        Later statement
                        <span className="sr-only"> by {revision.display_name}</span>
                      </Link>
                    </p>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p>No revision between collected statements is recorded.</p>
          )}
        </section>
        <div className="stack">
          <section className="panel" aria-labelledby="covered-questions">
            <h2 id="covered-questions">Covered questions</h2>
            <p>Ordered by how many public statements use the definition, then by name. This is coverage in the loaded dataset. It is not importance and not a probability.</p>
            {coveredTopics.length ? (
              <ul className="trend-index">
                {coveredTopics.map((topic) => (
                  <li key={topic.slug}>
                    <Link href={`/topics/${topic.slug}`}>{topic.name}</Link>
                    <span className="meta"> {countLabel(topic.statement_total, "statement")}</span>
                    <p>{topic.definition}</p>
                    <p><Link href={`/statements?topic=${topic.slug}`}>All statements on this question</Link></p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No question has a collected statement.</p>
            )}
          </section>
          {featured ? (
            <>
              <p className="meta">
                The question below has the widest comparable coverage: cohort members with a record, then statement count.
                Volume is listed with the other questions because it counts records. It is not a belief.
              </p>
              <TrendView trend={featured} />
            </>
          ) : null}
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
