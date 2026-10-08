import { Children, isValidElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { InvalidCursorError, SearchTimeoutError, searchPublic } from "@pdoom/db";
import { afterEach, describe, expect, it, vi } from "vitest";
import SearchPage from "../apps/web/app/search/page";

vi.mock("@pdoom/db", async (importOriginal) => ({
  ...await importOriginal<typeof import("@pdoom/db")>(),
  searchPublic: vi.fn(),
}));
vi.mock("@/lib/entity-labels", () => ({ resolveFilterLabels: vi.fn(async () => ({})) }));

type ResultsProps = { params: Record<string, string | undefined> };

// Resolve the page's final async Results boundary directly. Leave the production
// component boundary intact so these tests do not require changing streaming.
async function pageResults(params: ResultsProps["params"]): Promise<ReactNode> {
  const page = await SearchPage({ searchParams: Promise.resolve(params) });
  const results = Children.toArray(page.props.children).at(-1);
  if (!isValidElement<ResultsProps>(results) || typeof results.type !== "function") {
    throw new Error("Search page must render its Results boundary");
  }
  return (results.type as (props: ResultsProps) => Promise<ReactNode>)(results.props);
}

afterEach(() => vi.clearAllMocks());

describe("search page cursor recovery", () => {
  it.each([
    new InvalidCursorError(),
    Object.assign(new Error("invalid cursor from another module"), { name: "InvalidCursorError" }),
  ])("offers a restart for %s without retrying or dropping valid filters", async (error) => {
    vi.mocked(searchPublic).mockRejectedValueOnce(error);
    const params = {
      q: "extinction", type: "statement", person: "ada-quill", topic: "ai-extinction",
      statement_type: "explicit_numeric", from: "2020-01-01", to: "2026-12-31", mode: "page", limit: "1",
      cursor: "stale-cursor",
    };
    const html = renderToStaticMarkup(await pageResults(params));
    const expected = new URLSearchParams(params);
    expected.delete("cursor");
    expect(html).toContain('role="alert"');
    expect(html).toContain("This search link is invalid or out of date.");
    expect(html).toContain("Restart this search");
    expect(html).toContain(`href="/search?${expected.toString().replaceAll("&", "&amp;")}"`);
    expect(html).not.toContain("stale-cursor");
    expect(searchPublic).toHaveBeenCalledTimes(1);
    expect(searchPublic).toHaveBeenCalledWith({ ...params, limit: 1 });
  });

  it.each([
    new Error("database unavailable"),
    Object.assign(new Error("unrelated UUID cast failure"), { code: "22P02" }),
    new SearchTimeoutError(),
  ])("rethrows unrelated query failures: %s", async (error) => {
    vi.mocked(searchPublic).mockRejectedValueOnce(error);
    await expect(pageResults({ q: "extinction", type: "statement" })).rejects.toBe(error);
    expect(searchPublic).toHaveBeenCalledTimes(1);
  });
});
