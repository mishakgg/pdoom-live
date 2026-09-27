import { expectNoSeriousAxeViolations } from "./support/guard";
import { expect, test } from "./support/test";

test("a refused database keeps the process live and pages closed", async ({ page, request, guard }) => {
  guard.allowStatus(503);
  const live = await request.get("/api/live");
  expect(live.status()).toBe(200);
  expect(await live.json()).toEqual({ status: "live" });

  const health = await request.get("/api/health");
  expect(health.status()).toBe(503);
  expect(await health.json()).toEqual({
    status: "not_ready",
    checks: { process: "live", database: "unavailable", migrations: "unknown" },
  });
  const ready = await request.get("/api/ready");
  expect(ready.status()).toBe(503);
  expect((await ready.json()).status).toBe("not_ready");

  for (const path of ["/", "/methodology", "/people"]) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(503);
    await expect(page.getByText("pdoom.live is not ready.")).toBeVisible();
    await expect(page.getByText("Ada Quill")).toHaveCount(0);
    await expect(page.getByText("Synthetic fixture", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Median of included point estimates")).toHaveCount(0);
  }
  await expectNoSeriousAxeViolations(page);
});
