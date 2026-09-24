import { getOverview } from "@pdoom/db";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await getOverview());
}
