import { getTopic } from "@pdoom/db";
import { errorResponse } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const topic = await getTopic(slug);
  if (!topic) return errorResponse(404, "not_found", "Topic not found.");
  return Response.json(topic);
}
