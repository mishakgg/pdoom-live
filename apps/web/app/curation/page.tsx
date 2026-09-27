import { reviewStatus, listReviewQueue } from "@pdoom/db";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function CurationQueuePage({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
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
  return (
    <>
      <h1>Review queue</h1>
      <p className="lede">Priority is for the operator. It is not a judgment about the people. Only an explicit approval here can make a record human verified.</p>
      <dl className="audit">
        <dt>Unreviewed</dt><dd>{status.by_state.unreviewed ?? 0}</dd>
        <dt>Needs review</dt><dd>{status.by_state.needs_review ?? 0}</dd>
        <dt>Machine validated</dt><dd>{status.by_state.machine_validated ?? 0}</dd>
        <dt>Human verified</dt><dd>{status.by_state.human_verified ?? 0}</dd>
        <dt>Rejected</dt><dd>{status.by_state.rejected ?? 0}</dd>
        <dt>Numeric awaiting review</dt><dd>{status.explicit_numeric_awaiting_review}</dd>
        <dt>Missing horizon</dt><dd>{status.missing_horizon}</dd>
        <dt>Missing definition</dt><dd>{status.missing_definition}</dd>
      </dl>
      <form className="filters" method="get">
        <label>Type<select name="statement_type" defaultValue={params.statement_type ?? ""}><option value="">Any</option><option>explicit_numeric</option><option>explicit_qualitative</option><option>model_inferred_signal</option></select></label>
        <label>State<select name="review_state" defaultValue={params.review_state ?? ""}><option value="">Queue</option><option>unreviewed</option><option>needs_review</option><option>machine_validated</option></select></label>
        <label>Person<input name="person" defaultValue={params.person ?? ""} /></label>
        <label>Topic<input name="topic" defaultValue={params.topic ?? ""} /></label>
        <label>Source type<input name="source_type" defaultValue={params.source_type ?? ""} /></label>
        <label>Extractor<input name="extractor" defaultValue={params.extractor ?? ""} /></label>
        <label>From<input name="published_from" defaultValue={params.published_from ?? ""} placeholder="2024-01-01" /></label>
        <label>To<input name="published_to" defaultValue={params.published_to ?? ""} /></label>
        <label><input type="checkbox" name="missing_horizon" value="1" defaultChecked={params.missing_horizon === "1"} /> Missing horizon</label>
        <label><input type="checkbox" name="missing_definition" value="1" defaultChecked={params.missing_definition === "1"} /> Missing definition</label>
        <button type="submit">Filter</button>
      </form>
      {queue.map((item) => (
        <article className="card" key={item.slug}>
          <div className="row">
            <h2><Link href={`/curation/${item.slug}`}>{item.display_name}</Link></h2>
            <span className="meta">{item.statement_type} · {item.review_state} · priority {item.priority}</span>
          </div>
          <p>{item.normalized_text}</p>
          <p className="meta">{item.source_type} · {item.why}</p>
        </article>
      ))}
      {queue.length === 0 ? <p>No records match this queue.</p> : null}
    </>
  );
}
