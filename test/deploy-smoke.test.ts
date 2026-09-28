import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(new URL("../scripts/deploy-smoke.sh", import.meta.url), "utf8");

describe("deployment smoke script", () => {
  it("is valid bash and only reads the running site", () => {
    execFileSync("bash", ["-n", "scripts/deploy-smoke.sh"], { stdio: "pipe" });
    expect(source).toContain("/api/live");
    expect(source).toContain("/api/ready");
    expect(source).toContain("/api/health");
    expect(source).toContain("content-security-policy");
    expect(source).toContain("x-content-type-options");
    expect(source).toContain("referrer-policy");
    expect(source).toContain("x-frame-options");
    expect(source).toContain("permissions-policy");
    expect(source).toContain("Live dataset");
    expect(source).not.toMatch(/\b(migrate|import|seed|reset|pg_dump|pg_restore)\b/);
    expect(source).not.toContain("docker compose");
    expect(source).not.toMatch(/\b(POST|PUT|PATCH|DELETE)\b/);
  });
});
