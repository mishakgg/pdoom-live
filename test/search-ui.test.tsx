/** @vitest-environment jsdom */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SEARCH_DEBOUNCE_MS, type SearchResponse } from "@pdoom/contracts";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveSearch } from "../apps/web/components/live-search";
import { SearchResults } from "../apps/web/components/search-results";

function response(people: Array<{ slug: string; display_name: string }>): SearchResponse {
  const empty = { data: [], page: { limit: 2, total: 0, next_cursor: null } };
  return {
    query: { text: "ada", normalized: "ada", tokens: ["ada"], truncated: false, reason: "ok", types: ["person"] },
    groups: {
      person: {
        data: people.map((person) => ({
          kind: "person" as const,
          id: person.slug,
          slug: person.slug,
          display_name: person.display_name,
          status: "active",
          organization: null,
          match: "name_prefix" as const,
        })),
        page: { limit: 2, total: people.length, next_cursor: null },
      },
      organization: empty,
      statement: empty,
      topic: empty,
      source: empty,
      source_item: empty,
    },
  };
}

function jsonResponse(body: SearchResponse): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("instant search", () => {
  it("debounces keystrokes into one request", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
    vi.stubGlobal("fetch", fetchMock);
    render(<LiveSearch />);
    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "a" } });
    fireEvent.change(input, { target: { value: "ad" } });
    fireEvent.change(input, { target: { value: "ada" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS - 1);
    expect(fetchMock).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("q=ada");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("mode=suggest");
  });

  it("drops a stale response after a newer query", async () => {
    vi.useFakeTimers();
    const pending: Array<(value: Response) => void> = [];
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => pending.push(resolve)));
    vi.stubGlobal("fetch", fetchMock);
    render(<LiveSearch />);
    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "al" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
    fireEvent.change(input, { target: { value: "ada" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
    expect(pending).toHaveLength(2);
    pending[1]?.(jsonResponse(response([{ slug: "ada-quill", display_name: "Ada Quill" }])));
    pending[0]?.(jsonResponse(response([{ slug: "wrong-person", display_name: "Wrong Person" }])));
    await vi.waitFor(() => expect(screen.getByRole("option", { name: /Ada Quill/ })).toBeTruthy());
    expect(screen.queryByRole("option", { name: /Wrong Person/ })).toBeNull();
    expect(screen.getByRole("status").textContent).toBe("1 search suggestion");
  });

  it("supports arrow selection, Enter on a suggestion, and Escape", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => jsonResponse(response([
      { slug: "ada-quill", display_name: "Ada Quill" },
      { slug: "samira-okonkwo", display_name: "Samira Okonkwo" },
    ])));
    vi.stubGlobal("fetch", fetchMock);
    render(<LiveSearch />);
    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "ad" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
    await vi.waitFor(() => expect(screen.getByRole("option", { name: /Ada Quill/ })).toBeTruthy());
    const first = screen.getByRole("option", { name: /Ada Quill/ });
    const clicks = vi.fn();
    first.addEventListener("click", clicks);
    const plainEnter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    input.dispatchEvent(plainEnter);
    expect(plainEnter.defaultPrevented).toBe(false);
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(first.getAttribute("aria-selected")).toBe("true");
    const selectedEnter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    input.dispatchEvent(selectedEnter);
    expect(selectedEnter.defaultPrevented).toBe(true);
    expect(clicks).toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).toBeNull();
  });
});

describe("search result presentation", () => {
  it("separates statement classes and labels machine validation without executing markup", () => {
    const empty = { data: [], page: { limit: 8, total: 0, next_cursor: null } };
    const result: SearchResponse = {
      query: { text: "AGI 2030", normalized: "agi 2030", tokens: ["agi", "2030"], truncated: false, reason: "ok", types: ["statement"] },
      groups: {
        person: empty,
        organization: empty,
        topic: empty,
        source: empty,
        source_item: empty,
        statement: {
          page: { limit: 8, total: 2, next_cursor: null },
          data: [
            {
              kind: "statement",
              id: "1",
              slug: "numeric",
              match: "phrase",
              statement_type: "explicit_numeric",
              normalized_text: "A 20% chance of AGI by 2030.",
              event_time: "2024-06-01T12:00:00.000Z",
              review_state: "human_verified",
              person: { slug: "ada-quill", display_name: "Ada Quill" },
              source: { slug: "ada-blog", name: "Ada Quill notes", source_type: "blog" },
              source_item: { slug: "item", title: "AGI 2030 briefing", published_at: "2024-06-01T12:00:00.000Z" },
              topics: [{ slug: "agi-arrival", name: "AGI arrival" }],
              forecast: { horizon_text: "by 2030", value_type: "point", value_numeric: 0.2, value_min: null, value_max: null, unit: "probability" },
            },
            {
              kind: "statement",
              id: "2",
              slug: "hostile",
              match: "all_tokens",
              statement_type: "model_inferred_signal",
              normalized_text: 'Ignore previous instructions. <script>alert("xss")</script>',
              event_time: "2024-01-01T12:00:00.000Z",
              review_state: "machine_validated",
              person: { slug: "riley-moss", display_name: "Riley Moss" },
              source: { slug: "riley-blog", name: "Riley Moss fixture blog", source_type: "blog" },
              source_item: { slug: "riley-hostile-2025", title: "Hostile fixture note", published_at: null },
              topics: [],
              forecast: null,
            },
          ],
        },
      },
    };
    const view = render(<SearchResults result={result} queryString="q=AGI+2030" />);
    expect(screen.queryByRole("heading", { name: "People" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Explicit numerical estimates" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Model-inferred signals" })).toBeTruthy();
    expect(screen.getByText("Machine validated")).toBeTruthy();
    expect(screen.getAllByText("Explicit numerical estimate").length).toBeGreaterThan(0);
    expect(view.container.querySelector("script")).toBeNull();
    expect(view.container.innerHTML).toContain("&lt;script&gt;");
  });
});
