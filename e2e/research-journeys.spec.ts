import { expectNoHorizontalOverflow, expectNavUsable } from "./support/guard";
import { expect, test } from "./support/test";

test("name selection stores a stable id and history restores it", async ({ page }) => {
  await page.goto("/statements");
  const person = page.getByRole("combobox", { name: "Person" });
  await person.fill("Okonkwo");
  const samir = page.getByRole("option", { name: /Samir Okonkwo/ });
  const samira = page.getByRole("option", { name: /Samira Okonkwo/ });
  await expect(samir).toBeVisible();
  await expect(samira).toBeVisible();
  await expect(samir).toContainText("Northwind Alignment Lab");
  await expect(samira).toContainText("Lumen Institute");
  await person.fill("Samira");
  await expect(page.getByRole("option", { name: /Samira Okonkwo/ })).toBeVisible();
  await person.press("ArrowDown");
  await person.press("Enter");
  await expect(page.getByText("Samira Okonkwo").first()).toBeVisible();
  await person.press("Enter");
  await expect(page).toHaveURL(/\/statements\?.*person=samira-okonkwo/);
  await expect(page.locator("input[name='person']")).toHaveValue("samira-okonkwo");
  await page.goBack();
  await expect(page).not.toHaveURL(/person=/);
  await page.goForward();
  await expect(page).toHaveURL(/person=samira-okonkwo/);
  await expect(page.getByText("Samira Okonkwo").first()).toBeVisible();
  await page.getByRole("link", { name: "Remove person" }).click();
  await expect(page).not.toHaveURL(/person=/);
});

test("clear all and shared filters survive the paged statement list", async ({ page }) => {
  await page.goto("/statements?person=ada-quill&topic=ai-extinction&from=2020-01-01&statement_type=explicit_numeric&review_state=human_verified");
  await expect(page.getByLabel("From date")).toHaveValue("2020-01-01");
  await expect(page.getByLabel("Type")).toHaveValue("explicit_numeric");
  await expect(page.getByLabel("Review")).toHaveValue("human_verified");
  await expect(page.locator(".entity-selected").filter({ hasText: "Ada Quill" })).toBeVisible();
  await expect(page.locator(".entity-selected").filter({ hasText: "Human extinction from AI" })).toBeVisible();
  const count = page.getByText(/\d+ matching statements/);
  await expect(count).toBeVisible();
  const total = Number((await count.textContent())?.match(/\d+/)?.[0]);
  const seen = new Set<string>();
  for (let guard = 0; guard < 20; guard += 1) {
    const hrefs = await page.locator("article.card h3 a").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    for (const href of hrefs) {
      expect(href).toBeTruthy();
      expect(seen.has(href ?? "")).toBe(false);
      seen.add(href ?? "");
    }
    const next = page.getByRole("link", { name: "Next statements" });
    if (!(await next.count())) break;
    await next.click();
    await expect(page).toHaveURL(/person=ada-quill/);
    await expect(page).toHaveURL(/topic=ai-extinction/);
    await expect(page).toHaveURL(/from=2020-01-01/);
    await expect(page).toHaveURL(/statement_type=explicit_numeric/);
    await expect(page).toHaveURL(/review_state=human_verified/);
  }
  expect(seen.size).toBe(total);
  await page.getByRole("link", { name: "Clear all filters" }).click();
  await expect(page).toHaveURL(/\/statements$/);
});

test("profile and topic navigation keep both constraints and disclose the preview", async ({ page }) => {
  await page.goto("/people/ada-quill");
  await expect(page.getByText(/All \d+ public statements collected for this view are listed here/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Statements" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Forecasts" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Changes" })).toBeVisible();
  const paged = page.getByRole("link", { name: "Open the paged statement list" });
  await expect(paged).toHaveAttribute("href", "/statements?person=ada-quill");
  await page.getByRole("navigation", { name: "On this page" }).getByRole("link", { name: "Statements" }).click();
  await page.locator("#statements").getByRole("link", { name: /Human extinction from AI/ }).first().click();
  await expect(page).toHaveURL(/\/topics\/ai-extinction\?person=ada-quill/);
  await expect(page.getByRole("link", { name: "Open the paged statement list" })).toHaveAttribute(
    "href",
    "/statements?person=ada-quill&topic=ai-extinction",
  );
  await page.locator("article.card").getByRole("link", { name: "Ada Quill", exact: true }).first().click();
  await expect(page).toHaveURL(/\/people\/ada-quill\?topic=ai-extinction/);
  await expect(page.getByText(/before these filters/)).toBeVisible();
});

test("freshness names the separate clocks without claiming a new collection", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Publication time, observation time, last successful collection, and dataset update are different clocks.")).toBeVisible();
  await expect(page.getByText("Reloading this page reads the stored dataset. It does not collect sources again.")).toBeVisible();
  await expect(page.locator("dt", { hasText: "Latest publication" })).toBeVisible();
  await expect(page.locator("dt", { hasText: "Last successful collection" })).toBeVisible();
  await expect(page.locator("dt", { hasText: "Dataset updated" })).toBeVisible();
  await page.goto("/statements/mateo-undated");
  await expect(page.locator("dt", { hasText: "When" }).locator("xpath=following-sibling::dd[1]")).toHaveText("Time unknown");
  await expect(page.getByText("When is the event time.")).toBeVisible();
});

test("mobile masthead drops the row flex basis", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "390×844 project");
  await page.goto("/");
  const mast = await page.locator("header.mast").boundingBox();
  const nav = await page.locator("nav.nav").boundingBox();
  const search = await page.locator("form.search").boundingBox();
  expect(nav?.height ?? 999).toBeLessThan(140);
  expect(search?.height ?? 999).toBeLessThan(160);
  expect(mast?.height ?? 999).toBeLessThan(340);
  await expectNoHorizontalOverflow(page);
  await expectNavUsable(page);
});

test("intermediate width and 200% zoom keep navigation on screen", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "desktop project resizes");
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/people/ada-quill");
  await expect(page.getByRole("heading", { level: 1, name: "Ada Quill" })).toBeVisible();
  const nav = await page.locator("nav.nav").boundingBox();
  expect(nav?.height ?? 999).toBeLessThan(140);
  await expectNoHorizontalOverflow(page);
  await expectNavUsable(page);

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/statements/ada-extinction-2025");
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  await expect(page.getByRole("heading", { level: 1, name: "Ada Quill" })).toBeVisible();
  await expect(page.locator("blockquote.evidence")).toBeVisible();
  await expectNoHorizontalOverflow(page);
  const link = page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "People" });
  const box = await link.boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  const search = page.getByRole("combobox", { name: "Search people, statements, topics, and sources" });
  await search.focus();
  const outline = await search.evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(outline).not.toBe("none");
});
