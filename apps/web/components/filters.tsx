import { isPublicReviewState, PERSON_STATUSES, REVIEW_STATES, STATEMENT_TYPES } from "@pdoom/contracts";
import Link from "next/link";
import { EntitySelect, type EntitySelection } from "@/components/entity-select";
import type { FilterLabels } from "@/lib/entity-labels";
import { reviewLabel, typeLabel } from "@/lib/format";
import {
  filterStateKey,
  personStatusLabel,
  type ResearchFilterKey,
} from "@/lib/presentation";

function selection(label: FilterLabels[keyof FilterLabels]): EntitySelection | null {
  if (!label) return null;
  return { slug: label.slug, name: label.name, detail: label.detail };
}

const FILTER_NAMES: Record<ResearchFilterKey, string> = {
  q: "text",
  person: "person",
  organization: "organization",
  source: "source",
  topic: "topic",
  statement_type: "statement type",
  review_state: "review",
  from: "from date",
  to: "to date",
};

const FILTER_ORDER = [
  "q",
  "person",
  "organization",
  "source",
  "topic",
  "statement_type",
  "review_state",
  "status",
  "type",
  "from",
  "to",
];

const SKIPPED_PARAMS = new Set(["cursor", "limit"]);

function filterValue(key: string, value: string, labels: FilterLabels): string {
  if (key === "person" && labels.person) return `${labels.person.name} (${labels.person.detail})`;
  if (key === "organization" && labels.organization) return `${labels.organization.name} (${labels.organization.detail})`;
  if (key === "source" && labels.source) return `${labels.source.name} (${labels.source.detail})`;
  if (key === "topic" && labels.topic) return labels.topic.name;
  if (key === "statement_type") return typeLabel(value);
  if (key === "review_state") return reviewLabel(value);
  if (key === "status") return personStatusLabel(value);
  if (key === "from") return `from ${value}`;
  if (key === "to") return `to ${value}`;
  return value;
}

function withoutParam(path: string, params: Record<string, string | undefined>, key: string): string {
  const search = new URLSearchParams();
  for (const name of orderedKeys(params)) {
    if (name === key) continue;
    const value = params[name];
    if (value) search.set(name, value);
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

function orderedKeys(params: Record<string, string | undefined>): string[] {
  const present = Object.entries(params)
    .filter((entry): entry is [string, string] => Boolean(entry[1]) && !SKIPPED_PARAMS.has(entry[0]))
    .map((entry) => entry[0]);
  return [
    ...FILTER_ORDER.filter((key) => present.includes(key)),
    ...present.filter((key) => !FILTER_ORDER.includes(key)).sort(),
  ];
}

export function ActiveFilters({
  path,
  params,
  labels,
}: {
  path: string;
  params: Record<string, string | undefined>;
  labels: FilterLabels;
}) {
  const keys = orderedKeys(params);
  if (!keys.length) return null;
  return (
    <div className="active-filters">
      <h2 className="sr-only">Active filters</h2>
      <ul>
        {keys.map((key) => {
          const name = FILTER_NAMES[key as ResearchFilterKey] ?? key.replaceAll("_", " ");
          return (
            <li key={key}>
              <span>{name}: {filterValue(key, params[key] ?? "", labels)}</span>
              <Link href={withoutParam(path, params, key)}>Remove {name}</Link>
            </li>
          );
        })}
      </ul>
      <Link href={path}>Clear all filters</Link>
    </div>
  );
}

export function PeopleFilters({
  params,
  labels = { person: null, organization: null, source: null, topic: null },
}: {
  params: Record<string, string | undefined>;
  labels?: FilterLabels;
}) {
  return (
    <form key={filterStateKey(params)} className="filters" method="get" aria-describedby="people-filter-note">
      <p id="people-filter-note" className="meta">
        Choose an organization by name. The address keeps its stable identifier. Apply writes this address. Remove and Clear all change the address immediately.
      </p>
      <label>
        Name
        <input name="q" defaultValue={params.q ?? ""} />
      </label>
      <EntitySelect kind="organization" label="Organization" name="organization" selected={selection(labels.organization)} />
      <label>
        Status
        <select name="status" defaultValue={params.status ?? ""}>
          <option value="">Any</option>
          {PERSON_STATUSES.map((status) => (
            <option key={status} value={status}>{personStatusLabel(status)}</option>
          ))}
        </select>
      </label>
      <button type="submit">Apply filters</button>
      <ActiveFilters path="/people" params={params} labels={labels} />
    </form>
  );
}

export function StatementFilters({
  params,
  labels = { person: null, organization: null, source: null, topic: null },
}: {
  params: Record<string, string | undefined>;
  labels?: FilterLabels;
}) {
  return (
    <form key={filterStateKey(params)} className="filters" method="get" aria-describedby="statement-filter-note">
      <p id="statement-filter-note" className="meta">
        Choose a person, organization, source, or topic by name. The address keeps the stable identifier. Dates filter event time in UTC. Apply writes this address.
      </p>
      <label>
        Text
        <input name="q" defaultValue={params.q ?? ""} />
      </label>
      <EntitySelect kind="person" label="Person" name="person" selected={selection(labels.person)} />
      <EntitySelect kind="organization" label="Organization" name="organization" selected={selection(labels.organization)} />
      <EntitySelect kind="source" label="Source" name="source" selected={selection(labels.source)} />
      <EntitySelect kind="topic" label="Topic" name="topic" selected={selection(labels.topic)} />
      <label>
        Type
        <select name="statement_type" defaultValue={params.statement_type ?? ""}>
          <option value="">Any</option>
          {STATEMENT_TYPES.map((type) => (
            <option key={type} value={type}>{typeLabel(type)}</option>
          ))}
        </select>
      </label>
      <label>
        Review
        <select name="review_state" defaultValue={params.review_state ?? ""}>
          <option value="">Any</option>
          {REVIEW_STATES.filter(isPublicReviewState).map((state) => (
            <option key={state} value={state}>{reviewLabel(state)}</option>
          ))}
        </select>
      </label>
      <label>
        From date
        <input type="date" name="from" defaultValue={params.from ?? ""} />
      </label>
      <label>
        To date
        <input type="date" name="to" defaultValue={params.to ?? ""} />
      </label>
      <button type="submit">Apply filters</button>
      <ActiveFilters path="/statements" params={params} labels={labels} />
    </form>
  );
}

export function Pager({
  label,
  previousHref,
  nextHref,
}: {
  label: string;
  previousHref: string | null;
  nextHref: string | null;
}) {
  if (!previousHref && !nextHref) return null;
  return (
    <nav className="pager" aria-label={`${label} pages`}>
      {previousHref ? <Link className="button secondary" href={previousHref}>Previous {label}</Link> : null}
      {nextHref ? <Link className="button" href={nextHref}>Next {label}</Link> : null}
    </nav>
  );
}

export function InvalidFilters() {
  return <p className="warning" role="alert">Those filters are not valid. Adjust the query and try again.</p>;
}
