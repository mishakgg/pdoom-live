import { listTrends, getTrend } from "@pdoom/db";
import { DistributionPanel, VolumePanel } from "@/components/trends";
import Link from "next/link";

export const dynamic = "force-dynamic";
export const metadata = { title: "Trends" };

export default async function TrendsPage() {
  const trends = await listTrends();
  const computed = await Promise.all(trends.map((trend) => getTrend(trend.slug)));
  return (
    <>
      <h1>Trends</h1>
      <p className="lede">Each trend names its method version, cohort, and the records it refuses to combine.</p>
      {computed.map((trend) => trend ? (
        <div key={trend.slug} className="stack" style={{ marginBottom: "1rem" }}>
          <p><Link href={`/trends/${trend.slug}`}>{trend.name}</Link></p>
          {trend.kind === "distribution" ? (
            <DistributionPanel
              name={trend.name}
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
              rows={trend.volume.rows}
              methodVersion={trend.method_version}
              contributingPersonCount={trend.volume.contributing_person_count}
              contributingStatementCount={trend.volume.contributing_statement_count}
            />
          )}
        </div>
      ) : null)}
    </>
  );
}
