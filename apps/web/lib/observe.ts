import { acceptCorrelationId, recordHttp, runWithCorrelation } from "@pdoom/observability";

export type ObservedRoute = "health" | "status" | "metrics" | "api";

export function observe<C>(
  route: ObservedRoute,
  handler: (request: Request, context: C) => Promise<Response> | Response,
): (request: Request, context: C) => Promise<Response> {
  return async (request: Request, context: C) => {
    const requestId = acceptCorrelationId(request.headers.get("x-request-id"));
    const started = performance.now();
    try {
      const response = await runWithCorrelation({ requestId }, () => handler(request, context));
      recordHttp(route, response.status, performance.now() - started);
      try {
        response.headers.set("x-request-id", requestId);
        return response;
      } catch {
        const headers = new Headers(response.headers);
        headers.set("x-request-id", requestId);
        return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
      }
    } catch (error) {
      recordHttp(route, 500, performance.now() - started);
      throw error;
    }
  };
}
