import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "ui-avatars.com",
        pathname: "/api/**",
      },
    ],
  },
  // outputFileTracingRoot is deliberately not set.
  //
  // It silenced a local workspace-root warning, but Vercel's Next builder
  // assumes the app root is the repo root and re-roots .next and the .nft.json
  // traces against it. With Root Directory set to `frontend`, every traced
  // path came out shifted, the routing manifest landed where the CDN does not
  // look, and every route returned a platform 404 while the build reported
  // success. See vercel/next.js#88579.
};

export default nextConfig;
