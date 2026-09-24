import { getTrend } from "@pdoom/db";
import { DistributionPanel, VolumePanel } from "@/components/trends";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function TrendPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const trend = await getTrend(slug);
  if (!trend) notFound();
  return (
    <>
      <p className="kicker">Calculated {trend.calculated_at}</p>
      <h1>{trend.name}</h1>
      <p className="lede">{trend.cohort_definition}</p>
      <p className="meta">Cohort {trend.cohort_slug} version {trend.cohort_version}. Method {trend.method_version}.</p>
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
    </>
  );
}
