/** @vitest-environment jsdom */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { StatementCardData } from "@/components/statement-bits";
import { loadDataset, loadPerson } from "@/lib/loaders";
import PersonPage from "./page";

vi.mock("@/lib/loaders", () => ({
  loadPerson: vi.fn(),
  loadDataset: vi.fn(),
}));

vi.mock("@/lib/request-nonce", () => ({
  requestNonce: vi.fn(async () => undefined),
}));

vi.mock("@pdoom/db", () => ({
  listStatements: vi.fn(),
}));

afterEach(() => {
  cleanup();
});

function forecast(overrides: Partial<NonNullable<StatementCardData["forecast"]>>): NonNullable<StatementCardData["forecast"]> {
  return {
    question_key: "question",
    value_type: "point",
    value_numeric: null,
    value_min: null,
    value_max: null,
    unit: "probability",
    horizon_text: null,
    ...overrides,
  };
}

function row(overrides: Partial<StatementCardData> & Pick<StatementCardData, "slug" | "statement_type" | "normalized_text">): StatementCardData {
  return {
    event_time: null,
    review_state: "human_verified",
    person: { slug: "ada-quill", display_name: "Ada Quill" },
    source: { slug: "ada-blog", name: "Ada notes", source_type: "personal_site" },
    source_item: {
      published_at: null,
      observed_at: null,
    },
    forecast: null,
    topics: [],
    ...overrides,
  };
}

function person(statements: StatementCardData[]) {
  return {
    slug: "ada-quill",
    display_name: "Ada Quill",
    given_name: "Ada",
    family_name: "Quill",
    bio_short: "Research lead.",
    status: "active",
    inclusion_reason: "Included for the fixture.",
    cohort_tags: [],
    updated_at: null,
    affiliations: [],
    identities: [],
    sources: [],
    statements,
    statement_total: statements.length,
  };
}

describe("person statement classes", () => {
  it("labels each statement and shows a stored quantity only on an explicit numeric row that has one", async () => {
    const statements = [
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
    vi.mocked(loadPerson).mockResolvedValue(person(statements) as NonNullable<Awaited<ReturnType<typeof loadPerson>>>);
    vi.mocked(loadDataset).mockResolvedValue(null);

    render(await PersonPage({
      params: Promise.resolve({ slug: "ada-quill" }),
      searchParams: Promise.resolve({}),
    }));

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
    expect(articles.missing!.textContent).not.toContain("No numeric value");

    expect(within(articles.qualitative!).getByText("explicit qualitative")).toBeTruthy();
    expect(within(articles.qualitative!).queryByText("explicit numeric")).toBeNull();
    expect(within(articles.qualitative!).queryByText("model-inferred signal")).toBeNull();
    expect(articles.qualitative!.textContent).not.toMatch(/%/);
    expect(articles.qualitative!.textContent).not.toContain("42");
    expect(articles.qualitative!.textContent).not.toContain("No numeric value");

    expect(within(articles.inferred!).getByText("model-inferred signal")).toBeTruthy();
    expect(within(articles.inferred!).queryByText("explicit numeric")).toBeNull();
    expect(within(articles.inferred!).queryByText("explicit qualitative")).toBeNull();
    expect(articles.inferred!.textContent).not.toMatch(/%/);
    expect(articles.inferred!.textContent).not.toContain("7%");
    expect(articles.inferred!.textContent).not.toContain("0.07");
    expect(articles.inferred!.textContent).not.toContain("No numeric value");

    expect(screen.getByText(/not a personal probability/)).toBeTruthy();
    expect(screen.queryByText(/personal p\(doom\)/i)).toBeNull();
    const pageText = document.body.textContent ?? "";
    expect(pageText).not.toContain("42%");
    expect(pageText).not.toContain("7%");
    expect(pageText).not.toContain("15%");
  });
});
