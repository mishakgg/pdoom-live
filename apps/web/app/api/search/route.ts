import { searchAll } from "@pdoom/db";
import { errorResponse } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(request: Request) {
  const q = new URL(request.url).searchParams.get("q")?.trim() ?? "";
  if (q.length < 2 || q.length > 200) return errorResponse(400, "invalid_query", "Search text must be 2–200 characters.");
  return Response.json(await searchAll(q));
});
