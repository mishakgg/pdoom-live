import { errorResponse } from "@/lib/http";
import { metricsAuthorized, metricsEnabled } from "@/lib/metrics-access";
import { observe } from "@/lib/observe";
import { operationalMetrics } from "@/lib/operational";

export const dynamic = "force-dynamic";

export const GET = observe("metrics", async function GET(request: Request) {
  if (!metricsEnabled()) return errorResponse(404, "not_found", "Not found.");
  if (!metricsAuthorized(request)) return errorResponse(403, "forbidden", "Forbidden.");
  return new Response(await operationalMetrics(), {
    headers: {
      "content-type": "text/plain; version=0.0.4; charset=utf-8",
      "cache-control": "no-store",
    },
  });
});
