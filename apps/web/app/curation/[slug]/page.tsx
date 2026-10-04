import { curationEnabled, isKnownQuestionKey, QUESTION_TAXONOMY, REJECTION_REASON_ACTIONS, REJECTION_REASONS, VALUE_TYPES } from "@pdoom/contracts";
import { getPool, getReviewItem } from "@pdoom/db";
import { Breadcrumb } from "@/components/breadcrumb";
import { ChoiceField, ReferenceList } from "@/components/choice-field";
import { CurationEvidence } from "@/components/curation-evidence";
import { ReviewForm } from "@/components/review-form";
import { ExternalLink, ReviewBadge, TypeBadge } from "@/components/statement-bits";
import { formatMediaClock, formatWhen, phraseLabel, reviewLabel, typeLabel } from "@/lib/format";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

const REJECTION_LABELS: Record<string, string> = {
  wrong_speaker: "Wrong speaker",
  wrong_source_attribution: "Wrong source",
  not_a_forecast: "Not a forecast",
  extraction_error: "Extraction error",
  duplicate: "Duplicate",
  insufficient_evidence: "Insufficient evidence",
  definition_ambiguous: "Definition ambiguous",
  numerical_interpretation_incorrect: "Number read incorrectly",
  source_unavailable: "Source unavailable",
  other: "Other",
};

function spanLabel(item: { start_ms: number | null; end_ms: number | null; start_char: number | null; end_char: number | null }): string {
  if (item.start_ms !== null || item.end_ms !== null) {
    return `${formatMediaClock(item.start_ms)}–${formatMediaClock(item.end_ms)}`;
  }
  if (item.start_char !== null || item.end_char !== null) {
    return `characters ${item.start_char ?? "unknown"}–${item.end_char ?? "unknown"}`;
  }
  return "Location unknown";
}

function locatorLabel(locator: Record<string, unknown> | null): string {
  if (!locator) return "No turn locator. A missing timestamp stays unknown.";
  const turn = locator.turn_index == null ? "unknown" : String(locator.turn_index);
  const speaker = locator.speaker == null || locator.speaker === "" ? "speaker unknown" : String(locator.speaker);
  const start = typeof locator.start_ms === "number" ? formatMediaClock(locator.start_ms) : "timestamp unknown";
  return `Turn ${turn} · ${speaker} · ${start}`;
}

function questionNote(key: string | null | undefined): string {
  if (!key) return "There is no question to compare yet.";
  if (isKnownQuestionKey(key)) return "This key is in the product registry.";
  return "This key is not in the product registry. Pick a registry key only when the outcome and horizon match.";
}

