import { defineConfig, loadEnv } from "vite";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL(".", import.meta.url));
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, path.dirname(root), ""), ...process.env };
  return {
    root,
    envDir: path.dirname(root),
    server: {
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      proxy: { "/api": { target: `http://127.0.0.1:${env.GATEWAY_PORT || 3000}` } },
    },
    build: { outDir: "dist", emptyOutDir: true },
  };
});
