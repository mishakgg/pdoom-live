/** @vitest-environment jsdom */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SEARCH_DEBOUNCE_MS, type SearchResponse } from "@pdoom/contracts";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EntitySelect } from "../apps/web/components/entity-select";
import { FilterForm } from "../apps/web/components/filter-form";

function response(people: Array<{ slug: string; display_name: string; organization: string }>): SearchResponse {
  const empty = { data: [], page: { limit: 8, total: 0, next_cursor: null } };
  return {
    query: { text: "ok", normalized: "ok", tokens: ["ok"], truncated: false, reason: "ok", types: ["person"] },
    groups: {
      person: {
        data: people.map((person) => ({
          kind: "person" as const,
          id: person.slug,
          slug: person.slug,
          display_name: person.display_name,
          status: "active",
          organization: { slug: "org", name: person.organization, role: "Researcher" },
          match: "name_prefix" as const,
        })),
        page: { limit: 8, total: people.length, next_cursor: null },
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

describe("entity selection", () => {
  it("debounces name lookup and stores the slug while showing the name", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => jsonResponse(response([
      { slug: "samira-okonkwo", display_name: "Samira Okonkwo", organization: "Lumen Institute" },
    ])));
    vi.stubGlobal("fetch", fetchMock);
    render(
      <form>
        <EntitySelect kind="person" label="Person" name="person" selected={null} />
      </form>,
    );
    const input = screen.getByRole("combobox", { name: "Person" });
    fireEvent.change(input, { target: { value: "s" } });
    fireEvent.change(input, { target: { value: "sa" } });
    fireEvent.change(input, { target: { value: "sam" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS - 1);
    expect(fetchMock).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("type=person");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("mode=page");
    await vi.waitFor(() => expect(screen.getByRole("option", { name: /Samira Okonkwo/ })).toBeTruthy());
    expect(screen.getByRole("option", { name: /Lumen Institute/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("option", { name: /Samira Okonkwo/ }));
    const hidden = document.querySelector<HTMLInputElement>("input[name='person']");
    expect(hidden?.value).toBe("samira-okonkwo");
    expect(screen.getByText("Samira Okonkwo")).toBeTruthy();
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("drops a stale name response after a newer query", async () => {
    vi.useFakeTimers();
    const pending: Array<(value: Response) => void> = [];
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => pending.push(resolve)));
    vi.stubGlobal("fetch", fetchMock);
    render(<EntitySelect kind="person" label="Person" name="person" selected={null} />);
    const input = screen.getByRole("combobox", { name: "Person" });
    fireEvent.change(input, { target: { value: "sa" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
    fireEvent.change(input, { target: { value: "sam" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
    expect(pending).toHaveLength(2);
    pending[1]?.(jsonResponse(response([{ slug: "samira-okonkwo", display_name: "Samira Okonkwo", organization: "Lumen Institute" }])));
    pending[0]?.(jsonResponse(response([{ slug: "wrong-person", display_name: "Wrong Person", organization: "Elsewhere" }])));
    await vi.waitFor(() => expect(screen.getByRole("option", { name: /Samira Okonkwo/ })).toBeTruthy());
    expect(screen.queryByRole("option", { name: /Wrong Person/ })).toBeNull();
  });

  it("selects with the keyboard and removes the choice without leaving the slug in the form", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => jsonResponse(response([
      { slug: "samir-okonkwo", display_name: "Samir Okonkwo", organization: "Northwind Alignment Lab" },
      { slug: "samira-okonkwo", display_name: "Samira Okonkwo", organization: "Lumen Institute" },
    ])));
    vi.stubGlobal("fetch", fetchMock);
    const submitted = vi.fn((event: Event) => event.preventDefault());
    render(
      <form onSubmit={submitted}>
        <EntitySelect kind="person" label="Person" name="person" selected={null} />
      </form>,
    );
    const input = screen.getByRole("combobox", { name: "Person" });
    fireEvent.change(input, { target: { value: "ok" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
    await vi.waitFor(() => expect(screen.getByRole("option", { name: /Samir Okonkwo/ })).toBeTruthy());
    fireEvent.keyDown(input, { key: "ArrowDown" });
    const selectedEnter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    await act(async () => {
      input.dispatchEvent(selectedEnter);
    });
    expect(selectedEnter.defaultPrevented).toBe(true);
    expect(document.querySelector<HTMLInputElement>("input[name='person']")?.value).toBe("samir-okonkwo");
    fireEvent.click(screen.getByRole("button", { name: "Remove Person" }));
    expect(document.querySelector<HTMLInputElement>("input[name='person']")).toBeNull();
    expect(submitted).toHaveBeenCalled();
  });

  it("hides the previous suggestions as soon as the name changes", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => jsonResponse(response([
      { slug: "samir-okonkwo", display_name: "Samir Okonkwo", organization: "Northwind Alignment Lab" },
    ])));
    vi.stubGlobal("fetch", fetchMock);
    render(<EntitySelect kind="person" label="Person" name="person" selected={null} />);
    const input = screen.getByRole("combobox", { name: "Person" });
    fireEvent.change(input, { target: { value: "ok" } });
    await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS);
    await vi.waitFor(() => expect(screen.getByRole("option", { name: /Samir Okonkwo/ })).toBeTruthy());
    fireEvent.change(input, { target: { value: "sa" } });
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(screen.queryByRole("option", { name: /Samir Okonkwo/ })).toBeNull();
  });

  it("leaves blank fields out of the submitted form", () => {
    const submitted = vi.fn((event: Event) => event.preventDefault());
    render(
      <FilterForm onSubmit={submitted}>
        <input name="q" defaultValue="" />
        <input name="person" defaultValue="ada-quill" />
        <button type="submit">Apply filters</button>
      </FilterForm>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(document.querySelector<HTMLInputElement>("input[name='q']")?.disabled).toBe(true);
    expect(document.querySelector<HTMLInputElement>("input[name='person']")?.disabled).toBe(false);
    expect(submitted).toHaveBeenCalled();
  });
});
