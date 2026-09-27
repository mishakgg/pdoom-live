import { listPeople } from "@pdoom/db";
import { peopleListQuerySchema } from "@pdoom/contracts";
import Link from "next/link";
import { typeLabel } from "@/lib/format";
import { canonicalOrigin, hasDiscoveryFilter, listPageFields, pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  return pageMetadata(canonicalOrigin(), listPageFields("people", hasDiscoveryFilter(params)));
}

export default async function PeoplePage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const query = peopleListQuerySchema.parse({
    q: params.q || undefined,
    organization: params.organization || undefined,
    status: params.status || undefined,
    cursor: params.cursor || undefined,
    limit: params.limit ?? 20,
  });
  const page = await listPeople(query);
  return (
    <>
      <h1>Tracked people</h1>
      <p className="lede">Every person has an inclusion reason. Similar names are not merged.</p>
      <form className="filters" method="get">
        <label>Name<input name="q" defaultValue={params.q ?? ""} /></label>
        <label>Organization slug<input name="organization" defaultValue={params.organization ?? ""} /></label>
        <label>
          Status
          <select name="status" defaultValue={params.status ?? ""}>
            <option value="">Any</option>
            <option value="active">active</option>
            <option value="historical">historical</option>
            <option value="review">review</option>
          </select>
        </label>
        <button type="submit">Filter</button>
      </form>
      <div className="person-list">
        {page.data.map((person) => (
          <article className="card" key={person.slug}>
            <div className="row">
              <h2>
                <Link href={`/people/${person.slug}`}>{person.display_name}</Link>
              </h2>
              <span className="meta">{person.status}</span>
            </div>
            <p>{person.inclusion_reason}</p>
            <p className="meta">
              {person.organization ? `${person.organization.role ?? "Affiliate"} · ${person.organization.name}` : "No current affiliation"}
              {" · "}
              {Object.entries(person.statement_counts)
                .map(([type, count]) => `${count} ${typeLabel(type)}`)
                .join(" · ") || "No statements"}
            </p>
          </article>
        ))}
      </div>
      <p className="meta">{page.page.total} people</p>
      <div className="pager">
        {page.page.next_cursor ? <Link className="button" href={`/people?cursor=${page.page.next_cursor}`}>Next</Link> : null}
      </div>
    </>
  );
}
