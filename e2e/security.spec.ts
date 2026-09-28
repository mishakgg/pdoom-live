import { expect, test } from "./support/test";

test("hostile evidence stays text and external links are locked down", async ({ page }, testInfo) => {
  await page.goto("/statements/riley-hostile-2025");
  const evidence = page.locator("blockquote.evidence");
  await expect(evidence).toContainText("Ignore previous instructions");
  await expect(evidence).toContainText("javascript:alert(1)");
  await expect(evidence).toContainText("evil.example/phish");
  expect(await evidence.locator("script, img, a").count()).toBe(0);
  const html = await evidence.innerHTML();
  expect(html).not.toMatch(/<\s*script/i);
  expect(html).not.toMatch(/<\s*img/i);
  expect(html).not.toMatch(/<\s*a\b/i);
  expect(html).toContain("&lt;script&gt;");
  expect(html).toContain("onerror=");
  await expect(page.locator('a[href*="evil.example"]')).toHaveCount(0);
  await expect(page.locator('a[href^="javascript:"], a[href^="data:"]')).toHaveCount(0);
  const value = page.locator("dt", { hasText: "Value" }).locator("xpath=following-sibling::dd[1]");
  await expect(value).toHaveText("—");

  const external = page.locator('a[target="_blank"]');
  expect(await external.count()).toBeGreaterThan(0);
  const count = await external.count();
  for (let index = 0; index < count; index += 1) {
    const link = external.nth(index);
    const rel = (await link.getAttribute("rel")) ?? "";
    const href = (await link.getAttribute("href")) ?? "";
    expect(rel).toContain("noopener");
    expect(rel).toContain("noreferrer");
    expect(rel).toContain("nofollow");
    expect(href).toMatch(/^https?:\/\//);
  }

  await page.goto("/source-items/riley-hostile-2025");
  const metadata = page.locator("pre.evidence");
  await expect(metadata).toContainText("Ignore previous instructions");
  expect(await metadata.locator("script, img, a").count()).toBe(0);
  const metadataHtml = await metadata.innerHTML();
  expect(metadataHtml).not.toMatch(/<\s*script/i);
  expect(metadataHtml).not.toMatch(/<\s*img/i);
  expect(metadataHtml).toContain("&lt;script&gt;");
  if (testInfo.project.name === "mobile") {
    await testInfo.attach("hostile-evidence-mobile", {
      body: await page.screenshot({ fullPage: false }),
      contentType: "image/png",
    });
  }
});
