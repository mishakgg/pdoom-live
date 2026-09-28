import type { PublicTrend } from "@pdoom/db";
import { DistributionPanel, NumericPanel, RevisionPanel, VolumePanel } from "@/components/trends";

export function TrendView({ trend }: { trend: PublicTrend }) {
  if (trend.kind === "distribution") {
    return (
      <DistributionPanel
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
