import { handlePublicApi } from "@/lib/public-api-handler";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return handlePublicApi(request);
}
