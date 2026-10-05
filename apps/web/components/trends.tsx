import Link from "next/link";
import { useId } from "react";
import { MEDIAN_INTERPRETATION, exclusionLabel, trendKindLabel } from "@pdoom/contracts";
import { formatDay, formatEstimate, formatProbability, formatYear, typeLabel } from "@/lib/format";
import styles from "./trends.module.css";

function PanelTitle({ id, duplicate, children }: { id?: string; duplicate?: boolean; children: string }) {
  return <h2 id={id} className={duplicate ? "duplicate-title" : undefined}>{children}</h2>;
}

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
  preserved_value?: string | null;
};

type ComparabilityCopy = {
  outcomeLabel?: string | null;
  deadlineLabel?: string | null;
  conditionLabel?: string | null;
  exactQuestionId?: string | null;
  storedQuestionKey?: string | null;
  historyNote?: string | null;
  medianInterpretation?: string | null;
};

export type NumericSemantics = "probability" | "year" | "quantity";

function countNoun(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function ScaleBar({ percent, range = false, quantity = false }: { percent: number; range?: boolean; quantity?: boolean }) {
  const width = Math.max(0, Math.min(100, percent));
  const className = range ? "bar range" : quantity ? "bar quantity" : "bar";
  return (
    <svg className={className} viewBox="0 0 100 1" preserveAspectRatio="none" aria-hidden="true">
      <rect x="0" y="0" height="1" width={width} strokeWidth={range ? 2 : undefined} vectorEffect={range ? "non-scaling-stroke" : undefined} />
    </svg>
  );
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
        {cohortVersion ? ` · version ${cohortVersion}` : ""}
        {unit ? ` · Unit ${unit}` : ""}
        {conditionality && conditionality !== "unspecified" ? ` · ${conditionality}` : ""}
      </p>
      <p className="meta">
        {countNoun(personCount, "person", "people")}, {countNoun(statementCount, "statement", "statements")}. Cohort size {cohortSize}. {missingCount} members have no included record in this view.
      </p>
      {missingnessNote ? <p className="meta">{missingnessNote}</p> : null}
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
      {questionText || definitionText || cohortDefinition || questionKey ? (
        <details className="technical">
          <summary>Question text and cohort definition</summary>
          {questionText ? <p>{questionText}</p> : null}
          {definitionText ? <p>{definitionText}</p> : null}
          {cohortDefinition ? <p>{cohortDefinition}</p> : null}
          {questionKey ? <p className="meta">Stored question {questionKey}</p> : null}
        </details>
      ) : null}
    </div>
  );
}

export function ComparabilityFacts({
  outcomeLabel,
  deadlineLabel,
  conditionLabel,
  exactQuestionId,
  storedQuestionKey,
  historyNote,
  medianInterpretation,
}: ComparabilityCopy) {
  if (!outcomeLabel && !deadlineLabel && !conditionLabel && !exactQuestionId && !historyNote && !medianInterpretation) return null;
  return (
    <div className={styles.facts}>
      {(outcomeLabel || deadlineLabel || conditionLabel) ? (
        <dl className="scope">
          {outcomeLabel ? <div><dt>Outcome</dt><dd>{outcomeLabel}</dd></div> : null}
          {deadlineLabel ? <div><dt>Deadline or value</dt><dd>{deadlineLabel}</dd></div> : null}
          {conditionLabel ? <div><dt>Condition</dt><dd>{conditionLabel}</dd></div> : null}
        </dl>
      ) : null}
      {medianInterpretation ? <p>{medianInterpretation}</p> : null}
      {historyNote ? <p className="meta">{historyNote}</p> : null}
      {(exactQuestionId || (storedQuestionKey && storedQuestionKey !== exactQuestionId)) ? (
        <details className="technical">
          <summary>Question identifiers</summary>
          {exactQuestionId ? <p className="meta">Exact question {exactQuestionId}</p> : null}
          {storedQuestionKey && storedQuestionKey !== exactQuestionId ? <p className="meta">Stored key {storedQuestionKey}. The stored key is not rewritten.</p> : null}
        </details>
      ) : null}
    </div>
  );
}

function exclusionAnchor(item: ExclusionRow): string {
  if (item.preserved_value) return item.preserved_value;
  return item.statement_slug.replaceAll("-", " ");
}

