import { statementListQuerySchema } from "@pdoom/contracts";
import { listStatements } from "@pdoom/db";
import Link from "next/link";
import { InvalidFilters, Pager, StatementFilters } from "@/components/filters";
import { ReviewBadge } from "@/components/statement-bits";
import { EmptyState, NoResults } from "@/components/states";
import { resolveFilterLabels } from "@/lib/entity-labels";
import { formatValue, formatWhen, phraseLabel } from "@/lib/format";
import { isInvalidCursor } from "@/lib/http";
import { canonicalOrigin, hasDiscoveryFilter, listPageFields, pageMetadata } from "@/lib/seo";
import {
  personResearchHref,
  researchFilters,
  timeRelation,
  topicResearchHref,
  withCursor,
  type ResearchFilters,
} from "@/lib/presentation";

export const dynamic = "force-dynamic";

const STATEMENT_CLASS_LABEL = {
  explicit_numeric: "explicit numeric",
  explicit_qualitative: "explicit qualitative",
  model_inferred_signal: "model-inferred signal",
} as const;

type ListedStatement = Awaited<ReturnType<typeof listStatements>>["data"][number];

export async function generateMetadata({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  return pageMetadata(canonicalOrigin(), listPageFields("statements", hasDiscoveryFilter(params)));
}

function filtered(params: Record<string, string | undefined>): boolean {
  return Object.entries(params).some(([key, value]) => key !== "cursor" && key !== "limit" && Boolean(value));
}

function statementClassLabel(type: string): string {
  if (type === "explicit_numeric" || type === "explicit_qualitative" || type === "model_inferred_signal") {
    return STATEMENT_CLASS_LABEL[type];
  }
  return type.replaceAll("_", " ");
}

function finiteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function hasRecordedNumber(forecast: NonNullable<ListedStatement["forecast"]>): boolean {
  if (!forecast.value_type || forecast.value_type === "none") return false;
  if (forecast.value_type === "range") return finiteNumber(forecast.value_min) && finiteNumber(forecast.value_max);
  return finiteNumber(forecast.value_numeric);
}

/** A percentage or other stored quantity, only for an explicit numeric row that already has one. */
function explicitNumericText(statement: ListedStatement): string | null {
  if (statement.statement_type !== "explicit_numeric") return null;
  const forecast = statement.forecast;
  if (!forecast || !hasRecordedNumber(forecast)) return null;
  const text = formatValue(forecast);
  if (!text || text === "No numeric value" || text.includes("—")) return null;
  return text;
}

function StatementListCard({
  statement,
  filters,
}: {
  statement: ListedStatement;
  filters: ResearchFilters;
}) {
  const topics = Array.isArray(statement.topics) ? statement.topics : [];
  const sourceItem = statement.source_item;
  const relation = timeRelation({
    published_at: sourceItem.published_at,
    observed_at: sourceItem.observed_at,
  });
  const recorded = explicitNumericText(statement);
  return (
    <article className="card">
      <h3 className="claim">
        <Link href={`/statements/${statement.slug}`}>{statement.normalized_text}</Link>
      </h3>
      <p className="who">
        <Link href={personResearchHref(statement.person.slug, filters)}>{statement.person.display_name}</Link>
      </p>
      <p className="card-flags">
        <span className={`badge ${statement.statement_type}`}>{statementClassLabel(statement.statement_type)}</span>
        <ReviewBadge state={statement.review_state} />
        <time className="meta" dateTime={statement.event_time ?? undefined}>
          Event {formatWhen(statement.event_time)}
        </time>
      </p>
      <p className="meta">
        Published {formatWhen(sourceItem.published_at)}
        {" · "}
        Observed {formatWhen(sourceItem.observed_at)}
        {" · "}
        {relation.label}
      </p>
      <p className="meta">
        <Link href={`/sources/${statement.source.slug}`}>{statement.source.name}</Link>
        {" · "}
        {phraseLabel(statement.source.source_type)}
        {statement.forecast?.horizon_text ? ` · Horizon ${statement.forecast.horizon_text}` : ""}
        {recorded ? ` · ${recorded}` : ""}
      </p>
      {topics.length ? (
        <ul className="chips" aria-label="Topics">
          {topics.map((topic) => (
            <li key={topic.slug}>
              <Link href={topicResearchHref(topic.slug, filters)}>{topic.name}</Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="meta">No topic recorded</p>
      )}
    </article>
  );
}

export default async function StatementsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const cleaned = Object.fromEntries(Object.entries(params).filter((entry) => entry[1]));
  const parsed = statementListQuerySchema.safeParse({
    ...cleaned,
    limit: params.limit ?? 10,
  });
  const labels = await resolveFilterLabels({
    person: params.person,
    organization: params.organization,
    source: params.source,
    topic: params.topic,
  });
  let invalid = !parsed.success;
  let page: Awaited<ReturnType<typeof listStatements>> | null = null;
  if (parsed.success) {
    try {
      page = await listStatements(parsed.data);
    } catch (error) {
      if (!isInvalidCursor(error)) throw error;
      invalid = true;
    }
  }
  return (
    <>
      <h1>Statements</h1>
      <p className="lede">
        Each row names the claim, the person, the source, and one statement class: explicit numeric, explicit qualitative, or model-inferred signal. Those three classes stay separate. Open a row for the original evidence. This list is paged. The count is every match, including rows on other pages.
      </p>
      <StatementFilters params={params} labels={labels} />
      {invalid || !page ? <InvalidFilters /> : <StatementResults params={params} page={page} filtered={filtered(params)} />}
    </>
  );
}

function StatementResults({
  params,
  page,
  filtered,
}: {
  params: Record<string, string | undefined>;
  page: NonNullable<Awaited<ReturnType<typeof listStatements>>>;
  filtered: boolean;
}) {
  const filters = researchFilters(params);
  return (
    <>
      <section aria-labelledby="statement-results">
        <h2 id="statement-results" className="sr-only">Matching statements</h2>
        {page.data.length ? page.data.map((statement) => (
          <StatementListCard key={statement.slug} statement={statement} filters={filters} />
        )) : filtered ? (
          <NoResults what="statements" />
        ) : (
          <EmptyState title="No statement has been collected" heading="h3">
            <p>The statement list is empty. A dataset can be loaded before any sourced statement is stored. Emptiness here is not evidence that tracked people have never spoken.</p>
          </EmptyState>
        )}
      </section>
      <p className="meta">{page.page.total} matching statements</p>
      <Pager
        label="statements"
        previousHref={page.page.prev_cursor ? withCursor("/statements", params, page.page.prev_cursor) : null}
        nextHref={page.page.next_cursor ? withCursor("/statements", params, page.page.next_cursor) : null}
      />
    </>
  );
}
