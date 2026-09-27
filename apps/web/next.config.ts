import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@pdoom/contracts", "@pdoom/db"],
  poweredByHeader: false,
  trailingSlash: false,
  async headers() {
    return [
      {
        source: "/api/:path*",
        headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
      },
    ];
  },
};

export default nextConfig;
