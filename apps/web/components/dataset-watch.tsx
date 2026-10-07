"use client";

import { createRequestGate } from "@pdoom/contracts/browser";
import { useEffect, useRef, useState } from "react";
import { fingerprintFromOverview } from "@/lib/presentation";

export const DATASET_WATCH_INITIAL_MS = 90_000;
export const DATASET_WATCH_MAX_MS = 5 * 60_000;

/**
 * Rechecks the stored overview while the tab is visible.
 * A change offers a reload. The reload reads the database and does not collect sources.
 */
export function DatasetWatch({ fingerprint }: { fingerprint: string }) {
  const fingerprintRef = useRef(fingerprint);
  const [notice, setNotice] = useState<"available" | "check_failed" | null>(null);

  useEffect(() => {
    fingerprintRef.current = fingerprint;
  }, [fingerprint]);

  useEffect(() => {
    const gate = createRequestGate();
    let timer = 0;
    let delay = DATASET_WATCH_INITIAL_MS;
    let controller: AbortController | null = null;
    let stopped = false;

    const clearTimer = () => window.clearTimeout(timer);

    const schedule = () => {
      clearTimer();
      if (stopped || document.visibilityState !== "visible") return;
      timer = window.setTimeout(() => {
        void tick();
      }, delay);
    };

    const tick = async () => {
      if (stopped || document.visibilityState !== "visible") return;
      controller?.abort();
      const current = new AbortController();
      controller = current;
      const requestId = gate.next();
      try {
        const response = await fetch("/api/overview", { signal: current.signal, cache: "no-store" });
        if (!gate.shouldApply(requestId)) return;
        if (!response.ok) {
          setNotice((currentNotice) => (currentNotice === "available" ? currentNotice : "check_failed"));
          delay = Math.min(delay * 2, DATASET_WATCH_MAX_MS);
          schedule();
          return;
        }
        const body: unknown = await response.json();
        if (!gate.shouldApply(requestId)) return;
        const next = fingerprintFromOverview(body);
        if (next && next !== fingerprintRef.current) setNotice("available");
        delay = Math.min(delay * 2, DATASET_WATCH_MAX_MS);
        schedule();
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (!gate.shouldApply(requestId)) return;
        setNotice((currentNotice) => (currentNotice === "available" ? currentNotice : "check_failed"));
        delay = Math.min(delay * 2, DATASET_WATCH_MAX_MS);
        schedule();
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") schedule();
      else {
        clearTimer();
        controller?.abort();
      }
    };

    document.addEventListener("visibilitychange", onVisibility);
    schedule();
    return () => {
      stopped = true;
      clearTimer();
      controller?.abort();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  if (!notice) return null;
  if (notice === "available") {
    return (
      <div className="watch-banner" role="status">
        <p>New stored data is available. The list you are reading has not been changed.</p>
        <button type="button" onClick={() => window.location.reload()}>Show stored data</button>
        <p>Reload reads the database again. It does not collect sources.</p>
      </div>
    );
  }
  return (
    <div className="watch-banner" role="status">
      <p>The stored dataset could not be rechecked. This page still shows the last loaded copy. Sources were not collected.</p>
    </div>
  );
}
