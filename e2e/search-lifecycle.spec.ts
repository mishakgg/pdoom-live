import type { SearchEntityType, SearchResponse } from "@pdoom/contracts";
import { expect, test } from "./support/test";

const empty = { data: [], page: { limit: 8, total: 0, next_cursor: null } };
const suggestions: SearchResponse = {
  query: { text: "ada", normalized: "ada", tokens: ["ada"], truncated: false, reason: "ok", types: ["person"] },
  groups: {
    person: {
      data: Array.from({ length: 8 }, (_, index) => ({
        kind: "person", id: `ada-${index}`, slug: index === 0 ? "ada-quill" : `fixture-person-${index}`, display_name: `Ada fixture ${index}`,
        status: "active", organization: null, match: "name_prefix",
      })),
      page: { limit: 8, total: 8, next_cursor: null },
    },
    organization: empty, statement: empty, topic: empty, source: empty, source_item: empty,
  },
};

for (const name of ["Search people, statements, topics, and sources", "Person"]) {
  test(`${name} stays dismissed during an interrupted lookup`, async ({ page }) => {
    let started = false;
    let finish!: () => void;
    const released = new Promise<void>((resolve) => { finish = resolve; });
    await page.route("**/api/search?**", async (route) => {
      started = true;
      await released;
      await route.fulfill({ json: suggestions });
    });
    await page.goto("/statements");
    const input = page.getByRole("combobox", { name, exact: true });
    await input.fill("ada");
    await expect.poll(() => started).toBe(true);
    await input.press("Escape");
    finish();
    // Observe the delayed completion, rather than only the instant Escape state.
    await page.waitForTimeout(250);
    await expect(input).toHaveAttribute("aria-expanded", "false");
    await page.getByRole("heading", { name: "Statements", exact: true }).click();
    await expect(page.getByRole("listbox")).toHaveCount(0);
  });
}

test("keyboard suggestions stay visible, dismiss outside, and reset after navigation", async ({ page }, testInfo) => {
  // Keep unique slugs/DOM IDs while retaining one real detail destination below.
  await page.route("**/api/search?**", (route) => route.fulfill({
    json: { ...suggestions, groups: { ...suggestions.groups, person: {
      ...suggestions.groups.person,
      data: suggestions.groups.person.data.map((person, index) => ({ ...person, slug: index === 0 ? "ada-quill" : `fixture-person-${index}` })),
    } } },
  }));
  await page.goto("/statements");
  const input = page.getByRole("combobox", { name: "Search people, statements, topics, and sources" });
  await input.fill("ada");
  await expect(page.getByRole("listbox")).toBeVisible();
  for (let index = 0; index < 8; index += 1) await input.press("ArrowDown");
  const visible = await input.evaluate((element) => {
    const id = element.getAttribute("aria-activedescendant");
    const option = id ? document.getElementById(id) : null;
    const list = option?.closest("[role=listbox]");
    if (!option || !list) return false;
    const itemBounds = option.getBoundingClientRect();
    const listBounds = list.getBoundingClientRect();
    return itemBounds.top >= listBounds.top && itemBounds.bottom <= listBounds.bottom + 1;
  });
  expect(visible).toBe(true);
  // On mobile the popup covers the page heading. Click exposed page padding,
  // after verifying hit-testing really is outside the widget; never force a
  // click through a suggestion (which would test a different interaction).
  const outside = { x: 2, y: 2 };
  expect(await page.evaluate(({ x, y }) => {
    const target = document.elementFromPoint(x, y);
    return target !== null && !target.closest("form.search");
  }, outside)).toBe(true);
  if (testInfo.project.use.hasTouch) await page.touchscreen.tap(outside.x, outside.y);
  else await page.mouse.click(outside.x, outside.y);
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await input.fill("adab");
  await page.getByRole("option", { name: /Ada fixture 0/ }).click();
  await expect(page).toHaveURL(/\/people\/ada-quill$/);
  await expect(input).toHaveValue("");
  await expect(page.getByRole("listbox")).toHaveCount(0);
});

