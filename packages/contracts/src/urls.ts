const BLOCKED_HOSTS = new Set([
  "localhost",
  "localhost.localdomain",
  "metadata.google.internal",
  "metadata.google",
]);

function ipv4ToInt(host: string): number | null {
  const parts = host.split(".");
  if (parts.length !== 4) return null;
  const nums = parts.map((part) => Number(part));
  if (nums.some((n) => !Number.isInteger(n) || n < 0 || n > 255)) return null;
  return (((nums[0]! << 24) >>> 0) + (nums[1]! << 16) + (nums[2]! << 8) + nums[3]!) >>> 0;
}

function inCidr(ip: number, base: number, bits: number): boolean {
  const mask = bits === 0 ? 0 : (~0 << (32 - bits)) >>> 0;
  return (ip & mask) === (base & mask);
}

/** True for loopback, private, link-local, and cloud-metadata addresses. */
export function isBlockedIp(ip: string): boolean {
  const normalized = ip.trim().toLowerCase().replace(/^\[|\]$/g, "");
  if (normalized === "::1" || normalized === "0:0:0:0:0:0:0:1") return true;
  if (normalized.startsWith("fe80:") || normalized.startsWith("fc") || normalized.startsWith("fd")) {
    return true;
  }
  const v4 = ipv4ToInt(normalized);
  if (v4 === null) return false;
  return (
    inCidr(v4, ipv4ToInt("0.0.0.0")!, 8) ||
    inCidr(v4, ipv4ToInt("10.0.0.0")!, 8) ||
    inCidr(v4, ipv4ToInt("127.0.0.0")!, 8) ||
    inCidr(v4, ipv4ToInt("169.254.0.0")!, 16) ||
    inCidr(v4, ipv4ToInt("172.16.0.0")!, 12) ||
    inCidr(v4, ipv4ToInt("192.168.0.0")!, 16) ||
    inCidr(v4, ipv4ToInt("100.64.0.0")!, 10)
  );
}

export function isBlockedHostname(hostname: string): boolean {
  const host = hostname.trim().toLowerCase().replace(/\.$/, "");
  if (!host) return true;
  if (BLOCKED_HOSTS.has(host)) return true;
  if (host.endsWith(".localhost") || host.endsWith(".local") || host.endsWith(".internal")) {
    return true;
  }
  return isBlockedIp(host);
}

export type UrlSafety =
  | { ok: true; url: string }
  | { ok: false; reason: string };

/**
 * Validates a URL that may later be fetched. Does not perform DNS resolution.
 * Collectors must resolve the host and reject blocked IPs before connecting,
 * and must repeat that check on every redirect.
 */
export function assessFetchUrl(input: string): UrlSafety {
  let url: URL;
  try {
    url = new URL(input);
  } catch {
    return { ok: false, reason: "unparseable_url" };
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return { ok: false, reason: "scheme_not_http" };
  }
  if (url.username || url.password) {
    return { ok: false, reason: "embedded_credentials" };
  }
  if (isBlockedHostname(url.hostname)) {
    return { ok: false, reason: "blocked_host" };
  }
  return { ok: true, url: url.toString() };
}

/** URL safe to render as an external link. Returns null for non-http(s) values. */
export function safeExternalUrl(input: string | null | undefined): string | null {
  if (!input) return null;
  const assessed = assessFetchUrl(input);
  if (!assessed.ok) return null;
  return assessed.url;
}
