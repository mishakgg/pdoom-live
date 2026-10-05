import { readinessReport, type ReadinessReport } from "@pdoom/db";
import { singleFlight } from "./single-flight";

let cache: { expires: number; ready: boolean } | null = null;

export function clearReadinessCache(): void {
  cache = null;
}

export async function applicationReady(load: () => Promise<ReadinessReport> = readinessReport): Promise<boolean> {
  const now = Date.now();
  if (cache && cache.expires > now) return cache.ready;
  return singleFlight("readiness", async () => {
    const current = Date.now();
    if (cache && cache.expires > current) return cache.ready;
    const report = await load();
    const ready = report.status === "ready";
    cache = { expires: current + (ready ? 2_000 : 400), ready };
    return ready;
  });
}
