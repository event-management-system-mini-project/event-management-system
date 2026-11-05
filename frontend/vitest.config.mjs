import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{js,jsx}"],
    setupFiles: ["./src/test/setup.js"],
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{js,jsx}"],
      exclude: ["src/**/*.test.{js,jsx}", "src/test/**"],
      reporter: ["text", "json-summary", "json", "html"],
      reportsDirectory: "../docs/part-3/coverage/frontend",
    },
  },
});
