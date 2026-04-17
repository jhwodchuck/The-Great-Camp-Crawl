import type { NextConfig } from "next";

const API_HOST =
  process.env.NEXT_PUBLIC_API_URL ?? "https://the-great-camp-crawl-api.vercel.app";

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      // beforeFiles ensures these rewrites run before Next.js's own /api/* handling,
      // so requests to /api/* are proxied to the backend rather than returning 404.
      beforeFiles: [
        {
          source: "/api/:path*",
          destination: `${API_HOST}/api/:path*`,
        },
        {
          source: "/health",
          destination: `${API_HOST}/health`,
        },
      ],
    };
  },
};

export default nextConfig;
