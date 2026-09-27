const SQLSTATE = /^[0-9A-Z]{5}$/;
const ERRNO = /^(ECONNREFUSED|ECONNRESET|ENOTFOUND|ETIMEDOUT)$/;

export function dbErrorClass(error: unknown): string {
  const code = readCode(error);
  if (code.startsWith("08") || code === "57P01" || code === "57P02" || code === "57P03" || code === "ECONNREFUSED" || code === "ECONNRESET" || code === "ENOTFOUND") {
    return "connection";
  }
  if (code === "57014" || code === "ETIMEDOUT") return "timeout";
  if (code.startsWith("23")) return "constraint";
  return "unknown";
}

function readCode(error: unknown): string {
  if (typeof error !== "object" || error === null || !("code" in error)) return "";
  const code = (error as { code?: unknown }).code;
  if (typeof code !== "string") return "";
  if (SQLSTATE.test(code) || ERRNO.test(code)) return code;
  return "";
}
