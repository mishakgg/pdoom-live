import { setDatabaseReady } from "@pdoom/observability";
import { observe } from "@/lib/observe";
import { readinessResponse } from "@/lib/readiness-response";

export const dynamic = "force-dynamic";

export const GET = observe("health", async function GET() {
  const response = await readinessResponse();
  try {
    const report = (await response.clone().json()) as { checks?: { database?: string } };
    setDatabaseReady(report.checks?.database === "ok");
  } catch {
    setDatabaseReady(false);
  }
  return response;
});
