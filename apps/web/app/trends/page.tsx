import { listComputedTrends } from "@pdoom/db";
import { trendKindLabel } from "@pdoom/contracts";
import { DensityMark } from "@/components/trends";
import Link from "next/link";

export const dynamic = "force-dynamic";
export const metadata = { title: "Trends" };

const GROUPS = ["distribution", "timeline", "quantity", "revision", "volume"] as const;

export default async function TrendsPage() {
  const trends = await listComputedTrends();
  return (
    <>
      <h1>Trends</h1>
      <p className="lede">
        Each link is one question key, one unit, and one method version. Similar topics stay in separate sections. Open a question to see the individual estimates, the table, and why other records were left out. A small number of estimates stays inspectable, and an empty section stays empty.
      </p>
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
    </>
  );
}
