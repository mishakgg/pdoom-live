"use server";

import { curationEnabled, reviewCommandSchema } from "@pdoom/contracts";
import { applyReviewDecision } from "@pdoom/db";
import { redirect } from "next/navigation";

function flag(form: FormData, name: string): boolean {
  return form.get(name) === "on";
}

function text(form: FormData, name: string): string | null {
  const value = form.get(name);
  if (typeof value !== "string" || value.trim() === "") return null;
  return value.trim();
}

export async function submitReview(formData: FormData) {
  if (!curationEnabled()) throw new Error("curation_disabled");
  const decision = String(formData.get("decision") ?? "");
  const command = reviewCommandSchema.parse({
    decision_key: null,
    statement_slug: String(formData.get("statement_slug") ?? ""),
    decision,
    reviewer: text(formData, "reviewer") ?? "local-operator",
    reviewed_at: new Date().toISOString(),
    note: text(formData, "note"),
    rejection_reason: text(formData, "rejection_reason"),
    confirmations: {
      person: flag(formData, "confirm_person"),
      evidence: flag(formData, "confirm_evidence"),
      value: flag(formData, "confirm_value"),
      units: flag(formData, "confirm_units"),
      definition: flag(formData, "confirm_definition"),
      conditionality: flag(formData, "confirm_conditionality"),
      horizon: flag(formData, "confirm_horizon"),
      question_key: flag(formData, "confirm_question_key"),
    },
    corrections: {
      ...(text(formData, "statement_type") ? { statement_type: text(formData, "statement_type") } : {}),
      ...(text(formData, "normalized_text") ? { normalized_text: text(formData, "normalized_text") } : {}),
      ...(text(formData, "topic_slugs") ? { topic_slugs: text(formData, "topic_slugs")!.split(",").map((item) => item.trim()).filter(Boolean) } : {}),
      ...(text(formData, "question_key") ? { question_key: text(formData, "question_key") } : {}),
      ...(text(formData, "question_text") ? { question_text: text(formData, "question_text") } : {}),
      ...(text(formData, "horizon_text") ? { horizon_text: text(formData, "horizon_text") } : {}),
      ...(text(formData, "definition_text") ? { definition_text: text(formData, "definition_text") } : {}),
      ...(text(formData, "condition_text") ? { condition_text: text(formData, "condition_text") } : {}),
      ...(text(formData, "value_type") ? { value_type: text(formData, "value_type") } : {}),
      ...(text(formData, "value_numeric") ? { value_numeric: Number(text(formData, "value_numeric")) } : {}),
      ...(text(formData, "value_min") ? { value_min: Number(text(formData, "value_min")) } : {}),
      ...(text(formData, "value_max") ? { value_max: Number(text(formData, "value_max")) } : {}),
      ...(text(formData, "unit") ? { unit: text(formData, "unit") } : {}),
      ...(text(formData, "evidence_text") ? { evidence_text: String(formData.get("evidence_text")) } : {}),
    },
    relationship: text(formData, "other_statement_slug") && text(formData, "relationship_type")
      ? { other_statement_slug: text(formData, "other_statement_slug"), relationship_type: text(formData, "relationship_type") }
      : null,
    source_content_hash: text(formData, "source_content_hash"),
    evidence_hash: text(formData, "evidence_hash"),
    content_version: text(formData, "content_version") ? Number(text(formData, "content_version")) : null,
  });
  await applyReviewDecision((await import("@pdoom/db")).getPool(), command);
  redirect(`/curation/${command.statement_slug}`);
}
