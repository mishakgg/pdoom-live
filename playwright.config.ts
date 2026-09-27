import { defineConfig } from "@playwright/test";
import {
  downBaseURL,
  downDatabaseUrl,
  downPort,
  emptyBaseURL,
  emptyDatabaseUrl,
  emptyPort,
  fixtureBaseURL,
  fixtureDatabaseUrl,
  fixturePort,
  serverEnv,
} from "./e2e/support/env";

const desktop = { width: 1280, height: 800 };
const mobile = { width: 390, height: 844 };

export default defineConfig({
  testDir: "e2e",
  globalSetup: "./e2e/global-setup.ts",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  outputDir: "test-results",
  use: {
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: { viewport: desktop, baseURL: fixtureBaseURL },
      testIgnore: /\/(empty-live|database-down)\.spec\.ts/,
    },
    {
      name: "mobile",
      use: { viewport: mobile, baseURL: fixtureBaseURL, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
      testIgnore: /\/(empty-live|database-down|performance)\.spec\.ts/,
    },
    {
      name: "empty-live",
      use: { viewport: desktop, baseURL: emptyBaseURL },
      testMatch: /empty-live\.spec\.ts/,
    },
    {
      name: "database-down",
      use: { viewport: desktop, baseURL: downBaseURL },
      testMatch: /database-down\.spec\.ts/,
    },
  ],
  webServer: [
    {
      command: `npm run start -w @pdoom/web -- -H 127.0.0.1 -p ${fixturePort}`,
      url: `${fixtureBaseURL}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: serverEnv(fixtureDatabaseUrl, fixturePort),
    },
    {
      command: `npm run start -w @pdoom/web -- -H 127.0.0.1 -p ${emptyPort}`,
      url: `${emptyBaseURL}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: serverEnv(emptyDatabaseUrl, emptyPort),
    },
    {
      command: `npm run start -w @pdoom/web -- -H 127.0.0.1 -p ${downPort}`,
      url: `${downBaseURL}/methodology`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: serverEnv(downDatabaseUrl, downPort),
    },
  ],
});
