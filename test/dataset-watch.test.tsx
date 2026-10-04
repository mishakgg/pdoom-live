/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DATASET_WATCH_INITIAL_MS, DatasetWatch } from "../apps/web/components/dataset-watch";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
});

describe("stored dataset watch", () => {
  it("waits, backs off, and does not reload until asked", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      dataset: { imported_at: "2026-02-01T00:00:00.000Z", statement_count: 9, coverage: {} },
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const reload = vi.fn();
    Object.defineProperty(window, "location", { configurable: true, value: { reload } });
    render(<DatasetWatch fingerprint="2026-01-01T00:00:00.000Z|4|||||" />);
    await vi.advanceTimersByTimeAsync(DATASET_WATCH_INITIAL_MS - 1);
    expect(fetchMock).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    await vi.waitFor(() => expect(screen.getByRole("status").textContent).toMatch(/New stored data is available/));
    expect(reload).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(DATASET_WATCH_INITIAL_MS);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(DATASET_WATCH_INITIAL_MS);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("pauses while the tab is hidden and ignores an aborted response", async () => {
    vi.useFakeTimers();
    let rejectAbort: ((error: Error) => void) | undefined;
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      rejectAbort = reject;
      init?.signal?.addEventListener("abort", () => {
        const error = new DOMException("aborted", "AbortError");
        reject(error);
      });
    }));
    vi.stubGlobal("fetch", fetchMock);
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    render(<DatasetWatch fingerprint="same" />);
    await vi.advanceTimersByTimeAsync(DATASET_WATCH_INITIAL_MS);
    expect(fetchMock).not.toHaveBeenCalled();
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    document.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(DATASET_WATCH_INITIAL_MS);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    document.dispatchEvent(new Event("visibilitychange"));
    rejectAbort?.(new DOMException("aborted", "AbortError"));
    await vi.waitFor(() => expect(screen.queryByRole("status")).toBeNull());
  });
});
