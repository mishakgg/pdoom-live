import type pg from "pg";
import { migrationState, type MigrationStatus } from "./migrate";
import { getPool } from "./pool";

export type ReadinessReport = {
  status: "ready" | "not_ready";
  checks: {
    process: "live";
    database: "ok" | "unavailable";
    migrations: MigrationStatus | "unknown";
  };
};

async function ping(pool: pg.Pool): Promise<boolean> {
  try {
    await pool.query("SELECT 1");
    return true;
  } catch {
    try {
      await pool.query("SELECT 1");
      return true;
    } catch {
      return false;
    }
  }
}

export async function readinessReport(pool?: pg.Pool): Promise<ReadinessReport> {
  let active: pg.Pool;
  try {
    active = pool ?? getPool();
  } catch {
    return {
      status: "not_ready",
      checks: { process: "live", database: "unavailable", migrations: "unknown" },
    };
  }
  if (!(await ping(active))) {
    return {
      status: "not_ready",
      checks: { process: "live", database: "unavailable", migrations: "unknown" },
    };
  }
  try {
    const migrations = await migrationState(active);
    if (migrations !== "current") {
      return {
        status: "not_ready",
        checks: { process: "live", database: "ok", migrations },
      };
    }
  } catch {
    return {
      status: "not_ready",
      checks: { process: "live", database: "ok", migrations: "unknown" },
    };
  }
  return {
    status: "ready",
    checks: { process: "live", database: "ok", migrations: "current" },
  };
}
