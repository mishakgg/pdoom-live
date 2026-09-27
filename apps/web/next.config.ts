import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@pdoom/contracts", "@pdoom/db", "@pdoom/observability"],
  poweredByHeader: false,
};

export default nextConfig;
