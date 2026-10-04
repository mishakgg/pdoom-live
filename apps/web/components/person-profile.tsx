import Link from "next/link";
import { HistoryPreview } from "@/components/history-preview";
import { ExternalLink, ReviewBadge, StatementCard, type StatementCardData } from "@/components/statement-bits";
import { countLabel, formatWhen, isHumanVerified, phraseLabel, reviewLabel, typeLabel } from "@/lib/format";
import {
  NO_STATEMENT_COLLECTED,
  NO_STATEMENT_COLLECTED_NOTE,
  affiliationDates,
  freshnessLabel,
  identityGroup,
  personStatusLabel,
  statementsHref,
  topicResearchHref,
  type ResearchFilters,
} from "@/lib/presentation";

type Affiliation = {
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  confidence_level: string;
  verification_detail: string | null;
  review_state: string;
  settled: boolean;
  organization: { slug: string; name: string };
};

type Identity = {
  namespace: string;
  external_id: string;
  canonical_url: string | null;
  handle: string | null;
  verification_method: string;
  verification_detail: string | null;
  confidence_level: string;
  review_state: string;
  settled: boolean;
  verified_at: string | null;
};

type PersonSource = {
  slug: string;
  name: string;
  source_type: string;
  canonical_url: string;
  review_state: string;
  settled: boolean;
  enabled: boolean;
  last_success_at: string | null;
  freshness: string;
};

export type PersonProfileData = {
  slug: string;
  display_name: string;
  bio_short: string;
  status: string;
  inclusion_reason: string;
  cohort_tags: string[];
  updated_at: string | null;
  affiliations: Affiliation[];
  identities: Identity[];
  sources: PersonSource[];
  statements: StatementCardData[];
  statement_total: number;
};

function IdentityItems({ identities, established }: { identities: Identity[]; established: boolean }) {
  if (!identities.length) return <p>None recorded.</p>;
  return (
    <ul className="source-index">
      {identities.map((identity) => {
        const label = identity.handle ?? identity.external_id;
        return (
          <li key={`${identity.namespace}-${identity.external_id}`}>
            {established ? (
              <p>
                {identity.canonical_url ? (
                  <ExternalLink href={identity.canonical_url}>{label}</ExternalLink>
                ) : (
                  label
                )}
                <span className="meta">
                  {" · "}
                  {phraseLabel(identity.namespace)}
                  {" · "}
                  {phraseLabel(identity.verification_method)}
                  {identity.verification_detail ? ` (${identity.verification_detail})` : ""}
                  {" · "}
                  {phraseLabel(identity.confidence_level)} confidence
                </span>
              </p>
            ) : (
              <>
                <p>
                  <ReviewBadge state={identity.review_state} />{" "}
                  {phraseLabel(identity.namespace)} · {label}
                </p>
                <p>
                  {identity.review_state === "machine_validated"
                    ? "Machine validated. Not human verified."
                    : "Candidate record. Not an established identity."}
                </p>
                {identity.canonical_url ? (
                  <p>
                    <ExternalLink href={identity.canonical_url}>{identity.canonical_url}</ExternalLink>
                  </p>
                ) : null}
                <p className="meta">
                  {phraseLabel(identity.verification_method)}
                  {identity.verification_detail ? ` · ${identity.verification_detail}` : ""}
                  {" · "}
                  {phraseLabel(identity.confidence_level)} confidence
                  {" · "}
                  {reviewLabel(identity.review_state)}
                </p>
              </>
            )}
          </li>
        );
      })}
    </ul>
  );
}

const STATEMENT_CLASSES = ["explicit_numeric", "explicit_qualitative", "model_inferred_signal"] as const;