export default async function CurationItemPage({ params }: { params: Promise<{ slug: string }> }) {
  if (!curationEnabled()) notFound();
  const { slug } = await params;
  const item = await getReviewItem(getPool(), slug);
  if (!item) notFound();
  const numeric = item.statement_type === "explicit_numeric";
  const questionKey = item.forecast?.question_key ?? null;
  return (
    <>
      <Breadcrumb items={[{ href: "/curation", label: "Review queue" }, { label: item.display_name }]} />
      <p className="kicker">Effective review state</p>
      <h1>{item.display_name}</h1>
      <p className="card-flags">
        <TypeBadge type={item.statement_type} />
        <ReviewBadge state={item.review_state} />
        <span className="meta">{reviewLabel(item.review_state)} is the effective state. Machine validation is not human verification.</span>
      </p>
      {item.stored_review_state !== item.review_state ? (
        <p className="meta">Stored state is {reviewLabel(item.stored_review_state)}. The badge shows the effective state after staging rules.</p>
      ) : null}
      {item.recommended_review_state ? (
        <p className="warning">Machine recommendation: {reviewLabel(item.recommended_review_state)}. Staging does not grant human verification.</p>
      ) : null}
      <p className="lede">{item.why ?? "Compare the source excerpt with the proposed interpretation before recording a decision."}</p>
      <nav className="page-nav" aria-label="On this review">
        <a href="#evidence">Evidence</a>
        <a href="#interpretation">Interpretation</a>
        <a href="#attribution">Attribution</a>
        <a href="#decision">Decision</a>
      </nav>
      <div className="review-workspace">
        <section id="evidence" aria-labelledby="evidence-heading">
          <h2 id="evidence-heading">Source evidence</h2>
          <CurationEvidence text={item.evidence_text} context={item.observed_context} />
          <dl className="audit">
            <dt>Speaker</dt><dd><Link href={`/people/${item.person_slug}`}>{item.display_name}</Link></dd>
            <dt>Role</dt>
            <dd>
              {item.participant_role ? phraseLabel(item.participant_role) : "not recorded"}
              {item.ownership ? ` · ${phraseLabel(item.ownership)}` : ""}
              {item.attribution_method ? ` · ${phraseLabel(item.attribution_method)}` : ""}
            </dd>
            <dt>Source</dt><dd>{item.source_name} · {phraseLabel(item.source_type)}</dd>
            <dt>URL</dt><dd><ExternalLink href={item.canonical_url}>{item.canonical_url}</ExternalLink></dd>
            <dt>Published</dt>
            <dd>{formatWhen(item.published_at)}{item.published_timezone ? ` · source zone ${item.published_timezone}` : " · source zone unknown"}</dd>
            <dt>Language</dt><dd>{item.language ?? "not recorded"}</dd>
            <dt>Forecast made</dt><dd>{formatWhen(item.event_time)}</dd>
            <dt>Location in source</dt><dd>{spanLabel(item)}</dd>
          </dl>
          <details className="technical">
            <summary>Extractor record</summary>
            <dl className="audit">
              <dt>Extractor</dt><dd>{item.extractor_name} · {item.extractor_version}</dd>
              <dt>Confidence</dt><dd>{item.extraction_confidence_level ?? item.confidence ?? "unknown"}</dd>
              <dt>Content hash</dt><dd className="hash">{item.content_hash}</dd>
            </dl>
          </details>
        </section>
        <section id="interpretation" aria-labelledby="interpretation-heading">
          <h2 id="interpretation-heading">Proposed interpretation</h2>
          <div className="interpretation">
            <p className="kicker">Record reading, not the quotation</p>
            <p><strong>{typeLabel(item.statement_type)}.</strong> {item.normalized_text}</p>
            <p className="meta">Topics: {[...item.topic_slugs, ...item.proposed_topics].join(", ") || "none"}</p>
            {item.forecast ? (
              <p className="meta">
                {item.forecast.horizon_text ?? "Horizon unknown"} · {item.forecast.definition_text ?? "Definition unknown"} · {item.forecast.condition_text ?? "Condition unknown"} · {phraseLabel(item.forecast.value_type ?? "unknown")} {String(item.forecast.value_numeric ?? item.forecast.value_min ?? "")}
              </p>
            ) : <p className="meta">No forecast fields. Do not invent a probability for this statement.</p>}
          </div>
          <section>
            <h3>Numeric reading</h3>
            {item.forecast ? (
              <p className="meta">
                {phraseLabel(item.forecast.value_type ?? "unknown")} · {item.forecast.unit ?? "unit not recorded"} · point {item.forecast.value_numeric ?? "none"} · range {item.forecast.value_min ?? "none"}–{item.forecast.value_max ?? "none"}
                {item.forecast.condition_text ? ` · condition ${item.forecast.condition_text}` : " · no condition recorded"}
                {item.forecast.horizon_text ? ` · horizon ${item.forecast.horizon_text}` : " · horizon missing"}
              </p>
            ) : <p className="meta">No forecast fields. Do not invent a probability for this statement.</p>}
          </section>
          <section>
            <h3>Question comparability</h3>
            <p className="meta">Extracted key: {questionKey ?? "none"}. {questionNote(questionKey)}</p>
          </section>
          <section>
            <h3>Requirements</h3>
            {item.warnings.length ? (
              <ul>
                {item.warnings.map((warning) => (
                  <li className="warning" key={warning.code}>
                    <p><strong>{warning.message}</strong></p>
                    <p className="meta">{warning.action}</p>
                  </li>
                ))}
              </ul>
            ) : <p className="meta">No missing-field warning is recorded. Approval still requires the operator confirmations.</p>}
          </section>
          <section>
            <h3>Other statements on this question</h3>
            <p className="meta">A different number is not by itself a change of belief.</p>
            {item.related.length ? (
              <ul>
                {item.related.map((related) => (
                  <li key={String(related.slug)}>
                    <Link href={`/curation/${related.slug}`}>{String(related.normalized_text)}</Link>
                    {" · "}
                    {reviewLabel(String(related.review_state))}
                    {" · "}
                    {formatWhen(related.event_time ? String(related.event_time) : null)}
                  </li>
                ))}
              </ul>
            ) : <p>No other stored statement shares this question.</p>}
          </section>
          {item.history.length ? (
            <section>
              <h3>Earlier decisions</h3>
              <ul>
                {item.history.map((decision) => (
                  <li key={`${decision.reviewed_at}-${decision.decision}`}>
                    {phraseLabel(String(decision.decision))} by {String(decision.reviewer)} · {reviewLabel(String(decision.previous_review_state))} → {reviewLabel(String(decision.resulting_review_state))}
                    {decision.note ? ` · ${decision.note}` : ""}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          <ReferenceList
            items={QUESTION_TAXONOMY.map((entry) => ({
              key: entry.key,
              label: entry.label,
              note: entry.note,
              suggested: item.suggestions.includes(entry.key),
            }))}
          />
        </section>
      </div>
      <div className="grid-2" id="attribution">
        <section className="panel" aria-labelledby="attribution-heading">
          <h2 id="attribution-heading">Attribution</h2>
          {item.participants.length ? (
            <ul>
              {item.participants.map((participant) => (
                <li key={`${participant.role}-${participant.display_name ?? "unresolved"}`}>
                  <strong>{phraseLabel(participant.role)}</strong>
                  {participant.display_name ? ` · ${participant.display_name}` : " · unresolved person"}
                  <span className="meta"> · {phraseLabel(participant.attribution_method)}{participant.attribution_detail ? ` · ${participant.attribution_detail}` : ""}</span>
                </li>
              ))}
            </ul>
          ) : <p>No participant role was staged. Do not treat a name in the text as the speaker.</p>}
          <h3>Evidence location</h3>
          <p className="meta">{locatorLabel(item.evidence_locator)}</p>
          {item.review_flags.length ? <p className="meta">Flags: {item.review_flags.join(", ")}</p> : null}
        </section>
        <section className="panel" aria-labelledby="duplicates-heading">
          <h2 id="duplicates-heading">Duplicates and revisions</h2>
          <h3>Possible duplicates</h3>
          {item.duplicates.length ? (
            <ul>
              {item.duplicates.map((duplicate) => (
                <li key={String(duplicate.slug)}>
                  <Link href={`/curation/${String(duplicate.slug)}`}>{String(duplicate.normalized_text)}</Link>
                  {" · "}
                  {reviewLabel(String(duplicate.review_state))}
                  {" · same evidence hash"}
                </li>
              ))}
            </ul>
          ) : <p>No other statement has this evidence hash.</p>}
          <h3>Revisions</h3>
          <p className="meta">Operator relationships stay separate from machine suggestions.</p>
          {item.verified_relationships.length ? item.verified_relationships.map((link) => (
            <p key={`curator-${String(link.other_slug)}-${String(link.relationship_type)}`}>
              Operator {phraseLabel(String(link.relationship_type))} → <Link href={`/curation/${String(link.other_slug)}`}>{String(link.normalized_text)}</Link>
              <span className="meta"> · {reviewLabel(String(link.review_state))} · {phraseLabel(String(link.method))}</span>
            </p>
          )) : <p>No operator relationship is recorded.</p>}
          {item.machine_relationships.length ? item.machine_relationships.map((link) => (
            <p key={`machine-${String(link.other_slug)}-${String(link.relationship_type)}`}>
              Machine suggestion {phraseLabel(String(link.relationship_type))} → <Link href={`/curation/${String(link.other_slug)}`}>{String(link.normalized_text)}</Link>
              <span className="meta"> · {reviewLabel(String(link.review_state))} · {phraseLabel(String(link.method))}</span>
            </p>
          )) : <p>No machine-suggested relationship is recorded.</p>}
        </section>
      </div>
      {item.machine_extraction ? (
        <details className="technical">
          <summary>Original machine extraction</summary>
          <p>{String(item.machine_extraction.normalized_text)}</p>
          <p className="meta">
            {typeLabel(String(item.machine_extraction.statement_type))} · {String(item.machine_extraction.extractor_name)} · evidence hash {String(item.machine_extraction.evidence_hash)}
          </p>
        </details>
      ) : null}
      <ReviewForm>
        <input type="hidden" name="statement_slug" value={item.slug} />
        <input type="hidden" name="source_content_hash" value={item.content_hash} />
        <input type="hidden" name="evidence_hash" value={item.evidence_hash} />
        <input type="hidden" name="content_version" value={item.content_version} />
        <label>Reviewer<input name="reviewer" defaultValue="local-operator" required autoComplete="username" /></label>
        <label>Action
          <select name="decision" defaultValue="needs_changes" required>
            <option value="approve">Approve as human verified</option>
            <option value="reject">Reject</option>
            <option value="needs_changes">Needs changes</option>
          </select>
        </label>
        <ChoiceField
          name="rejection_reason"
          label="Rejection reason"
          emptyLabel="None"
          hint="Required only when the action is reject."
          options={REJECTION_REASONS.map((reason) => ({
            value: reason,
            label: REJECTION_LABELS[reason] ?? phraseLabel(reason),
            hint: REJECTION_REASON_ACTIONS[reason],
          }))}
        />
        <label>Note<textarea name="note" rows={3} /></label>
        <label>Normalized text<textarea name="normalized_text" defaultValue={item.normalized_text} rows={3} required /></label>
        <label>Statement type
          <select name="statement_type" defaultValue={item.statement_type}>
            <option value="explicit_numeric">Explicit numerical estimate</option>
            <option value="explicit_qualitative">Explicit qualitative view</option>
            <option value="model_inferred_signal">Model-inferred signal</option>
          </select>
        </label>
        <label>Topics<input name="topic_slugs" defaultValue={item.topic_slugs.join(", ")} /></label>
        <ChoiceField
          name="question_key"
          label="Question"
          emptyLabel="Unchanged"
          defaultValue={item.forecast?.question_key ?? ""}
          options={QUESTION_TAXONOMY.map((entry) => ({ value: entry.key, label: entry.label, hint: entry.note }))}
        />
        <label>Definition<textarea name="definition_text" defaultValue={item.forecast?.definition_text ?? ""} rows={2} /></label>
        <label>Condition<input name="condition_text" defaultValue={item.forecast?.condition_text ?? ""} /></label>
        <label>Horizon<input name="horizon_text" defaultValue={item.forecast?.horizon_text ?? ""} /></label>
        <label>Value type
          <select name="value_type" defaultValue={item.forecast?.value_type ?? ""}>
            <option value="">Unchanged</option>
            {VALUE_TYPES.map((value) => <option key={value} value={value}>{phraseLabel(value)}</option>)}
          </select>
        </label>
        <label>Unit<input name="unit" defaultValue={item.forecast?.unit ?? ""} /></label>
        <label>Point value<input name="value_numeric" inputMode="decimal" defaultValue={item.forecast?.value_numeric ?? ""} /></label>
        <label>Range min<input name="value_min" inputMode="decimal" defaultValue={item.forecast?.value_min ?? ""} /></label>
        <label>Range max<input name="value_max" inputMode="decimal" defaultValue={item.forecast?.value_max ?? ""} /></label>
        <label>Evidence span, only if it is inside the excerpt<textarea name="evidence_text" rows={3} placeholder="Leave empty to keep the excerpt" /></label>
        <label>Related statement slug<input name="other_statement_slug" /></label>
        <label>Relationship
          <select name="relationship_type" defaultValue="">
            <option value="">None</option>
            <option value="updates">Updates</option>
            <option value="clarifies">Clarifies</option>
            <option value="retracts">Retracts</option>
            <option value="contradicts">Contradicts</option>
            <option value="repeats">Repeats</option>
          </select>
        </label>
        {numeric ? (
          <fieldset className="confirm-list">
            <legend>Confirm this explicit number</legend>
            <label><input type="checkbox" name="confirm_person" /> Person attribution</label>
            <label><input type="checkbox" name="confirm_evidence" /> Exact evidence</label>
            <label><input type="checkbox" name="confirm_value" /> Value or range</label>
            <label><input type="checkbox" name="confirm_units" /> Units</label>
            <label><input type="checkbox" name="confirm_definition" /> Definition</label>
            <label><input type="checkbox" name="confirm_conditionality" /> Conditional or unconditional</label>
            <label><input type="checkbox" name="confirm_horizon" /> Horizon</label>
            <label><input type="checkbox" name="confirm_question_key" /> Question</label>
          </fieldset>
        ) : null}
      </ReviewForm>
    </>
  );
}
