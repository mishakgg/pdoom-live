import { expect, it } from "vitest";
import { evidenceSpan } from "./presentation";

it.each([
  [1860000, 1885000, "31:00–31:25 (1860000–1885000 ms) · Transcript"],
  [0, 1500, "0:00–0:01.5 (0–1500 ms) · Transcript"],
  [3723001, 3723990, "1:02:03.001–1:02:03.99 (3723001–3723990 ms) · Transcript"],
  [null, 1000, "unknown–0:01 (unknown–1000 ms) · Transcript"],
])("makes media offsets %s–%s readable while retaining the exact stored milliseconds", (start_ms, end_ms, expected) => {
  expect(evidenceSpan({ start_ms, end_ms, start_char: null, end_char: null, segment_kind: "transcript" })).toBe(expected);
});

it("keeps character offsets and absent locators distinct from media timestamps", () => {
  expect(evidenceSpan({ start_ms: null, end_ms: null, start_char: 0, end_char: 12, segment_kind: "text" })).toBe("characters 0–12 · Text");
  expect(evidenceSpan({ start_ms: null, end_ms: null, start_char: null, end_char: null, segment_kind: "text" })).toBe("Span not recorded · Text");
});
