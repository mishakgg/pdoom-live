import { ZodError } from "zod";
import { InvalidCursorError } from "@pdoom/db";

export function errorResponse(status: number, code: string, message: string) {
  return Response.json({ error: { code, message } }, { status });
}

export function isInvalidCursor(error: unknown): boolean {
  return error instanceof InvalidCursorError || (error instanceof Error && error.name === "InvalidCursorError");
}

export function queryError(error: unknown) {
  if (isInvalidCursor(error)) return errorResponse(400, "invalid_cursor", "Cursor is invalid.");
  if (error instanceof ZodError) return errorResponse(400, "invalid_query", "Query parameters are invalid.");
  if (error instanceof Error && error.message.startsWith("duplicate query")) {
    return errorResponse(400, "invalid_query", "Duplicate query parameters are not accepted.");
  }
  console.error("query failed");
  return errorResponse(500, "query_failed", "The query could not be completed.");
}
