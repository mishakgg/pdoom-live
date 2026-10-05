/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MethodologyDocument } from "./page";

afterEach(() => {
  cleanup();
});

describe("methodology coverage limits", () => {
  it("states the tracked set is a defined cohort and a qualitative statement is not a probability", () => {
    render(<MethodologyDocument />);

    const coverage = screen.getByText(/The tracked set is a defined cohort/).closest("p");
    expect(coverage?.textContent).toBe(
      "The tracked set is a defined cohort and not all AI researchers. The count is the cohort membership shown on the people page.",
    );
    expect(coverage?.textContent).not.toMatch(/\d|consensus|the frontier believes/i);
    expect(screen.getByRole("link", { name: "people page" }).getAttribute("href")).toBe("/people");

    const qualitative = screen.getByText(/A qualitative statement is not a numeric probability/).closest("p");
    expect(qualitative?.textContent).toMatch(/Explicit qualitative view/);
    expect(qualitative?.textContent).toMatch(/A qualitative statement is not a numeric probability\./);
    expect(qualitative?.textContent).toMatch(/does not invent a probability/);
    expect(qualitative?.textContent).not.toMatch(/the frontier believes/i);
  });
});
