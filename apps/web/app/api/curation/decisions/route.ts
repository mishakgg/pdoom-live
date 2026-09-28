import { curationEnabled, reviewCommandSchema } from "@pdoom/contracts";
import { applyReviewDecision, getPool } from "@pdoom/db";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!curationEnabled()) return new Response(null, { status: 404 });
  try {
    const command = reviewCommandSchema.parse(await request.json());
    const result = await applyReviewDecision(getPool(), command);
    return Response.json(result);
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "review failed" }, { status: 400 });
  }
}
