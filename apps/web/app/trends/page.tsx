import { listComputedTrends } from "@pdoom/db";
import { trendKindLabel } from "@pdoom/contracts";
import { DensityMark } from "@/components/trends";
import { EmptyState } from "@/components/states";
import { formatWhen } from "@/lib/format";
import Link from "next/link";
import { canonicalOrigin, listPageFields, pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return pageMetadata(canonicalOrigin(), listPageFields("trends"));
}

const FILTERS = [
  ["all", "All questions"],
  ["summary", "Supported summary"],
  ["individual", "Individual estimates"],
  ["missing", "No comparable estimates"],
] as const;

type EvidenceFilter = (typeof FILTERS)[number][0];

function evidenceFilter(value: string | undefined): EvidenceFilter {
  if (value === "summary" || value === "individual" || value === "missing") return value;
  return "all";
}

function matches(density: string, filter: EvidenceFilter): boolean {
  if (filter === "all") return true;
  if (filter === "summary") return density === "comparable";
  if (filter === "missing") return density === "empty";
  return density === "sparse" || density === "individual" || density === "unlinked";
}

export default async function TrendsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const filter = evidenceFilter(params.evidence);
  const trends = await listComputedTrends();
  const visible = trends.filter((trend) => matches(trend.density, filter));
  return (
    <>
      <h1>Trends</h1>
      <p className="lede">
        Each row is one exact question. A supported summary is a median of included estimates, with its sample count. It is not the probability of the event. Questions with no comparable estimates stay listed.
      </p>
      <p className="meta">
        Contributing is people with an included record, out of the tracked cohort. Dataset read is when this table was read from storage. It is not a new collection.
      </p>
      {trends.length === 0 ? (
        <EmptyState title="No published trend">
          <p>No published trend method has a result in this dataset. An empty trend list is not a probability, and it is not a consensus.</p>
        </EmptyState>
      ) : (
        <>
          <nav className="segmented" aria-label="Evidence availability">
            {FILTERS.map(([value, label]) => {
              const count = trends.filter((trend) => matches(trend.density, value)).length;
              const href = value === "all" ? "/trends" : `/trends?evidence=${value}`;
              return (
                <Link key={value} href={href} aria-current={filter === value ? "page" : undefined}>
                  {label} ({count})
                </Link>
              );
            })}
          </nav>
          {visible.length === 0 ? (
            <EmptyState title="No question in this filter">
              <p>This filter hides the other questions. They are still in the dataset.</p>
              <p><Link href="/trends">Show all questions</Link></p>
            </EmptyState>
          ) : (
            <div className="chart-scroll trend-index">
              <table className="catalog-table">
                <caption className="sr-only">Questions available for comparison</caption>
                <thead>
                  <tr>
                    <th scope="col">Question</th>
                    <th scope="col">Family</th>
                    <th scope="col">Evidence</th>
                    <th scope="col">Contributing</th>
                    <th scope="col">Dataset read</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((trend) => (
                    <tr key={trend.slug}>
                      <td data-label="Question"><Link href={`/trends/${trend.slug}`}>{trend.name}</Link></td>
                      <td data-label="Family">{trendKindLabel(trend.kind)}</td>
                      <td data-label="Evidence"><DensityMark density={trend.density} /></td>
                      <td data-label="Contributing">{trend.contributing_person_count} of {trend.cohort_size}</td>
                      <td data-label="Dataset read">{formatWhen(trend.calculated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <details className="technical">
            <summary>Question identifiers</summary>
            <ul className="reference-list">
              {visible.map((trend) => (
                <li key={`${trend.slug}-key`}>
                  <Link href={`/trends/${trend.slug}`}>{trend.name}</Link>
                  <code>{trend.question_key ?? trend.exact_question_id ?? "no stored key"}</code>
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
    </>
  );
}
