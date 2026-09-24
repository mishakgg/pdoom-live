import { parseSearchParams, statementListQuerySchema } from "@pdoom/contracts";
import { listStatements } from "@pdoom/db";
import { queryError } from "@/lib/http";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const query = statementListQuerySchema.parse(parseSearchParams(new URL(request.url).searchParams));
    const page = await listStatements(query);
    return Response.json(page);
  } catch (error) {
    return queryError(error);
  }
}
