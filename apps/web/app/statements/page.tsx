import { statementListQuerySchema } from "@pdoom/contracts";
import { InvalidCursorError, listStatements } from "@pdoom/db";
import { StatementCard } from "@/components/statement-bits";
import { InvalidFilters, Pager, StatementFilters } from "@/components/filters";
import { EmptyState, NoResults } from "@/components/states";
import { withCursor } from "@/lib/presentation";

export const dynamic = "force-dynamic";
export const metadata = { title: "Statements" };

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
  return (
    <>
      <h1>Statements</h1>
      <p className="lede">Each row names the claim, the person, the source, and whether the record is explicit or inferred. Open it for the original evidence.</p>
      <StatementFilters params={params} />
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
    if (error instanceof InvalidCursorError) return <InvalidFilters />;
    throw error;
  }
  return (
    <>
      <section aria-labelledby="statement-results">
        <h2 id="statement-results" className="sr-only">Matching statements</h2>
        {page.data.length ? page.data.map((statement) => (
          <StatementCard key={statement.slug} statement={statement} headingLevel="h3" />
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
