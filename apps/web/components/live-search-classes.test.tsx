/** @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { SEARCH_DEBOUNCE_MS, type SearchResponse } from "@pdoom/contracts/browser";
import { afterEach, expect, it, vi } from "vitest";
import { LiveSearch } from "./live-search";

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

it("labels the class and review state before a statement suggestion is opened", async () => {
  vi.useFakeTimers();
  const empty = { data: [], page: { limit: 2, total: 0, next_cursor: null } };
  const body: SearchResponse = {
    query: { text: "risk", normalized: "risk", tokens: ["risk"], truncated: false, reason: "ok", types: ["statement"] },
    groups: {
      person: empty, organization: empty, topic: empty, source: empty, source_item: empty,
      statement: {
        data: [
          { kind: "statement", id: "numeric", slug: "numeric", normalized_text: "A direct risk estimate.", statement_type: "explicit_numeric", review_state: "human_verified", event_time: null, person: { slug: "ada", display_name: "Ada" }, source: { slug: "notes", name: "Notes", source_type: "blog" }, source_item: { slug: "item", title: "Risk note", published_at: null }, forecast: null, topics: [], match: "phrase" },
          { kind: "statement", id: "inferred", slug: "inferred", normalized_text: "A model reading of risk.", statement_type: "model_inferred_signal", review_state: "machine_validated", event_time: null, person: { slug: "ada", display_name: "Ada" }, source: { slug: "notes", name: "Notes", source_type: "blog" }, source_item: { slug: "item", title: "Risk note", published_at: null }, forecast: null, topics: [], match: "phrase" },
          { kind: "statement", id: "qualitative", slug: "qualitative", normalized_text: "A qualitative risk view.", statement_type: "explicit_qualitative", review_state: "needs_review", event_time: null, person: { slug: "ada", display_name: "Ada" }, source: { slug: "notes", name: "Notes", source_type: "blog" }, source_item: { slug: "item", title: "Risk note", published_at: null }, forecast: null, topics: [], match: "phrase" },
        ],
        page: { limit: 3, total: 3, next_cursor: null },
      },
    },
  };
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body))));
  render(<LiveSearch />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "risk" } });
  await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
  await vi.waitFor(() => expect(screen.getAllByRole("option")).toHaveLength(3));
  const numeric = within(screen.getByRole("option", { name: /A direct risk estimate/ }));
  expect(numeric.getByText("Explicit numerical estimate")).toBeTruthy();
  expect(numeric.getByText("Human verified")).toBeTruthy();
  const inferred = within(screen.getByRole("option", { name: /A model reading of risk/ }));
  expect(inferred.getByText("Model-inferred signal")).toBeTruthy();
  expect(inferred.getByText("Machine validated")).toBeTruthy();
  expect(inferred.queryByText("Human verified")).toBeNull();
  const qualitative = within(screen.getByRole("option", { name: /A qualitative risk view/ }));
  expect(qualitative.getByText("Explicit qualitative view")).toBeTruthy();
  expect(qualitative.getByText("Needs review")).toBeTruthy();
});
