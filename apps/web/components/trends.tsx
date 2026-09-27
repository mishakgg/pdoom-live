import Link from "next/link";
import { countLabel, formatProbability, phraseLabel, typeLabel } from "@/lib/format";

type Included = {
  statement_slug: string;
  display_name: string;
  person_slug: string;
  value_numeric: number;
  event_time: string | null;
};

export function DistributionPanel({
  name,
  methodVersion,
  cohortDefinition,
  included,
  median,
  minimum,
  maximum,
  contributingPersonCount,
  contributingStatementCount,
  coverage,
  exclusions,
  titleId = "distribution-title",
  showTitle = true,
  detailHref,
}: {
  name: string;
  methodVersion: string;
  cohortDefinition: string;
  included: Included[];
  median: number | null;
  minimum: number | null;
  maximum: number | null;
  contributingPersonCount: number;
  contributingStatementCount: number;
  coverage: { cohort_size: number; cohort_members_without_included_estimate: number; missingness_note: string };
  exclusions: Array<{ statement_slug: string; reason: string }>;
  titleId?: string;
  showTitle?: boolean;
  detailHref?: string;
}) {
  const max = Math.max(...included.map((item) => item.value_numeric), 0.01);
  const summaryId = `${titleId}-summary`;
  const listed = included.length
    ? included.map((item) => `${item.display_name} ${formatProbability(item.value_numeric)}`).join(", ")
    : "none";
  return (
    <section className="panel" aria-labelledby={showTitle ? titleId : undefined} aria-label={showTitle ? undefined : name}>
      <p className="kicker">Comparable explicit estimates</p>
      {showTitle ? <h2 id={titleId}>{name}</h2> : null}
      <p className="meta">
        Method {methodVersion}. {countLabel(contributingPersonCount, "person", "people")} and {countLabel(contributingStatementCount, "statement")}. Cohort size {coverage.cohort_size}. {coverage.cohort_members_without_included_estimate === 1 ? "1 member has" : `${coverage.cohort_members_without_included_estimate} members have`} no included estimate.
      </p>
      <p>{cohortDefinition}</p>
      <p className="median" id={summaryId}>
        Median of included point estimates: {formatProbability(median)}. Range {formatProbability(minimum)}–{formatProbability(maximum)}. This is not a field consensus.
      </p>
      <p className="sr-only">Included point estimates: {listed}. The longest bar is the largest included estimate.</p>
      {included.length ? (
        <div className="table-scroll">
          <table className="dist" aria-describedby={summaryId}>
            <caption className="kicker">Included point estimates only. Scale bars compare them with the largest included value.</caption>
            <thead>
              <tr>
                <th scope="col">Person</th>
                <th scope="col">Estimate</th>
                <th scope="col">Compared with largest</th>
              </tr>
            </thead>
            <tbody>
              {included.map((item) => (
                <tr key={item.statement_slug}>
                  <th scope="row">
                    <Link href={`/people/${item.person_slug}`}>{item.display_name}</Link>
                  </th>
                  <td>
                    <Link href={`/statements/${item.statement_slug}`}>{formatProbability(item.value_numeric)}</Link>
                  </td>
                  <td>
                    <div className="bar" aria-hidden="true" style={{ width: `${(item.value_numeric / max) * 100}%` }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No point estimates are included.</p>
      )}
      <details>
        <summary>{countLabel(exclusions.length, "excluded record")}</summary>
        {exclusions.length ? (
          <ul>
            {exclusions.map((item) => (
              <li key={`${item.statement_slug}-${item.reason}`}>
                <Link href={`/statements/${item.statement_slug}`}>{item.statement_slug}</Link> · {phraseLabel(item.reason)}
              </li>
            ))}
          </ul>
        ) : (
          <p>No records were excluded.</p>
        )}
      </details>
      <p className="meta">{coverage.missingness_note}</p>
      {detailHref ? <p><Link href={detailHref}>Open this trend</Link></p> : null}
    </section>
  );
}

export function VolumePanel({
  rows,
  methodVersion,
  contributingStatementCount,
  contributingPersonCount,
  titleId = "volume-title",
  showTitle = true,
  expanded = false,
  detailHref,
}: {
  rows: Array<{ bucket: string | null; topic_slug: string; statement_type: string; statement_count: number; person_count?: number }>;
  methodVersion: string;
  contributingStatementCount: number;
  contributingPersonCount: number;
  titleId?: string;
  showTitle?: boolean;
  expanded?: boolean;
  detailHref?: string;
}) {
  const totals = new Map<string, number>();
  for (const row of rows) {
    totals.set(row.statement_type, (totals.get(row.statement_type) ?? 0) + row.statement_count);
  }
  const summary = [...totals.entries()].map(([type, count]) => `${typeLabel(type)} ${count}`).join(", ") || "none";
  return (
    <section className="panel" aria-labelledby={showTitle ? titleId : undefined} aria-label={showTitle ? undefined : "Statements by type"}>
      <p className="kicker">Volume, not a probability</p>
      {showTitle ? <h2 id={titleId}>Statements by type</h2> : <h2 id={titleId} className="sr-only">Statements by type</h2>}
      <p className="meta">
        Method {methodVersion}. {countLabel(contributingStatementCount, "statement")} from {countLabel(contributingPersonCount, "person", "people")}. Counts stay split by statement class.
      </p>
      <p className="sr-only">Class totals: {summary}.</p>
      {totals.size ? (
        <ul className="volume" aria-label="Statement counts by class">
          {[...totals.entries()].map(([type, count]) => (
            <li key={type}>
              <span>{typeLabel(type)}</span>
              <div className="bar" data-class={type} aria-hidden="true" style={{ width: `${Math.min(100, count * 8)}%` }} />
              <span>{count}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p>No statements are included in this count.</p>
      )}
      <details open={expanded}>
        <summary>Topic and quarter counts</summary>
        {rows.length ? (
          <div className="table-scroll">
            <table className="dist">
              <caption className="kicker">Counts stay split by topic, quarter, and statement class. They are not averaged.</caption>
              <thead>
                <tr>
                  <th scope="col">Quarter</th>
                  <th scope="col">Topic</th>
                  <th scope="col">Class</th>
                  <th scope="col">Statements</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={`${row.bucket ?? "unknown"}-${row.topic_slug}-${row.statement_type}`}>
                    <td>{row.bucket ?? "Time unknown"}</td>
                    <td className="hash">{row.topic_slug}</td>
                    <td>{typeLabel(row.statement_type)}</td>
                    <td>{row.statement_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No topic rows are included.</p>
        )}
      </details>
      {detailHref ? <p><Link href={detailHref}>Open this trend</Link></p> : null}
    </section>
  );
}
