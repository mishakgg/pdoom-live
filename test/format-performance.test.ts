import { afterEach, describe, expect, it, vi } from "vitest";
import { formatDay, formatWhen } from "../apps/web/lib/format";

afterEach(() => vi.restoreAllMocks());

describe("UTC date presentation", () => {
  it("preserves known, unknown, invalid, and offset date output", () => {
    expect(formatWhen(null)).toBe("Time unknown");
    expect(formatWhen(undefined)).toBe("Time unknown");
    expect(formatWhen("")).toBe("Time unknown");
    expect(formatWhen("not a date")).toBe("Time unknown");
    expect(formatWhen("2026-10-07T23:59:00Z")).toBe("07 Oct 2026, 23:59 UTC");
    expect(formatWhen("2025-02-03T01:00:00-05:00")).toBe("03 Feb 2025, 06:00 UTC");
    expect(formatWhen("2025-03-30T23:30:00-04:00")).toBe("31 Mar 2025, 03:30 UTC");
    expect(formatDay("2025-03-30T23:30:00-04:00")).toBe("31 Mar 2025");
    expect(formatDay(null)).toBe("Date unknown");
    expect(formatDay("not a date")).toBe("Time unknown");
  });

  it("constructs its formatter only once, and only for a valid date", async () => {
    vi.resetModules();
    const original = Intl.DateTimeFormat;
    const constructor = vi.spyOn(Intl, "DateTimeFormat").mockImplementation(function (...args) { return new original(...args); });
    const fresh = await import("../apps/web/lib/format");
    fresh.formatWhen(null);
    fresh.formatWhen("invalid");
    expect(constructor).not.toHaveBeenCalled();
    for (let index = 0; index < 100; index += 1) {
      fresh.formatWhen("2026-10-07T23:59:00Z");
      fresh.formatDay("2025-02-03T01:00:00-05:00");
    }
    expect(constructor).toHaveBeenCalledTimes(1);
    expect(constructor).toHaveBeenCalledWith("en-GB", {
      year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "UTC", hourCycle: "h23",
    });
  });
});
