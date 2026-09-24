import { z } from "zod";

const databaseUrl = z.string().regex(/^postgres(ql)?:\/\//, "DATABASE_URL must be a postgres URL");

export function readDatabaseUrl(name = "DATABASE_URL"): string {
  const value = process.env[name] ?? (name === "DATABASE_URL" ? undefined : process.env.DATABASE_URL);
  const parsed = databaseUrl.safeParse(value);
  if (!parsed.success) {
    throw new Error(`${name} is missing or not a postgres URL`);
  }
  return parsed.data;
}

export function assertTestDatabase(url: string): void {
  const dbName = new URL(url).pathname.replace(/^\//, "");
  if (!dbName.includes("test")) {
    throw new Error(`Refusing to run destructive tests against database "${dbName}"`);
  }
}
