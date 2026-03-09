import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "logo.clearbit.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "ui-avatars.com",
        pathname: "/api/**",
      },
      {
        protocol: "https",
        hostname: "logos.composio.dev",
        pathname: "/api/**",
      },
      {
        protocol: "https",
        hostname: "ticktick.com",
        pathname: "/**",
      },
    ],
  },
  // Fix workspace root detection
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
