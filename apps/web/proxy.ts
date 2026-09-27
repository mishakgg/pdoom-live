import { readRuntimeConfig } from "@pdoom/db";
import { NextRequest, NextResponse } from "next/server";
import { applicationReady } from "./lib/ready-cache";
import { applySecurityHeaders, contentSecurityPolicy, createNonce, type SecurityHeaderOptions } from "./lib/security-headers";

const PROBES = new Set(["/api/live", "/api/ready", "/api/health"]);

function headerOptions(): SecurityHeaderOptions {
  const config = readRuntimeConfig();
  return {
    nonce: createNonce(),
    development: config.mode === "development",
    hsts: config.hsts,
  };
}

export async function proxy(request: NextRequest) {
  const options = headerOptions();
  const policy = contentSecurityPolicy(options);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", options.nonce);
  requestHeaders.set("Content-Security-Policy", policy);

  const path = request.nextUrl.pathname;
  if (!PROBES.has(path) && !(await applicationReady())) {
    const headers = new Headers();
    applySecurityHeaders(headers, options);
    headers.set("Cache-Control", "no-store");
    const wantsHtml = request.headers.get("accept")?.includes("text/html") && !path.startsWith("/api/");
    if (wantsHtml) {
      headers.set("Content-Type", "text/html; charset=utf-8");
      return new NextResponse("<!doctype html><title>pdoom.live</title><p>pdoom.live is not ready.</p>", {
        status: 503,
        headers,
      });
    }
    headers.set("Content-Type", "application/json; charset=utf-8");
    return new NextResponse(
      JSON.stringify({ error: { code: "not_ready", message: "Application is not ready." } }),
      { status: 503, headers },
    );
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  applySecurityHeaders(response.headers, options);
  if (PROBES.has(path)) response.headers.set("Cache-Control", "no-store");
  return response;
}

export const config = {
  matcher: [
    {
      source: "/((?!_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
