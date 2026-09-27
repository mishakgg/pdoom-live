import { execFileSync } from "node:child_process";

export default function globalSetup(): void {
  execFileSync(process.execPath, ["--import", "tsx", "e2e/bootstrap.ts"], {
    stdio: "inherit",
    env: process.env,
  });
}
