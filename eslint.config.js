import nextConfig from "eslint-config-next";

const config = [
  {
    ignores: [
      "**/.next/**",
      "**/node_modules/**",
      "**/coverage/**",
      "data/fixtures/synthetic/dataset.json",
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
