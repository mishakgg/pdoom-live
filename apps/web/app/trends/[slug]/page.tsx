import { DistributionPanel, VolumePanel } from "@/components/trends";
import { formatWhen } from "@/lib/format";
import { loadTrend } from "@/lib/loaders";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const trend = await loadTrend(slug);
  return { title: trend?.name ?? "Trend" };
}

export default async function TrendPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const trend = await loadTrend(slug);
  if (!trend) notFound();
  return (
    <>
      <p className="kicker">Calculated {formatWhen(trend.calculated_at)}</p>
      <h1 id="trend-title">{trend.name}</h1>
      <p className="lede">{trend.cohort_definition}</p>
      <p className="meta">Cohort {trend.cohort_slug} version {trend.cohort_version}. Method {trend.method_version}.</p>
      {trend.kind === "distribution" ? (
        <DistributionPanel
          name={trend.name}
          titleId="trend-title"
          showTitle={false}
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
          titleId="trend-volume"
          expanded
          rows={trend.volume.rows}
          methodVersion={trend.method_version}
          contributingPersonCount={trend.volume.contributing_person_count}
          contributingStatementCount={trend.volume.contributing_statement_count}
        />
      )}
    </>
  );
}
