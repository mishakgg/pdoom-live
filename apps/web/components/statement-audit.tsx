import Link from "next/link";
import { EvidenceBlock, ExternalLink, ReviewBadge, TypeBadge } from "@/components/statement-bits";
import { PartialCollectionNote, UnavailableState } from "@/components/states";
import { formatValue, formatWhen, phraseLabel, reviewLabel } from "@/lib/format";
import { evidenceSpan, missingValue, relationshipLabel, sourceMaterialState } from "@/lib/presentation";

export type StatementAuditData = {
  slug: string;
  statement_type: string;
  normalized_text: string;
  event_time: string | null;
  review_state: string;
  confidence: number | null;
  extractor_version: string;
  person: { slug: string; display_name: string };
  source: { slug: string; name: string; source_type: string };
  source_item: {
    slug: string;
    title: string | null;
    canonical_url: string;
    published_at: string | null;
    observed_at: string | null;
  };
  forecast: {
    question_key: string;
    question_text: string;
    value_type: string;
    value_numeric: number | null;
    value_min: number | null;
    value_max: number | null;
    unit: string | null;
    horizon_text: string | null;
    forecast_kind?: string | null;
    definition_text?: string | null;
    condition_text?: string | null;
    target_date_start?: string | null;
    target_date_end?: string | null;
    resolution_criteria?: string | null;
  } | null;
  topics: Array<{ slug: string; name: string }>;
  evidence: {
    segment_kind: string;
    start_char: number | null;
    end_char: number | null;
    start_ms: number | null;
    end_ms: number | null;
    text: string;
    context_text: string | null;
    segment_hash: string;
  };
  provenance: {
    content_hash: string;
    content_reference: string | null;
    language: string | null;
    published_timezone: string | null;
    collection_status: string;
    availability: string;
    extractor_name: string | null;
    prompt_contract_version: string | null;
    input_hash: string | null;
    model_name: string | null;
  };
  relationships: Array<{
    relationship_type: string;
    review_state: string;
    from_slug: string;
    to_slug: string;
  }>;
};

function targetDates(forecast: NonNullable<StatementAuditData["forecast"]>): string {
  if (!forecast.target_date_start && !forecast.target_date_end) return "Not stated";
  return `${forecast.target_date_start ?? "open"} – ${forecast.target_date_end ?? "open"}`;
}

