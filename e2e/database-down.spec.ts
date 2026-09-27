import { expectNoSeriousAxeViolations } from "./support/guard";
import { expect, test } from "./support/test";

test("methodology still renders when the database is down", async ({ page }) => {
  const response = await page.goto("/methodology");
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("heading", { level: 1, name: "Methodology" })).toBeVisible();
  await expect(page.getByText("temporarily unavailable")).toHaveCount(0);
});

test("data pages and health report the outage without leaking fixture content", async ({ page, request, guard }) => {
  guard.allowStatus(500);
  guard.allowStatus(503);
  const health = await request.get("/api/health");
  expect(health.status()).toBe(503);
  expect(await health.json()).toEqual({ ok: false });

  const response = await page.goto("/");
  expect(response?.status()).toBe(500);
  await expect(page.getByRole("heading", { name: "This page could not be loaded" })).toBeVisible();
  await expect(page.getByText("The dataset is temporarily unavailable. Nothing on this page is a forecast.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByText("Ada Quill")).toHaveCount(0);
  await expect(page.getByText("Synthetic fixture")).toHaveCount(0);
  await expect(page.getByText("Median of included point estimates")).toHaveCount(0);
  await expectNoSeriousAxeViolations(page);
});
