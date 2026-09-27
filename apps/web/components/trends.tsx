import Link from "next/link";
import { formatProbability } from "@/lib/format";

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
}) {
  const max = Math.max(...included.map((item) => item.value_numeric), 0.01);
  return (
    <section className="panel" aria-labelledby="dist-title">
      <p className="kicker">Comparable explicit estimates</p>
      <h2 id="dist-title">{name}</h2>
      <p className="meta">
        Method {methodVersion}. {contributingPersonCount} people, {contributingStatementCount} statements. Cohort size {coverage.cohort_size}. {coverage.cohort_members_without_included_estimate} members have no included estimate.
      </p>
      <p>{cohortDefinition}</p>
      <p className="median">
        Median of included point estimates: {formatProbability(median)}. Range {formatProbability(minimum)}–{formatProbability(maximum)}. This is not a field consensus.
      </p>
      <div className="dist-scroll">
      <table className="dist">
        <caption className="kicker">Included point estimates only</caption>
        <thead>
          <tr>
            <th>Person</th>
            <th>Estimate</th>
            <th>Scale</th>
          </tr>
        </thead>
        <tbody>
          {included.map((item) => (
            <tr key={item.statement_slug}>
              <td>
                <Link href={`/people/${item.person_slug}`}>{item.display_name}</Link>
              </td>
              <td>
                <Link href={`/statements/${item.statement_slug}`}>{formatProbability(item.value_numeric)}</Link>
              </td>
              <td>
                <div className="bar" style={{ width: `${(item.value_numeric / max) * 100}%` }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <details>
        <summary>{exclusions.length} excluded records</summary>
        <ul>
          {exclusions.map((item) => (
            <li key={`${item.statement_slug}-${item.reason}`}>
              <Link href={`/statements/${item.statement_slug}`}>{item.statement_slug}</Link> · {item.reason.replaceAll("_", " ")}
            </li>
          ))}
        </ul>
      </details>
      <p className="meta">{coverage.missingness_note}</p>
    </section>
  );
}

export function VolumePanel({
  rows,
  methodVersion,
  contributingStatementCount,
  contributingPersonCount,
}: {
  rows: Array<{ bucket: string | null; topic_slug: string; statement_type: string; statement_count: number }>;
  methodVersion: string;
  contributingStatementCount: number;
  contributingPersonCount: number;
}) {
  const totals = new Map<string, number>();
  for (const row of rows) {
    const key = row.statement_type;
    totals.set(key, (totals.get(key) ?? 0) + row.statement_count);
  }
  return (
    <section className="panel">
      <p className="kicker">Volume, not a probability</p>
      <h2>Statements by type</h2>
      <p className="meta">
        Method {methodVersion}. {contributingStatementCount} statements from {contributingPersonCount} people. Counts stay split by statement class.
      </p>
      <div className="volume">
        {[...totals.entries()].map(([type, count]) => (
          <div key={type}>
            <span>{type.replaceAll("_", " ")}</span>
            <div className="bar" style={{ width: `${Math.min(100, count * 8)}%` }} />
            <span>{count}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
