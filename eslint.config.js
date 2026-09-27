import nextConfig from "eslint-config-next";

const config = [
  {
    ignores: [
      "**/.next/**",
      "**/node_modules/**",
      "**/coverage/**",
      "data/fixtures/synthetic/dataset.json",
      "playwright-report/**",
      "test-results/**",
      "blob-report/**",
    ],
  },
  ...nextConfig,
  {
    settings: {
      next: {
        rootDir: "apps/web",
      },
    },
  },
];

export default config;
