import nextConfig from "eslint-config-next";

const config = [
  ...nextConfig,
  {
    settings: {
      next: {
        rootDir: "apps/web",
      },
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "coverage/**", "data/fixtures/synthetic/dataset.json"],
  },
];

export default config;
