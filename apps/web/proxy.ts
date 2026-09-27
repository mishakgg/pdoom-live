import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const CORRELATION_ID = /^[A-Za-z0-9_-]{8,64}$/;

function requestId(incoming: string | null): string {
  if (incoming && CORRELATION_ID.test(incoming)) return incoming;
  return crypto.randomUUID().replace(/-/g, "");
}

export function proxy(request: NextRequest) {
  const id = requestId(request.headers.get("x-request-id"));
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-request-id", id);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("x-request-id", id);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
