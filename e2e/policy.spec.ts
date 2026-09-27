import { rejectedMarker, rejectedSlug, unreviewedMarker, unreviewedSlug } from "./support/env";
import { expect, test } from "./support/test";

test("rejected and unreviewed statements cannot be opened", async ({ page, request, guard }) => {
  guard.allowStatus(404);
  for (const [slug, marker] of [
    [rejectedSlug, rejectedMarker],
    [unreviewedSlug, unreviewedMarker],
  ] as const) {
    const response = await page.goto(`/statements/${slug}`);
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "Not in the dataset" })).toBeVisible();
    await expect(page.getByText(marker)).toHaveCount(0);
    const api = await request.get(`/api/statements/${slug}`);
    expect(api.status()).toBe(404);
  }
});

test("private markers stay out of home, search, and the person timeline", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.getByText(unreviewedMarker)).toHaveCount(0);
  await expect(page.getByText(rejectedMarker)).toHaveCount(0);

  const searchResponse = page.waitForResponse((response) => response.url().includes("/api/search?q=zeta"));
  await page.getByRole("textbox", { name: "Search statements" }).fill("zeta");
  expect((await searchResponse).status()).toBe(200);
  await expect(page.getByText(unreviewedMarker)).toHaveCount(0);
  await expect(page.getByText(rejectedMarker)).toHaveCount(0);
  const search = await request.get("/api/search?q=zeta");
  const body = (await search.json()) as { statements: unknown[]; people: unknown[] };
  expect(body.statements).toEqual([]);

  await page.goto("/people/riley-moss");
  await expect(page.getByRole("heading", { level: 1, name: "Riley Moss" })).toBeVisible();
  await expect(page.getByText(unreviewedMarker)).toHaveCount(0);
  await expect(page.getByText(rejectedMarker)).toHaveCount(0);
  await expect(page.getByText(/wording is stored only as untrusted evidence/)).toBeVisible();
});

test("review filters do not publish rejected or unreviewed rows", async ({ page }) => {
  await page.goto("/statements?review_state=rejected");
  await expect(page.getByText("0 matching statements")).toBeVisible();
  await expect(page.getByText(rejectedMarker)).toHaveCount(0);
  await page.goto("/statements?review_state=unreviewed");
  await expect(page.getByText("0 matching statements")).toBeVisible();
  await expect(page.getByText(unreviewedMarker)).toHaveCount(0);
});

test("needs review stays visible and is not labeled verified", async ({ page }) => {
  await page.goto("/statements/jonah-extinction-review-2024");
  await expect(page.getByRole("heading", { level: 1, name: "Jonah Hale" })).toBeVisible();
  await expect(page.getByText("needs review", { exact: true })).toBeVisible();
  await expect(page.getByText("human verified")).toHaveCount(0);
  await expect(page.getByText("30%", { exact: true })).toBeVisible();
  await page.goto("/trends/extinction-by-2070-distribution");
  const included = page.locator("table.dist");
  await expect(included.getByRole("link", { name: "30%" })).toHaveCount(0);
  await expect(included.getByRole("link", { name: "12%" })).toBeVisible();
  await page.locator("summary", { hasText: "excluded records" }).click();
  await expect(page.getByRole("link", { name: "jonah-extinction-review-2024" })).toBeVisible();
});

test("machine-validated output is labeled and human-verified estimates stay explicit", async ({ page }) => {
  await page.goto("/statements/ada-inferred-2024");
  await expect(page.getByText("Model-inferred signal", { exact: true })).toBeVisible();
  await expect(page.getByText("machine validated", { exact: true })).toBeVisible();
  await expect(page.getByText("This is a model-inferred signal. It is not a quotation and it is not this person’s probability.")).toBeVisible();
  await expect(page.getByText("human verified")).toHaveCount(0);
  const inferredValue = page.locator("dt", { hasText: "Value" }).locator("xpath=following-sibling::dd[1]");
  await expect(inferredValue).toHaveText("—");

  await page.goto("/statements/ada-extinction-2025");
  await expect(page.getByText("Explicit numerical estimate")).toBeVisible();
  await expect(page.getByText("human verified", { exact: true })).toBeVisible();
  await expect(page.locator("dt", { hasText: "Value" }).locator("xpath=following-sibling::dd[1]")).toHaveText("12%");
});

test("a qualitative statement does not display an invented probability", async ({ page }) => {
  await page.goto("/statements/ada-misuse-2024");
  await expect(page.getByText("Explicit qualitative view", { exact: true })).toBeVisible();
  await expect(page.getByText("Explicit qualitative view. No probability has been inferred from the wording.")).toBeVisible();
  await expect(page.locator("dt", { hasText: "Value" }).locator("xpath=following-sibling::dd[1]")).toHaveText("No numeric value");
  await expect(page.locator("body")).not.toContainText(/%/);
});
