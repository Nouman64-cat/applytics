import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next.js blocks cross-origin requests to dev-only assets (HMR websocket, etc.) by
  // default. Wildcarded so it survives ngrok free-tier restarts, which mint a new
  // random subdomain every time the tunnel reconnects.
  allowedDevOrigins: ["*.ngrok-free.app"],
};

export default nextConfig;
