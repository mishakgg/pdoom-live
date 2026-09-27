import { JsonLd } from "@/components/json-ld";
import { DistributionPanel, VolumePanel } from "@/components/trends";
import { loadTrend } from "@/lib/loaders";
import { canonicalOrigin, notFoundMetadata, pageMetadata, trendFields } from "@/lib/seo";
import { trendStructuredData } from "@/lib/structured-data";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const trend = await loadTrend(slug);
  if (!trend) return notFoundMetadata();
  return pageMetadata(
    canonicalOrigin(),
    trendFields({
      slug: trend.slug,
      name: trend.name,
      method_version: trend.method_version,
      cohort_version: trend.cohort_version,
    }),
  );
}

export default async function TrendPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const trend = await loadTrend(slug);
  if (!trend) notFound();
  return (
    <>
      <JsonLd
        data={trendStructuredData({
          origin: canonicalOrigin(),
          slug: trend.slug,
          name: trend.name,
          method_version: trend.method_version,
          cohort_definition: trend.cohort_definition,
        })}
      />
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
