import { PUBLIC_API_LIMITS } from "@pdoom/contracts";

const MAX_CLIENT_KEYS = 1024;

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
      let safeKey = key.slice(0, 80) || "direct";
      if (!buckets.has(safeKey) && buckets.size >= MAX_CLIENT_KEYS) {
        for (const [entry, value] of buckets) {
          if (now >= value.resetAt) buckets.delete(entry);
        }
      }
      if (!buckets.has(safeKey) && buckets.size >= MAX_CLIENT_KEYS) safeKey = "overflow";
      const bucket = buckets.get(safeKey) ?? { count: 0, resetAt: 0 };
      buckets.set(safeKey, bucket);
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

function isIPv4(value: string): boolean {
  const parts = value.split(".");
  if (parts.length !== 4) return false;
  return parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) <= 255);
}

function isIPv6(value: string): boolean {
  return value.length >= 2 && value.length <= 45 && value.includes(":") && /^[0-9A-Fa-f:]+$/.test(value);
}

function trustedProxyHops(): number {
  const raw = process.env.PDOOM_TRUSTED_PROXY_HOPS;
  if (!raw) return 0;
  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed < 0 || parsed > 8) return 0;
  return parsed;
}

/**
 * X-Forwarded-For is a client-supplied header unless the operator says how
 * many reverse proxies append a peer address. Unset means every request
 * shares the `direct` bucket. With N hops, the client is N places from the
 * right: the address the nearest trusted proxy observed, not the leftmost
 * value a caller can spoof.
 */
export function publicClientKey(request: Request): string {
  const hops = trustedProxyHops();
  if (hops <= 0) return "direct";
  const forwarded = request.headers.get("x-forwarded-for");
  if (!forwarded) return "direct";
  const parts = forwarded.split(",").map((part) => part.trim()).filter((part) => part.length > 0);
  if (parts.length < hops) return "direct";
  if (!parts.every((part) => isIPv4(part) || isIPv6(part))) return "direct";
  const client = parts[parts.length - hops];
  if (!client) return "direct";
  return `xff:${client}`;
}

export const publicApiLimiter = createRateLimiter();
