import type { PublicTrend } from "@pdoom/db";
import { DistributionPanel, InspectionPanel, NumericPanel, QualitativePanel, RevisionPanel, VolumePanel } from "@/components/trends";

function numericFacts(result: {
  outcome_label: string;
  deadline_label: string | null;
  condition_label: string | null;
  exact_question_id: string;
  question_key: string;
  median_interpretation: string;
  history: { note: string };
}) {
  return {
    outcomeLabel: result.outcome_label,
    deadlineLabel: result.deadline_label,
    conditionLabel: result.condition_label,
    exactQuestionId: result.exact_question_id,
    storedQuestionKey: result.question_key,
    historyNote: result.history.note,
    medianInterpretation: result.median_interpretation,
  };
}

export function TrendView({ trend, duplicateTitle = false, preview = false }: { trend: PublicTrend; duplicateTitle?: boolean; preview?: boolean }) {
  const previewHref = preview ? `/trends/${trend.slug}` : undefined;
  if (trend.kind === "distribution") {
    return (
      <DistributionPanel
        duplicateTitle={duplicateTitle}
        preview={preview}
        previewHref={previewHref}
        name={trend.name}
        methodVersion={trend.method_version}
        cohortSlug={trend.cohort_slug}
        cohortVersion={trend.cohort_version}
        cohortDefinition={trend.cohort_definition}
        questionKey={trend.distribution.question_key}
        questionText={trend.distribution.question_text}
        definitionText={trend.distribution.definition_text}
        unit={trend.distribution.unit}
        conditionality={trend.distribution.conditionality}
        included={trend.distribution.included}
        median={trend.distribution.median}
        minimum={trend.distribution.minimum}
        maximum={trend.distribution.maximum}
        density={trend.distribution.density}
        summaryNote={trend.distribution.summary_note}
        contributingPeople={trend.distribution.coverage.contributing_people}
        contributingPersonCount={trend.distribution.contributing_person_count}
        contributingStatementCount={trend.distribution.contributing_statement_count}
        coverage={trend.distribution.coverage}
        exclusions={trend.distribution.exclusions}
        {...numericFacts(trend.distribution)}
      />
    );
  }
  if (trend.kind === "timeline") {
    return (
      <NumericPanel
        semantics="year"
        name={trend.name}
        methodVersion={trend.method_version}
        cohortSlug={trend.cohort_slug}
        cohortVersion={trend.cohort_version}
        cohortDefinition={trend.cohort_definition}
        questionKey={trend.timeline.question_key}
        questionText={trend.timeline.question_text}
        definitionText={trend.timeline.definition_text}
        unit={trend.timeline.unit}
        conditionality={trend.timeline.conditionality}
        included={trend.timeline.included}
        median={trend.timeline.median}
        minimum={trend.timeline.minimum}
        maximum={trend.timeline.maximum}
        density={trend.timeline.density}
        summaryNote={trend.timeline.summary_note}
        contributingPeople={trend.timeline.coverage.contributing_people}
        contributingPersonCount={trend.timeline.contributing_person_count}
        contributingStatementCount={trend.timeline.contributing_statement_count}
        coverage={trend.timeline.coverage}
        exclusions={trend.timeline.exclusions}
        duplicateTitle={duplicateTitle}
        preview={preview}
        previewHref={previewHref}
        {...numericFacts(trend.timeline)}
      />
    );
  }
  if (trend.kind === "quantity") {
    return (
      <NumericPanel
        semantics="quantity"
        name={trend.name}
        methodVersion={trend.method_version}
        cohortSlug={trend.cohort_slug}
        cohortVersion={trend.cohort_version}
        cohortDefinition={trend.cohort_definition}
        questionKey={trend.quantity.question_key}
        questionText={trend.quantity.question_text}
        definitionText={trend.quantity.definition_text}
        unit={trend.quantity.unit}
        conditionality={trend.quantity.conditionality}
        included={trend.quantity.included}
        median={trend.quantity.median}
        minimum={trend.quantity.minimum}
        maximum={trend.quantity.maximum}
        density={trend.quantity.density}
        summaryNote={trend.quantity.summary_note}
        contributingPeople={trend.quantity.coverage.contributing_people}
        contributingPersonCount={trend.quantity.contributing_person_count}
        contributingStatementCount={trend.quantity.contributing_statement_count}
        coverage={trend.quantity.coverage}
        exclusions={trend.quantity.exclusions}
        duplicateTitle={duplicateTitle}
        preview={preview}
        previewHref={previewHref}
        {...numericFacts(trend.quantity)}
      />
    );
  }
  if (trend.kind === "qualitative") {
    return (
      <QualitativePanel
        name={trend.name}
        methodVersion={trend.method_version}
        cohortSlug={trend.cohort_slug}
        cohortVersion={trend.cohort_version}
        cohortDefinition={trend.cohort_definition}
        questionKey={trend.qualitative.question_key}
        definitionText={trend.qualitative.definition_text}
        note={trend.qualitative.note}
        rows={trend.qualitative.rows}
        cohortSize={trend.cohort_size}
        historyNote={trend.history.note}
        duplicateTitle={duplicateTitle}
      />
    );
  }
  if (trend.kind === "inspection") {
    return (
      <InspectionPanel
        name={trend.name}
        methodVersion={trend.method_version}
        cohortDefinition={trend.cohort_definition}
        note={trend.inspection.note}
        rows={trend.inspection.rows}
        cohortSize={trend.cohort_size}
        historyNote={trend.history.note}
        duplicateTitle={duplicateTitle}
      />
    );
  }
  if (trend.kind === "revision") {
    return (
      <RevisionPanel
        name={trend.name}
        methodVersion={trend.method_version}
        cohortSlug={trend.cohort_slug}
        cohortVersion={trend.cohort_version}
        cohortDefinition={trend.cohort_definition}
        questionKey={trend.revision.question_key}
        questionText={trend.revision.question_text}
        definitionText={trend.revision.definition_text}
        unit={trend.revision.unit}
        density={trend.revision.density}
        summaryNote={trend.revision.summary_note}
        chains={trend.revision.chains}
        repeats={trend.revision.repeats}
        eligibleEstimateCount={trend.revision.eligible_estimate_count}
        contributingPeople={trend.revision.coverage.contributing_people}
        contributingPersonCount={trend.revision.contributing_person_count}
        contributingStatementCount={trend.revision.contributing_statement_count}
        coverage={trend.revision.coverage}
        exclusions={trend.revision.exclusions}
        outcomeLabel={trend.revision.outcome_label}
        deadlineLabel={trend.revision.deadline_label}
        conditionLabel={trend.revision.condition_label}
        exactQuestionId={trend.revision.exact_question_id}
        historyNote={trend.revision.history.note}
        duplicateTitle={duplicateTitle}
      />
    );
  }
  return (
    <VolumePanel
      rows={trend.volume.rows}
      methodVersion={trend.method_version}
      contributingStatementCount={trend.volume.contributing_statement_count}
      contributingPersonCount={trend.volume.contributing_person_count}
      cohortSize={trend.volume.coverage.cohort_size}
      missingCount={trend.volume.coverage.cohort_members_without_included_estimate}
      missingnessNote={trend.volume.coverage.missingness_note}
      contributingPeople={trend.volume.contributing_people}
      exclusions={trend.volume.exclusions}
    />
  );
}
