import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  affiliationFact,
  coverageCopy,
  coverageTone,
  evidenceSpan,
  isNavCurrent,
  sourceMaterialState,
  withCursor,
} from "../apps/web/lib/presentation";

describe("public presentation helpers", () => {
  it("treats a live dataset with no verified statements as unverified, not broken", () => {
    const input = {
      datasetKind: "live",
      cohortSize: 12,
      statementBearingPeople: 4,
      publicStatementCount: 6,
      humanVerifiedStatementCount: 0,
    };
    expect(coverageTone(input)).toBe("unverified");
    const copy = coverageCopy(input);
    expect(copy?.title).toBe("No human-verified statement yet");
    expect(copy?.body).toMatch(/not evidence that tracked people have never spoken/);
  });

  it("describes zero collected statements without implying silence", () => {
    const copy = coverageCopy({
      datasetKind: "live",
      cohortSize: 8,
      statementBearingPeople: 0,
      publicStatementCount: 0,
      humanVerifiedStatementCount: 0,
    });
    expect(copy?.title).toBe("No statement has been collected");
    expect(copy?.body).toMatch(/never spoken/);
    expect(copy?.body).toMatch(/not evidence/);
  });

  it("marks thin coverage only when some statements exist and most people are missing", () => {
    expect(coverageTone({
      datasetKind: "synthetic",
      cohortSize: 10,
      statementBearingPeople: 2,
      publicStatementCount: 3,
      humanVerifiedStatementCount: 3,
    })).toBe("thin");
    expect(coverageTone({
      datasetKind: "synthetic",
      cohortSize: 10,
      statementBearingPeople: 8,
      publicStatementCount: 20,
      humanVerifiedStatementCount: 12,
    })).toBe("reported");
  });

  it("does not present an unverified affiliation as established", () => {
    expect(affiliationFact(null).text).toBe("No current affiliation recorded");
    expect(affiliationFact({ name: "Northwind", role: "Lead", review_state: "needs_review" })).toEqual({
      established: false,
      text: "Not established · Lead · Northwind",
    });
    expect(affiliationFact({ name: "Northwind", role: "Lead", review_state: "human_verified" }).established).toBe(true);
  });

  it("classifies missing source material", () => {
    expect(sourceMaterialState("collected", "available")).toBe("available");
    expect(sourceMaterialState("partial", "available")).toBe("partial");
    expect(sourceMaterialState("unavailable", "available")).toBe("unavailable");
    expect(sourceMaterialState("collected", "removed")).toBe("unavailable");
  });

  it("keeps pagination links free of an empty query", () => {
    expect(withCursor("/statements", { q: "risk", cursor: "old" }, "next")).toBe("/statements?q=risk&cursor=next");
    expect(withCursor("/people", {}, "next")).toBe("/people?cursor=next");
  });

  it("marks nested routes in the primary nav without marking every page as home", () => {
    expect(isNavCurrent("/people/ada-quill", "/people")).toBe(true);
    expect(isNavCurrent("/people/ada-quill", "/")).toBe(false);
    expect(isNavCurrent("/", "/")).toBe(true);
    expect(isNavCurrent("/trends", "/people")).toBe(false);
  });

  it("describes a missing evidence span without inventing one", () => {
    expect(evidenceSpan({
      start_ms: null,
      end_ms: null,
      start_char: null,
      end_char: null,
      segment_kind: "text",
    })).toBe("Span not recorded · Text");
  });

  it("keeps long tokens inside the viewport rules", () => {
    const css = readFileSync("apps/web/app/globals.css", "utf8");
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain(".sr-only");
    expect(css).toContain(".table-scroll");
    expect(css).toContain("max-width: 640px");
    expect(css).toContain("prefers-reduced-motion");
    expect(css).toContain(":focus-visible");
  });
});
