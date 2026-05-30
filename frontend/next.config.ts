import type { NextConfig } from "next";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

/**
 * Minimal loader for the project-root .env (one directory above frontend/).
 * Next.js only auto-loads .env files inside the frontend dir, so we read the
 * shared root .env here to source the backend API URL for the CSP. No secret
 * values are emitted — only the public backend URL is used.
 */
function loadRootEnv(): Record<string, string> {
  try {
    const raw = readFileSync(resolve(process.cwd(), "..", ".env"), "utf8");
    const out: Record<string, string> = {};
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq === -1) continue;
      out[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
    }
    return out;
  } catch {
    return {};
  }
}

const env = loadRootEnv();

const BACKEND_HOST = env.BACKEND_HOST || "127.0.0.1";
const BACKEND_PORT = env.BACKEND_PORT || "8002";
const APP_URL = (env.APP_URL || "").trim();

// Local backend origin (used in development) + production app origin from .env.
const BACKEND_LOCAL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const connectSources = ["'self'", BACKEND_LOCAL, APP_URL].filter(Boolean).join(" ");

// Content-Security-Policy as specified in the project requirements.
const cspDirectives = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  `connect-src ${connectSources}`,
  "font-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: cspDirectives },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
