import Link from "next/link";
import { useId } from "react";
import { exclusionLabel, trendKindLabel } from "@pdoom/contracts";
import { formatDay, formatEstimate, formatProbability, formatYear } from "@/lib/format";

type PersonRef = { person_slug: string; display_name: string };

type EstimateRow = {
  statement_slug: string;
  display_name: string;
  person_slug: string;
  value_numeric: number | null;
  value_min?: number | null;
  value_max?: number | null;
  value_type?: "point" | "range" | string;
  event_time: string | null;
  horizon_text?: string | null;
  in_summary?: boolean;
};

type ExclusionRow = {
  statement_slug: string;
  reason: string;
  reason_label?: string;
  person_slug?: string;
  display_name?: string;
};

export type NumericSemantics = "probability" | "year" | "quantity";

function countNoun(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function densityLabel(density: string): string {
  if (density === "empty") return "No comparable estimates";
  if (density === "sparse") return "Individual estimates only";
  if (density === "comparable") return "Summary of included records";
  if (density === "individual") return "Individual verified changes";
  if (density === "unlinked") return "No verified change link";
  return density;
}

export function DensityMark({ density }: { density: string }) {
  return <span className="density">{densityLabel(density)}</span>;
}

export function CoverageBlock({
  methodVersion,
  cohortSlug,
  cohortVersion,
  cohortDefinition,
  cohortSize,
  questionKey,
  questionText,
  definitionText,
  unit,
  conditionality,
  people,
  personCount,
  statementCount,
  missingCount,
  missingnessNote,
}: {
  methodVersion: string;
  cohortSlug?: string | null;
  cohortVersion?: string | null;
  cohortDefinition?: string | null;
  cohortSize: number;
  questionKey?: string | null;
  questionText?: string | null;
  definitionText?: string | null;
  unit?: string | null;
  conditionality?: string | null;
  people?: PersonRef[];
  personCount: number;
  statementCount: number;
  missingCount: number;
  missingnessNote?: string | null;
}) {
  return (
    <div>
      <p className="meta">
        Method {methodVersion}
        {cohortSlug ? ` · Cohort ${cohortSlug}` : ""}
        {cohortVersion ? ` ${cohortVersion}` : ""}
        {questionKey ? ` · Question ${questionKey}` : ""}
        {unit ? ` · Unit ${unit}` : ""}
        {conditionality && conditionality !== "unspecified" ? ` · ${conditionality}` : ""}
      </p>
      {questionText ? <p>{questionText}</p> : null}
      {definitionText ? <p>{definitionText}</p> : null}
      {cohortDefinition ? <p>{cohortDefinition}</p> : null}
      <p className="meta">
        {countNoun(personCount, "person", "people")}, {countNoun(statementCount, "statement", "statements")}. Cohort size {cohortSize}. {missingCount} members have no included record in this view.
      </p>
      {people && people.length > 0 ? (
        <p>
          Contributing people:{" "}
          {people.map((person, index) => (
            <span key={person.person_slug}>
              {index > 0 ? ", " : ""}
              <Link href={`/people/${person.person_slug}`}>{person.display_name}</Link>
            </span>
          ))}
        </p>
      ) : (
        <p>No contributing people in this view.</p>
      )}
      {missingnessNote ? <p className="meta">{missingnessNote}</p> : null}
    </div>
  );
}

export function ExclusionList({ exclusions }: { exclusions: ExclusionRow[] }) {
  if (exclusions.length === 0) return <p className="meta">No excluded records in scope.</p>;
  return (
    <details>
      <summary>{countNoun(exclusions.length, "excluded record", "excluded records")}</summary>
      <ul>
        {exclusions.map((item) => (
          <li key={`${item.statement_slug}-${item.reason}`}>
            <Link href={`/statements/${item.statement_slug}`}>{item.display_name ?? item.statement_slug}</Link>
            {" · "}
            {item.reason_label ?? exclusionLabel(item.reason)}
          </li>
        ))}
      </ul>
    </details>
  );
}

function ProbabilityChart({ rows }: { rows: EstimateRow[] }) {
  const titleId = useId();
  const width = 640;
  const height = 88;
  const points = rows.filter((row) => (row.value_type ?? "point") !== "range" && row.value_numeric !== null);
  if (points.length === 0) return null;
  return (
    <div className="chart-scroll">
      <svg className="trend-chart" role="img" aria-labelledby={titleId} viewBox={`0 0 ${width} ${height}`}>
        <title id={titleId}>Dot plot of included probabilities from 0% to 100%. The table states the same values.</title>
        <line x1="28" x2={width - 16} y1="46" y2="46" stroke="currentColor" strokeWidth="1" />
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
          const x = 28 + tick * (width - 44);
          return (
            <g key={tick}>
              <line x1={x} x2={x} y1="42" y2="50" stroke="currentColor" />
              <text x={x} y="72" textAnchor="middle">{formatProbability(tick)}</text>
            </g>
          );
        })}
        {points.map((row) => {
          const x = 28 + (row.value_numeric ?? 0) * (width - 44);
          return (
            <circle key={row.statement_slug} cx={x} cy="32" r="5" fill="currentColor">
              <title>{`${row.display_name}: ${formatProbability(row.value_numeric)}`}</title>
            </circle>
          );
        })}
      </svg>
    </div>
  );
}

