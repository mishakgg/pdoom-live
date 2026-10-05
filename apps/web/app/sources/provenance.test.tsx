/** @vitest-environment jsdom */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { formatWhen } from "@/lib/format";
import { SourceRecord, type LoadedSource } from "./[slug]/page";
import { SourcesCatalog, type ListedSource } from "./page";

const MODEL_PROSE = "Model synthesis: this channel implies a 40 percent extinction probability.";
const PUBLISHED_AT = "2020-01-02T03:04:00.000Z";
const OBSERVED_AT = "2021-05-06T07:08:00.000Z";
const SUCCESS_AT = "2022-09-10T11:12:00.000Z";
const CHECKED_AT = "2023-11-12T13:14:00.000Z";

afterEach(() => {
  cleanup();
});

function listedSource(overrides: Partial<ListedSource> = {}): ListedSource {
  return {
    slug: "ada-blog",
    name: "Ada Quill notes",
    source_type: "blog",
    canonical_url: "https://synthetic.pdoom.example/sources/ada-blog",
    platform: "blog",
    enabled: true,
    last_checked_at: CHECKED_AT,
    last_success_at: SUCCESS_AT,
    collection_method: "fixture",
    collection_adapter: null,
    review_state: "human_verified",
    freshness: "stale",
    rights_notes: null,
    owner_name: "Ada Quill",
    owner_slug: "ada-quill",
    organization_name: null,
    item_count: 1,
    ...overrides,
  };
}

function loadedSource(overrides: Partial<LoadedSource> = {}): LoadedSource {
  return {
    ...listedSource(),
    items: [],
    ...overrides,
  };
}

function field(scope: HTMLElement, term: string): HTMLElement {
  const termNode = within(scope).getByText(term, { selector: "dt" });
  const value = termNode.nextElementSibling;
  if (!(value instanceof HTMLElement) || value.tagName !== "DD") {
    throw new Error(`missing value for ${term}`);
  }
  return value;
}

