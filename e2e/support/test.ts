import { test as base, expect } from "@playwright/test";
import { attachGuard, PageGuard } from "./guard";

export const test = base.extend<{ guard: PageGuard }>({
  guard: [
    async ({ page }, use) => {
      const guard = new PageGuard();
      await attachGuard(page, guard);
      await use(guard);
      guard.assertClean();
    },
    { auto: true },
  ],
});

export { expect };
