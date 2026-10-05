import { readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import robots from "../apps/web/app/robots";
import { isIndexablePath, renderUrlSet, toSitemapLinks } from "../apps/web/lib/seo";

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../apps/web/app");
const origin = "https://pdoom.live";

function pageRoutes(directory = appDir, segments: string[] = []): string[] {
  const routes: string[] = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.name.startsWith("_") || entry.name.startsWith("@") || entry.name === "node_modules") continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      const next = entry.name.startsWith("(") && entry.name.endsWith(")") ? segments : [...segments, entry.name];
      routes.push(...pageRoutes(full, next));
      continue;
    }
    if (entry.name !== "page.tsx") continue;
    const pathname = `/${segments.join("/")}`;
    routes.push(pathname === "/" ? "/" : pathname);
  }
  return routes.sort();
}

function isCuration(pathname: string): boolean {
  return pathname === "/curation" || pathname.startsWith("/curation/");
}

function samplePath(pathname: string): string {
  return pathname.replace(/\[[^\]]+\]/g, "sample-record");
}

function sitemapPaths(xml: string): string[] {
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => {
    const loc = match[1];
    if (!loc) throw new Error("sitemap loc is empty");
    const pathname = new URL(loc).pathname;
    return pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
  });
}

function disallowRules(): string[] {
  const rules = robots().rules;
  const list = Array.isArray(rules) ? rules : [rules];
  return list.flatMap((rule) => {
    const value = rule.disallow ?? [];
    return typeof value === "string" ? [value] : [...value];
  });
}

function robotsBlocks(pathname: string, rules: readonly string[]): boolean {
  return rules.some((rule) => !rule.includes("*") && pathname.startsWith(rule));
}

describe("public sitemap coverage", () => {
  const routes = pageRoutes();
  const publicStatic = routes.filter((route) => !route.includes("[") && !isCuration(route));
  const publicDynamic = routes.filter((route) => route.includes("[") && !isCuration(route));
  const curationRoutes = routes.filter(isCuration);

  it("includes existing public dataset routes and omits curation", () => {
    expect(publicStatic).toEqual(
      expect.arrayContaining([
        "/",
        "/people",
        "/topics",
        "/statements",
        "/sources",
        "/search",
        "/trends",
        "/data",
        "/methodology",
      ]),
    );
    expect(curationRoutes).toEqual(expect.arrayContaining(["/curation"]));

    const samples = publicDynamic.map((route) => samplePath(route));
    const xml = renderUrlSet(
      toSitemapLinks(
        origin,
        [
          ...samples.map((path) => ({ path, lastModified: null })),
          { path: "/curation", lastModified: null },
          { path: "/curation/sample-record", lastModified: null },
          { path: "/api/v1/dataset", lastModified: null },
          { path: "/admin", lastModified: null },
        ],
        true,
      ),
    );
    const locs = sitemapPaths(xml);
    const sampleSet = new Set(samples);

    for (const route of publicStatic) {
      expect(locs, route).toContain(route);
    }
    for (const route of publicDynamic) {
      const sample = samplePath(route);
      expect(isIndexablePath(sample), sample).toBe(true);
      expect(locs, sample).toContain(sample);
    }
    for (const loc of locs) {
      if (sampleSet.has(loc)) continue;
      expect(publicStatic, loc).toContain(loc);
    }
    expect(xml).not.toContain("/curation");
    const privateLoc = locs.some(
      (route) => route === "/api" || route.startsWith("/api/") || route === "/admin" || route.startsWith("/admin/"),
    );
    expect(privateLoc).toBe(false);
    for (const route of curationRoutes) {
      expect(isIndexablePath(samplePath(route))).toBe(false);
    }
  });

  it("disallows api, curation, and admin paths", () => {
    const rules = disallowRules();
    expect(rules).toEqual(expect.arrayContaining(["/api/", "/curation", "/curation/", "/admin", "/admin/"]));
    for (const pathname of ["/api/", "/api/v1/dataset", "/curation", "/curation/sample-record", "/admin", "/admin/queue"]) {
      expect(robotsBlocks(pathname, rules), pathname).toBe(true);
    }
    for (const route of [...publicStatic, ...publicDynamic.map(samplePath)]) {
      expect(robotsBlocks(route, rules), route).toBe(false);
    }
    for (const route of curationRoutes) {
      expect(robotsBlocks(samplePath(route), rules), route).toBe(true);
    }
  });
});
