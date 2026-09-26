export const FRESHNESS_THRESHOLDS = {
  current_days: 14,
  aging_days: 90,
} as const;

export type Freshness = "current" | "aging" | "stale" | "never_checked";

export function classifyFreshness(lastSuccessAt: string | null, asOf: string): Freshness {
  if (!lastSuccessAt) return "never_checked";
  const ageMs = new Date(asOf).getTime() - new Date(lastSuccessAt).getTime();
  const days = ageMs / 86_400_000;
  if (days <= FRESHNESS_THRESHOLDS.current_days) return "current";
  if (days <= FRESHNESS_THRESHOLDS.aging_days) return "aging";
  return "stale";
}
