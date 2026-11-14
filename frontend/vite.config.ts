import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const gateway = process.env.GATEWAY_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": gateway, "/v1": gateway, "/.well-known": gateway } },
  build: { sourcemap: false, chunkSizeWarningLimit: 900 },
});
