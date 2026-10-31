import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In `pnpm dev`, Vite serves the SPA and forwards API calls to uvicorn on :8080.
// In the container there is no Vite: FastAPI serves the built dist/ itself.
export default defineConfig({
  plugins: [tailwindcss(), react()],
  server: {
    proxy: { "/api": "http://localhost:8080", "/health": "http://localhost:8080" },
  },
});
