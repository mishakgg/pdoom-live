import { parseSearchParams, searchQuerySchema } from "@pdoom/contracts";
import { searchPublic } from "@pdoom/db";
import { queryError } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const query = searchQuerySchema.parse(parseSearchParams(new URL(request.url).searchParams));
    return Response.json(await searchPublic(query));
  } catch (error) {
    return queryError(error);
  }
}
