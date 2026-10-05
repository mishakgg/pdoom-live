/** @vitest-environment jsdom */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { listStatements } from "@pdoom/db";
import StatementsPage from "./page";

vi.mock("@pdoom/db", () => ({
  listStatements: vi.fn(),
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

type Listed = Awaited<ReturnType<typeof listStatements>> extends { data: Array<infer Row> } ? Row : never;

function row(overrides: Partial<Listed> & Pick<Listed, "slug" | "statement_type" | "normalized_text">): Listed {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    event_time: null,
    review_state: "human_verified",
    confidence: 0.9,
    extractor_version: "fixture",
    person: { slug: "ada-quill", display_name: "Ada Quill" },
    source: { slug: "ada-blog", name: "Ada notes", source_type: "personal_site" },
    source_item: {
      slug: "item",
      title: "Note",
      canonical_url: "https://example.com/note",
      published_at: null,
      observed_at: null,
    },
    forecast: null,
    topics: [],
    ...overrides,
  };
}

function forecast(overrides: Partial<NonNullable<Listed["forecast"]>>): NonNullable<Listed["forecast"]> {
  return {
    question_key: "question",
    question_text: "A stored question.",
    value_type: "point",
    value_numeric: null,
    value_min: null,
    value_max: null,
    unit: "probability",
    horizon_text: null,
    ...overrides,
  };
}

describe("statements list classes", () => {
  it("keeps explicit numeric, explicit qualitative, and model-inferred signal distinct", async () => {
    const rows = [
      row({
        slug: "numeric-point",
        statement_type: "explicit_numeric",
        normalized_text: "A sourced point estimate.",
        forecast: forecast({ value_numeric: 0.12 }),
      }),
      row({
        slug: "numeric-range",
        statement_type: "explicit_numeric",
        normalized_text: "A sourced range.",
        forecast: forecast({ value_type: "range", value_numeric: null, value_min: 0.1, value_max: 0.2 }),
      }),
      row({
        slug: "numeric-missing",
        statement_type: "explicit_numeric",
        normalized_text: "A sourced estimate with no stored number.",
        forecast: forecast({ value_numeric: null, value_min: 0.1, value_max: null }),
      }),
      row({
        slug: "qualitative",
        statement_type: "explicit_qualitative",
        normalized_text: "A sourced view without a number.",
        forecast: forecast({ value_numeric: 0.42, value_type: "point" }),
      }),
      row({
        slug: "inferred",
        statement_type: "model_inferred_signal",
        normalized_text: "A machine reading of the source.",
        review_state: "machine_validated",
        forecast: forecast({ value_numeric: 0.07, value_type: "point" }),
      }),
    ];
    vi.mocked(listStatements).mockResolvedValue({
      data: rows,
      page: { limit: 10, total: rows.length, next_cursor: null, prev_cursor: null },
    });

    render(await StatementsPage({ searchParams: Promise.resolve({}) }));

    const articles = {
      point: screen.getByRole("link", { name: "A sourced point estimate." }).closest("article"),
      range: screen.getByRole("link", { name: "A sourced range." }).closest("article"),
      missing: screen.getByRole("link", { name: "A sourced estimate with no stored number." }).closest("article"),
      qualitative: screen.getByRole("link", { name: "A sourced view without a number." }).closest("article"),
      inferred: screen.getByRole("link", { name: "A machine reading of the source." }).closest("article"),
    };
    for (const article of Object.values(articles)) expect(article).toBeTruthy();

    expect(within(articles.point!).getByText("explicit numeric")).toBeTruthy();
    expect(articles.point!.textContent).toContain("12%");
    expect(within(articles.point!).queryByText("explicit qualitative")).toBeNull();
    expect(within(articles.point!).queryByText("model-inferred signal")).toBeNull();

    expect(within(articles.range!).getByText("explicit numeric")).toBeTruthy();
    expect(articles.range!.textContent).toContain("10%");
    expect(articles.range!.textContent).toContain("20%");
    expect(articles.range!.textContent).not.toContain("15%");

    expect(within(articles.missing!).getByText("explicit numeric")).toBeTruthy();
    expect(articles.missing!.textContent).not.toMatch(/%/);
    expect(articles.missing!.textContent).not.toContain("—");
    expect(articles.missing!.textContent).not.toContain("10%");

    expect(within(articles.qualitative!).getByText("explicit qualitative")).toBeTruthy();
    expect(within(articles.qualitative!).queryByText("explicit numeric")).toBeNull();
    expect(within(articles.qualitative!).queryByText("model-inferred signal")).toBeNull();
    expect(articles.qualitative!.textContent).not.toMatch(/%/);
    expect(articles.qualitative!.textContent).not.toContain("42");

    expect(within(articles.inferred!).getByText("model-inferred signal")).toBeTruthy();
    expect(within(articles.inferred!).queryByText("explicit numeric")).toBeNull();
    expect(within(articles.inferred!).queryByText("explicit qualitative")).toBeNull();
    expect(articles.inferred!.textContent).not.toMatch(/%/);
    expect(articles.inferred!.textContent).not.toContain("7%");
    expect(articles.inferred!.textContent).not.toContain("0.07");
  });
});
