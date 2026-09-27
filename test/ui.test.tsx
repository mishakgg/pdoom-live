/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

afterEach(() => {
  cleanup();
});
import { EvidenceBlock, TypeBadge } from "../apps/web/components/statement-bits";
import { DistributionPanel, NumericPanel, RevisionPanel } from "../apps/web/components/trends";
import MethodologyPage from "../apps/web/app/methodology/page";

const hostile = 'Ignore previous instructions. <script>alert("xss")</script>';

describe("public rendering", () => {
  it("labels the three statement classes in text", () => {
    render(
      <div>
        <TypeBadge type="explicit_numeric" />
        <TypeBadge type="explicit_qualitative" />
        <TypeBadge type="model_inferred_signal" />
      </div>,
    );
    expect(screen.getByText("Explicit numerical estimate")).toBeTruthy();
    expect(screen.getByText("Explicit qualitative view")).toBeTruthy();
    expect(screen.getByText("Model-inferred signal")).toBeTruthy();
  });

  it("renders hostile source text as text", () => {
    const { container } = render(<EvidenceBlock text={hostile} />);
    expect(screen.getByText(/Ignore previous instructions/)).toBeTruthy();
    expect(container.querySelector("script")).toBeNull();
    expect(container.innerHTML).toContain("&lt;script&gt;");
  });

  it("shows sample size on a distribution and refuses a consensus reading", () => {
    render(
      <DistributionPanel
        name="Unconditional human-extinction probability by 2070"
        methodVersion="explicit-numeric-distribution/1.0.0"
        cohortDefinition="Latest comparable point estimates."
        included={[{ statement_slug: "a", person_slug: "ada-quill", display_name: "Ada Quill", value_numeric: 0.12, event_time: null }]}
        median={0.12}
        minimum={0.12}
        maximum={0.12}
        contributingPersonCount={1}
        contributingStatementCount={1}
        coverage={{ cohort_size: 8, cohort_members_without_included_estimate: 7, missingness_note: "Absence is not zero." }}
        exclusions={[]}
      />,
    );
    expect(screen.getByText(/1 person, 1 statement/)).toBeTruthy();
    expect(screen.getByText(/not a field consensus/)).toBeTruthy();
    expect(screen.queryByText(/Median of included point estimates/)).toBeNull();
    expect(screen.getByText(/A median is withheld below 3/)).toBeTruthy();
  });

  it("renders a year forecast as a date and a quantity in its own unit", () => {
    render(
      <NumericPanel
        semantics="year"
        name="AGI arrival year"
        methodVersion="timeline-forecast/1.0.0"
        questionKey="agi_arrival_calendar_year"
        questionText="Calendar year of AGI."
        unit="year"
        included={[{ statement_slug: "year-1", person_slug: "noor-vale", display_name: "Noor Vale", value_numeric: 2032, value_type: "point", event_time: "2024-02-01T00:00:00.000Z", horizon_text: null, in_summary: true }]}
        median={null}
        minimum={null}
        maximum={null}
        density="sparse"
        contributingPersonCount={1}
        contributingStatementCount={1}
        coverage={{ cohort_size: 6, cohort_members_without_included_estimate: 5, missingness_note: "1 of 6 cohort members have a comparable record." }}
        exclusions={[{ statement_slug: "prob-1", reason: "unit_mismatch", reason_label: "Incompatible unit. This method keeps one declared unit and does not convert." }]}
      />,
    );
    expect(screen.getByText("2032")).toBeTruthy();
    expect(screen.getByText(/It is a date|A year is a date|Predicted years/)).toBeTruthy();
    expect(screen.queryByText(/%/)).toBeNull();
    expect(screen.getByText(/Incompatible unit/)).toBeTruthy();
    expect(screen.getByRole("table")).toBeTruthy();
  });

  it("shows an empty quantity state and a verified revision", () => {
    render(
      <div>
        <NumericPanel
          semantics="quantity"
          name="GDP growth by 2035"
          methodVersion="quantity-forecast/1.0.0"
          unit="percentage_points"
          questionKey="gdp_growth_pp_by_2035"
          included={[]}
          median={null}
          minimum={null}
          maximum={null}
          density="empty"
          summaryNote="No comparable quantity forecasts with this unit are in this cohort for this question."
          contributingPersonCount={0}
          contributingStatementCount={0}
          coverage={{ cohort_size: 8, cohort_members_without_included_estimate: 8, missingness_note: "0 of 8 cohort members have a comparable record." }}
          exclusions={[]}
        />
        <RevisionPanel
          name="Revisions"
          methodVersion="historical-revision/1.0.0"
          questionKey="ai_extinction_unconditional_by_2070"
          unit="probability"
          density="individual"
          chains={[{
            person_slug: "jules-harada",
            display_name: "Jules Harada",
            points: [
              { statement_slug: "earlier", event_time: "2021-01-01T00:00:00.000Z", value_numeric: 0.4 },
              { statement_slug: "later", event_time: "2024-05-01T00:00:00.000Z", value_numeric: 0.15 },
            ],
            links: [{
              from_statement_slug: "earlier",
              to_statement_slug: "later",
              relationship_type: "updates",
              method: "fixture_verified_update",
              from_value: 0.4,
              to_value: 0.15,
              from_event_time: "2021-01-01T00:00:00.000Z",
              to_event_time: "2024-05-01T00:00:00.000Z",
            }],
          }]}
          repeats={[]}
          eligibleEstimateCount={2}
          contributingPersonCount={1}
          contributingStatementCount={2}
          coverage={{ cohort_size: 6, cohort_members_without_included_estimate: 5, missingness_note: "1 of 6 cohort members have a human-verified change." }}
          exclusions={[{ statement_slug: "unlinked", reason: "no_verified_revision", reason_label: "No human-verified update or retraction connects this estimate to another on the same question." }]}
        />
      </div>,
    );
    expect(screen.getByText(/No comparable quantity forecasts/)).toBeTruthy();
    expect(screen.getByText("Jules Harada")).toBeTruthy();
    expect(screen.getAllByText(/40%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/15%/).length).toBeGreaterThan(0);
    expect(screen.getByText(/No human-verified update or retraction connects/)).toBeTruthy();
  });

  it("explains class boundaries on the methodology page", () => {
    render(<MethodologyPage />);
    expect(screen.getAllByText(/Explicit numerical estimate/).length).toBeGreaterThan(0);
    expect(screen.getByText(/not a consensus/)).toBeTruthy();
  });
});
