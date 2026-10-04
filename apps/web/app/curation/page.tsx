import { curationEnabled } from "@pdoom/contracts";
import { reviewStatus, listReviewQueue } from "@pdoom/db";
import Link from "next/link";
import { notFound } from "next/navigation";
import { formatWhen, phraseLabel, reviewLabel, typeLabel } from "@/lib/format";

export const dynamic = "force-dynamic";

const TYPES = ["explicit_numeric", "explicit_qualitative", "model_inferred_signal"] as const;
const STATES = ["unreviewed", "needs_review", "machine_validated"] as const;

export default async function CurationQueuePage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  if (!curationEnabled()) notFound();
  const params = await searchParams;
  const [status, queue] = await Promise.all([
    reviewStatus(),
    listReviewQueue({
      statement_type: params.statement_type,
      person: params.person,
      topic: params.topic,
      source_type: params.source_type,
      extractor: params.extractor,
      review_state: params.review_state,
      missing_horizon: params.missing_horizon === "1",
      missing_definition: params.missing_definition === "1",
      published_from: params.published_from,
      published_to: params.published_to,
    }),
  ]);
  const active = Object.entries(params).some(([, value]) => Boolean(value));
  return (
    <>
      <h1>Review queue</h1>
      <p className="lede">Priority orders the operator’s queue. It is not a judgment about the people. Only an explicit approval here can make a record human verified.</p>
      <dl className="stat-strip">
        <div><dt>Unreviewed</dt><dd>{status.by_state.unreviewed ?? 0}</dd></div>
        <div><dt>Needs review</dt><dd>{status.by_state.needs_review ?? 0}</dd></div>
        <div><dt>Machine validated</dt><dd>{status.by_state.machine_validated ?? 0}</dd></div>
        <div><dt>Human verified</dt><dd>{status.by_state.human_verified ?? 0}</dd></div>
        <div><dt>Rejected</dt><dd>{status.by_state.rejected ?? 0}</dd></div>
        <div><dt>Numeric awaiting review</dt><dd>{status.explicit_numeric_awaiting_review}</dd></div>
        <div><dt>Missing horizon</dt><dd>{status.missing_horizon}</dd></div>
        <div><dt>Missing definition</dt><dd>{status.missing_definition}</dd></div>
      </dl>
      <form className="filters" method="get">
        <label>Type
          <select name="statement_type" defaultValue={params.statement_type ?? ""}>
            <option value="">Any</option>
            {TYPES.map((type) => <option key={type} value={type}>{typeLabel(type)}</option>)}
          </select>
        </label>
        <label>State
          <select name="review_state" defaultValue={params.review_state ?? ""}>
            <option value="">Queue</option>
            {STATES.map((state) => <option key={state} value={state}>{reviewLabel(state)}</option>)}
          </select>
        </label>
        <label>Person<input name="person" defaultValue={params.person ?? ""} /></label>
        <label>Topic<input name="topic" defaultValue={params.topic ?? ""} /></label>
        <label>Source type<input name="source_type" defaultValue={params.source_type ?? ""} /></label>
        <label>Extractor<input name="extractor" defaultValue={params.extractor ?? ""} /></label>
        <label>From<input type="date" name="published_from" defaultValue={params.published_from ?? ""} /></label>
        <label>To<input type="date" name="published_to" defaultValue={params.published_to ?? ""} /></label>
        <label className="check-row"><input type="checkbox" name="missing_horizon" value="1" defaultChecked={params.missing_horizon === "1"} /> Missing horizon</label>
        <label className="check-row"><input type="checkbox" name="missing_definition" value="1" defaultChecked={params.missing_definition === "1"} /> Missing definition</label>
        <button type="submit">Filter</button>
        {active ? <Link className="button secondary" href="/curation">Reset filters</Link> : null}
      </form>
      {queue.length === 0 ? <p>No records match this queue.</p> : (
        <div className="chart-scroll">
          <table className="queue-table">
            <caption className="sr-only">{queue.length} records in this queue view</caption>
            <thead>
              <tr>
                <th scope="col">Person</th>
                <th scope="col">Statement</th>
                <th scope="col">Type</th>
                <th scope="col">Review</th>
                <th scope="col">Source</th>
                <th scope="col">Attention</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((item) => (
                <tr key={item.slug}>
                  <td data-label="Person"><Link href={`/curation/${item.slug}`}>{item.display_name}</Link></td>
                  <td data-label="Statement">
                    <Link href={`/curation/${item.slug}`}>{item.normalized_text}</Link>
                    <p className="meta">Forecast made {formatWhen(item.event_time)} · priority {item.priority}</p>
                  </td>
                  <td data-label="Type">{typeLabel(item.statement_type)}</td>
                  <td data-label="Review">
                    {reviewLabel(item.review_state)}
                    {item.stored_review_state !== item.review_state ? (
                      <p className="meta">Stored {reviewLabel(item.stored_review_state)}. The row shows the effective state.</p>
                    ) : null}
                    {item.recommended_review_state ? (
                      <p className="meta">Machine recommendation: {reviewLabel(item.recommended_review_state)}. Not human verification.</p>
                    ) : null}
                  </td>
                  <td data-label="Source">
                    {item.source_name}
                    <p className="meta">
                      {phraseLabel(item.source_type)}
                      {item.participant_role ? ` · ${phraseLabel(item.participant_role)}` : ""}
                      {item.value_label ? ` · ${item.value_label}` : ""}
                    </p>
                  </td>
                  <td data-label="Attention">{item.why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
