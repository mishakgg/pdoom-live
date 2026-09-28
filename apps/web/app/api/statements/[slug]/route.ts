import { getStatement } from "@pdoom/db";
import { errorResponse } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const statement = await getStatement(slug);
  if (!statement) return errorResponse(404, "not_found", "Statement not found.");
  return Response.json(statement);
});
