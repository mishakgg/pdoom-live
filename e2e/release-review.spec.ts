import type { Page, TestInfo } from "@playwright/test";
import { expectNoHorizontalOverflow, expectNoSeriousAxeViolations } from "./support/guard";
import { expect, test } from "./support/test";

async function capture(page: Page, testInfo: TestInfo, name: string) {
  await page.evaluate(async () => { await document.fonts.ready; });
  await testInfo.attach(`${name}-${testInfo.project.name}`, {
    body: await page.screenshot({ fullPage: true }), contentType: "image/png",
  });
}

test("fixture journey identifies fictional records through researcher, statement, and evidence", async ({ page, context }, testInfo) => {
  const notice = page.getByRole("note", { name: "Synthetic dataset notice" });
  await page.goto("/");
  await expect(notice).toContainText("People, organizations, statements, and evidence are fictional.");
  await capture(page, testInfo, "home");
  await page.getByRole("link", { name: "Ada Quill", exact: true }).first().click();
  await expect(page).toHaveURL(/\/people\/ada-quill$/);
  await expect(notice).toBeVisible();
  await capture(page, testInfo, "researcher");
  await page.getByRole("link", { name: /updated her unconditional extinction probability by the end of 2070 to 12%/ }).click();
  await expect(page).toHaveURL(/\/statements\/ada-extinction-2025$/);
  await expect(page.getByRole("heading", { level: 1, name: "Statement by Ada Quill", exact: true })).toBeVisible();
  await expect(notice).toBeVisible();
  const evidence = page.locator("section", { has: page.getByRole("heading", { name: "Original evidence", exact: true }) });
  await expect(evidence.locator("blockquote")).toContainText("12 percent");
  await expect(evidence).toContainText("31:00–31:25 (1860000–1885000 ms)");
  const canonical = "https://synthetic.pdoom.example/items/ada-podcast-2025";
  const original = evidence.getByRole("link", { name: canonical });
  await expect(original).toHaveAttribute("href", canonical);
  await expect(original).toHaveAttribute("target", "_blank");
  await expect(original).toHaveAttribute("rel", /noopener/);
  await capture(page, testInfo, "statement");

  // Fixture originals use a reserved .example host. Verify navigation without
  // pretending a mock response is a real publication or making a network call.
  await context.route(canonical, (route) => route.fulfill({
    contentType: "text/html", body: "<title>Synthetic navigation target</title><p>Fixture URL navigation only.</p>",
  }));
  const opened = context.waitForEvent("page");
  await original.click();
  const popup = await opened;
  await expect(popup).toHaveURL(canonical);
  await popup.close();

  await evidence.getByRole("link", { name: "Fictional podcast appearance" }).click();
  await expect(page).toHaveURL(/\/source-items\/ada-podcast-2025$/);
  await expect(notice).toBeVisible();
  await expect(page.locator("blockquote.evidence")).toContainText("12 percent");
  await expectNoHorizontalOverflow(page);
  await expectNoSeriousAxeViolations(page);
  await capture(page, testInfo, "source-evidence");
});

test("deep-linked statement and search suggestions disclose class and review before navigation", async ({ page }, testInfo) => {
  await page.goto("/statements/ada-inferred-2024");
  await expect(page.getByRole("note", { name: "Synthetic dataset notice" })).toBeVisible();
  await expect(page.getByText("This is a model-inferred signal. It is not a quotation and it is not this person’s probability.")).toBeVisible();
  const search = page.getByRole("search");
  await search.getByRole("combobox").fill("concern");
  const inferred = search.getByRole("option").filter({ hasText: "Model-inferred signal" });
  await expect(inferred).toHaveCount(1);
  await expect(inferred).toContainText("Machine validated");
  await expect(inferred).not.toContainText("Human verified");
  await expectNoHorizontalOverflow(page);
  await capture(page, testInfo, "inferred-search");
});
