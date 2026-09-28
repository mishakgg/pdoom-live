import { readinessReport } from "@pdoom/db";

export async function readinessResponse(): Promise<Response> {
  const report = await readinessReport();
  return Response.json(report, {
    status: report.status === "ready" ? 200 : 503,
    headers: { "Cache-Control": "no-store" },
  });
}
