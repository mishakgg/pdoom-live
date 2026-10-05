import { listPeople } from "@pdoom/db";
import { peopleListQuerySchema } from "@pdoom/contracts";
import Link from "next/link";
import { InvalidFilters, Pager, PeopleFilters } from "@/components/filters";
import { EmptyState, NoResults } from "@/components/states";
import { isInvalidCursor } from "@/lib/http";
import { typeLabel } from "@/lib/format";
import { resolveFilterLabels } from "@/lib/entity-labels";
import { canonicalOrigin, hasDiscoveryFilter, listPageFields, pageMetadata } from "@/lib/seo";
import { NO_STATEMENT_COLLECTED, NO_STATEMENT_COLLECTED_NOTE, affiliationFact, personStatusLabel, withCursor } from "@/lib/presentation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  return pageMetadata(canonicalOrigin(), listPageFields("people", hasDiscoveryFilter(params)));
}

function filtered(params: Record<string, string | undefined>): boolean {
  return Boolean(params.q || params.organization || params.status);
}

export default async function PeoplePage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const labels = await resolveFilterLabels({ organization: params.organization });
  const parsed = peopleListQuerySchema.safeParse({
    q: params.q || undefined,
    organization: params.organization || undefined,
    status: params.status || undefined,
    cursor: params.cursor || undefined,
    limit: params.limit ?? 20,
  });
  const results = parsed.success
    ? await PeopleResults({ params, query: parsed.data, filtered: filtered(params) })
    : <InvalidFilters />;
  return (
    <>
      <h1>Tracked people</h1>
      <p className="lede">Every person has an inclusion reason. Similar names are not merged. A missing statement means nothing has been collected, not that the person has never spoken.</p>
      <p>The tracked set is a defined cohort and not all AI researchers. The count is the cohort membership shown on this page.</p>
      <PeopleFilters params={params} labels={labels} />
      {results}
    </>
  );
}

async function PeopleResults({
  params,
  query,
  filtered,
}: {
  params: Record<string, string | undefined>;
  query: ReturnType<typeof peopleListQuerySchema.parse>;
  filtered: boolean;
}) {
  let page;
  try {
    page = await listPeople(query);
  } catch (error) {
    if (isInvalidCursor(error)) return <InvalidFilters />;
    throw error;
  }
  return (
    <>
      {page.data.length ? (
        <div className="person-list">
          {page.data.map((person) => {
            const affiliation = affiliationFact(person.organization);
            const counts = Object.entries(person.statement_counts);
            return (
              <article className="card" key={person.slug}>
                <p className="meta">{personStatusLabel(person.status)}</p>
                <h2>
                  <Link href={`/people/${person.slug}`}>{person.display_name}</Link>
                </h2>
                <p>{person.inclusion_reason}</p>
                <p>{affiliation.text}</p>
                {counts.length ? (
                  <p className="meta">
                    Collected statements: {counts.map(([type, count]) => `${count} ${typeLabel(type)}`).join(" · ")}
                  </p>
                ) : (
                  <>
                    <p>{NO_STATEMENT_COLLECTED}</p>
                    <p className="meta">{NO_STATEMENT_COLLECTED_NOTE}</p>
                  </>
                )}
              </article>
            );
          })}
        </div>
      ) : filtered ? (
        <NoResults what="people" />
      ) : (
        <EmptyState title="No people are loaded">
          <p>The person registry is empty. That is a dataset state, not a claim about who works on frontier AI.</p>
        </EmptyState>
      )}
      <p className="meta">{page.page.total} people</p>
      <Pager
        label="people"
        previousHref={page.page.prev_cursor ? withCursor("/people", params, page.page.prev_cursor) : null}
        nextHref={page.page.next_cursor ? withCursor("/people", params, page.page.next_cursor) : null}
      />
    </>
  );
}