function TimelineChart({ rows }: { rows: EstimateRow[] }) {
  const titleId = useId();
  if (rows.length === 0) return null;
  const years = rows.flatMap((row) => {
    if (row.value_type === "range") return [row.value_min, row.value_max].filter((value): value is number => value !== null && value !== undefined);
    return row.value_numeric === null ? [] : [row.value_numeric];
  });
  if (years.length === 0) return null;
  const min = Math.min(...years) - 2;
  const max = Math.max(...years) + 2;
  const span = Math.max(1, max - min);
  const width = 640;
  const rowHeight = 28;
  const height = 36 + rows.length * rowHeight;
  const xOf = (year: number) => 132 + ((year - min) / span) * (width - 148);
  return (
    <div className="chart-scroll">
      <svg className="trend-chart" role="img" aria-labelledby={titleId} viewBox={`0 0 ${width} ${height}`}>
        <title id={titleId}>Timeline of predicted years. Each row is one person. The table states the same years.</title>
        <line x1="132" x2={width - 12} y1={height - 18} y2={height - 18} stroke="currentColor" />
        <text x="132" y={height - 4}>{formatYear(min)}</text>
        <text x={width - 12} y={height - 4} textAnchor="end">{formatYear(max)}</text>
        {rows.map((row, index) => {
          const y = 22 + index * rowHeight;
          const label = row.display_name.length > 16 ? `${row.display_name.slice(0, 15)}…` : row.display_name;
          return (
            <g key={row.statement_slug}>
              <text x="4" y={y + 4}>{label}</text>
              {row.value_type === "range" && row.value_min !== null && row.value_min !== undefined && row.value_max !== null && row.value_max !== undefined ? (
                <line x1={xOf(row.value_min)} x2={xOf(row.value_max)} y1={y} y2={y} stroke="currentColor" strokeWidth="3" />
              ) : row.value_numeric !== null ? (
                <circle cx={xOf(row.value_numeric)} cy={y} r="5" fill="currentColor">
                  <title>{`${row.display_name}: ${formatYear(row.value_numeric)}`}</title>
                </circle>
              ) : null}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function NumericPanel({
  semantics,
  name,
  methodVersion,
  cohortSlug,
  cohortVersion,
  cohortDefinition,
  questionKey,
  questionText,
  definitionText,
  unit,
  conditionality,
  included,
  median,
  minimum,
  maximum,
  density,
  summaryNote,
  contributingPeople,
  contributingPersonCount,
  contributingStatementCount,
  coverage,
  exclusions,
}: {
  semantics: NumericSemantics;
  name: string;
  methodVersion: string;
  cohortSlug?: string | null;
  cohortVersion?: string | null;
  cohortDefinition?: string | null;
  questionKey?: string | null;
  questionText?: string | null;
  definitionText?: string | null;
  unit?: string | null;
  conditionality?: string | null;
  included: EstimateRow[];
  median: number | null;
  minimum: number | null;
  maximum: number | null;
  density?: string;
  summaryNote?: string | null;
  contributingPeople?: PersonRef[];
  contributingPersonCount: number;
  contributingStatementCount: number;
  coverage: { cohort_size: number; cohort_members_without_included_estimate: number; missingness_note?: string | null };
  exclusions: ExclusionRow[];
}) {
  const headingId = useId();
  const resolvedDensity = density ?? (included.length === 0 ? "empty" : included.length < 3 ? "sparse" : "comparable");
  const showSummary = resolvedDensity === "comparable" && median !== null;
  const kicker = semantics === "year" ? "Predicted years" : semantics === "quantity" ? "Quantity forecasts" : "Comparable explicit estimates";
  const valueLabel = semantics === "year" ? "Predicted year" : semantics === "quantity" ? "Quantity" : "Estimate";
  return (
    <section className="panel" aria-labelledby={headingId}>
      <p className="kicker">{kicker}</p>
      <h2 id={headingId}>{name}</h2>
      <DensityMark density={resolvedDensity} />
      <CoverageBlock
        methodVersion={methodVersion}
        cohortSlug={cohortSlug}
        cohortVersion={cohortVersion}
        cohortDefinition={cohortDefinition}
        cohortSize={coverage.cohort_size}
        questionKey={questionKey}
        questionText={questionText}
        definitionText={definitionText}
        unit={unit ?? (semantics === "probability" ? "probability" : null)}
        conditionality={conditionality}
        people={contributingPeople ?? included.map((row) => ({ person_slug: row.person_slug, display_name: row.display_name }))}
        personCount={contributingPersonCount}
        statementCount={contributingStatementCount}
        missingCount={coverage.cohort_members_without_included_estimate}
        missingnessNote={coverage.missingness_note}
      />
      <p>These figures are not a field consensus.</p>
      {resolvedDensity === "empty" ? (
        <p className="empty-state">{summaryNote ?? "No comparable estimates are in this cohort for this question."}</p>
      ) : null}
      {resolvedDensity === "sparse" ? (
        <p>{summaryNote ?? "Individual estimates are listed in the table. A median is withheld below 3 comparable point estimates."}</p>
      ) : null}
      {showSummary ? (
        <p className="median">
          {semantics === "year"
            ? `Median of included point years: ${formatYear(median)}. Lowest ${formatYear(minimum)}. Highest ${formatYear(maximum)}. The median year is a summary of those records. It is a date.`
            : semantics === "quantity"
              ? `Median of included point estimates: ${formatEstimate({ value_numeric: median, unit })}. Lowest ${formatEstimate({ value_numeric: minimum, unit })}. Highest ${formatEstimate({ value_numeric: maximum, unit })}.`
              : `Median of included point estimates: ${formatProbability(median)}. Range ${formatProbability(minimum)}–${formatProbability(maximum)}. This is a summary of those records.`}
        </p>
      ) : null}
      {semantics === "probability" ? <ProbabilityChart rows={included} /> : null}
      {semantics === "year" ? <TimelineChart rows={included} /> : null}
      <div className="chart-scroll">
        <table className="dist">
          <caption className="kicker">Text equivalent of this {trendKindLabel(semantics === "probability" ? "distribution" : semantics === "year" ? "timeline" : "quantity").toLowerCase()}</caption>
          <thead>
            <tr>
              <th scope="col">Person</th>
              <th scope="col">{valueLabel}</th>
              <th scope="col">Forecast made</th>
              <th scope="col">Horizon</th>
              {semantics !== "year" ? <th scope="col">Scale</th> : null}
            </tr>
          </thead>
          <tbody>
            {included.length === 0 ? (
              <tr>
                <td colSpan={semantics === "year" ? 4 : 5}>No included estimates.</td>
              </tr>
            ) : included.map((item) => {
              const display = formatEstimate({
                value_type: item.value_type,
                value_numeric: item.value_numeric,
                value_min: item.value_min,
                value_max: item.value_max,
                unit: unit ?? (semantics === "probability" ? "probability" : semantics === "year" ? "year" : null),
              });
              const scaleValue = item.value_type === "range" ? item.value_max ?? 0 : item.value_numeric ?? 0;
              const width = semantics === "probability" ? Math.max(0, Math.min(100, scaleValue * 100)) : Math.max(4, Math.min(100, scaleValue * 100));
              return (
                <tr key={item.statement_slug}>
                  <td><Link href={`/people/${item.person_slug}`}>{item.display_name}</Link></td>
                  <td>
                    <Link href={`/statements/${item.statement_slug}`}>{display}</Link>
                    {item.value_type === "range" ? " · range" : ""}
                    {item.in_summary === false ? " · outside the median" : ""}
                  </td>
                  <td>{formatDay(item.event_time)}</td>
                  <td>{item.horizon_text ?? "Horizon missing"}</td>
                  {semantics !== "year" ? (
                    <td>{item.value_type === "range" ? <div className="bar range" style={{ width: `${width}%` }} /> : <div className="bar" style={{ width: `${width}%` }} />}</td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ExclusionList exclusions={exclusions} />
    </section>
  );
}

export function DistributionPanel(props: Omit<Parameters<typeof NumericPanel>[0], "semantics">) {
  return <NumericPanel semantics="probability" {...props} />;
}

export function VolumePanel({
  rows,
  methodVersion,
  contributingStatementCount,
  contributingPersonCount,
  cohortSize,
  missingCount,
  missingnessNote,
  contributingPeople,
  exclusions,
}: {
  rows: Array<{ bucket: string | null; topic_slug: string; statement_type: string; statement_count: number; person_count?: number }>;
  methodVersion: string;
  contributingStatementCount: number;
  contributingPersonCount: number;
  cohortSize?: number;
  missingCount?: number;
  missingnessNote?: string | null;
  contributingPeople?: PersonRef[];
  exclusions?: ExclusionRow[];
}) {
  const totals = new Map<string, number>();
  for (const row of rows) totals.set(row.statement_type, (totals.get(row.statement_type) ?? 0) + row.statement_count);
  const max = Math.max(...totals.values(), 1);
  return (
    <section className="panel">
      <p className="kicker">Volume, a count of records</p>
      <h2>Statements by type</h2>
      <CoverageBlock
        methodVersion={methodVersion}
        cohortSize={cohortSize ?? contributingPersonCount}
        questionText="Counts of statements by topic and statement class."
        definitionText="Statement classes stay separate. This count is not a probability."
        people={contributingPeople}
        personCount={contributingPersonCount}
        statementCount={contributingStatementCount}
        missingCount={missingCount ?? 0}
        missingnessNote={missingnessNote}
      />
      <p>These figures are not a field consensus.</p>
      {rows.length === 0 ? <p className="empty-state">No counted statements are in this cohort.</p> : null}
      <div className="volume">
        {[...totals.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([type, count]) => (
          <div key={type}>
            <span>{type.replaceAll("_", " ")}</span>
            <div className="bar" style={{ width: `${(count / max) * 100}%` }} />
            <span>{count}</span>
          </div>
        ))}
      </div>
      <div className="chart-scroll">
        <table className="dist">
          <caption className="kicker">Text equivalent of the statement counts</caption>
          <thead>
            <tr>
              <th scope="col">Quarter</th>
              <th scope="col">Topic</th>
              <th scope="col">Statement class</th>
              <th scope="col">Statements</th>
              <th scope="col">People</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={5}>No counted statements.</td></tr>
            ) : rows.map((row) => (
              <tr key={`${row.bucket ?? "unknown"}-${row.topic_slug}-${row.statement_type}`}>
                <td>{row.bucket ?? "Time unknown"}</td>
                <td>{row.topic_slug}</td>
                <td>{row.statement_type.replaceAll("_", " ")}</td>
                <td>{row.statement_count}</td>
                <td>{row.person_count ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {exclusions ? <ExclusionList exclusions={exclusions} /> : null}
    </section>
  );
}

export function RevisionPanel({
  name,
  methodVersion,
  cohortSlug,
  cohortVersion,
  cohortDefinition,
  questionKey,
  questionText,
  definitionText,
  unit,
  density,
  summaryNote,
  chains,
  repeats,
  eligibleEstimateCount,
  contributingPeople,
  contributingPersonCount,
  contributingStatementCount,
  coverage,
  exclusions,
}: {
  name: string;
  methodVersion: string;
  cohortSlug?: string | null;
  cohortVersion?: string | null;
  cohortDefinition?: string | null;
  questionKey?: string | null;
  questionText?: string | null;
  definitionText?: string | null;
  unit?: string | null;
  density: string;
  summaryNote?: string | null;
  chains: Array<{
    person_slug: string;
    display_name: string;
    points: Array<{ statement_slug: string; event_time: string | null; value_numeric: number; horizon_text?: string | null }>;
    links: Array<{ from_statement_slug: string; to_statement_slug: string; relationship_type: string; method: string; from_value: number; to_value: number; from_event_time: string | null; to_event_time: string | null }>;
  }>;
  repeats: Array<{ from_statement_slug: string; to_statement_slug: string; display_name: string; person_slug: string; from_value: number | null; to_value: number | null; note: string }>;
  eligibleEstimateCount: number;
  contributingPeople?: PersonRef[];
  contributingPersonCount: number;
  contributingStatementCount: number;
  coverage: { cohort_size: number; cohort_members_without_included_estimate: number; missingness_note?: string | null };
  exclusions: ExclusionRow[];
}) {
  return (
    <section className="panel">
      <p className="kicker">Historical revision</p>
      <h2>{name}</h2>
      <DensityMark density={density} />
      <CoverageBlock
        methodVersion={methodVersion}
        cohortSlug={cohortSlug}
        cohortVersion={cohortVersion}
        cohortDefinition={cohortDefinition}
        cohortSize={coverage.cohort_size}
        questionKey={questionKey}
        questionText={questionText}
        definitionText={definitionText}
        unit={unit}
        people={contributingPeople}
        personCount={contributingPersonCount}
        statementCount={contributingStatementCount}
        missingCount={coverage.cohort_members_without_included_estimate}
        missingnessNote={coverage.missingness_note}
      />
      <p>These figures are not a field consensus. {eligibleEstimateCount} comparable point estimates are in scope. A change appears only along a human-verified update or retraction.</p>
      {summaryNote ? <p>{summaryNote}</p> : null}
      {chains.length === 0 ? <p className="empty-state">No verified change is drawn for this question.</p> : null}
      {chains.map((chain) => (
        <article key={chain.person_slug}>
          <h3><Link href={`/people/${chain.person_slug}`}>{chain.display_name}</Link></h3>
          <RevisionChart chain={chain} unit={unit ?? null} />
          <div className="chart-scroll">
            <table className="dist">
              <caption className="kicker">Text equivalent of {chain.display_name}&apos;s verified change</caption>
              <thead>
                <tr>
                  <th scope="col">Earlier</th>
                  <th scope="col">Later</th>
                  <th scope="col">Relationship</th>
                  <th scope="col">Recorded method</th>
                </tr>
              </thead>
              <tbody>
                {chain.links.map((link) => (
                  <tr key={`${link.from_statement_slug}-${link.to_statement_slug}-${link.relationship_type}`}>
                    <td>
                      <Link href={`/statements/${link.from_statement_slug}`}>{formatEstimate({ value_numeric: link.from_value, unit })}</Link>
                      {" · "}{formatDay(link.from_event_time)}
                    </td>
                    <td>
                      <Link href={`/statements/${link.to_statement_slug}`}>{formatEstimate({ value_numeric: link.to_value, unit })}</Link>
                      {" · "}{formatDay(link.to_event_time)}
                    </td>
                    <td>{link.relationship_type}</td>
                    <td>{link.method}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ))}
      {repeats.length > 0 ? (
        <>
          <h3>Repeated forecasts</h3>
          <p>A repeat is recorded as the same forecast. It is not drawn as a change.</p>
          <ul>
            {repeats.map((repeat) => (
              <li key={`${repeat.from_statement_slug}-${repeat.to_statement_slug}`}>
                <Link href={`/people/${repeat.person_slug}`}>{repeat.display_name}</Link>
                {" · "}
                <Link href={`/statements/${repeat.from_statement_slug}`}>{formatEstimate({ value_numeric: repeat.from_value, unit })}</Link>
                {" → "}
                <Link href={`/statements/${repeat.to_statement_slug}`}>{formatEstimate({ value_numeric: repeat.to_value, unit })}</Link>
                {" · "}{repeat.note}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <ExclusionList exclusions={exclusions} />
    </section>
  );
}

function RevisionChart({
  chain,
  unit,
}: {
  chain: {
    display_name: string;
    points: Array<{ statement_slug: string; event_time: string | null; value_numeric: number }>;
    links: Array<{ from_statement_slug: string; to_statement_slug: string; from_value: number; to_value: number; from_event_time: string | null; to_event_time: string | null }>;
  };
  unit: string | null;
}) {
  const titleId = useId();
  const times = chain.points.map((point) => point.event_time).filter((time): time is string => Boolean(time)).sort();
  if (times.length === 0 || chain.points.length === 0) return null;
  const start = new Date(times[0]!).getTime();
  const end = new Date(times[times.length - 1]!).getTime();
  const span = Math.max(1, end - start);
  const values = chain.points.map((point) => point.value_numeric);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const valueSpan = Math.max(0.0001, max - min);
  const width = 640;
  const height = 140;
  const xOf = (time: string | null) => {
    if (!time) return 48;
    return 48 + ((new Date(time).getTime() - start) / span) * (width - 72);
  };
  const yOf = (value: number) => 20 + (1 - (value - min) / valueSpan) * 80;
  const pointBySlug = new Map(chain.points.map((point) => [point.statement_slug, point]));
  return (
    <div className="chart-scroll">
      <svg className="trend-chart" role="img" aria-labelledby={titleId} viewBox={`0 0 ${width} ${height}`}>
        <title id={titleId}>{`${chain.display_name}: verified forecast values over time. The table states the same values.`}</title>
        {chain.links.map((link) => {
          const from = pointBySlug.get(link.from_statement_slug);
          const to = pointBySlug.get(link.to_statement_slug);
          if (!from || !to) return null;
          return (
            <line
              key={`${link.from_statement_slug}-${link.to_statement_slug}`}
              x1={xOf(from.event_time)}
              y1={yOf(from.value_numeric)}
              x2={xOf(to.event_time)}
              y2={yOf(to.value_numeric)}
              stroke="currentColor"
              strokeWidth="2"
            />
          );
        })}
        {chain.points.map((point) => (
          <g key={point.statement_slug}>
            <circle cx={xOf(point.event_time)} cy={yOf(point.value_numeric)} r="5" fill="currentColor">
              <title>{`${formatEstimate({ value_numeric: point.value_numeric, unit })} on ${formatDay(point.event_time)}`}</title>
            </circle>
            <text x={xOf(point.event_time) + 8} y={yOf(point.value_numeric) - 8}>{formatEstimate({ value_numeric: point.value_numeric, unit })}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}
