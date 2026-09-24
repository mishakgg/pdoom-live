import { statementListQuerySchema } from "@pdoom/contracts";
import { listStatements } from "@pdoom/db";
import { StatementCard } from "@/components/statement-bits";
import Link from "next/link";
import { STATEMENT_TYPES, REVIEW_STATES } from "@pdoom/contracts";

export const dynamic = "force-dynamic";
export const metadata = { title: "Statements" };

export default async function StatementsPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const cleaned = Object.fromEntries(Object.entries(params).filter((entry) => entry[1]));
  const parsed = statementListQuerySchema.safeParse({
    ...cleaned,
    limit: params.limit ?? 10,
  });
  if (!parsed.success) {
    return (
      <>
        <h1>Statements</h1>
        <p className="warning">Those filters are not valid. Adjust the query and try again.</p>
      </>
    );
  }
  const page = await listStatements(parsed.data);
  const preserve = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value && key !== "cursor") preserve.set(key, value);
  }
  return (
    <>
      <h1>Statements</h1>
      <p className="lede">List rows carry the claim, source label, and class. Evidence text is on the statement page.</p>
      <form className="filters" method="get">
        <label>Text<input name="q" defaultValue={params.q ?? ""} /></label>
        <label>Person<input name="person" defaultValue={params.person ?? ""} /></label>
        <label>Organization<input name="organization" defaultValue={params.organization ?? ""} /></label>
        <label>Source<input name="source" defaultValue={params.source ?? ""} /></label>
        <label>Topic<input name="topic" defaultValue={params.topic ?? ""} /></label>
        <label>
          Type
          <select name="statement_type" defaultValue={params.statement_type ?? ""}>
            <option value="">Any</option>
            {STATEMENT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
        </label>
        <label>
          Review
          <select name="review_state" defaultValue={params.review_state ?? ""}>
            <option value="">Any</option>
            {REVIEW_STATES.map((state) => <option key={state} value={state}>{state}</option>)}
          </select>
        </label>
        <label>From<input type="date" name="from" defaultValue={params.from ?? ""} /></label>
        <label>To<input type="date" name="to" defaultValue={params.to ?? ""} /></label>
        <button type="submit">Apply</button>
      </form>
      {page.data.map((statement) => <StatementCard key={statement.slug} statement={statement} />)}
      <p className="meta">{page.page.total} matching statements</p>
      <div className="pager">
        {page.page.prev_cursor ? <Link className="button secondary" href={`/statements?${preserve.toString()}&cursor=${page.page.prev_cursor}`}>Previous</Link> : null}
        {page.page.next_cursor ? <Link className="button" href={`/statements?${preserve.toString()}&cursor=${page.page.next_cursor}`}>Next</Link> : null}
      </div>
    </>
  );
}
