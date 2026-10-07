import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { EXCLUSION_REASONS, exclusionLabel } from "@pdoom/contracts";
import { ExclusionList } from "../apps/web/components/trends";

describe("trend chronology exclusion presentation", () => {
  it("renders the shared reason with its statement audit link", () => {
    const reason = "relationship_time_order";
    expect(EXCLUSION_REASONS).toContain(reason);
    const html = renderToStaticMarkup(createElement(ExclusionList, {
      exclusions: [{ statement_slug: "fixture-statement", display_name: "Ada Example", reason }],
    }));
    expect(html).toContain('href="/statements/fixture-statement"');
    expect(html).toContain(exclusionLabel(reason));
    expect(html).not.toContain("Excluded by this method");
  });
});
