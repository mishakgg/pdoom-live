import { listTopics } from "@pdoom/db";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json({ data: await listTopics() });
}
