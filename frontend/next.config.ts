import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 16 blocks dev resources for other hostnames; allow 127.0.0.1 used by local tooling.
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    // In production Vercel Services route /api/* to the FastAPI service; locally we proxy to uvicorn.
    if (process.env.NODE_ENV !== "development") return [];
    const backend = process.env.BACKEND_DEV_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
