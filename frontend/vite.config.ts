import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/matches": "http://localhost:8000",
      "/companies": "http://localhost:8000",
      "/tracker": "http://localhost:8000",
      "/applications": "http://localhost:8000",
      "/cv-variants": "http://localhost:8000",
      "/trigger-scan": "http://localhost:8000",
      "/scan-status": "http://localhost:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
