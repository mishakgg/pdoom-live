import { QUESTION_TAXONOMY, REJECTION_REASONS, VALUE_TYPES } from "@pdoom/contracts";
import { getPool, getReviewItem } from "@pdoom/db";
import { CurationEvidence } from "@/components/curation-evidence";
import { ExternalLink } from "@/components/statement-bits";
import { formatWhen } from "@/lib/format";
import { submitReview } from "../actions";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function CurationItemPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = await getReviewItem(getPool(), slug);
  if (!item) notFound();
  const numeric = item.statement_type === "explicit_numeric";
  return (
    <>
      <p className="kicker"><Link href="/curation">Queue</Link> · {item.review_state}</p>
      <h1>{item.display_name}</h1>
      <p className="lede">{item.why ?? "Review the evidence before the extracted fields."}</p>
      <CurationEvidence text={item.evidence_text} context={item.observed_context} />
      <dl className="audit">
        <dt>Person</dt><dd><Link href={`/people/${item.person_slug}`}>{item.display_name}</Link></dd>
        <dt>Source</dt><dd>{item.source_name} · {item.source_type}</dd>
        <dt>URL</dt><dd><ExternalLink href={item.canonical_url}>{item.canonical_url}</ExternalLink></dd>
        <dt>Published</dt><dd>{formatWhen(item.published_at)}</dd>
        <dt>Event time</dt><dd>{formatWhen(item.event_time)}</dd>
        <dt>Span</dt><dd>{item.start_ms !== null ? `${item.start_ms}–${item.end_ms} ms` : item.start_char !== null ? `chars ${item.start_char}–${item.end_char}` : "not recorded"}</dd>
        <dt>Extractor</dt><dd>{item.extractor_name} · {item.extractor_version}</dd>
        <dt>Confidence</dt><dd>{item.extraction_confidence_level ?? item.confidence ?? "unknown"}</dd>
        <dt>Content hash</dt><dd className="meta">{item.content_hash}</dd>
      </dl>
      <section className="panel">
        <h2>Machine reading</h2>
        <p><strong>{item.statement_type}.</strong> {item.normalized_text}</p>
        <p className="meta">Topics: {[...item.topic_slugs, ...item.proposed_topics].join(", ") || "none"}</p>
        {item.forecast ? (
          <p className="meta">
            {item.forecast.question_key} · {item.forecast.horizon_text ?? "no horizon"} · {item.forecast.definition_text ?? "no definition"} · {item.forecast.condition_text ?? "no condition"} · {item.forecast.value_type} {String(item.forecast.value_numeric ?? item.forecast.value_min ?? "")}
          </p>
        ) : <p className="meta">No forecast fields.</p>}
      </section>
      {item.warnings.length ? (
        <ul>{item.warnings.map((warning) => <li className="warning" key={warning.code}>{warning.message}</li>)}</ul>
      ) : null}
      <section>
        <h2>Other statements on this question</h2>
        <p className="meta">A different number is not by itself a change of belief.</p>
        <ul>
          {item.related.map((related) => (
            <li key={String(related.slug)}><Link href={`/curation/${related.slug}`}>{String(related.slug)}</Link> · {String(related.review_state)} · {String(related.normalized_text)}</li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Question keys</h2>
        <ul>
          {QUESTION_TAXONOMY.map((entry) => (
            <li key={entry.key}><code>{entry.key}</code> — {entry.label}. {entry.note}{item.suggestions.includes(entry.key) ? " Suggested from the text; still confirm it." : ""}</li>
          ))}
        </ul>
      </section>
      {item.history.length ? (
        <section>
          <h2>Earlier decisions</h2>
          <ul>
            {item.history.map((decision) => (
              <li key={`${decision.reviewed_at}-${decision.decision}`}>{String(decision.decision)} by {String(decision.reviewer)} · {String(decision.previous_review_state)} → {String(decision.resulting_review_state)}{decision.note ? ` · ${decision.note}` : ""}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <form action={submitReview} className="stack">
        <h2>Decision</h2>
        <input type="hidden" name="statement_slug" value={item.slug} />
        <input type="hidden" name="source_content_hash" value={item.content_hash} />
        <input type="hidden" name="evidence_hash" value={item.evidence_hash} />
        <input type="hidden" name="content_version" value={item.content_version} />
        <label>Reviewer<input name="reviewer" defaultValue="local-operator" required /></label>
        <label>Action
          <select name="decision" defaultValue="needs_changes">
            <option value="approve">Approve as human verified</option>
            <option value="reject">Reject</option>
            <option value="needs_changes">Needs changes</option>
          </select>
        </label>
        <label>Rejection reason
          <select name="rejection_reason" defaultValue="">
            <option value="">None</option>
            {REJECTION_REASONS.map((reason) => <option key={reason} value={reason}>{reason}</option>)}
          </select>
        </label>
        <label>Note<textarea name="note" rows={3} /></label>
        <label>Normalized text<textarea name="normalized_text" defaultValue={item.normalized_text} rows={3} /></label>
        <label>Statement type
          <select name="statement_type" defaultValue={item.statement_type}>
            <option>explicit_numeric</option>
            <option>explicit_qualitative</option>
            <option>model_inferred_signal</option>
          </select>
        </label>
        <label>Topics<input name="topic_slugs" defaultValue={item.topic_slugs.join(", ")} /></label>
        <label>Question key
          <select name="question_key" defaultValue={item.forecast?.question_key ?? ""}>
            <option value="">Unchanged</option>
            {QUESTION_TAXONOMY.map((entry) => <option key={entry.key} value={entry.key}>{entry.label}</option>)}
          </select>
        </label>
        <label>Definition<textarea name="definition_text" defaultValue={item.forecast?.definition_text ?? ""} rows={2} /></label>
        <label>Condition<input name="condition_text" defaultValue={item.forecast?.condition_text ?? ""} /></label>
        <label>Horizon<input name="horizon_text" defaultValue={item.forecast?.horizon_text ?? ""} /></label>
        <label>Value type
          <select name="value_type" defaultValue={item.forecast?.value_type ?? ""}>
            <option value="">Unchanged</option>
            {VALUE_TYPES.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>Unit<input name="unit" defaultValue={item.forecast?.unit ?? ""} /></label>
        <label>Point value<input name="value_numeric" defaultValue={item.forecast?.value_numeric ?? ""} /></label>
        <label>Range min<input name="value_min" defaultValue={item.forecast?.value_min ?? ""} /></label>
        <label>Range max<input name="value_max" defaultValue={item.forecast?.value_max ?? ""} /></label>
        <label>Evidence span, only if it is inside the excerpt<textarea name="evidence_text" rows={3} placeholder="Leave empty to keep the excerpt" /></label>
        <label>Related statement slug<input name="other_statement_slug" /></label>
        <label>Relationship
          <select name="relationship_type" defaultValue="">
            <option value="">None</option>
            <option>updates</option>
            <option>clarifies</option>
            <option>retracts</option>
            <option>contradicts</option>
            <option>repeats</option>
          </select>
        </label>
        {numeric ? (
          <fieldset>
            <legend>Confirm this explicit number</legend>
            <label><input type="checkbox" name="confirm_person" /> Person attribution</label>
            <label><input type="checkbox" name="confirm_evidence" /> Exact evidence</label>
            <label><input type="checkbox" name="confirm_value" /> Value or range</label>
            <label><input type="checkbox" name="confirm_units" /> Units</label>
            <label><input type="checkbox" name="confirm_definition" /> Definition</label>
            <label><input type="checkbox" name="confirm_conditionality" /> Conditional or unconditional</label>
            <label><input type="checkbox" name="confirm_horizon" /> Horizon</label>
            <label><input type="checkbox" name="confirm_question_key" /> Question key</label>
          </fieldset>
        ) : null}
        <button type="submit">Record decision</button>
      </form>
    </>
  );
}
