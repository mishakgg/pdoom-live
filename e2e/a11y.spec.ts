import { expectNoSeriousAxeViolations, expectNavUsable } from "./support/guard";
import { publicRoutes } from "./support/routes";
import { expect, test } from "./support/test";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

for (const route of publicRoutes) {
  test(`axe, headings, and landmarks on ${route.path}`, async ({ page }) => {
    await page.goto(route.path);
    await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("contentinfo")).toBeVisible();
    await expectNavUsable(page);
    await expectNoSeriousAxeViolations(page);
  });
}

test("skip link, focus ring, labels, and keyboard search", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  const skipOutline = await skip.evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(skipOutline).not.toBe("none");

  await page.goto("/statements");
  await expect(page.getByRole("textbox", { name: "Text" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Type" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Review" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Apply" })).toBeVisible();

  const search = page.getByRole("textbox", { name: "Search statements" });
  await search.focus();
  const searchOutline = await search.evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(searchOutline).not.toBe("none");
  await page.keyboard.type("Ada");
  const result = page.getByRole("search").getByRole("link", { name: "Ada Quill", exact: true });
  await expect(result).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(result).toBeFocused();
  const resultOutline = await result.evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(resultOutline).not.toBe("none");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/people\/ada-quill$/);
  await expect(page.getByRole("heading", { level: 1, name: "Ada Quill" })).toBeVisible();
});
