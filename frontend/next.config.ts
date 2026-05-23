import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Optional: proxy API calls during local dev when NEXT_PUBLIC_API_URL is unset
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_URL;
    if (!apiBase) {
      return [
        {
          source: "/api/:path*",
          destination: "http://localhost:8000/api/:path*",
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
