import { expectEvidenceReadable, expectNavUsable, expectNoHorizontalOverflow, expectTrendUsable } from "./support/guard";
import { publicRoutes } from "./support/routes";
import { expect, test } from "./support/test";

for (const route of publicRoutes) {
  test(`layout stays usable on ${route.path}`, async ({ page }) => {
    await page.goto(route.path);
    await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await expectNavUsable(page);
    if (await page.locator("blockquote.evidence").count()) {
      await expectEvidenceReadable(page);
    }
    if (route.path === "/trends" || route.path.startsWith("/trends/")) {
      await expectTrendUsable(page);
    }
  });
}
