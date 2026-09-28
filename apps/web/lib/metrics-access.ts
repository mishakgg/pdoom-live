import { timingSafeEqual } from "node:crypto";

export function metricsEnabled(): boolean {
  const value = process.env.PDOOM_METRICS_ENABLED;
  return value === "1" || value === "true";
}

export function metricsAuthorized(request: Request): boolean {
  const expected = process.env.PDOOM_METRICS_TOKEN;
  if (!expected) return true;
  const header = request.headers.get("authorization");
  const presented = header?.startsWith("Bearer ") ? header.slice("Bearer ".length) : "";
  const left = Buffer.from(presented);
  const right = Buffer.from(expected);
  if (left.length !== right.length) {
    timingSafeEqual(right, right);
    return false;
  }
  return timingSafeEqual(left, right);
}
