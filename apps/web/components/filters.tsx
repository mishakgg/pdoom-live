import { isPublicReviewState, PERSON_STATUSES, REVIEW_STATES, STATEMENT_TYPES } from "@pdoom/contracts";
import Link from "next/link";
import { reviewLabel, typeLabel } from "@/lib/format";
import { personStatusLabel } from "@/lib/presentation";

export function PeopleFilters({ params }: { params: Record<string, string | undefined> }) {
  return (
    <form className="filters" method="get" aria-describedby="people-filter-note">
      <p id="people-filter-note" className="meta">Organization uses the organization slug.</p>
      <label>
        Name
        <input name="q" defaultValue={params.q ?? ""} />
      </label>
      <label>
        Organization
        <input name="organization" defaultValue={params.organization ?? ""} />
      </label>
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
    </form>
  );
}

export function StatementFilters({ params }: { params: Record<string, string | undefined> }) {
  return (
    <form className="filters" method="get" aria-describedby="statement-filter-note">
      <p id="statement-filter-note" className="meta">Person, organization, source, and topic use record slugs. Dates filter event time in UTC.</p>
      <label>
        Text
        <input name="q" defaultValue={params.q ?? ""} />
      </label>
      <label>
        Person
        <input name="person" defaultValue={params.person ?? ""} />
      </label>
      <label>
        Organization
        <input name="organization" defaultValue={params.organization ?? ""} />
      </label>
      <label>
        Source
        <input name="source" defaultValue={params.source ?? ""} />
      </label>
      <label>
        Topic
        <input name="topic" defaultValue={params.topic ?? ""} />
      </label>
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