test("canceled filter submits preserve editing and omit only empty submitted values", async ({ page }) => {
  await page.goto("/people");
  const form = page.locator("form.filters");
  await form.evaluate((element) => element.addEventListener("submit", (event) => event.preventDefault()));
  await page.getByRole("button", { name: "Apply filters" }).click();
  const name = page.getByRole("textbox", { name: "Name", exact: true });
  const status = page.getByRole("combobox", { name: "Status", exact: true });
  await expect(name).toBeEnabled();
  await expect(status).toBeEnabled();
  await name.fill("Ada");
  await status.selectOption("active");
  await page.getByRole("button", { name: "Apply filters" }).click();
  expect(await form.evaluate((element) => [...new FormData(element as HTMLFormElement).entries()])).toEqual([
    ["q", "Ada"], ["status", "active"],
  ]);
  await name.fill("");
  await status.selectOption("");
  expect(await form.evaluate((element) => [...new FormData(element as HTMLFormElement).entries()])).toEqual([]);
});

for (const problem of ["malformed ID", "stale fingerprint"]) {
  test(`search recovers from a ${problem} while retaining filters`, async ({ page }) => {
    const params = new URLSearchParams({
      q: "extinction", type: "statement", person: "ada-quill", topic: "ai-extinction",
      statement_type: "explicit_numeric", from: "2020-01-01", to: "2026-12-31", mode: "page", limit: "1",
    });
    const response = await page.request.get(`/api/search?${params}`);
    expect(response.ok()).toBe(true);
    const result = await response.json() as SearchResponse;
    const cursor = result.groups.statement.page.next_cursor;
    expect(cursor).toBeTruthy();
    const payload = JSON.parse(Buffer.from(cursor!, "base64url").toString("utf8")) as Record<string, unknown>;
    if (problem === "malformed ID") payload.id = "-".repeat(36);
    else payload.fp = "stale";
    params.set("cursor", Buffer.from(JSON.stringify(payload)).toString("base64url"));
    await page.goto(`/search?${params}`);

    const warning = page.getByRole("alert").filter({ hasText: "This search link is invalid or out of date." });
    await expect(warning).toBeVisible();
    const restart = page.getByRole("link", { name: "Restart this search" });
    params.delete("cursor");
    await expect(restart).toHaveAttribute("href", `/search?${params}`);
    const form = page.locator("form.filters");
    await expect(form.getByRole("textbox", { name: "Text", exact: true })).toHaveValue("extinction");
    await expect(form.locator('[name="type"]')).toHaveValue("statement");
    await expect(form.locator('[name="person"]')).toHaveValue("ada-quill");
    await expect(form.locator('[name="topic"]')).toHaveValue("ai-extinction");
    await expect(form.locator('[name="statement_type"]')).toHaveValue("explicit_numeric");
    await expect(form.locator('[name="from"]')).toHaveValue("2020-01-01");
    await expect(form.locator('[name="to"]')).toHaveValue("2026-12-31");
    await expect(form.getByRole("button", { name: "Search", exact: true })).toBeEnabled();

    await restart.click();
    await expect(page).toHaveURL((url) => url.pathname === "/search" && url.searchParams.toString() === params.toString());
    await expect(warning).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Explicit numerical estimates", exact: true })).toBeVisible();
    await page.goBack();
    await expect(warning).toBeVisible();
    await expect(restart).toHaveAttribute("href", `/search?${params}`);
  });
}

