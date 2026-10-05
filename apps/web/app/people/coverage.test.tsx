/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { listPeople } from "@pdoom/db";
import PeoplePage from "./page";

vi.mock("@pdoom/db", () => ({
  listPeople: vi.fn(),
  InvalidCursorError: class InvalidCursorError extends Error {
    constructor(message = "invalid cursor") {
      super(message);
      this.name = "InvalidCursorError";
    }
  },
  AdmissionError: class AdmissionError extends Error {},
  SearchTimeoutError: class SearchTimeoutError extends Error {},
  isStatementTimeout: () => false,
}));

vi.mock("@/lib/entity-labels", () => ({
  resolveFilterLabels: async () => ({
    person: null,
    organization: null,
    source: null,
    topic: null,
  }),
}));

afterEach(() => {
  cleanup();
});

const COHORT_COPY =
  "The tracked set is a defined cohort and not all AI researchers. The count is the cohort membership shown on this page.";

type Listed = Awaited<ReturnType<typeof listPeople>> extends { data: Array<infer Row> } ? Row : never;

function person(index: number, displayName: string): Listed {
  return {
    id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    slug: displayName.toLowerCase().replaceAll(" ", "-"),
    display_name: displayName,
    bio_short: "Tracked member of the reviewed cohort.",
    status: "active",
    inclusion_reason: "Reviewed member of the defined cohort.",
    cohort_tags: ["cohort_2026_09"],
    organization: null,
    statement_counts: {},
  };
}

function loaded(names: string[]) {
  const data = names.map((name, index) => person(index + 1, name));
  return {
    data,
    page: {
      limit: 20,
      total: data.length,
      next_cursor: null,
      prev_cursor: null,
    },
  };
}

async function renderPeople(names: string[]) {
  const result = loaded(names);
  vi.mocked(listPeople).mockResolvedValue(result);
  render(await PeoplePage({ searchParams: Promise.resolve({}) }));
  return result;
}

describe("people page coverage", () => {
  it("states the tracked set is a defined cohort and shows the loaded membership count", async () => {
    for (const names of [
      ["Ada Quill"],
      ["Ada Quill", "Bao Lin", "Cleo Moss", "Dee Park"],
    ]) {
      const result = await renderPeople(names);
      const coverage = screen.getByText(/The tracked set is a defined cohort/).closest("p");
      expect(coverage?.textContent).toBe(COHORT_COPY);
      expect(coverage?.textContent).not.toMatch(/\d|consensus|the frontier believes/i);
      expect(screen.getByText(`${result.page.total} people`).textContent).toBe(`${result.data.length} people`);
      for (const name of names) {
        expect(screen.getByRole("link", { name }).getAttribute("href")).toBe(`/people/${name.toLowerCase().replaceAll(" ", "-")}`);
      }
      expect(document.body.textContent).not.toMatch(/consensus|the frontier believes/i);
      cleanup();
    }
  });

  it("shows zero when the loaded cohort membership is empty", async () => {
    vi.mocked(listPeople).mockResolvedValue({
      data: [],
      page: { limit: 20, total: 0, next_cursor: null, prev_cursor: null },
    });

    render(await PeoplePage({ searchParams: Promise.resolve({}) }));

    const coverage = screen.getByText(/The tracked set is a defined cohort/).closest("p");
    expect(coverage?.textContent).toBe(COHORT_COPY);
    expect(coverage?.textContent).not.toMatch(/\d|consensus|the frontier believes/i);
    expect(screen.getByText("0 people").textContent).toBe("0 people");
    expect(screen.getByRole("heading", { name: "No people are loaded" })).toBeTruthy();
    expect(screen.queryByText(/[1-9]\d* people/)).toBeNull();
    expect(document.body.textContent).not.toMatch(/consensus|the frontier believes/i);
  });
});
