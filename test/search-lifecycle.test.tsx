/** @vitest-environment jsdom */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { SEARCH_DEBOUNCE_MS } from "@pdoom/contracts";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveSearch } from "../apps/web/components/live-search";
import { EntitySelect } from "../apps/web/components/entity-select";
import { FilterForm } from "../apps/web/components/filter-form";
import { filterStateKey } from "../apps/web/lib/presentation";

const navigation = vi.hoisted(() => ({ pathname: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => navigation.pathname }));
const empty = { data: [], page: { limit: 8, total: 0, next_cursor: null } };
const body = {
  query: { text: "ada", normalized: "ada", tokens: ["ada"], reason: "ok", truncated: false, types: ["person"] },
  groups: {
    person: {
      data: Array.from({ length: 8 }, (_, index) => ({
        kind: "person", id: `ada-${index}`, slug: `ada-${index}`, display_name: `Ada ${index}`,
        status: "active", organization: null, match: "name_prefix",
      })),
      page: { limit: 8, total: 8, next_cursor: null },
    },
    organization: empty, statement: empty, topic: empty, source: empty, source_item: empty,
  },
};
const response = () => new Response(JSON.stringify(body), { status: 200 });
const controls = [
  ["global search", LiveSearch],
  ["entity selector", () => <EntitySelect kind="person" label="Person" name="person" selected={null} />],
] as const;

async function debounce() {
  await act(async () => { await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS); });
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  navigation.pathname = "/";
});

for (const [name, Component] of controls) {
  describe(`${name} interrupted requests`, () => {
    for (const dismissal of ["Escape", "blur", "outside pointer", "clear", "shorten"] as const) {
      it(`ignores a buffered response after ${dismissal}`, async () => {
        vi.useFakeTimers();
        let complete!: (value: unknown) => void;
        vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: () => new Promise((resolve) => { complete = resolve; }) })));
        render(<Component />);
        const input = screen.getByRole("combobox");
        fireEvent.change(input, { target: { value: "ada" } });
        await debounce();
        if (dismissal === "Escape") fireEvent.keyDown(input, { key: "Escape" });
        if (dismissal === "blur") fireEvent.blur(input, { relatedTarget: document.body });
        if (dismissal === "outside pointer") fireEvent.pointerDown(document.body);
        if (dismissal === "clear") fireEvent.change(input, { target: { value: "" } });
        if (dismissal === "shorten") fireEvent.change(input, { target: { value: "a" } });
        await act(async () => { complete(body); });
        expect(screen.queryByRole("listbox")).toBeNull();
        expect(input.getAttribute("aria-expanded")).toBe("false");
      });
    }

    it("cancels a pending debounce on dismissal and can search again on focus", async () => {
      vi.useFakeTimers();
      const fetchMock = vi.fn(async () => response());
      vi.stubGlobal("fetch", fetchMock);
      render(<Component />);
      const input = screen.getByRole("combobox");
      fireEvent.change(input, { target: { value: "ada" } });
      fireEvent.keyDown(input, { key: "Escape" });
      await debounce();
      expect(fetchMock).not.toHaveBeenCalled();
      fireEvent.focus(input);
      await debounce();
      expect(screen.getByRole("listbox")).toBeTruthy();
      fireEvent.blur(input, { relatedTarget: document.body });
      expect(screen.queryByRole("listbox")).toBeNull();
    });

    it("keeps tabbing inside the popup usable and scrolls the keyboard-active option", async () => {
      vi.useFakeTimers();
      vi.stubGlobal("fetch", vi.fn(async () => response()));
      render(<Component />);
      const input = screen.getByRole("combobox");
      fireEvent.change(input, { target: { value: "ada" } });
      await debounce();
      const last = screen.getAllByRole("option").at(-1)!;
      const scroll = vi.fn();
      Object.defineProperty(last, "scrollIntoView", { configurable: true, value: scroll });
      for (let index = 0; index < 8; index += 1) fireEvent.keyDown(input, { key: "ArrowDown" });
      expect(scroll).toHaveBeenCalledWith({ block: "nearest" });
      fireEvent.blur(input, { relatedTarget: last });
      expect(screen.getByRole("listbox")).toBeTruthy();
    });
  });
}

it("resets global search when the persistent header changes route", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn(async () => response()));
  const view = render(<LiveSearch />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "ada" } });
  await debounce();
  navigation.pathname = "/people";
  view.rerender(<LiveSearch />);
  expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("");
  expect(screen.queryByRole("listbox")).toBeNull();
});

it("closes global suggestions immediately after a selected link is activated", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn(async () => response()));
  render(<LiveSearch />);
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "ada" } });
  await debounce();
  const option = screen.getAllByRole("option")[0]!;
  option.addEventListener("click", (event) => event.preventDefault());
  fireEvent.click(option);
  expect(screen.queryByRole("listbox")).toBeNull();
  expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("");
});

it("resets controls for status/type URL changes and cannot collide on embedded separators", () => {
  expect(filterStateKey({ status: "active" })).not.toBe(filterStateKey({ status: "historical" }));
  expect(filterStateKey({ q: "Ada", type: "person" })).not.toBe(filterStateKey({ q: "Ada", type: "statement" }));
  expect(filterStateKey({ q: "x&person=y" })).not.toBe(filterStateKey({ q: "x", person: "y" }));
  const Form = ({ status }: { status: string }) => <FilterForm key={filterStateKey({ status })}><select aria-label="Status" defaultValue={status}><option value="active">Active</option><option value="historical">Historical</option></select></FilterForm>;
  const view = render(<Form status="active" />);
  view.rerender(<Form status="historical" />);
  expect((screen.getByRole("combobox") as HTMLSelectElement).value).toBe("historical");
});

it("leaves filters editable after repeated canceled submits and preserves nonempty duplicate values", () => {
  render(<FilterForm onSubmit={(event) => event.preventDefault()}><input aria-label="Text" name="q" /><input name="tag" defaultValue="" /><input name="tag" defaultValue="keep" /><button>Apply</button></FilterForm>);
  for (let attempt = 0; attempt < 2; attempt += 1) fireEvent.click(screen.getByRole("button"));
  const input = screen.getByRole("textbox", { name: "Text" }) as HTMLInputElement;
  expect(input.disabled).toBe(false);
  fireEvent.change(input, { target: { value: "risk" } });
  const formData = new FormData(input.form!);
  const event = new Event("formdata");
  Object.defineProperty(event, "formData", { value: formData });
  input.form!.dispatchEvent(event);
  expect(formData.get("q")).toBe("risk");
  expect(formData.getAll("tag")).toEqual(["keep"]);
});
