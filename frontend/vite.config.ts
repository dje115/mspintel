import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/** Browser → Vite → backend (Docker service name). Set in compose as `API_PROXY_TARGET`. */
const API_PROXY_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8001";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: API_PROXY_TARGET,
        changeOrigin: true
      }
    }
  }
});
