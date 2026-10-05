/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import {
  QuestionHorizonList,
  SEPARATE_QUESTIONS,
  distinctQuestions,
  horizonLabel,
  type DisplayedQuestion,
} from "./question-horizons";
import type { ForecastFacts } from "@pdoom/contracts";

afterEach(() => {
  cleanup();
});

function fact(input: ForecastFacts & { value_numeric?: number | null }): ForecastFacts {
  return input;
}

describe("topic question horizons", () => {
  it("labels a missing horizon unknown or ambiguous and does not invent a catalog deadline", () => {
    expect(horizonLabel(fact({
      question_key: "ai_extinction_unconditional_by_2070",
      definition_text: "Literal human extinction.",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.22,
      horizon_text: null,
    }))).toBe("unknown");

    expect(horizonLabel(fact({
      question_key: "extinction_unconditional",
      definition_text: "Literal human extinction.",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.22,
      horizon_text: null,
    }))).toBe("ambiguous");

    expect(horizonLabel(fact({ horizon_text: null }))).toBe("unknown");
    expect(horizonLabel(fact({
      horizon_text: "by 2030",
      target_date_end: "2050-12-31",
    }))).toBe("ambiguous");
    expect(horizonLabel(fact({
      question_key: "ai_extinction_unconditional_by_2070",
      horizon_text: "by end of 2070",
      unit: "probability",
      value_type: "point",
      value_numeric: 0.08,
    }))).toBe("by end of 2070");
  });

  it("keeps extinction, catastrophic harm, disempowerment, AGI arrival, and economic impact apart", () => {
    const rows = distinctQuestions([
      fact({
        question_key: "ai_extinction_unconditional_by_2070",
        question_text: "Unconditional probability of literal human extinction by the end of 2070.",
        definition_text: "Literal human extinction.",
        horizon_text: "by end of 2070",
        unit: "probability",
        value_type: "point",
        value_numeric: 0.08,
      }),
      fact({
        question_key: "ai_catastrophe_not_extinction_by_2070",
        question_text: "Probability of catastrophic harm short of extinction by the end of 2070.",
        definition_text: "Catastrophic harm short of extinction.",
        horizon_text: "by end of 2070",
        unit: "probability",
        value_type: "point",
        value_numeric: 0.25,
      }),
      fact({
        question_key: "permanent_disempowerment_conditional_on_agi",
        question_text: "Probability of permanent human disempowerment conditional on AGI.",
        definition_text: "Permanent disempowerment.",
        condition_text: "conditional on AGI",
        horizon_text: "conditional on AGI",
        unit: "probability",
        value_type: "point",
        value_numeric: 0.4,
      }),
      fact({
        question_key: "agi_arrival_by_2032",
        question_text: "Probability of AGI arrival by the end of 2032.",
        definition_text: "AGI arrival under the speaker's definition.",
        horizon_text: "by end of 2032",
        unit: "probability",
        value_type: "point",
        value_numeric: 0.4,
      }),
      fact({
        question_key: "gdp_growth_pp_by_2035",
        question_text: "Annual GDP growth by 2035.",
        definition_text: "Annual GDP growth, an economic impact quantity.",
        horizon_text: "by 2035",
        unit: "percentage_points",
        value_type: "point",
        value_numeric: 1.5,
      }),
      fact({
        question_key: "extinction_unconditional",
        question_text: "Probability of human extinction from AI.",
        definition_text: "Literal human extinction with no stated horizon.",
        horizon_text: null,
        unit: "probability",
        value_type: "point",
        value_numeric: 0.22,
      }),
      fact({ horizon_text: null, value_numeric: 0.99 }),
    ]);

    const outcomes = new Set(rows.map((row) => row.outcome_id));
    expect(outcomes.has("human_extinction")).toBe(true);
    expect(outcomes.has("catastrophe")).toBe(true);
    expect(outcomes.has("disempowerment")).toBe(true);
    expect(outcomes.has("agi")).toBe(true);
    expect(outcomes.has("gdp")).toBe(true);
    expect(rows).toHaveLength(7);
    expect(rows.every((row) => !("value_numeric" in row))).toBe(true);

    const horizons = rows.map((row) => row.horizon);
    expect(horizons).toContain("by end of 2070");
    expect(horizons).toContain("conditional on AGI");
    expect(horizons).toContain("by end of 2032");
    expect(horizons).toContain("by 2035");
    expect(horizons).toContain("ambiguous");
    expect(horizons).toContain("unknown");
    expect(rows.find((row) => row.question_key === "ai_extinction_unconditional_by_2070")?.horizon).toBe("by end of 2070");
    expect(rows.find((row) => row.question_key === "extinction_unconditional")?.horizon).toBe("ambiguous");

    render(
      <QuestionHorizonList
        topicDefinition="Parent family for distinct risk questions."
        questions={rows}
      />,
    );
    const text = document.body.textContent ?? "";
    expect(text).toContain(SEPARATE_QUESTIONS);
    expect(text).toContain("Literal human extinction.");
    expect(text).toContain("Catastrophic harm short of extinction.");
    expect(text).toContain("Permanent disempowerment.");
    expect(text).toContain("AGI arrival under the speaker's definition.");
    expect(text).toContain("economic impact");
    expect(text).toContain("Horizon ambiguous");
    expect(text).toContain("Horizon unknown");
    expect(text).not.toMatch(/\d+(?:\.\d+)?%/);
    expect(text).not.toContain("0.08");
    expect(text).not.toContain("0.22");
    expect(text).not.toContain("0.25");
    expect(text).not.toContain("0.99");
    expect(text).not.toContain("1.5");
    expect(SEPARATE_QUESTIONS).toContain("Extinction");
    expect(SEPARATE_QUESTIONS).toContain("catastrophic harm");
    expect(SEPARATE_QUESTIONS).toContain("disempowerment");
    expect(SEPARATE_QUESTIONS).toContain("AGI arrival");
    expect(SEPARATE_QUESTIONS).toContain("economic impact");
  });

  it("shows the topic definition and an unknown horizon when statements have not supplied one", () => {
    render(
      <QuestionHorizonList
        topicDefinition="Probability of literal human extinction caused by advanced AI."
        questions={[] as DisplayedQuestion[]}
      />,
    );
    expect(screen.getByText("Probability of literal human extinction caused by advanced AI.")).toBeTruthy();
    expect(screen.getByText("Horizon unknown")).toBeTruthy();
    expect(document.body.textContent ?? "").not.toMatch(/\d+(?:\.\d+)?%/);
  });

  it("does not call a filtered-out list an unknown horizon", () => {
    render(
      <QuestionHorizonList
        topicDefinition="Parent family for distinct risk questions."
        questions={[]}
        includeTopicDefinition={false}
        emptyAsUnknown={false}
      />,
    );
    expect(screen.getByText("This view has no statements.")).toBeTruthy();
    expect(screen.queryByText("Horizon unknown")).toBeNull();
  });
});
