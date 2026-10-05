/** @vitest-environment jsdom */
import { cleanup, render } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it } from "vitest";
import { PublicApiValidatorCopy } from "../apps/web/components/public-api-validator-copy";

const validatorCopy =
  "Responses send ETag and Cache-Control. Last-Modified is not sent. If-Modified-Since does not change the response. A 304 is returned only when If-None-Match matches the current body.";

afterEach(() => {
  cleanup();
});

describe("public data page validator copy", () => {
  it("describes a body ETag and does not claim Last-Modified comes from import time", () => {
    render(
      <p>
        <PublicApiValidatorCopy />
      </p>,
    );
    const paragraph = document.querySelector("p");
    expect(paragraph?.textContent).toBe(validatorCopy);
    expect(Array.from(paragraph?.querySelectorAll("code") ?? [], (node) => node.textContent)).toEqual([
      "ETag",
      "Cache-Control",
      "Last-Modified",
      "If-Modified-Since",
      "If-None-Match",
    ]);
    const page = readFileSync("apps/web/app/data/page.tsx", "utf8");
    expect(page).toContain("<PublicApiValidatorCopy />");
    expect(page).not.toContain("from the dataset import time");
  });
});
