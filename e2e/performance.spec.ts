import type { Response } from "@playwright/test";
import { budgets } from "./support/budgets";
import { performanceRoutes } from "./support/routes";
import { expect, test } from "./support/test";

test.beforeAll(async ({ request }) => {
  for (const route of performanceRoutes) {
    const response = await request.get(route.path);
    expect(response.status(), route.path).toBe(200);
  }
});

test("critical routes stay inside the response and script budgets", async ({ page }, testInfo) => {
  for (const route of performanceRoutes) {
    const scriptCounts = new Map<string, number>();
    const pending: Promise<void>[] = [];
    let scriptBytes = 0;
    const onResponse = (response: Response) => {
      const path = response.url().split("?")[0] ?? "";
      if (!path.includes("/_next/static/") || !path.endsWith(".js")) return;
      scriptCounts.set(path, (scriptCounts.get(path) ?? 0) + 1);
      pending.push(
        response.body().then((body) => {
          scriptBytes += body.length;
        }),
      );
    };
    page.on("response", onResponse);
    const response = await page.goto(route.path, { waitUntil: "load" });
    await Promise.all(pending);
    page.off("response", onResponse);
    const timing = response?.request().timing();
    expect(timing?.responseEnd ?? -1, `${route.path} responseEnd`).toBeGreaterThan(0);
    expect(timing?.responseEnd ?? Number.POSITIVE_INFINITY, `${route.path} responseEnd ${timing?.responseEnd}ms`).toBeLessThan(
      budgets.documentResponseMs,
    );
    expect(scriptBytes, `${route.path} shipped ${scriptBytes} bytes of JavaScript`).toBeLessThan(budgets.maxJavaScriptBytes);
    testInfo.annotations.push({
      type: "perf",
      description: `${route.path} responseEnd=${Math.round(timing?.responseEnd ?? -1)}ms scriptBytes=${scriptBytes}`,
    });
    expect(scriptBytes, `${route.path} shipped no JavaScript`).toBeGreaterThan(10_000);
    for (const [script, count] of scriptCounts) {
      expect(count, `duplicate script ${script} on ${route.path}`).toBeLessThanOrEqual(budgets.maxIdenticalScriptRequests);
    }
    await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();
  }
});

test("search stays within a small request budget", async ({ page }) => {
  await page.goto("/");
  let searchRequests = 0;
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === "/api/search") searchRequests += 1;
  });
  const pending = page.waitForResponse((response) => response.url().includes("/api/search?q=Ada"));
  const started = Date.now();
  await page.getByRole("combobox", { name: "Search people, statements, topics, and sources" }).fill("Ada");
  const response = await pending;
  expect(response.status()).toBe(200);
  expect(Date.now() - started, "search round trip").toBeLessThan(budgets.searchResponseMs);
  await expect(page.getByRole("search").getByRole("option", { name: /Ada Quill/ }).first()).toBeVisible();
  expect(searchRequests).toBeLessThanOrEqual(budgets.maxSearchRequests);
});
