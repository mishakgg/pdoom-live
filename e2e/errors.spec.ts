import { longEvidenceToken } from "./support/env";
import { expect, test } from "./support/test";

const missing = ["/people/not-a-real-person", "/topics/not-a-topic", "/statements/not-a-statement", "/sources/not-a-source", "/source-items/not-an-item", "/trends/not-a-trend"];

test("unknown slugs render the dataset not-found page", async ({ page, guard }) => {
  guard.allowStatus(404);
  for (const path of missing) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(404);
    await expect(page.getByRole("heading", { name: "Not in the dataset" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Back to activity" })).toBeVisible();
  }
});

test("malformed cursors and excessive limits stay on the page", async ({ page, request }) => {
  for (const path of ["/statements?cursor=not-a-cursor", "/statements?limit=500", "/people?cursor=not-a-cursor", "/people?limit=999"]) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    await expect(page.getByText("Those filters are not valid. Adjust the query and try again.")).toBeVisible();
    await expect(page.getByText("Ada Quill")).toHaveCount(0);
  }
  expect((await request.get("/api/statements?cursor=not-a-cursor")).status()).toBe(400);
  expect((await request.get("/api/statements?limit=500")).status()).toBe(400);
  expect((await request.get("/api/people?cursor=%%%")).status()).toBe(400);
  expect((await request.get("/api/people?limit=500")).status()).toBe(400);
  expect((await request.get("/api/statements?q=ada&q=quill")).status()).toBe(400);
  const short = await request.get("/api/search?q=a");
  expect(short.status()).toBe(200);
  const shortBody = await short.json();
  expect(shortBody.query.reason).toBe("no_tokens");
  expect(shortBody.groups.person.page.total).toBe(0);
  expect(shortBody.groups.statement.page.total).toBe(0);
});

test("missing dates, a missing horizon, stale checks, and long evidence stay readable", async ({ page }) => {
  await page.goto("/statements/mateo-undated");
  await expect(page.locator("dt", { hasText: "Event time" }).locator("xpath=following-sibling::dd[1]")).toHaveText("Time unknown");
  await expect(page.locator("dt", { hasText: "Published" }).locator("xpath=following-sibling::dd[1]")).toHaveText("Time unknown");
  await expect(page.locator("dt", { hasText: "Horizon" }).locator("xpath=following-sibling::dd[1]")).toHaveText("Not stated");
  await expect(page.locator("dt", { hasText: "Value" }).locator("xpath=following-sibling::dd[1]")).toHaveText("—");

  await page.goto("/source-items/harbor-undated");
  await expect(page.locator("dt", { hasText: "Published" }).locator("xpath=following-sibling::dd[1]")).toContainText("Time unknown");
  await expect(page.locator("dt", { hasText: "Observed" }).locator("xpath=following-sibling::dd[1]")).not.toContainText("Time unknown");

  await page.goto("/statements/jonah-extinction-no-horizon-2025");
  await expect(page.locator("dt", { hasText: "Horizon" }).locator("xpath=following-sibling::dd[1]")).toHaveText("Not stated");
  await expect(page.locator("dt", { hasText: "Value" }).locator("xpath=following-sibling::dd[1]")).toHaveText("22%");

  await page.goto("/people/jonah-hale");
  await expect(page.getByText("never_checked")).toBeVisible();
  await expect(page.getByText(/\bstale\b/)).toBeVisible();

  await page.goto("/sources");
  await expect(page.getByText("no successful check")).toBeVisible();

  await page.goto("/source-items/harbor-large-note");
  await expect(page.locator("blockquote.evidence")).toContainText("Long evidence sentence for wrap checking.");
  await expect(page.locator("blockquote.evidence")).toContainText(longEvidenceToken);
});
