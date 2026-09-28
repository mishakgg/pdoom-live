import { getPerson } from "@pdoom/db";
import { errorResponse } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const person = await getPerson(slug);
  if (!person) return errorResponse(404, "not_found", "Person not found.");
  return Response.json(person);
});
