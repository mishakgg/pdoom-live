import { STATEMENT_TYPES, STATEMENT_TYPE_LABELS, parseSearchParams, searchQuerySchema, SEARCH_ENTITY_TYPES } from "@pdoom/contracts";
import { searchPublic } from "@pdoom/db";
import { SearchResults } from "@/components/search-results";
import { canonicalOrigin, hasDiscoveryFilter, listPageFields, pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  return pageMetadata(canonicalOrigin(), listPageFields("search", hasDiscoveryFilter(params)));
}

const TYPE_LABEL: Record<(typeof SEARCH_ENTITY_TYPES)[number], string> = {
  person: "People",
  organization: "Organizations",
  statement: "Statements",
  topic: "Topics",
  source: "Sources",
  source_item: "Source item titles",
};

function Filters({ params }: { params: Record<string, string | undefined> }) {
  return (
    <form className="filters" method="get" action="/search">
      <label>Text<input name="q" defaultValue={params.q ?? ""} required maxLength={200} /></label>
      <label>
        Entity
        <select name="type" defaultValue={params.type ?? ""}>
          <option value="">All public types</option>
          {SEARCH_ENTITY_TYPES.map((type) => (
            <option key={type} value={type}>{TYPE_LABEL[type]}</option>
          ))}
        </select>
      </label>
      <label>Topic slug<input name="topic" defaultValue={params.topic ?? ""} /></label>
      <label>Person slug<input name="person" defaultValue={params.person ?? ""} /></label>
      <label>
        Statement class
        <select name="statement_type" defaultValue={params.statement_type ?? ""}>
          <option value="">Any</option>
          {STATEMENT_TYPES.map((type) => (
            <option key={type} value={type}>{STATEMENT_TYPE_LABELS[type]}</option>
          ))}
        </select>
      </label>
      <label>From<input type="date" name="from" defaultValue={params.from ?? ""} /></label>
      <label>To<input type="date" name="to" defaultValue={params.to ?? ""} /></label>
      <button type="submit">Search</button>
    </form>
  );
}

export default async function SearchPage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  return (
    <>
      <h1>Search</h1>
      <p className="lede">
        Search public people, organizations, statements, topics, sources, and source-item titles.
        Rejected and unreviewed statements, review notes, and unpublished source bodies are not included. Needs-review statements stay visible and are not labeled verified. Match labels describe the rule that ranked the row.
      </p>
      <Filters params={params} />
      <Results params={params} />
    </>
  );
}

async function Results({ params }: { params: Record<string, string | undefined> }) {
  if (!params.q?.trim()) {
    return <p className="meta">Enter a name, topic, or phrase. Two or more letters work best.</p>;
  }
  let parsed;
  try {
    const cleaned = Object.fromEntries(
      Object.entries(params).filter((entry): entry is [string, string] => Boolean(entry[1])),
    );
    parsed = searchQuerySchema.safeParse(parseSearchParams(new URLSearchParams(cleaned)));
  } catch {
    return <p className="warning">Those filters are not valid. Adjust the query and try again.</p>;
  }
  if (!parsed.success) {
    return <p className="warning">Those filters are not valid. Adjust the query and try again.</p>;
  }
  const result = await searchPublic(parsed.data);
  const queryString = new URLSearchParams(
    Object.entries(params).filter((entry): entry is [string, string] => Boolean(entry[1]) && entry[0] !== "cursor"),
  ).toString();
  return <SearchResults result={result} queryString={queryString} />;
}
