import { build } from "esbuild";
import { describe, expect, it } from "vitest";
import { SEARCH_DEBOUNCE_MS, SEARCH_SUGGEST_MIN, STATEMENT_TYPE_LABELS, createRequestGate } from "@pdoom/contracts/browser";
import { SEARCH_DEBOUNCE_MS as serverDebounce, SEARCH_SUGGEST_MIN as serverMinimum } from "@pdoom/contracts";

describe("browser contract entry", () => {
  it("keeps shared runtime semantics identical to the server entry", () => {
    expect(SEARCH_DEBOUNCE_MS).toBe(serverDebounce);
    expect(SEARCH_SUGGEST_MIN).toBe(serverMinimum);
    expect(STATEMENT_TYPE_LABELS.explicit_numeric).toBe("Explicit numerical estimate");
    const gate = createRequestGate();
    const first = gate.next();
    expect(gate.shouldApply(first)).toBe(true);
    gate.next();
    expect(gate.shouldApply(first)).toBe(false);
  });

  it("bundles without server crypto, schema initialization, or Node polyfills", async () => {
    const result = await build({
      stdin: {
        contents: 'import * as browser from "@pdoom/contracts/browser"; globalThis.pdoomBrowserContracts = browser;',
        resolveDir: process.cwd(),
      },
      bundle: true,
      platform: "browser",
      format: "esm",
      minify: true,
      write: false,
      metafile: true,
      logLevel: "silent",
    });
    const inputs = Object.keys(result.metafile!.inputs).join("\n");
    expect(inputs).not.toMatch(/(?:curation|schemas|search)\.ts|node_modules|crypto/);
    expect(result.outputFiles[0]!.contents.length).toBeLessThan(2_000);
  });
});
