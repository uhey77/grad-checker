import { defineConfig } from "vite";

const proxy = {
  "/api": {
    target: process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
    changeOrigin: false,
  },
};

export default defineConfig({
  server: { proxy },
  preview: { proxy },
});
