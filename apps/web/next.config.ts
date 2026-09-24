import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@pdoom/contracts", "@pdoom/db"],
  poweredByHeader: false,
};

export default nextConfig;
