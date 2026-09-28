import { getTrend } from "@pdoom/db";
import { trendKindLabel } from "@pdoom/contracts";
import { TrendView } from "@/components/trend-view";
import { formatWhen } from "@/lib/format";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function TrendPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const trend = await getTrend(slug);
  if (!trend) notFound();
  return (
    <>
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
