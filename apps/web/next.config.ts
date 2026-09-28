import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appDir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(appDir, "../.."),
  outputFileTracingIncludes: {
    "/opengraph-image": ["./assets/fonts/SourceSans3-Regular.ttf"],
    "/people/[slug]/opengraph-image": ["./assets/fonts/SourceSans3-Regular.ttf"],
    "/topics/[slug]/opengraph-image": ["./assets/fonts/SourceSans3-Regular.ttf"],
    "/statements/[slug]/opengraph-image": ["./assets/fonts/SourceSans3-Regular.ttf"],
    "/sources/[slug]/opengraph-image": ["./assets/fonts/SourceSans3-Regular.ttf"],
    "/source-items/[slug]/opengraph-image": ["./assets/fonts/SourceSans3-Regular.ttf"],
    "/trends/[slug]/opengraph-image": ["./assets/fonts/SourceSans3-Regular.ttf"],
  },
  transpilePackages: ["@pdoom/contracts", "@pdoom/db", "@pdoom/observability"],
  poweredByHeader: false,
  trailingSlash: false,
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
          },
        ],
      },
      {
        source: "/api/:path*",
        headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
      },
    ];
  },
};

export default nextConfig;
