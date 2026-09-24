import { parseSearchParams, peopleListQuerySchema } from "@pdoom/contracts";
import { listPeople } from "@pdoom/db";
import { queryError } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const query = peopleListQuerySchema.parse(parseSearchParams(new URL(request.url).searchParams));
    return Response.json(await listPeople(query));
  } catch (error) {
    return queryError(error);
  }
}
