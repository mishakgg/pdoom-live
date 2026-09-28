import { readinessReport } from "@pdoom/db";

let cache: { expires: number; ready: boolean } | null = null;

export function clearReadinessCache(): void {
  cache = null;
}

export async function applicationReady(): Promise<boolean> {
  const now = Date.now();
  if (cache && cache.expires > now) return cache.ready;
  const report = await readinessReport();
  const ready = report.status === "ready";
  cache = { expires: now + (ready ? 2_000 : 400), ready };
  return ready;
}
