import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  root: resolve(import.meta.dirname, "classroom"),
  envDir: import.meta.dirname,
  build: { outDir: resolve(import.meta.dirname, "dist"), emptyOutDir: true },
});