describe("public source provenance", () => {
  it("shows source type, canonical URL, and stored retrieval times on the list", () => {
    const source = listedSource();
    render(<SourcesCatalog sources={[source]} />);
    const card = screen.getByRole("heading", { name: source.name }).closest("article");
    if (!card) throw new Error("missing source card");

    expect(field(card, "Source type").textContent).toBe("Blog");
    const canonical = within(field(card, "Canonical URL")).getByRole("link");
    expect(canonical.getAttribute("href")).toBe(source.canonical_url);
    expect(canonical.textContent).toContain(source.canonical_url);
    expect(within(card).getByRole("link", { name: source.name }).getAttribute("href")).toBe(`/sources/${source.slug}`);
    expect(field(card, "Last successful collection").textContent).toBe(formatWhen(SUCCESS_AT));
    expect(field(card, "Last check").textContent).toBe(formatWhen(CHECKED_AT));
    expect(field(card, "Last successful collection").textContent).not.toBe(formatWhen(CHECKED_AT));
  });

  it("labels a missing or unreadable retrieval time unknown and does not invent one", () => {
    render(
      <SourcesCatalog
        sources={[
          listedSource({
            slug: "undated-channel",
            name: "Undated channel",
            last_checked_at: null,
            last_success_at: null,
            freshness: "never_checked",
          }),
          listedSource({
            slug: "unreadable-channel",
            name: "Unreadable channel",
            last_checked_at: null,
            last_success_at: "not-a-time",
            freshness: "never_checked",
          }),
        ]}
      />,
    );

    for (const name of ["Undated channel", "Unreadable channel"]) {
      const card = screen.getByRole("heading", { name }).closest("article");
      if (!card) throw new Error(`missing card ${name}`);
      expect(field(card, "Last successful collection").textContent).toBe("Time unknown");
      expect(field(card, "Last check").textContent).toBe("Time unknown");
      expect(card.textContent).not.toMatch(/\d{2}:\d{2} UTC/);
      expect(card.textContent).not.toContain("not-a-time");
      expect(card.textContent).not.toContain(SUCCESS_AT);
      expect(card.textContent).not.toContain(CHECKED_AT);
    }
  });

  it("shows item publication and observation times beside the source link", () => {
    const source = loadedSource({
      source_type: "podcast",
      canonical_url: "https://synthetic.pdoom.example/sources/ada-podcast",
      items: [
        {
          slug: "dated-note",
          title: "Dated note",
          canonical_url: "https://synthetic.pdoom.example/items/dated-note",
          published_at: PUBLISHED_AT,
          observed_at: null,
          collection_status: "collected",
          availability: "available",
          content_reference: null,
          language: "en",
        },
        {
          slug: "retrieved-note",
          title: "Retrieved note",
          canonical_url: "https://synthetic.pdoom.example/items/retrieved-note",
          published_at: null,
          observed_at: OBSERVED_AT,
          collection_status: "collected",
          availability: "available",
          content_reference: null,
          language: null,
        },
      ],
    });
    const { container } = render(<SourceRecord source={source} />);
    const sourceAudit = container.querySelector("dl.audit");
    if (!(sourceAudit instanceof HTMLElement)) throw new Error("missing source audit");

    expect(field(sourceAudit, "Source type").textContent).toBe("Podcast");
    expect(within(field(sourceAudit, "Canonical URL")).getByRole("link").getAttribute("href")).toBe(source.canonical_url);
    expect(field(sourceAudit, "Last successful collection").textContent).toBe(formatWhen(SUCCESS_AT));
    expect(field(sourceAudit, "Last check").textContent).toBe(formatWhen(CHECKED_AT));

    const dated = screen.getByRole("heading", { name: "Dated note" }).closest("article");
    const retrieved = screen.getByRole("heading", { name: "Retrieved note" }).closest("article");
    if (!dated || !retrieved) throw new Error("missing item");

    expect(within(dated).getByRole("link", { name: "Dated note" }).getAttribute("href")).toBe("/source-items/dated-note");
    expect(field(dated, "Published").textContent).toBe(formatWhen(PUBLISHED_AT));
    expect(field(dated, "Observed").textContent).toBe("Time unknown");
    expect(within(field(dated, "Canonical URL")).getByRole("link").getAttribute("href")).toBe(
      "https://synthetic.pdoom.example/items/dated-note",
    );
    expect(dated.textContent).not.toContain(formatWhen(OBSERVED_AT));

    expect(field(retrieved, "Published").textContent).toBe("Time unknown");
    expect(field(retrieved, "Observed").textContent).toBe(formatWhen(OBSERVED_AT));
    expect(retrieved.textContent).not.toContain(formatWhen(PUBLISHED_AT));
  });

  it("does not present model-written prose as a sourced statement", () => {
    render(
      <SourceRecord
        source={loadedSource({
          rights_notes: MODEL_PROSE,
          items: [
            {
              slug: "title-only",
              title: "Stored title",
              canonical_url: "https://synthetic.pdoom.example/items/title-only",
              published_at: null,
              observed_at: null,
              collection_status: "collected",
              availability: "available",
              content_reference: null,
              language: null,
            },
          ],
        })}
      />,
    );

    const prose = screen.getByText(MODEL_PROSE);
    expect(prose.tagName).toBe("P");
    expect(prose.className).toContain("lede");
    expect(prose.closest("blockquote")).toBeNull();
    expect(screen.queryByRole("blockquote")).toBeNull();
    expect(screen.queryByText(/explicit numerical estimate/i)).toBeNull();
    expect(screen.queryByText(MODEL_PROSE, { selector: "blockquote, h1, h2, h3" })).toBeNull();
    const item = screen.getByRole("heading", { name: "Stored title" }).closest("article");
    if (!item) throw new Error("missing item");
    expect(field(item, "Published").textContent).toBe("Time unknown");
    expect(field(item, "Observed").textContent).toBe("Time unknown");
    expect(item.textContent).not.toContain(MODEL_PROSE);
  });
});
