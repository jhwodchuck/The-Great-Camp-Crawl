import type { NextConfig } from "next";

const API_HOST =
  process.env.NEXT_PUBLIC_API_URL ?? "https://the-great-camp-crawl-api.vercel.app";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_HOST}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${API_HOST}/health`,
      },
    ];
  },
};

export default nextConfig;
