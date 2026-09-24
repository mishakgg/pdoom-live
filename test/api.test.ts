import { GET as listStatements } from "../apps/web/app/api/statements/route";
import { GET as getStatement } from "../apps/web/app/api/statements/[slug]/route";
import { describe, expect, it } from "vitest";

describe("statement API", () => {
  it("rejects invalid filters and cursors", async () => {
    const badLimit = await listStatements(new Request("http://localhost/api/statements?limit=500"));
    expect(badLimit.status).toBe(400);
    const badCursor = await listStatements(new Request("http://localhost/api/statements?cursor=not-a-cursor"));
    expect(badCursor.status).toBe(400);
    const badType = await listStatements(new Request("http://localhost/api/statements?statement_type=sentiment"));
    expect(badType.status).toBe(400);
  });

  it("omits evidence bodies from list payloads and returns them on detail", async () => {
    const response = await listStatements(new Request("http://localhost/api/statements?person=riley-moss"));
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(JSON.stringify(body)).not.toContain("<script>");
    expect(JSON.stringify(body)).not.toContain("content_hash_input");
    const detail = await getStatement(new Request("http://localhost/api/statements/riley-hostile-2025"), {
      params: Promise.resolve({ slug: "riley-hostile-2025" }),
    });
    const detailBody = await detail.json();
    expect(detailBody.evidence.text).toContain("Ignore previous instructions");
  });
});
