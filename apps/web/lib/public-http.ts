import { createHash } from "node:crypto";
import { PUBLIC_API_VERSION, PUBLIC_EXPORT_SCHEMA_VERSION } from "@pdoom/contracts";

export function publicError(status: number, code: string, message: string, extraHeaders?: Record<string, string>) {
  const headers = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-api-version": PUBLIC_API_VERSION,
    "access-control-allow-origin": "*",
  });
  for (const [key, value] of Object.entries(extraHeaders ?? {})) headers.set(key, value);
  return new Response(JSON.stringify({ error: { code, message } }), { status, headers });
}

function etagMatches(header: string, etag: string): boolean {
  return header.split(",").some((part) => part.trim().replace(/^W\//, "") === etag);
}

/** Cache validators for public GETs. Last-Modified is the dataset import time when provided. */
export function publicJson(
  request: Request,
  body: unknown,
  lastModified: string | null,
  extraHeaders?: Record<string, string>,
): Response {
  const payload = JSON.stringify(body);
  const etag = `"${createHash("sha256").update(payload).digest("hex")}"`;
  const headers = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "public, max-age=60, stale-while-revalidate=300",
    etag,
    "x-api-version": PUBLIC_API_VERSION,
    "x-export-schema-version": PUBLIC_EXPORT_SCHEMA_VERSION,
    "access-control-allow-origin": "*",
  });
  for (const [key, value] of Object.entries(extraHeaders ?? {})) headers.set(key, value);
  let modified: Date | null = null;
  if (lastModified) {
    const date = new Date(lastModified);
    if (!Number.isNaN(date.getTime())) {
      modified = date;
      headers.set("last-modified", date.toUTCString());
    }
  }
  const noneMatch = request.headers.get("if-none-match");
  if (noneMatch && etagMatches(noneMatch, etag)) return new Response(null, { status: 304, headers });
  const modifiedSince = request.headers.get("if-modified-since");
  if (!noneMatch && modifiedSince && modified) {
    const since = new Date(modifiedSince);
    // HTTP-date has one-second resolution. Compare truncated instants so a
    // client echoing Last-Modified is not treated as stale by leftover milliseconds.
    if (!Number.isNaN(since.getTime()) && Math.floor(since.getTime() / 1000) >= Math.floor(modified.getTime() / 1000)) {
      return new Response(null, { status: 304, headers });
    }
  }
  return new Response(payload, { status: 200, headers });
}

export function apiEnvelope(data: unknown, page?: unknown, extra?: Record<string, unknown>) {
  return {
    api_version: PUBLIC_API_VERSION,
    export_schema_version: PUBLIC_EXPORT_SCHEMA_VERSION,
    ...extra,
    data,
    ...(page ? { page } : {}),
  };
}
