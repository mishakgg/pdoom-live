import { curationEnabled, isKnownQuestionKey, QUESTION_TAXONOMY, REJECTION_REASON_ACTIONS, REJECTION_REASONS, VALUE_TYPES } from "@pdoom/contracts";
import { getPool, getReviewItem } from "@pdoom/db";
import { CurationEvidence } from "@/components/curation-evidence";
import { ExternalLink } from "@/components/statement-bits";
import { formatWhen } from "@/lib/format";
import { submitReview } from "../actions";
import Link from "next/link";
import { notFound } from "next/navigation";
import styles from "../curation.module.css";

export const dynamic = "force-dynamic";

export default async function CurationItemPage({ params }: { params: Promise<{ slug: string }> }) {
  if (!curationEnabled()) notFound();
  const { slug } = await params;
  const item = await getReviewItem(getPool(), slug);
  if (!item) notFound();
  const numeric = item.statement_type === "explicit_numeric";
  return (
    <>
      <p className="kicker"><Link href="/curation">Queue</Link> · effective {item.review_state}{item.stored_review_state !== item.review_state ? ` · stored ${item.stored_review_state}` : ""}</p>
      <h1>{item.display_name}</h1>
      <p className="lede">{item.why ?? "Review the evidence before the extracted fields."}</p>
      {item.recommended_review_state ? <p className={styles.note}>Machine recommendation: {item.recommended_review_state}. Staging does not grant human verification.</p> : null}
      <CurationEvidence text={item.evidence_text} context={item.observed_context} />
      <dl className="audit">
        <dt>Person</dt><dd><Link href={`/people/${item.person_slug}`}>{item.display_name}</Link></dd>
        <dt>Source</dt><dd>{item.source_name} · {item.source_type}</dd>
        <dt>URL</dt><dd><ExternalLink href={item.canonical_url}>{item.canonical_url}</ExternalLink></dd>
        <dt>Role</dt><dd>{item.participant_role ?? "not recorded"}{item.ownership ? ` · ${item.ownership}` : ""}{item.attribution_method ? ` · ${item.attribution_method}` : ""}</dd>
        <dt>Published</dt><dd>{formatWhen(item.published_at)}{item.published_timezone ? ` · source zone ${item.published_timezone}` : " · source zone unknown"}</dd>
        <dt>Language</dt><dd>{item.language ?? "not recorded"}</dd>
        <dt>Event time</dt><dd>{formatWhen(item.event_time)}</dd>
        <dt>Span</dt><dd>{item.start_ms !== null ? `${item.start_ms}–${item.end_ms ?? "unknown"} ms` : item.start_char !== null ? `chars ${item.start_char}–${item.end_char}` : "location unknown"}</dd>
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
      <div className={styles.sections}>
        <section className={styles.panel}>
          <h2>Attribution</h2>
          {item.participants.length ? (
            <ul className={styles.list}>
              {item.participants.map((participant) => (
                <li key={`${participant.role}-${participant.display_name ?? "unresolved"}`}>
                  <strong>{participant.role}</strong>
                  {participant.display_name ? ` · ${participant.display_name}` : " · unresolved person"}
                  <span className={styles.meta}> · {participant.attribution_method}{participant.attribution_detail ? ` · ${participant.attribution_detail}` : ""}</span>
                </li>
              ))}
            </ul>
          ) : <p className={styles.note}>No participant role was staged. Do not treat a name in the text as the speaker.</p>}
        </section>
        <section className={styles.panel}>
          <h2>Evidence location</h2>
          <p className={styles.meta}>
            {item.evidence_locator
              ? `Turn ${String(item.evidence_locator.turn_index ?? "unknown")} · ${String(item.evidence_locator.speaker ?? "speaker unknown")} · ${item.evidence_locator.start_ms == null ? "timestamp unknown" : `${String(item.evidence_locator.start_ms)} ms`}`
              : "No turn locator. A missing timestamp stays unknown."}
          </p>
          {item.review_flags.length ? <p className={styles.meta}>Flags: {item.review_flags.join(", ")}</p> : null}
        </section>
        <section className={styles.panel}>
          <h2>Numeric reading</h2>
          {item.forecast ? (
            <p className={styles.meta}>
              {item.forecast.value_type} · {item.forecast.unit ?? "unit not recorded"} · point {String(item.forecast.value_numeric ?? "none")} · range {String(item.forecast.value_min ?? "none")}–{String(item.forecast.value_max ?? "none")}
              {item.forecast.condition_text ? ` · condition ${item.forecast.condition_text}` : " · no condition recorded"}
              {item.forecast.horizon_text ? ` · horizon ${item.forecast.horizon_text}` : " · horizon missing"}
            </p>
          ) : <p className={styles.note}>No forecast fields. Do not invent a probability for this statement.</p>}
        </section>
        <section className={styles.panel}>
          <h2>Question comparability</h2>
          <p className={styles.meta}>
            Extracted key: {item.forecast?.question_key ?? "none"}.
            {item.forecast?.question_key ? (isKnownQuestionKey(item.forecast.question_key) ? " This key is in the product registry." : " This key is not in the product registry. Pick a registry key only when the outcome and horizon match.") : " There is no question to compare yet."}
          </p>
        </section>
        <div className={styles.split}>
          <section className={styles.panel}>
            <h2>Possible duplicates</h2>
            {item.duplicates.length ? (
              <ul className={styles.list}>
                {item.duplicates.map((duplicate) => (
                  <li key={String(duplicate.slug)}><Link href={`/curation/${String(duplicate.slug)}`}>{String(duplicate.slug)}</Link> · {String(duplicate.review_state)} · same evidence hash</li>
                ))}
              </ul>
            ) : <p className={styles.note}>No other statement has this evidence hash.</p>}
          </section>
          <section className={styles.panel}>
            <h2>Revisions</h2>
            <p className={styles.meta}>Operator relationships stay separate from machine suggestions.</p>
            {item.verified_relationships.length ? item.verified_relationships.map((link) => (
              <p key={`curator-${String(link.other_slug)}-${String(link.relationship_type)}`} className={styles.meta}>Operator {String(link.relationship_type)} → {String(link.other_slug)} · {String(link.review_state)} · {String(link.method)}</p>
            )) : <p className={styles.note}>No operator relationship is recorded.</p>}
            {item.machine_relationships.length ? item.machine_relationships.map((link) => (
              <p key={`machine-${String(link.other_slug)}-${String(link.relationship_type)}`} className={styles.meta}>Machine suggestion {String(link.relationship_type)} → {String(link.other_slug)} · {String(link.review_state)} · {String(link.method)}</p>
            )) : <p className={styles.note}>No machine-suggested relationship is recorded.</p>}
          </section>
        </div>
        {item.machine_extraction ? (
          <section className={styles.panel}>
            <h2>Original machine extraction</h2>
            <p>{String(item.machine_extraction.normalized_text)}</p>
            <p className={styles.meta}>{String(item.machine_extraction.statement_type)} · {String(item.machine_extraction.extractor_name)} · evidence hash {String(item.machine_extraction.evidence_hash)}</p>
          </section>
        ) : null}
        <section className={styles.panel}>
          <h2>Requirements</h2>
          {item.warnings.length ? (
            <ul className={styles.list}>
              {item.warnings.map((warning) => (
                <li className={`${styles.requirement} warning`} key={warning.code}>
                  <strong>{warning.message}</strong>
                  <span className={styles.action}>{warning.action}</span>
                </li>
              ))}
            </ul>
          ) : <p className={styles.note}>No missing-field warning is recorded. Approval still requires the operator confirmations.</p>}
        </section>
      </div>
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
      <form action={submitReview} className={styles.form}>
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
        <ul className={styles.list}>
          {REJECTION_REASONS.map((reason) => <li key={reason} className={styles.meta}><code>{reason}</code> — {REJECTION_REASON_ACTIONS[reason]}</li>)}
        </ul>
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
