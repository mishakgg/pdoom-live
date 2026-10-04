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
        Read from the current corpus at {formatWhen(trend.calculated_at)}. This time is not a historical reconstruction.
      </p>
      <h1>{trend.name}</h1>
      <p className="lede">{trend.cohort_definition}</p>
      <p className="meta">
        Cohort {trend.cohort_slug} version {trend.cohort_version}. Method {trend.method_version}. Pooling rules {trend.comparability_policy_version}.
        {trend.history.presented_as_reconstruction ? " Inputs were filtered by statement date, observation time, and review time." : " Statement dates alone were not treated as a reconstruction."}
        {trend.source === "prepared_method" ? " Prepared method for this exact question." : ""}
        {trend.source === "discovered_question" && trend.kind !== "qualitative" && trend.kind !== "inspection" ? " Opened from stored forecasts that agree on one exact question." : ""}
        {trend.kind === "qualitative" ? " Qualitative statements. No probability is inferred from the wording." : ""}
        {trend.kind === "inspection" ? " These records were not pooled." : ""}
        {trend.source === "published_definition" ? " The published definition keeps its stored method version." : ""}
      </p>
      <TrendView trend={trend} />
    </>
  );
}
