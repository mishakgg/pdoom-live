import { getOverview } from "@pdoom/db";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET() {
  return Response.json(await getOverview());
});
