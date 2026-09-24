import { getPerson } from "@pdoom/db";
import { errorResponse } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const person = await getPerson(slug);
  if (!person) return errorResponse(404, "not_found", "Person not found.");
  return Response.json(person);
}
