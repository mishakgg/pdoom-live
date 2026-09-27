import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import { budgets } from "./budgets";

/**
 * Documented network exceptions:
 * - net::ERR_ABORTED: Chromium cancels a prefetch when the next navigation starts.
 * - Statuses passed to allowStatus(): intentional 404s and the database-down 500/503.
 * Everything else on a journey, including external hosts, fails the test.
 */
export class PageGuard {
  readonly pageErrors: string[] = [];
  readonly consoleErrors: string[] = [];
  readonly networkProblems: string[] = [];
  readonly apiCounts = new Map<string, number>();
  private readonly allowedStatuses = new Set<number>();

  allowStatus(status: number): void {
    this.allowedStatuses.add(status);
  }

  assertClean(): void {
    expect(this.pageErrors, `uncaught browser exceptions:\n${this.pageErrors.join("\n")}`).toEqual([]);
    const consoleErrors = this.consoleErrors.filter((message) => !this.consoleErrorAllowed(message));
    expect(consoleErrors, `console errors:\n${consoleErrors.join("\n")}`).toEqual([]);
    const networkProblems = this.networkProblems.filter((problem) => !this.networkProblemAllowed(problem));
    expect(networkProblems, `failed or external requests:\n${networkProblems.join("\n")}`).toEqual([]);
    for (const [key, count] of this.apiCounts) {
      expect(count, `repeated API request ${key}`).toBeLessThanOrEqual(budgets.maxIdenticalApiRequests);
    }
  }

  private consoleErrorAllowed(message: string): boolean {
    if (!/failed to load resource/i.test(message)) return false;
    return [...this.allowedStatuses].some((status) => message.includes(String(status)));
  }

  private networkProblemAllowed(problem: string): boolean {
    const match = /^(\d{3})\s/.exec(problem);
    if (!match) return false;
    return this.allowedStatuses.has(Number(match[1]));
  }
}

function isLocal(url: URL): boolean {
  if (url.protocol === "data:" || url.protocol === "blob:" || url.protocol === "about:") return true;
  return url.hostname === "127.0.0.1" || url.hostname === "localhost";
}

export async function attachGuard(page: Page, guard: PageGuard): Promise<void> {
  page.on("pageerror", (error) => {
    guard.pageErrors.push(`${error.name}: ${error.message}`);
  });
  page.on("console", (message) => {
    if (message.type() === "error") guard.consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => {
    const text = request.failure()?.errorText ?? "request failed";
    if (text.includes("ERR_ABORTED")) return;
    guard.networkProblems.push(`${text} ${request.url()}`);
  });
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (response.status() >= 400) {
      guard.networkProblems.push(`${response.status()} ${url.pathname}${url.search}`);
    }
    if (url.pathname.startsWith("/api/")) {
      const key = `${url.pathname}${url.search}`;
      guard.apiCounts.set(key, (guard.apiCounts.get(key) ?? 0) + 1);
    }
  });
  page.on("dialog", (dialog) => {
    guard.networkProblems.push(`dialog ${dialog.type()} ${dialog.message()}`);
    void dialog.dismiss();
  });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (!isLocal(url)) {
      guard.networkProblems.push(`external ${url.hostname}${url.pathname}`);
      await route.abort("blockedbyclient");
      return;
    }
    await route.continue();
  });
}

export async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

export async function expectNavUsable(page: Page): Promise<void> {
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("viewport is not set");
  const links = page.getByRole("navigation", { name: "Primary" }).getByRole("link");
  const count = await links.count();
  expect(count).toBeGreaterThanOrEqual(7);
  for (let index = 0; index < count; index += 1) {
    const box = await links.nth(index).boundingBox();
    expect(box, `nav link ${index} has no box`).not.toBeNull();
    if (!box) continue;
    expect(box.width).toBeGreaterThan(8);
    expect(box.height).toBeGreaterThan(8);
    expect(box.x).toBeGreaterThanOrEqual(-1);
    expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1);
  }
  const search = page.getByRole("textbox", { name: "Search statements" });
  await expect(search).toBeVisible();
  const searchBox = await search.boundingBox();
  expect(searchBox).not.toBeNull();
  if (searchBox) {
    expect(searchBox.x).toBeGreaterThanOrEqual(-1);
    expect(searchBox.x + searchBox.width).toBeLessThanOrEqual(viewport.width + 1);
  }
}

export async function expectEvidenceReadable(page: Page): Promise<void> {
  const block = page.locator("blockquote.evidence").first();
  await expect(block).toBeVisible();
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("viewport is not set");
  const box = await block.boundingBox();
  expect(box).not.toBeNull();
  if (!box) return;
  expect(box.height).toBeGreaterThan(8);
  expect(box.x).toBeGreaterThanOrEqual(-1);
  expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1);
  const overflow = await block.evaluate((element) => element.scrollWidth - element.clientWidth);
  expect(overflow).toBeLessThanOrEqual(2);
}

export async function expectTrendUsable(page: Page): Promise<void> {
  const table = page.locator("table.dist").first();
  await expect(table).toBeVisible();
  const box = await table.boundingBox();
  expect(box).not.toBeNull();
  if (!box) return;
  expect(box.height).toBeGreaterThan(40);
  expect(box.width).toBeGreaterThan(80);
  await expect(page.locator(".volume, table.dist").first()).toBeVisible();
}

export async function expectNoSeriousAxeViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((violation) => violation.impact === "serious" || violation.impact === "critical");
  const summary = blocking
    .map((violation) => {
      const nodes = violation.nodes
        .slice(0, 3)
        .map((node) => node.target.join(" "))
        .join("; ");
      return `${violation.id} (${violation.impact}): ${violation.help} [${nodes}]`;
    })
    .join("\n");
  expect(blocking, summary).toEqual([]);
}
