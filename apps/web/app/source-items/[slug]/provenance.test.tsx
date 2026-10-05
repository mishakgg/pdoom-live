/** @vitest-environment jsdom */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { formatWhen, phraseLabel } from "@/lib/format";
import { SourceItemRecord, type SourceItemRecordData } from "./page";

const MODEL_PROSE = "Model synthesis: this channel implies a 40 percent extinction probability.";
const PUBLISHED_AT = "2020-01-02T03:04:00.000Z";
const OBSERVED_AT = "2021-05-06T07:08:00.000Z";
const CONTENT_HASH = "a".repeat(64);
const CANONICAL_URL = "https://synthetic.pdoom.example/items/ada-essay-2023";
const EXCERPT = "Ada Quill wrote that her unconditional probability of human extinction from advanced AI by the end of 2070 was 8 percent.";

afterEach(() => {
  cleanup();
});

function item(overrides: Partial<SourceItemRecordData> = {}): SourceItemRecordData {
  return {
    slug: "ada-essay-2023",
    title: "A fictional note on extinction risk",
    canonical_url: CANONICAL_URL,
    published_at: PUBLISHED_AT,
    published_timezone: "UTC",
    observed_at: OBSERVED_AT,
    language: "en",
    content_hash: CONTENT_HASH,
    content_version: 1,
    content_reference: "fixture://source-items/ada-essay-2023",
    metadata: { synthetic: true },
    collection_status: "collected",
    availability: "available",
    logical_key: "ada-essay-2023",
    collector: "rss",
    collection_method: "fixture",
    rights_notes: null,
    source: {
      slug: "ada-blog",
      name: "Ada Quill notes",
      source_type: "blog",
    },
    participants: [],
    evidence: [],
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

function auditList(container: HTMLElement): HTMLElement {
  const audit = container.querySelector("dl.audit");
  if (!(audit instanceof HTMLElement)) throw new Error("missing audit");
  return audit;
}

describe("public source-item provenance", () => {
  it("shows the canonical URL, stored times, content hash, and collector", () => {
    const record = item();
    const { container } = render(<SourceItemRecord item={record} />);
    const audit = auditList(container);
    const technical = container.querySelector("details.technical");
    if (!(technical instanceof HTMLElement)) throw new Error("missing technical record");

    const canonical = within(field(audit, "URL")).getByRole("link");
    expect(canonical.getAttribute("href")).toBe(CANONICAL_URL);
    expect(canonical.getAttribute("target")).toBe("_blank");
    expect(canonical.textContent).toContain(CANONICAL_URL);
    expect(field(audit, "Published").textContent).toBe(`${formatWhen(PUBLISHED_AT)} (UTC)`);
    expect(field(audit, "Observed").textContent).toBe(formatWhen(OBSERVED_AT));
    expect(field(audit, "Published").textContent).not.toBe(field(audit, "Observed").textContent);
    expect(field(audit, "Collector").textContent).toBe("rss");
    expect(field(audit, "Collection method").textContent).toBe(phraseLabel("fixture"));
    expect(field(technical, "Content hash").textContent).toBe(CONTENT_HASH);
  });

  it("shows the collection method when the record has no collector", () => {
    const { container } = render(
      <SourceItemRecord
        item={item({
          collector: null,
          collection_method: "rss",
        })}
      />,
    );
    const audit = auditList(container);
    expect(within(audit).queryByText("Collector", { selector: "dt" })).toBeNull();
    expect(field(audit, "Collection method").textContent).toBe(phraseLabel("rss"));
    expect(field(audit, "Collection method").textContent).not.toBe(formatWhen(PUBLISHED_AT));
    expect(field(audit, "Collection method").textContent).not.toBe(formatWhen(OBSERVED_AT));
  });

  it("labels a null or unreadable time unknown and does not copy the other time", () => {
    const { rerender, container } = render(
      <SourceItemRecord
        item={item({
          published_at: PUBLISHED_AT,
          published_timezone: "America/New_York",
          observed_at: null,
          collector: null,
          collection_method: null,
        })}
      />,
    );
    let audit = auditList(container);
    expect(field(audit, "Published").textContent).toBe(`${formatWhen(PUBLISHED_AT)} (America/New_York)`);
    expect(field(audit, "Observed").textContent).toBe("Time unknown");
    expect(field(audit, "Observed").textContent).not.toContain(formatWhen(PUBLISHED_AT));
    expect(container.textContent).not.toContain(OBSERVED_AT);

    rerender(
      <SourceItemRecord
        item={item({
          published_at: null,
          published_timezone: "UTC",
          observed_at: OBSERVED_AT,
          collector: " ",
          collection_method: "",
        })}
      />,
    );
    audit = auditList(container);
    expect(field(audit, "Published").textContent).toBe("Time unknown");
    expect(field(audit, "Observed").textContent).toBe(formatWhen(OBSERVED_AT));
    expect(field(audit, "Published").textContent).not.toContain(formatWhen(OBSERVED_AT));
    expect(within(audit).queryByText("Collector", { selector: "dt" })).toBeNull();
    expect(within(audit).queryByText("Collection method", { selector: "dt" })).toBeNull();

    rerender(
      <SourceItemRecord
        item={item({
          title: "Unreadable times",
          published_at: "not-a-time",
          published_timezone: "UTC",
          observed_at: "also-not-a-time",
        })}
      />,
    );
    audit = auditList(container);
    expect(field(audit, "Published").textContent).toBe("Time unknown");
    expect(field(audit, "Observed").textContent).toBe("Time unknown");
    expect(container.textContent).not.toContain("not-a-time");
    expect(container.textContent).not.toContain("also-not-a-time");
    expect(container.textContent).not.toContain(formatWhen(PUBLISHED_AT));
    expect(container.textContent).not.toContain(formatWhen(OBSERVED_AT));
  });

  it("renders a title that contains HTML as text", () => {
    const title = `Hostile note <img src="x" alt="injected" onerror="alert(1)"><script>alert(1)</script>`;
    const { container } = render(<SourceItemRecord item={item({ title })} />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toBe(title);
    expect(heading.querySelector("img, script")).toBeNull();
    expect(container.querySelector("img, script")).toBeNull();
    expect(heading.innerHTML).toContain("&lt;img");
    expect(heading.innerHTML).toContain("&lt;script&gt;");
    expect(heading.innerHTML).not.toMatch(/<\s*img/i);
    expect(heading.innerHTML).not.toMatch(/<\s*script/i);
  });

  it("does not present rights notes or model prose as a sourced quotation", () => {
    render(
      <SourceItemRecord
        item={item({
          title: "Stored title",
          rights_notes: MODEL_PROSE,
          metadata: { synthetic: true, note: "stored metadata only" },
          evidence: [
            {
              slug: "ada-essay-2023-evidence",
              segment_kind: "text",
              sequence: 1,
              start_char: 0,
              end_char: EXCERPT.length,
              start_ms: null,
              end_ms: null,
              text: EXCERPT,
              context_text: "Surrounding fixture context.",
              segment_hash: "b".repeat(64),
            },
          ],
        })}
      />,
    );

    const quote = screen.getByRole("blockquote");
    expect(quote.textContent).toBe(EXCERPT);
    expect(quote.textContent).not.toContain(MODEL_PROSE);
    expect(quote.closest("figure")?.textContent).not.toContain(MODEL_PROSE);
    expect(screen.queryByText(MODEL_PROSE)).toBeNull();
    expect(screen.queryByText(MODEL_PROSE, { selector: "blockquote, h1, h2, h3, p" })).toBeNull();
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Stored title");
    expect(screen.getByText("Surrounding fixture context.").closest("blockquote")).toBeNull();
  });
});
