import { observe } from "@/lib/observe";
import { operationalReport } from "@/lib/operational";

export const dynamic = "force-dynamic";

export const GET = observe("status", async function GET() {
  const report = await operationalReport();
  const status = report.status.app === "operational" ? 200 : 503;
  return Response.json(report.status, {
    status,
    headers: { "cache-control": "no-store" },
  });
});
