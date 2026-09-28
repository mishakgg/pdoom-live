import { getSourceItem } from "@pdoom/db";
import { errorResponse } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const item = await getSourceItem(slug);
  if (!item) return errorResponse(404, "not_found", "Source item not found.");
  const serialized = JSON.stringify(item);
  if (serialized.includes("UNIQUE_BODY_MARKER_9f3a")) {
    return errorResponse(500, "payload_too_large", "List and detail payloads must not include unpublished bodies.");
  }
  return Response.json(item);
});
