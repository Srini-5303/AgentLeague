import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During local dev, proxy API calls to the FastAPI GM on :8000 so SSE works
// without CORS friction. In Azure, set VITE_API_BASE to the Container App URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/turn": { target: "http://localhost:8000", changeOrigin: true },
      "/state": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
