import { getTrend, listTrends } from "@pdoom/db";
import { EmptyState } from "@/components/states";
import { DistributionPanel, VolumePanel } from "@/components/trends";

export const dynamic = "force-dynamic";
export const metadata = { title: "Trends" };

export default async function TrendsPage() {
  const trends = await listTrends();
  const computed = await Promise.all(trends.map((trend) => getTrend(trend.slug)));
  const visible = computed.filter((trend) => trend !== null);
  return (
    <>
      <h1>Trends</h1>
      <p className="lede">Each trend names its method version, cohort, and the records it refuses to combine. A chart is a summary of those records, not a field consensus.</p>
      {visible.length ? visible.map((trend) => trend ? (
        <div key={trend.slug} className="stack" style={{ marginBottom: "1.2rem" }}>
          {trend.kind === "distribution" ? (
            <DistributionPanel
              name={trend.name}
              titleId={`${trend.slug}-title`}
              detailHref={`/trends/${trend.slug}`}
              methodVersion={trend.method_version}
              cohortDefinition={trend.cohort_definition}
              included={trend.distribution.included}
              median={trend.distribution.median}
              minimum={trend.distribution.minimum}
              maximum={trend.distribution.maximum}
              contributingPersonCount={trend.distribution.contributing_person_count}
              contributingStatementCount={trend.distribution.contributing_statement_count}
              coverage={trend.distribution.coverage}
              exclusions={trend.distribution.exclusions}
            />
          ) : (
            <VolumePanel
              titleId={`${trend.slug}-title`}
              detailHref={`/trends/${trend.slug}`}
              expanded
              rows={trend.volume.rows}
              methodVersion={trend.method_version}
              contributingPersonCount={trend.volume.contributing_person_count}
              contributingStatementCount={trend.volume.contributing_statement_count}
            />
          )}
        </div>
      ) : null) : (
        <EmptyState title="No published trend">
          <p>No published trend method has a result in this dataset. An empty trend list is not a probability, and it is not a consensus.</p>
        </EmptyState>
      )}
    </>
  );
}
