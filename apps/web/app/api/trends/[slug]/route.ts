import { getTrend } from "@pdoom/db";
import { errorResponse } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const trend = await getTrend(slug);
  if (!trend) return errorResponse(404, "not_found", "Trend not found.");
  return Response.json(trend);
}
