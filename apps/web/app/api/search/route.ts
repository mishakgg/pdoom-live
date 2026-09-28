import { parseSearchParams, searchQuerySchema } from "@pdoom/contracts";
import { searchPublic } from "@pdoom/db";
import { queryError } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(request: Request) {
  try {
    const query = searchQuerySchema.parse(parseSearchParams(new URL(request.url).searchParams));
    return Response.json(await searchPublic(query));
  } catch (error) {
    return queryError(error);
  }
});
