import { trendKindLabel } from "@pdoom/contracts";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import { TrendView } from "@/components/trend-view";
import { formatWhen } from "@/lib/format";
import { loadTrend } from "@/lib/loaders";
import { requestNonce } from "@/lib/request-nonce";
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
  const nonce = await requestNonce();
  return (
    <>
      <JsonLd
        nonce={nonce}
        data={trendStructuredData({
          origin: canonicalOrigin(),
          slug: trend.slug,
          name: trend.name,
          method_version: trend.method_version,
          cohort_definition: trend.cohort_definition,
        })}
      />
      <p className="kicker">
        <Link href="/trends">Trends</Link>
        {" · "}
        {trendKindLabel(trend.kind)}
        {" · "}
        Calculated {formatWhen(trend.calculated_at)}
      </p>
      <h1>{trend.name}</h1>
      <p className="lede">{trend.cohort_definition}</p>
      <p className="meta">
        Cohort {trend.cohort_slug} version {trend.cohort_version}. Method {trend.method_version}.
        {trend.source === "prepared_method" ? " Prepared method for this question key." : ""}
        {trend.source === "discovered_question" ? " Opened from a stored question key that has a human-verified numeric forecast." : ""}
        {trend.source === "published_definition" ? " Published with the loaded dataset." : ""}
      </p>
      <TrendView trend={trend} />
    </>
  );
}
