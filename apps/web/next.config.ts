import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  async rewrites() {
    const api = process.env.API_PROXY_URL ?? "http://127.0.0.1:8000";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health", destination: `${api}/health` },
      { source: "/ready", destination: `${api}/ready` },
    ];
  },
};

export default nextConfig;
