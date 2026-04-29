/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/** Browser → Vite → backend (Docker service name). Set in compose as `API_PROXY_TARGET`. */
const API_PROXY_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8001";

/** Bind mounts (e.g. Docker Desktop on Windows) often miss fs events; polling lets HMR pick up host edits. */
const usePoll =
  process.env.CHOKIDAR_USEPOLLING === "true" || process.env.VITE_DEV_POLL === "true";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"]
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    ...(usePoll ? { watch: { usePolling: true, interval: 1000 } } : {}),
    proxy: {
      "/api": {
        target: API_PROXY_TARGET,
        changeOrigin: true
      }
    }
  }
});
