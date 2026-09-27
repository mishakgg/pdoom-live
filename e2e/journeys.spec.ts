import { expect, test } from "./support/test";

test("home shows the fixture cohort and a sourced trend", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Who said what, under which definition." })).toBeVisible();
  await expect(page.locator("main").getByText("Synthetic fixture", { exact: true })).toBeVisible();
  await expect(page.getByText("synthetic-frontier-v1")).toBeVisible();
  await expect(page.getByText("Synthetic frontier cohort v1")).toBeVisible();
  await expect(page.getByText("8 tracked people")).toBeVisible();
  await expect(page.getByRole("link", { name: /Ada Quill updated her unconditional extinction probability/ })).toBeVisible();
  await expect(page.getByText("10.5%")).toBeVisible();
  await expect(page.getByText("not a field consensus")).toBeVisible();
  await expect(page.getByText("4 people, 4 statements")).toBeVisible();
  if (testInfo.project.name === "desktop") {
    await testInfo.attach("home-desktop", {
      body: await page.screenshot({ fullPage: false }),
      contentType: "image/png",
    });
  }
});

test("primary navigation reaches the people list", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "People" }).click();
  await expect(page).toHaveURL(/\/people$/);
  await expect(page.getByRole("heading", { level: 1, name: "Tracked people" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ada Quill" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Samir Okonkwo" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Samira Okonkwo" })).toBeVisible();
  await expect(page.getByText("9 people")).toBeVisible();
  await expect(page.getByText("Similar names are not merged.")).toBeVisible();
});

test("person detail shows inclusion, affiliation, and a numeric statement", async ({ page }) => {
  await page.goto("/people/ada-quill");
  await expect(page.getByRole("heading", { level: 1, name: "Ada Quill" })).toBeVisible();
  await expect(page.locator("p.lede")).toHaveText("Fictional research lead used to show an explicit numeric revision.");
  await expect(page.getByText("Northwind Alignment Lab")).toBeVisible();
  await expect(page.getByRole("link", { name: /updated her unconditional extinction probability by the end of 2070 to 12%/ })).toBeVisible();
});

test("topic detail keeps the extinction definition and links the distribution", async ({ page }) => {
  await page.goto("/topics/ai-extinction");
  await expect(page.getByRole("heading", { level: 1, name: "Human extinction from AI" })).toBeVisible();
  await expect(page.locator("p.lede")).toContainText(/literal human extinction/i);
  await expect(page.getByRole("link", { name: "Open the 2070 extinction distribution" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Priya Sen stated an 18%/ })).toBeVisible();
});

test("statement detail shows the audit record and evidence", async ({ page }) => {
  await page.goto("/statements/ada-extinction-2025");
  await expect(page.getByRole("heading", { level: 1, name: "Ada Quill" })).toBeVisible();
  await expect(page.getByText("Explicit numerical estimate")).toBeVisible();
  await expect(page.getByText("human verified")).toBeVisible();
  await expect(page.getByText("12%", { exact: true })).toBeVisible();
  await expect(page.getByText("by end of 2070")).toBeVisible();
  await expect(page.locator("blockquote.evidence")).toContainText("12 percent");
  await expect(page.getByRole("link", { name: "https://synthetic.pdoom.example/items/ada-podcast-2025" })).toBeVisible();
  await expect(page.getByText(/^[a-f0-9]{64}$/).first()).toBeVisible();
});

test("source and source item show publication separate from observation", async ({ page }) => {
  await page.goto("/sources/ada-blog");
  await expect(page.getByRole("heading", { level: 1, name: "Ada Quill notes" })).toBeVisible();
  await page.getByRole("link", { name: "A fictional note on extinction risk" }).click();
  await expect(page).toHaveURL(/\/source-items\/ada-essay-2023$/);
  await expect(page.getByRole("heading", { level: 1, name: "A fictional note on extinction risk" })).toBeVisible();
  await expect(page.getByText("Published")).toBeVisible();
  await expect(page.getByText("Observed")).toBeVisible();
  await expect(page.getByRole("link", { name: "Ada Quill", exact: true })).toBeVisible();
  await expect(page.locator("blockquote.evidence")).toContainText("8 percent");
});

test("trends name the method, sample, and median", async ({ page }) => {
  await page.goto("/trends");
  await expect(page.getByRole("heading", { level: 1, name: "Trends" })).toBeVisible();
  await expect(page.getByText("explicit-numeric-distribution/1.0.0")).toBeVisible();
  await expect(page.getByText("count-by-topic-type/1.0.0")).toBeVisible();
  await expect(page.getByText("4 people, 4 statements")).toBeVisible();
  await expect(page.getByText("10.5%")).toBeVisible();
  await expect(page.getByText("not a field consensus")).toBeVisible();
  await page.getByRole("link", { name: "Unconditional human-extinction probability by 2070" }).click();
  await expect(page).toHaveURL(/\/trends\/extinction-by-2070-distribution$/);
  await expect(page.getByRole("heading", { level: 1, name: "Unconditional human-extinction probability by 2070" })).toBeVisible();
  await expect(page.getByRole("link", { name: "12%" })).toBeVisible();
});

test("methodology states the class boundaries", async ({ page }) => {
  await page.goto("/methodology");
  await expect(page.getByRole("heading", { level: 1, name: "Methodology" })).toBeVisible();
  await expect(page.getByText(/The person supplied a number, range, or distribution/)).toBeVisible();
  await expect(page.getByText(/does not invent a probability/)).toBeVisible();
  await expect(page.getByText(/not a consensus/)).toBeVisible();
  await expect(page.getByText("Samir Okonkwo and Samira Okonkwo remain different people.")).toBeVisible();
});

test("header search opens a person and the statement filter finds a claim", async ({ page }) => {
  await page.goto("/topics");
  const search = page.getByRole("search");
  await search.getByRole("textbox", { name: "Search statements" }).fill("Samira");
  await search.getByRole("link", { name: "Samira Okonkwo", exact: true }).click();
  await expect(page).toHaveURL(/\/people\/samira-okonkwo$/);
  await expect(page.getByRole("heading", { level: 1, name: "Samira Okonkwo" })).toBeVisible();
  await expect(page.locator("p.lede")).toContainText(/labor economist/i);

  await page.goto("/statements");
  await page.getByRole("textbox", { name: "Text" }).fill("disempowerment");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByRole("link", { name: /permanent disempowerment/ })).toBeVisible();
  await expect(page.getByText(/\d+ matching statements/)).toBeVisible();
});
