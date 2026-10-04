import {
  STATEMENT_TYPES,
  type SearchEntityType,
  type SearchMatch,
  type SearchResponse,
  type SearchStatementHit,
} from "@pdoom/contracts";
import Link from "next/link";
import { formatWhen, phraseLabel } from "@/lib/format";
import { personStatusLabel, type ResearchFilters } from "@/lib/presentation";
import { ReviewBadge, StatementCard } from "./statement-bits";

const MATCH_LABEL: Record<SearchMatch, string> = {
  exact_text: "Exact text",
  exact_name: "Exact name",
  family_name: "Surname",
  name_prefix: "Name prefix",
  token_prefix: "Matching words",
  phrase: "Phrase",
  all_tokens: "All words",
  affiliation_role: "Affiliation role",
};

const CLASS_LABEL = {
  explicit_numeric: "Explicit numerical estimates",
  explicit_qualitative: "Explicit qualitative views",
  model_inferred_signal: "Model-inferred signals",
} as const;

function moreHref(base: string, type: string, cursor: string | null): string | null {
  if (!cursor) return null;
  const params = new URLSearchParams(base);
  params.set("type", type);
  params.delete("cursor");
  params.set("cursor", cursor);
  return `/search?${params.toString()}`;
}

function clip(text: string, max = 280): string {
  const flat = text.replace(/\s+/g, " ").trim();
  if (flat.length <= max) return flat;
  return `${flat.slice(0, max - 1).trimEnd()}…`;
}

export function SearchResults({
  result,
  queryString,
  filters,
}: {
  result: SearchResponse;
  queryString: string;
  filters?: ResearchFilters;
}) {
  const { groups } = result;
  const shown = new Set<SearchEntityType>(result.query.types);
  const total = result.query.types.reduce((sum, type) => sum + groups[type].page.total, 0);
  return (
    <div>
      <p className="meta" role="status">
        {total} public {total === 1 ? "match" : "matches"}
        {result.query.truncated ? " · extra words were ignored" : ""}
        {result.query.reason === "no_tokens" ? " · no searchable words" : ""}
      </p>
      {shown.has("person") ? <section className="search-kind" aria-labelledby="search-people">
        <h2 id="search-people">People</h2>
        {groups.person.page.total === 0 ? <p className="meta">No people matched.</p> : null}
        {groups.person.data.map((person) => {
          const sameName = groups.person.data.filter((other) => other.display_name === person.display_name).length > 1;
          return (
            <article className="card" key={person.slug}>
              <div className="row">
                <h3><Link href={`/people/${person.slug}`}>{person.display_name}</Link></h3>
                <span className="meta">{personStatusLabel(person.status)}</span>
              </div>
              <p className="meta">
                {person.organization ? `${person.organization.role ?? "Affiliate"} · ${person.organization.name}` : "No current affiliation"}
                {sameName ? ` · Record ${person.slug}` : ""}
                {" · "}
                {MATCH_LABEL[person.match]}
              </p>
            </article>
          );
        })}
        <More href={moreHref(queryString, "person", groups.person.page.next_cursor)} />
      </section> : null}
      {shown.has("organization") ? <section className="search-kind" aria-labelledby="search-organizations">
        <h2 id="search-organizations">Organizations</h2>
        {groups.organization.page.total === 0 ? <p className="meta">No organizations matched.</p> : null}
        {groups.organization.data.map((organization) => (
          <article className="card" key={organization.slug}>
            <h3><Link href={`/people?organization=${organization.slug}`}>{organization.name}</Link></h3>
            <p className="meta">
              {organization.organization_type}
              {organization.affiliation ? ` · ${organization.affiliation.role ?? "Affiliate"} · ${organization.affiliation.display_name}` : ""}
              {" · "}
              {MATCH_LABEL[organization.match]}
            </p>
          </article>
        ))}
        <More href={moreHref(queryString, "organization", groups.organization.page.next_cursor)} />
      </section> : null}
      {shown.has("statement") ? <section className="search-kind" aria-labelledby="search-statements">
        <h2 id="search-statements">Statements</h2>
        {groups.statement.page.total === 0 ? <p className="meta">No statements matched.</p> : null}
        {STATEMENT_TYPES.map((type) => {
          const rows = groups.statement.data.filter((statement) => statement.statement_type === type);
          if (!rows.length) return null;
          return (
            <div key={type}>
              <h3>{CLASS_LABEL[type]}</h3>
              {rows.map((statement) => (
                <SearchStatement key={statement.slug} statement={statement} filters={filters} />
              ))}
            </div>
          );
        })}
        <More href={moreHref(queryString, "statement", groups.statement.page.next_cursor)} />
      </section> : null}
      {shown.has("topic") ? <section className="search-kind" aria-labelledby="search-topics">
        <h2 id="search-topics">Topics</h2>
        {groups.topic.page.total === 0 ? <p className="meta">No topics matched.</p> : null}
        {groups.topic.data.map((topic) => (
          <article className="card" key={topic.slug}>
            <h3><Link href={`/topics/${topic.slug}`}>{topic.name}</Link></h3>
            <p>{clip(topic.definition)}</p>
            <p className="meta">{MATCH_LABEL[topic.match]}</p>
          </article>
        ))}
        <More href={moreHref(queryString, "topic", groups.topic.page.next_cursor)} />
      </section> : null}
      {shown.has("source") ? <section className="search-kind" aria-labelledby="search-sources">
        <h2 id="search-sources">Sources</h2>
        {groups.source.page.total === 0 ? <p className="meta">No sources matched.</p> : null}
        {groups.source.data.map((source) => (
          <article className="card" key={source.slug}>
            <div className="row">
              <h3><Link href={`/sources/${source.slug}`}>{source.name}</Link></h3>
              <span className="meta">{phraseLabel(source.source_type)}</span>
            </div>
            <p className="meta">
              {source.owner ? source.owner.display_name : "No owner"}
              {" · "}
              <ReviewBadge state={source.review_state} />
              {" · "}
              {MATCH_LABEL[source.match]}
            </p>
          </article>
        ))}
        <More href={moreHref(queryString, "source", groups.source.page.next_cursor)} />
      </section> : null}
      {shown.has("source_item") ? <section className="search-kind" aria-labelledby="search-items">
        <h2 id="search-items">Source item titles</h2>
        {groups.source_item.page.total === 0 ? <p className="meta">No source item titles matched.</p> : null}
        {groups.source_item.data.map((item) => (
          <article className="card" key={item.slug}>
            <h3><Link href={`/source-items/${item.slug}`}>{item.title ?? "Untitled source item"}</Link></h3>
            <p className="meta">
              {item.source.source_type} · <Link href={`/sources/${item.source.slug}`}>{item.source.name}</Link>
              {" · "}
              {formatWhen(item.published_at)}
              {" · "}
              {MATCH_LABEL[item.match]}
            </p>
          </article>
        ))}
        <More href={moreHref(queryString, "source_item", groups.source_item.page.next_cursor)} />
      </section> : null}
    </div>
  );
}

function SearchStatement({ statement, filters }: { statement: SearchStatementHit; filters?: ResearchFilters }) {
  return (
    <div>
      <StatementCard statement={{ ...statement, normalized_text: clip(statement.normalized_text) }} filters={filters} />
      <p className="meta">{MATCH_LABEL[statement.match]}</p>
    </div>
  );
}

function More({ href }: { href: string | null }) {
  if (!href) return null;
  return <p><Link className="button secondary" href={href}>More</Link></p>;
}
