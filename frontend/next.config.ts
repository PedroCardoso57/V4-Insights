import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  // Em desenvolvimento, /api é encaminhado ao FastAPI (mesma origem → cookies de sessão).
  // Em produção, o proxy reverso (Caddy) faz esse roteamento.
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    const api = process.env.API_PROXY_URL ?? "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health/:path*", destination: `${api}/health/:path*` },
    ];
  },
};

export default config;
