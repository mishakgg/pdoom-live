import { listComputedTrends } from "@pdoom/db";
import { trendKindLabel } from "@pdoom/contracts";
import { DensityMark } from "@/components/trends";
import { EmptyState } from "@/components/states";
import Link from "next/link";
import { canonicalOrigin, listPageFields, pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return pageMetadata(canonicalOrigin(), listPageFields("trends"));
}

const GROUPS = ["distribution", "timeline", "quantity", "qualitative", "revision", "inspection", "volume"] as const;

export default async function TrendsPage() {
  const trends = await listComputedTrends();
  return (
    <>
      <h1>Trends</h1>
      <p className="lede">
        Each link is one exact question: one outcome, one deadline or predicted value, one unit, and one condition. A broad family key is not itself a comparison. Open a question to see who is included, which records were left out, and the evidence. A small number of estimates stays inspectable, and an empty section stays empty. Qualitative statements stay in their own section. A cross-person median summarizes included statements. It is not automatically the probability of an event.
      </p>
      {trends.length === 0 ? (
        <EmptyState title="No published trend">
          <p>No published trend method has a result in this dataset. An empty trend list is not a probability, and it is not a consensus.</p>
        </EmptyState>
      ) : (
        <nav aria-label="Trend sections">
          <ul className="trend-index">
            {GROUPS.map((kind) => {
              const group = trends.filter((trend) => trend.kind === kind);
              if (group.length === 0) return null;
              return (
                <li key={kind}>
                  <p className="kicker">{trendKindLabel(kind)}</p>
                  <ul>
                    {group.map((trend) => (
                      <li key={trend.slug}>
                        <Link href={`/trends/${trend.slug}`}>{trend.name}</Link>
                        {" · "}
                        <DensityMark density={trend.density} />
                        {" · "}
                        {trend.contributing_person_count} of {trend.cohort_size} cohort members
                        {trend.question_key ? ` · ${trend.question_key}` : ""}
                      </li>
                    ))}
                  </ul>
                </li>
              );
            })}
          </ul>
        </nav>
      )}
    </>
  );
}