export function StatementAudit({ statement }: { statement: StatementAuditData }) {
  const material = sourceMaterialState(statement.provenance.collection_status, statement.provenance.availability);
  const topics = Array.isArray(statement.topics) ? statement.topics : [];
  return (
    <article className="audit-record">
      <header className="audit-header">
        <p className="kicker">Statement audit</p>
        <h1>Statement by {statement.person.display_name}</h1>
        <p className="card-flags">
          <TypeBadge type={statement.statement_type} />
          <ReviewBadge state={statement.review_state} />
        </p>
        <dl className="facts">
          <div>
            <dt>Said by</dt>
            <dd><Link href={`/people/${statement.person.slug}`}>{statement.person.display_name}</Link></dd>
          </div>
          <div>
            <dt>When</dt>
            <dd><time dateTime={statement.event_time ?? undefined}>{formatWhen(statement.event_time)}</time></dd>
          </div>
          <div>
            <dt>Where</dt>
            <dd>
              <Link href={`/sources/${statement.source.slug}`}>{statement.source.name}</Link>
              <span className="meta"> · {phraseLabel(statement.source.source_type)}</span>
            </dd>
          </div>
          <div>
            <dt>Review</dt>
            <dd>{reviewLabel(statement.review_state)}</dd>
          </div>
        </dl>
      </header>

      <section aria-labelledby="original-evidence">
        <h2 id="original-evidence">Original evidence</h2>
        <p className="meta">Source text as stored. It is not rewritten, and it outranks the interpretation below.</p>
        {material === "unavailable" ? (
          <UnavailableState
            heading="h3"
            collectionStatus={statement.provenance.collection_status}
            availability={statement.provenance.availability}
          />
        ) : null}
        {material === "partial" ? <PartialCollectionNote /> : null}
        <EvidenceBlock text={statement.evidence.text} context={statement.evidence.context_text} prominent />
        <dl className="audit">
          <dt>Source item</dt>
          <dd>
            <Link href={`/source-items/${statement.source_item.slug}`}>
              {statement.source_item.title ?? "Untitled source item"}
            </Link>
          </dd>
          <dt>Canonical URL</dt>
          <dd><ExternalLink href={statement.source_item.canonical_url}>{statement.source_item.canonical_url}</ExternalLink></dd>
          <dt>Evidence span</dt>
          <dd>{evidenceSpan(statement.evidence)}</dd>
          <dt>Published</dt>
          <dd>
            {formatWhen(statement.source_item.published_at)}
            {statement.source_item.published_at && statement.provenance.published_timezone
              ? ` (${statement.provenance.published_timezone})`
              : ""}
          </dd>
          <dt>Observed</dt>
          <dd>{formatWhen(statement.source_item.observed_at)}</dd>
        </dl>
      </section>

      <section className="interpretation" aria-labelledby="normalized-interpretation">
        <h2 id="normalized-interpretation">Normalized interpretation</h2>
        <p className="kicker">Record reading, not a quotation</p>
        {statement.statement_type === "model_inferred_signal" ? (
          <p className="warning">This is a model-inferred signal. It is not a quotation and it is not this person’s probability.</p>
        ) : null}
        {statement.statement_type === "explicit_qualitative" ? (
          <p className="warning">Explicit qualitative view. No probability has been inferred from the wording.</p>
        ) : null}
        <p className="lede">{statement.normalized_text}</p>
        {topics.length ? (
          <ul className="chips" aria-label="Topics">
            {topics.map((topic) => (
              <li key={topic.slug}>
                <Link href={`/topics/${topic.slug}`}>{topic.name}</Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="meta">No topic recorded</p>
        )}
      </section>

      <section aria-labelledby="forecast-structure">
        <h2 id="forecast-structure">Forecast structure</h2>
        {statement.forecast ? (
          <dl className="audit">
            <dt>Kind</dt>
            <dd>{phraseLabel(statement.forecast.forecast_kind ?? "forecast")}</dd>
            <dt>Question</dt>
            <dd>{statement.forecast.question_text}</dd>
            <dt>Question key</dt>
            <dd className="hash">{statement.forecast.question_key}</dd>
            <dt>Definition</dt>
            <dd>{missingValue(statement.forecast.definition_text)}</dd>
            <dt>Condition</dt>
            <dd>{missingValue(statement.forecast.condition_text, "None stated")}</dd>
            <dt>Horizon</dt>
            <dd>{missingValue(statement.forecast.horizon_text)}</dd>
            <dt>Target dates</dt>
            <dd>{targetDates(statement.forecast)}</dd>
            <dt>Value</dt>
            <dd>{formatValue(statement.forecast)}</dd>
            <dt>Unit</dt>
            <dd>{missingValue(statement.forecast.unit)}</dd>
            {statement.forecast.resolution_criteria ? (
              <>
                <dt>Resolution</dt>
                <dd>{statement.forecast.resolution_criteria}</dd>
              </>
            ) : null}
          </dl>
        ) : (
          <>
            <p>No structured forecast is attached. No probability was inferred to fill that gap.</p>
            <dl className="audit">
              <dt>Horizon</dt>
              <dd>Not stated</dd>
              <dt>Value</dt>
              <dd>—</dd>
            </dl>
          </>
        )}
      </section>

      <section aria-labelledby="provenance">
        <h2 id="provenance">Provenance</h2>
        <dl className="audit">
          <dt>Source</dt>
          <dd>
            <Link href={`/sources/${statement.source.slug}`}>{statement.source.name}</Link>
            {" · "}
            {phraseLabel(statement.source.source_type)}
          </dd>
          <dt>Canonical URL</dt>
          <dd><ExternalLink href={statement.source_item.canonical_url}>{statement.source_item.canonical_url}</ExternalLink></dd>
          <dt>Collection</dt>
          <dd>{phraseLabel(statement.provenance.collection_status)} · {phraseLabel(statement.provenance.availability)}</dd>
          <dt>Language</dt>
          <dd>{missingValue(statement.provenance.language, "Not recorded")}</dd>
          <dt>Content reference</dt>
          <dd className="url">{missingValue(statement.provenance.content_reference, "Not recorded")}</dd>
          <dt>Content hash</dt>
          <dd className="hash">{statement.provenance.content_hash}</dd>
          <dt>Evidence hash</dt>
          <dd className="hash">{statement.evidence.segment_hash}</dd>
          <dt>Extractor</dt>
          <dd>{statement.provenance.extractor_name ?? statement.extractor_version} · {statement.extractor_version}</dd>
          <dt>Model</dt>
          <dd>{missingValue(statement.provenance.model_name, "Not recorded")}</dd>
          <dt>Prompt contract</dt>
          <dd>{missingValue(statement.provenance.prompt_contract_version, "Not recorded")}</dd>
          <dt>Input hash</dt>
          <dd className="hash">{missingValue(statement.provenance.input_hash, "Not recorded")}</dd>
          <dt>Extractor confidence</dt>
          <dd>{statement.confidence === null ? "Not recorded" : statement.confidence.toFixed(2)}</dd>
          <dt>Review state</dt>
          <dd>{reviewLabel(statement.review_state)}</dd>
        </dl>
      </section>

      <section aria-labelledby="relations">
        <h2 id="relations">Revisions and relations</h2>
        {statement.relationships.length ? (
          <ul className="relation-list">
            {statement.relationships.map((relation) => (
              <li key={`${relation.from_slug}-${relation.to_slug}-${relation.relationship_type}`}>
                {relationshipLabel(relation.relationship_type)}
                {relation.review_state === "human_verified" ? "" : ` · ${reviewLabel(relation.review_state)}`}
                {": "}
                <Link href={`/statements/${relation.from_slug}`}>
                  From statement
                  <span className="sr-only"> {relation.from_slug}</span>
                </Link>
                {" → "}
                <Link href={`/statements/${relation.to_slug}`}>
                  To statement
                  <span className="sr-only"> {relation.to_slug}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>No linked revision is recorded.</p>
        )}
      </section>
    </article>
  );
}
