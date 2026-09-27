import { getPool } from "@pdoom/db";
import { setDatabaseReady } from "@pdoom/observability";
import { observe } from "@/lib/observe";

export const dynamic = "force-dynamic";

export const GET = observe("health", async function GET() {
  try {
    await getPool().query("SELECT 1");
    setDatabaseReady(true);
    return Response.json({ ok: true });
  } catch {
    setDatabaseReady(false);
    return Response.json({ ok: false }, { status: 503 });
  }
});
