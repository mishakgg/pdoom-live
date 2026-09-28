import { parseSearchParams, peopleListQuerySchema } from "@pdoom/contracts";
import { listPeople } from "@pdoom/db";
import { queryError } from "@/lib/http";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("api", async function GET(request: Request) {
  try {
    const query = peopleListQuerySchema.parse(parseSearchParams(new URL(request.url).searchParams));
    return Response.json(await listPeople(query));
  } catch (error) {
    return queryError(error);
  }
});
