/** @vitest-environment jsdom */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceBlock, TypeBadge } from "../apps/web/components/statement-bits";
import { DistributionPanel } from "../apps/web/components/trends";
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
    expect(screen.getByText(/1 people, 1 statements/)).toBeTruthy();
    expect(screen.getByText(/not a field consensus/)).toBeTruthy();
  });

  it("explains class boundaries on the methodology page", () => {
    render(<MethodologyPage />);
    expect(screen.getAllByText(/Explicit numerical estimate/).length).toBeGreaterThan(0);
    expect(screen.getByText(/not a consensus/)).toBeTruthy();
  });
});
