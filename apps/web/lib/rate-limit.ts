import { PUBLIC_API_LIMITS } from "@pdoom/contracts";

type Bucket = { count: number; resetAt: number };

export type RateDecision =
  | { ok: true; remaining: number; limit: number }
  | { ok: false; retryAfter: number; limit: number };

function envInt(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

/**
 * Fixed-window limiter for one Node process.
 * Production deployments should also rate-limit at a reverse proxy or CDN.
 * This limiter is only for the public HTTP API. Server-rendered pages call
 * the database helpers directly and do not pass through it.
 */
export function createRateLimiter() {
  const buckets = new Map<string, Bucket>();
  let processBucket: Bucket = { count: 0, resetAt: 0 };

  function take(bucket: Bucket, limit: number, windowMs: number, now: number): { limited: boolean; retryAfter: number; remaining: number } {
    if (now >= bucket.resetAt) {
      bucket.count = 0;
      bucket.resetAt = now + windowMs;
    }
    bucket.count += 1;
    if (bucket.count > limit) {
      return { limited: true, retryAfter: Math.max(1, Math.ceil((bucket.resetAt - now) / 1000)), remaining: 0 };
    }
    return { limited: false, retryAfter: 0, remaining: Math.max(0, limit - bucket.count) };
  }

  return {
    consume(key: string, now = Date.now()): RateDecision {
      const limit = envInt("PDOOM_PUBLIC_RATE_LIMIT", PUBLIC_API_LIMITS.rateLimitPerMinute);
      const windowMs = envInt("PDOOM_PUBLIC_RATE_WINDOW_MS", PUBLIC_API_LIMITS.rateWindowMs);
      const processLimit = envInt("PDOOM_PUBLIC_PROCESS_RATE_LIMIT", PUBLIC_API_LIMITS.processRateLimitPerMinute);
      const processDecision = take(processBucket, processLimit, windowMs, now);
      if (processDecision.limited) return { ok: false, retryAfter: processDecision.retryAfter, limit: processLimit };
      const safeKey = key.slice(0, 80) || "direct";
      const bucket = buckets.get(safeKey) ?? { count: 0, resetAt: 0 };
      buckets.set(safeKey, bucket);
      if (buckets.size > 5000) {
        for (const [entry, value] of buckets) {
          if (now >= value.resetAt) buckets.delete(entry);
        }
      }
      const decision = take(bucket, limit, windowMs, now);
      if (decision.limited) return { ok: false, retryAfter: decision.retryAfter, limit };
      return { ok: true, remaining: decision.remaining, limit };
    },
    reset() {
      buckets.clear();
      processBucket = { count: 0, resetAt: 0 };
    },
  };
}

export const publicApiLimiter = createRateLimiter();

export function publicClientKey(request: Request): string {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim() ?? "";
    if (first.length > 0 && first.length <= 80 && /^[A-Za-z0-9.:]+$/.test(first)) return `xff:${first}`;
  }
  return "direct";
}
