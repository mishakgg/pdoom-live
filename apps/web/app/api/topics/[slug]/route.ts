import { getTopic } from "@pdoom/db";
import { errorResponse } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const topic = await getTopic(slug);
  if (!topic) return errorResponse(404, "not_found", "Topic not found.");
  return Response.json(topic);
});
