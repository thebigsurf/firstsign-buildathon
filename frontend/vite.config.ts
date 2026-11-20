import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8001" },
  },
  build: {
    chunkSizeWarningLimit: 600,
  },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
