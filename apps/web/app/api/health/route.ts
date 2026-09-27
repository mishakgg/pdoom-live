import { readinessResponse } from "@/lib/readiness-response";

export const dynamic = "force-dynamic";

export function GET() {
  return readinessResponse();
}
