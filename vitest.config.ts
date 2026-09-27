import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "node",
    fileParallelism: false,
    setupFiles: ["./test/setup.ts"],
    globalSetup: ["./test/global-setup.ts"],
    testTimeout: 30_000,
    hookTimeout: 30_000,
    exclude: [
      "**/node_modules/**",
      "**/dist/**",
      "**/.{idea,git,cache,output,temp}/**",
      "**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*",
      "e2e/**",
      "playwright.config.ts",
    ],
  },
  resolve: {
    alias: {
      "@": new URL("./apps/web", import.meta.url).pathname,
    },
  },
});
