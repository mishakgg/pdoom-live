import { getTrend } from "@pdoom/db";
import { errorResponse } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const trend = await getTrend(slug);
  if (!trend) return errorResponse(404, "not_found", "Trend not found.");
  return Response.json(trend);
});
