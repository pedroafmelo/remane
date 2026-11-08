import type { NextConfig } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants";

// Build: export estático em web/dist, servido pelo FastAPI (escalista.api.app, imagem única).
// Dev: proxy para a API na porta 8000 (rewrites não existem no export estático).
export default function config(phase: string): NextConfig {
  if (phase === PHASE_PRODUCTION_BUILD) {
    return { output: "export", distDir: "dist", trailingSlash: true };
  }
  return {
    async rewrites() {
      return [
        { source: "/api/:path*", destination: "http://localhost:8000/api/:path*" },
        { source: "/auth/:path*", destination: "http://localhost:8000/auth/:path*" }, // login e logout de demo ficam fora de /api
        { source: "/health", destination: "http://localhost:8000/health" },
      ];
    },
  };
}
