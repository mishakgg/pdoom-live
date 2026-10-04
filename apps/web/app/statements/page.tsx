import { statementListQuerySchema } from "@pdoom/contracts";
import { listStatements } from "@pdoom/db";
import { StatementCard } from "@/components/statement-bits";
import { InvalidFilters, Pager, StatementFilters } from "@/components/filters";
import { EmptyState, NoResults } from "@/components/states";
import { resolveFilterLabels } from "@/lib/entity-labels";
import { isInvalidCursor } from "@/lib/http";
import { canonicalOrigin, hasDiscoveryFilter, listPageFields, pageMetadata } from "@/lib/seo";
import { researchFilters, withCursor } from "@/lib/presentation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  return pageMetadata(canonicalOrigin(), listPageFields("statements", hasDiscoveryFilter(params)));
}

function filtered(params: Record<string, string | undefined>): boolean {
  return Object.entries(params).some(([key, value]) => key !== "cursor" && key !== "limit" && Boolean(value));
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
  return (
    <>
      <h1>Statements</h1>
      <p className="lede">Each row names the claim, the person, the source, and whether the record is explicit or inferred. Open it for the original evidence. This list is paged. The count is every match, including rows on other pages.</p>
      <StatementFilters params={params} labels={labels} />
      {!parsed.success ? <InvalidFilters /> : <StatementResults params={params} query={parsed.data} filtered={filtered(params)} />}
    </>
  );
}

async function StatementResults({
  params,
  query,
  filtered,
}: {
  params: Record<string, string | undefined>;
  query: ReturnType<typeof statementListQuerySchema.parse>;
  filtered: boolean;
}) {
  let page;
  try {
    page = await listStatements(query);
  } catch (error) {
    if (isInvalidCursor(error)) return <InvalidFilters />;
    throw error;
  }
  return (
    <>
      <section aria-labelledby="statement-results">
        <h2 id="statement-results" className="sr-only">Matching statements</h2>
        {page.data.length ? page.data.map((statement) => (
          <StatementCard key={statement.slug} statement={statement} headingLevel="h3" filters={researchFilters(params)} />
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
