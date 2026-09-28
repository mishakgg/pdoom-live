import { getSource } from "@pdoom/db";
import { errorResponse } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const source = await getSource(slug);
  if (!source) return errorResponse(404, "not_found", "Source not found.");
  return Response.json(source);
});