const groupedContinuationCases: Array<{
  kind: SearchEntityType;
  heading: string;
  query: string;
  firstSlug: string;
  nextSlug: string;
}> = [
  { kind: "person", heading: "People", query: "Okonkwo", firstSlug: "samir-okonkwo", nextSlug: "samira-okonkwo" },
  { kind: "organization", heading: "Organizations", query: "lead", firstSlug: "brightpath-robotics", nextSlug: "northwind-alignment-lab" },
  { kind: "statement", heading: "Statements", query: "Ada Quill", firstSlug: "ada-extinction-2025", nextSlug: "ada-inferred-2024" },
  { kind: "topic", heading: "Topics", query: "AI", firstSlug: "ai-catastrophic-harm", nextSlug: "frontier-ai-risk" },
  { kind: "source", heading: "Sources", query: "Harbor", firstSlug: "harbor-blog", nextSlug: "harbor-papers" },
  { kind: "source_item", heading: "Source item titles", query: "labor", firstSlug: "lumen-paper-2025", nextSlug: "samira-letter-2024" },
];

function searchHitPath(kind: SearchEntityType, slug: string): string {
  const roots = {
    person: "/people/", organization: "/people?organization=", statement: "/statements/",
    topic: "/topics/", source: "/sources/", source_item: "/source-items/",
  };
  return `${roots[kind]}${slug}`;
}