export function PersonProfile({
  person,
  navigation,
}: {
  person: PersonProfileData;
  navigation?: { filters: ResearchFilters; narrowed: boolean; unfilteredTotal: number };
}) {
  const verifiedCurrent = person.affiliations.filter((item) => item.settled && !item.end_date);
  const verifiedHistory = person.affiliations.filter((item) => item.settled && item.end_date);
  const unestablishedAffiliations = person.affiliations.filter((item) => !item.settled);
  const verifiedIdentities = person.identities.filter((item) => identityGroup(item.review_state) === "verified");
  const machineIdentities = person.identities.filter((item) => identityGroup(item.review_state) === "machine");
  const unestablishedIdentities = person.identities.filter((item) => identityGroup(item.review_state) === "unestablished");
  const freshness = { current: 0, aging: 0, stale: 0, never_checked: 0 };
  for (const source of person.sources) {
    if (source.freshness in freshness) freshness[source.freshness as keyof typeof freshness] += 1;
  }
  const latestSuccess = person.sources
    .map((source) => source.last_success_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1) ?? null;
  const topics = new Map<string, { slug: string; name: string; count: number }>();
  for (const statement of person.statements) {
    for (const topic of statement.topics ?? []) {
      const existing = topics.get(topic.slug);
      if (existing) existing.count += 1;
      else topics.set(topic.slug, { slug: topic.slug, name: topic.name, count: 1 });
    }
  }
  const topicList = [...topics.values()].sort((a, b) => a.name.localeCompare(b.name));
  const shown = person.statements.length;
  const filters = navigation?.filters ?? { person: person.slug };
  const narrowed = navigation?.narrowed ?? false;
  const unfilteredTotal = navigation?.unfilteredTotal ?? person.statement_total;
  const statementHref = statementsHref(filters);
  const filteredOut = person.statement_total === 0 && unfilteredTotal > 0;

  return (
    <>
      <p className="kicker">Record status: {personStatusLabel(person.status)} · record updated {formatWhen(person.updated_at)}</p>
      {person.status === "review" ? (
        <p className="warning">This person record is in review. Inclusion is not fully settled.</p>
      ) : null}
      <h1>{person.display_name}</h1>
      <p className="lede">{person.bio_short}</p>
      <nav className="page-nav" aria-label="On this page">
        <a href="#statements">Statements</a>
        <a href="#forecasts">Forecasts</a>
        <a href="#changes">Changes</a>
        <a href="#why-included">Inclusion</a>
        <a href="#affiliation">Affiliation</a>
        <a href="#identities">Identities</a>
        <a href="#source-coverage">Collection</a>
      </nav>

      <section aria-labelledby="person-statements" id="statements">
        <h2 id="person-statements">Statements over time</h2>
        {filteredOut ? (
          <div className="warning" role="status">
            <p>No statement in this view matches the selected filters.</p>
            <p>
              {unfilteredTotal} public {unfilteredTotal === 1 ? "statement is" : "statements are"} collected for this person before these filters.
            </p>
            <p>
              <Link href={statementHref}>Open the paged statement list</Link>
            </p>
          </div>
        ) : (
          <HistoryPreview
            shown={shown}
            total={person.statement_total}
            href={statementHref}
            note={narrowed
              ? `${unfilteredTotal} public ${unfilteredTotal === 1 ? "statement is" : "statements are"} collected for this person before these filters.`
              : "Event time orders this list. Publication time and observation time are on each statement."}
          />
        )}
        {person.statement_total === 0 && !filteredOut ? (
          <>
            <p>{NO_STATEMENT_COLLECTED}</p>
            <p>{NO_STATEMENT_COLLECTED_NOTE}</p>
          </>
        ) : person.statement_total > 0 ? (
          <div className="timeline">
            {person.statements.map((statement) => (
              <StatementCard key={statement.slug} statement={statement} headingLevel="h3" filters={filters} />
            ))}
          </div>
        ) : null}
        <h3>Topics in this view</h3>
        <p className="meta">Topics attached to the statements shown above. A topic beyond this preview is reached from the paged list.</p>
        {topicList.length ? (
          <ul className="chips" aria-label="Topics on collected statements">
            {topicList.map((topic) => (
              <li key={topic.slug}>
                <Link href={topicResearchHref(topic.slug, filters)}>
                  {topic.name}
                  <span className="sr-only">, {countLabel(topic.count, "statement")} in this view</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>No topic is attached to a collected statement in this view.</p>
        )}
      </section>

      <section aria-labelledby="forecasts">
        <h2 id="forecasts">Forecasts</h2>
        <p className="meta">Counts below are the statements shown on this page. They are not a personal probability, and qualitative or inferred rows are not converted into one.</p>
        <ul className="relation-list">
          {STATEMENT_CLASSES.map((type) => {
            const count = person.statements.filter((statement) => statement.statement_type === type).length;
            return (
              <li key={type}>
                {countLabel(count, typeLabel(type))} in this view.{" "}
                <Link href={statementsHref(filters, { statement_type: type })}>All {typeLabel(type).toLowerCase()} records</Link>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="changes">
        <h2 id="changes">Changes</h2>
        <p>A supported revision is a recorded link between two statements. Open a statement to see whether a later one updates, retracts, clarifies, contradicts, or repeats an earlier one. This profile does not turn those links into an overall belief.</p>
        <p><Link href={statementHref}>Review this person&apos;s statements</Link></p>
      </section>

      <section className="panel" aria-labelledby="why-included">
        <h2 id="why-included">Why this record exists</h2>
        <p>{person.inclusion_reason}</p>
        {person.cohort_tags.length ? (
          <ul className="chips" aria-label="Cohort tags">
            {person.cohort_tags.map((tag) => (
              <li key={tag}>{tag}</li>
            ))}
          </ul>
        ) : (
          <p className="meta">No cohort tags recorded.</p>
        )}
      </section>

      <div className="grid-2 profile-facts">
        <section aria-labelledby="affiliation">
          <h2 id="affiliation">Affiliation</h2>
          <h3>Current and verified</h3>
          {verifiedCurrent.length ? (
            <ul className="source-index">
              {verifiedCurrent.map((affiliation) => (
                <li key={`${affiliation.organization.slug}-${affiliation.start_date}`}>
                  <p>{affiliation.role ?? "Role not recorded"} · {affiliation.organization.name}</p>
                  <p className="meta">
                    {affiliationDates(affiliation.start_date, affiliation.end_date, true)}
                    {" · "}
                    {phraseLabel(affiliation.confidence_level)} confidence
                    {" · "}
                    Human verified
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p>No human-verified current affiliation is recorded.</p>
          )}
          <h3>Verified history</h3>
          {verifiedHistory.length ? (
            <ul className="source-index">
              {verifiedHistory.map((affiliation) => (
                <li key={`${affiliation.organization.slug}-${affiliation.start_date}-past`}>
                  <p>{affiliation.role ?? "Role not recorded"} · {affiliation.organization.name}</p>
                  <p className="meta">{affiliationDates(affiliation.start_date, affiliation.end_date, true)} · Human verified</p>
                </li>
              ))}
            </ul>
          ) : (
            <p>No earlier verified affiliation is recorded.</p>
          )}
          <h3>Not established</h3>
          {unestablishedAffiliations.length ? (
            <ul className="source-index">
              {unestablishedAffiliations.map((affiliation) => (
                <li key={`${affiliation.organization.slug}-${affiliation.review_state}-${affiliation.start_date}`}>
                  <p>
                    <ReviewBadge state={affiliation.review_state} />{" "}
                    Candidate: {affiliation.role ?? "Role not recorded"} · {affiliation.organization.name}
                  </p>
                  <p>Not an established affiliation.</p>
                  <p className="meta">
                    {affiliationDates(affiliation.start_date, affiliation.end_date, false)}
                    {" · "}
                    {phraseLabel(affiliation.confidence_level)} confidence
                    {affiliation.verification_detail ? ` · ${affiliation.verification_detail}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p>No unresolved affiliation record.</p>
          )}
        </section>

        <section aria-labelledby="source-coverage">
          <h2 id="source-coverage">Source coverage</h2>
          <dl className="facts">
            <div>
              <dt>Linked sources</dt>
              <dd>{person.sources.length}</dd>
            </div>
            <div>
              <dt>Checked within 14 days</dt>
              <dd>{freshness.current}</dd>
            </div>
            <div>
              <dt>Aging</dt>
              <dd>{freshness.aging}</dd>
            </div>
            <div>
              <dt>Stale</dt>
              <dd>{freshness.stale}</dd>
            </div>
            <div>
              <dt>Never checked</dt>
              <dd>{freshness.never_checked}</dd>
            </div>
            <div>
              <dt>Collected statements</dt>
              <dd>{person.statement_total}</dd>
            </div>
          </dl>
          <p className="meta">Freshness describes collection checks, not whether this person has spoken.</p>
          <p className="meta">Latest successful check {formatWhen(latestSuccess)}</p>
          {person.sources.length === 0 ? (
            <p>No source is linked to this person. Missing sources are a coverage gap, separate from whether they have spoken in public.</p>
          ) : null}
          {person.sources.length > 0 && person.sources.every((source) => source.freshness === "never_checked") ? (
            <p>None of the linked sources has a successful check. That is a collection gap.</p>
          ) : null}
          {person.sources.length ? (
            <ul className="source-index">
              {person.sources.map((source) => (
                <li key={source.slug}>
                  <p>
                    <Link href={`/sources/${source.slug}`}>{source.name}</Link>
                    {isHumanVerified(source.review_state) ? null : (
                      <>
                        {" "}
                        <ReviewBadge state={source.review_state} />
                      </>
                    )}
                  </p>
                  <p className="meta">
                    {phraseLabel(source.source_type)}
                    {" · "}
                    {freshnessLabel(source.freshness)}
                    {" · "}
                    Last success {formatWhen(source.last_success_at)}
                    {" · "}
                    {source.enabled ? "Enabled" : "Disabled"}
                    {source.settled ? "" : " · not a settled source record"}
                  </p>
                  <p><ExternalLink href={source.canonical_url}>{source.canonical_url}</ExternalLink></p>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>

      <section aria-labelledby="identities">
        <h2 id="identities">Identities</h2>
        <div aria-labelledby="verified-identities">
          <h3 id="verified-identities">Human verified</h3>
          {verifiedIdentities.length ? (
            <IdentityItems identities={verifiedIdentities} established />
          ) : (
            <p>No human-verified public identity is recorded.</p>
          )}
        </div>
        <div aria-labelledby="machine-identities">
          <h3 id="machine-identities">Machine validated</h3>
          <p className="meta">A machine check is not human verification.</p>
          <IdentityItems identities={machineIdentities} established={false} />
        </div>
        <div aria-labelledby="unestablished-identities">
          <h3 id="unestablished-identities">Not established</h3>
          <p>Needs-review and unreviewed identities are candidates. They are not confirmed facts about this person.</p>
          <IdentityItems identities={unestablishedIdentities} established={false} />
        </div>
      </section>
    </>
  );
}
