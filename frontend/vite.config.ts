import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Set VITE_API_PROXY (e.g. http://localhost:8102) to point the dev server at a different backend.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: { "/api": env.VITE_API_PROXY ?? "http://localhost:8001" },
    },
    build: {
      chunkSizeWarningLimit: 600,
    },
    test: { environment: "node", include: ["src/**/*.test.{ts,tsx}"] },
  };
});