for (const { kind, heading, query, firstSlug, nextSlug } of groupedContinuationCases) {
  test(`untyped search ${kind} More opens the next result`, async ({ page }) => {
    // Use the real fixture-backed route and the rendered href, rather than
    // constructing a typed cursor request or mocking the search API.
    const params = new URLSearchParams({ q: query, mode: "page", limit: "1" });
    const firstResponse = await page.request.get(`/api/search?${params}`);
    expect(firstResponse.ok()).toBe(true);
    const firstResult = await firstResponse.json() as SearchResponse;
    expect(firstResult.query.types).toHaveLength(6);
    expect(firstResult.groups[kind].data.map((hit) => hit.slug)).toEqual([firstSlug]);
    expect(firstResult.groups[kind].page.total).toBeGreaterThan(1);

    await page.goto(`/search?${params}`);
    expect(new URL(page.url()).searchParams.has("type")).toBe(false);
    const section = page.getByRole("region", { name: heading, exact: true });
    const firstHit = section.locator(`a[href="${searchHitPath(kind, firstSlug)}"]`);
    const nextHit = section.locator(`a[href="${searchHitPath(kind, nextSlug)}"]`);
    await expect(firstHit).toBeVisible();
    await expect(section.locator("article.card")).toHaveCount(1);
    await expect(nextHit).toHaveCount(0);
    const more = section.getByRole("link", { name: "More", exact: true });
    const href = await more.getAttribute("href");
    expect(href).toBeTruthy();
    const nextUrl = new URL(href!, page.url());
    expect(nextUrl.searchParams.get("type")).toBe(kind);
    expect(nextUrl.searchParams.get("cursor")).toBeTruthy();
    for (const [key, value] of params) expect(nextUrl.searchParams.get(key)).toBe(value);

    await more.click();
    await expect(page).toHaveURL(nextUrl.href);
    await expect(page.getByRole("alert").filter({ hasText: "This search link is invalid or out of date." })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Restart this search" })).toHaveCount(0);
    await expect(page.locator("section.search-kind")).toHaveCount(1);
    await expect(nextHit).toBeVisible();
    await expect(section.locator("article.card")).toHaveCount(1);
    await expect(firstHit).toHaveCount(0);
    await expect(page.getByRole("status").filter({ hasText: "public matches" }))
      .toHaveText(`${firstResult.groups[kind].page.total} public matches`);

    const nextResponse = await page.request.get(`/api/search${nextUrl.search}`);
    expect(nextResponse.ok()).toBe(true);
    const nextResult = await nextResponse.json() as SearchResponse;
    expect(nextResult.query.types).toEqual([kind]);
    expect(nextResult.groups[kind].data.map((hit) => hit.slug)).toEqual([nextSlug]);
    expect(nextResult.groups[kind].page.total).toBe(firstResult.groups[kind].page.total);
  });
}

test("filtered untyped statement More preserves normalized text and filters through history", async ({ page }) => {
  const params = new URLSearchParams({
    q: "  ＡＤＡ　   ＱＵＩＬＬ  ", person: "ada-quill", topic: "ai-extinction",
    statement_type: "explicit_numeric", from: "2020-01-01", to: "2026-12-31", mode: "page", limit: "1",
  });
  const response = await page.request.get(`/api/search?${params}`);
  expect(response.ok()).toBe(true);
  const firstResult = await response.json() as SearchResponse;
  expect(firstResult.query.normalized).toBe("ada quill");
  expect(firstResult.query.types).toEqual(["statement"]);
  expect(firstResult.groups.statement.data.map((hit) => hit.slug)).toEqual(["ada-extinction-2025"]);
  expect(firstResult.groups.statement.page.total).toBe(2);
  expect(firstResult.groups.statement.page.next_cursor).toBeTruthy();

  await page.goto(`/search?${params}`);
  const firstUrl = page.url();
  expect(new URL(firstUrl).searchParams.has("type")).toBe(false);
  const section = page.getByRole("region", { name: "Statements", exact: true });
  const firstHit = section.locator('a[href="/statements/ada-extinction-2025"]');
  const nextHit = section.locator('a[href="/statements/ada-extinction-2023"]');
  const more = section.getByRole("link", { name: "More", exact: true });
  await expect(firstHit).toBeVisible();
  await expect(nextHit).toHaveCount(0);
  const href = await more.getAttribute("href");
  expect(href).toBeTruthy();
  const nextUrl = new URL(href!, firstUrl);
  const expectedParams = new URLSearchParams(params);
  expectedParams.set("type", "statement");
  expectedParams.set("cursor", firstResult.groups.statement.page.next_cursor!);
  expect(nextUrl.searchParams.toString()).toBe(expectedParams.toString());

  const expectFilters = async (type: string) => {
    const form = page.locator("form.filters");
    await expect(form.getByRole("textbox", { name: "Text", exact: true })).toHaveValue(params.get("q")!);
    await expect(form.locator('[name="type"]')).toHaveValue(type);
    for (const name of ["person", "topic", "statement_type", "from", "to"]) {
      await expect(form.locator(`[name="${name}"]`)).toHaveValue(params.get(name)!);
    }
  };
  const expectNextPage = async () => {
    await expect(page).toHaveURL(nextUrl.href);
    await expect(page.getByRole("alert").filter({ hasText: "This search link is invalid or out of date." })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Restart this search" })).toHaveCount(0);
    await expect(nextHit).toBeVisible();
    await expect(section.locator("article.card")).toHaveCount(1);
    await expect(firstHit).toHaveCount(0);
    await expect(more).toHaveCount(0);
    await expect(page.getByRole("status").filter({ hasText: "public matches" })).toHaveText("2 public matches");
    await expectFilters("statement");
  };

  await expectFilters("");
  await more.click();
  await expectNextPage();
  const nextResponse = await page.request.get(`/api/search${nextUrl.search}`);
  expect(nextResponse.ok()).toBe(true);
  const nextResult = await nextResponse.json() as SearchResponse;
  expect(nextResult.query.normalized).toBe("ada quill");
  expect(nextResult.groups.statement.data.map((hit) => hit.slug)).toEqual(["ada-extinction-2023"]);
  expect(nextResult.groups.statement.page).toEqual({ limit: 1, total: 2, next_cursor: null });

  await page.goBack();
  await expect(page).toHaveURL(firstUrl);
  await expect(firstHit).toBeVisible();
  await expect(nextHit).toHaveCount(0);
  await expect(more).toHaveAttribute("href", href!);
  await expectFilters("");
  await page.goForward();
  await expectNextPage();
  await page.goBack();
  await expect(firstHit).toBeVisible();
  await more.click();
  await expectNextPage();
});
