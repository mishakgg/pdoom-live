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

export type PublicRepresentation = {
  body: string;
  etag: string;
  headers: [string, string][];
};

function etagMatches(header: string, etag: string): boolean {
  return header.split(",").some((part) => {
    const token = part.trim();
    if (token === "*") return true;
    return token.replace(/^W\//, "") === etag;
  });
}

function baseHeaders(extraHeaders?: Record<string, string>): Headers {
  const headers = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "public, max-age=60, stale-while-revalidate=300",
    "x-api-version": PUBLIC_API_VERSION,
    "x-export-schema-version": PUBLIC_EXPORT_SCHEMA_VERSION,
    "access-control-allow-origin": "*",
  });
  for (const [key, value] of Object.entries(extraHeaders ?? {})) headers.set(key, value);
  return headers;
}

/**
 * Strong ETag of the response bytes. Last-Modified is omitted: dataset import
 * time does not change on curator corrections, and HTTP-date cannot tell two
 * changes in the same second apart.
 */
export function representPublicJson(body: unknown, extraHeaders?: Record<string, string>): PublicRepresentation {
  const payload = JSON.stringify(body);
  const etag = `"${createHash("sha256").update(payload).digest("hex")}"`;
  const headers = baseHeaders(extraHeaders);
  headers.set("etag", etag);
  return { body: payload, etag, headers: [...headers.entries()] };
}

export function applyPublicValidators(request: Request, representation: PublicRepresentation): Response {
  const headers = new Headers(representation.headers);
  const noneMatch = request.headers.get("if-none-match");
  // If-None-Match is the only supported validator. A present If-None-Match
  // wins over If-Modified-Since, including when the ETag does not match.
  if (noneMatch !== null && etagMatches(noneMatch, representation.etag)) {
    return new Response(null, { status: 304, headers });
  }
  return new Response(representation.body, { status: 200, headers });
}

export function publicJson(request: Request, body: unknown, extraHeaders?: Record<string, string>): Response {
  return applyPublicValidators(request, representPublicJson(body, extraHeaders));
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
