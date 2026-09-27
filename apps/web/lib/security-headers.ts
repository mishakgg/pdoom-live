import { randomBytes } from "node:crypto";

export type SecurityHeaderOptions = {
  nonce: string;
  development: boolean;
  hsts: boolean;
};

export function createNonce(): string {
  return randomBytes(16).toString("base64");
}

export function contentSecurityPolicy(options: SecurityHeaderOptions): string {
  const script = ["script-src 'self'", `'nonce-${options.nonce}'`, "'strict-dynamic'"];
  if (options.development) script.push("'unsafe-eval'");
  const style = options.development
    ? "style-src 'self' 'unsafe-inline'"
    : `style-src 'self' 'nonce-${options.nonce}'`;
  const directives = [
    "default-src 'self'",
    script.join(" "),
    style,
    "img-src 'self'",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "frame-src 'none'",
    "script-src-attr 'none'",
  ];
  if (options.hsts) directives.push("upgrade-insecure-requests");
  return directives.join("; ");
}

export function applySecurityHeaders(headers: Headers, options: SecurityHeaderOptions): void {
  headers.set("Content-Security-Policy", contentSecurityPolicy(options));
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  headers.set("X-Frame-Options", "DENY");
  headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  );
  if (options.hsts) {
    headers.set("Strict-Transport-Security", "max-age=15552000");
  } else {
    headers.delete("Strict-Transport-Security");
  }
}