export function ExclusionList({ exclusions }: { exclusions: ExclusionRow[] }) {
  if (exclusions.length === 0) return <p className="meta">No excluded records in scope. Excluded from this comparison is not the same as rejected during review.</p>;
  const groups = new Map<string, ExclusionRow[]>();
  for (const item of exclusions) {
    const label = item.reason_label ?? exclusionLabel(item.reason);
    const group = groups.get(label) ?? [];
    group.push(item);
    groups.set(label, group);
  }
  return (
    <details>
      <summary>{countNoun(exclusions.length, "excluded record", "excluded records")}</summary>
      <p className="meta">These records stay stored. Excluded from this comparison is not the same as rejected during review.</p>
      {[...groups.entries()].map(([label, items]) => (
        <section key={label}>
          <h3>{countNoun(items.length, "record", "records")}</h3>
          <ul>
            {items.map((item) => (
              <li key={`${item.statement_slug}-${item.reason}`}>
                <Link href={`/statements/${item.statement_slug}`} title={item.statement_slug}>{exclusionAnchor(item)}</Link>
                {item.display_name ? ` · ${item.display_name}` : ""}
                {` · ${label}`}
                {item.preserved_value ? <span className={styles.preserved}> · preserved value {item.preserved_value}</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </details>
  );
}

function ProbabilityChart({ rows }: { rows: EstimateRow[] }) {
  const titleId = useId();
  const width = 640;
  const height = 112;
  const points = rows.filter((row) => (row.value_type ?? "point") !== "range" && row.value_numeric !== null);
  if (points.length === 0) return null;
  const used = new Map<number, number>();
  return (
    <div className="chart-scroll plot">
      <svg className="trend-chart" role="group" aria-labelledby={titleId} viewBox={`0 0 ${width} ${height}`}>
        <title id={titleId}>Dot plot of included probabilities from 0% to 100%. Filled circles are point estimates. The table states the same values and links.</title>
        <text x="28" y="16">Probability</text>
        <rect x="28" y="28" width={width - 44} height="50" rx="8" fill="#e5f3f0" />
        <line x1="28" x2={width - 16} y1="78" y2="78" stroke="currentColor" strokeWidth="1.5" />
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
          const x = 28 + tick * (width - 44);
          return (
            <g key={tick}>
              <line x1={x} x2={x} y1="74" y2="82" stroke="currentColor" />
              <text x={x} y="104" textAnchor="middle">{formatProbability(tick)}</text>
            </g>
          );
        })}
        {points.map((row) => {
          const key = Math.round((row.value_numeric ?? 0) * 1000);
          const slot = used.get(key) ?? 0;
          used.set(key, slot + 1);
          const x = 28 + (row.value_numeric ?? 0) * (width - 44);
          const y = 58 - (slot % 3) * 14;
          const detail = `${row.display_name}: ${formatProbability(row.value_numeric)}.`;
          return (
            <a key={row.statement_slug} href={`/statements/${row.statement_slug}`} aria-label={`${row.display_name}. View statement.`}>
              <circle cx={x} cy={y} r="7.5" fill="currentColor" stroke="#ffffff" strokeWidth="2">
                <title>{detail}</title>
              </circle>
            </a>
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
  const rowHeight = 32;
  const height = 78 + rows.length * rowHeight;
  const xOf = (year: number) => 132 + ((year - min) / span) * (width - 148);
  return (
    <div className="chart-scroll plot">
      <svg className="trend-chart" role="group" aria-labelledby={titleId} viewBox={`0 0 ${width} ${height}`}>
        <title id={titleId}>Timeline of predicted years. Each row is one person. The table states the same years.</title>
        <text x="132" y="14">Predicted year</text>
        <rect x="128" y="22" width={width - 140} height={Math.max(24, height - 46)} rx="8" fill="#e5f3f0" />
        <line x1="132" x2={width - 12} y1={height - 18} y2={height - 18} stroke="currentColor" />
        <text x="132" y={height - 4}>{formatYear(min)}</text>
        <text x={width - 12} y={height - 4} textAnchor="end">{formatYear(max)}</text>
        {rows.map((row, index) => {
          const y = 40 + index * rowHeight;
          const label = row.display_name.length > 18 ? `${row.display_name.slice(0, 17)}…` : row.display_name;
          const full = row.value_type === "range"
            ? `${row.display_name}: ${formatYear(row.value_min)}–${formatYear(row.value_max)}`
            : `${row.display_name}: ${formatYear(row.value_numeric)}`;
          return (
            <g key={row.statement_slug}>
              <text x="4" y={y + 4}>{label}</text>
              {row.value_type === "range" && row.value_min !== null && row.value_min !== undefined && row.value_max !== null && row.value_max !== undefined ? (
                <a href={`/statements/${row.statement_slug}`} aria-label={`${row.display_name}. View statement.`}>
                  <line x1={xOf(row.value_min)} x2={xOf(row.value_max)} y1={y} y2={y} stroke="currentColor" strokeWidth="3" />
                  <title>{full}</title>
                </a>
              ) : row.value_numeric !== null ? (
                <a href={`/statements/${row.statement_slug}`} aria-label={`${row.display_name}. View statement.`}>
                  <rect x={xOf(row.value_numeric) - 5} y={y - 5} width="10" height="10" fill="currentColor">
                    <title>{full}</title>
                  </rect>
                </a>
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
  outcomeLabel,
  deadlineLabel,
  conditionLabel,
  exactQuestionId,
  historyNote,
  medianInterpretation,
  duplicateTitle,
  preview = false,
  previewHref,
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
  duplicateTitle?: boolean;
  preview?: boolean;
  previewHref?: string;
} & ComparabilityCopy) {
  const headingId = useId();
  const interpretation = medianInterpretation ?? (semantics === "year" ? MEDIAN_INTERPRETATION.year : semantics === "quantity" ? MEDIAN_INTERPRETATION.quantity : MEDIAN_INTERPRETATION.probability);
  const resolvedDensity = density ?? (included.length === 0 ? "empty" : included.length < 3 ? "sparse" : "comparable");
  const showSummary = resolvedDensity === "comparable" && median !== null;
  const kicker = semantics === "year" ? "Predicted years" : semantics === "quantity" ? "Quantity forecasts" : "Comparable explicit estimates";
  const valueLabel = semantics === "year" ? "Predicted year" : semantics === "quantity" ? "Quantity" : "Estimate";
  return (
    <section className={preview ? "panel preview-panel" : "panel"} aria-labelledby={headingId}>
      <p className="kicker">{kicker}</p>
      <PanelTitle id={headingId} duplicate={duplicateTitle}>{name}</PanelTitle>
      <DensityMark density={resolvedDensity} />
      {preview ? null : (
        <ComparabilityFacts
          outcomeLabel={outcomeLabel}
          deadlineLabel={deadlineLabel}
          conditionLabel={conditionLabel}
          medianInterpretation={interpretation}
        />
      )}
      <p>
        {countNoun(contributingPersonCount, "person", "people")}, {countNoun(contributingStatementCount, "statement", "statements")}. Cohort size {coverage.cohort_size}. {coverage.cohort_members_without_included_estimate} members have no included record in this view. These figures are not a field consensus.
      </p>
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
              : `Median of included point estimates: ${formatProbability(median)}. Range ${formatProbability(minimum)}–${formatProbability(maximum)}.`}
        </p>
      ) : null}
      {semantics === "probability" ? <ProbabilityChart rows={included} /> : null}
      {semantics === "year" ? <TimelineChart rows={included} /> : null}
      {semantics === "quantity" ? <p className="meta">Each bar below is a quantity in the stated unit. It is not a probability.</p> : null}
      {preview ? (
        previewHref ? <p className="actions"><Link href={previewHref}>Open this comparison</Link></p> : null
      ) : (
      <>
      <div className="chart-scroll">
        <table className="dist">
          <caption>Text equivalent of this {trendKindLabel(semantics === "probability" ? "distribution" : semantics === "year" ? "timeline" : "quantity").toLowerCase()}</caption>
          <thead>
            <tr>
              <th scope="col">Person</th>
              <th scope="col">{valueLabel}</th>
              <th scope="col">Forecast made</th>
              <th scope="col">Horizon</th>
              {semantics !== "year" ? <th scope="col">Scale</th> : null}
              <th scope="col">Record</th>
            </tr>
          </thead>
          <tbody>
            {included.length === 0 ? (
              <tr>
                <td colSpan={semantics === "year" ? 5 : 6}>No included estimates.</td>
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
                  <td data-label="Person"><Link href={`/people/${item.person_slug}`}>{item.display_name}</Link></td>
                  <td data-label={valueLabel}>
                    <Link href={`/statements/${item.statement_slug}`}>{display}</Link>
                    {item.value_type === "range" ? " · range" : ""}
                    {item.in_summary === false ? " · outside the median" : ""}
                  </td>
                  <td data-label="Forecast made">{formatDay(item.event_time)}</td>
                  <td data-label="Horizon">{item.horizon_text ?? "Horizon missing"}</td>
                  {semantics !== "year" ? (
                    <td data-label="Scale"><ScaleBar percent={width} range={item.value_type === "range"} quantity={semantics === "quantity"} /></td>
                  ) : null}
                  <td data-label="Record"><Link href={`/statements/${item.statement_slug}`}>View statement</Link></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p>
        Contributing people:{" "}
        {(contributingPeople ?? included.map((row) => ({ person_slug: row.person_slug, display_name: row.display_name }))).length > 0
          ? (contributingPeople ?? included.map((row) => ({ person_slug: row.person_slug, display_name: row.display_name }))).map((person, index) => (
            <span key={person.person_slug}>
              {index > 0 ? ", " : ""}
              <Link href={`/people/${person.person_slug}`}>{person.display_name}</Link>
            </span>
          ))
          : "none in this view."}
      </p>
      {coverage.missingness_note ? <p className="meta">{coverage.missingness_note}</p> : null}
      <p className="meta">
        Method {methodVersion}
        {cohortSlug ? ` · Cohort ${cohortSlug}` : ""}
        {cohortVersion ? ` · version ${cohortVersion}` : ""}
        {` · Unit ${unit ?? (semantics === "probability" ? "probability" : "not stated")}`}
        {conditionality && conditionality !== "unspecified" ? ` · ${conditionality}` : ""}
      </p>
      <details className="technical">
        <summary>Question text, cohort, and how to read this</summary>
        {questionText ? <p>{questionText}</p> : <p>No separate question text is stored.</p>}
        {definitionText ? <p>{definitionText}</p> : null}
        {cohortDefinition ? <p>{cohortDefinition}</p> : null}
        {questionKey ? <p className="meta">Stored question {questionKey}</p> : null}
        {exactQuestionId ? <p className="meta">Exact question {exactQuestionId}</p> : null}
        {historyNote ? <p className="meta">{historyNote}</p> : null}
      </details>
      <ExclusionList exclusions={exclusions} />
      </>
      )}
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
            <span>{typeLabel(type)}</span>
            <ScaleBar percent={(count / max) * 100} />
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
  outcomeLabel,
  deadlineLabel,
  conditionLabel,
  exactQuestionId,
  historyNote,
  duplicateTitle,
}: {
  name: string;
  duplicateTitle?: boolean;
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
    links: Array<{ from_statement_slug: string; to_statement_slug: string; relationship_type: string; method: string; from_value: number; to_value: number | null; from_event_time: string | null; to_event_time: string | null; withdrawal?: boolean }>;
  }>;
  repeats: Array<{ from_statement_slug: string; to_statement_slug: string; display_name: string; person_slug: string; from_value: number | null; to_value: number | null; note: string }>;
  eligibleEstimateCount: number;
  contributingPeople?: PersonRef[];
  contributingPersonCount: number;
  contributingStatementCount: number;
  coverage: { cohort_size: number; cohort_members_without_included_estimate: number; missingness_note?: string | null };
  exclusions: ExclusionRow[];
} & ComparabilityCopy) {
  return (
    <section className="panel">
      <p className="kicker">Historical revision</p>
      <PanelTitle duplicate={duplicateTitle}>{name}</PanelTitle>
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
      <ComparabilityFacts
        outcomeLabel={outcomeLabel}
        deadlineLabel={deadlineLabel}
        conditionLabel={conditionLabel}
        exactQuestionId={exactQuestionId}
        historyNote={historyNote}
      />
      <p>These figures are not a field consensus. {eligibleEstimateCount} comparable point estimates are in scope. A change appears only along a human-verified update, retraction, or withdrawal. A later statement without that link is not a change of mind.</p>
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
                      {link.withdrawal || link.to_value === null ? (
                        <span className={styles.withdrawal}>Withdrawn, no replacement value</span>
                      ) : (
                        <Link href={`/statements/${link.to_statement_slug}`}>{formatEstimate({ value_numeric: link.to_value, unit })}</Link>
                      )}
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
    links: Array<{ from_statement_slug: string; to_statement_slug: string; from_value: number; to_value: number | null; from_event_time: string | null; to_event_time: string | null }>;
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
    <div className="chart-scroll plot">
      <svg className="trend-chart" role="group" aria-labelledby={titleId} viewBox={`0 0 ${width} ${height}`}>
        <title id={titleId}>{`${chain.display_name}: verified forecast values over time. The table states the same values.`}</title>
        <rect x="36" y="12" width={width - 48} height="108" rx="8" fill="#e5f3f0" />
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

export function QualitativePanel({
  name,
  methodVersion,
  cohortSlug,
  cohortVersion,
  cohortDefinition,
  questionKey,
  definitionText,
  note,
  rows,
  cohortSize,
  historyNote,
  duplicateTitle,
}: {
  name: string;
  duplicateTitle?: boolean;
  methodVersion: string;
  cohortSlug?: string | null;
  cohortVersion?: string | null;
  cohortDefinition?: string | null;
  questionKey: string;
  definitionText: string;
  note: string;
  rows: Array<{ statement_slug: string; person_slug: string; display_name: string; question_text: string | null; event_time: string | null }>;
  cohortSize: number;
  historyNote?: string | null;
}) {
  const people = [...new Map(rows.map((row) => [row.person_slug, row.display_name])).entries()].map(([person_slug, display_name]) => ({ person_slug, display_name }));
  return (
    <section className="panel">
      <p className="kicker">Qualitative statements</p>
      <PanelTitle duplicate={duplicateTitle}>{name}</PanelTitle>
      <CoverageBlock
        methodVersion={methodVersion}
        cohortSlug={cohortSlug}
        cohortVersion={cohortVersion}
        cohortDefinition={cohortDefinition}
        cohortSize={cohortSize}
        questionKey={questionKey}
        definitionText={definitionText}
        people={people}
        personCount={people.length}
        statementCount={rows.length}
        missingCount={Math.max(0, cohortSize - people.length)}
      />
      <ComparabilityFacts historyNote={historyNote} medianInterpretation={note} />
      <p>No number on this page is a probability inferred from the wording.</p>
      <ul>
        {rows.map((row) => (
          <li key={row.statement_slug}>
            <Link href={`/people/${row.person_slug}`}>{row.display_name}</Link>
            {" · "}
            <Link href={`/statements/${row.statement_slug}`}>{row.question_text ?? row.statement_slug}</Link>
            {" · "}
            {formatDay(row.event_time)}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function InspectionPanel({
  name,
  methodVersion,
  cohortDefinition,
  note,
  rows,
  cohortSize,
  historyNote,
  duplicateTitle,
}: {
  name: string;
  duplicateTitle?: boolean;
  methodVersion: string;
  cohortDefinition?: string | null;
  note: string;
  rows: Array<{
    statement_slug: string;
    person_slug: string;
    display_name: string;
    question_key: string;
    reason_label: string;
    preserved_value: string | null;
    horizon_text: string | null;
    target_date_end: string | null;
    unit: string | null;
  }>;
  cohortSize: number;
  historyNote?: string | null;
}) {
  const people = [...new Map(rows.map((row) => [row.person_slug, row.display_name])).entries()].map(([person_slug, display_name]) => ({ person_slug, display_name }));
  return (
    <section className="panel">
      <p className="kicker">Not pooled</p>
      <PanelTitle duplicate={duplicateTitle}>{name}</PanelTitle>
      <CoverageBlock
        methodVersion={methodVersion}
        cohortDefinition={cohortDefinition}
        cohortSize={cohortSize}
        questionText="Records that do not meet one exact comparison."
        definitionText={note}
        people={people}
        personCount={people.length}
        statementCount={rows.length}
        missingCount={Math.max(0, cohortSize - people.length)}
      />
      <ComparabilityFacts historyNote={historyNote} />
      <div className="chart-scroll">
        <table className="dist">
          <caption className="kicker">Records left out of pooled comparisons</caption>
          <thead>
            <tr>
              <th scope="col">Person</th>
              <th scope="col">Stored key</th>
              <th scope="col">Why it is not pooled</th>
              <th scope="col">Preserved value</th>
              <th scope="col">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.statement_slug}>
                <td><Link href={`/people/${row.person_slug}`}>{row.display_name}</Link></td>
                <td>{row.question_key}</td>
                <td>{row.reason_label}</td>
                <td>{row.preserved_value ?? row.horizon_text ?? row.target_date_end ?? row.unit ?? "Stored without a pooled value"}</td>
                <td><Link href={`/statements/${row.statement_slug}`}>Statement</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
