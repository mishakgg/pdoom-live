import { expect, test } from "./support/test";

test("an empty live dataset does not invent a trend or a probability", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Live dataset")).toBeVisible();
  await expect(page.getByText("e2e-empty-live")).toBeVisible();
  await expect(page.getByText("E2E empty cohort")).toBeVisible();
  await expect(page.getByText("0 public statements")).toBeVisible();
  await expect(page.getByText("E2E empty live dataset. No statements are loaded. This is not a census and it is not a probability.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "No verified trend" })).toBeVisible();
  await expect(page.getByText("Empty coverage is not a probability.")).toBeVisible();
  await expect(page.getByText("Synthetic fixture")).toHaveCount(0);
  await expect(page.getByText("Median of included point estimates")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(/%/);
});

test("the empty cohort still lists its member and an empty topic", async ({ page, request }) => {
  await page.goto("/people");
  await expect(page.getByRole("heading", { level: 1, name: "Tracked people" })).toBeVisible();
  await expect(page.getByRole("link", { name: "E2E Empty Member" })).toBeVisible();
  await expect(page.getByText("1 people")).toBeVisible();
  await page.goto("/statements");
  await expect(page.getByText("0 matching statements")).toBeVisible();
  await page.goto("/topics/e2e-empty-topic");
  await expect(page.getByRole("heading", { level: 1, name: "E2E empty topic" })).toBeVisible();
  await expect(page.getByText("A topic with no statements. It must not become a probability.")).toBeVisible();
  const search = await request.get("/api/search?q=Ada");
  expect(search.status()).toBe(200);
  const body = (await search.json()) as { people: unknown[]; statements: unknown[] };
  expect(body.people).toEqual([]);
  expect(body.statements).toEqual([]);
});
