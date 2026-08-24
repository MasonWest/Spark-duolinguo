import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // bind all interfaces, so both localhost and 127.0.0.1 work
    port: 6001, // 统一使用 6001（6000 被 Chromium 列为 ERR_UNSAFE_PORT）
    proxy: {
      // Forward API calls to the FastAPI backend on port 9000
      "/api": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
    },
  },
});
