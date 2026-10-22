import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { assertSixMemberBuildTarget } from "./classroom/config.js";

export default defineConfig(({ command, mode }) => {
  if (command === "build") assertSixMemberBuildTarget(loadEnv(mode, import.meta.dirname, "VITE_").VITE_WIRE_ADDRESS);
  return {
    plugins: [react()],
    root: resolve(import.meta.dirname, "classroom"),
    envDir: import.meta.dirname,
    build: { outDir: resolve(import.meta.dirname, "dist"), emptyOutDir: true },
  };
});
